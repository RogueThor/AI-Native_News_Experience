"""
Agent 1 – News Fetcher & Classifier
Fetches Indian business news via NewsAPI, classifies each article
using Groq llama3-8b-8192, and saves to MongoDB.
Scheduled via APScheduler every 30 minutes.
"""

import os
import json
import asyncio
from datetime import datetime
from newsapi import NewsApiClient
from groq import Groq
from dotenv import load_dotenv

from db.mongo import save_article
from db.sqlite import log_agent

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "")

CLASSIFY_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "..", "prompts", "classify.txt")
BATCH_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "..", "prompts", "batch_classify.txt")

_classify_template: str = ""


def _batch_classify_articles(groq_client: Groq, articles: list) -> list:
    """Call Groq to classify a batch of articles in one go."""
    with open(BATCH_PROMPT_PATH, "r", encoding="utf-8") as f:
        template = f.read()
    
    # Format articles for the prompt
    articles_text = ""
    for idx, a in enumerate(articles):
        articles_text += f"[{idx}] Title: {a['title']}\nDesc: {a['description']}\n\n"
    
    prompt = template.replace("{articles_text}", articles_text)
    
    try:
        resp = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=2000,
        )
        raw = resp.choices[0].message.content.strip()
        # Strip markdown code fences
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"): raw = raw[4:].strip()
        
        results = json.loads(raw)
        # Ensure we have a result for each article
        if not isinstance(results, list): return []
        return results
    except Exception as e:
        print(f"[Fetcher] Batch classification error: {e}")
        return []


async def run_fetcher(state: dict) -> dict:
    """
    LangGraph-compatible agent node.
    Fetches India business headlines, classifies, and persists them.
    """
    articles_saved = 0
    articles_skipped = 0

    try:
        newsapi = NewsApiClient(api_key=NEWSAPI_KEY)
        groq_client = Groq(api_key=GROQ_API_KEY)

        response = newsapi.get_top_headlines(
            country="in",
            category="business",
            page_size=20,
        )

        articles_raw = response.get("articles", [])
        print(f"[Fetcher] Top headlines found: {len(articles_raw)}")

        # Fallback to general search if top headlines is empty (common in free tier)
        if not articles_raw:
            print("[Fetcher] No top headlines. Falling back to 'get_everything'...")
            response = newsapi.get_everything(
                q='business AND (India OR Mumbai OR Nifty OR Sensex)',
                language='en',
                sort_by='publishedAt',
                page_size=20
            )
            articles_raw = response.get("articles", [])
            print(f"[Fetcher] Everything search found: {len(articles_raw)}")

        # Parallel processing via batching
        to_process = []
        for item in articles_raw:
            title = item.get("title") or ""
            desc  = item.get("description") or ""
            url   = item.get("url") or ""
            if not title or not url:
                articles_skipped += 1
                continue
            to_process.append(item)

        if not to_process:
            return {**state, "articles": []}

        # Chunk articles into batches of 10 for better reliability
        batch_size = 10
        for i in range(0, len(to_process), batch_size):
            batch = to_process[i : i + batch_size]
            print(f"[Fetcher] Batch classifying {len(batch)} articles (Chunk {i//batch_size + 1})...")
            
            loop = asyncio.get_event_loop()
            classifications = await loop.run_in_executor(
                None, _batch_classify_articles, groq_client, batch
            )

            # Fallback for failed batch
            if not classifications:
                classifications = [{ "category": "other", "sentiment": "neutral", "story_cluster_id": "general_news" }] * len(batch)

            async def _save(item, cls):
                nonlocal articles_saved
                try:
                    doc = {
                        "title": item.get("title"),
                        "url": item.get("url"),
                        "description": item.get("description"),
                        "raw_text": item.get("description"),
                        "category": cls.get("category", "other"),
                        "sentiment": cls.get("sentiment", "neutral"),
                        "story_cluster_id": cls.get("story_cluster_id", "general_news"),
                        "image_url": item.get("urlToImage"),
                        "published_at": item.get("publishedAt") or datetime.utcnow().isoformat(),
                        "source": item.get("source", {}).get("name", "Unknown"),
                    }
                    await save_article(doc)
                    articles_saved += 1
                except Exception:
                    pass

            # Concurrent saves for this batch
            tasks = []
            for j, item in enumerate(batch):
                cls = classifications[j] if j < len(classifications) else classifications[-1]
                tasks.append(_save(item, cls))
            
            await asyncio.gather(*tasks)

        await log_agent(
            agent_name="fetcher",
            action="batch_fetch_and_classify",
            input_summary=f"Count: {len(to_process)}",
            output_summary=f"saved={articles_saved} skipped={articles_skipped}",
        )

    except Exception as e:
        await log_agent(
            agent_name="fetcher",
            action="error",
            input_summary="",
            output_summary=str(e),
        )

    return {**state, "articles": []}


async def scheduled_fetch():
    """Entry point for APScheduler – runs the fetcher standalone."""
    print("[Fetcher] scheduled_fetch called.")
    await run_fetcher({})
