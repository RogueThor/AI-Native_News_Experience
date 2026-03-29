"""
routes/arc.py – Story Arc JSON API endpoint.
Note: /arc/:topic page is served by the React SPA — only the JSON API remains here.
"""

import os
from fastapi import APIRouter, Request, Depends, HTTPException

from db.mongo import get_user_by_id, get_story_arc
from agents.story_arc import build_arc_for_topic

router = APIRouter()


# ── Auth dependency (duplicated for encapsulation) ────────────────────────────

async def get_current_user(request: Request) -> dict:
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=307, headers={"Location": "/login"})
    user = await get_user_by_id(user_id)
    if not user:
        request.session.clear()
        raise HTTPException(status_code=307, headers={"Location": "/login"})
    return user


# ── Arc JSON API ──────────────────────────────────────────────────────────────

@router.get("/arc/data/{topic}")
async def arc_json(
    topic: str,
    request: Request,
    user: dict = Depends(get_current_user),
):
    force_refresh = request.query_params.get("refresh") == "true"
    arc = await get_story_arc(topic)
    if not arc or force_refresh:
        arc = await build_arc_for_topic(topic)
    if not arc:
        # Return empty arc structure instead of 404 so React can show "no data" state
        return {"arc": None, "topic": topic}

    # Convert ObjectId fields if present
    if "_id" in arc:
        arc["_id"] = str(arc["_id"])
    return {"arc": arc, "topic": topic}
