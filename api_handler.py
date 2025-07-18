#!/usr/bin/env python3
"""
Gestionnaire d'API HTTP - Endpoints et routes
"""

import time
import json
import logging
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, urlencode

class APIHandler(BaseHTTPRequestHandler):
    def __init__(self, request, client_address, server, extractor):
        self.extractor = extractor
        super().__init__(request, client_address, server)
    
    def log_message(self, format, *args):
        """Logging HTTP minimal"""
        pass  # Désactiver les logs HTTP
    
    def do_GET(self):
        start_time = time.time()
        
        if self.path == '/color':
            self._handle_color_endpoint(start_time)
        elif self.path == '/infos':
            self._handle_infos_endpoint(start_time)
        elif self.path == '/health':
            self._handle_health_endpoint()
        elif self.path == '/spotify/oauth-url':
            self._handle_oauth_url_endpoint()
        elif self.path.startswith('/spotify/callback'):
            self._handle_spotify_callback()
        elif self.path == '/debug/track':
            self._handle_debug_track_endpoint()
        else:
            self._send_json_response(404, {"error": "Not found"})
    
    def _handle_color_endpoint(self, start_time):
        """Endpoint pour récupérer la couleur dominante"""
        try:
            color = self.extractor.extract_color()
            response = {
                "status": "success",
                "color": {
                    "r": color[0],
                    "g": color[1],
                    "b": color[2],
                    "hex": f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}"
                },
                "timestamp": int(time.time()),
                "processing_time_ms": int((time.time() - start_time) * 1000)
            }
            self._send_json_response(200, response)
        except Exception as e:
            response = {
                "status": "error",
                "error": str(e),
                "color": {"r": 100, "g": 200, "b": 255, "hex": "#64c8ff"},
                "timestamp": int(time.time())
            }
            self._send_json_response(500, response)
    
    def _handle_infos_endpoint(self, start_time):
        """Endpoint pour récupérer les infos de la piste + couleur"""
        try:
            track_info = self.extractor.get_current_track_info()
            if track_info and track_info.get('id'):
                # Extraire la couleur pour cette piste
                color = self.extractor.extract_color()
                
                response = {
                    "status": "success",
                    "track": {
                        "id": track_info.get('id'),
                        "title": track_info.get('name'),
                        "artist": track_info.get('artist'),
                        "album": track_info.get('album'),
                        "image_url": track_info.get('image_url'),
                        "duration_ms": track_info.get('duration_ms'),
                        "progress_ms": track_info.get('progress_ms'),
                        "is_playing": track_info.get('is_playing', False)
                    },
                    "color": {
                        "r": color[0],
                        "g": color[1],
                        "b": color[2],
                        "hex": f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}"
                    },
                    "timestamp": int(time.time()),
                    "processing_time_ms": int((time.time() - start_time) * 1000)
                }
            else:
                # Pas de musique, retourner les infos par défaut
                fallback_color = self.extractor._get_fallback_color()
                response = {
                    "status": "no_track",
                    "track": {
                        "id": None,
                        "title": "Aucune musique",
                        "artist": "Spotify",
                        "album": "Pas de lecture en cours",
                        "image_url": None,
                        "duration_ms": 0,
                        "progress_ms": 0,
                        "is_playing": False
                    },
                    "color": {
                        "r": fallback_color[0],
                        "g": fallback_color[1],
                        "b": fallback_color[2],
                        "hex": f"#{fallback_color[0]:02x}{fallback_color[1]:02x}{fallback_color[2]:02x}"
                    },
                    "timestamp": int(time.time()),
                    "processing_time_ms": int((time.time() - start_time) * 1000)
                }
            self._send_json_response(200, response)
        except Exception as e:
            fallback_color = (100, 200, 255)
            response = {
                "status": "error",
                "error": str(e),
                "track": {
                    "id": None,
                    "title": "Erreur",
                    "artist": "Système",
                    "album": "Erreur de récupération",
                    "image_url": None,
                    "duration_ms": 0,
                    "progress_ms": 0,
                    "is_playing": False
                },
                "color": {
                    "r": fallback_color[0],
                    "g": fallback_color[1],
                    "b": fallback_color[2],
                    "hex": "#64c8ff"
                },
                "timestamp": int(time.time())
            }
            self._send_json_response(500, response)
    
    def _handle_health_endpoint(self):
        """Endpoint de santé du service"""
        response = {
            "status": "healthy",
            "service": "spotify-color-api-modular",
            "stats": self.extractor.get_stats(),
            "timestamp": int(time.time())
        }
        self._send_json_response(200, response)
    
    def _handle_oauth_url_endpoint(self):
        """Endpoint pour générer l'URL d'OAuth Spotify"""
        if self.extractor.spotify_client_id:
            params = {
                'client_id': self.extractor.spotify_client_id,
                'response_type': 'code',
                'redirect_uri': 'http://192.168.1.9:8765/spotify/callback',
                'scope': 'user-read-currently-playing user-read-playback-state',
                'state': 'spotify-color-api'
            }
            oauth_url = f"https://accounts.spotify.com/authorize?{urlencode(params)}"
            response = {"status": "success", "oauth_url": oauth_url}
            self._send_json_response(200, response)
        else:
            response = {"status": "error", "message": "Client ID non configuré"}
            self._send_json_response(400, response)
    
    def _handle_spotify_callback(self):
        """Gérer le callback OAuth Spotify"""
        try:
            parsed_url = urlparse(self.path)
            params = parse_qs(parsed_url.query)
            
            if 'code' in params:
                authorization_code = params['code'][0]
                
                if self.extractor.exchange_code_for_tokens(authorization_code):
                    html_content = """
                    <html><body>
                    <h1>✅ Authentification réussie!</h1>
                    <p>Vous pouvez fermer cette fenêtre.</p>
                    <p>La surveillance des changements de musique est maintenant active.</p>
                    </body></html>
                    """
                    self._send_html_response(200, html_content)
                else:
                    html_content = """
                    <html><body>
                    <h1>❌ Erreur d'authentification</h1>
                    <p>Veuillez réessayer.</p>
                    </body></html>
                    """
                    self._send_html_response(400, html_content)
            else:
                html_content = """
                <html><body>
                <h1>❌ Code d'autorisation manquant</h1>
                </body></html>
                """
                self._send_html_response(400, html_content)
                
        except Exception as e:
            html_content = f"""
            <html><body>
            <h1>❌ Erreur</h1>
            <p>{str(e)}</p>
            </body></html>
            """
            self._send_html_response(500, html_content)
    
    def _handle_debug_track_endpoint(self):
        """Endpoint de debug pour voir les infos de la piste actuelle"""
        try:
            track_info = self.extractor.get_current_track_info()
            if track_info:
                response = {
                    "status": "success",
                    "track": track_info,
                    "has_image": bool(track_info.get('image_url')),
                    "current_track_id": self.extractor.current_track_id,
                    "current_image_url": self.extractor.current_track_image_url
                }
            else:
                response = {
                    "status": "no_track",
                    "message": "Aucune musique en cours de lecture",
                    "spotify_enabled": self.extractor.spotify_enabled
                }
            self._send_json_response(200, response)
        except Exception as e:
            response = {
                "status": "error",
                "error": str(e),
                "spotify_enabled": self.extractor.spotify_enabled
            }
            self._send_json_response(500, response)
    
    def _send_json_response(self, status_code, data):
        """Envoyer une réponse JSON"""
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        
        json_response = json.dumps(data, indent=2)
        self.wfile.write(json_response.encode('utf-8'))
    
    def _send_html_response(self, status_code, content):
        """Envoyer une réponse HTML"""
        self.send_response(status_code)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(content.encode('utf-8'))


def create_handler_class(extractor):
    """Factory pour créer une classe handler avec l'extractor injecté"""
    class ColorAPIHandler(APIHandler):
        def __init__(self, request, client_address, server):
            super().__init__(request, client_address, server, extractor)
    
    return ColorAPIHandler
