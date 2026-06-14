import pytest
from app.collections.service import (
    ensure_system_collections, get_user_collections, create_collection,
    add_book_to_collection, remove_book_from_collection, delete_collection, is_book_in_favorites,
)
import uuid


class TestCollectionsService:
    """Test collections: system collections, CRUD, favorites check, cross-device sync."""

    @pytest.mark.asyncio
    async def test_system_collections_created(self, db):
        """System collections (Favorites, To Read) are auto-created for new users."""
        from app.users.models import User

        user = User(username="col_user", email="col@test.com", password_hash="x")
        db.add(user)
        await db.flush()

        await ensure_system_collections(db, user.id)
        collections = await get_user_collections(db, user.id)

        names = [c["name"] for c in collections]
        assert "Favorites" in names
        assert "To Read" in names
        assert all(c["is_system"] for c in collections if c["name"] in ("Favorites", "To Read"))

    @pytest.mark.asyncio
    async def test_cannot_delete_system_collection(self, db):
        """System collections cannot be deleted."""
        from app.users.models import User

        user = User(username="col_sys", email="colsys@test.com", password_hash="x")
        db.add(user)
        await db.flush()

        await ensure_system_collections(db, user.id)
        collections = await get_user_collections(db, user.id)
        fav = next(c for c in collections if c["collection_type"] == "favorites")

        with pytest.raises(ValueError, match="Cannot delete system"):
            await delete_collection(db, user.id, fav["id"])

    @pytest.mark.asyncio
    async def test_add_remove_book(self, db, sample_book_data):
        """Can add and remove books from collections."""
        from app.users.models import User
        from app.books.models import Book

        user = User(username="col_add", email="coladd@test.com", password_hash="x")
        book = Book(**{**sample_book_data, "content_hash": "col_unique1"})
        db.add_all([user, book])
        await db.flush()

        col = await create_collection(db, user.id, "My List")
        await add_book_to_collection(db, user.id, col.id, book.id, "device-1")

        assert await is_book_in_favorites(db, user.id, book.id) is False

        await ensure_system_collections(db, user.id)
        collections = await get_user_collections(db, user.id)
        fav = next(c for c in collections if c["collection_type"] == "favorites")
        await add_book_to_collection(db, user.id, fav["id"], book.id)
        assert await is_book_in_favorites(db, user.id, book.id) is True

    @pytest.mark.asyncio
    async def test_vector_clock_increments(self, db, sample_book_data):
        """Vector clock increments when adding items from a device."""
        from app.users.models import User
        from app.books.models import Book
        from app.collections.models import Collection
        from sqlalchemy import select

        user = User(username="col_vc", email="colvc@test.com", password_hash="x")
        book = Book(**{**sample_book_data, "content_hash": "col_vc_1"})
        db.add_all([user, book])
        await db.flush()

        col = await create_collection(db, user.id, "VC Test")
        await add_book_to_collection(db, user.id, col.id, book.id, "phone")

        refreshed = (await db.execute(select(Collection).where(Collection.id == col.id))).scalar_one()
        assert refreshed.vector_clock.get("phone") == 1
