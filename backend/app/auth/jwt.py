from jose import jwt, JWTError
from datetime import datetime, timedelta, timezone
from app.config import get_settings
import uuid

settings = get_settings()

ALGORITHM = "HS256"


def create_access_token(user_id: str, jti: str | None = None) -> tuple[str, str]:
    jti = jti or str(uuid.uuid4())
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    payload = {
        "sub": user_id,
        "jti": jti,
        "type": "access",
        "exp": expires,
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)
    return token, jti


def create_refresh_token(user_id: str, jti: str | None = None) -> tuple[str, str, datetime]:
    jti = jti or str(uuid.uuid4())
    expires = datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_token_expire_days)
    payload = {
        "sub": user_id,
        "jti": jti,
        "type": "refresh",
        "exp": expires,
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)
    return token, jti, expires


def decode_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
