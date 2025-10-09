try:
    # Reuse existing symmetric crypto (Fernet) from Flask app if available
    from app.security.crypto import encrypt_str, decrypt_str  # type: ignore
except Exception:  # pragma: no cover - fallback Fernet-based crypto
    import os
    import base64
    import hashlib
    from typing import Optional
    from cryptography.fernet import Fernet, InvalidToken

    _fernet: Optional[Fernet] = None

    def _get_fernet() -> Optional[Fernet]:
        global _fernet
        if _fernet is not None:
            return _fernet
        # Prefer a dedicated ENCRYPTION_KEY; else derive from JWT_SECRET or SECRET_KEY
        key_env = (
            os.getenv("ENCRYPTION_KEY")
            or os.getenv("JWT_SECRET")
            or os.getenv("SECRET_KEY")
        )
        if not key_env:
            return None
        try:
            # Accept raw Fernet key (base64 urlsafe 32 bytes)
            if len(key_env) >= 43:  # typical length of Fernet key
                _fernet = Fernet(key_env.encode("utf-8"))
                return _fernet
            # Derive a Fernet key from provided secret using SHA-256
            digest = hashlib.sha256(key_env.encode("utf-8")).digest()
            fkey = base64.urlsafe_b64encode(digest)
            _fernet = Fernet(fkey)
            return _fernet
        except Exception:
            return None

    def encrypt_str(v: str | None) -> str | None:  # type: ignore
        if v is None:
            return None
        s = str(v)
        f = _get_fernet()
        if not f:
            # As a last resort, return original (not ideal but avoids data loss)
            return s
        try:
            return f.encrypt(s.encode("utf-8")).decode("utf-8")
        except Exception:
            return s

    def decrypt_str(v: str | None) -> str | None:  # type: ignore
        if v is None:
            return None
        s = str(v)
        f = _get_fernet()
        if not f:
            return s
        try:
            return f.decrypt(s.encode("utf-8")).decode("utf-8")
        except InvalidToken:
            # Not encrypted or different scheme: return as-is
            return s
        except Exception:
            return s
