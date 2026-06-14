import pytest
from unittest.mock import patch, AsyncMock
from app.enrichment.service import fetch_enrichment_candidates, apply_enrichment
from app.enrichment.rate_limiter import RedisRateLimiter
import uuid


class TestEnrichmentService:
    """Test metadata enrichment: rate limiting, caching, conflict merge rules."""

    @pytest.mark.asyncio
    async def test_apply_never_overwrites_calibrated(self, db, sample_book_data):
        """External enrichment must not overwrite calibrated fields."""
        from app.books.models import Book
        from app.books.metadata_models import BookMetadata
        from app.users.models import User

        user = User(username="enr_admin", email="enr@test.com", password_hash="x")
        book = Book(**{**sample_book_data, "content_hash": "enr_unique1"})
        db.add_all([user, book])
        await db.flush()

        meta = BookMetadata(
            book_id=book.id,
            source_title="Original Title",
            calibrated_title="Admin Override Title",
            metadata_source="manual",
        )
        db.add(meta)
        await db.flush()

        candidate = {"title": "Google Title", "authors": ["Google Author"], "external_id": "gb123"}
        await apply_enrichment(db, book.id, "google_books", candidate, user.id)

        from sqlalchemy import select
        refreshed = (await db.execute(select(BookMetadata).where(BookMetadata.book_id == book.id))).scalar_one()
        assert refreshed.calibrated_title == "Admin Override Title"
        assert refreshed.source_title == "Original Title"  # not overwritten because already populated

    @pytest.mark.asyncio
    async def test_apply_fills_empty_source_fields(self, db, sample_book_data):
        """External enrichment fills empty source fields."""
        from app.books.models import Book
        from app.books.metadata_models import BookMetadata
        from app.users.models import User

        user = User(username="enr_fill", email="enrfill@test.com", password_hash="x")
        book = Book(**{**sample_book_data, "content_hash": "enr_unique2"})
        db.add_all([user, book])
        await db.flush()

        meta = BookMetadata(book_id=book.id, metadata_source="epub_opf")
        db.add(meta)
        await db.flush()

        candidate = {
            "title": "Enriched Title",
            "authors": ["Author A", "Author B"],
            "description": "A great book about testing.",
            "publisher": "Test Press",
            "language": "en",
            "isbn_13": "9781234567890",
            "published_date": "2023-05-01",
            "external_id": "gb456",
        }
        await apply_enrichment(db, book.id, "google_books", candidate, user.id)

        from sqlalchemy import select
        refreshed = (await db.execute(select(BookMetadata).where(BookMetadata.book_id == book.id))).scalar_one()
        assert refreshed.source_title == "Enriched Title"
        assert refreshed.source_author == "Author A, Author B"
        assert refreshed.source_description == "A great book about testing."
        assert refreshed.source_publisher == "Test Press"
        assert refreshed.source_isbn == "9781234567890"
        assert refreshed.metadata_source == "google_books"

    @pytest.mark.asyncio
    async def test_rate_limiter_blocks_when_exhausted(self):
        """Rate limiter should block requests when tokens are exhausted."""
        mock_redis = AsyncMock()
        limiter = RedisRateLimiter(mock_redis)

        mock_redis.pipeline.return_value.__aenter__ = AsyncMock()
        pipe = AsyncMock()
        pipe.execute = AsyncMock(return_value=[101, True])
        mock_redis.pipeline.return_value = pipe

        result = await limiter.acquire("test_key", max_tokens=100, window_seconds=3600)
        assert result is False

    @pytest.mark.asyncio
    async def test_rate_limiter_allows_within_limit(self):
        """Rate limiter allows requests within the token budget."""
        mock_redis = AsyncMock()
        limiter = RedisRateLimiter(mock_redis)

        pipe = AsyncMock()
        pipe.incr = AsyncMock()
        pipe.expire = AsyncMock()
        pipe.execute = AsyncMock(return_value=[5, True])
        mock_redis.pipeline.return_value = pipe

        result = await limiter.acquire("test_key", max_tokens=100, window_seconds=3600)
        assert result is True
