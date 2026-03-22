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

    groq_client = Groq(api_key=os.getenv("GROQ_API_KEY", ""))
    prompt = f"""You are a sharp, energetic Indian English news reporter — think Times Now or NDTV style.
Summarize this article in 3-4 punchy sentences using confident Indian English. Use direct, impactful phrasing typical of Indian TV journalism: phrases like "and that is the big picture", "the ground reality is", "make no mistake about it", "sources are telling us", "this is a game-changer", "the numbers are staggering", "and here is the clincher". Keep it factual but dramatic and engaging. Pure English only — no Hindi words.

Title: {title}
Description: {desc}

Give only the spoken reporter summary, no labels or extra formatting."""

    def _call():
        resp = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.85,
            max_tokens=300,
        )
        return resp.choices[0].message.content.strip()

    try:
        loop = asyncio.get_event_loop()
        summary = await loop.run_in_executor(None, _call)
    except Exception as e:
        summary = f"{title}. {desc}"

    return {"summary": summary}
