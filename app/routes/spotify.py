from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from ..utils.database import get_db
from ..utils.auth_dep import get_current_user_id
from ..models.user import SpotifySecret, SpotifyToken
import app.utils.encryption as enc
from ..schemas.spotify import SpotifyCredentialsIn, SpotifyCredentialsStatusOut
from ..services.state import get_state


router = APIRouter()


def _get_or_create_secret(db: Session, uid: str) -> SpotifySecret:
    row = db.query(SpotifySecret).filter(SpotifySecret.user_id == uid).first()
    if not row:
        row = SpotifySecret(user_id=uid)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


@router.get("/credentials/status", response_model=SpotifyCredentialsStatusOut)
def get_spotify_credentials_status(
    uid: str = Depends(get_current_user_id), db: Session = Depends(get_db)
):
    row = db.query(SpotifySecret).filter(SpotifySecret.user_id == uid).first()
    tok = db.query(SpotifyToken).filter(SpotifyToken.user_id == uid).first()
    return SpotifyCredentialsStatusOut(
        has_client_id=bool(getattr(row, "client_id", None)),
        has_client_secret=bool(getattr(row, "client_secret", None)),
        has_refresh_token=bool(getattr(tok, "refresh_token", None)),
    )


@router.patch("/credentials", response_model=SpotifyCredentialsStatusOut)
def upsert_spotify_credentials(
    payload: SpotifyCredentialsIn,
    uid: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    row = _get_or_create_secret(db, uid)

    def _normalize(v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v2 = v.strip()
        return v2 if v2 else None

    if payload.client_id is not None:
        # client_id is not a secret in OAuth; store as plain text
        row.client_id = _normalize(payload.client_id)
    if payload.client_secret is not None:
        row.client_secret = enc.encrypt_str(_normalize(payload.client_secret))
    if payload.refresh_token is not None:
        # Nouveau stockage séparé pour le refresh token
        tok = db.query(SpotifyToken).filter(SpotifyToken.user_id == uid).first()
        if not tok:
            tok = SpotifyToken(user_id=uid)
        tok.refresh_token = enc.encrypt_str(_normalize(payload.refresh_token))
        db.add(tok)

    db.add(row)
    db.commit()
    db.refresh(row)
    tok = db.query(SpotifyToken).filter(SpotifyToken.user_id == uid).first()
    return SpotifyCredentialsStatusOut(
        has_client_id=bool(row.client_id),
        has_client_secret=bool(row.client_secret),
        has_refresh_token=bool(getattr(tok, "refresh_token", None)),
    )


@router.get("/auth/url")
def get_spotify_auth_url(
    redirect_uri: str | None = None,
    uid: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    state = get_state()
    extractor = state.get_extractor_for_user(uid, db)
    if redirect_uri:
        extractor.spotify_client.redirect_uri = redirect_uri
    url = extractor.spotify_client.get_auth_url()
    if not url:
        raise HTTPException(status_code=400, detail="Client ID non configuré")
    return {"url": url}


@router.get("/callback")
def spotify_oauth_callback(
    code: str | None = None,
    redirect_uri: str | None = None,
    uid: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    if not code:
        raise HTTPException(status_code=400, detail="Paramètre 'code' manquant")
    state = get_state()
    extractor = state.get_extractor_for_user(uid, db)
    if redirect_uri:
        extractor.spotify_client.redirect_uri = redirect_uri

    ok = extractor.exchange_code_for_tokens(code)
    if not ok:
        raise HTTPException(status_code=400, detail="Échange du code échoué")

    # Persister le refresh token en DB si disponible
    rt = extractor.spotify_client.spotify_refresh_token
    if rt:
        tok = db.query(SpotifyToken).filter(SpotifyToken.user_id == uid).first()
        if not tok:
            tok = SpotifyToken(user_id=uid)
        tok.refresh_token = enc.encrypt_str(rt)
        db.add(tok)
        db.commit()
    return {"status": "ok"}


@router.get("/auth/status")
def spotify_auth_status(
    uid: str = Depends(get_current_user_id), db: Session = Depends(get_db)
):
    tok = db.query(SpotifyToken).filter(SpotifyToken.user_id == uid).first()
    has_rt = bool(getattr(tok, "refresh_token", None))
    state = get_state()
    extractor = state.get_extractor_for_user(uid, db)
    return {"authenticated": has_rt or extractor.spotify_client.is_authenticated()}


@router.post("/logout")
def spotify_logout(
    uid: str = Depends(get_current_user_id), db: Session = Depends(get_db)
):
    # Nettoyer en DB
    tok = db.query(SpotifyToken).filter(SpotifyToken.user_id == uid).first()
    if tok:
        tok.refresh_token = None
        db.add(tok)
        db.commit()
    # Nettoyer en mémoire
    extractor = get_state().get_extractor_for_user(uid, db)
    extractor.spotify_client.logout()
    return {"status": "logged_out"}
