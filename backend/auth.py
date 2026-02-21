"""Simple auth: single shared password, JWT for session."""
import os
from datetime import datetime, timedelta
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

# Env: REVIEW_APP_PASSWORD (required); JWT_SECRET (optional)
REVIEW_APP_PASSWORD = os.environ.get("REVIEW_APP_PASSWORD", "")
JWT_SECRET = os.environ.get("JWT_SECRET", REVIEW_APP_PASSWORD or "change-me-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24 * 7  # 1 week

security = HTTPBearer(auto_error=False)


def _get_secret_key() -> str:
    if not JWT_SECRET or JWT_SECRET == "change-me-in-production":
        return "dev-secret-key-change-in-production"
    return JWT_SECRET


def verify_password(plain: str) -> bool:
    """Check plain password against REVIEW_APP_PASSWORD."""
    if not REVIEW_APP_PASSWORD:
        return False
    return plain == REVIEW_APP_PASSWORD


def create_access_token() -> str:
    return jwt.encode(
        {"sub": "user", "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRE_HOURS)},
        _get_secret_key(),
        algorithm=JWT_ALGORITHM,
    )


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, _get_secret_key(), algorithms=[JWT_ALGORITHM])
    except JWTError:
        return None


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> dict:
    if not credentials or credentials.scheme != "Bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload
