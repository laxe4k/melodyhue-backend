#!/usr/bin/env python3
"""
Helpers de chiffrement symétrique pour secrets en base (Fernet/AES-GCM).
Requiert la variable d'environnement ENCRYPTION_KEY (clé Fernet base64 32 octets).
"""
import os
from typing import Optional
from cryptography.fernet import Fernet, InvalidToken

_PREFIX = "enc:"


def _get_fernet() -> Fernet:
    key = os.getenv("ENCRYPTION_KEY")
    if not key:
        raise RuntimeError(
            "ENCRYPTION_KEY manquant. Définissez une clé Fernet (base64, 32 octets)."
        )
    try:
        return Fernet(key)
    except Exception as e:
        raise RuntimeError(f"ENCRYPTION_KEY invalide: {e}")


def encrypt_str(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    f = _get_fernet()
    token = f.encrypt(value.encode("utf-8"))
    return _PREFIX + token.decode("utf-8")


def decrypt_str(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    if not value.startswith(_PREFIX):
        # Valeur legacy non chiffrée
        return value
    token = value[len(_PREFIX) :].encode("utf-8")
    f = _get_fernet()
    try:
        plain = f.decrypt(token)
        return plain.decode("utf-8")
    except InvalidToken:
        # Si la clé a changé ou donnée corrompue, renvoyer brut pour éviter la perte
        return value
