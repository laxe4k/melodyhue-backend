from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from ..utils.database import get_db
from ..utils.auth_dep import require_moderator_or_admin
from ..models.user import User, UserWarning, UserBan, Overlay
from ..schemas.admin import UserListOut, UserListItem, WarnUserIn, BanUserIn
from ..schemas.overlay import OverlayUpdateIn, OverlayOut, OverlayModerationOut

router = APIRouter()


# Users moderation
@router.get("/users", response_model=UserListOut)
def list_users(
    _: User = Depends(require_moderator_or_admin),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = None,
):
    q = db.query(User)
    if search:
        like = f"%{search}%"
        q = q.filter(or_(User.username.like(like), User.email.like(like)))
    total = q.count()
    items = (
        q.order_by(User.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return UserListOut(
        items=[UserListItem.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/users/{user_id}", response_model=UserListItem)
def view_user(
    user_id: str,
    _: User = Depends(require_moderator_or_admin),
    db: Session = Depends(get_db),
):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    return UserListItem.model_validate(u)


@router.patch("/users/{user_id}")
def edit_user(
    user_id: str,
    payload: dict,
    _: User = Depends(require_moderator_or_admin),
    db: Session = Depends(get_db),
):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    # Allow editing username and email only here
    if "username" in payload and isinstance(payload["username"], str):
        u.username = payload["username"]
    if "email" in payload and isinstance(payload["email"], str):
        # Ensure email uniqueness
        exists = (
            db.query(User)
            .filter(User.email == payload["email"], User.id != user_id)
            .first()
        )
        if exists:
            raise HTTPException(status_code=409, detail="Email déjà utilisé")
        u.email = payload["email"]
    db.add(u)
    db.commit()
    return {"status": "ok"}


@router.post("/users/{user_id}/warn")
def warn_user(
    user_id: str,
    body: WarnUserIn,
    moderator: User = Depends(require_moderator_or_admin),
    db: Session = Depends(get_db),
):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    warn = UserWarning(user_id=u.id, moderator_id=moderator.id, reason=body.reason)
    db.add(warn)
    db.commit()
    return {"status": "ok", "warning_id": warn.id}


@router.post("/users/{user_id}/ban")
def ban_user(
    user_id: str,
    body: BanUserIn,
    moderator: User = Depends(require_moderator_or_admin),
    db: Session = Depends(get_db),
):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    # Optional: check if already banned and not revoked
    active_ban = (
        db.query(UserBan)
        .filter(UserBan.user_id == user_id, UserBan.revoked_at.is_(None))
        .order_by(UserBan.created_at.desc())
        .first()
    )
    if active_ban and (
        active_ban.until is None or active_ban.until > datetime.utcnow()
    ):
        # keep multiple bans allowed, or reject; let's reject to keep simple
        raise HTTPException(status_code=400, detail="Utilisateur déjà banni")
    ban = UserBan(
        user_id=u.id, moderator_id=moderator.id, reason=body.reason, until=body.until
    )
    db.add(ban)
    db.commit()
    return {"status": "ok", "ban_id": ban.id}


@router.post("/users/{user_id}/ban/revoke")
def revoke_ban(
    user_id: str,
    _: User = Depends(require_moderator_or_admin),
    db: Session = Depends(get_db),
):
    ban = (
        db.query(UserBan)
        .filter(UserBan.user_id == user_id, UserBan.revoked_at.is_(None))
        .order_by(UserBan.created_at.desc())
        .first()
    )
    if not ban:
        raise HTTPException(status_code=404, detail="Aucun bannissement actif")
    ban.revoked_at = datetime.utcnow()
    db.add(ban)
    db.commit()
    return {"status": "ok"}


# Overlays moderation (view/edit/delete any overlay)
@router.get("/overlays")
def list_all_overlays(
    _: User = Depends(require_moderator_or_admin),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = None,
):
    # Join with User to allow searching by username as well
    q = db.query(Overlay).join(User, Overlay.owner_id == User.id)
    if search:
        like = f"%{search}%"
        q = q.filter(
            or_(
                Overlay.name.like(like),
                Overlay.template.like(like),
                Overlay.id.like(like),
                Overlay.owner_id.like(like),
                User.username.like(like),
            )
        )
    total = q.count()
    items = (
        q.order_by(Overlay.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "items": [
            OverlayModerationOut(
                id=o.id,
                owner_id=o.owner_id,
                owner_username=getattr(o.owner, "username", None),
                name=o.name,
                template=o.template,
                created_at=o.created_at,
                updated_at=o.updated_at,
            )
            for o in items
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/overlays/{overlay_id}", response_model=OverlayModerationOut)
def get_overlay(
    overlay_id: str,
    _: User = Depends(require_moderator_or_admin),
    db: Session = Depends(get_db),
):
    o = db.query(Overlay).filter(Overlay.id == overlay_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="Overlay introuvable")
    return OverlayModerationOut(
        id=o.id,
        owner_id=o.owner_id,
        owner_username=getattr(o.owner, "username", None),
        name=o.name,
        template=o.template,
        created_at=o.created_at,
        updated_at=o.updated_at,
    )


@router.patch("/overlays/{overlay_id}", response_model=OverlayOut)
def edit_overlay(
    overlay_id: str,
    body: OverlayUpdateIn,
    _: User = Depends(require_moderator_or_admin),
    db: Session = Depends(get_db),
):
    o = db.query(Overlay).filter(Overlay.id == overlay_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="Overlay introuvable")
    if body.name is not None:
        o.name = body.name
    if body.template is not None:
        o.template = body.template
    db.add(o)
    db.commit()
    db.refresh(o)
    return o


@router.delete("/overlays/{overlay_id}")
def delete_overlay(
    overlay_id: str,
    _: User = Depends(require_moderator_or_admin),
    db: Session = Depends(get_db),
):
    o = db.query(Overlay).filter(Overlay.id == overlay_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="Overlay introuvable")
    db.delete(o)
    db.commit()
    return {"status": "ok"}
