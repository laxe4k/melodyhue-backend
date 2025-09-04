#!/usr/bin/env python3
"""
Service utilitaire pour récupérer la version depuis les releases GitHub
et l'année de création du dépôt.

Par défaut, utilise le repo 'laxe4k/nowplaying-color-api' mais peut être
surchargé via la variable d'environnement GITHUB_REPO (format: owner/repo).
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Optional

import requests
import logging


GITHUB_API_BASE = "https://api.github.com"


def _repo_slug() -> str:
    return os.getenv("GITHUB_REPO", "laxe4k/nowplaying-color-api")


def _auth_token() -> Optional[str]:
    """Retourne un token GitHub si défini dans l'environnement.

    Variables supportées (par priorité):
    - GITHUB_TOKEN
    - GH_TOKEN
    - GITHUB_API_TOKEN
    """
    return (
        os.getenv("GITHUB_TOKEN")
        or os.getenv("GH_TOKEN")
        or os.getenv("GITHUB_API_TOKEN")
        or None
    )


def _api_headers() -> dict:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "nowplaying-color-api/1.0",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = _auth_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def get_latest_release_version(timeout: float = 2.5) -> Optional[str]:
    """Retourne la version (tag) de la dernière release GitHub.

    - Strips le préfixe 'v' s'il existe pour n'afficher que 'X.Y.Z'.
    - Retourne None si introuvable ou en cas d'erreur réseau.
    """
    owner_repo = _repo_slug()
    url = f"{GITHUB_API_BASE}/repos/{owner_repo}/releases/latest"
    headers = _api_headers()
    try:
        r = requests.get(url, headers=headers, timeout=timeout)
        if r.status_code != 200:
            # Si l'API est limitée (403) ou aucune release (404), tenter un repli sans API
            logging.warning(
                "GitHub API /releases/latest status=%s; tentative de fallback HTML",
                r.status_code,
            )
            tag = _fallback_latest_tag_via_redirect(timeout=timeout)
            if tag:
                return tag
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
        # Repli final via redirection HTML si l'appel API a échoué
        logging.exception(
            "Erreur lors de l'appel GitHub API pour la version; fallback HTML"
        )
        return _fallback_latest_tag_via_redirect(timeout=timeout)


def _fallback_latest_tag_via_redirect(timeout: float = 2.5) -> Optional[str]:
    """Essaie de récupérer le dernier tag en utilisant la redirection HTML de GitHub.

    Appelle https://github.com/<owner>/<repo>/releases/latest avec allow_redirects=False
    et lit l'en-tête Location qui pointe vers /tag/<TAG>. Ne consomme pas l'API.
    """
    try:
        owner_repo = _repo_slug()
        url = f"https://github.com/{owner_repo}/releases/latest"
        # Ne pas suivre la redirection pour pouvoir lire Location
        r = requests.get(
            url,
            allow_redirects=False,
            timeout=timeout,
            headers={
                "User-Agent": "nowplaying-color-api/1.0",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
        )
        # GitHub renvoie généralement 302 ou 301 vers /releases/tag/<vX.Y.Z>
        if r.status_code in (301, 302, 303, 307, 308):
            loc = r.headers.get("Location") or r.headers.get("location")
            if not loc:
                return None
            # Exemple: https://github.com/owner/repo/releases/tag/v1.2.3
            # Extraire la dernière partie après '/tag/'
            tag = loc.split("/tag/")[-1].split("/")[-1].strip()
            if not tag:
                return None
            if tag.lower().startswith("v"):
                tag = tag[1:]
            return tag
        # Si GitHub change le comportement et suit la redirection automatiquement
        # on peut tenter de lire l'URL finale via r.url quand status 200
        if r.status_code == 200:
            final_url = r.url or ""
            if "/releases/tag/" in final_url:
                tag = final_url.split("/tag/")[-1].split("/")[-1].strip()
                if tag.lower().startswith("v"):
                    tag = tag[1:]
                return tag
        return None
    except Exception:
        logging.exception("Fallback HTML /releases/latest a échoué")
        return None


def get_repo_created_year(timeout: float = 2.5) -> Optional[int]:
    """Retourne l'année de création du dépôt GitHub.

    Retourne None si indisponible ou en cas d'erreur réseau.
    """
    owner_repo = _repo_slug()
    url = f"{GITHUB_API_BASE}/repos/{owner_repo}"
    headers = _api_headers()
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
    headers = _api_headers()
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
