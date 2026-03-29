"""
routers/feed.py — WebSocket Real-Time Feed + Feed API (Feature 6)
Manages active WebSocket connections and pushes new articles to users.
"""

import asyncio
import json
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import os

router = APIRouter()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "frontend", "templates"))

# ── Connection Manager ────────────────────────────────────────────────────────

class ConnectionManager:
    def __init__(self):
        # user_id -> WebSocket
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        print(f"[WS Feed] User {user_id} connected. Total: {len(self.active_connections)}")

    def disconnect(self, user_id: str):
        self.active_connections.pop(user_id, None)
        print(f"[WS Feed] User {user_id} disconnected. Total: {len(self.active_connections)}")

    async def send_to_user(self, user_id: str, data: dict) -> bool:
        """Send JSON data to a specific user. Returns False if not connected."""
        ws = self.active_connections.get(user_id)
        if ws:
            try:
                await ws.send_text(json.dumps(data, default=str))
                return True
            except Exception:
                self.disconnect(user_id)
        return False

    async def broadcast_to_all(self, data: dict):
        """Broadcast to all connected users."""
        disconnected = []
        for user_id, ws in list(self.active_connections.items()):
            try:
                await ws.send_text(json.dumps(data, default=str))
            except Exception:
                disconnected.append(user_id)
        for uid in disconnected:
            self.disconnect(uid)


manager = ConnectionManager()


async def notify_ws_users_new_articles(articles: list):
    """
    Called by fetcher_agent after saving new articles.
    Pushes to all connected users.
    """
    if not articles or not manager.active_connections:
        return

    # Serialize articles (convert ObjectIds etc.)
    serialized = []
    for a in articles[:20]:
        item = dict(a)
        if "_id" in item:
            item["_id"] = str(item["_id"])
        serialized.append(item)

    message = {
        "type": "new_articles",
        "count": len(serialized),
        "articles": serialized,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    await manager.broadcast_to_all(message)


# ── Auth dependency ───────────────────────────────────────────────────────────

async def get_current_user(request: Request) -> dict:
    from db.mongo import get_user_by_id
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=307, headers={"Location": "/login"})
    user = await get_user_by_id(user_id)
    if not user:
        request.session.clear()
        raise HTTPException(status_code=307, headers={"Location": "/login"})
    return user


# ── WebSocket endpoint ────────────────────────────────────────────────────────

@router.websocket("/ws/feed/{user_id}")
async def ws_feed(websocket: WebSocket, user_id: str):
    """WebSocket feed endpoint with heartbeat."""
    await manager.connect(user_id, websocket)

    async def heartbeat():
        while True:
            await asyncio.sleep(30)
            try:
                await websocket.send_text(json.dumps({"type": "ping"}))
            except Exception:
                break

    heartbeat_task = asyncio.create_task(heartbeat())
    try:
        while True:
            # Wait for any client messages (keep-alive pong etc.)
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"[WS Feed] Error for user {user_id}: {e}")
    finally:
        heartbeat_task.cancel()
        manager.disconnect(user_id)


# ── Feed page & API (migrated from routes/news.py) ────────────────────────────

@router.get("/ws-feed", response_class=HTMLResponse)
async def feed_page_ws(request: Request, user: dict = Depends(get_current_user)):
    return templates.TemplateResponse("feed.html", {"request": request, "user": user})
