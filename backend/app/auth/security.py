from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta, timezone
from typing import Optional
import hashlib
import secrets

from app.config import settings

# ─── Password Hashing ─────────────────────────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ─── Token Hashing (for storing refresh tokens safely) ───────────────────────
def hash_token(token: str) -> str:
    """SHA-256 hash a token before storing it in DB — never store raw tokens."""
    return hashlib.sha256(token.encode()).hexdigest()


def generate_refresh_token() -> str:
    """Generate a cryptographically secure random token."""
    return secrets.token_urlsafe(64)


# ─── JWT Access Token ─────────────────────────────────────────────────────────
def create_access_token(payload: dict, expires_in_minutes: Optional[int] = None) -> str:
    expire_minutes = expires_in_minutes or settings.access_token_expire_minutes
    expire = datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)

    data = payload.copy()
    data.update({"exp": expire, "type": "access"})

    return jwt.encode(data, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT access token. Raises JWTError on failure."""
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    if payload.get("type") != "access":
        raise JWTError("Not an access token")
    return payload
