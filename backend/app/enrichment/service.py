from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.books.models import Book
from app.books.metadata_models import BookMetadata
from app.enrichment.google_books import get_cached_or_fetch_google
from app.enrichment.comicvine import get_cached_or_fetch_comicvine
from app.admin.service import log_action
import uuid


async def fetch_enrichment_candidates(db: AsyncSession, book_id: uuid.UUID) -> dict:
    book = (await db.execute(select(Book).where(Book.id == book_id))).scalar_one_or_none()
    if not book:
        return {"google_books": [], "comicvine": []}

    meta = (await db.execute(
        select(BookMetadata).where(BookMetadata.book_id == book_id)
    )).scalar_one_or_none()

    isbn = meta.source_isbn if meta else book.isbn
    title = book.title
    author = book.author

    google_results = []
    comicvine_results = []

    if book.file_format in ("epub", "pdf"):
        google_results = await get_cached_or_fetch_google(db, isbn=isbn, title=title, author=author)

    if book.file_format == "cbz":
        comicvine_results = await get_cached_or_fetch_comicvine(db, title=title)
    else:
        comicvine_results = await get_cached_or_fetch_comicvine(db, title=title)

    return {"google_books": google_results, "comicvine": comicvine_results}


async def apply_enrichment(
    db: AsyncSession,
    book_id: uuid.UUID,
    provider: str,
    candidate_data: dict,
    operator_id: uuid.UUID,
) -> BookMetadata:
    meta = (await db.execute(
        select(BookMetadata).where(BookMetadata.book_id == book_id)
    )).scalar_one_or_none()

    if not meta:
        from app.books.metadata_service import create_metadata_from_import
        meta = await create_metadata_from_import(db, book_id, metadata_source=provider)

    # Only populate source fields that are currently empty; never overwrite calibrated
    if not meta.source_title and candidate_data.get("title"):
        meta.source_title = candidate_data["title"]
    if not meta.source_author:
        authors = candidate_data.get("authors")
        if authors and isinstance(authors, list):
            meta.source_author = ", ".join(authors)
        elif candidate_data.get("publisher"):
            pass
    if not meta.source_description and candidate_data.get("description"):
        meta.source_description = candidate_data["description"][:2000]
    if not meta.source_publisher and candidate_data.get("publisher"):
        meta.source_publisher = candidate_data["publisher"]
    if not meta.source_language and candidate_data.get("language"):
        meta.source_language = candidate_data["language"]
    if not meta.source_isbn:
        isbn = candidate_data.get("isbn_13") or candidate_data.get("isbn_10")
        if isbn:
            meta.source_isbn = isbn
    if not meta.source_publish_date and candidate_data.get("published_date"):
        meta.source_publish_date = candidate_data["published_date"]

    # Store supplementary data in identifiers
    identifiers = dict(meta.identifiers or {})
    identifiers[provider] = {
        "external_id": candidate_data.get("external_id"),
        "fetched_at": str(uuid.uuid4())[:8],
    }
    meta.identifiers = identifiers
    meta.metadata_source = provider

    await db.flush()
    await log_action(db, operator_id, "metadata.enrich", "book", book_id, {
        "provider": provider, "external_id": candidate_data.get("external_id")
    })
    return meta
