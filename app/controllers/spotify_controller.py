#!/usr/bin/env python3
import os
import json
import time
from flask import Blueprint, current_app, jsonify, request

bp = Blueprint("spotify", __name__)


def _extractor():
    return current_app.extensions.get("extractor")


def _data_dir():
    # Plus d'usage de data/ pour la config; conservé pour compat postérieure si besoin
    return None


def _spotify_config_path():
    # Obsolète: pas de fichier de configuration local
    return None


@bp.route("/color", methods=["GET"])
def get_color():
    start_time = time.time()
    extractor = _extractor()
    try:
        color = extractor.extract_color()
        response = {
            "status": "success",
            "color": {
                "r": color[0],
                "g": color[1],
                "b": color[2],
                "hex": f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}",
            },
            "timestamp": int(time.time()),
            "processing_time_ms": int((time.time() - start_time) * 1000),
        }
        return jsonify(response)
    except Exception as e:
        response = {
            "status": "error",
            "error": str(e),
            "color": {"r": 100, "g": 200, "b": 255, "hex": "#64c8ff"},
            "timestamp": int(time.time()),
        }
        return jsonify(response), 500


@bp.route("/infos", methods=["GET"])
def get_infos():
    start_time = time.time()
    extractor = _extractor()
    try:
        track_info = extractor.get_current_track_info()
        if track_info and track_info.get("id"):
            color = extractor.extract_color()
            response = {
                "status": "success",
                "track": track_info,
                "color": {
                    "r": color[0],
                    "g": color[1],
                    "b": color[2],
                    "hex": f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}",
                },
                "timestamp": int(time.time()),
                "processing_time_ms": int((time.time() - start_time) * 1000),
            }
        else:
            fallback_color = (100, 200, 255)
            response = {
                "status": "no_music",
                "message": "Aucune musique en lecture sur Spotify",
                "color": {
                    "r": fallback_color[0],
                    "g": fallback_color[1],
                    "b": fallback_color[2],
                    "hex": "#64c8ff",
                },
                "timestamp": int(time.time()),
            }

        return jsonify(response)
    except Exception as e:
        fallback_color = (100, 200, 255)
        response = {
            "status": "error",
            "error": str(e),
            "color": {
                "r": fallback_color[0],
                "g": fallback_color[1],
                "b": fallback_color[2],
                "hex": "#64c8ff",
            },
            "timestamp": int(time.time()),
        }
        return jsonify(response), 500


@bp.route("/health", methods=["GET"])
def health_check():
    extractor = _extractor()
    response = {
        "status": "healthy",
        "service": "spotify-color-api-flask",
        "stats": extractor.get_stats() if extractor else {},
        "timestamp": int(time.time()),
    }
    return jsonify(response)


@bp.route("/spotify/oauth-url", methods=["GET"])
def spotify_oauth_url():
    extractor = _extractor()
    if extractor and extractor.spotify_client.spotify_client_id:
        auth_url = extractor.spotify_client.get_auth_url()
        return jsonify({"status": "success", "auth_url": auth_url})
    return jsonify({"status": "error", "error": "Spotify Client ID non configuré"}), 400


@bp.route("/spotify/logout", methods=["POST"])
def spotify_logout():
    extractor = _extractor()
    if not extractor:
        return jsonify({"status": "error", "error": "Extractor non initialisé"}), 500
    ok = extractor.spotify_client.logout()
    return jsonify({"status": "success" if ok else "error"})


@bp.route("/spotify/callback", methods=["GET"])
def spotify_callback():
    extractor = _extractor()
    try:
        code = request.args.get("code")
        error = request.args.get("error")

        from flask import render_template

        def render_cb(title: str, message: str, kind: str = "info"):
            accent = {"success": "#1db954", "error": "#ff6b6b", "info": "#64c8ff"}.get(
                kind, "#64c8ff"
            )
            return render_template(
                "callback.html", title=title, message=message, accent=accent
            )

        if error:
            return render_cb("Erreur Spotify", f"Erreur: {error}", kind="error"), 400

        if code and extractor:
            ok = extractor.spotify_client.handle_callback(code)
            if ok:
                return (
                    render_cb(
                        "Connexion réussie",
                        "Votre compte Spotify est connecté. Vous pouvez fermer cette fenêtre ou revenir à la page de connexion.",
                        kind="success",
                    ),
                    200,
                )
            return (
                render_cb(
                    "Échec de la connexion",
                    "Impossible de se connecter à Spotify. Revenez à la page de connexion pour réessayer.",
                    kind="error",
                ),
                500,
            )

        return (
            render_cb(
                "Code manquant",
                "Le paramètre 'code' est absent. Revenez à la page de connexion pour relancer l'autorisation.",
                kind="error",
            ),
            400,
        )
    except Exception as e:
        from flask import render_template

        return (
            render_template(
                "callback.html",
                title="Erreur serveur",
                message=f"Une erreur est survenue: {str(e)}",
                accent="#ff6b6b",
            ),
            500,
        )


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


@bp.route("/settings/spotify", methods=["GET"])
def get_spotify_settings():
    extractor = _extractor()
    cfg = {}

    client = extractor.spotify_client if extractor else None
    is_auth = client.is_authenticated() if client else False
    client_id_set = bool(client.spotify_client_id if client else None)
    redirect_uri = client.redirect_uri if client else None

    recommended_redirect = request.host_url.rstrip("/") + "/spotify/callback"

    return jsonify(
        {
            "status": "success",
            "config": {
                "client_id_set": client_id_set,
                "redirect_uri": redirect_uri,
                "recommended_redirect_uri": recommended_redirect,
                "is_authenticated": is_auth,
            },
        }
    )


@bp.route("/settings/spotify", methods=["POST"])
def set_spotify_settings():
    extractor = _extractor()
    if not extractor:
        return jsonify({"status": "error", "error": "Extractor non initialisé"}), 500

    data = request.get_json(silent=True) or {}
    client_id = (data.get("client_id") or "").strip()
    client_secret = (data.get("client_secret") or "").strip()
    recommended_redirect = request.host_url.rstrip("/") + "/spotify/callback"
    redirect_uri = recommended_redirect

    if not client_id or not client_secret:
        return (
            jsonify({"status": "error", "error": "client_id et client_secret requis"}),
            400,
        )

    # Désormais, la config est volatile pour l'instance globale uniquement

    client = extractor.spotify_client
    client.spotify_client_id = client_id
    client.spotify_client_secret = client_secret
    client.redirect_uri = recommended_redirect

    return jsonify(
        {
            "status": "success",
            "message": "Configuration enregistrée. Cliquez sur Connexion pour autoriser Spotify.",
            "is_authenticated": False,
        }
    )
