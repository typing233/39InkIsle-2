from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.auth import schemas, service
from app.auth.dependencies import get_current_user
from app.users.models import User
from uuid import UUID

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=schemas.UserResponse, status_code=201)
async def register(data: schemas.UserRegister, db: AsyncSession = Depends(get_db)):
    user = await service.register_user(db, data)
    return user


@router.post("/login", response_model=schemas.TokenResponse)
async def login(data: schemas.UserLogin, request: Request, db: AsyncSession = Depends(get_db)):
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    return await service.login_user(db, data, ip_address=ip, user_agent=ua)


@router.post("/refresh", response_model=schemas.TokenResponse)
async def refresh(data: schemas.RefreshRequest, db: AsyncSession = Depends(get_db)):
    return await service.refresh_access_token(db, data.refresh_token)


@router.post("/logout", status_code=204)
async def logout(
    session_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await service.revoke_session(db, session_id, user.id)


@router.get("/sessions", response_model=list[schemas.SessionResponse])
async def list_sessions(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sessions = await service.get_user_sessions(db, user.id)
    return sessions


@router.delete("/sessions/{session_id}", status_code=204)
async def revoke_session(
    session_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await service.revoke_session(db, session_id, user.id)
