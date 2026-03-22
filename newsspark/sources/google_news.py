"""
sources/google_news.py
Fetches Indian news from Google News via pygooglenews.
Returns normalized article dicts.
"""

import asyncio
import hashlib
from datetime import datetime

TOPICS = ["BUSINESS", "TECHNOLOGY", "SPORTS", "NATION"]


def _fetch_topic_sync(topic: str) -> list:
    """Synchronous pygooglenews fetch — runs in executor."""
    try:
        from pygooglenews import GoogleNews
        gn = GoogleNews(country="IN", lang="en")
        result = gn.topic_headlines(topic)
        entries = result.get("entries", [])
        articles = []
        for entry in entries[:10]:
            title = entry.get("title", "").strip()
            url = entry.get("link", "").strip()
            if not title or not url:
                continue
            # Google news titles include source: "Title - Source"
            clean_title = title.rsplit(" - ", 1)[0] if " - " in title else title
            source_part = title.rsplit(" - ", 1)[-1] if " - " in title else "Google News"
            published = ""
            if entry.get("published"):
                try:
                    from email.utils import parsedate_to_datetime
                    published = parsedate_to_datetime(entry["published"]).isoformat()
                except Exception:
                    published = entry.get("published", datetime.utcnow().isoformat())
            else:
                published = datetime.utcnow().isoformat()

            articles.append({
                "title": clean_title,
                "content": entry.get("summary", "")[:1000],
                "url": url,
                "url_hash": hashlib.md5(url.encode()).hexdigest(),
                "source_name": f"GoogleNews-{source_part}",
                "category": topic.lower(),
                "published_at": published,
                "sentiment": None,
                "entities": [],
                "language": "en",
                "country": "in",
                "image_url": None,
            })
        return articles
    except Exception as e:
        print(f"[GoogleNews] Error fetching topic {topic}: {e}")
        return []


async def fetch_google_news() -> tuple[list, dict]:
    """
    Fetch Google News for all topics concurrently.
    Returns (articles_list, source_counts).
    """
    loop = asyncio.get_event_loop()
    tasks = [loop.run_in_executor(None, _fetch_topic_sync, topic) for topic in TOPICS]
    results = await asyncio.gather(*tasks)

    all_articles = []
    source_counts = {}
    for i, articles in enumerate(results):
        topic = TOPICS[i]
        source_counts[f"GoogleNews-{topic}"] = len(articles)
        all_articles.extend(articles)

    print(f"[GoogleNews] Fetched {len(all_articles)} articles across {len(TOPICS)} topics")
    return all_articles, source_counts
