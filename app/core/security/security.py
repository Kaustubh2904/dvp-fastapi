from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Union
import jwt
from pwdlib import PasswordHash
from app.core.config.settings import settings

# Initialize Argon2id password hasher through pwdlib
hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return hasher.verify(plain_password, hashed_password)
    except Exception:
        return False


def create_jwt_token(
    subject: Union[str, Any],
    expires_delta: timedelta,
    token_type: str = "access",
    additional_data: Optional[dict[str, Any]] = None,
) -> str:
    now = datetime.now(timezone.utc)
    expire = now + expires_delta
    to_encode = {
        "exp": expire,
        "iat": now,
        "sub": str(subject),
        "type": token_type,
    }
    if additional_data:
        to_encode.update(additional_data)
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_access_token(
    subject: Union[str, Any], additional_data: Optional[dict[str, Any]] = None
) -> str:
    expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return create_jwt_token(
        subject=subject,
        expires_delta=expires,
        token_type="access",
        additional_data=additional_data,
    )


def create_refresh_token(
    subject: Union[str, Any], additional_data: Optional[dict[str, Any]] = None
) -> str:
    expires = timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
    return create_jwt_token(
        subject=subject,
        expires_delta=expires,
        token_type="refresh",
        additional_data=additional_data,
    )


def decode_token(token: str) -> dict[str, Any]:
    try:
        decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return decoded
    except jwt.PyJWTError:
        return {}
