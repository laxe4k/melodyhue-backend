#!/usr/bin/env python3
"""
Spotify Color API - Version Flask
Application web moderne et simple
"""

import os
import time
import logging
from urllib.parse import urlencode
from flask import Flask, jsonify, request, redirect, render_template_string
from flask_cors import CORS
from dotenv import load_dotenv

# Imports locaux
from app.models import SpotifyColorExtractor

# Charger les variables d'environnement
load_dotenv()

# Configuration du logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Créer l'application Flask
app = Flask(__name__)
CORS(app)  # Activer CORS pour toutes les routes

# Configuration
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key")
DATA_DIR = os.getenv("DATA_DIR", "./data")

# Initialiser l'extracteur global
extractor = None


def init_extractor():
    """Initialiser l'extracteur de couleurs"""
    global extractor
    if extractor is None:
        extractor = SpotifyColorExtractor(DATA_DIR)
        logging.info("✅ Extracteur de couleurs initialisé")
    return extractor


@app.before_request
def before_request():
    """Initialisation avant chaque requête (seulement la première fois)"""
    global extractor
    if extractor is None:
        print("🎵 SPOTIFY COLOR API - VERSION FLASK")
        print("=====================================")
        print("📁 Architecture: Flask + Modular")
        print(f"📡 Port: {os.getenv('PORT', 8765)}")
        print("🎨 Style: FLASHY - Couleurs vives et saturées")
        print("🔇 Logs: MINIMAL - seulement les changements")
        print("🎯 Endpoints: /color, /infos, /health, /debug/track")
        print("=====================================")
        init_extractor()


@app.route("/color", methods=["GET"])
def get_color():
    """Endpoint pour récupérer la couleur dominante"""
    start_time = time.time()

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


@app.route("/infos", methods=["GET"])
def get_infos():
    """Endpoint pour récupérer les infos de la piste + couleur"""
    start_time = time.time()

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


@app.route("/health", methods=["GET"])
def health_check():
    """Endpoint de santé du service"""
    response = {
        "status": "healthy",
        "service": "spotify-color-api-flask",
        "stats": extractor.get_stats() if extractor else {},
        "timestamp": int(time.time()),
    }
    return jsonify(response)


@app.route("/spotify/oauth-url", methods=["GET"])
def spotify_oauth_url():
    """Endpoint pour générer l'URL d'OAuth Spotify"""
    if extractor and extractor.spotify_client.spotify_client_id:
        auth_url = extractor.spotify_client.get_auth_url()
        return jsonify(
            {
                "status": "success",
                "auth_url": auth_url,
                "message": "Visitez cette URL pour autoriser l'accès à Spotify",
            }
        )
    else:
        return (
            jsonify({"status": "error", "error": "Spotify Client ID non configuré"}),
            400,
        )


@app.route("/spotify/callback", methods=["GET"])
def spotify_callback():
    """Gérer le callback OAuth Spotify"""
    try:
        code = request.args.get("code")
        error = request.args.get("error")

        if error:
            return (
                f"""
            <html>
                <body style='font-family: Arial; text-align: center; padding: 50px;'>
                    <h2 style='color: red;'>❌ Erreur d'autorisation</h2>
                    <p>Erreur: {error}</p>
                    <p>L'autorisation Spotify a été refusée.</p>
                </body>
            </html>
            """,
                400,
            )

        if code and extractor:
            success = extractor.spotify_client.handle_callback(code)
            if success:
                return """
                <html>
                    <body style='font-family: Arial; text-align: center; padding: 50px;'>
                        <h2 style='color: green;'>✅ Autorisation réussie !</h2>
                        <p>Spotify est maintenant connecté.</p>
                        <p>Vous pouvez fermer cette fenêtre.</p>
                    </body>
                </html>
                """
            else:
                return (
                    """
                <html>
                    <body style='font-family: Arial; text-align: center; padding: 50px;'>
                        <h2 style='color: red;'>❌ Erreur de connexion</h2>
                        <p>Impossible de se connecter à Spotify.</p>
                    </body>
                </html>
                """,
                    500,
                )
        else:
            return (
                """
            <html>
                <body style='font-family: Arial; text-align: center; padding: 50px;'>
                    <h2 style='color: red;'>❌ Code manquant</h2>
                    <p>Code d'autorisation manquant.</p>
                </body>
            </html>
            """,
                400,
            )

    except Exception as e:
        return (
            f"""
        <html>
            <body style='font-family: Arial; text-align: center; padding: 50px;'>
                <h2 style='color: red;'>❌ Erreur serveur</h2>
                <p>Erreur: {str(e)}</p>
            </body>
        </html>
        """,
            500,
        )


@app.route("/debug/track", methods=["GET"])
def debug_track():
    """Endpoint de debug pour voir les infos de la piste actuelle"""
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


@app.route("/", methods=["GET"])
def index():
    """Page d'accueil avec documentation"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Spotify Color API - Flask</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #1a1a1a; color: #fff; }
            .container { max-width: 800px; margin: 0 auto; }
            h1 { color: #1db954; text-align: center; }
            h2 { color: #1ed760; border-bottom: 2px solid #1ed760; padding-bottom: 10px; }
            .endpoint { background: #2a2a2a; padding: 15px; margin: 10px 0; border-radius: 5px; }
            .method { color: #ffd700; font-weight: bold; }
            .url { color: #87ceeb; font-family: monospace; }
            .description { color: #ddd; margin-top: 5px; }
            .stats { background: #333; padding: 15px; border-radius: 5px; margin: 20px 0; }
            .btn { background: #1db954; color: white; padding: 10px 20px; border: none; border-radius: 5px; text-decoration: none; display: inline-block; margin: 5px; }
            .btn:hover { background: #1ed760; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎵 Spotify Color API - Flask</h1>
            
            <h2>📡 Endpoints Disponibles</h2>
            
            <div class="endpoint">
                <span class="method">GET</span> <span class="url">/color</span>
                <div class="description">Récupère la couleur dominante de la piste actuelle</div>
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span> <span class="url">/infos</span>
                <div class="description">Infos complètes de la piste + couleur dominante</div>
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span> <span class="url">/health</span>
                <div class="description">État de santé du service + statistiques</div>
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span> <span class="url">/debug/track</span>
                <div class="description">Informations de debug détaillées</div>
            </div>
            
            <div class="endpoint">
                <span class="method">GET</span> <span class="url">/spotify/oauth-url</span>
                <div class="description">URL d'authentification Spotify OAuth</div>
            </div>
            
            <h2>🧪 Tests Rapides</h2>
            <a href="/color" class="btn">Tester /color</a>
            <a href="/infos" class="btn">Tester /infos</a>
            <a href="/health" class="btn">Tester /health</a>
            <a href="/debug/track" class="btn">Tester /debug</a>
            
            <div class="stats">
                <h3>📊 Architecture</h3>
                <ul>
                    <li>🐍 Framework: Flask 3.0.3</li>
                    <li>🎨 Extraction: K-means clustering + saturation boost</li>
                    <li>⚡ Cache: Intelligent avec invalidation automatique</li>
                    <li>🔄 Monitoring: Temps réel des changements de piste</li>
                    <li>🔐 Auth: OAuth 2.0 Spotify</li>
                </ul>
            </div>
        </div>
    </body>
    </html>
    """
    return html_content


@app.errorhandler(404)
def not_found(error):
    """Gestionnaire d'erreur 404"""
    return (
        jsonify(
            {
                "status": "error",
                "error": "Endpoint non trouvé",
                "available_endpoints": [
                    "/color",
                    "/infos",
                    "/health",
                    "/debug/track",
                    "/spotify/oauth-url",
                ],
                "timestamp": int(time.time()),
            }
        ),
        404,
    )


@app.errorhandler(500)
def internal_error(error):
    """Gestionnaire d'erreur 500"""
    return (
        jsonify(
            {
                "status": "error",
                "error": "Erreur interne du serveur",
                "timestamp": int(time.time()),
            }
        ),
        500,
    )


if __name__ == "__main__":
    # Configuration de démarrage
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8765))
    debug = os.getenv("FLASK_DEBUG", "False").lower() == "true"

    logging.info(f"🚀 Démarrage du serveur Flask sur {host}:{port}")

    # Initialiser l'extracteur avant le démarrage
    init_extractor()

    try:
        app.run(host=host, port=port, debug=debug)
    except KeyboardInterrupt:
        logging.info("🛑 Arrêt du serveur Flask")
        if extractor and extractor.monitoring_enabled:
            extractor.monitoring_enabled = False
            logging.info("🔌 Surveillance arrêtée")
