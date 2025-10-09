from fastapi import APIRouter, HTTPException, Depends
import time
from sqlalchemy.orm import Session
from ..services.state import get_state
from ..utils.database import get_db
from ..models.user import Overlay
from ..schemas.overlay import OverlayOut

router = APIRouter()


@router.get("/infos/{user_id}", summary="Infos")
async def infos(user_id: str, db: Session = Depends(get_db)):
    extractor = get_state().get_extractor_for_user(user_id, db)
    # Track info (peut être None si non configuré ou rien en lecture)
    track_info = extractor.get_current_track_info()
    # Couleur extraite avec mesure de temps
    started = time.time()
    r, g, b = extractor.extract_color()
    processing_ms = int((time.time() - started) * 1000)

    payload = {
        "color": {"r": r, "g": g, "b": b, "hex": f"#{r:02x}{g:02x}{b:02x}"},
        "processing_time_ms": processing_ms,
        "source": "album",
        "status": "success",
        "timestamp": int(time.time()),
        "user": user_id,
    }

    if track_info is None:
        payload["track"] = {"id": None, "name": "No music playing", "is_playing": False}
    else:
        payload["track"] = track_info

    return payload


@router.get("/color/{user_id}", summary="Color")
async def color(user_id: str, db: Session = Depends(get_db)):
    extractor = get_state().get_extractor_for_user(user_id, db)
    try:
        started = time.time()
        r, g, b = extractor.extract_color()
        processing_ms = int((time.time() - started) * 1000)
        return {
            "color": {"r": r, "g": g, "b": b, "hex": f"#{r:02x}{g:02x}{b:02x}"},
            "processing_time_ms": processing_ms,
            "source": "album",
            "status": "success",
            "timestamp": int(time.time()),
            "user": user_id,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/overlay/{overlay_id}", summary="Public overlay", response_model=OverlayOut
)
async def get_public_overlay(overlay_id: str, db: Session = Depends(get_db)):
    """Endpoint public (sans auth) pour récupérer un overlay par son ID.
    Ne renvoie pas d'informations sensibles (pas d'owner_id)."""
    ov = db.query(Overlay).filter(Overlay.id == overlay_id).first()
    if not ov:
        raise HTTPException(status_code=404, detail="Overlay introuvable")
    return ov
