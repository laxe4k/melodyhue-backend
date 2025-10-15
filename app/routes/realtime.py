import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from ..utils.database import get_db
from ..utils.security import decode_token
from ..models.user import User
from ..services.realtime import get_manager

router = APIRouter()

bearer = HTTPBearer(auto_error=False)


async def _auth_user_id(
    websocket: WebSocket, db: Session = Depends(get_db)
) -> str | None:
    # 1) Authorization header (Bearer)
    auth = websocket.headers.get("authorization")
    token = None
    if auth and auth.lower().startswith("bearer "):
        token = auth.split(" ", 1)[1].strip()
    # 2) Cookie mh_access_token
    if not token:
        token = websocket.cookies.get("mh_access_token")
    # 3) Query param token (fallback)
    if not token:
        token = websocket.query_params.get("token")
    # 4) Query param access_token (compat)
    if not token:
        token = websocket.query_params.get("access_token")
    if not token:
        logging.warning("[WS] auth failed: no token (no header/cookie/query)")
        return None
    try:
        payload = decode_token(token)
        sub = payload.get("sub")
        if not isinstance(sub, str):
            logging.warning("[WS] auth failed: invalid sub in token payload")
            return None
        # vérifier que l'utilisateur existe
        u = db.query(User).filter(User.id == sub).first()
        if not u:
            logging.warning("[WS] auth failed: user not found for sub=%s", sub)
            return None
        return sub
    except Exception:
        logging.exception("[WS] auth failed: token decode error")
        return None


@router.websocket("/ws")
async def ws_endpoint(websocket: WebSocket, db: Session = Depends(get_db)):
    user_id = await _auth_user_id(websocket, db)
    if not user_id:
        await websocket.close(code=4401)
        return
    await websocket.accept()
    manager = get_manager()
    await manager.connect(user_id, websocket)
    try:
        while True:
            # garder la connexion vivante; ignorer les messages
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)
