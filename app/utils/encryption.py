try:
    # Reuse existing symmetric crypto (Fernet) from Flask app
    from app.security.crypto import encrypt_str, decrypt_str  # type: ignore
except Exception:  # pragma: no cover - fallback no-op in dev
    def encrypt_str(v: str | None) -> str | None:  # type: ignore
        return v

    def decrypt_str(v: str | None) -> str | None:  # type: ignore
        return v
