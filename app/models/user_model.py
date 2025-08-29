#!/usr/bin/env python3
"""
Modèle User (SQLAlchemy) avec identifiants Spotify par utilisateur.
"""

from datetime import datetime
from uuid import uuid4
from ..extensions import db


class User(db.Model):
    __tablename__ = "users"

    uuid = db.Column(
        db.String(36),
        primary_key=True,
        nullable=False,
        default=lambda: str(uuid4()),
    )
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    # Credentials Spotify propres à l’utilisateur
    spotify_client_id = db.Column(db.String(255))
    spotify_client_secret = db.Column(db.String(255))
    spotify_refresh_token = db.Column(db.String(512))

    # Préférences d'affichage
    default_color_hex = db.Column(db.String(7))  # format normalisé '#rrggbb'

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<User {self.username}>"
