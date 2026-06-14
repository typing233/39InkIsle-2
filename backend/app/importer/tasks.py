import os
import uuid
from datetime import datetime, timezone
from arq import create_pool
from arq.connections import RedisSettings
from sqlalchemy import select
from app.config import get_settings
from app.db.session import async_session_factory
from app.books.models import Book
from app.importer.models import ImportTask, ImportFolder
from app.importer.scanner import scan_folder, compute_file_hash
from app.importer.parsers.epub_parser import EpubParser
from app.importer.parsers.pdf_parser import PdfParser
from app.importer.parsers.cbz_parser import CbzParser

settings = get_settings()

PARSERS = [EpubParser(), PdfParser(), CbzParser()]


def get_parser(file_path: str):
    for parser in PARSERS:
        if parser.supports(file_path):
            return parser
    return None


async def process_import_task(ctx: dict, task_id: str):
    async with async_session_factory() as db:
        result = await db.execute(select(ImportTask).where(ImportTask.id == uuid.UUID(task_id)))
        task = result.scalar_one_or_none()
        if not task:
            return

        task.status = "processing"
        task.started_at = datetime.now(timezone.utc)
        await db.commit()

        try:
            file_path = task.file_path

            if not os.path.exists(file_path):
                task.status = "failed"
                task.error_message = "File not found"
                task.completed_at = datetime.now(timezone.utc)
                await db.commit()
                return

            content_hash = compute_file_hash(file_path)

            existing = await db.execute(
                select(Book).where(Book.content_hash == content_hash)
            )
            if existing.scalar_one_or_none():
                task.status = "skipped"
                task.error_message = "Duplicate file"
                task.completed_at = datetime.now(timezone.utc)
                await db.commit()
                return

            parser = get_parser(file_path)
            if not parser:
                task.status = "failed"
                task.error_message = "Unsupported format"
                task.completed_at = datetime.now(timezone.utc)
                await db.commit()
                return

            metadata = parser.parse(file_path)

            cover_path = None
            if metadata.cover_data:
                cover_filename = f"{uuid.uuid4()}.{metadata.cover_ext}"
                cover_full_path = os.path.join(settings.covers_storage_path, cover_filename)
                os.makedirs(settings.covers_storage_path, exist_ok=True)
                with open(cover_full_path, "wb") as f:
                    f.write(metadata.cover_data)
                cover_path = cover_filename

            ext = os.path.splitext(file_path)[1].lower().lstrip(".")
            file_size = os.path.getsize(file_path)

            book = Book(
                title=metadata.title,
                author=metadata.author,
                description=metadata.description,
                cover_path=cover_path,
                file_path=file_path,
                file_format=ext,
                file_size=file_size,
                content_hash=content_hash,
                language=metadata.language,
                publisher=metadata.publisher,
                isbn=metadata.isbn,
                page_count=metadata.page_count,
            )
            db.add(book)
            await db.flush()

            task.status = "completed"
            task.book_id = book.id
            task.completed_at = datetime.now(timezone.utc)
            await db.commit()

        except Exception as e:
            await db.rollback()
            async with async_session_factory() as db2:
                result = await db2.execute(
                    select(ImportTask).where(ImportTask.id == uuid.UUID(task_id))
                )
                task = result.scalar_one_or_none()
                if task:
                    task.retry_count += 1
                    if task.retry_count >= task.max_retries:
                        task.status = "failed"
                        task.error_message = str(e)[:500]
                        task.completed_at = datetime.now(timezone.utc)
                    else:
                        task.status = "pending"
                        task.error_message = f"Retry {task.retry_count}: {str(e)[:400]}"
                    await db2.commit()


async def scan_import_folder(ctx: dict, folder_id: str):
    async with async_session_factory() as db:
        result = await db.execute(
            select(ImportFolder).where(ImportFolder.id == uuid.UUID(folder_id))
        )
        folder = result.scalar_one_or_none()
        if not folder or not folder.is_active:
            return

        files = scan_folder(folder.path)
        existing_paths_result = await db.execute(
            select(ImportTask.file_path).where(ImportTask.folder_id == folder.id)
        )
        existing_paths = set(existing_paths_result.scalars().all())

        new_tasks = []
        for file_info in files:
            if file_info["file_path"] not in existing_paths:
                task = ImportTask(
                    folder_id=folder.id,
                    file_path=file_info["file_path"],
                    file_name=file_info["file_name"],
                )
                db.add(task)
                new_tasks.append(task)

        folder.last_scanned_at = datetime.now(timezone.utc)
        await db.commit()

        redis = await create_pool(RedisSettings.from_dsn(settings.redis_url))
        for task in new_tasks:
            await redis.enqueue_job("process_import_task", str(task.id))
        await redis.close()


async def startup(ctx: dict):
    pass


async def shutdown(ctx: dict):
    pass


class WorkerSettings:
    functions = [process_import_task, scan_import_folder]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    max_jobs = settings.max_import_workers
    job_timeout = 600
