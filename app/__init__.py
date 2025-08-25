#!/usr/bin/env python3
"""
Initialisation de l'application Flask (factory)
"""

import os
import logging
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv

# Imports locaux
from .models import SpotifyColorExtractor


def create_app() -> Flask:
    """Créer et configurer l'application Flask.

    - Charge les variables d'environnement
    - Configure CORS
    - Initialise l'extracteur et l'attache à l'app (app.extensions['extractor'])
    - Enregistre les blueprints
    """
    # Charger .env
    load_dotenv()

    # Configuration du logging minimal
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    app = Flask(__name__)
    CORS(app)

    # Config
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key")
    app.config["DATA_DIR"] = os.getenv("DATA_DIR", "./data")

    # Initialiser l'extracteur et l'attacher à l'app
    extractor = SpotifyColorExtractor(app.config["DATA_DIR"])
    app.extensions = getattr(app, "extensions", {})
    app.extensions["extractor"] = extractor
    logging.info("✅ Extracteur de couleurs initialisé")

    # Log d'accueil
    print("🎵 SPOTIFY COLOR API - VERSION FLASK")
    print("=====================================")
    print("📁 Architecture: Flask + Blueprints")
    print(f"📡 Port: {os.getenv('PORT', 8765)}")
    print("🎨 Style: FLASHY - Couleurs vives et saturées")
    print("🎯 Endpoints: /color, /infos, /health, /debug/track")
    print("=====================================")

    # Enregistrer les blueprints
    from .controllers.defaultController import bp as default_bp

    app.register_blueprint(default_bp)

    return app
