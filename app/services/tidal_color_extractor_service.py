#!/usr/bin/env python3
"""
Extracteur de couleurs pour Tidal basé sur TidalClient.

Note: Tidal n'expose pas un endpoint public stable pour "currently playing".
Cet extracteur fonctionne par requête explicite d'une piste (track_id ou ISRC).
"""

import time
from typing import Optional

from .tidal_client_service import TidalClient


class TidalColorExtractor:
    def __init__(self) -> None:
        self.client = TidalClient()
        self._last_color_cache: dict[str, tuple[int, int, int]] = {}
        self._last_color_ts: float = 0.0
        self._cache_ttl = 5.0

    def get_track_and_color(
        self,
        user_ref: str,
        *,
        track_id: Optional[int] = None,
        isrc: Optional[str] = None,
    ) -> Optional[dict]:
        if not self.client.ensure_session(user_ref):
            return None

        info = None
        if track_id is not None:
            info = self.client.get_track_info_by_id(track_id)
        elif isrc:
            info = self.client.get_track_info_by_isrc(isrc)
        if not info or not info.get("image_url"):
            return None

        cache_key = f"{info['id']}_{int(time.time()//self._cache_ttl)}"
        now = time.time()
        color = self._last_color_cache.get(cache_key)
        if color and (now - self._last_color_ts) < self._cache_ttl:
            rgb = color
        else:
            rgb = self.client.extract_color_from_image(info["image_url"])
            self._last_color_cache = {cache_key: rgb}
            self._last_color_ts = now

        return {
            "track": info,
            "color": {
                "r": rgb[0],
                "g": rgb[1],
                "b": rgb[2],
                "hex": f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}",
            },
            "source": "album",
        }
