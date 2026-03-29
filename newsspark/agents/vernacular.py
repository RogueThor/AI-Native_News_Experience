"""
Agent 2 – Vernacular Adapter
Translates/adapts articles into Tamil or Hindi using Groq llama3-70b.
Uses SQLite cache to avoid redundant LLM calls.
"""

import os
import asyncio
from groq import Groq
from dotenv import load_dotenv

from db.sqlite import get_translation, save_translation, log_agent
from db.mongo import get_article_by_id

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

PROMPT_DIR = os.path.join(os.path.dirname(__file__), "..", "prompts")

_prompt_cache: dict[str, str] = {}


def _load_prompt(filename: str) -> str:
    if filename not in _prompt_cache:
        with open(os.path.join(PROMPT_DIR, filename), "r", encoding="utf-8") as f:
            _prompt_cache[filename] = f.read()
    return _prompt_cache[filename]


def _is_paywall(text: str) -> bool:
    """Detect NewsData.io (and similar) paywall placeholder text."""
    if not text:
        return True
    paywall_phrases = [
        "only available in",
        "available in paid",
        "paid plan",
        "upgrade to",
        "subscribe to",
    ]
    lower = text.lower()
    return any(p in lower for p in paywall_phrases)


def _adapt_sync(groq_client: Groq, article_text: str, language: str) -> str:
    """Synchronous Groq call – runs in executor."""
    if language == "tamil":
        template = _load_prompt("tamil_adapt.txt")
    elif language == "hindi":
        template = _load_prompt("hindi_adapt.txt")
    else:
        return article_text  # English – no adaptation needed

    prompt = template.replace("{article_text}", article_text)
    try:
        resp = groq_client.chat.completions.create(
            model=__import__('agents.model_config', fromlist=['QUALITY_MODEL']).QUALITY_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=1024,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"[Translation error: {e}]"


async def run_vernacular(state: dict) -> dict:
    """
    LangGraph-compatible agent node.
    state keys: article_id, language
    """
    article_id: str = state.get("article_id", "")
    language: str = state.get("language", "en")
    user_profile: dict = state.get("user_profile", {})

    # Resolve language from user profile if not explicitly set
    if not language or language == "en":
        language = user_profile.get("language_pref", "en")

    if language == "en":
        return {**state, "translated_text": None}

    # Check cache
    cached = await get_translation(article_id, language)
    if cached:
        await log_agent("vernacular", "cache_hit", article_id, f"lang={language}")
        return {**state, "translated_text": cached}

    # Fetch article
    article = await get_article_by_id(article_id)
    if not article:
        return {**state, "translated_text": "[Article not found]"}

    article_text = article.get("raw_text") or article.get("description") or article.get("title", "")

    # Strip paywall placeholder text that NewsData.io injects
    if _is_paywall(article_text):
        # Try other fields
        article_text = article.get("title", "")
        if not article_text:
            return {**state, "translated_text": "[Content not available for translation]"}

    groq_client = Groq(api_key=GROQ_API_KEY)
    loop = asyncio.get_event_loop()
    translated = await loop.run_in_executor(
        None, _adapt_sync, groq_client, article_text, language
    )

    await save_translation(article_id, language, translated)
    await log_agent(
        "vernacular", "translated",
        f"id={article_id} lang={language}",
        f"length={len(translated)}"
    )

    return {**state, "translated_text": translated}
