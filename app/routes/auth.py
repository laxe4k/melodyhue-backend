from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timedelta
import secrets, hashlib, os
from sqlalchemy.orm import Session
from ..utils.database import get_db
from ..controllers.auth_controller import AuthController
from ..schemas.auth import (
    RegisterIn,
    LoginIn,
    TokenPair,
    RefreshIn,
    ForgotPwdIn,
    ResetPwdIn,
    LoginStep1Out,
    Login2FAIn,
    LoginTokensOut,
)
from ..schemas.user import TwoFASetupOut, TwoFAVerifyIn, UserOut
from ..utils.security import decode_token
from ..utils.auth_dep import get_current_user_id
from ..models.user import User, PasswordReset

router = APIRouter()
ctrl = AuthController()


@router.post("/register", response_model=LoginTokensOut)
def register(payload: RegisterIn, db: Session = Depends(get_db)):
    try:
        u = ctrl.register(db, payload.username, payload.email, payload.password)
        # Considéré comme connecté après inscription: maj last_login_at
        u.last_login_at = datetime.utcnow()
        db.add(u)
        db.commit()
        db.refresh(u)
        # Émettre directement les tokens comme pour un login sans 2FA
        access, refresh = ctrl._issue_tokens(db, u)
        return LoginTokensOut(
            access_token=access,
            refresh_token=refresh,
            token_type="bearer",
            requires_2fa=False,
            ticket=None,
            role=getattr(u, "role", "user"),
            user_id=u.id,
        )
    except ValueError as e:
        if str(e) == "email_taken":
            raise HTTPException(status_code=409, detail="Email déjà pris")
        raise


@router.post("/login", response_model=LoginTokensOut | LoginStep1Out)
def login_step1(payload: LoginIn, db: Session = Depends(get_db)):
    try:
        u, ticket = ctrl.login_step1(db, payload.username_or_email, payload.password)
        if ticket:
            return {"requires_2fa": True, "ticket": ticket}
        # Pas de 2FA: on émet les tokens directement
        from ..controllers.auth_controller import AuthController

        # Rôle: default "user" (pas de champ role en DB pour l'instant)
        role = "user"
        access, refresh = AuthController()._issue_tokens(db, u)
        return LoginTokensOut(
            access_token=access,
            refresh_token=refresh,
            token_type="bearer",
            requires_2fa=False,
            ticket=None,
            role=role,
            user_id=u.id,
        )
    except ValueError as e:
        code = str(e)
        if code == "invalid_credentials":
            raise HTTPException(status_code=401, detail="Identifiants invalides")
        raise


@router.post("/login/2fa", response_model=TokenPair)
def login_step2_totp(body: Login2FAIn, db: Session = Depends(get_db)):
    try:
        u, access, refresh = ctrl.login_step2_totp(db, body.ticket, body.totp)
        return {
            "access_token": access,
            "refresh_token": refresh,
            "token_type": "bearer",
            "user_id": u.id,
            "role": getattr(u, "role", "user"),
        }
    except ValueError as e:
        code = str(e)
        if code == "invalid_or_expired_ticket":
            raise HTTPException(status_code=400, detail="Ticket invalide ou expiré")
        if code == "totp_required_or_invalid":
            raise HTTPException(status_code=401, detail="Code 2FA requis ou invalide")
        if code == "user_not_found":
            raise HTTPException(status_code=404, detail="Utilisateur introuvable")
        raise


@router.post("/refresh", response_model=TokenPair)
def refresh(payload: RefreshIn, db: Session = Depends(get_db)):
    try:
        access, refresh = ctrl.refresh(db, payload.refresh_token)
        return {
            "access_token": access,
            "refresh_token": refresh,
            "token_type": "bearer",
        }
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.post("/2fa/setup", response_model=TwoFASetupOut)
def twofa_setup(uid: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    u = db.query(User).filter(User.id == uid).first()
    if not u:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    secret, url = ctrl.enable_2fa(db, u)
    return {"secret": secret, "otpauth_url": url}


@router.post("/2fa/verify")
def twofa_verify(
    body: TwoFAVerifyIn,
    uid: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    u = db.query(User).filter(User.id == uid).first()
    if not u:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    ok = ctrl.verify_2fa(db, u, body.code)
    if not ok:
        raise HTTPException(status_code=400, detail="Code invalide")
    return {"status": "ok"}


# Password reset placeholders (token storage and email delivery to be implemented)
@router.post("/forgot")
def forgot_password(body: ForgotPwdIn, db: Session = Depends(get_db)):
    u = db.query(User).filter(User.email == body.email).first()
    # Always respond success to prevent enumeration
    if not u:
        return {"status": "sent"}
    raw = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    pr = PasswordReset(
        token=token_hash,
        user_id=u.id,
        created_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(hours=1),
    )
    db.add(pr)
    db.commit()
    # TODO: send email with raw token link
    if os.getenv("EMAIL_DEBUG", "false").lower() == "true":
        return {"status": "sent", "token": raw}
    return {"status": "sent"}


@router.post("/reset")
def reset_password(body: ResetPwdIn, db: Session = Depends(get_db)):
    token_hash = hashlib.sha256(body.token.encode("utf-8")).hexdigest()
    pr = db.query(PasswordReset).filter(PasswordReset.token == token_hash).first()
    if not pr or pr.used_at is not None or pr.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Token invalide ou expiré")
    u = db.query(User).filter(User.id == pr.user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    from ..utils.security import hash_password

    u.password_hash = hash_password(body.new_password)
    pr.used_at = datetime.utcnow()
    db.add(u)
    db.add(pr)
    db.commit()
    return {"status": "ok"}
