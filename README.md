# Spotify Info & Color API

🎵 **API d'extraction de couleur dominante et d'infos musicales à partir de Spotify**

---

## 🏗️ Structure du Projet

```
spotify_color_api/
├── main.py                 # Point d'entrée principal
├── api_handler.py          # Gestionnaire des endpoints HTTP
├── models/                 # Modules métier
│   ├── __init__.py
│   ├── spotify_client.py   # Client API Spotify
│   ├── color_extractor.py  # Extracteur de couleurs
│   └── spotify_color_extractor.py  # Orchestrateur principal
├── app.py.old              # Version monolithique (archivée)
├── requirements.txt        # Dépendances Python
├── .env                    # Variables d'environnement
├── .gitignore              # Fichiers ignorés
├── docker-compose.yml      # Configuration Docker
├── Dockerfile.optimized    # Image Docker
├── LICENSE                 # Licence MIT
└── data/                   # Données persistantes
    └── spotify_tokens.json
```

---

## 🚀 Démarrage

### 1. Installation des dépendances
```bash
pip install -r requirements.txt
```

### 2. Configuration
Créez un fichier `.env` avec vos identifiants Spotify :
```env
SPOTIFY_CLIENT_ID=your_client_id
SPOTIFY_CLIENT_SECRET=your_client_secret
PORT=8765
DATA_DIR=./data
```

### 3. Lancement du serveur
```bash
python main.py
```

### 4. Version legacy (archive)
```bash
python app.py.old
```

---

## 📦 Modules

### `main.py`
- Point d'entrée principal
- Configuration du serveur HTTP
- Initialisation des composants
- Gestion du cycle de vie de l'application

### `api_handler.py`
- Routage des requêtes HTTP
- Sérialisation/désérialisation JSON
- Gestion des erreurs HTTP
- Endpoints OAuth Spotify

### `models/spotify_client.py`
- Authentification OAuth 2.0
- Gestion des tokens (refresh automatique)
- Récupération des informations de piste
- Cache des requêtes API

### `models/color_extractor.py`
- Téléchargement d'images
- Analyse des pixels
- Algorithme de couleur dominante
- Amplification de saturation

### `models/spotify_color_extractor.py`
- Coordination entre Spotify et extraction
- Surveillance des changements de musique
- Gestion du cache couleurs
- Statistiques d'utilisation

---

## � Endpoints

| Endpoint                | Méthode | Description                                 |
|------------------------|---------|---------------------------------------------|
| `/color`               | GET     | Couleur dominante actuelle                  |
| `/infos`               | GET     | Infos complètes (piste + couleur)           |
| `/health`              | GET     | Santé du service + statistiques             |
| `/debug/track`         | GET     | Infos de debug                             |
| `/spotify/oauth-url`   | GET     | URL d'authentification OAuth                |
| `/spotify/callback`    | GET     | Callback OAuth                             |

---

## 📊 Fonctionnalités

- **Extraction couleur intelligente** : Algorithme optimisé
- **Surveillance temps réel** : Détection automatique des changements
- **Cache performant** : Évite les recalculs inutiles
- **Authentification OAuth** : Intégration Spotify sécurisée
- **Architecture propre** : Code modulaire et maintenable
- **Déploiement Docker** : Prêt pour la production

---

## 🎨 Algorithme de Couleur

- Analyse par clusters (groupement des couleurs similaires)
- Score hybride : 70% fréquence + 30% saturation
- Amplification naturelle : Préservation des teintes originales
- Seuil de luminosité : Couleurs visibles pour l'UI
- Cache intelligent : Limite les appels API

---

## � Déploiement Docker

### Build et démarrage
```bash
docker-compose up --build
```

### Ou avec Docker uniquement
```bash
docker build -f Dockerfile.optimized -t spotify-color-api .
docker run -p 8765:8765 spotify-color-api
```

---

## 📈 Monitoring

### Statistiques en temps réel
```bash
curl http://localhost:8765/health
```

### Logs structurés
```
2025-07-17 15:34:48,801 - INFO - ✅ Spotify API connectée
2025-07-17 15:34:48,802 - INFO - ⚡ Surveillance active
2025-07-17 15:35:17,591 - INFO - 🎵 Artist - Song Title
2025-07-17 15:35:17,708 - INFO - 🎨 #ca4d3a
```

---

## 🧪 Tests

```bash
# Test des endpoints
curl http://localhost:8765/color
curl http://localhost:8765/infos
curl http://localhost:8765/health

# Test avec PowerShell
Invoke-WebRequest -Uri "http://localhost:8765/color"
Invoke-WebRequest -Uri "http://localhost:8765/infos"
Invoke-WebRequest -Uri "http://localhost:8765/health"
```

---

## 🔄 Migration depuis la Version Monolithique

- La version `app.py.old` reste disponible pour référence.
- La migration vers la version modulaire apporte :
  - Architecture propre
  - Maintenabilité
  - Testabilité
  - Extensibilité
  - Performances identiques

---

## 📋 Licence

MIT License

---

## 🎯 Cas d'Usage

- Applications musicales : Couleurs dynamiques selon la piste
- Visualisations : Ambiance colorée synchronisée
- Interfaces utilisateur : Thèmes adaptatifs
- Éclairage intelligent : Synchronisation avec Philips Hue, etc.
```

## 🐋 Déploiement Docker

```bash
# Build et démarrage
docker-compose up --build

# Ou avec Docker uniquement
docker build -f Dockerfile.optimized -t spotify-color-api .
docker run -p 8765:8765 spotify-color-api
```

## 📈 Monitoring

### Statistiques en temps réel
```bash
curl http://localhost:8765/health
```

### Logs structurés
```
2025-07-17 15:34:48,801 - INFO - ✅ Spotify API connectée
2025-07-17 15:34:48,802 - INFO - ⚡ Surveillance active
2025-07-17 15:35:17,591 - INFO - 🎵 Artist - Song Title
2025-07-17 15:35:17,708 - INFO - 🎨 #ca4d3a
```

## 🧪 Tests

```bash
# Test des endpoints
curl http://localhost:8765/color
curl http://localhost:8765/infos
curl http://localhost:8765/health

# Test avec PowerShell
Invoke-WebRequest -Uri "http://localhost:8765/color"
Invoke-WebRequest -Uri "http://localhost:8765/infos"
Invoke-WebRequest -Uri "http://localhost:8765/health"
```

## 🔄 Migration

Si vous utilisez l'ancienne version monolithique (`app.py.old`), la migration vers la version modulaire est simple :

1. Utilisez `python main.py` au lieu de `python app.py.old`
2. Même configuration, mêmes endpoints
3. Architecture améliorée, performances identiques

## 🎯 Cas d'Usage

- **Applications musicales** : Couleurs dynamiques selon la piste
- **Visualisations** : Ambiance colorée synchronisée
- **Interfaces utilisateur** : Thèmes adaptatifs
- **Éclairage intelligent** : Synchronisation avec Philips Hue, etc.

## 📝 Licence

Ce projet est sous licence MIT - voir le fichier LICENSE pour plus de détails.

## 🤝 Contribution

Les contributions sont les bienvenues ! Pour contribuer :

1. Forkez le projet
2. Créez une branche pour votre fonctionnalité
3. Committez vos changements
4. Pushez vers la branche
5. Ouvrez une Pull Request

---

**Développé avec ❤️ pour la communauté Spotify**
