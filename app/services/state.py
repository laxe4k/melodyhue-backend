from typing import Optional, Dict
from sqlalchemy.orm import Session
from app.services.spotify_color_extractor_service import SpotifyColorExtractor
from app.models.user import SpotifySecret, User
import app.utils.encryption as enc


class AppState:
    def __init__(self) -> None:
        self.extractor: Optional[SpotifyColorExtractor] = None
        self.user_extractors: Dict[str, SpotifyColorExtractor] = {}

    async def start(self):
        # Ne pas initialiser d'extracteur global: chaque utilisateur a le sien
        return None

    async def stop(self):
        # Rien de spécial pour l'instant
        return None

    def get_extractor(self) -> SpotifyColorExtractor:
        if not self.extractor:
            self.extractor = SpotifyColorExtractor()
        return self.extractor

    def get_extractor_for_user(
        self, user_id: str, db: Session
    ) -> SpotifyColorExtractor:
        if not user_id:
            return self.get_extractor()
        # Récupérer ou créer l'extracteur utilisateur
        extractor = self.user_extractors.get(user_id)
        if not extractor:
            extractor = SpotifyColorExtractor()
            self.user_extractors[user_id] = extractor
        # Toujours rafraîchir la couleur de secours depuis la DB pour refléter immédiatement les changements
        try:
            from app.models.user import UserSetting

            s = db.query(UserSetting).filter(UserSetting.user_id == user_id).first()
            default_hex = getattr(s, "default_overlay_color", None) if s else None
            if default_hex:
                extractor.set_default_fallback_hex(default_hex)
        except Exception:
            pass
        # Configurer/rafraîchir les secrets Spotify si présents (ne change rien si identiques)
        try:
            secret = (
                db.query(SpotifySecret).filter(SpotifySecret.user_id == user_id).first()
            )
            if secret:
                cid = enc.decrypt_str(secret.client_id) if secret.client_id else None
                csec = (
                    enc.decrypt_str(secret.client_secret)
                    if secret.client_secret
                    else None
                )
                rtok = (
                    enc.decrypt_str(secret.refresh_token)
                    if secret.refresh_token
                    else None
                )
                if cid and csec:
                    extractor.spotify_client.configure_spotify_api(cid, csec, rtok)
        except Exception:
            pass
        return extractor


# Singleton global pour un accès simple depuis les routes
_STATE_SINGLETON: Optional[AppState] = None


def get_state() -> AppState:
    global _STATE_SINGLETON
    if _STATE_SINGLETON is None:
        _STATE_SINGLETON = AppState()
    return _STATE_SINGLETON
