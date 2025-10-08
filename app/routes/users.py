from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..utils.database import get_db
from ..utils.security import hash_password, verify_password, gravatar_url
from ..utils.auth_dep import get_current_user_id
from ..models.user import User
from ..schemas.user import UserOut, UpdateUsernameIn, UpdateEmailIn, ChangePasswordIn

router = APIRouter()


def _get_current_user(db: Session, uid: str) -> User:
    u = db.query(User).filter(User.id == uid).first()
    if not u:
        raise HTTPException(status_code=401, detail="Invalid token")
    return u


@router.get("/me", response_model=UserOut)
def me(uid: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    u = _get_current_user(db, uid)
    out = UserOut.model_validate(u)
    out.avatar_url = gravatar_url(u.email)
    return out


@router.patch("/me/username", response_model=UserOut)
def update_username(payload: UpdateUsernameIn, uid: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    u = _get_current_user(db, uid)
    if db.query(User).filter(User.username == payload.username, User.id != u.id).first():
        raise HTTPException(status_code=409, detail="Username déjà pris")
    u.username = payload.username
    db.add(u)
    db.commit()
    db.refresh(u)
    out = UserOut.model_validate(u)
    out.avatar_url = gravatar_url(u.email)
    return out


@router.patch("/me/email", response_model=UserOut)
def update_email(payload: UpdateEmailIn, uid: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
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
def change_password(payload: ChangePasswordIn, uid: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    u = _get_current_user(db, uid)
    if not verify_password(payload.old_password, u.password_hash):
        raise HTTPException(status_code=400, detail="Ancien mot de passe invalide")
    u.password_hash = hash_password(payload.new_password)
    db.add(u)
    db.commit()
    return {"status": "ok"}
