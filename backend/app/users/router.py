from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.auth.dependencies import get_current_user, require_admin
from app.users.models import User
from app.users import schemas, service
from uuid import UUID

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=schemas.UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    return user


@router.patch("/me", response_model=schemas.UserResponse)
async def update_me(
    data: schemas.UserUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if data.email:
        user.email = data.email
    if data.username:
        user.username = data.username
    await db.flush()
    return user


@router.get("", response_model=list[schemas.UserResponse])
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    users, _ = await service.get_all_users(db, page, page_size)
    return users


@router.patch("/{user_id}/role", response_model=schemas.UserResponse)
async def update_role(
    user_id: UUID,
    data: schemas.RoleUpdate,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await service.update_user_role(db, user_id, data.role)


@router.delete("/{user_id}", status_code=204)
async def deactivate_user(
    user_id: UUID,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    await service.deactivate_user(db, user_id)
