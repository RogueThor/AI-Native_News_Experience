"""
Agent 4 – Personalization Agent
Filters articles by user role and interests, and builds the feed.
"""

import asyncio
from db.mongo import get_articles_by_category, get_all_recent_articles
from db.sqlite import log_session, log_agent

ROLE_CATEGORIES = {
    "investor": ["markets", "rbi", "policy"],
    "student": ["markets", "budget", "startup", "policy", "rbi", "other"],
    "startup": ["startup", "policy", "other"],
    "salaried": ["budget", "policy", "markets"],
}


def _serialize_article(doc: dict) -> dict:
    """Convert MongoDB doc to JSON-serializable dict."""
    out = dict(doc)
    if "_id" in out:
        out["_id"] = str(out["_id"])
    return out


async def run_personalize(state: dict) -> dict:
    """
    LangGraph-compatible personalization node.
    state keys: user_id, user_profile
    Returns: state with feed populated.
    """
    user_id: str = state.get("user_id", "")
    user_profile: dict = state.get("user_profile", {})
    role: str = user_profile.get("role", "student")

    categories = ROLE_CATEGORIES.get(role, list(ROLE_CATEGORIES["student"]))

    # Fetch articles from MongoDB
    articles = await get_articles_by_category(categories, limit=20)
    if not articles:
        articles = await get_all_recent_articles(limit=20)

    # Take top 10
    articles = articles[:10]

    async def _process_item(article):
        item = _serialize_article(article)
        article_id = item.get("_id", "")
        
        # Log session activity
        if user_id and article_id:
            await log_session(user_id, article_id, "view")
        return item

    # Process all articles in parallel
    feed_items = await asyncio.gather(*[_process_item(a) for a in articles])

    await log_agent(
        "personalize",
        "build_feed",
        f"user={user_id} role={role}",
        f"articles={len(feed_items)}",
    )

    return {**state, "feed": list(feed_items)}
