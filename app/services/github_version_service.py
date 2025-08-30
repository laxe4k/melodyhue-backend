#!/usr/bin/env python3
"""
Service utilitaire pour récupérer la version depuis les releases GitHub
et l'année de création du dépôt.

Par défaut, utilise le repo 'laxe4k/spotify-color-api' mais peut être
surchargé via la variable d'environnement GITHUB_REPO (format: owner/repo).
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Optional

import requests


GITHUB_API_BASE = "https://api.github.com"


def _repo_slug() -> str:
    return os.getenv("GITHUB_REPO", "laxe4k/spotify-color-api")


def get_latest_release_version(timeout: float = 2.5) -> Optional[str]:
    """Retourne la version (tag) de la dernière release GitHub.

    - Strips le préfixe 'v' s'il existe pour n'afficher que 'X.Y.Z'.
    - Retourne None si introuvable ou en cas d'erreur réseau.
    """
    owner_repo = _repo_slug()
    url = f"{GITHUB_API_BASE}/repos/{owner_repo}/releases/latest"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "spotify-color-api/1.0",
    }
    try:
        r = requests.get(url, headers=headers, timeout=timeout)
        if r.status_code != 200:
            return None
        data = r.json() or {}
        tag = (data.get("tag_name") or data.get("name") or "").strip()
        if not tag:
            return None
        # Enlever un éventuel préfixe 'v' (ex: v1.2.3 -> 1.2.3)
        if tag.lower().startswith("v"):
            tag = tag[1:]
        return tag
    except Exception:
        return None


def get_repo_created_year(timeout: float = 2.5) -> Optional[int]:
    """Retourne l'année de création du dépôt GitHub.

    Retourne None si indisponible ou en cas d'erreur réseau.
    """
    owner_repo = _repo_slug()
    url = f"{GITHUB_API_BASE}/repos/{owner_repo}"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "spotify-color-api/1.0",
    }
    try:
        r = requests.get(url, headers=headers, timeout=timeout)
        if r.status_code != 200:
            return None
        data = r.json() or {}
        created_at = data.get("created_at")
        if not created_at:
            return None
        # created_at example: '2025-08-06T12:34:56Z'
        try:
            dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        except Exception:
            return None
        return dt.year
    except Exception:
        return None


def get_repo_owner_login(timeout: float = 2.5) -> Optional[str]:
    """Retourne le login du propriétaire (owner) du dépôt GitHub.

    Exemple: "laxe4k". Retourne None en cas d'erreur.
    """
    owner_repo = _repo_slug()
    url = f"{GITHUB_API_BASE}/repos/{owner_repo}"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "spotify-color-api/1.0",
    }
    try:
        r = requests.get(url, headers=headers, timeout=timeout)
        if r.status_code != 200:
            return None
        data = r.json() or {}
        owner = (data.get("owner") or {}).get("login")
        if owner and isinstance(owner, str):
            return owner
        return None
    except Exception:
        return None
