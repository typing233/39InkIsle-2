from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from arq import create_pool
from arq.connections import RedisSettings
from app.importer.models import ImportFolder, ImportTask
from app.importer.schemas import ImportFolderCreate, ImportFolderUpdate, ImportStats
from app.config import get_settings
from app.core.exceptions import NotFoundError
from app.admin.service import log_action
import uuid

settings = get_settings()


async def create_folder(db: AsyncSession, data: ImportFolderCreate, user_id: uuid.UUID) -> ImportFolder:
    folder = ImportFolder(path=data.path, scan_interval_seconds=data.scan_interval_seconds, created_by=user_id)
    db.add(folder)
    await db.flush()

    await log_action(
        db, user_id, "import.folder_create",
        resource_type="import_folder", resource_id=folder.id,
        details={"path": data.path},
    )
    return folder


async def get_folders(db: AsyncSession) -> list[ImportFolder]:
    result = await db.execute(select(ImportFolder).order_by(ImportFolder.created_at.desc()))
    return list(result.scalars().all())


async def update_folder(db: AsyncSession, folder_id: uuid.UUID, data: ImportFolderUpdate) -> ImportFolder:
    result = await db.execute(select(ImportFolder).where(ImportFolder.id == folder_id))
    folder = result.scalar_one_or_none()
    if not folder:
        raise NotFoundError("Folder not found")
    if data.is_active is not None:
        folder.is_active = data.is_active
    if data.scan_interval_seconds is not None:
        folder.scan_interval_seconds = data.scan_interval_seconds
    await db.flush()
    return folder


async def delete_folder(db: AsyncSession, folder_id: uuid.UUID) -> None:
    result = await db.execute(select(ImportFolder).where(ImportFolder.id == folder_id))
    folder = result.scalar_one_or_none()
    if not folder:
        raise NotFoundError("Folder not found")
    await db.delete(folder)


async def trigger_scan(db: AsyncSession, folder_id: uuid.UUID, operator_id: uuid.UUID) -> None:
    await log_action(
        db, operator_id, "import.scan_trigger",
        resource_type="import_folder", resource_id=folder_id,
    )
    redis = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    await redis.enqueue_job("scan_import_folder", str(folder_id))
    await redis.close()


async def get_tasks(
    db: AsyncSession, status: str | None = None, page: int = 1, page_size: int = 20
) -> tuple[list[ImportTask], int]:
    query = select(ImportTask)
    count_query = select(func.count(ImportTask.id))

    if status:
        query = query.where(ImportTask.status == status)
        count_query = count_query.where(ImportTask.status == status)

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    offset = (page - 1) * page_size
    result = await db.execute(query.order_by(ImportTask.created_at.desc()).offset(offset).limit(page_size))
    return list(result.scalars().all()), total


async def retry_task(db: AsyncSession, task_id: uuid.UUID, operator_id: uuid.UUID) -> None:
    await log_action(
        db, operator_id, "import.task_retry",
        resource_type="import_task", resource_id=task_id,
    )
    redis = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    await redis.enqueue_job("process_import_task", str(task_id))
    await redis.close()


async def get_stats(db: AsyncSession) -> ImportStats:
    total = (await db.execute(select(func.count(ImportTask.id)))).scalar_one()
    pending = (await db.execute(select(func.count(ImportTask.id)).where(ImportTask.status == "pending"))).scalar_one()
    processing = (await db.execute(select(func.count(ImportTask.id)).where(ImportTask.status == "processing"))).scalar_one()
    completed = (await db.execute(select(func.count(ImportTask.id)).where(ImportTask.status == "completed"))).scalar_one()
    failed = (await db.execute(select(func.count(ImportTask.id)).where(ImportTask.status == "failed"))).scalar_one()
    skipped = (await db.execute(select(func.count(ImportTask.id)).where(ImportTask.status == "skipped"))).scalar_one()

    return ImportStats(
        total_tasks=total, pending=pending, processing=processing,
        completed=completed, failed=failed, skipped=skipped,
    )
