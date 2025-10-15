from typing import Dict, Set
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        # Map user_id -> set of websockets
        self._by_user: Dict[str, Set[WebSocket]] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        self._by_user.setdefault(user_id, set()).add(websocket)

    def disconnect(self, user_id: str, websocket: WebSocket):
        conns = self._by_user.get(user_id)
        if not conns:
            return
        conns.discard(websocket)
        if not conns:
            self._by_user.pop(user_id, None)

    async def send_to_user(self, user_id: str, message: dict):
        conns = self._by_user.get(user_id)
        if not conns:
            return
        dead: Set[WebSocket] = set()
        for ws in conns:
            try:
                await ws.send_json(message)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self.disconnect(user_id, ws)

    async def kick_user(self, user_id: str, reason: str = "banned"):
        await self.send_to_user(user_id, {"type": "force_logout", "reason": reason})
        # Optionnel: fermer immédiatement toutes les connexions WS de l'utilisateur
        await self.close_user(user_id, code=4401, reason=reason)

    async def close_user(
        self, user_id: str, code: int = 4401, reason: str = "unauthorized"
    ):
        conns = self._by_user.get(user_id)
        if not conns:
            return
        dead: Set[WebSocket] = set()
        for ws in list(conns):
            try:
                await ws.close(code=code, reason=reason)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self.disconnect(user_id, ws)


_MANAGER: ConnectionManager | None = None


def get_manager() -> ConnectionManager:
    global _MANAGER
    if _MANAGER is None:
        _MANAGER = ConnectionManager()
    return _MANAGER
