from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..utils.database import get_db
from ..utils.auth_dep import get_current_user_id
from ..models.user import UserSetting

router = APIRouter()


def _get_or_create(db: Session, uid: str) -> UserSetting:
    s = db.query(UserSetting).filter(UserSetting.user_id == uid).first()
    if not s:
        s = UserSetting(user_id=uid)
        db.add(s)
        db.commit()
        db.refresh(s)
    return s


@router.get("/me")
def get_settings(uid: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    s = _get_or_create(db, uid)
    return {
        "theme": s.theme,
        "layout": s.layout,
        "default_overlay_color": s.default_overlay_color,
        "avatar_mode": getattr(s, "avatar_mode", "gravatar"),
        "avatar_color": getattr(s, "avatar_color", "#25d865"),
    }


@router.patch("/me")
def update_settings(payload: dict, uid: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    s = _get_or_create(db, uid)
    for key in ["theme", "layout", "default_overlay_color", "avatar_mode", "avatar_color"]:
        if key in payload and isinstance(payload[key], str):
            setattr(s, key, payload[key])
    db.add(s)
    db.commit()
    db.refresh(s)
    return {
        "theme": s.theme,
        "layout": s.layout,
        "default_overlay_color": s.default_overlay_color,
        "avatar_mode": getattr(s, "avatar_mode", "gravatar"),
        "avatar_color": getattr(s, "avatar_color", "#25d865"),
    }
