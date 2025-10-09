from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, DateTime, ForeignKey
from ..utils.database import Base
from ..utils.shortid import new_short_uuid


class User(Base):
    __tablename__ = "api_users"

    # Utiliser un id public court (UUID base64) comme clé primaire API
    id: Mapped[str] = mapped_column(
        String(32), primary_key=True, default=new_short_uuid
    )
    # Champs principaux
    # Le username peut être dupliqué; seule l'email doit rester unique
    username: Mapped[str] = mapped_column(String(80), index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(16), default="user")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relations
    overlays: Mapped[list["Overlay"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )
    sessions: Mapped[list["UserSession"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    twofa: Mapped[Optional["TwoFA"]] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    spotify: Mapped[Optional["SpotifySecret"]] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )


class Overlay(Base):
    __tablename__ = "api_overlays"

    id: Mapped[str] = mapped_column(
        String(32), primary_key=True, default=new_short_uuid
    )
    owner_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("api_users.id"), index=True
    )
    name: Mapped[str] = mapped_column(String(120), default="Overlay")
    # Couleur historique conservée pour compat DB, mais non utilisée par l'API de sortie
    color_hex: Mapped[str] = mapped_column(String(7), default="#25d865")
    # Nouveau: choix du template et du style (apparence)
    template: Mapped[str] = mapped_column(
        String(32), default="classic"
    )  # classic|compact|wave|cards
    style: Mapped[str] = mapped_column(
        String(32), default="light"
    )  # light|dark|glass|neon
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    owner: Mapped[User] = relationship("User", back_populates="overlays")


class UserSession(Base):
    __tablename__ = "api_user_sessions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=new_short_uuid
    )
    user_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("api_users.id"), index=True
    )
    refresh_token: Mapped[str] = mapped_column(String(512), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime)

    user: Mapped[User] = relationship("User", back_populates="sessions")


class TwoFA(Base):
    __tablename__ = "api_twofa"

    user_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("api_users.id"), primary_key=True
    )
    secret: Mapped[str] = mapped_column(String(64))
    enabled_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped[User] = relationship("User", back_populates="twofa")


class SpotifySecret(Base):
    __tablename__ = "api_spotify_secrets"

    user_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("api_users.id"), primary_key=True
    )
    client_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    client_secret: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    refresh_token: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    user: Mapped[User] = relationship("User", back_populates="spotify")


class PasswordReset(Base):
    __tablename__ = "api_password_resets"

    token: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("api_users.id"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class UserSetting(Base):
    __tablename__ = "api_user_settings"

    user_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("api_users.id"), primary_key=True
    )
    theme: Mapped[str] = mapped_column(String(16), default="light")  # light|dark
    layout: Mapped[str] = mapped_column(String(32), default="default")
    avatar_mode: Mapped[str] = mapped_column(
        String(16), default="gravatar"
    )  # gravatar|initials
    avatar_color: Mapped[str] = mapped_column(String(7), default="#25d865")
    # Couleur par défaut pour la création d'overlays (source de vérité)
    default_overlay_color: Mapped[str] = mapped_column(String(7), default="#25d865")


class LoginChallenge(Base):
    __tablename__ = "api_login_challenges"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=new_short_uuid
    )
    user_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("api_users.id"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
