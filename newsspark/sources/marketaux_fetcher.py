"""
sources/marketaux_fetcher.py
Fetches Indian financial and business news from Marketaux free tier.
Returns normalized article dicts.
"""

import asyncio
import hashlib
from datetime import datetime

import httpx

MARKETAUX_BASE_URL = "https://api.marketaux.com/v1/news/all"


async def fetch_marketaux() -> tuple[list, dict]:
    """
    Fetch Indian financial news from Marketaux.
    Uses the public/demo endpoint that doesn't require an API key (basic access).
    Returns (articles_list, source_counts).
    """
    try:
        params = {
            "countries": "in",
            "language": "en",
            "filter_entities": "true",
            "limit": 20,
            "published_after": "",  # No date filter for maximum coverage
        }
        # Remove empty params
        params = {k: v for k, v in params.items() if v}

        async with httpx.AsyncClient() as client:
            resp = await client.get(MARKETAUX_BASE_URL, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()

        articles = []
        for item in data.get("data", [])[:20]:
            title = (item.get("title") or "").strip()
            url = (item.get("url") or "").strip()
            if not title or not url:
                continue

            # Extract entities
            entities = []
            for ent in item.get("entities", []):
                if ent.get("name"):
                    entities.append(ent["name"])

            articles.append({
                "title": title,
                "content": (item.get("description") or "")[:1000],
                "url": url,
                "url_hash": hashlib.md5(url.encode()).hexdigest(),
                "source_name": item.get("source", "Marketaux"),
                "category": "business",
                "published_at": item.get("published_at") or datetime.utcnow().isoformat(),
                "sentiment": _map_sentiment(item.get("sentiment")),
                "entities": entities[:10],
                "language": "en",
                "country": "in",
                "image_url": item.get("image_url"),
            })

        source_counts = {"Marketaux": len(articles)}
        print(f"[Marketaux] Fetched {len(articles)} articles")
        return articles, source_counts

    except Exception as e:
        print(f"[Marketaux] Error: {e}")
        return [], {}


def _map_sentiment(raw) -> str | None:
    """Map Marketaux sentiment score to label."""
    if raw is None:
        return None
    try:
        score = float(raw)
        if score > 0.1:
            return "positive"
        elif score < -0.1:
            return "negative"
        else:
            return "neutral"
    except (TypeError, ValueError):
        if isinstance(raw, str):
            return raw.lower() if raw.lower() in ("positive", "negative", "neutral") else None
        return None
