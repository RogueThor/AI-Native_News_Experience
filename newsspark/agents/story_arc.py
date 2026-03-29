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
    prompt = f"""You are a senior news editor for an Indian news platform.
Given the following list of news articles from a potential cluster, perform these tasks:
1. Determine the main cohesive "Story Arc" or "Topic Name" (e.g., "US-Iran Escalation", "Q3 Earnings Season").
2. Identify which article headlines are TRULY relevant to this specific narrative.
3. List key players mentioned in the relevant articles.
4. Provide a "What to watch next" prediction.

ARTICLES:
{articles_text}

Return ONLY a JSON object:
{{
  "topic_name": "human readable topic name",
  "relevant_headlines": ["headline 1", "headline 2"],
  "key_players": ["name 1", "name 2"],
  "what_to_watch_next": "one sentence prediction"
}}

Strictly filter out articles that are unrelated to the main topic (e.g. don't mix Bollywood with Politics).
Only return valid JSON, no explanation."""
    try:
        resp = groq_client.chat.completions.create(
            model=__import__('agents.model_config', fromlist=['QUALITY_MODEL']).QUALITY_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=2048,
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

    # Filter timeline and sentiment_trend based on relevant_headlines
    relevant_headlines = set(llm_result.get("relevant_headlines", []))
    
    timeline = []
    sentiment_trend = []
    
    # Sort articles by date
    sorted_articles = sorted(articles, key=lambda x: x.get("published_at", ""))
    
    for a in sorted_articles:
        title = a.get("title", "")
        # Fuzzy match or exact match check
        is_relevant = any(rh.lower() in title.lower() or title.lower() in rh.lower() for rh in relevant_headlines)
        
        if is_relevant or not relevant_headlines: # Fallback to all if LLM fails to provide list
            timeline.append({
                "date": a.get("published_at", "")[:10],
                "headline": title,
                "sentiment": a.get("sentiment", "neutral"),
            })
            
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
