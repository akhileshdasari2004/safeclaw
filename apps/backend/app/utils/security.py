"""Password hashing, JWT, encryption, license key generation."""

import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(subject: str, extra: dict[str, Any] | None = None) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_access_expire_minutes)
    payload = {"sub": subject, "exp": expire, "type": "access"}
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(subject: str) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_expire_days)
    payload = {"sub": subject, "exp": expire, "type": "refresh"}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as e:
        raise ValueError("Invalid token") from e


def generate_license_key() -> str:
    alphabet = string.ascii_uppercase + string.digits
    segments = ["".join(secrets.choice(alphabet) for _ in range(4)) for _ in range(4)]
    return f"SC-{'-'.join(segments)}"


def _get_fernet() -> Fernet:
    settings = get_settings()
    key = settings.encryption_key.encode()
    if len(key) == 44 and key.endswith(b"="):
        return Fernet(key)
    # Derive a valid Fernet key from arbitrary secret (dev convenience)
    import base64
    import hashlib

    derived = base64.urlsafe_b64encode(hashlib.sha256(key).digest())
    return Fernet(derived)


def encrypt_secret(plaintext: str) -> str:
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_secret(ciphertext: str) -> str:
    try:
        return _get_fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken as e:
        raise ValueError("Failed to decrypt secret") from e
