#!/usr/bin/env python3
"""
Modèle séparé pour les identifiants Tidal par utilisateur.
"""

from datetime import datetime
from typing import Optional
from ..extensions import db


class TidalCredential(db.Model):
    __tablename__ = "tidal_credentials"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # Clé étrangère vers l'utilisateur (internal_id)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.internal_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # 1 seul enregistrement par utilisateur
        index=True,
    )

    # Tokens OAuth Tidal (chiffrés côté service)
    token_type = db.Column(db.String(50), nullable=True)
    access_token = db.Column(db.String(2048), nullable=True)
    refresh_token = db.Column(db.String(2048), nullable=True)
    expiry_time = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<TidalCredential user_id={self.user_id}>"
