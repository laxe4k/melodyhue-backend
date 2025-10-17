from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..utils.database import get_db
from ..utils.security import hash_password, verify_password, gravatar_url
from ..utils.auth_dep import get_current_user_id, get_current_user
from ..models.user import (
    User,
    Overlay,
    UserSession,
    TwoFA,
    SpotifySecret,
    SpotifyToken,
    PasswordReset,
    UserSetting,
    LoginChallenge,
    TwoFADisable,
    UserBan,
    UserWarning,
)
from ..schemas.user import (
    UserOut,
    PublicUserOut,
    UpdateUsernameIn,
    UpdateEmailIn,
    ChangePasswordIn,
)

router = APIRouter()


def _get_current_user(db: Session, uid: str) -> User:
    u = db.query(User).filter(User.id == uid).first()
    if not u:
        raise HTTPException(status_code=401, detail="Invalid token")
    return u


@router.get("/me", response_model=UserOut)
def me(
    user: User = Depends(get_current_user),  # applique la vérification ban
    db: Session = Depends(get_db),
):
    u = user
    out = UserOut.model_validate(u)
    out.avatar_url = gravatar_url(u.email)
    # Couleur par défaut des overlays: préférer UserSetting.default_overlay_color
    settings_row = db.query(UserSetting).filter(UserSetting.user_id == u.id).first()
    color_default = (
        getattr(settings_row, "default_overlay_color", None) if settings_row else None
    ) or None
    # Renseigner le nouveau champ de sortie
    out.default_overlay_color = color_default
    tfa = db.query(TwoFA).filter(TwoFA.user_id == u.id).first()
    out.twofa_enabled = bool(tfa and getattr(tfa, "verified_at", None))
    return out


@router.get("/{user_id}", response_model=PublicUserOut, tags=["public"])
def get_user_public(user_id: str, db: Session = Depends(get_db)):
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    # Source de vérité: paramètres utilisateur s'ils existent
    settings_row = db.query(UserSetting).filter(UserSetting.user_id == user_id).first()
    legacy_default_color_hex = (
        getattr(settings_row, "default_overlay_color", None) if settings_row else None
    ) or None
    return PublicUserOut(
        id=u.id,
        username=u.username,
        created_at=u.created_at,
        avatar_url=gravatar_url(u.email),
        default_overlay_color=legacy_default_color_hex,
    )


@router.patch("/me/username", response_model=UserOut)
def update_username(
    payload: UpdateUsernameIn,
    uid: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    u = _get_current_user(db, uid)
    if (
        db.query(User)
        .filter(User.username == payload.username, User.id != u.id)
        .first()
    ):
        raise HTTPException(status_code=409, detail="Username déjà pris")
    u.username = payload.username
    db.add(u)
    db.commit()
    db.refresh(u)
    out = UserOut.model_validate(u)
    out.avatar_url = gravatar_url(u.email)
    return out


@router.patch("/me/email", response_model=UserOut)
def update_email(
    payload: UpdateEmailIn,
    uid: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    u = _get_current_user(db, uid)
    if db.query(User).filter(User.email == payload.email, User.id != u.id).first():
        raise HTTPException(status_code=409, detail="Email déjà utilisé")
    u.email = payload.email
    db.add(u)
    db.commit()
    db.refresh(u)
    out = UserOut.model_validate(u)
    out.avatar_url = gravatar_url(u.email)
    return out


@router.post("/me/password")
def change_password(
    payload: ChangePasswordIn,
    uid: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    u = _get_current_user(db, uid)
    if not verify_password(payload.old_password, u.password_hash):
        raise HTTPException(status_code=400, detail="Ancien mot de passe invalide")
    u.password_hash = hash_password(payload.new_password)
    db.add(u)
    db.commit()
    return {"status": "ok"}


@router.delete("/me", summary="Delete my account")
def delete_me_rest(
    uid: str = Depends(get_current_user_id), db: Session = Depends(get_db)
):
    u = db.query(User).filter(User.id == uid).first()
    if not u:
        raise HTTPException(status_code=401, detail="Invalid token")
    # Delete dependent rows explicitly to avoid FK issues
    db.query(Overlay).filter(Overlay.owner_id == uid).delete(synchronize_session=False)
    db.query(UserSession).filter(UserSession.user_id == uid).delete(
        synchronize_session=False
    )
    db.query(TwoFA).filter(TwoFA.user_id == uid).delete(synchronize_session=False)
    db.query(SpotifySecret).filter(SpotifySecret.user_id == uid).delete(
        synchronize_session=False
    )
    db.query(SpotifyToken).filter(SpotifyToken.user_id == uid).delete(
        synchronize_session=False
    )
    db.query(PasswordReset).filter(PasswordReset.user_id == uid).delete(
        synchronize_session=False
    )
    db.query(UserSetting).filter(UserSetting.user_id == uid).delete(
        synchronize_session=False
    )
    db.query(LoginChallenge).filter(LoginChallenge.user_id == uid).delete(
        synchronize_session=False
    )
    db.query(TwoFADisable).filter(TwoFADisable.user_id == uid).delete(
        synchronize_session=False
    )
    db.query(UserWarning).filter(UserWarning.user_id == uid).delete(
        synchronize_session=False
    )
    db.query(UserWarning).filter(UserWarning.moderator_id == uid).delete(
        synchronize_session=False
    )
    db.query(UserBan).filter(UserBan.user_id == uid).delete(synchronize_session=False)
    # Finally delete user
    db.delete(u)
    db.commit()
    return {"status": "deleted"}
