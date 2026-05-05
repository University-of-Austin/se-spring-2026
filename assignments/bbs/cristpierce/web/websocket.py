"""WebSocket connection manager for real-time BBS notifications."""

import json
from fastapi import WebSocket


class ConnectionManager:
    """Manages WebSocket connections per user for real-time notifications."""

    def __init__(self):
        self.active: dict[int, set[WebSocket]] = {}

    async def connect(self, user_id: int, ws: WebSocket):
        await ws.accept()
        if user_id not in self.active:
            self.active[user_id] = set()
        self.active[user_id].add(ws)

    def disconnect(self, user_id: int, ws: WebSocket):
        if user_id in self.active:
            self.active[user_id].discard(ws)
            if not self.active[user_id]:
                del self.active[user_id]

    async def notify(self, user_id: int, event_type: str, message: str):
        """Send a notification to all connections for a user."""
        if user_id not in self.active:
            return
        data = json.dumps({"type": event_type, "message": message})
        dead = []
        for ws in self.active[user_id]:
            try:
                await ws.send_text(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.active[user_id].discard(ws)


manager = ConnectionManager()
