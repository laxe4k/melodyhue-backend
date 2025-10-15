from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from ..models.user import User, UserSession, TwoFA, LoginChallenge, TwoFADisable
from ..utils.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    is_refresh,
    totp_generate_secret,
    totp_verify,
)


class AuthController:
    def register(self, db: Session, username: str, email: str, password: str) -> User:
        # Unicité sur l'email uniquement; usernames peuvent être dupliqués
        if db.query(User).filter(User.email == email).first():
            raise ValueError("email_taken")
        u = User(username=username, email=email, password_hash=hash_password(password))
        db.add(u)
        db.commit()
        db.refresh(u)
        return u

    def _issue_tokens(self, db: Session, user: User) -> tuple[str, str]:
        access = create_access_token(
            user.id, {"username": user.username, "role": getattr(user, "role", "user")}
        )
        refresh = create_refresh_token(user.id)
        # Persist refresh token session
        sess = UserSession(
            user_id=user.id,
            refresh_token=refresh,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=30),
        )
        db.add(sess)
        db.commit()
        return access, refresh

    def login_step1(
        self, db: Session, username_or_email: str, password: str
    ) -> tuple[User, Optional[str]]:
        q = (
            db.query(User)
            .filter(
                (User.username == username_or_email) | (User.email == username_or_email)
            )
            .first()
        )
        if not q or not verify_password(password, q.password_hash):
            raise ValueError("invalid_credentials")
        # 2FA enabled AND verified? issue login challenge ticket
        tfa = db.query(TwoFA).filter(TwoFA.user_id == q.id).first()
        if tfa and getattr(tfa, "verified_at", None):
            ticket = LoginChallenge(
                user_id=q.id,
                created_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(minutes=5),
            )
            db.add(ticket)
            db.commit()
            db.refresh(ticket)
            return q, ticket.id
        # No 2FA -> immediate tokens
        q.last_login_at = datetime.utcnow()
        db.add(q)
        db.commit()
        return q, None

    def login_step2_totp(
        self, db: Session, ticket: str, code: str
    ) -> tuple[User, str, str]:
        ch = db.query(LoginChallenge).filter(LoginChallenge.id == ticket).first()
        if not ch or ch.used_at is not None or ch.expires_at < datetime.utcnow():
            raise ValueError("invalid_or_expired_ticket")
        u = db.query(User).filter(User.id == ch.user_id).first()
        if not u:
            raise ValueError("user_not_found")
        tfa = db.query(TwoFA).filter(TwoFA.user_id == u.id).first()
        if not tfa or not totp_verify(tfa.secret, code):
            raise ValueError("totp_required_or_invalid")
        ch.used_at = datetime.utcnow()
        u.last_login_at = datetime.utcnow()
        db.add(ch)
        db.add(u)
        db.commit()
        access, refresh = self._issue_tokens(db, u)
        return u, access, refresh

    def refresh(self, db: Session, refresh_token: str) -> tuple[str, str]:
        payload = decode_token(refresh_token)
        if not is_refresh(payload):
            raise ValueError("not_refresh_token")
        # Validate session exists
        sess = (
            db.query(UserSession)
            .filter(UserSession.refresh_token == refresh_token)
            .first()
        )
        if not sess:
            raise ValueError("session_revoked")
        user = db.query(User).filter(User.id == sess.user_id).first()
        if not user:
            raise ValueError("user_not_found")
        # rotate refresh token
        db.delete(sess)
        db.commit()
        access, refresh = self._issue_tokens(db, user)
        return access, refresh

    def enable_2fa(self, db: Session, user: User) -> tuple[str, str]:
        secret = totp_generate_secret()
        otpauth = (
            f"otpauth://totp/MelodyHue:{user.email}?secret={secret}&issuer=MelodyHue"
        )
        # Upsert
        tfa = db.query(TwoFA).filter(TwoFA.user_id == user.id).first()
        if not tfa:
            tfa = TwoFA(user_id=user.id, secret=secret, verified_at=None)
            db.add(tfa)
        else:
            tfa.secret = secret
            tfa.verified_at = None
        db.commit()
        return secret, otpauth

    def verify_2fa(self, db: Session, user: User, code: str) -> bool:
        tfa = db.query(TwoFA).filter(TwoFA.user_id == user.id).first()
        if not tfa:
            return False
        ok = totp_verify(tfa.secret, code)
        if ok and getattr(tfa, "verified_at", None) is None:
            from datetime import datetime as _dt

            tfa.verified_at = _dt.utcnow()
            db.add(tfa)
            db.commit()
        return ok

    def disable_2fa(self, db: Session, user: User, code: str) -> bool:
        """
        Désactive la 2FA pour l'utilisateur après vérification d'un code TOTP valide.
        Lève des ValueError avec codes:
        - "twofa_not_enabled" si aucune 2FA n'est configurée
        - "invalid_code" si le code TOTP fourni est invalide
        """
        tfa = db.query(TwoFA).filter(TwoFA.user_id == user.id).first()
        if not tfa:
            raise ValueError("twofa_not_enabled")
        if not totp_verify(tfa.secret, code):
            raise ValueError("invalid_code")
        db.delete(tfa)
        db.commit()
        return True

    def request_twofa_disable(self, db: Session, user: User) -> str:
        """Crée un token de désactivation 2FA (valide 1h) et le retourne (brut).
        L'appelant peut l'envoyer par email.
        """
        from secrets import token_urlsafe
        import hashlib

        raw = token_urlsafe(32)
        token_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        ent = TwoFADisable(
            token=token_hash,
            user_id=user.id,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=1),
        )
        db.add(ent)
        db.commit()
        return raw

    def confirm_twofa_disable(self, db: Session, raw_token: str) -> bool:
        import hashlib

        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        ent = db.query(TwoFADisable).filter(TwoFADisable.token == token_hash).first()
        if not ent or ent.used_at is not None or ent.expires_at < datetime.utcnow():
            raise ValueError("invalid_or_expired_token")
        user = db.query(User).filter(User.id == ent.user_id).first()
        if not user:
            raise ValueError("user_not_found")
        # Remove 2FA if exists
        tfa = db.query(TwoFA).filter(TwoFA.user_id == user.id).first()
        if tfa:
            db.delete(tfa)
        ent.used_at = datetime.utcnow()
        db.add(ent)
        db.commit()
        return True
