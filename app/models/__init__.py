#!/usr/bin/env python3
"""
Package app.models (compatibilité) - redirige vers app.services
"""

import os
import glob

from app.services import ColorExtractor, SpotifyClient, SpotifyColorExtractor

__all__ = [
    os.path.basename(f)[:-3]
    for f in glob.glob(os.path.dirname(__file__) + "/*.py")
    if not os.path.basename(f).startswith("__")
]
