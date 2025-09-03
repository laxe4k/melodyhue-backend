#!/usr/bin/env python3
"""
Client Tidal (via tidalapi) + helpers d'authentification par code appareil
et récupération des pochettes à partir d'un track_id ou ISRC.
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any

import tidalapi  # type: ignore

from app.security.crypto import encrypt_str, decrypt_str
from app.services.color_extractor_service import ColorExtractor
from app.services.user_service import UserService


class TidalClient:
    def __init__(self) -> None:
        self.session = tidalapi.Session()
        self.user_service = UserService()
        self._link_logins: dict[str, tidalapi.session.LinkLogin] = {}
        self.color_extractor = ColorExtractor()

    # ---- Auth appareil (Device Link)
    def start_device_login(self, user_ref: str) -> Dict[str, Any]:
        """Démarre l'association via code appareil pour l'utilisateur donné.

        Renvoie un dict contenant user_code et verification_uri_complete.
        """
        link = self.session.get_link_login()
        # Mémoriser temporairement côté serveur
        self._link_logins[user_ref] = link
        return {
            "user_code": link.user_code,
            "verification_uri": link.verification_uri,
            "verification_uri_complete": link.verification_uri_complete,
            "expires_in": int(link.expires_in),
            "interval": int(link.interval),
        }

    def finalize_device_login(self, user_ref: str) -> bool:
        """Tente de finaliser l'association pour l'utilisateur ref (polling)."""
        link = self._link_logins.get(user_ref)
        if not link:
            return False
        ok = self.session.process_link_login(link, until_expiry=True)
        if not ok:
            return False
        # Persister les tokens chiffrés en base
        username = self._resolve_username(user_ref)
        if not username:
            return False
        try:
            self.user_service.set_tidal_tokens(
                username=username,
                token_type=self.session.token_type or "Bearer",
                access_token=self.session.access_token or "",
                refresh_token=self.session.refresh_token or "",
                expiry_time=self.session.expiry_time,
            )
        except Exception as e:
            logging.error(f"Tidal: échec de sauvegarde des tokens: {e}")
            return False
        return True

    def _resolve_username(self, ref: str) -> Optional[str]:
        """Accepte un username ou un UUID et renvoie le username réel."""
        u = self.user_service.get_user(ref) or self.user_service.get_user_by_uuid(ref)
        return u.username if u else None

    # ---- Session / tokens
    def ensure_session(self, user_ref: str) -> bool:
        """Charge/rafraîchit la session Tidal à partir des tokens DB pour cet utilisateur."""
        username = self._resolve_username(user_ref)
        if not username:
            return False
        tokens = self.user_service.get_tidal_tokens(username)
        if not tokens:
            return False
        token_type, access_token, refresh_token, expiry_time = tokens
        try:
            # Rafraîchir d'abord l'access token si on a un refresh
            if refresh_token:
                self.session.token_refresh(refresh_token)
                # Normaliser la session complète (sessions -> user, country_code, etc.)
                self.session.load_oauth_session(
                    token_type=self.session.token_type or token_type or "Bearer",
                    access_token=self.session.access_token or access_token or "",
                    refresh_token=refresh_token,
                    expiry_time=self.session.expiry_time or expiry_time,
                )
                return True
            # Sinon, tenter une session directe si access_token non expiré (peu fréquent)
            if access_token:
                self.session.load_oauth_session(
                    token_type=token_type or "Bearer",
                    access_token=access_token,
                    refresh_token=refresh_token,
                    expiry_time=expiry_time,
                )
                return True
        except Exception as e:
            logging.warning(f"Tidal: ensure_session a échoué: {e}")
            return False
        return False

    # ---- Récupération d'images et infos piste
    def get_track_info_by_id(self, track_id: int) -> Optional[dict]:
        try:
            t = self.session.track(track_id)
            # Charger métadonnées complètes
            track = t.factory()
            album = track.album()
            image_url = album.image(640)
            artists = ", ".join([a.name for a in track.artists()])
            return {
                "id": track.id,
                "name": track.name,
                "artist": artists,
                "album": album.name,
                "image_url": image_url,
            }
        except Exception:
            return None

    def get_track_info_by_isrc(self, isrc: str) -> Optional[dict]:
        try:
            tracks = self.session.get_tracks_by_isrc(isrc)
            if not tracks:
                return None
            track = tracks[0]
            album = track.album()
            image_url = album.image(640)
            artists = ", ".join([a.name for a in track.artists()])
            return {
                "id": track.id,
                "name": track.name,
                "artist": artists,
                "album": album.name,
                "image_url": image_url,
            }
        except Exception:
            return None

    def extract_color_from_image(self, image_url: str) -> tuple[int, int, int]:
        try:
            img = self.color_extractor.download_image(image_url)
            if not img:
                return (255, 0, 150)
            return self.color_extractor.extract_primary_color(img)
        except Exception:
            return (255, 0, 150)
