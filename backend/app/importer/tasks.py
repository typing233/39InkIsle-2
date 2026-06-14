import os
import uuid
import asyncio
from datetime import datetime, timezone
from arq import create_pool
from arq.connections import RedisSettings
from sqlalchemy import select, update
from app.config import get_settings
from app.db.session import async_session_factory
from app.books.models import Book
from app.books.metadata_models import BookMetadata
from app.importer.models import ImportTask, ImportFolder
from app.importer.scanner import scan_folder, compute_file_hash
from app.importer.parsers.epub_parser import EpubParser
from app.importer.parsers.pdf_parser import PdfParser
from app.importer.parsers.cbz_parser import CbzParser
from app.admin.models import AuditLog

settings = get_settings()

PARSERS = [EpubParser(), PdfParser(), CbzParser()]

_scan_locks: dict[str, asyncio.Lock] = {}


def get_parser(file_path: str):
    for parser in PARSERS:
        if parser.supports(file_path):
            return parser
    return None


def _get_scan_lock(folder_id: str) -> asyncio.Lock:
    if folder_id not in _scan_locks:
        _scan_locks[folder_id] = asyncio.Lock()
    return _scan_locks[folder_id]


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
                task.error_message = "File not found or removed"
                task.completed_at = datetime.now(timezone.utc)
                await db.commit()
                return

            content_hash = compute_file_hash(file_path)

            existing = await db.execute(
                select(Book).where(Book.content_hash == content_hash)
            )
            existing_book = existing.scalar_one_or_none()
            if existing_book:
                # File might have moved — update path if different
                if existing_book.file_path != file_path:
                    existing_book.file_path = file_path
                    existing_book.is_available = True
                task.status = "skipped"
                task.error_message = "Duplicate (hash match)"
                task.book_id = existing_book.id
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

            # Create independent metadata record
            format_source_map = {"epub": "epub_opf", "pdf": "pdf_info", "cbz": "cbz_filename"}
            book_meta = BookMetadata(
                book_id=book.id,
                source_title=metadata.title,
                source_author=metadata.author,
                source_description=metadata.description,
                source_publisher=metadata.publisher,
                source_language=metadata.language,
                source_isbn=metadata.isbn,
                source_publish_date=metadata.publish_date,
                metadata_source=format_source_map.get(ext, "unknown"),
            )
            db.add(book_meta)

            task.status = "completed"
            task.book_id = book.id
            task.completed_at = datetime.now(timezone.utc)

            # Audit: book imported
            audit = AuditLog(
                user_id=None,
                action="import.book_completed",
                resource_type="book",
                resource_id=book.id,
                details={"title": metadata.title, "author": metadata.author, "file": file_path},
            )
            db.add(audit)
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
                        # Exponential backoff: re-enqueue with delay
                        task.status = "pending"
                        task.error_message = f"Retry {task.retry_count}/{task.max_retries}: {str(e)[:400]}"
                    await db2.commit()

                # Re-enqueue if retries remain
                if task and task.retry_count < task.max_retries:
                    backoff_seconds = min(60 * (2 ** task.retry_count), 600)
                    redis = await create_pool(RedisSettings.from_dsn(settings.redis_url))
                    await redis.enqueue_job(
                        "process_import_task", str(task.id),
                        _defer_by=backoff_seconds,
                    )
                    await redis.close()


async def scan_import_folder(ctx: dict, folder_id: str):
    lock = _get_scan_lock(folder_id)

    # Prevent concurrent scans of the same folder
    if lock.locked():
        return

    async with lock:
        async with async_session_factory() as db:
            result = await db.execute(
                select(ImportFolder).where(ImportFolder.id == uuid.UUID(folder_id))
            )
            folder = result.scalar_one_or_none()
            if not folder or not folder.is_active:
                return

            # Scan filesystem for current files
            current_files = scan_folder(folder.path)
            current_paths = {f["file_path"] for f in current_files}

            # Get all tasks previously created for this folder
            existing_tasks_result = await db.execute(
                select(ImportTask).where(ImportTask.folder_id == folder.id)
            )
            existing_tasks = list(existing_tasks_result.scalars().all())
            existing_paths = {t.file_path for t in existing_tasks}

            # --- Detect NEW files ---
            new_tasks = []
            for file_info in current_files:
                if file_info["file_path"] not in existing_paths:
                    task = ImportTask(
                        folder_id=folder.id,
                        file_path=file_info["file_path"],
                        file_name=file_info["file_name"],
                    )
                    db.add(task)
                    new_tasks.append(task)

            # --- Detect DELETED/MOVED files ---
            for task in existing_tasks:
                if task.file_path not in current_paths and task.status == "completed" and task.book_id:
                    # File no longer exists at this path — mark book unavailable
                    await db.execute(
                        update(Book).where(Book.id == task.book_id).values(is_available=False)
                    )

            # --- Detect files that reappeared (moved back or restored) ---
            for task in existing_tasks:
                if task.file_path in current_paths and task.status == "completed" and task.book_id:
                    await db.execute(
                        update(Book).where(Book.id == task.book_id).values(is_available=True)
                    )

            folder.last_scanned_at = datetime.now(timezone.utc)
            await db.commit()

            # Enqueue new import tasks
            if new_tasks:
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
