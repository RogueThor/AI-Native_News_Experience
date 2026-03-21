"""
Agent 3 – Story Arc Builder
Fetches all articles for a cluster, calls Groq to produce an arc,
builds timeline + sentiment_trend, and upserts to MongoDB.
"""

import os
import json
import asyncio
from datetime import datetime
from groq import Groq
from dotenv import load_dotenv

from db.mongo import (
    get_articles_by_cluster,
    upsert_story_arc,
    get_story_arc,
)
from db.sqlite import log_agent

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
PROMPT_DIR = os.path.join(os.path.dirname(__file__), "..", "prompts")

_SENTIMENT_SCORE = {"positive": 1.0, "neutral": 0.0, "negative": -1.0}


def _load_prompt() -> str:
    with open(os.path.join(PROMPT_DIR, "arc_builder.txt"), "r", encoding="utf-8") as f:
        return f.read()


def _build_arc_sync(groq_client: Groq, articles_text: str) -> dict:
    """Synchronous Groq call."""
    template = _load_prompt()
    prompt = template.replace("{articles_text}", articles_text)
    try:
        resp = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=512,
        )
        raw = resp.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw)
    except Exception as e:
        return {
            "topic_name": "Unknown Topic",
            "key_players": [],
            "what_to_watch_next": "Unable to generate arc",
        }


async def build_arc_for_topic(topic: str) -> dict:
    """Build or refresh the story arc for a topic key. Returns arc dict."""
    articles = await get_articles_by_cluster(topic, limit=15)
    if not articles:
        return {}

    # Build articles text for LLM
    lines = []
    for a in articles:
        lines.append(
            f"[{a.get('published_at','')[:10]}] {a.get('title','')} – {a.get('description','')}"
        )
    articles_text = "\n".join(lines)

    groq_client = Groq(api_key=GROQ_API_KEY)
    loop = asyncio.get_event_loop()
    llm_result = await loop.run_in_executor(
        None, _build_arc_sync, groq_client, articles_text
    )

    # Build timeline from articles (no LLM)
    timeline = []
    for a in sorted(articles, key=lambda x: x.get("published_at", "")):
        timeline.append({
            "date": a.get("published_at", "")[:10],
            "headline": a.get("title", ""),
            "sentiment": a.get("sentiment", "neutral"),
        })

    # Build sentiment_trend
    sentiment_trend = []
    for a in sorted(articles, key=lambda x: x.get("published_at", "")):
        score = _SENTIMENT_SCORE.get(a.get("sentiment", "neutral"), 0.0)
        sentiment_trend.append({
            "date": a.get("published_at", "")[:10],
            "score": score,
        })

    arc = {
        "_id": topic,
        "topic_name": llm_result.get("topic_name", topic),
        "timeline": timeline,
        "key_players": llm_result.get("key_players", []),
        "sentiment_trend": sentiment_trend,
        "what_to_watch_next": llm_result.get("what_to_watch_next", ""),
        "last_updated": datetime.utcnow().isoformat(),
    }

    await upsert_story_arc(arc.copy())
    await log_agent(
        "story_arc",
        "build_arc",
        f"topic={topic} articles={len(articles)}",
        f"players={len(arc['key_players'])}",
    )
    return arc


async def run_story_arc(state: dict) -> dict:
    """LangGraph-compatible node."""
    topic: str = state.get("topic", "")
    if not topic:
        return {**state, "arc_data": None}

    arc = await build_arc_for_topic(topic)
    return {**state, "arc_data": arc}
