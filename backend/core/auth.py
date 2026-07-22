"""Authentication service - JWT + password hashing"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

from backend.core.config import get_config


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        salt.encode(),
        100000,
    )
    return f"{salt}${key.hex()}"


def verify_password(password: str, hashed: str) -> bool:
    try:
        salt, key_hex = hashed.split("$", 1)
        key = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode(),
            salt.encode(),
            100000,
        )
        return key.hex() == key_hex
    except Exception:
        return False


def create_access_token(
    data: Dict[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    from jose import jwt

    config = get_config()
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=config.security.access_token_expire_minutes
        )

    to_encode.update({"exp": expire})
    return jwt.encode(
        to_encode, config.security.secret_key, algorithm=config.security.algorithm
    )


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    from jose import jwt, JWTError

    config = get_config()
    try:
        payload = jwt.decode(
            token,
            config.security.secret_key,
            algorithms=[config.security.algorithm],
        )
        return payload
    except JWTError:
        return None


def generate_api_key() -> tuple[str, str, str]:
    config = get_config()
    raw_key = secrets.token_urlsafe(32)
    key_with_prefix = f"{config.security.api_key_prefix}{raw_key}"
    key_hash = hashlib.sha256(key_with_prefix.encode()).hexdigest()
    return raw_key, key_with_prefix, key_hash


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


def authenticate_user(db, email: str, password: str):
    from backend.db.models import User

    user = db.query(User).filter(User.email == email).first()
    if user and verify_password(password, user.hashed_password):
        return user
    return None


def create_user(db, email: str, name: str, password: str):
    from backend.db.models import User

    existing = db.query(User).filter(User.email == email).first()
    if existing:
        return None

    user = User(
        email=email,
        name=name,
        hashed_password=hash_password(password),
        role="member",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
