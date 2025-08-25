# Spotify Info & Color API (Flask)

API Flask qui récupère la piste Spotify en cours, extrait une couleur dominante “naturelle mais punchy”, et expose des endpoints JSON simples. UI incluse pour configurer et connecter Spotify.

---

## 🏗️ Structure

```
spotify-info-color-api/
├─ run.py                             # Entrypoint (HOST/PORT/FLASK_DEBUG via .env)
├─ app/
│  ├─ __init__.py                     # App factory + enregistrement des blueprints
│  ├─ controllers/
│  │  └─ defaultController.py         # Routes: /, /connect, API, OAuth
│  └─ models/
│     ├─ __init__.py
│     ├─ spotify_client.py            # OAuth/Tokens + appels API Spotify
│     ├─ color_extractor.py           # Téléchargement image + couleur dominante
│     └─ spotify_color_extractor.py   # Orchestrateur + monitoring
├─ data/                              # (créé au runtime) tokens & config
├─ Dockerfile
├─ docker-compose.yml
├─ requirements.txt
└─ LICENSE
```

---

## 🚀 Démarrage rapide

### Option A — Python local

1) Installer les dépendances

```powershell
pip install -r requirements.txt
```

2) Variables d’environnement (facultatif)

Créez un `.env` minimal (pas de secrets Spotify ici):

```env
HOST=0.0.0.0
PORT=8765
FLASK_DEBUG=False
DATA_DIR=./data
```

3) Lancer

```powershell
python run.py
```

4) Ouvrir l’UI
- Accueil: http://localhost:8765/
- Connexion: http://localhost:8765/connect

### Option B — Docker Compose

Exemple recommandé (extrait):

```yaml
services:
  spotify-info-color-api:
    image: ghcr.io/laxe4k/spotify-info-color-api:latest
    container_name: spotify_info_color_api
    ports:
      - "${SERVER_PORT}:${SERVER_PORT}"
    environment:
      - HOST=${SERVER_HOST}
      - PORT=${SERVER_PORT}
      - FLASK_DEBUG=${FLASK_DEBUG}
      - DATA_DIR=/home/spotifyapi/data   # Utilise le volume persistant
    volumes:
      - spotify_data:/home/spotifyapi/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:${SERVER_PORT}/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    networks:
      - spotify-network
    restart: unless-stopped

volumes:
  spotify_data:
```

Sur un hôte Ubuntu, les fichiers persistants se trouveront dans le volume Docker (généralement `/var/lib/docker/volumes/.../_data`, inspectable via `docker volume inspect`). Alternative: bind mount vers un dossier local (ex: `/srv/spotify-info-color-api:/home/spotifyapi/data`).

---

## 🔐 Connexion Spotify (OAuth 2.0)

1) Crée une application sur https://developer.spotify.com/dashboard
- Ajoute une Redirect URI: `http(s)://<ton-host>:<port>/spotify/callback`

2) Va sur l’UI /connect
- Renseigne Client ID et Client Secret
- Le Redirect URI est forcé automatiquement côté serveur à `<host>/spotify/callback`
- Clique “Sauvegarder” (ne connecte pas)
- Clique “Connexion” pour ouvrir Spotify et autoriser

3) Une fois autorisé
- Les tokens sont stockés dans `DATA_DIR/spotify_tokens.json`
- La config (client_id/secret/redirect_uri) dans `DATA_DIR/spotify_config.json`
- Bouton “Déconnexion” pour révoquer côté app (supprime les tokens locaux)

Important
- Ne mets PAS `SPOTIFY_CLIENT_ID` / `SPOTIFY_CLIENT_SECRET` dans `.env`. Utilise l’UI /connect (ou les endpoints `/settings/spotify`).

---

## 🔗 Endpoints

- GET `/` — Landing page
- GET `/connect` — UI config + connexion Spotify
- GET `/color` — Couleur dominante actuelle
- GET `/infos` — Détails piste + couleur
- GET `/health` — Santé + stats
- GET `/debug/track` — Debug en cours
- GET `/spotify/oauth-url` — URL d’auth Spotify
- GET `/spotify/callback` — Callback OAuth
- GET `/settings/spotify` — Lire l’état/config
- POST `/spotify/logout` — Déconnexion (purge tokens locaux)
- POST `/settings/spotify` — Enregistrer client_id/secret (sans connexion auto)

Réponses JSON standardisées (status, timestamp, etc.).

---

## 🎨 Extraction de couleur (résumé)

- Téléchargement pochette (cache 10 images)
- Filtrage pixels trop sombres, sélection couleur dominante par fréquence/saturation
- Légère amplification de saturation + éclaircissement si trop sombre
- Couleur "pause": `#53ac6a` (bientôt personnalisable)
- Cache par track_id (TTL court) pour limiter le recalcul

---

## 🧪 Essais rapides

PowerShell (Windows):

```powershell
Invoke-WebRequest -Uri "http://localhost:8765/color"
Invoke-WebRequest -Uri "http://localhost:8765/infos"
Invoke-WebRequest -Uri "http://localhost:8765/health"
```

curl:

```bash
curl http://localhost:8765/color
curl http://localhost:8765/infos
curl http://localhost:8765/health
```

---

## 🛠️ Dépannage

- 400 “redirect_uri_mismatch” sur l’OAuth: assure-toi d’avoir bien ajouté `http(s)://<host>:<port>/spotify/callback` dans le Dashboard Spotify, et d’accéder via la même URL.
- Données non persistées en Docker: mets `DATA_DIR=/home/spotifyapi/data` et monte un volume sur ce chemin.
- Pas de musique détectée: Spotify peut renvoyer 204 si rien ne joue sur le compte autorisé.

---

## 📄 Licence & Crédits

Ce projet est distribué sous licence **MIT** — voir [LICENSE](LICENSE) pour les détails complets.

### Contributions
- Développé par **Laxe4k** avec ❤️
- Contributions et issues bienvenues sur GitHub
- N'hésitez pas à fork et adapter selon vos besoins

### Remerciements
- API Spotify pour l'accès aux données musicales
- Flask pour le framework web léger et efficace
- Communauté Python pour les excellentes librairies utilisées

---

Made for fun. Enjoy 🎧
