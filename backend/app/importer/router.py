from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.auth.dependencies import require_admin
from app.users.models import User
from app.importer import schemas, service
from uuid import UUID

router = APIRouter(prefix="/import", tags=["import"])


@router.get("/folders", response_model=list[schemas.ImportFolderResponse])
async def list_folders(
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await service.get_folders(db)


@router.post("/folders", response_model=schemas.ImportFolderResponse, status_code=201)
async def create_folder(
    data: schemas.ImportFolderCreate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await service.create_folder(db, data, admin.id)


@router.patch("/folders/{folder_id}", response_model=schemas.ImportFolderResponse)
async def update_folder(
    folder_id: UUID,
    data: schemas.ImportFolderUpdate,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await service.update_folder(db, folder_id, data)


@router.delete("/folders/{folder_id}", status_code=204)
async def delete_folder(
    folder_id: UUID,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    await service.delete_folder(db, folder_id)


@router.post("/folders/{folder_id}/scan", status_code=202)
async def trigger_scan(
    folder_id: UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    await service.trigger_scan(db, folder_id, operator_id=admin.id)
    return {"message": "Scan queued"}


@router.get("/tasks", response_model=list[schemas.ImportTaskResponse])
async def list_tasks(
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    tasks, _ = await service.get_tasks(db, status, page, page_size)
    return tasks


@router.post("/tasks/{task_id}/retry", status_code=202)
async def retry_task(
    task_id: UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    await service.retry_task(db, task_id, operator_id=admin.id)
    return {"message": "Task re-queued"}


@router.get("/stats", response_model=schemas.ImportStats)
async def get_stats(
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await service.get_stats(db)
