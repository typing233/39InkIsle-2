from arq import cron
from arq.connections import RedisSettings
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.config import get_settings
from app.importer.tasks import process_import_task, scan_import_folder
from app.tasks.thumbnails import generate_thumbnails, generate_all_missing_thumbnails
from app.tasks.cache_cleanup import cleanup_expired_metadata_cache, cleanup_orphaned_covers, cleanup_dead_sessions


async def startup(ctx: dict) -> None:
    settings = get_settings()
    engine = create_async_engine(settings.database_url, pool_size=5, max_overflow=5)
    ctx["db_session"] = async_sessionmaker(engine, expire_on_commit=False)


async def shutdown(ctx: dict) -> None:
    pass


class WorkerSettings:
    functions = [
        process_import_task,
        scan_import_folder,
        generate_thumbnails,
        generate_all_missing_thumbnails,
        cleanup_expired_metadata_cache,
        cleanup_orphaned_covers,
        cleanup_dead_sessions,
    ]

    cron_jobs = [
        cron(cleanup_expired_metadata_cache, hour=3, minute=0),
        cron(cleanup_orphaned_covers, hour=4, minute=0),
        cron(generate_all_missing_thumbnails, hour=2, minute=0),
        cron(cleanup_dead_sessions, hour=5, minute=0),
    ]

    on_startup = startup
    on_shutdown = shutdown

    @staticmethod
    def redis_settings() -> RedisSettings:
        settings = get_settings()
        return RedisSettings.from_dsn(settings.redis_url)

    max_jobs = 10
    job_timeout = 600
