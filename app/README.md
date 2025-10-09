# MelodyHue FastAPI

Nouvelle API FastAPI (MVC sans vues) située dans `fastapi_app/`.

- Endpoints publics:
  - `GET /infos` — infos piste Spotify actuelle
  - `GET /color` — couleur dominante actuelle
- Auth:
  - `POST /auth/register`, `POST /auth/login`, `POST /auth/refresh`
  - `POST /auth/2fa/setup`, `POST /auth/2fa/verify`
- Utilisateur:
  - `GET /users/me`, `PATCH /users/me/username`, `PATCH /users/me/email`, `POST /users/me/password`
- Overlays:
  - CRUD `/overlays`

Dépendances clés: fastapi, uvicorn, python-jose, pyotp, SQLAlchemy.

## Démarrer en local

1. Créez un fichier `.env` avec les variables DB_* ou `DATABASE_URL`, et `JWT_SECRET`.
2. Installez les dépendances (voir `requirements.txt`).
3. Lancez le serveur:

```
uvicorn fastapi_app.asgi:app --reload --host 0.0.0.0 --port 8765
```

