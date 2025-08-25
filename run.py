#!/usr/bin/env python3
import os
import logging

from app import create_app


def main():
    app = create_app()
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8765))
    debug = os.getenv("FLASK_DEBUG", "False").lower() == "true"

    logging.info(f"🚀 Démarrage du serveur Flask sur {host}:{port}")
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    main()
