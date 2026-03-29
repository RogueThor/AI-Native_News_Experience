"""
agents/fetcher_agent.py — Multi-Source News Fetcher & Classifier (Feature 1)
Fetches Indian news from 4 parallel sources, deduplicates, normalizes,
classifies via Groq, saves to MongoDB, then ingests into ChromaDB.
"""

import os
import json
import asyncio
import hashlib
from datetime import datetime
from bs4 import BeautifulSoup

from groq import Groq
from dotenv import load_dotenv
from langsmith import traceable

from db.mongo import save_article
from db.sqlite import log_agent

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "")


def _clean_content(raw_html: str) -> tuple[str, str | None]:
    """Strip HTML tags and return (plain_text, first_img_url)."""
    if not raw_html:
        return "", None
    soup = BeautifulSoup(raw_html, "html.parser")
    # Extract first image if exists
    img = soup.find("img")
    img_url = img.get("src") if img else None
    # Strip tags
    text = soup.get_text(separator=" ").strip()
    return text, img_url


# Maps any classifier output category to a valid UI category
_CATEGORY_NORMALISE: dict[str, str] = {
    "health":        "science",
    "education":     "science",
    "crime":         "politics",
    "markets":       "business",
    "startup":       "technology",
    "rbi":           "business",
    "budget":        "business",
    "policy":        "politics",
    "finance":       "business",
    "economy":       "business",
    "bollywood":     "entertainment",
    "cricket":       "sports",
    "ipl":           "sports",
}

VALID_CATEGORIES = frozenset([
    "business", "technology", "sports", "entertainment",
    "politics", "science", "other"
])


def _normalise_category(cat: str) -> str:
    """Map any category to a valid UI category key."""
    cat = (cat or "other").lower().strip()
    cat = _CATEGORY_NORMALISE.get(cat, cat)
    return cat if cat in VALID_CATEGORIES else "other"

def _batch_classify_sync(groq_client: Groq, articles: list) -> list:
    """
    Classify a batch of articles via Groq (category + sentiment).
    Returns list of {category, sentiment} dicts.
    """
    if not articles:
        return []

    lines = ""
    for i, a in enumerate(articles):
        lines += f"[{i}] Title: {a.get('title', '')}\nContent: {a.get('content', '')[:200]}\n\n"

    prompt = f"""You are a news classifier for Indian articles.
For each article below, return a JSON array where each element has:
- "category": STRICTLY one of: business|technology|sports|entertainment|politics|science|other
  Rules: financial/economy/market → business, cricket/ipl/football → sports,
  films/bollywood/celebs → entertainment, government/election/law → politics,
  health/environment → science, AI/software/startup → technology.
- "sentiment": one of positive|negative|neutral
- "story_slug": a 2-3 word lowercased slug for the specific news story (e.g. "cricket-ipl-2024", "isro-launch"). 
  Articles about the EXACT same news event MUST have the SAME slug!

ARTICLES:
{lines}

Return ONLY a JSON array with {len(articles)} objects in order, no extra text.
Example: [{{"category":"business","sentiment":"neutral","story_slug":"stock-market-crash"}}]"""

    try:
        resp = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",  # 8b for bulk classification (saves 70b daily quota)
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=300,
        )
        raw = resp.choices[0].message.content.strip()
        # Find the first '[' and last ']' to extract the JSON array
        start = raw.find("[")
        end = raw.rfind("]")
        if start != -1 and end != -1:
            raw = raw[start:end+1]
        
        try:
            results = json.loads(raw)
        except json.JSONDecodeError:
            # Try removing common junk like trailing commas before ]
            import re
            raw = re.sub(r",\s*\]", "]", raw)
            results = json.loads(raw)

        if not isinstance(results, list):
            return []
        # Normalise categories to valid UI values
        for r in results:
            if isinstance(r, dict):
                r["category"] = _normalise_category(r.get("category", "other"))
        return results
    except Exception as e:
        print(f"[Fetcher] Batch classify error: {e}")
        return []


# ── NewsAPI fallback ──────────────────────────────────────────────────────────

async def _fetch_newsapi_fallback() -> list:
    """NewsAPI fallback — used only when all other sources fail."""
    try:
        from newsapi import NewsApiClient
        import hashlib
        loop = asyncio.get_event_loop()

        def _call():
            client = NewsApiClient(api_key=NEWSAPI_KEY)
            resp = client.get_top_headlines(country="in", category="business", page_size=20)
            articles = resp.get("articles", [])
            if not articles:
                resp = client.get_everything(
                    q="business AND (India OR Mumbai)",
                    language="en",
                    sort_by="publishedAt",
                    page_size=20,
                )
                articles = resp.get("articles", [])
            return articles

        raw = await loop.run_in_executor(None, _call)
        normalized = []
        for item in raw:
            title = (item.get("title") or "").strip()
            url = (item.get("url") or "").strip()
            if not title or not url:
                continue
            normalized.append({
                "title": title,
                "content": (item.get("description") or "")[:1000],
                "url": url,
                "url_hash": hashlib.md5(url.encode()).hexdigest(),
                "source_name": item.get("source", {}).get("name", "NewsAPI"),
                "category": "business",
                "published_at": item.get("publishedAt") or datetime.utcnow().isoformat(),
                "sentiment": "neutral",
                "entities": [],
                "language": "en",
                "country": "in",
                "image_url": item.get("urlToImage"),
            })
        print(f"[Fetcher] NewsAPI fallback: {len(normalized)} articles")
        return normalized
    except Exception as e:
        print(f"[Fetcher] NewsAPI fallback error: {e}")
        return []


# ── Main fetcher node ─────────────────────────────────────────────────────────

@traceable(name="fetcher_agent", metadata={"agent": "fetcher"})
async def run_fetcher(state: dict) -> dict:
    """
    LangGraph-compatible node.
    Fetches from all 4 sources in parallel, deduplicates, classifies, saves.
    """
    articles_saved = 0
    articles_skipped = 0
    all_source_counts = {}

    try:
        # ── 1. Parallel fetch from all sources ────────────────────────────────
        from sources.rss_fetcher import fetch_all_rss
        from sources.google_news import fetch_google_news
        from sources.newsdata_fetcher import fetch_newsdata
        from sources.marketaux_fetcher import fetch_marketaux

        rss_result, google_result, newsdata_result, marketaux_result = await asyncio.gather(
            fetch_all_rss(),
            fetch_google_news(),
            fetch_newsdata(),
            fetch_marketaux(),
            return_exceptions=True,
        )

        def _safe(result, default=([], {})):
            return result if not isinstance(result, Exception) else default

        rss_articles, rss_counts = _safe(rss_result)
        google_articles, google_counts = _safe(google_result)
        newsdata_articles, newsdata_counts = _safe(newsdata_result)
        marketaux_articles, marketaux_counts = _safe(marketaux_result)

        all_source_counts.update(rss_counts)
        all_source_counts.update(google_counts)
        all_source_counts.update(newsdata_counts)
        all_source_counts.update(marketaux_counts)

        combined = rss_articles + google_articles + newsdata_articles + marketaux_articles
        print(f"[Fetcher] Total combined (before dedup): {len(combined)}")

        # ── 2. Fallback if all sources returned < 5 articles ─────────────────
        if len(combined) < 5:
            print("[Fetcher] All sources returned < 5 articles. Activating NewsAPI fallback.")
            fallback = await _fetch_newsapi_fallback()
            combined.extend(fallback)
            all_source_counts["NewsAPI-fallback"] = len(fallback)

        # ── 3. Dedup by MD5 of URL ────────────────────────────────────────────
        seen_hashes = set()
        unique_articles = []
        for a in combined:
            url_hash = a.get("url_hash") or hashlib.md5(a.get("url", "").encode()).hexdigest()
            if url_hash and url_hash not in seen_hashes:
                seen_hashes.add(url_hash)
                a["url_hash"] = url_hash
                unique_articles.append(a)

        print(f"[Fetcher] After dedup: {len(unique_articles)} unique articles")

        # ── 4. Classify RSS articles (those without category/sentiment) ────────
        groq_client = Groq(api_key=GROQ_API_KEY)
        # Process any article that is missing category, sentiment, OR story_slug
        to_classify = [a for a in unique_articles if not a.get("category") or not a.get("sentiment") or not a.get("story_slug")]

        loop = asyncio.get_event_loop()
        # Process ALL articles now that we have unique slug logic
        articles_to_process = to_classify
        batch_size = 10
        classify_map = {}

        for i in range(0, len(articles_to_process), batch_size):
            batch = articles_to_process[i: i + batch_size]
            classifications = await loop.run_in_executor(
                None, _batch_classify_sync, groq_client, batch
            )
            if not classifications:
                classifications = [{"category": "other", "sentiment": "neutral"}] * len(batch)
            for j, art in enumerate(batch):
                cls = classifications[j] if j < len(classifications) else classifications[-1] if classifications else {}
                classify_map[art["url_hash"]] = cls

        # Merge classifications
        for a in unique_articles:
            cls = classify_map.get(a.get("url_hash"), {})
            if cls.get("category") and not a.get("category"):
                a["category"] = _normalise_category(cls["category"])
            if cls.get("sentiment") and not a.get("sentiment"):
                a["sentiment"] = cls["sentiment"]
            if cls.get("story_slug"):
                a["story_slug"] = cls["story_slug"].strip().lower().replace(" ", "-")
            
            # Final normalisation
            a["category"] = _normalise_category(a.get("category", "other"))
            a.setdefault("sentiment", "neutral")
            
            # If still no slug, use a short hash of title to keep it unique but stable
            if not a.get("story_slug") or a["story_slug"] == "general":
                import hashlib
                title_hash = hashlib.md5(a.get("title", "").encode()).hexdigest()[:8]
                a["story_slug"] = f"news-{title_hash}"

            a["story_cluster_id"] = f"{a.get('category', 'other')}_{a['story_slug']}"

        # ── 4.5. Fuzzy Match Titles to Merge LLM Slugs Across Batches ────────
        from difflib import SequenceMatcher
        def similar(a, b):
            return SequenceMatcher(None, a, b).ratio()
        
        for i in range(len(unique_articles)):
            for j in range(i+1, len(unique_articles)):
                if similar(unique_articles[i]["title"], unique_articles[j]["title"]) > 0.45:
                    slug1 = unique_articles[i].get("story_slug")
                    slug2 = unique_articles[j].get("story_slug")
                    
                    if slug1 and not slug1.startswith("news-"):
                        unique_articles[j]["story_slug"] = slug1
                        unique_articles[j]["story_cluster_id"] = f"{unique_articles[j].get('category', 'other')}_{slug1}"
                    elif slug2 and not slug2.startswith("news-"):
                        unique_articles[i]["story_slug"] = slug2
                        unique_articles[i]["story_cluster_id"] = f"{unique_articles[i].get('category', 'other')}_{slug2}"

        # ── 4.6. Clear Story Cluster ID for Singletons ───────────────────────
        cluster_counts = {}
        for a in unique_articles:
            cid = a.get("story_cluster_id")
            if cid:
                cluster_counts[cid] = cluster_counts.get(cid, 0) + 1
        
        for a in unique_articles:
            cid = a.get("story_cluster_id")
            if cid and cluster_counts[cid] < 2:
                a["story_cluster_id"] = None

        # ── 5. Save to MongoDB + ChromaDB ────────────────────────────────────
        async def _save_article(article: dict):
            nonlocal articles_saved, articles_skipped
            try:
                raw_desc = article.get("content", "") or article.get("description", "")
                text, extracted_img = _clean_content(raw_desc)
                
                doc = {
                    "url_hash": article.get("url_hash", ""),  # crucial for stable mock _id
                    "title": article.get("title", ""),
                    "url": article.get("url", ""),
                    "content": text[:5000],
                    "raw_text": text,
                    "description": text[:500],
                    "category": article.get("category", "other"),
                    "sentiment": article.get("sentiment", "neutral"),
                    "story_slug": article.get("story_slug", "general"),
                    # REMOVED date from ID to allow multi-day arcs!
                    "story_cluster_id": f"{article.get('category', 'other')}_{article.get('story_slug', 'general').strip() or 'general'}",
                    "source": article.get("source_name", "Unknown"),
                    "source_name": article.get("source_name", "Unknown"),
                    "published_at": article.get("published_at", datetime.utcnow().isoformat()),
                    "entities": article.get("entities", []),
                    "language": article.get("language", "en"),
                    "country": article.get("country", "in"),
                    "image_url": article.get("image_url") or extracted_img,
                }
                saved_doc = await save_article(doc)
                if saved_doc:  # Returns the doc with _id if newly saved
                    articles_saved += 1
                    # Ingest into ChromaDB after MongoDB save
                    try:
                        from db.chroma import ingest_article
                        chroma_doc = dict(doc)
                        if saved_doc.get("_id"):
                            chroma_doc["_id"] = saved_doc["_id"]
                        await asyncio.get_event_loop().run_in_executor(
                            None, ingest_article, chroma_doc
                        )
                    except Exception as ce:
                        print(f"[Fetcher] ChromaDB ingest error: {ce}")
                else:
                    articles_skipped += 1
            except Exception as e:
                articles_skipped += 1

        await asyncio.gather(*[_save_article(a) for a in unique_articles])

        await log_agent(
            agent_name="fetcher_agent",
            action="multi_source_fetch",
            input_summary=f"sources={list(all_source_counts.keys())}",
            output_summary=f"saved={articles_saved} skipped={articles_skipped} total={len(unique_articles)}",
        )

        print(f"[Fetcher] Done: saved={articles_saved}, skipped={articles_skipped}")
        print(f"[Fetcher] Source counts: {all_source_counts}")

        # Push to active WebSocket connections
        try:
            from routers.feed import notify_ws_users_new_articles
            await notify_ws_users_new_articles(unique_articles[:articles_saved])
        except Exception:
            pass  # WebSocket push is best-effort

    except Exception as e:
        import traceback
        print(f"[Fetcher] Fatal error: {e}")
        traceback.print_exc()
        await log_agent("fetcher_agent", "error", "", str(e))

    return {**state, "articles": []}


async def scheduled_fetch():
    """Entry point for APScheduler."""
    print("[Fetcher] scheduled_fetch called.")
    await run_fetcher({})
