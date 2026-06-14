from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone
from app.users.models import User, Session
from app.core.security import hash_password, verify_password
from app.core.exceptions import ConflictError, UnauthorizedError
from app.auth.jwt import create_access_token, create_refresh_token, decode_token
from app.auth.schemas import UserRegister, UserLogin, TokenResponse
from app.admin.service import log_action
import uuid


async def register_user(db: AsyncSession, data: UserRegister) -> User:
    existing = await db.execute(
        select(User).where((User.username == data.username) | (User.email == data.email))
    )
    if existing.scalar_one_or_none():
        raise ConflictError("Username or email already exists")

    user = User(
        username=data.username,
        email=data.email,
        password_hash=hash_password(data.password),
    )
    db.add(user)
    await db.flush()
    return user


async def login_user(
    db: AsyncSession, data: UserLogin, ip_address: str | None = None, user_agent: str | None = None
) -> TokenResponse:
    result = await db.execute(select(User).where(User.username == data.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(data.password, user.password_hash):
        raise UnauthorizedError("Invalid credentials")
    if not user.is_active:
        raise UnauthorizedError("Account is disabled")

    access_token, access_jti = create_access_token(str(user.id))
    refresh_token, refresh_jti, expires_at = create_refresh_token(str(user.id))

    session = Session(
        user_id=user.id,
        token_jti=refresh_jti,
        device_name=data.device_name,
        ip_address=ip_address,
        user_agent=user_agent,
        expires_at=expires_at,
    )
    db.add(session)
    await db.flush()

    await log_action(
        db, user.id, "user.login",
        resource_type="session", resource_id=session.id,
        details={"device": data.device_name, "ip": ip_address},
        ip_address=ip_address,
    )

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


async def refresh_access_token(db: AsyncSession, refresh_token: str) -> TokenResponse:
    payload = decode_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise UnauthorizedError("Invalid refresh token")

    jti = payload["jti"]
    user_id = payload["sub"]

    result = await db.execute(
        select(Session).where(Session.token_jti == jti, Session.is_revoked == False)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise UnauthorizedError("Session revoked or expired")

    session.last_active_at = datetime.now(timezone.utc)
    new_access_token, _ = create_access_token(user_id)

    return TokenResponse(access_token=new_access_token, refresh_token=refresh_token)


async def revoke_session(db: AsyncSession, session_id: uuid.UUID, user_id: uuid.UUID) -> None:
    result = await db.execute(
        select(Session).where(Session.id == session_id, Session.user_id == user_id)
    )
    session = result.scalar_one_or_none()
    if session:
        session.is_revoked = True


async def get_user_sessions(db: AsyncSession, user_id: uuid.UUID) -> list[Session]:
    result = await db.execute(
        select(Session).where(
            Session.user_id == user_id,
            Session.is_revoked == False,
        ).order_by(Session.last_active_at.desc())
    )
    return list(result.scalars().all())


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()
