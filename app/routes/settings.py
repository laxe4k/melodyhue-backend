from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..utils.database import get_db
from ..utils.auth_dep import get_current_user_id
from ..models.user import UserSetting, User

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
def get_settings(
    uid: str = Depends(get_current_user_id), db: Session = Depends(get_db)
):
    s = _get_or_create(db, uid)
    u = db.query(User).filter(User.id == uid).first()
    # Déterminer la couleur par défaut des overlays
    # Préférence: s.default_color_overlays, sinon héritage legacy depuis User.default_color_hex
    color_default = (
        getattr(s, "default_color_overlays", None)
        or getattr(u, "default_color_hex", None)
        or "#25d865"
    )
    return {
        "theme": s.theme,
        "layout": s.layout,
        # Renvoi conservant le nom historique pour compatibilité API
        "default_color_hex": color_default,
        # Nouveau nom explicite
        "default_color_overlays": color_default,
        "avatar_mode": getattr(s, "avatar_mode", "gravatar"),
        "avatar_color": getattr(s, "avatar_color", "#25d865"),
    }


@router.patch("/me")
def update_settings(
    payload: dict,
    uid: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    s = _get_or_create(db, uid)
    # Mettre à jour préférences non liées à la couleur
    for key in ["theme", "layout", "avatar_mode", "avatar_color"]:
        if key in payload and isinstance(payload[key], str):
            setattr(s, key, payload[key])
    # Gérer la couleur par défaut des overlays: nouvelle source -> UserSetting.default_color_overlays
    u = db.query(User).filter(User.id == uid).first()
    new_color = None
    # Noms acceptés: nouveau "default_color_overlays", compat "default_color_hex" et "default_overlay_color"
    for k in ("default_color_overlays", "default_color_hex", "default_overlay_color"):
        if isinstance(payload.get(k), str):
            new_color = payload[k]
            break
    if new_color:
        setattr(s, "default_color_overlays", new_color)
        # Optionnel: mettre à jour aussi l'ancien champ s'il existait côté User pour compat extraction Spotify
        if u is not None:
            try:
                u.default_color_hex = new_color
                db.add(u)
            except Exception:
                pass
    db.add(s)
    db.commit()
    db.refresh(s)
    if u:
        db.refresh(u)
    color_default = (
        getattr(s, "default_color_overlays", None)
        or getattr(u, "default_color_hex", None)
        or "#25d865"
    )
    return {
        "theme": s.theme,
        "layout": s.layout,
        "default_color_hex": color_default,
        "default_color_overlays": color_default,
        "avatar_mode": getattr(s, "avatar_mode", "gravatar"),
        "avatar_color": getattr(s, "avatar_color", "#25d865"),
    }
