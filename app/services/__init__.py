#!/usr/bin/env python3
"""
Package app.services
"""

import os
import glob

from .color_extractor_service import ColorExtractor
from .spotify_client_service import SpotifyClient
from .spotify_color_extractor_service import SpotifyColorExtractor

__all__ = [
    os.path.basename(f)[:-3]
    for f in glob.glob(os.path.dirname(__file__) + "/*.py")
    if not os.path.basename(f).startswith("__")
]
