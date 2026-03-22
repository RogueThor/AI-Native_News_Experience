"""
agents/personalize_agent.py — Agentic RAG Personalization (Feature 3)
Uses ChromaDB MMR retrieval + user behavior vectors to return diverse, relevant articles.
"""

import asyncio
from langsmith import traceable
from db.mongo import get_articles_by_category, get_all_recent_articles
from db.sqlite import log_agent


def _serialize_article(doc: dict) -> dict:
    """Convert MongoDB doc to JSON-serializable dict."""
    out = dict(doc)
    if "_id" in out:
        out["_id"] = str(out["_id"])
    return out


def _build_interest_categories(user_profile: dict) -> list:
    """
    Derive target categories from user profile:
    - Uses explicit interests list
    - Falls back to role-based categories
    - Deprioritizes skipped categories
    """
    from db.demo_users import ROLE_CATEGORIES, INTEREST_CATEGORY_MAP

    role = user_profile.get("role", "general")
    interests = user_profile.get("interests", [])
    behavior = user_profile.get("behavior", {})
    skipped = behavior.get("skipped_categories", {})

    # Map interests to categories
    interest_cats = []
    for interest in interests:
        cat = INTEREST_CATEGORY_MAP.get(interest.lower())
        if cat and cat not in interest_cats:
            interest_cats.append(cat)

    # Fall back to role categories
    if not interest_cats:
        interest_cats = ROLE_CATEGORIES.get(role, ["business", "technology"])

    # Remove heavily skipped categories (skipped > 5 times)
    filtered = [c for c in interest_cats if skipped.get(c, 0) < 5]
    return filtered if filtered else interest_cats


def _chroma_rag_search(user_profile: dict, categories: list) -> list:
    """Synchronous ChromaDB similarity/MMR search — runs in executor."""
    try:
        from db.chroma import similarity_search

        role = user_profile.get("role", "general")
        query = f"latest Indian news about {' and '.join(categories[:3])}"

        results = similarity_search(query, k=20, categories=categories)
        return results
    except Exception as e:
        print(f"[Personalize] ChromaDB search error: {e}")
        return []


@traceable(name="personalize_agent", metadata={"agent": "personalize"})
async def run_personalize(state: dict) -> dict:
    """
    Agentic RAG personalization node.
    1. Determine target categories from user profile + behavior
    2. ChromaDB MMR search for relevant articles
    3. Fall back to MongoDB if ChromaDB returns < 5 results
    4. Return top 20 diverse articles
    """
    user_id: str = state.get("user_id", "")
    user_profile: dict = state.get("user_profile", {})
    category_filter: str = state.get("topic") # From the new UI tabs

    # If a specific category is requested (not 'top'), do a clean category fetch
    if category_filter and category_filter != "top":
        print(f"[Personalize] Category mode: {category_filter}")
        from db.mongo import get_articles_by_category
        articles = await get_articles_by_category([category_filter], limit=20)
        feed_items = [_serialize_article(a) for a in articles]
        return {**state, "feed": feed_items}

    # Otherwise, proceed with Personalised RAG (Top Stories)
    categories = _build_interest_categories(user_profile)

    # Try ChromaDB first (Agentic RAG)
    loop = asyncio.get_event_loop()
    chroma_results = await loop.run_in_executor(
        None, _chroma_rag_search, user_profile, categories
    )

    feed_items = []

    if len(chroma_results) >= 5:
        # Fetch full rich documents from MongoDB using ChromaDB IDs
        article_ids = [r.get("article_id") for r in chroma_results[:20] if r.get("article_id")]
        
        from db.mongo import get_articles_by_ids
        articles = await get_articles_by_ids(article_ids)
        feed_items = [_serialize_article(a) for a in articles]
        
        print(f"[Personalize] RAG returned {len(feed_items)} articles")
    else:
        # Fallback to MongoDB
        print(f"[Personalize] ChromaDB returned {len(chroma_results)} — falling back to MongoDB")
        from db.mongo import get_articles_by_category, get_all_recent_articles
        articles = await get_articles_by_category(categories, limit=20)
        if not articles:
            articles = await get_all_recent_articles(limit=20)
        feed_items = [_serialize_article(a) for a in articles[:20]]

    await log_agent(
        "personalize_agent",
        "rag_feed",
        f"user={user_id} categories={categories}",
        f"articles={len(feed_items)}",
    )

    return {**state, "feed": feed_items}
