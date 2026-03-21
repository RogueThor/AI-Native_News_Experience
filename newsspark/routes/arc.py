"""
routes/arc.py – Story Arc page and JSON API endpoints.
"""

import os
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from db.mongo import get_user_by_id, get_story_arc
from agents.story_arc import build_arc_for_topic

router = APIRouter()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "frontend", "templates"))


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


# ── Arc HTML page ─────────────────────────────────────────────────────────────

@router.get("/arc/{topic}", response_class=HTMLResponse)
async def arc_page(
    topic: str,
    request: Request,
    user: dict = Depends(get_current_user),
):
    # Try to load from MongoDB, otherwise build fresh
    arc = await get_story_arc(topic)
    if not arc:
        arc = await build_arc_for_topic(topic)

    return templates.TemplateResponse(
        "arc.html",
        {"request": request, "user": user, "arc": arc, "topic": topic}
    )


# ── Arc JSON API ──────────────────────────────────────────────────────────────

@router.get("/arc/data/{topic}")
async def arc_json(
    topic: str,
    request: Request,
    user: dict = Depends(get_current_user),
):
    arc = await get_story_arc(topic)
    if not arc:
        arc = await build_arc_for_topic(topic)
    if not arc:
        raise HTTPException(status_code=404, detail="No arc data for this topic")

    # Convert ObjectId fields if present
    if "_id" in arc:
        arc["_id"] = str(arc["_id"])
    return arc


# ── Briefing page ─────────────────────────────────────────────────────────────

@router.get("/briefing", response_class=HTMLResponse)
async def briefing_page(
    request: Request,
    user: dict = Depends(get_current_user),
):
    from fastapi.templating import Jinja2Templates as T
    return templates.TemplateResponse(
        "briefing.html",
        {"request": request, "user": user}
    )
