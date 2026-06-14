from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.users.models import User
from app.core.security import verify_password
from app.auth.dependencies import get_current_user
import secrets

http_basic = HTTPBasic(auto_error=False)


async def get_opds_user(
    credentials: HTTPBasicCredentials | None = Depends(http_basic),
    db: AsyncSession = Depends(get_db),
) -> User:
    if credentials:
        result = await db.execute(
            select(User).where(User.username == credentials.username, User.is_active == True)
        )
        user = result.scalar_one_or_none()
        if user and verify_password(credentials.password, user.password_hash):
            return user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials",
        headers={"WWW-Authenticate": "Basic realm=\"InkIsle OPDS\""},
    )
