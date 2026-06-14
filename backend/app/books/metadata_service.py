from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone
from app.books.metadata_models import BookMetadata
from app.core.exceptions import NotFoundError
from app.admin.service import log_action
import uuid


async def get_metadata(db: AsyncSession, book_id: uuid.UUID) -> BookMetadata | None:
    result = await db.execute(
        select(BookMetadata).where(BookMetadata.book_id == book_id)
    )
    return result.scalar_one_or_none()


async def create_metadata_from_import(
    db: AsyncSession,
    book_id: uuid.UUID,
    source_title: str | None = None,
    source_author: str | None = None,
    source_description: str | None = None,
    source_publisher: str | None = None,
    source_language: str | None = None,
    source_isbn: str | None = None,
    source_publish_date: str | None = None,
    metadata_source: str = "epub_opf",
) -> BookMetadata:
    meta = BookMetadata(
        book_id=book_id,
        source_title=source_title,
        source_author=source_author,
        source_description=source_description,
        source_publisher=source_publisher,
        source_language=source_language,
        source_isbn=source_isbn,
        source_publish_date=source_publish_date,
        metadata_source=metadata_source,
    )
    db.add(meta)
    await db.flush()
    return meta


async def calibrate_metadata(
    db: AsyncSession,
    book_id: uuid.UUID,
    updates: dict,
    operator_id: uuid.UUID,
) -> BookMetadata:
    result = await db.execute(
        select(BookMetadata).where(BookMetadata.book_id == book_id)
    )
    meta = result.scalar_one_or_none()
    if not meta:
        raise NotFoundError("Metadata not found for this book")

    changed_fields = {}
    for field, value in updates.items():
        if value is not None and hasattr(meta, field):
            old_value = getattr(meta, field)
            if old_value != value:
                changed_fields[field] = {"old": old_value, "new": value}
            setattr(meta, field, value)

    meta.last_calibrated_by = operator_id
    meta.last_calibrated_at = datetime.now(timezone.utc)
    await db.flush()

    # Also update the books table display fields for search/display
    from app.books.models import Book
    book_result = await db.execute(select(Book).where(Book.id == book_id))
    book = book_result.scalar_one_or_none()
    if book:
        if updates.get("calibrated_title"):
            book.title = updates["calibrated_title"]
        if updates.get("calibrated_author"):
            book.author = updates["calibrated_author"]
        if updates.get("calibrated_description"):
            book.description = updates["calibrated_description"]
        if updates.get("calibrated_publisher"):
            book.publisher = updates["calibrated_publisher"]
        if updates.get("calibrated_language"):
            book.language = updates["calibrated_language"]
        if updates.get("calibrated_isbn"):
            book.isbn = updates["calibrated_isbn"]
        await db.flush()

    # Audit log for manual edits
    if changed_fields:
        await log_action(
            db, operator_id, "metadata.calibrate",
            resource_type="book", resource_id=book_id,
            details={"changes": changed_fields},
        )

    return meta
