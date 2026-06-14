from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone
from app.reader.models import ReadingProgress
from app.reader.schemas import ProgressUpdate
from app.books.models import Book
from app.core.exceptions import NotFoundError
import uuid
import ebooklib
from ebooklib import epub


async def get_progress(
    db: AsyncSession, user_id: uuid.UUID, book_id: uuid.UUID
) -> list[ReadingProgress]:
    result = await db.execute(
        select(ReadingProgress).where(
            ReadingProgress.user_id == user_id,
            ReadingProgress.book_id == book_id,
        ).order_by(ReadingProgress.updated_at.desc())
    )
    return list(result.scalars().all())


async def update_progress(
    db: AsyncSession, user_id: uuid.UUID, book_id: uuid.UUID, data: ProgressUpdate
) -> ReadingProgress:
    result = await db.execute(
        select(ReadingProgress).where(
            ReadingProgress.user_id == user_id,
            ReadingProgress.book_id == book_id,
            ReadingProgress.device_id == data.device_id,
        )
    )
    progress = result.scalar_one_or_none()

    if progress:
        if data.cfi is not None:
            progress.cfi = data.cfi
        if data.chapter_index is not None:
            progress.chapter_index = data.chapter_index
        if data.progress_percent is not None:
            progress.progress_percent = data.progress_percent
        vc = progress.vector_clock or {}
        vc[data.device_id] = vc.get(data.device_id, 0) + 1
        progress.vector_clock = vc
        progress.updated_at = datetime.now(timezone.utc)
    else:
        progress = ReadingProgress(
            user_id=user_id,
            book_id=book_id,
            cfi=data.cfi,
            chapter_index=data.chapter_index,
            progress_percent=data.progress_percent,
            device_id=data.device_id,
            vector_clock={data.device_id: 1},
        )
        db.add(progress)

    await db.flush()
    return progress


def get_epub_toc(file_path: str) -> list[dict]:
    book = epub.read_epub(file_path)
    toc_items = []

    def _flatten_toc(toc, level=0):
        if isinstance(toc, tuple):
            section, children = toc
            toc_items.append({"title": section.title, "href": section.href, "level": level})
            for child in children:
                _flatten_toc(child, level + 1)
        elif isinstance(toc, epub.Link):
            toc_items.append({"title": toc.title, "href": toc.href, "level": level})

    for item in book.toc:
        _flatten_toc(item)

    return toc_items
