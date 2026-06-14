import pytest
from unittest.mock import AsyncMock, patch
from app.reviews.service import create_review, get_reviews_for_book, update_review, delete_review, _recalculate_rating
from app.reviews.schemas import ReviewCreate, ReviewUpdate
import uuid


class TestReviewsService:
    """Test the reviews system: creation, uniqueness, rating recalculation, permissions."""

    @pytest.mark.asyncio
    async def test_create_review(self, db, sample_book_data):
        """Users can create a review with rating 1-5 and optional text."""
        from app.books.models import Book
        from app.users.models import User

        user = User(username="reviewer", email="r@test.com", password_hash="x")
        db.add(user)
        book = Book(**sample_book_data)
        db.add(book)
        await db.flush()

        review = await create_review(db, user.id, book.id, ReviewCreate(rating=4, review_text="Great book"))
        assert review.rating == 4
        assert review.review_text == "Great book"
        assert review.user_id == user.id

    @pytest.mark.asyncio
    async def test_rating_recalculation(self, db, sample_book_data):
        """avg_rating and rating_count update after review CRUD."""
        from app.books.models import Book
        from app.users.models import User

        user1 = User(username="u1", email="u1@test.com", password_hash="x")
        user2 = User(username="u2", email="u2@test.com", password_hash="x")
        db.add_all([user1, user2])
        book = Book(**{**sample_book_data, "content_hash": "unique1"})
        db.add(book)
        await db.flush()

        await create_review(db, user1.id, book.id, ReviewCreate(rating=4))
        await create_review(db, user2.id, book.id, ReviewCreate(rating=2))

        from sqlalchemy import select
        refreshed = (await db.execute(select(Book).where(Book.id == book.id))).scalar_one()
        assert float(refreshed.avg_rating) == 3.0
        assert refreshed.rating_count == 2

    @pytest.mark.asyncio
    async def test_duplicate_review_raises(self, db, sample_book_data):
        """Same user cannot review same book twice (unique constraint)."""
        from app.books.models import Book
        from app.users.models import User
        from sqlalchemy.exc import IntegrityError

        user = User(username="dup", email="dup@test.com", password_hash="x")
        db.add(user)
        book = Book(**{**sample_book_data, "content_hash": "unique2"})
        db.add(book)
        await db.flush()

        await create_review(db, user.id, book.id, ReviewCreate(rating=5))
        with pytest.raises(IntegrityError):
            await create_review(db, user.id, book.id, ReviewCreate(rating=3))

    @pytest.mark.asyncio
    async def test_update_review(self, db, sample_book_data):
        """Users can update their own review."""
        from app.books.models import Book
        from app.users.models import User

        user = User(username="upd", email="upd@test.com", password_hash="x")
        db.add(user)
        book = Book(**{**sample_book_data, "content_hash": "unique3"})
        db.add(book)
        await db.flush()

        await create_review(db, user.id, book.id, ReviewCreate(rating=3))
        updated = await update_review(db, user.id, book.id, ReviewUpdate(rating=5))
        assert updated.rating == 5

    @pytest.mark.asyncio
    async def test_delete_review_recalculates(self, db, sample_book_data):
        """Deleting a review updates avg_rating."""
        from app.books.models import Book
        from app.users.models import User
        from sqlalchemy import select

        user = User(username="del", email="del@test.com", password_hash="x")
        db.add(user)
        book = Book(**{**sample_book_data, "content_hash": "unique4"})
        db.add(book)
        await db.flush()

        await create_review(db, user.id, book.id, ReviewCreate(rating=4))
        await delete_review(db, user.id, book.id)

        refreshed = (await db.execute(select(Book).where(Book.id == book.id))).scalar_one()
        assert refreshed.avg_rating is None
        assert refreshed.rating_count == 0
