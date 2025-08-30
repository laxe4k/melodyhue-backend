#!/usr/bin/env python3
"""
Service utilisateurs basé sur SQLAlchemy + Argon2id.
"""

from typing import Optional, Tuple
from sqlalchemy import func
from argon2.exceptions import VerifyMismatchError
from ..extensions import db, password_hasher
from ..models.user_model import User
from ..security.crypto import encrypt_str, decrypt_str


class UserService:
    def __init__(self):
        # Plus de stockage local; tout passe par la base de données
        pass

    # Comptes
    def user_exists(self, username: str) -> bool:
        return User.query.filter_by(username=username).first() is not None

    def create_user(self, username: str, email: str, password: str) -> bool:
        if User.query.filter(
            (User.username == username) | (User.email == email)
        ).first():
            return False
        password_hash = password_hasher.hash(password)
        user = User(username=username, email=email, password_hash=password_hash)
        db.session.add(user)
        db.session.commit()
        return True

    def authenticate(self, username: str, password: str) -> bool:
        # Recherche insensible à la casse
        user = User.query.filter(
            func.lower(User.username) == (username or "").lower()
        ).first()
        if not user:
            return False
        try:
            password_hasher.verify(user.password_hash, password)
            return True
        except VerifyMismatchError:
            return False

    def get_user(self, username: str) -> Optional[User]:
        return User.query.filter_by(username=username).first()

    def get_user_insensitive(self, username: str) -> Optional[User]:
        return User.query.filter(
            func.lower(User.username) == (username or "").lower()
        ).first()

    def get_user_by_uuid(self, user_uuid: str) -> Optional[User]:
        return User.query.filter_by(uuid=user_uuid).first()

    # Credentials Spotify par utilisateur
    def set_spotify_credentials(
        self, username: str, client_id: str, client_secret: str
    ) -> bool:
        user = self.get_user(username)
        if not user:
            return False
        user.spotify_client_id = client_id
        # Chiffrer le secret avant stockage
        user.spotify_client_secret = encrypt_str(client_secret)
        db.session.commit()
        return True

    def get_spotify_credentials(
        self, username: str
    ) -> Tuple[Optional[str], Optional[str]]:
        user = self.get_user(username)
        if not user:
            return (None, None)
        # Déchiffrer si préfixé enc:
        return (user.spotify_client_id, decrypt_str(user.spotify_client_secret))

    def set_refresh_token(self, username: str, refresh_token: Optional[str]) -> bool:
        user = self.get_user(username)
        if not user:
            return False
        # Chiffrer le refresh token avant stockage (None reste None)
        user.spotify_refresh_token = encrypt_str(refresh_token)
        db.session.commit()
        return True

    def get_refresh_token(self, username: str) -> Optional[str]:
        u = self.get_user(username)
        # Déchiffrer si préfixé enc:, sinon retourne la valeur legacy en clair
        return decrypt_str(u.spotify_refresh_token) if u else None

    # Préférences: couleur par défaut (format '#rrggbb')
    def set_default_color(self, username: str, color_hex: Optional[str]) -> bool:
        u = self.get_user(username)
        if not u:
            return False
        if color_hex:
            h = color_hex.strip().lstrip("#")
            if len(h) == 3:
                h = "".join([c * 2 for c in h])
            if not (len(h) == 6 and all(c in "0123456789abcdefABCDEF" for c in h)):
                return False
            u.default_color_hex = "#" + h.lower()
        else:
            u.default_color_hex = None
        db.session.commit()
        return True

    def get_default_color(self, username: str) -> Optional[str]:
        u = self.get_user(username)
        return u.default_color_hex if u else None

    # Profil: mise à jour username / email
    def update_profile(
        self,
        current_username: str,
        new_username: Optional[str] = None,
        new_email: Optional[str] = None,
    ) -> tuple[bool, Optional[str], Optional[str], Optional[str]]:
        """Met à jour username et/ou email.

        Retourne (ok, error, username, email).
        """
        user = self.get_user(current_username)
        if not user:
            return (False, "Utilisateur introuvable", None, None)

        # Normalisations de base
        if new_username is not None:
            new_username = new_username.strip()
        if new_email is not None:
            new_email = new_email.strip()

        # Unicité username/email si modifiés
        if new_username and new_username != user.username:
            if User.query.filter(User.username == new_username).first():
                return (False, "Nom d'utilisateur déjà pris", None, None)
            user.username = new_username

        if new_email and new_email != user.email:
            if User.query.filter(User.email == new_email).first():
                return (False, "Email déjà utilisé", None, None)
            user.email = new_email

        db.session.commit()
        return (True, None, user.username, user.email)

    # Sécurité: mise à jour du mot de passe
    def update_password(
        self, current_username: str, current_password: str, new_password: str
    ) -> tuple[bool, str | None]:
        user = self.get_user(current_username)
        if not user:
            return (False, "Utilisateur introuvable")
        try:
            password_hasher.verify(user.password_hash, current_password)
        except VerifyMismatchError:
            return (False, "Mot de passe actuel incorrect")
        if not new_password or len(new_password) < 8:
            return (False, "Nouveau mot de passe trop court (8 caractères min)")
        user.password_hash = password_hasher.hash(new_password)
        db.session.commit()
        return (True, None)
