#!/usr/bin/env python3
"""
Modèle séparé pour les identifiants Spotify par utilisateur.
"""

from datetime import datetime
from ..extensions import db


class SpotifyCredential(db.Model):
    __tablename__ = "spotify_credentials"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # Clé étrangère vers l'utilisateur (internal_id)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.internal_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # 1 seul enregistrement par utilisateur
        index=True,
    )

    # Identifiants Spotify (chiffrés côté service si nécessaire)
    client_id = db.Column(db.String(255), nullable=True)
    client_secret = db.Column(db.String(255), nullable=True)
    refresh_token = db.Column(db.String(1024), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relation inverse vers User
    user = db.relationship("User", back_populates="spotify_credential")

    def __repr__(self) -> str:
        return f"<SpotifyCredential user_id={self.user_id}>"
