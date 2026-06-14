from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy import select, delete
from app.enrichment.models import MetadataCache, DeadLetterTask, Thumbnail
from app.users.models import Session
from app.books.models import Book
from pathlib import Path
from app.config import get_settings


async def cleanup_expired_metadata_cache(ctx: dict) -> int:
    db_session: async_sessionmaker = ctx["db_session"]
    async with db_session() as db:
        result = await db.execute(
            delete(MetadataCache).where(MetadataCache.expires_at < datetime.now(timezone.utc))
        )
        await db.commit()
        return result.rowcount or 0


async def cleanup_orphaned_covers(ctx: dict) -> int:
    settings = get_settings()
    covers_dir = Path(settings.covers_storage_path)
    if not covers_dir.exists():
        return 0

    db_session: async_sessionmaker = ctx["db_session"]
    async with db_session() as db:
        result = await db.execute(select(Book.cover_path).where(Book.cover_path.isnot(None)))
        known_paths = {row[0] for row in result.all()}

    removed = 0
    for file in covers_dir.iterdir():
        if file.is_file() and str(file) not in known_paths and file.name not in {p.split("/")[-1] for p in known_paths if p}:
            file.unlink()
            removed += 1

    return removed


async def cleanup_dead_sessions(ctx: dict) -> int:
    db_session: async_sessionmaker = ctx["db_session"]
    async with db_session() as db:
        from datetime import timedelta
        cutoff = datetime.now(timezone.utc) - timedelta(days=37)
        result = await db.execute(
            delete(Session).where(Session.created_at < cutoff)
        )
        await db.commit()
        return result.rowcount or 0
