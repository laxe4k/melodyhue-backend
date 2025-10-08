import os
import time
import hashlib
import pyotp
from typing import Optional, Tuple
from jose import jwt, JWTError
from argon2 import PasswordHasher, exceptions as argon_exc

JWT_SECRET = os.getenv("JWT_SECRET", os.getenv("SECRET_KEY", "change-me"))
JWT_ALG = os.getenv("JWT_ALG", "HS256")
ACCESS_TOKEN_EXPIRE_MIN = int(os.getenv("ACCESS_TOKEN_EXPIRE_MIN", "15"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))

password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return password_hasher.verify(password_hash, password)
    except argon_exc.VerifyMismatchError:
        return False
    except Exception:
        return False


def create_access_token(sub: str, extra: Optional[dict] = None) -> str:
    now = int(time.time())
    payload = {"sub": sub, "iat": now, "exp": now + ACCESS_TOKEN_EXPIRE_MIN * 60, "type": "access"}
    if extra:
        payload.update(extra)
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def create_refresh_token(sub: str, extra: Optional[dict] = None) -> str:
    now = int(time.time())
    payload = {"sub": sub, "iat": now, "exp": now + REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600, "type": "refresh"}
    if extra:
        payload.update(extra)
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def decode_token(token: str) -> dict:
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])


def is_refresh(token_payload: dict) -> bool:
    return token_payload.get("type") == "refresh"


def totp_generate_secret() -> str:
    return pyotp.random_base32()


def totp_current_code(secret: str) -> str:
    return pyotp.TOTP(secret).now()


def totp_verify(secret: str, code: str, valid_window: int = 1) -> bool:
    try:
        return pyotp.TOTP(secret).verify(code, valid_window=valid_window)
    except Exception:
        return False


def gravatar_url(email: str, size: int = 128) -> str:
    e = (email or "").strip().lower().encode("utf-8")
    h = hashlib.md5(e).hexdigest()
    return f"https://www.gravatar.com/avatar/{h}?s={size}&d=identicon"