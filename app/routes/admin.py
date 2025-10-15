from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..utils.database import get_db
from ..utils.auth_dep import require_admin
from ..models.user import User, Overlay, TwoFA
from ..schemas.admin import AdminStatsOut, RoleUpdateIn, UserListOut, UserListItem

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
