#!/usr/bin/env python3
import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import (
    public,
    auth,
    users,
    overlays,
    settings,
    spotify,
    admin,
    modo,
    realtime,
)
from .services.state import get_state
from .utils.database import create_all


log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=log_level, format="%(asctime)s - %(levelname)s - %(message)s")

app = FastAPI(title="MelodyHue API", version=os.getenv("APP_VERSION", "4.3.0"))

# CORS (configurable)
if os.getenv("ENABLE_CORS", "false").lower() == "true":
    origins_env = os.getenv("CORS_ALLOW_ORIGINS", "").strip()
    # Liste d'origines séparées par des virgules
    allow_origins = [o.strip() for o in origins_env.split(",") if o.strip()] or ["*"]
    allow_credentials = os.getenv("CORS_ALLOW_CREDENTIALS", "false").lower() == "true"
    # Si wildcard et credentials=true, les navigateurs refusent: forcer credentials à false
    if "*" in allow_origins and allow_credentials:
        logging.warning(
            "CORS: '*' avec credentials=true n'est pas supporté par les navigateurs; credentials sera forcé à false."
        )
        allow_credentials = False

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )

state = get_state()

# Include routers
app.include_router(public.router, tags=["public"])  # /infos, /color
app.include_router(
    auth.router, prefix="/auth", tags=["auth"]
)  # /auth/login, /auth/register, ...
app.include_router(users.router, prefix="/users", tags=["users"])  # profile updates
app.include_router(
    overlays.router, prefix="/overlays", tags=["overlays"]
)  # CRUD overlays
app.include_router(
    settings.router, prefix="/settings", tags=["settings"]
)  # user settings
app.include_router(spotify.router, prefix="/spotify", tags=["spotify"])
app.include_router(
    admin.router, prefix="/admin", tags=["admin"]
)  # admin dashboard & roles
app.include_router(modo.router, prefix="/modo", tags=["moderation"])  # moderator tools
app.include_router(realtime.router, tags=["realtime"])  # /ws


@app.on_event("startup")
async def on_startup():
    try:
        create_all(None)
    except Exception:
        pass
    await state.start()


@app.on_event("shutdown")
async def on_shutdown():
    await state.stop()


# Simple health
@app.get("/health")
async def health():
    return {"status": "ok"}
