#!/usr/bin/env python3
"""
Initialisation de l'application Flask (factory)
"""

import logging
import os
from datetime import datetime
from urllib.parse import quote_plus as urlquote

from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS
from .extensions import db, migrate
import wtforms_json

# Imports locaux
from .services import SpotifyColorExtractor
from .services.github_version_service import (
    get_latest_release_version,
    get_repo_created_year,
    get_repo_owner_login,
)


def create_app() -> Flask:
    """Créer et configurer l'application Flask.

    - Charge les variables d'environnement
    - Configure CORS
    - Initialise l'extracteur et l'attache à l'app (app.extensions['extractor'])
    - Enregistre les blueprints
    """
    # Charger .env
    load_dotenv()
    # Activer WTForms-JSON
    wtforms_json.init()

    # Configuration du logging minimal
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    # Définir le dossier des templates sous app/views/templates
    app = Flask(__name__, template_folder="views/templates")
    CORS(app)

    # Config
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key")
    # Version de l'application (affichée dans le footer)
    # Version affichée dans l'UI: par défaut release GitHub; fallback env/valeur dev
    gh_version = get_latest_release_version() or None
    env_version = os.getenv("APP_VERSION") or os.getenv("VERSION")
    app.config["APP_VERSION"] = gh_version or env_version or "0.0.0-dev"
    # Année de création du dépôt pour le © (fallback: année courante si non dispo)
    created_year = get_repo_created_year() or None
    app.config["CREATED_YEAR"] = created_year
    # Propriétaire du repo (pour ©)
    app.config["REPO_OWNER"] = (
        get_repo_owner_login() or os.getenv("REPO_OWNER") or "Laxe4k"
    )
    # Forcer la sortie JSON en UTF-8 (ne pas échapper les accents)
    app.config["JSON_AS_ASCII"] = False
    try:
        # Flask >= 2.2: JSON provider
        app.json.ensure_ascii = False  # type: ignore[attr-defined]
    except Exception:
        pass

    # DB config
    # Priorité: DATABASE_URL > paramètres DB_* ; aucun fallback SQLite
    db_uri = os.getenv("DATABASE_URL")
    if not db_uri:
        db_host = os.getenv("DB_HOST")
        db_name = os.getenv("DB_DATABASE")
        db_user = os.getenv("DB_USER")
        db_password = os.getenv("DB_PASSWORD")
        db_port = os.getenv("DB_PORT", "3306")
        db_driver = os.getenv("DB_DRIVER", "mysql+pymysql")

        if all([db_host, db_name, db_user, db_password]):
            # Encoder le mot de passe pour supporter les caractères spéciaux (@,!,#,...)
            enc_pwd = urlquote(db_password)
            db_uri = f"{db_driver}://{db_user}:{enc_pwd}@{db_host}:{db_port}/{db_name}?charset=utf8mb4"
            logging.info("Base de données configurée via variables DB_* (non-SQLite)")
        else:
            raise RuntimeError(
                "Configuration base de données manquante. Définissez DATABASE_URL ou DB_HOST/DB_DATABASE/DB_USER/DB_PASSWORD."
            )

    app.config["SQLALCHEMY_DATABASE_URI"] = db_uri
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Init DB et migrations
    db.init_app(app)
    migrate.init_app(app, db)

    # Importer les modèles afin que les métadonnées soient disponibles pour les migrations
    # (sinon, `flask db migrate` peut générer une révision vide)
    try:
        from .models import user_model  # noqa: F401
        from .models import spotify_credential_model  # noqa: F401
    except Exception as e:
        logging.warning(f"Impossible d'importer les modèles lors de l'init: {e}")

    # Initialiser l'extracteur et l'attacher à l'app
    extractor = SpotifyColorExtractor()
    app.extensions = getattr(app, "extensions", {})
    app.extensions["extractor"] = extractor
    logging.info("✅ Extracteur de couleurs initialisé")

    # Cache extracteurs par utilisateur
    app.extensions["user_extractors"] = {}

    # Enregistrer les blueprints par domaine
    from .controllers.pages_controller import bp as pages_bp
    from .controllers.spotify_controller import bp as spotify_bp
    from .controllers.auth_controller import bp as auth_bp
    from .controllers.user_controller import bp as user_bp

    app.register_blueprint(pages_bp)
    app.register_blueprint(spotify_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp)

    # Rendre la version et l'année courante disponibles dans tous les templates
    @app.context_processor
    def inject_globals():  # noqa: D401
        return {
            "APP_VERSION": app.config.get("APP_VERSION", "0.0.0-dev"),
            "CURRENT_YEAR": datetime.utcnow().year,
            "CREATED_YEAR": app.config.get("CREATED_YEAR") or datetime.utcnow().year,
            "REPO_OWNER": app.config.get("REPO_OWNER", "Laxe4k"),
        }

    return app
