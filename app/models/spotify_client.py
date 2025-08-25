#!/usr/bin/env python3
"""
Client Spotify API - Gestion des tokens et requêtes
"""

import os
import time
import json
import base64
import logging
import requests
from dotenv import load_dotenv

load_dotenv()


class SpotifyClient:
    def __init__(self, data_dir="./data"):
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)
        self.tokens_file = os.path.join(self.data_dir, "spotify_tokens.json")

        # Créer le fichier tokens s'il n'existe pas
        if not os.path.exists(self.tokens_file):
            with open(self.tokens_file, "w", encoding="utf-8") as f:
                json.dump({}, f)

        # Spotify API credentials
        self.spotify_client_id = None
        self.spotify_client_secret = None
        self.spotify_access_token = None
        self.spotify_refresh_token = None
        self.spotify_token_expires = 0
        self.spotify_enabled = False
        self.spotify_api_errors = 0
        self.max_spotify_errors = 5
        self.redirect_uri = os.getenv(
            "SPOTIFY_REDIRECT_URI", "http://localhost:8765/spotify/callback"
        )

        # Cache pour éviter les appels répétés
        self._last_spotify_check = 0
        self._last_spotify_result = None

        # Auto-configuration
        self._setup_spotify()

    def _setup_spotify(self):
        """Configuration Spotify automatique"""
        client_id = os.getenv("SPOTIFY_CLIENT_ID")
        client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")

        # Fallback: charger depuis data/spotify_config.json
        if not client_id or not client_secret:
            try:
                cfg_path = os.path.join(self.data_dir, "spotify_config.json")
                if os.path.exists(cfg_path):
                    with open(cfg_path, "r", encoding="utf-8") as f:
                        cfg = json.load(f)
                        client_id = client_id or cfg.get("client_id")
                        client_secret = client_secret or cfg.get("client_secret")
                        if cfg.get("redirect_uri"):
                            self.redirect_uri = cfg["redirect_uri"]
            except Exception:
                pass

        if client_id and client_secret:
            refresh_token = self._load_refresh_token()
            if self.configure_spotify_api(client_id, client_secret, refresh_token):
                if self._test_spotify_api():
                    logging.info("✅ Spotify API connectée")
                    return True

        logging.warning("⚠️ Spotify API non configurée")
        return False

    def configure_spotify_api(self, client_id, client_secret, refresh_token=None):
        """Configurer l'API Spotify"""
        self.spotify_client_id = client_id
        self.spotify_client_secret = client_secret
        self.spotify_refresh_token = refresh_token

        if self._get_spotify_access_token():
            self.spotify_enabled = True
            return True
        return False

    def _load_refresh_token(self):
        """Charger le refresh token depuis le fichier JSON"""
        try:
            if os.path.exists(self.tokens_file):
                with open(self.tokens_file, "r", encoding="utf-8") as f:
                    tokens = json.load(f)
                    return tokens.get("refresh_token")
        except Exception as e:
            logging.error(f"Error loading refresh token: {e}")
        return None

    def _save_tokens(self, access_token, refresh_token=None, expires_in=3600):
        """Sauvegarder les tokens dans le fichier JSON"""
        try:
            tokens = {
                "access_token": access_token,
                "expires_at": time.time() + expires_in,
                "created_at": time.time(),
                "last_updated": time.time(),
            }

            if refresh_token:
                tokens["refresh_token"] = refresh_token

            # Conserver le refresh token existant s'il n'y en a pas de nouveau
            if not refresh_token and os.path.exists(self.tokens_file):
                try:
                    with open(self.tokens_file, "r", encoding="utf-8") as f:
                        existing_tokens = json.load(f)
                        if existing_tokens.get("refresh_token"):
                            tokens["refresh_token"] = existing_tokens["refresh_token"]
                except Exception:
                    # Tolérer un JSON corrompu, on réécrira plus tard
                    pass

            with open(self.tokens_file, "w", encoding="utf-8") as f:
                json.dump(tokens, f, indent=2, ensure_ascii=False)

            return True
        except Exception:
            return False

    def _load_access_token(self):
        """Charger l'access token depuis le fichier JSON si encore valide"""
        try:
            if os.path.exists(self.tokens_file):
                with open(self.tokens_file, "r", encoding="utf-8") as f:
                    tokens = json.load(f)

                    access_token = tokens.get("access_token")
                    expires_at = tokens.get("expires_at", 0)

                    if access_token and time.time() < (expires_at - 300):
                        self.spotify_access_token = access_token
                        self.spotify_token_expires = expires_at
                        return True
            return False
        except Exception:
            return False

    def _get_spotify_access_token(self):
        """Obtenir un token d'accès Spotify"""
        if self._load_access_token():
            return True

        try:
            if self.spotify_refresh_token:
                success = self._refresh_access_token()
                if success:
                    return True

            # Client Credentials Flow
            auth_string = f"{self.spotify_client_id}:{self.spotify_client_secret}"
            auth_bytes = auth_string.encode("utf-8")
            auth_base64 = base64.b64encode(auth_bytes).decode("utf-8")

            url = "https://accounts.spotify.com/api/token"
            headers = {
                "Authorization": f"Basic {auth_base64}",
                "Content-Type": "application/x-www-form-urlencoded",
            }
            data = {"grant_type": "client_credentials"}

            response = requests.post(url, headers=headers, data=data, timeout=10)

            if response.status_code == 200:
                token_data = response.json()
                self.spotify_access_token = token_data["access_token"]
                expires_in = token_data.get("expires_in", 3600)
                self.spotify_token_expires = time.time() + expires_in - 60
                self._save_tokens(self.spotify_access_token, expires_in=expires_in)
                return True

            return False
        except Exception:
            return False

    def _refresh_access_token(self):
        """Rafraîchir l'access token avec le refresh token"""
        try:
            auth_string = f"{self.spotify_client_id}:{self.spotify_client_secret}"
            auth_bytes = auth_string.encode("utf-8")
            auth_base64 = base64.b64encode(auth_bytes).decode("utf-8")

            url = "https://accounts.spotify.com/api/token"
            headers = {
                "Authorization": f"Basic {auth_base64}",
                "Content-Type": "application/x-www-form-urlencoded",
            }
            data = {
                "grant_type": "refresh_token",
                "refresh_token": self.spotify_refresh_token,
            }

            response = requests.post(url, headers=headers, data=data, timeout=10)

            if response.status_code == 200:
                token_data = response.json()
                self.spotify_access_token = token_data["access_token"]
                expires_in = token_data.get("expires_in", 3600)
                self.spotify_token_expires = time.time() + expires_in - 60

                new_refresh_token = token_data.get("refresh_token")
                if new_refresh_token:
                    self.spotify_refresh_token = new_refresh_token

                self._save_tokens(
                    self.spotify_access_token,
                    new_refresh_token or self.spotify_refresh_token,
                    expires_in,
                )
                return True

            return False
        except Exception:
            return False

    def _test_spotify_api(self):
        """Tester la connectivité de l'API Spotify"""
        if not self.spotify_enabled:
            return False

        try:
            headers = {
                "Authorization": f"Bearer {self.spotify_access_token}",
                "Content-Type": "application/json",
            }

            if self.spotify_refresh_token:
                response = requests.get(
                    "https://api.spotify.com/v1/me/player/currently-playing",
                    headers=headers,
                    timeout=5,
                )
                return response.status_code in [200, 204]
            else:
                response = requests.get(
                    "https://api.spotify.com/v1/browse/categories",
                    headers=headers,
                    params={"limit": 1},
                    timeout=5,
                )
                return response.status_code == 200
        except:
            return False

    def get_current_track(self):
        """Obtenir les informations de la piste actuelle"""
        if not self.spotify_enabled:
            return None

        # Cache ultra rapide pour éviter les appels répétés
        now = time.time()
        if now - self._last_spotify_check < 1:  # Cache 1 seconde
            return self._last_spotify_result

        self._last_spotify_check = now

        try:
            if time.time() > self.spotify_token_expires:
                self._get_spotify_access_token()

            headers = {
                "Authorization": f"Bearer {self.spotify_access_token}",
                "Content-Type": "application/json",
            }

            if self.spotify_refresh_token:
                response = requests.get(
                    "https://api.spotify.com/v1/me/player/currently-playing",
                    headers=headers,
                    timeout=3,
                )

                if response.status_code == 200:
                    data = response.json()
                    if data and data.get("item"):
                        track = data["item"]
                        # Récupérer l'URL de la pochette en haute résolution
                        image_url = None
                        if track.get("album", {}).get("images"):
                            images = track["album"]["images"]
                            image_url = images[0]["url"]

                        track_info = {
                            "id": track["id"],
                            "name": track["name"],
                            "artist": ", ".join(
                                [artist["name"] for artist in track["artists"]]
                            ),
                            "album": track["album"]["name"],
                            "duration_ms": track["duration_ms"],
                            "progress_ms": data.get("progress_ms", 0),
                            "is_playing": data.get("is_playing", False),
                            "image_url": image_url,
                            "timestamp": time.time(),
                        }
                        self.spotify_api_errors = 0
                        self._last_spotify_result = track_info
                        return track_info

                elif response.status_code == 204:
                    self.spotify_api_errors = 0
                    result = {
                        "id": None,
                        "name": "No music playing",
                        "is_playing": False,
                    }
                    self._last_spotify_result = result
                    return result
                else:
                    self.spotify_api_errors += 1
                    self._last_spotify_result = None
                    return None
            else:
                self._last_spotify_result = None
                return None
        except Exception:
            self.spotify_api_errors += 1
            self._last_spotify_result = None
            return None

    def exchange_code_for_tokens(self, authorization_code):
        """Échanger le code d'autorisation contre des tokens"""
        try:
            auth_string = f"{self.spotify_client_id}:{self.spotify_client_secret}"
            auth_bytes = auth_string.encode("utf-8")
            auth_base64 = base64.b64encode(auth_bytes).decode("utf-8")

            url = "https://accounts.spotify.com/api/token"
            headers = {
                "Authorization": f"Basic {auth_base64}",
                "Content-Type": "application/x-www-form-urlencoded",
            }
            data = {
                "grant_type": "authorization_code",
                "code": authorization_code,
                "redirect_uri": self.redirect_uri,
            }

            response = requests.post(url, headers=headers, data=data, timeout=10)

            if response.status_code == 200:
                token_data = response.json()

                self.spotify_access_token = token_data["access_token"]
                self.spotify_refresh_token = token_data.get("refresh_token")
                expires_in = token_data.get("expires_in", 3600)
                self.spotify_token_expires = time.time() + expires_in - 60

                self._save_tokens(
                    self.spotify_access_token, self.spotify_refresh_token, expires_in
                )

                # Activer Spotify après autorisation utilisateur
                self.spotify_enabled = True

                logging.info("🎉 Tokens OAuth sauvegardés!")
                return True
            else:
                return False
        except Exception:
            return False

    # === Helpers OAuth pour l'API ===
    def get_auth_url(self):
        """Générer l'URL d'authentification Spotify OAuth."""
        if not self.spotify_client_id:
            return None
        params = {
            "client_id": self.spotify_client_id,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            # Scopes requis pour lire la musique actuelle
            "scope": "user-read-currently-playing user-read-playback-state",
            "show_dialog": "false",
        }
        return f"https://accounts.spotify.com/authorize?{requests.compat.urlencode(params)}"

    def handle_callback(self, code: str) -> bool:
        """Traiter le callback OAuth (échange du code)."""
        if not code:
            return False
        return self.exchange_code_for_tokens(code)

    def is_authenticated(self) -> bool:
        """Retourne True si l'API est configurée et dispose d'un refresh token ou d'un access token valide."""
        if not self.spotify_enabled:
            return False
        if self.spotify_refresh_token:
            return True
        # Sinon, vérifier access token actuel
        return bool(
            self.spotify_access_token and time.time() < self.spotify_token_expires
        )

    def logout(self) -> bool:
        """Déconnecter l’utilisateur: supprimer tokens et remettre l’état à zéro."""
        try:
            # Effacer tokens en mémoire
            self.spotify_access_token = None
            self.spotify_refresh_token = None
            self.spotify_token_expires = 0
            self._last_spotify_result = None
            # Vider fichier tokens
            try:
                if os.path.exists(self.tokens_file):
                    with open(self.tokens_file, "w", encoding="utf-8") as f:
                        json.dump({}, f)
            except Exception:
                pass
            return True
        except Exception:
            return False
