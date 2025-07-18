#!/usr/bin/env python3
"""
Spotify Color API - Point d'entrée principal
Version modulaire avec architecture propre
"""

import os
import logging
from http.server import HTTPServer
from dotenv import load_dotenv

# Imports locaux
from models import SpotifyColorExtractor
from api_handler import create_handler_class

# Charger les variables d'environnement
load_dotenv()

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def main():
    """Fonction principale du serveur"""
    print("🎵 SPOTIFY COLOR API - VERSION MODULAIRE")
    print("=========================================")
    print("📁 Architecture: Modular & Clean")
    print("📡 Port: 8765")
    print("🎨 Style: FLASHY - Couleurs vives et saturées")
    print("🔇 Logs: MINIMAL - seulement les changements")
    print("🎯 Endpoints: /color, /infos, /health, /debug/track")
    print("=========================================")
    
    # Configurer le répertoire de données
    data_dir = os.getenv('DATA_DIR', './data')
    
    # Initialiser l'extracteur principal
    extractor = SpotifyColorExtractor(data_dir)
    
    # Créer la classe handler avec l'extracteur injecté
    handler_class = create_handler_class(extractor)
    
    # Configurer le serveur
    port = int(os.getenv('PORT', 8765))
    server = HTTPServer(('0.0.0.0', port), handler_class)
    
    logging.info(f"✅ Serveur démarré sur 0.0.0.0:{port}")
    logging.info("🎨 Mode couleurs FLASHY activé")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logging.info("🛑 Arrêt du serveur")
        server.shutdown()
        
    # Arrêter la surveillance
    if extractor.monitoring_enabled:
        extractor.monitoring_enabled = False
        logging.info("🔌 Surveillance arrêtée")

if __name__ == "__main__":
    main()
