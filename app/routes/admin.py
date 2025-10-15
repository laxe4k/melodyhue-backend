from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, aliased
from sqlalchemy import func, or_
from ..utils.database import get_db
from ..utils.auth_dep import require_admin
from ..models.user import User, Overlay, TwoFA, UserWarning
from ..schemas.admin import (
    AdminStatsOut,
    RoleUpdateIn,
    UserListOut,
    UserListItem,
    UserWarningsOut,
    WarningItem,
)

router = APIRouter()


@router.get("/stats", response_model=AdminStatsOut)
def admin_stats(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    users_count = db.query(func.count(User.id)).scalar() or 0
    overlays_count = db.query(func.count(Overlay.id)).scalar() or 0
    moderators_count = (
        db.query(func.count(User.id)).filter(User.role == "moderator").scalar() or 0
    )
    admins_count = (
        db.query(func.count(User.id)).filter(User.role == "admin").scalar() or 0
    )
    active_2fa_count = (
        db.query(func.count(TwoFA.user_id))
        .filter(TwoFA.verified_at.is_not(None))
        .scalar()
        or 0
    )
    last_user = db.query(User).order_by(User.created_at.desc()).first()
    return AdminStatsOut(
        users_count=users_count,
        overlays_count=overlays_count,
        moderators_count=moderators_count,
        admins_count=admins_count,
        active_2fa_count=active_2fa_count,
        last_user_registered_at=last_user.created_at if last_user else None,
    )


@router.get("/users", response_model=UserListOut)
def admin_list_users(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = None,
):
    q = db.query(User)
    if search:
        like = f"%{search}%"
        q = q.filter((User.username.like(like)) | (User.email.like(like)))
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


@router.patch("/users/{user_id}/role")
def admin_update_role(
    user_id: str,
    body: RoleUpdateIn,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    u.role = body.role
    db.add(u)
    db.commit()
    return {"status": "ok", "user_id": u.id, "role": u.role}


@router.get("/users/{user_id}/warnings", response_model=UserWarningsOut)
def admin_list_user_warnings(
    user_id: str,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    # Vérifier que l'utilisateur existe
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    q = db.query(UserWarning).filter(UserWarning.user_id == user_id)
    total = q.count()
    warnings = (
        q.order_by(UserWarning.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    # Optionnel: enrichir avec le pseudo/email du modérateur et les infos user
    mod_by_id: dict[str, tuple[str | None, str | None]] = {}
    items: list[WarningItem] = []
    for w in warnings:
        mod_username = None
        mod_email = None
        mod_id = getattr(w, "moderator_id", None)
        if mod_id:
            if mod_id in mod_by_id:
                mod_username, mod_email = mod_by_id[mod_id]
            else:
                mod = (
                    db.query(User)
                    .with_entities(User.username, User.email)
                    .filter(User.id == mod_id)
                    .first()
                )
                if mod:
                    mod_username, mod_email = mod.username, mod.email
                mod_by_id[mod_id] = (mod_username, mod_email)
        items.append(
            WarningItem(
                id=w.id,
                user_id=w.user_id,
                user_username=(
                    getattr(w.user, "username", None) if hasattr(w, "user") else None
                ),
                user_email=(
                    getattr(w.user, "email", None) if hasattr(w, "user") else None
                ),
                moderator_id=mod_id,
                moderator_username=mod_username,
                moderator_email=mod_email,
                reason=getattr(w, "reason", None),
                created_at=getattr(w, "created_at", None),
            )
        )

    return UserWarningsOut(items=items, total=total, page=page, page_size=page_size)


@router.get("/warnings", response_model=UserWarningsOut)
def admin_list_all_warnings(
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = None,
):
    U = aliased(User)
    M = aliased(User)

    base_q = (
        db.query(
            UserWarning,
            U.username.label("user_username"),
            U.email.label("user_email"),
            M.username.label("moderator_username"),
            M.email.label("moderator_email"),
        )
        .outerjoin(U, UserWarning.user_id == U.id)
        .outerjoin(M, UserWarning.moderator_id == M.id)
    )

    if search:
        like = f"%{search}%"
        base_q = base_q.filter(
            or_(
                UserWarning.id.like(like),
                UserWarning.user_id.like(like),
                UserWarning.moderator_id.like(like),
                UserWarning.reason.like(like),
                U.username.like(like),
                U.email.like(like),
                M.username.like(like),
                M.email.like(like),
            )
        )

    # Total
    count_q = (
        db.query(func.count(UserWarning.id))
        .outerjoin(U, UserWarning.user_id == U.id)
        .outerjoin(M, UserWarning.moderator_id == M.id)
    )
    if search:
        like = f"%{search}%"
        count_q = count_q.filter(
            or_(
                UserWarning.id.like(like),
                UserWarning.user_id.like(like),
                UserWarning.moderator_id.like(like),
                UserWarning.reason.like(like),
                U.username.like(like),
                U.email.like(like),
                M.username.like(like),
                M.email.like(like),
            )
        )
    total = count_q.scalar() or 0

    rows = (
        base_q.order_by(UserWarning.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items: list[WarningItem] = []
    for w, user_username, user_email, moderator_username, moderator_email in rows:
        items.append(
            WarningItem(
                id=w.id,
                user_id=w.user_id,
                user_username=user_username,
                user_email=user_email,
                moderator_id=getattr(w, "moderator_id", None),
                moderator_username=moderator_username,
                moderator_email=moderator_email,
                reason=getattr(w, "reason", None),
                created_at=getattr(w, "created_at", None),
            )
        )

    return UserWarningsOut(items=items, total=total, page=page, page_size=page_size)


@router.delete("/warnings/{warning_id}")
def admin_delete_warning(
    warning_id: str,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    w = db.query(UserWarning).filter(UserWarning.id == warning_id).first()
    if not w:
        raise HTTPException(status_code=404, detail="Warning introuvable")
    db.delete(w)
    db.commit()
    return {"status": "ok", "deleted": 1, "warning_id": warning_id}


@router.delete("/users/{user_id}/warnings")
def admin_delete_user_warnings(
    user_id: str,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    # Vérifier que l'utilisateur existe
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    deleted_count = (
        db.query(UserWarning).filter(UserWarning.user_id == user_id).delete()
    )
    db.commit()
    return {"status": "ok", "deleted": int(deleted_count), "user_id": user_id}
