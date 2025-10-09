from fastapi import APIRouter, Depends, HTTPException
from typing import List
from sqlalchemy.orm import Session
from ..utils.database import get_db
from ..utils.auth_dep import get_current_user_id
from ..models.user import User, Overlay
from ..schemas.overlay import OverlayCreateIn, OverlayUpdateIn, OverlayOut

router = APIRouter()


"""
All routes use HTTP Bearer dependency from utils.auth_dep to get current user id.
"""


@router.get("/", response_model=List[OverlayOut])
def list_overlays(
    uid: str = Depends(get_current_user_id), db: Session = Depends(get_db)
):
    items = db.query(Overlay).filter(Overlay.owner_id == uid).all()
    return items


@router.post("/", response_model=OverlayOut)
def create_overlay(
    body: OverlayCreateIn,
    uid: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    owner = db.query(User).filter(User.id == uid).first()
    if not owner:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    # Couleur: si non fournie, on hérite de la préférence utilisateur
    # Priorité: settings.default_overlay_color > valeur par défaut
    from ..models.user import UserSetting  # import local pour éviter cycles

    settings_row = db.query(UserSetting).filter(UserSetting.user_id == uid).first()
    pref_color = (
        getattr(settings_row, "default_overlay_color", None) if settings_row else None
    )
    color = body.color_hex or pref_color or "#25d865"
    ov = Overlay(owner_id=uid, name=body.name, color_hex=color)
    db.add(ov)
    db.commit()
    db.refresh(ov)
    return ov


@router.get("/{overlay_id}", response_model=OverlayOut)
def get_overlay(
    overlay_id: str,
    uid: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    ov = (
        db.query(Overlay)
        .filter(Overlay.id == overlay_id, Overlay.owner_id == uid)
        .first()
    )
    if not ov:
        raise HTTPException(status_code=404, detail="Overlay introuvable")
    return ov


@router.patch("/{overlay_id}", response_model=OverlayOut)
def update_overlay(
    overlay_id: str,
    body: OverlayUpdateIn,
    uid: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    ov = (
        db.query(Overlay)
        .filter(Overlay.id == overlay_id, Overlay.owner_id == uid)
        .first()
    )
    if not ov:
        raise HTTPException(status_code=404, detail="Overlay introuvable")
    if body.name is not None:
        ov.name = body.name
    if body.color_hex is not None:
        ov.color_hex = body.color_hex
    db.add(ov)
    db.commit()
    db.refresh(ov)
    return ov


@router.post("/{overlay_id}/duplicate", response_model=OverlayOut)
def duplicate_overlay(
    overlay_id: str,
    uid: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    ov = (
        db.query(Overlay)
        .filter(Overlay.id == overlay_id, Overlay.owner_id == uid)
        .first()
    )
    if not ov:
        raise HTTPException(status_code=404, detail="Overlay introuvable")
    dup = Overlay(owner_id=uid, name=f"{ov.name} (copy)", color_hex=ov.color_hex)
    db.add(dup)
    db.commit()
    db.refresh(dup)
    return dup


@router.delete("/{overlay_id}")
def delete_overlay(
    overlay_id: str,
    uid: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    ov = (
        db.query(Overlay)
        .filter(Overlay.id == overlay_id, Overlay.owner_id == uid)
        .first()
    )
    if not ov:
        raise HTTPException(status_code=404, detail="Overlay introuvable")
    db.delete(ov)
    db.commit()
    return {"status": "ok"}
