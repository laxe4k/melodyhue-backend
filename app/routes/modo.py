from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from ..utils.database import get_db
from ..utils.auth_dep import require_moderator_or_admin
from ..models.user import User, UserWarning, UserBan, UserSession, Overlay
from ..schemas.admin import (
    UserListItem,  # conservé pour compat éventuelle
    WarnUserIn,
    BanUserIn,
    ModerationUserListOut,
    ModerationUserListItem,
)
from ..schemas.overlay import OverlayUpdateIn, OverlayOut, OverlayModerationOut
from ..services.realtime import get_manager

router = APIRouter()


# Users moderation
@router.get("/users", response_model=ModerationUserListOut)
def list_users(
    _: User = Depends(require_moderator_or_admin),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = None,
    banned: bool | None = None,
):
    q = db.query(User)
    if search:
        like = f"%{search}%"
        q = q.filter(or_(User.username.like(like), User.email.like(like)))
    # Filtre pour n'afficher que les utilisateurs bannis si demandé
    if banned is True:
        from sqlalchemy.orm import aliased

        UB = aliased(UserBan)
        now = datetime.utcnow()
        q = q.join(
            UB,
            and_(
                UB.user_id == User.id,
                UB.revoked_at.is_(None),
                or_(UB.until.is_(None), UB.until > now),
            ),
        ).distinct(User.id)
    total = q.count()
    items = (
        q.order_by(User.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    # Récupérer les bans actifs pour les utilisateurs listés
    ids = [u.id for u in items]
    active_bans: dict[str, UserBan] = {}
    if ids:
        now = datetime.utcnow()
        bans = (
            db.query(UserBan)
            .filter(
                UserBan.user_id.in_(ids),
                UserBan.revoked_at.is_(None),
                or_(UserBan.until.is_(None), UserBan.until > now),
            )
            .order_by(UserBan.created_at.desc())
            .all()
        )
        for b in bans:
            if b.user_id not in active_bans:
                active_bans[b.user_id] = b
    return ModerationUserListOut(
        items=[
            ModerationUserListItem(
                id=u.id,
                username=u.username,
                email=u.email,
                role=u.role,
                created_at=u.created_at,
                last_login_at=u.last_login_at,
                is_banned=(u.id in active_bans),
                ban_reason=(active_bans[u.id].reason if u.id in active_bans else None),
                ban_until=(active_bans[u.id].until if u.id in active_bans else None),
            )
            for u in items
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/users/{user_id}", response_model=ModerationUserListItem)
def view_user(
    user_id: str,
    _: User = Depends(require_moderator_or_admin),
    db: Session = Depends(get_db),
):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    # Chercher ban actif
    now = datetime.utcnow()
    b = (
        db.query(UserBan)
        .filter(
            UserBan.user_id == user_id,
            UserBan.revoked_at.is_(None),
            or_(UserBan.until.is_(None), UserBan.until > now),
        )
        .order_by(UserBan.created_at.desc())
        .first()
    )
    return ModerationUserListItem(
        id=u.id,
        username=u.username,
        email=u.email,
        role=u.role,
        created_at=u.created_at,
        last_login_at=u.last_login_at,
        is_banned=bool(b),
        ban_reason=(b.reason if b else None),
        ban_until=(b.until if b else None),
    )


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
    bg: BackgroundTasks,
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
    # Révoquer toutes les sessions (refresh tokens) de l'utilisateur pour forcer la déconnexion
    revoked = db.query(UserSession).filter(UserSession.user_id == u.id).delete()
    db.commit()
    # Notifier en temps réel (si connecté via /ws): force logout immédiat
    try:
        manager = get_manager()
        # 1) Envoyer un message explicite au client pour déclencher la déconnexion UI
        bg.add_task(
            manager.send_to_user, u.id, {"type": "force_logout", "reason": "banned"}
        )
        # 2) Fermer toutes les connexions WS pour couper net (le front gère le code 4401)
        bg.add_task(manager.close_user, u.id, 4401, "banned")
    except Exception:
        pass
    return {"status": "ok", "ban_id": ban.id, "revoked_sessions": int(revoked)}


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
    return {"status": "ok", "revoked_at": ban.revoked_at}


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
