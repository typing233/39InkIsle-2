from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.users.models import User
from app.core.exceptions import NotFoundError
from app.admin.service import log_action
import uuid


async def get_all_users(
    db: AsyncSession, page: int = 1, page_size: int = 20
) -> tuple[list[User], int]:
    total_result = await db.execute(select(func.count(User.id)))
    total = total_result.scalar_one()

    offset = (page - 1) * page_size
    result = await db.execute(
        select(User).order_by(User.created_at.desc()).offset(offset).limit(page_size)
    )
    users = list(result.scalars().all())
    return users, total


async def update_user_role(
    db: AsyncSession, user_id: uuid.UUID, role: str, operator_id: uuid.UUID
) -> User:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundError("User not found")
    old_role = user.role
    user.role = role
    await db.flush()

    await log_action(
        db, operator_id, "user.role_change",
        resource_type="user", resource_id=user_id,
        details={"old_role": old_role, "new_role": role, "target_user": user.username},
    )
    return user


async def deactivate_user(
    db: AsyncSession, user_id: uuid.UUID, operator_id: uuid.UUID
) -> None:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundError("User not found")
    user.is_active = False
    await db.flush()

    await log_action(
        db, operator_id, "user.deactivate",
        resource_type="user", resource_id=user_id,
        details={"username": user.username},
    )
