"""
routers/chat.py — Live News Chatbot endpoints (Feature 9)
WebSocket streaming + REST fallback.
"""

import asyncio
import json
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request, Depends, HTTPException

router = APIRouter()


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


# ── WebSocket chat endpoint ───────────────────────────────────────────────────

@router.websocket("/ws/chat/{user_id}")
async def ws_chat(websocket: WebSocket, user_id: str):
    """WebSocket chat endpoint — streaming responses from LiveChatAgent."""
    await websocket.accept()
    print(f"[WS Chat] User {user_id} connected.")

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                payload = json.loads(raw)
                message = payload.get("message", raw)
            except Exception:
                message = raw

            if not message.strip():
                continue

            # Send "thinking" indicator
            await websocket.send_text(json.dumps({
                "type": "thinking",
                "message": "Searching news sources...",
            }))

            try:
                from agents.live_chat_agent import run_live_chat
                result = await run_live_chat(message, user_id=user_id)
                await websocket.send_text(json.dumps({
                    "type": "response",
                    "data": result,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }, default=str))
            except Exception as e:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": str(e),
                }))

    except WebSocketDisconnect:
        print(f"[WS Chat] User {user_id} disconnected.")
    except Exception as e:
        print(f"[WS Chat] Error for user {user_id}: {e}")


# ── REST fallback ─────────────────────────────────────────────────────────────

@router.post("/chat")
@router.post("/api/chat")
async def chat_rest(request: Request, user: dict = Depends(get_current_user)):
    """REST fallback for chat (available at both /chat and /api/chat)."""
    from agents.live_chat_agent import run_live_chat

    body = await request.json()
    message = body.get("message", "")
    user_id = str(user.get("_id", "anonymous"))

    if not message.strip():
        raise HTTPException(status_code=400, detail="message is required")

    result = await run_live_chat(message, user_id=user_id)
    return result
