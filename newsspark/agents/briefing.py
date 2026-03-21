"""
Agent 5 – Briefing & Q&A Agent
Generates a comprehensive topic briefing and handles Q&A using Groq.
Uses SQLite cache for briefings.
"""

import os
import asyncio
from groq import Groq
from dotenv import load_dotenv

from db.mongo import get_articles_by_category, get_all_recent_articles
from db.sqlite import get_briefing, save_briefing, log_agent

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
PROMPT_DIR = os.path.join(os.path.dirname(__file__), "..", "prompts")


def _load_briefing_prompt() -> str:
    with open(os.path.join(PROMPT_DIR, "briefing.txt"), "r", encoding="utf-8") as f:
        return f.read()


def _call_groq_sync(groq_client: Groq, messages: list, max_tokens: int = 1024) -> str:
    """Synchronous Groq call – runs in executor."""
    try:
        resp = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.4,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"[LLM error: {e}]"


async def _get_topic_articles(topic: str) -> list:
    """Fetch top 5 articles relevant to a topic."""
    articles = await get_articles_by_category([topic], limit=5)
    if not articles:
        articles = await get_all_recent_articles(limit=5)
    return articles


def _format_articles(articles: list) -> str:
    lines = []
    for a in articles:
        lines.append(
            f"Title: {a.get('title','')}\n"
            f"Source: {a.get('source','')}\n"
            f"Description: {a.get('description','')}\n"
        )
    return "\n---\n".join(lines)


async def run_briefing(state: dict) -> dict:
    """
    LangGraph-compatible briefing node.
    state keys: topic, question (optional), request_type
    """
    topic: str = state.get("topic", "markets")
    question: str = state.get("question", "")
    request_type: str = state.get("request_type", "briefing")

    articles = await _get_topic_articles(topic)
    context = _format_articles(articles)
    groq_client = Groq(api_key=GROQ_API_KEY)
    loop = asyncio.get_event_loop()

    if request_type == "briefing":
        # Check cache first
        cached = await get_briefing(topic)
        if cached:
            await log_agent("briefing", "cache_hit", f"topic={topic}", f"len={len(cached)}")
            return {**state, "briefing_text": cached, "answer_text": None}

        template = _load_briefing_prompt()
        prompt = template.replace("{topic}", topic).replace("{context}", context)
        messages = [{"role": "user", "content": prompt}]
        result = await loop.run_in_executor(None, _call_groq_sync, groq_client, messages, 1024)

        await save_briefing(topic, result)
        await log_agent("briefing", "generated", f"topic={topic}", f"len={len(result)}")
        return {**state, "briefing_text": result, "answer_text": None}

    elif request_type == "ask":
        # Q&A: inject articles as context then answer the question
        system_msg = (
            f"You are a business news analyst. Use these articles about '{topic}' to answer "
            f"questions. Always cite the article title inline.\n\nArticles:\n{context}"
        )
        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": question},
        ]
        answer = await loop.run_in_executor(None, _call_groq_sync, groq_client, messages, 512)
        await log_agent("briefing", "qa_answered", f"topic={topic} q={question[:60]}", f"len={len(answer)}")
        return {**state, "answer_text": answer, "briefing_text": None}

    return {**state, "briefing_text": None, "answer_text": None}
