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
        if user_id in self.user_extractors:
            return self.user_extractors[user_id]
        # Create a new extractor and configure with user-specific settings & Spotify secrets if present
        extractor = SpotifyColorExtractor()
        try:
            # Paramétrer la couleur de secours depuis les settings utilisateur (prioritaire)
            from app.models.user import UserSetting

            u = db.query(User).filter(User.id == user_id).first()
            s = db.query(UserSetting).filter(UserSetting.user_id == user_id).first()
            default_hex = (
                getattr(s, "default_color_overlays", None) if s else None
            ) or (getattr(u, "default_color_hex", None) if u else None)
            if default_hex:
                extractor.set_default_fallback_hex(default_hex)

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
            # Fallback to unconfigured extractor
            pass
        self.user_extractors[user_id] = extractor
        return extractor


# Singleton global pour un accès simple depuis les routes
_STATE_SINGLETON: Optional[AppState] = None


def get_state() -> AppState:
    global _STATE_SINGLETON
    if _STATE_SINGLETON is None:
        _STATE_SINGLETON = AppState()
    return _STATE_SINGLETON
