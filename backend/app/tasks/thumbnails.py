from pathlib import Path
from PIL import Image
import io
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import select
from app.books.models import Book
from app.enrichment.models import Thumbnail
from app.config import get_settings

THUMBNAIL_SIZES = {
    "small": (150, 225),
    "medium": (300, 450),
    "large": (600, 900),
}


async def generate_thumbnails(ctx: dict, book_id: str) -> None:
    settings = get_settings()
    db_session: async_sessionmaker = ctx["db_session"]

    async with db_session() as db:
        book = (await db.execute(select(Book).where(Book.id == book_id))).scalar_one_or_none()
        if not book or not book.cover_path:
            return

        cover_path = Path(book.cover_path)
        if not cover_path.exists():
            cover_path = Path(settings.covers_storage_path) / book.cover_path
            if not cover_path.exists():
                return

        thumbs_dir = Path(settings.thumbnails_storage_path)
        thumbs_dir.mkdir(parents=True, exist_ok=True)

        with Image.open(cover_path) as img:
            for variant, (w, h) in THUMBNAIL_SIZES.items():
                thumb = img.copy()
                thumb.thumbnail((w, h), Image.LANCZOS)

                out_filename = f"{book_id}_{variant}.webp"
                out_path = thumbs_dir / out_filename
                thumb.save(out_path, "WEBP", quality=85)

                existing = (await db.execute(
                    select(Thumbnail).where(
                        Thumbnail.book_id == book_id,
                        Thumbnail.size_variant == variant,
                    )
                )).scalar_one_or_none()

                if existing:
                    existing.file_path = str(out_path)
                    existing.width = thumb.width
                    existing.height = thumb.height
                else:
                    db.add(Thumbnail(
                        book_id=book_id,
                        size_variant=variant,
                        file_path=str(out_path),
                        width=thumb.width,
                        height=thumb.height,
                    ))

            await db.commit()


async def generate_all_missing_thumbnails(ctx: dict) -> None:
    db_session: async_sessionmaker = ctx["db_session"]

    async with db_session() as db:
        q = (
            select(Book.id)
            .where(Book.is_available == True, Book.cover_path.isnot(None))
            .outerjoin(Thumbnail, Book.id == Thumbnail.book_id)
            .where(Thumbnail.id.is_(None))
            .limit(100)
        )
        book_ids = (await db.execute(q)).scalars().all()

    for book_id in book_ids:
        await generate_thumbnails(ctx, str(book_id))
