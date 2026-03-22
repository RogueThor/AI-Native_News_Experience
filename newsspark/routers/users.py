"""
routers/users.py — User profile, interaction tracking, and memory management (Features 3 & 7)
"""

from fastapi import APIRouter, Request, Depends, HTTPException

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


@router.post("/interaction")
async def track_interaction(
    request: Request,
    user: dict = Depends(get_current_user),
):
    """
    Track user interaction with an article.
    Payload: {user_id, article_id, action: "read"|"skip"|"bookmark"|"share"}
    """
    from db.mongo import get_article_by_id, update_user_behavior, add_user_bookmark

    body = await request.json()
    article_id = body.get("article_id", "")
    action = body.get("action", "read")
    user_id = str(user.get("_id", ""))

    if action not in ("read", "skip", "bookmark", "share"):
        raise HTTPException(status_code=400, detail="Invalid action")

    # Get article for category/source info
    article = await get_article_by_id(article_id)
    category = article.get("category", "") if article else ""
    source = article.get("source") or article.get("source_name", "") if article else ""

    # Update behavior
    await update_user_behavior(user_id, action, category, source)

    if action == "bookmark" and article_id:
        await add_user_bookmark(user_id, article_id)

    return {"status": "ok", "action": action, "article_id": article_id}


@router.post("/briefing/clear/{user_id}")
async def clear_briefing_memory(
    user_id: str,
    request: Request,
    user: dict = Depends(get_current_user),
):
    """Clear persistent conversation memory for a user."""
    from agents.briefing_agent import clear_user_memory

    # Only allow users to clear their own memory (or admin in future)
    current_user_id = str(user.get("_id", ""))
    if current_user_id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden")

    await clear_user_memory(user_id)
    return {"status": "ok", "message": f"Memory cleared for user {user_id}"}


@router.get("/user/me")
async def get_profile(request: Request, user: dict = Depends(get_current_user)):
    """Return current user profile."""
    out = dict(user)
    if "_id" in out:
        out["_id"] = str(out["_id"])
    return out
