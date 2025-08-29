# Spotify Info & Color API (Flask)

[![GitHub Release](https://img.shields.io/github/v/release/laxe4k/spotify-info-color-api)](https://github.com/laxe4k/spotify-info-color-api/releases)
[![GitHub Release Date](https://img.shields.io/github/release-date/laxe4k/spotify-info-color-api)](https://github.com/laxe4k/spotify-info-color-api/releases)
[![GitHub License](https://img.shields.io/github/license/laxe4k/spotify-info-color-api)](https://github.com/laxe4k/spotify-info-color-api/blob/main/LICENSE)
[![GitHub contributors](https://img.shields.io/github/contributors/laxe4k/spotify-info-color-api)](https://github.com/laxe4k/spotify-info-color-api/graphs/contributors)
[![GitHub Packages](https://img.shields.io/badge/GitHub%20Packages-ghcr.io-blue)](https://github.com/laxe4k/spotify-info-color-api/pkgs/container/spotify-info-color-api)
[![GitHub Issues](https://img.shields.io/github/issues/laxe4k/spotify-info-color-api)](https://github.com/laxe4k/spotify-info-color-api/issues)

API Flask avec UI qui affiche la musique Spotify en cours et extrait une couleur dominante « naturelle mais punchy » depuis la pochette.
Support multi‑utilisateurs (comptes), OAuth Spotify par utilisateur, tokens chiffrés, endpoints JSON simples et déploiement Docker.

---

## 🏗️ Structure

```
spotify-info-color-api/
├─ run.py                                     # Entrypoint Flask (HOST/PORT/FLASK_DEBUG via .env)
├─ app/
│  ├─ __init__.py                             # App factory, config, enregistrement des blueprints
│  ├─ extensions.py                           # Extensions (SQLAlchemy, Migrate)
│  ├─ controllers/                            # Routes HTTP
│  │  ├─ auth_controller.py                   # Auth: login/register/logout
│  │  ├─ pages_controller.py                  # Pages UI (index, settings, ...)
│  │  ├─ spotify_controller.py                # Endpoints Spotify & couleurs
│  │  └─ user_controller.py                   # Profil & gestion utilisateur
│  ├─ services/                               # Logique métier
│  │  ├─ color_extractor_service.py           # Extraction couleur dominante (Pillow)
│  │  ├─ spotify_client_service.py            # OAuth + appels API Spotify
│  │  ├─ spotify_color_extractor_service.py   # Orchestrateur Spotify+couleur
│  │  └─ user_service.py                      # Opérations utilisateur
│  ├─ models/
│  │  └─ user_model.py                        # Modèle User (UUID, hash Argon2)
│  ├─ security/
│  │  └─ crypto.py                            # Chiffrement des tokens (Fernet)
│  ├─ forms/
│  │  ├─ auth_forms.py                        # WTForms pour auth
│  │  └─ spotify_forms.py                     # WTForms pour config Spotify
│  ├─ views/
│  │  └─ templates/                           # Templates Jinja2 (index, login, ...)
│  └─ static/
│     └─ css/                                 # Styles globaux + pages
├─ migrations/                                # Migrations Alembic
├─ Dockerfile
├─ docker-compose.yml
├─ requirements.txt
├─ ruff.toml                                  # Lint/format (Ruff)
├─ .env.example                               # Exemple d’environnement
└─ LICENSE
```

---

## 🚀 Démarrage rapide

### Option A - Python local

1) Installer les dépendances

```powershell
pip install -r requirements.txt
```

2) Variables d’environnement

Reportez-vous à la section ci‑dessous « Variables d’environnement (.env commun) ».

3) Lancer

```powershell
python run.py
```

4) Ouvrir l’UI
- Accueil: http://localhost:8765/
- Connexion: http://localhost:8765/login
- Inscription: http://localhost:8765/register

---

### Variables d’environnement (.env commun)

Ces variables sont utilisées à la fois en exécution locale et avec Docker Compose.

Exemple de `.env` minimal (à la racine du projet):
```env
# Flask
SECRET_KEY=dev-secret-key
HOST=0.0.0.0
PORT=8765
FLASK_DEBUG=False

# Chiffrement (Fernet, 32 octets base64)
ENCRYPTION_KEY=YOUR_ENCRYPTION_KEY

# Spotify (optionnel)
SPOTIFY_REDIRECT_URI=http://localhost:8765/spotify/callback

# Base de données
DB_HOST=your.db.host
DB_DATABASE=your.db.name
DB_USER=your.db.user
DB_PASSWORD=your.db.password
DB_PORT=3306

# SMTP (optionnel)
SMTP_HOST=your.smtp.host
SMTP_PORT=587
SMTP_USER=your@smtp.user
SMTP_PASSWORD=your.smtp.password
```

Générer une clé Fernet (Windows PowerShell):
```powershell
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

### Option A - Python local

1) Installer les dépendances

```powershell
pip install -r requirements.txt
```

2) Variables d’environnement
```powershell
# Copier le fichier d'exemple
cp .env.example .env
# ou
copy .env.example .env
```
> *N'oubliez pas de remplir les variables d'environnement dans le fichier `.env` avec vos propres valeurs.*

3) Lancer

```powershell
python run.py
```

4) Ouvrir l’UI
- Accueil: http://localhost:8765/
- Connexion: http://localhost:8765/login
- Inscription: http://localhost:8765/register

---

### Option B - Docker Compose

1) Docker Compose

```yaml
services:
  spotify-info-color-api:
    image: ghcr.io/laxe4k/spotify-info-color-api:latest
    container_name: spotify_info_color_api
    ports:
      - "${PORT}:${PORT}"
    environment:
      # Flask configuration
      SECRET_KEY: ${SECRET_KEY}
      HOST: ${HOST}
      PORT: ${PORT}
      FLASK_DEBUG: ${FLASK_DEBUG}

      # Encryption configuration
      ENCRYPTION_KEY: ${ENCRYPTION_KEY}

      # Spotify API configuration (optionnel)
      SPOTIFY_REDIRECT_URI: ${SPOTIFY_REDIRECT_URI}

      # DB configuration
      DB_HOST: ${DB_HOST}
      DB_DATABASE: ${DB_DATABASE}
      DB_USER: ${DB_USER}
      DB_PASSWORD: ${DB_PASSWORD}
      DB_PORT: ${DB_PORT}

      # SMTP configuration (not used for now)
      SMTP_HOST: ${SMTP_HOST}
      SMTP_PORT: ${SMTP_PORT}
      SMTP_USER: ${SMTP_USER}
      SMTP_PASSWORD: ${SMTP_PASSWORD}
    volumes:
      - spotify_data:/home/spotifyapi/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:${PORT}/health"]
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


2) Préparer le fichier `.env`

```powershell
# Copier le fichier d'exemple
cp .env.example .env
# ou
copy .env.example .env
```
> *N'oubliez pas de remplir les variables d'environnement dans le fichier `.env` avec vos propres valeurs.*

3) Lancer

```powershell
# Si votre `.env` est à côté de `docker-compose.yml` (recommandé)
docker compose up -d

# Si votre fichier d'environnement est ailleurs
# docker compose --env-file .env up -d
```

4) Ouvrir l’UI
- Accueil: http://localhost:8765/
- Connexion: http://localhost:8765/login
- Inscription: http://localhost:8765/register

---

## 🔐 Connexion Spotify (OAuth 2.0)

1) Crée une application sur https://developer.spotify.com/dashboard
- Ajoute les Redirect URIs nécessaires selon ton usage:
  - Mode global: `http(s)://<host>:<port>/spotify/callback`
  - Mode par utilisateur: `http(s)://<host>:<port>/<username>/spotify/callback` ou `http(s)://<host>:<port>/<uuid>/spotify/callback`
  - Remarque: en mode par utilisateur, chaque utilisateur doit déclarer l’URI exacte dans SA propre app Spotify (Client ID/Secret personnels).

2) Côté application
- Crée un compte via `/register`, puis connecte-toi via `/login`
- Ouvre `/<username>/settings` et renseigne ton `Client ID` et `Client Secret` Spotify
- Clique “Sauvegarder”, puis “Connecter Spotify” pour autoriser l’application

3) Après autorisation
- Les tokens sont chiffrés (Fernet) et stockés en base par utilisateur (refresh token géré automatiquement)
- “Déconnecter Spotify” révoque localement l’accès (suppression des tokens de l’app)

Important
- Ne mets PAS `SPOTIFY_CLIENT_ID` / `SPOTIFY_CLIENT_SECRET` dans `.env`. Utilise l’UI utilisateur (`/<username>/settings`) ou, en option, la config globale via les endpoints `/settings/spotify`.

---

## 🔗 Endpoints

- Public/ généraux
  - GET `/` — Landing page
  - GET `/health` — Santé + stats
  - GET `/color` — Couleur dominante (global)
  - GET `/infos` — Infos piste + couleur (global)
  - GET `/debug/track` — Debug

- Pages (UI)
  - GET `/login` — Page de connexion
  - GET `/register` — Page d’inscription
  - GET `/<username>/settings` — Page paramètres utilisateur (privée)

- Auth API
  - POST `/api/auth/login`
  - POST `/api/auth/signup` (alias: `/api/auth/register`)
  - POST `/logout`

- Spotify (instance globale)
  - GET `/settings/spotify` — Lire l’état/config globale
  - POST `/settings/spotify` — Enregistrer client_id/secret (global)
  - GET `/spotify/oauth-url` — URL d’auth globale
  - GET `/spotify/callback` — Callback OAuth globale
  - POST `/spotify/logout` — Déconnexion globale

- Spotify / Couleurs par utilisateur
  - GET `/<username>/color` — Couleur (supporte `?default=<hex|db|auto>`)
  - GET `/<uuid:user_uuid>/color`
  - GET `/<username>/infos` — Détails piste + couleur
  - GET `/<uuid:user_uuid>/infos`
  - GET `/u/<username>/nowplaying` — Page Now Playing
  - GET `/<uuid:user_uuid>/nowplaying` — Page Now Playing (UUID)
  - GET `/<username>/nowplaying.json` — Now Playing (JSON)
  - GET `/<uuid:user_uuid>/color-fullscreen` — Vue plein écran de la couleur

- OAuth Spotify par utilisateur
  - GET `/<username>/spotify/oauth-url`
  - GET `/<uuid:user_uuid>/spotify/oauth-url`
  - GET `/<username>/spotify/callback`
  - GET `/<uuid:user_uuid>/spotify/callback`
  - POST `/<username>/spotify/logout`
  - POST `/<uuid:user_uuid>/spotify/logout`

- Paramètres utilisateur
  - GET|POST `/<username>/settings/spotify`
  - GET|POST `/<username>/settings/profile`
  - GET|POST `/<username>/settings/display`
  - GET|POST `/<uuid:user_uuid>/settings/profile`
  - GET|POST `/<uuid:user_uuid>/settings/display`

Réponses JSON standardisées (status, timestamp, etc.).

---

## 🎨 Extraction de couleur (résumé)

- Téléchargement pochette (cache 10 images)
- Filtrage pixels trop sombres, sélection couleur dominante par fréquence/saturation
- Légère amplification de saturation + éclaircissement si trop sombre
- Couleur "pause": `#53ac6a` (personnalisable)
- Cache par track_id (TTL court) pour limiter le recalcul

---

## 📄 Licence & Crédits

Ce projet est distribué sous licence **MIT** - voir [LICENSE](LICENSE) pour les détails complets.

### Contributions
- Développé par **[Laxe4k](https://github.com/laxe4k)** avec ❤️
- Contributions et issues bienvenues sur GitHub
- N'hésitez pas à fork et adapter selon vos besoins

### Remerciements
- API Spotify pour l'accès aux données musicales
- Flask pour le framework web léger et efficace
- Communauté Python pour les excellentes librairies utilisées

---

## ⚡ Contribuer

### Comment contribuer
- **Issues** : Signalez des bugs ou proposez des améliorations via [GitHub Issues](https://github.com/laxe4k/spotify-info-color-api/issues)
- **Pull Requests** : Fork le projet, créez une branche feature, et soumettez vos modifications
- **Discussions** : Partagez vos idées dans les [GitHub Discussions](https://github.com/laxe4k/spotify-info-color-api/discussions)

### Idées d'améliorations
- Algorithmes de couleur alternatifs (palette complète, couleurs complémentaires)
- Webhooks pour notifier les changements de piste
- Support d'autres plateformes musicales (Apple Music, Deezer, Tidal)
- Interface d'administration avancée
- Métriques et analytics de l'API

### Guidelines de développement
- Suivez les conventions Python (PEP 8)
- Ajoutez des tests pour les nouvelles fonctionnalités
- Documentez les changements dans le changelog
- Testez avec Docker avant de soumettre

---

Made for fun. Enjoy 🎧
