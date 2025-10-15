from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from .security import decode_token
from .database import get_db
from ..models.user import User, UserBan
from datetime import datetime


# Allow absence of Authorization header; we'll fallback to cookies
bearer_scheme = HTTPBearer(auto_error=False)


def get_current_payload(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict:
    # Prefer Authorization header; fallback to HttpOnly cookies
    token = creds.credentials if creds else request.cookies.get("mh_access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Invalid token")
    try:
        return decode_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")


def get_current_user_id(payload: dict = Depends(get_current_payload)) -> str:
    sub = payload.get("sub")
    if not isinstance(sub, str) or not sub:
        raise HTTPException(status_code=401, detail="Invalid token")
    return sub


def get_current_user(
    payload: dict = Depends(get_current_payload), db: Session = Depends(get_db)
) -> User:
    sub = payload.get("sub")
    if not isinstance(sub, str) or not sub:
        raise HTTPException(status_code=401, detail="Invalid token")
    u = db.query(User).filter(User.id == sub).first()
    if not u:
        raise HTTPException(status_code=401, detail="Invalid token")
    # Bloquer si banni (ban actif: until NULL ou > now, et non révoqué)
    now = datetime.utcnow()
    active_ban = (
        db.query(UserBan)
        .filter(
            UserBan.user_id == u.id,
            UserBan.revoked_at.is_(None),
            ((UserBan.until.is_(None)) | (UserBan.until > now)),
        )
        .order_by(UserBan.created_at.desc())
        .first()
    )
    if active_ban:
        raise HTTPException(status_code=403, detail="Banned")
    return u


def require_roles(*roles: str):
    """Dependency factory: returns the current user only if their role is in roles.
    Raises 403 otherwise.
    """

    def _dep(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Forbidden")
        return user

    return _dep


# Shortcuts
def require_admin(user: User = Depends(require_roles("admin"))) -> User:  # type: ignore
    return user


def require_moderator_or_admin(
    user: User = Depends(require_roles("moderator", "admin")),  # type: ignore
) -> User:
    return user
