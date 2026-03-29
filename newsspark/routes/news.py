"""
routes/news.py – Feed JSON API, Translation, Briefing, and Q&A endpoints.
Note: HTML page routes for /feed, /chat, /briefing are handled by the React SPA.
"""

import os
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse

from db.mongo import get_user_by_id

router = APIRouter()


# ── Auth dependency ───────────────────────────────────────────────────────────

async def get_current_user(request: Request) -> dict:
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=307, headers={"Location": "/login"})
    user = await get_user_by_id(user_id)
    if not user:
        request.session.clear()
        raise HTTPException(status_code=307, headers={"Location": "/login"})
    return user



# ── Feed JSON API ─────────────────────────────────────────────────────────────

@router.get("/news/feed")
async def news_feed_api(request: Request, category: str = None, user: dict = Depends(get_current_user)):
    from pipeline.graph import run_pipeline

    state = {
        "request_type": "feed",
        "user_id": user.get("_id", ""),
        "user_profile": user,
        "article_id": None,
        "topic": category,
        "question": None,
        "language": user.get("language_pref", "en"),
        "articles": [],
        "arc_data": None,
        "translated_text": None,
        "briefing_text": None,
        "answer_text": None,
        "feed": None,
    }

    result = await run_pipeline(state)
    return {"feed": result.get("feed", [])}


# ── Translation API ───────────────────────────────────────────────────────────

@router.get("/news/translate/{article_id}")
async def translate_article(
    article_id: str,
    request: Request,
    user: dict = Depends(get_current_user),
):
    from pipeline.graph import run_pipeline

    lang = request.query_params.get("lang", user.get("language_pref", "en"))

    state = {
        "request_type": "translate",
        "user_id": user.get("_id", ""),
        "user_profile": user,
        "article_id": article_id,
        "topic": None,
        "question": None,
        "language": lang,
        "articles": [],
        "arc_data": None,
        "translated_text": None,
        "briefing_text": None,
        "answer_text": None,
        "feed": None,
    }

    result = await run_pipeline(state)
    return {"translated_text": result.get("translated_text")}


# ── Arc page redirect ─────────────────────────────────────────────────────────

@router.get("/news/arc/{topic}")
async def arc_page_redirect(
    topic: str,
    request: Request,
    user: dict = Depends(get_current_user),
):
    return RedirectResponse(url=f"/arc/{topic}")


# ── Briefing API ──────────────────────────────────────────────────────────────

@router.post("/news/briefing")
async def news_briefing(
    request: Request,
    user: dict = Depends(get_current_user),
):
    body = await request.json()
    topic = body.get("topic", "markets")

    from pipeline.graph import run_pipeline

    state = {
        "request_type": "briefing",
        "user_id": user.get("_id", ""),
        "user_profile": user,
        "article_id": None,
        "topic": topic,
        "question": None,
        "language": user.get("language_pref", "en"),
        "articles": [],
        "arc_data": None,
        "translated_text": None,
        "briefing_text": None,
        "answer_text": None,
        "feed": None,
    }

    result = await run_pipeline(state)
    return {"briefing_text": result.get("briefing_text")}


# ── Q&A API ───────────────────────────────────────────────────────────────────

@router.post("/news/ask")
async def news_ask(
    request: Request,
    user: dict = Depends(get_current_user),
):
    body = await request.json()
    topic = body.get("topic", "markets")
    question = body.get("question", "")

    if not question:
        raise HTTPException(status_code=400, detail="question is required")

    from pipeline.graph import run_pipeline

    state = {
        "request_type": "ask",
        "user_id": user.get("_id", ""),
        "user_profile": user,
        "article_id": None,
        "topic": topic,
        "question": question,
        "language": user.get("language_pref", "en"),
        "articles": [],
        "arc_data": None,
        "translated_text": None,
        "briefing_text": None,
        "answer_text": None,
        "feed": None,
    }

    result = await run_pipeline(state)
    return {"answer_text": result.get("answer_text")}


