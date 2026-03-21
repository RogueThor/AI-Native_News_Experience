"""
routes/news.py – Feed, Translation, Briefing, and Q&A endpoints.
"""

import os
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from db.mongo import get_user_by_id

router = APIRouter()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "frontend", "templates"))


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


# ── Feed page ─────────────────────────────────────────────────────────────────

@router.get("/feed", response_class=HTMLResponse)
async def feed_page(request: Request, user: dict = Depends(get_current_user)):
    return templates.TemplateResponse(
        "feed.html",
        {"request": request, "user": user}
    )


# ── Feed JSON API ─────────────────────────────────────────────────────────────

@router.get("/news/feed")
async def news_feed_api(request: Request, user: dict = Depends(get_current_user)):
    from pipeline.graph import run_pipeline

    state = {
        "request_type": "feed",
        "user_id": user.get("_id", ""),
        "user_profile": user,
        "article_id": None,
        "topic": None,
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

@router.get("/news/arc/{topic}", response_class=HTMLResponse)
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


# ── AI Reporter Summary ────────────────────────────────────────────────────────

@router.get("/news/reporter/{article_id}")
async def reporter_summary(
    article_id: str,
    request: Request,
    user: dict = Depends(get_current_user),
):
    """Generate an Indian English / Hinglish-flavored summary for TTS."""
    import os
    from groq import Groq
    from db.mongo import get_article_by_id

    article = await get_article_by_id(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    title = article.get("title", "")
    desc  = article.get("description", "") or article.get("raw_text", "")

    groq_client = Groq(api_key=os.getenv("GROQ_API_KEY", ""))
    prompt = f"""You are a sharp, energetic Indian English news reporter — think Times Now or NDTV style.
Summarize this article in 3-4 punchy sentences using confident Indian English. Use direct, impactful phrasing typical of Indian TV journalism: phrases like "and that is the big picture", "the ground reality is", "make no mistake about it", "sources are telling us", "this is a game-changer", "the numbers are staggering", "and here is the clincher". Keep it factual but dramatic and engaging. Pure English only — no Hindi words.

Title: {title}
Description: {desc}

Give only the spoken reporter summary, no labels or extra formatting."""

    try:
        resp = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.85,
            max_tokens=300,
        )
        summary = resp.choices[0].message.content.strip()
    except Exception as e:
        summary = f"{title}. {desc}"

    return {"summary": summary}
