#!/usr/bin/env python3
"""
Extracteur de couleurs - Analyse d'images et extraction de couleurs dominantes
"""

import io
import time
import requests
from PIL import Image

class ColorExtractor:
    def __init__(self):
        self.image_cache = {}  # Cache pour les images téléchargées
        self.session = requests.Session()  # Session persistante
        
    def download_image(self, image_url):
        """Télécharger une image depuis une URL"""
        if not image_url:
            return None
            
        # Vérifier le cache d'images
        if image_url in self.image_cache:
            return self.image_cache[image_url]
            
        try:
            response = self.session.get(image_url, timeout=10, stream=True)
            if response.status_code == 200:
                image = Image.open(io.BytesIO(response.content))
                if image.mode != 'RGB':
                    image = image.convert('RGB')
                
                # Mettre en cache (limiter à 10 images max)
                if len(self.image_cache) >= 10:
                    oldest_key = next(iter(self.image_cache))
                    del self.image_cache[oldest_key]
                
                self.image_cache[image_url] = image
                return image
            else:
                return None
        except Exception as e:
            return None
    
    def extract_primary_color(self, image):
        """Extraction couleur NATURELLE mais AMPLIFIÉE"""
        # Redimensionner pour optimiser
        image = image.resize((100, 100), Image.Resampling.LANCZOS)
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        pixels = list(image.getdata())
        
        # Filtrer les pixels trop sombres pour l'analyse
        bright_pixels = []
        for r, g, b in pixels:
            brightness = (r + g + b) / 3
            if brightness > 30:
                bright_pixels.append((r, g, b))
        
        if not bright_pixels:
            bright_pixels = pixels  # Fallback si image très sombre
        
        # 1. ÉTAPE : Trouver la couleur la plus VIBRANTE/SATURÉE
        most_vibrant_color = self._find_most_vibrant_color(bright_pixels)
        
        # 2. ÉTAPE : AMPLIFIER LA SATURATION en préservant la teinte
        return self._amplify_saturation(most_vibrant_color[0], most_vibrant_color[1], most_vibrant_color[2])
    
    def _find_most_vibrant_color(self, pixels):
        """Trouver la couleur la plus vibrante/saturée parmi les pixels"""
        if not pixels:
            return (255, 0, 150)  # Fallback rose
        
        # Analyser les pixels par groupes de couleurs similaires
        color_groups = {}
        
        for r, g, b in pixels:
            # Calculer la saturation de ce pixel
            max_val = max(r, g, b)
            min_val = min(r, g, b)
            
            if max_val == 0:
                saturation = 0
            else:
                saturation = (max_val - min_val) / max_val
            
            # Ignorer les pixels trop peu saturés (gris)
            if saturation < 0.2:
                continue
            
            # Grouper par couleurs similaires (arrondir à des groupes de 20)
            group_key = (r // 20, g // 20, b // 20)
            
            if group_key not in color_groups:
                color_groups[group_key] = {
                    'pixels': [],
                    'saturation_sum': 0,
                    'count': 0
                }
            
            color_groups[group_key]['pixels'].append((r, g, b))
            color_groups[group_key]['saturation_sum'] += saturation
            color_groups[group_key]['count'] += 1
        
        if not color_groups:
            # Fallback : prendre la couleur la plus lumineuse
            brightest_pixel = max(pixels, key=lambda p: sum(p))
            return brightest_pixel
        
        # Trouver le groupe avec la meilleure combinaison fréquence + saturation
        best_group = None
        best_score = 0
        
        for group_key, group_data in color_groups.items():
            avg_saturation = group_data['saturation_sum'] / group_data['count']
            frequency_weight = group_data['count'] / len(pixels)  # Pourcentage réel
            
            # Privilégier la FRÉQUENCE (dominance) avec saturation minimum
            # Score = fréquence principale + saturation comme bonus
            score = frequency_weight * 0.7 + avg_saturation * 0.3
            
            if score > best_score:
                best_score = score
                best_group = group_data
        
        # Calculer la couleur moyenne du meilleur groupe
        if best_group:
            total_r = sum(r for r, g, b in best_group['pixels'])
            total_g = sum(g for r, g, b in best_group['pixels'])
            total_b = sum(b for r, g, b in best_group['pixels'])
            count = len(best_group['pixels'])
            
            return (total_r / count, total_g / count, total_b / count)
        
        # Fallback final
        return (255, 0, 150)
    
    def _amplify_saturation(self, r, g, b):
        """Amplifier LÉGÈREMENT la saturation d'une couleur en préservant sa teinte"""
        # Convertir en HSV pour manipuler la saturation
        max_val = max(r, g, b)
        min_val = min(r, g, b)
        
        # Calculer la saturation actuelle
        if max_val == 0:
            saturation = 0
        else:
            saturation = (max_val - min_val) / max_val
        
        # Amplification DOUCE selon la saturation existante
        if saturation > 0.7:
            # Couleur déjà très saturée : amplification minimale
            boost_factor = 1.1
        elif saturation > 0.4:
            # Couleur moyennement saturée : amplification modérée
            boost_factor = 1.2
        else:
            # Couleur peu saturée : amplification plus forte
            boost_factor = 1.4
        
        # Calculer le centre (gris)
        center = (r + g + b) / 3
        
        # Amplifier en s'éloignant du centre
        new_r = center + (r - center) * boost_factor
        new_g = center + (g - center) * boost_factor
        new_b = center + (b - center) * boost_factor
        
        # S'assurer que les valeurs restent dans les limites
        new_r = max(0, min(255, new_r))
        new_g = max(0, min(255, new_g))
        new_b = max(0, min(255, new_b))
        
        # Éclaircir les couleurs trop sombres pour une meilleure visibilité
        brightness = (new_r + new_g + new_b) / 3
        if brightness < 120:  # Seuil plus élevé pour éviter les couleurs trop sombres
            # Calculer l'éclaircissement nécessaire
            target_brightness = 120
            brightness_boost = (target_brightness - brightness) * 0.8
            
            # Éclaircir tout en préservant les proportions de couleur
            new_r = min(255, new_r + brightness_boost)
            new_g = min(255, new_g + brightness_boost)
            new_b = min(255, new_b + brightness_boost)
        
        return (int(new_r), int(new_g), int(new_b))
