#!/usr/bin/env python3
"""
Modèle User (SQLAlchemy) avec identifiants Spotify par utilisateur.
"""

from datetime import datetime
from uuid import uuid4
from ..extensions import db


class User(db.Model):
    __tablename__ = "users"

    # Nouvel identifiant interne auto-incrémenté (PK)
    internal_id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # UUID stable et unique (non-PK)
    uuid = db.Column(
        db.String(36),
        nullable=False,
        unique=True,
        default=lambda: str(uuid4()),
    )

    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    # Préférences d'affichage
    default_color_hex = db.Column(db.String(7))  # format normalisé '#rrggbb'

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relation 1-1 vers les identifiants Spotify (table séparée)
    spotify_credential = db.relationship(
        "SpotifyCredential",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User {self.username}>"
