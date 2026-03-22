"""
sources/rss_fetcher.py
Fetches Indian news from multiple RSS feeds in parallel using feedparser.
Returns normalized article dicts.
"""

import asyncio
import hashlib
from datetime import datetime
from email.utils import parsedate_to_datetime

import feedparser

RSS_FEEDS = [
    ("Economic Times", "https://economictimes.indiatimes.com/rssfeedstopstories.cms"),
    ("Times of India", "https://timesofindia.indiatimes.com/rssfeeds/1898055.cms"),
    ("Moneycontrol", "https://www.moneycontrol.com/rss/MCtopnews.xml"),
    ("NDTV Profit", "https://feeds.feedburner.com/ndtvprofit-latest"),
    ("Livemint", "https://www.livemint.com/rss/news"),
    ("NDTV", "https://www.ndtv.com/rss"),
    ("BBC India", "http://feeds.bbci.co.uk/news/world/asia/india/rss.xml"),
]


def _parse_rss_date(entry) -> str:
    """Try multiple date fields and return ISO string."""
    for field in ["published", "updated", "created"]:
        val = entry.get(field)
        if val:
            try:
                return parsedate_to_datetime(val).isoformat()
            except Exception:
                return val
    return datetime.utcnow().isoformat()

def _extract_img(entry) -> str | None:
    """Extract image URL from feedparser entry if present."""
    for media in entry.get("media_content", []):
        if media.get("url"): return media["url"]
    for media in entry.get("media_thumbnail", []):
        if media.get("url"): return media["url"]
    for link in entry.get("links", []):
        if link.get("type", "").startswith("image/") and link.get("href"):
            return link["href"]
    for enc in entry.get("enclosures", []):
        if enc.get("type", "").startswith("image/") and enc.get("href"):
            return enc["href"]
    return None


def _fetch_feed_sync(source_name: str, url: str) -> list:
    """Synchronous feedparser call — runs in executor."""
    try:
        feed = feedparser.parse(url)
        articles = []
        for entry in feed.entries[:15]:
            title = entry.get("title", "").strip()
            url_val = entry.get("link", "").strip()
            if not title or not url_val:
                continue
            summary = entry.get("summary", "") or entry.get("description", "") or ""
            articles.append({
                "title": title,
                "content": summary[:1000],
                "url": url_val,
                "url_hash": hashlib.md5(url_val.encode()).hexdigest(),
                "source_name": source_name,
                "category": None,       # Will be classified by Groq
                "published_at": _parse_rss_date(entry),
                "sentiment": None,      # Will be classified by Groq
                "entities": [],
                "language": "en",
                "country": "in",
                "image_url": _extract_img(entry),
            })
        return articles
    except Exception as e:
        print(f"[RSS] Error fetching {source_name}: {e}")
        return []


async def fetch_all_rss() -> tuple[list, dict]:
    """
    Fetch all RSS feeds concurrently.
    Returns (articles_list, source_counts).
    """
    loop = asyncio.get_event_loop()
    tasks = [
        loop.run_in_executor(None, _fetch_feed_sync, name, url)
        for name, url in RSS_FEEDS
    ]
    results = await asyncio.gather(*tasks)

    all_articles = []
    source_counts = {}
    for i, articles in enumerate(results):
        name = RSS_FEEDS[i][0]
        source_counts[name] = len(articles)
        all_articles.extend(articles)

    print(f"[RSS] Fetched {len(all_articles)} articles from {len(RSS_FEEDS)} feeds")
    return all_articles, source_counts
