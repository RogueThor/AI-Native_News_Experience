"""
routers/articles.py — Article endpoints + Multi-Lens Perspectives (Feature 8)
"""

import os
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import JSONResponse

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


@router.post("/article/{article_id}/lenses")
async def get_article_lenses(
    article_id: str,
    request: Request,
    user: dict = Depends(get_current_user),
):
    """
    Generate or return cached multi-lens perspectives for an article.
    Checks MongoDB cache first — never re-generates the same article twice.
    """
    from db.mongo import get_article_by_id
    from agents.multi_lens_agent import generate_lenses

    article = await get_article_by_id(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    # Build article text
    text = f"{article.get('title', '')}\n\n{article.get('content') or article.get('description') or ''}"

    lenses = await generate_lenses(article_id, text)
    return lenses


@router.get("/news/reporter/{article_id}")
async def reporter_summary(
    article_id: str,
    request: Request,
    user: dict = Depends(get_current_user),
):
    """Generate Indian English reporter summary for TTS."""
    import asyncio
    from groq import Groq
    from db.mongo import get_article_by_id

    article = await get_article_by_id(article_id)
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    title = article.get("title", "")
    desc = article.get("content", "") or article.get("description", "") or article.get("raw_text", "")

    # Filter paywall text from NewsData.io
    paywall_phrases = ["only available in", "available in paid", "paid plan", "upgrade to"]
    if desc and any(p in desc.lower() for p in paywall_phrases):
        desc = ""

    groq_client = Groq(api_key=os.getenv("GROQ_API_KEY", ""))
    from agents.model_config import QUALITY_MODEL

    if not desc.strip():
        # No content available — just read the title
        prompt = f"""You are an energetic Indian English news anchor (think Times Now / NDTV style).
Read out this headline in 2 confident, punchy sentences. Do NOT mention or infer other news or events — 
only report what this headline says. Pure English only.

Headline: {title}

Give only the spoken reporter line, no labels or formatting."""
    else:
        prompt = f"""You are a sharp, energetic Indian English news reporter — think Times Now or NDTV style.
Summarize ONLY the article below in 3-4 punchy sentences using confident Indian English.
Do NOT reference any other news articles, events, or information not present in this article.
Use direct, impactful phrasing: "the ground reality is", "make no mistake about it", 
"sources are telling us", "this is a game-changer", "and here is the clincher".
Keep it factual and based strictly on what is written below. Pure English only.

Title: {title}
Article Content: {desc}

Give only the spoken reporter summary, no labels or extra formatting."""

    def _call():
        resp = groq_client.chat.completions.create(
            model=QUALITY_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=1024,
        )
        return resp.choices[0].message.content.strip()

    try:
        loop = asyncio.get_event_loop()
        summary = await loop.run_in_executor(None, _call)
    except Exception as e:
        summary = f"{title}. {desc}"

    return {"summary": summary}
