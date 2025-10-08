#!/usr/bin/env python3
import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import public, auth, users, overlays, settings
from .services.state import get_state
from .utils.database import create_all


log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=log_level, format="%(asctime)s - %(levelname)s - %(message)s")

app = FastAPI(title="MelodyHue API", version=os.getenv("APP_VERSION", "4.0.0"))

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
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
