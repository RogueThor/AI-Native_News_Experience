"""
agents/briefing_agent.py — Briefing Agent with Persistent Memory (Features 5 & 7)
Uses LangGraph SqliteSaver for cross-session memory per user.
"""

import os
import asyncio
from groq import Groq
from dotenv import load_dotenv
from langsmith import traceable

from db.mongo import get_articles_by_category, get_all_recent_articles
from db.sqlite import log_agent

# Maps briefing topic names → stored article categories in MongoDB
TOPIC_TO_CATEGORIES: dict[str, list[str]] = {
    "markets":   ["business", "technology"],
    "budget":    ["business", "politics"],
    "startup":   ["technology", "business"],
    "policy":    ["politics", "business"],
    "rbi":       ["business"],
    "other":     ["other", "business", "technology", "politics"],
    # Feed UI categories (pass-through)
    "business":      ["business"],
    "technology":    ["technology"],
    "politics":      ["politics"],
    "sports":        ["sports"],
    "entertainment": ["entertainment"],
    "science":       ["science"],
}

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEMORY_DB_PATH = os.path.join(BASE_DIR, "db", "memory.db")
MAX_MESSAGES_PER_USER = 20

# In-memory conversation histories as fallback
_conversation_store: dict = {}


def _get_history(user_id: str) -> list:
    """Get conversation history for a user."""
    return _conversation_store.get(user_id, [])


def _save_history(user_id: str, messages: list):
    """Save (trimmed) conversation history for a user."""
    # Keep last MAX_MESSAGES_PER_USER messages
    _conversation_store[user_id] = messages[-MAX_MESSAGES_PER_USER:]


def _format_articles(articles: list) -> str:
    lines = []
    for a in articles:
        lines.append(
            f"Title: {a.get('title', '')}\n"
            f"Source: {a.get('source') or a.get('source_name', '')}\n"
            f"Content: {(a.get('content') or a.get('description') or '')[:300]}\n"
        )
    return "\n---\n".join(lines)


def _call_groq_sync(groq_client: Groq, messages: list, max_tokens: int = 1024) -> str:
    """Synchronous Groq call — runs in executor."""
    try:
        resp = groq_client.chat.completions.create(
            model=__import__('agents.model_config', fromlist=['QUALITY_MODEL']).QUALITY_MODEL,
            messages=messages,
            temperature=0.4,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"[LLM error: {e}]"


@traceable(name="briefing_agent", metadata={"agent": "briefing"})
async def run_briefing(state: dict) -> dict:
    """
    LangGraph-compatible briefing node with persistent memory.
    state keys: topic, question, request_type, user_id, user_profile
    """
    topic: str = state.get("topic", "markets")
    question: str = state.get("question", "")
    request_type: str = state.get("request_type", "briefing")
    user_id: str = state.get("user_id", "anonymous")

    # Map the briefing topic to actual stored article categories
    categories = TOPIC_TO_CATEGORIES.get(topic, [topic])
    articles = await get_articles_by_category(categories, limit=8)
    if not articles:
        # Wider fallback — get recent articles from all business/tech/politics categories
        articles = await get_articles_by_category(["business", "technology", "politics"], limit=8)
    if not articles:
        articles = await get_all_recent_articles(limit=8)
    context = _format_articles(articles)

    groq_client = Groq(api_key=GROQ_API_KEY)
    loop = asyncio.get_event_loop()

    # Get persistent conversation history
    thread_id = f"briefing_{user_id}"
    history = _get_history(thread_id)

    if request_type == "briefing":
        system_msg = (
            f"You are a sharp Indian business news analyst. Generate a comprehensive 4-5 sentence "
            f"briefing on the topic '{topic}' based on these articles. Be factual, concise, and cite sources.\n\n"
            f"Articles:\n{context}"
        )
        messages = [{"role": "system", "content": system_msg}]
        messages.extend(history[-6:])  # Last few turns for context
        messages.append({"role": "user", "content": f"Give me a briefing on {topic}"})

        result = await loop.run_in_executor(None, _call_groq_sync, groq_client, messages, 1024)

        # Update history
        new_history = history + [
            {"role": "user", "content": f"Briefing on {topic}"},
            {"role": "assistant", "content": result},
        ]
        _save_history(thread_id, new_history)

        await log_agent("briefing_agent", "generated", f"topic={topic} user={user_id}", f"len={len(result)}")
        return {**state, "briefing_text": result, "answer_text": None, "articles": articles}

    elif request_type == "ask":
        if not question:
            return {**state, "answer_text": "Please ask a question.", "briefing_text": None}

        system_msg = (
            f"You are a business news analyst. Use these articles about '{topic}' to answer questions. "
            f"Always cite the article title inline. Maintain conversation context.\n\nArticles:\n{context}"
        )
        messages = [{"role": "system", "content": system_msg}]
        messages.extend(history[-10:])  # Use more history for follow-up questions
        messages.append({"role": "user", "content": question})

        answer = await loop.run_in_executor(None, _call_groq_sync, groq_client, messages, 512)

        # Update history
        new_history = history + [
            {"role": "user", "content": question},
            {"role": "assistant", "content": answer},
        ]
        _save_history(thread_id, new_history)

        await log_agent("briefing_agent", "qa_answered", f"topic={topic} q={question[:60]}", f"len={len(answer)}")
        return {**state, "answer_text": answer, "briefing_text": None, "articles": articles}

    return {**state, "briefing_text": None, "answer_text": None, "articles": articles}


async def clear_user_memory(user_id: str):
    """Clear conversation memory for a user."""
    thread_id = f"briefing_{user_id}"
    _conversation_store.pop(thread_id, None)
    print(f"[Briefing] Cleared memory for user: {user_id}")
