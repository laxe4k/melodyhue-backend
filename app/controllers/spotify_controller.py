#!/usr/bin/env python3
import time
from flask import Blueprint, current_app, jsonify

bp = Blueprint("spotify", __name__)


def _extractor():
    return current_app.extensions.get("extractor")


## Routes globales obsolètes supprimées: /color et /infos


@bp.route("/health", methods=["GET"])
def health_check():
    extractor = _extractor()
    response = {
        "status": "healthy",
        "service": "nowplaying-color-api-flask",
        "stats": extractor.get_stats() if extractor else {},
        "timestamp": int(time.time()),
    }
    return jsonify(response)


@bp.route("/debug/track", methods=["GET"])
def debug_track():
    extractor = _extractor()
    try:
        track_info = extractor.get_current_track_info() if extractor else None
        debug_info = {
            "timestamp": int(time.time()),
            "extractor_initialized": extractor is not None,
            "spotify_connected": (
                extractor.spotify_client.is_authenticated() if extractor else False
            ),
            "current_track": track_info,
            "cache_info": {
                "color_cache_size": len(extractor.color_cache) if extractor else 0,
                "current_track_id": extractor.current_track_id if extractor else None,
                "current_image_url": (
                    extractor.current_track_image_url if extractor else None
                ),
            },
        }
        return jsonify(debug_info)
    except Exception as e:
        return jsonify({"error": str(e), "timestamp": int(time.time())}), 500
