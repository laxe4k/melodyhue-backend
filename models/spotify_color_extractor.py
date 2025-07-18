#!/usr/bin/env python3
"""
Extracteur de couleurs Spotify - Combine client Spotify et extraction de couleurs
"""

import time
import logging
import threading
from .spotify_client import SpotifyClient
from .color_extractor import ColorExtractor

class SpotifyColorExtractor:
    def __init__(self, data_dir='./data'):
        # Initialiser les composants
        self.spotify_client = SpotifyClient(data_dir)
        self.color_extractor = ColorExtractor()
        
        # État actuel
        self.current_track_image_url = None
        self.current_track_id = None
        
        # Cache et configuration
        self.color_cache = {}
        self.last_extraction_time = 0
        self.cache_duration = 5
        
        # Surveillance
        self.monitoring_enabled = True
        self.monitoring_thread = None
        self.spotify_check_interval = 1
        self.last_spotify_check = 0
        
        # Stats
        self.stats = {'requests': 0, 'cache_hits': 0, 'extractions': 0, 'errors': 0}
        
        # Démarrer la surveillance
        self.start_monitoring()
    
    def start_monitoring(self):
        """Démarrer la surveillance des changements de musique"""
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            return
        
        self.monitoring_enabled = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        logging.info("⚡ Surveillance active - Logs réduits")
    
    def _monitoring_loop(self):
        """Surveillance silencieuse - logs seulement les changements"""
        last_track_id = None
        last_is_playing = None
        
        while self.monitoring_enabled:
            try:
                current_time = time.time()
                
                if (self.spotify_client.spotify_enabled and 
                    current_time - self.last_spotify_check >= self.spotify_check_interval):
                    
                    track_info = self.spotify_client.get_current_track()
                    self.last_spotify_check = current_time
                    
                    if track_info:
                        current_track_id = track_info.get('id')
                        current_is_playing = track_info.get('is_playing', False)
                        
                        # 1. ÉVÉNEMENT : Changement de piste
                        if last_track_id != current_track_id and current_track_id:
                            logging.info(f"🎵 {track_info.get('artist', 'Unknown')} - {track_info.get('name', 'Unknown')}")
                            self.current_track_image_url = track_info.get('image_url')
                            self.current_track_id = current_track_id
                            self.color_cache.clear()
                            new_color = self.extract_color()
                            logging.info(f"🎨 #{new_color[0]:02x}{new_color[1]:02x}{new_color[2]:02x}")
                            last_track_id = current_track_id
                        
                        # 2. ÉVÉNEMENT : Changement état lecture (play/pause)
                        if last_is_playing != current_is_playing:
                            if current_is_playing:
                                logging.info(f"▶️ {track_info.get('artist', 'Unknown')} - {track_info.get('name', 'Unknown')}")
                                if self.current_track_id != current_track_id:
                                    self.current_track_image_url = track_info.get('image_url')
                                    self.current_track_id = current_track_id
                                    self.color_cache.clear()
                                new_color = self.extract_color()
                                logging.info(f"🎨 #{new_color[0]:02x}{new_color[1]:02x}{new_color[2]:02x}")
                            else:
                                logging.info("⏸️ PAUSE")
                            last_is_playing = current_is_playing
                    else:
                        # Reset silencieux si plus de musique
                        if last_track_id is not None or last_is_playing is not None:
                            logging.info("🔇 STOP")
                            last_track_id = None
                            last_is_playing = None
                
                time.sleep(1)
                
            except Exception as e:
                logging.error(f"❌ Erreur monitoring: {e}")
                time.sleep(10)
    
    def extract_color(self):
        """Extraction couleur dominante depuis la pochette d'album"""
        current_time = time.time()
        self.stats['requests'] += 1
        
        # Vérifier d'abord si la musique est en pause
        track_info = self.spotify_client.get_current_track()
        if track_info and not track_info.get('is_playing', False):
            # Retourner la couleur de pause #53ac6a
            return (83, 172, 106)
        
        # Cache check basé sur l'ID de la piste
        cache_key = f"color_{self.current_track_id}"
        if (cache_key in self.color_cache and 
            current_time - self.last_extraction_time < self.cache_duration):
            self.stats['cache_hits'] += 1
            return self.color_cache[cache_key]
        
        self.stats['extractions'] += 1
        
        try:
            # Si pas d'image URL, récupérer les infos de la piste actuelle
            if not self.current_track_image_url:
                if track_info and track_info.get('image_url'):
                    self.current_track_image_url = track_info['image_url']
                    self.current_track_id = track_info.get('id')
                else:
                    return self._get_fallback_color()
            
            if not self.current_track_image_url:
                return self._get_fallback_color()
            
            # Télécharger et analyser la pochette
            image = self.color_extractor.download_image(self.current_track_image_url)
            if not image:
                return self._get_fallback_color()
            
            color = self.color_extractor.extract_primary_color(image)
            
            # Mettre en cache
            if self.current_track_id:
                cache_key = f"color_{self.current_track_id}"
                self.color_cache[cache_key] = color
            
            self.last_extraction_time = current_time
            return color
            
        except Exception as e:
            self.stats['errors'] += 1
            logging.error(f"❌ Erreur extraction couleur: {e}")
            return self._get_fallback_color()
    
    def _get_fallback_color(self):
        """Couleur de fallback FLASHY"""
        # Chercher dans le cache une couleur récente
        for key in self.color_cache:
            if key.startswith("color_"):
                return self.color_cache[key]
        return (255, 0, 150)  # Rose FLASHY par défaut
    
    def get_current_track_info(self):
        """Obtenir les infos de la piste actuelle"""
        return self.spotify_client.get_current_track()
    
    def get_stats(self):
        """Retourner les statistiques"""
        return self.stats
    
    def exchange_code_for_tokens(self, authorization_code):
        """Échanger le code d'autorisation contre des tokens"""
        return self.spotify_client.exchange_code_for_tokens(authorization_code)
    
    @property
    def spotify_client_id(self):
        """Accès au client ID Spotify"""
        return self.spotify_client.spotify_client_id
    
    @property
    def spotify_enabled(self):
        """Statut de l'API Spotify"""
        return self.spotify_client.spotify_enabled
