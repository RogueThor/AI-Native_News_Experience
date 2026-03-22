"""
sources/newsdata_fetcher.py
Fetches Indian news from NewsData.io free tier (200 req/day).
Returns normalized article dicts.
"""

import os
import asyncio
import hashlib
from datetime import datetime

import httpx
from dotenv import load_dotenv

load_dotenv()

NEWSDATA_API_KEY = os.getenv("NEWSDATA_API_KEY", "")
NEWSDATA_BASE_URL = "https://newsdata.io/api/1/news"

CATEGORIES = [
    "business", "technology", "sports", "entertainment",
    "politics", "health", "education", "crime"
]

CATEGORY_MAP = {
    "business": "business",
    "technology": "technology",
    "sports": "sports",
    "entertainment": "entertainment",
    "politics": "politics",
    "health": "health",
    "education": "education",
    "crime": "crime",
}


async def _fetch_category(client: httpx.AsyncClient, category: str) -> list:
    """Fetch one category from NewsData.io."""
    if not NEWSDATA_API_KEY:
        return []
    try:
        params = {
            "apikey": NEWSDATA_API_KEY,
            "country": "in",
            "language": "en",
            "category": category,
        }
        resp = await client.get(NEWSDATA_BASE_URL, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])
        articles = []
        for item in results[:10]:
            title = (item.get("title") or "").strip()
            url = (item.get("link") or "").strip()
            if not title or not url:
                continue
            pub_date = item.get("pubDate") or datetime.utcnow().isoformat()
            articles.append({
                "title": title,
                "content": (item.get("content") or item.get("description") or "")[:1000],
                "url": url,
                "url_hash": hashlib.md5(url.encode()).hexdigest(),
                "source_name": item.get("source_id", "NewsData"),
                "category": CATEGORY_MAP.get(category, category),
                "published_at": pub_date,
                "sentiment": item.get("sentiment"),
                "entities": [],
                "language": "en",
                "country": "in",
                "image_url": item.get("image_url"),
            })
        return articles
    except Exception as e:
        print(f"[NewsData] Error fetching category '{category}': {e}")
        return []


async def fetch_newsdata() -> tuple[list, dict]:
    """
    Fetch all NewsData.io categories concurrently.
    Returns (articles_list, source_counts).
    """
    if not NEWSDATA_API_KEY:
        print("[NewsData] No API key set, skipping.")
        return [], {}

    async with httpx.AsyncClient() as client:
        tasks = [_fetch_category(client, cat) for cat in CATEGORIES]
        results = await asyncio.gather(*tasks)

    all_articles = []
    source_counts = {}
    for i, articles in enumerate(results):
        cat = CATEGORIES[i]
        source_counts[f"NewsData-{cat}"] = len(articles)
        all_articles.extend(articles)

    print(f"[NewsData] Fetched {len(all_articles)} articles across {len(CATEGORIES)} categories")
    return all_articles, source_counts
