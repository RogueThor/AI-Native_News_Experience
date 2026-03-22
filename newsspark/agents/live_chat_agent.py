"""
agents/live_chat_agent.py — Live News Chatbot with ReAct (Feature 9)
Uses ChromaDB retriever + DuckDuckGo live search.
"""

import os
import json
import asyncio
from datetime import datetime, timedelta

from groq import Groq
from dotenv import load_dotenv
from langsmith import traceable

from db.sqlite import log_agent

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

CHAT_SYSTEM_PROMPT = """You are an AI news assistant for NewsSpark, an Indian news platform.

You have access to two information sources:
1. Stored articles (ChromaDB) - articles ingested by NewsSpark
2. Live web search (DuckDuckGo) - real-time results

DECISION LOGIC:
- First search ChromaDB for stored articles on the topic
- If all results are older than 24 hours OR fewer than 3 relevant results → use DuckDuckGo
- Combine both sources if needed for comprehensive answer

RESPONSE FORMAT — You MUST always respond with this exact JSON structure:
{
  "topic": "extracted topic name",
  "timeline": [
    {"date": "Mar 22", "headline": "...", "sentiment": "positive|negative|neutral"},
    ...
  ],
  "summary": "3-line narrative summary of the full story",
  "sources": ["source1", "source2"]
}

Provide 3-6 timeline items minimum. Be specific with dates and facts.
Focus on India-relevant news."""


def _ddg_search_sync(query: str, max_results: int = 5) -> list:
    """Synchronous DuckDuckGo search — runs in executor."""
    try:
        from duckduckgo_search import DDGS
        results = []
        with DDGS() as ddgs:
            for r in ddgs.news(f"{query} India", max_results=max_results):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "body": r.get("body", ""),
                    "published": r.get("date", ""),
                    "source": r.get("source", "DuckDuckGo"),
                })
        return results
    except Exception as e:
        print(f"[LiveChat] DuckDuckGo error: {e}")
        return []


def _chroma_search_sync(query: str, k: int = 5) -> list:
    """Synchronous ChromaDB search — runs in executor."""
    try:
        from db.chroma import similarity_search
        return similarity_search(query, k=k)
    except Exception as e:
        print(f"[LiveChat] ChromaDB search error: {e}")
        return []


def _are_results_fresh(results: list, hours: int = 24) -> bool:
    """Check if any result is fresher than N hours."""
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    for r in results:
        pub = r.get("published_at") or r.get("published") or ""
        if pub:
            try:
                # Try ISO format
                pub_dt = datetime.fromisoformat(pub.replace("Z", "+00:00").replace("+00:00", ""))
                if pub_dt > cutoff:
                    return True
            except Exception:
                pass
    return False


def _build_context(chroma_results: list, ddg_results: list) -> str:
    """Build context string from search results for LLM."""
    context = ""
    if chroma_results:
        context += "=== STORED ARTICLES ===\n"
        for r in chroma_results[:5]:
            context += f"Title: {r.get('title', '')}\nDate: {r.get('published_at', '')}\nContent: {r.get('content', '')[:300]}\n\n"

    if ddg_results:
        context += "=== LIVE WEB SEARCH ===\n"
        for r in ddg_results[:5]:
            context += f"Title: {r.get('title', '')}\nDate: {r.get('published', '')}\nContent: {r.get('body', '')[:300]}\nSource: {r.get('source', '')}\n\n"

    return context.strip()


def _call_groq_chat_sync(groq_client: Groq, messages: list) -> str:
    """Synchronous Groq call for chat — runs in executor."""
    try:
        resp = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            temperature=0.4,
            max_tokens=800,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return json.dumps({
            "topic": "Error",
            "timeline": [],
            "summary": f"Error generating response: {e}",
            "sources": [],
        })


@traceable(name="live_chat_agent", metadata={"agent": "live_chat"})
async def run_live_chat(user_message: str, user_id: str = "anonymous") -> dict:
    """
    ReAct-style live chat agent.
    1. Search ChromaDB
    2. Check freshness → DuckDuckGo if stale/insufficient
    3. Combine sources and generate structured response
    """
    loop = asyncio.get_event_loop()

    # Step 1: ChromaDB search
    chroma_results = await loop.run_in_executor(None, _chroma_search_sync, user_message, 5)
    use_ddg = False

    # Step 2: Decide if we need live search
    if len(chroma_results) < 3:
        print(f"[LiveChat] ChromaDB returned {len(chroma_results)} results → using DuckDuckGo")
        use_ddg = True
    elif not _are_results_fresh(chroma_results, hours=24):
        print("[LiveChat] Results are stale → using DuckDuckGo")
        use_ddg = True

    ddg_results = []
    if use_ddg:
        ddg_results = await loop.run_in_executor(None, _ddg_search_sync, user_message, 5)

    # Step 3: Build context and generate response
    context = _build_context(chroma_results, ddg_results)

    sources = list({
        r.get("source", "NewsSpark") for r in (chroma_results + ddg_results)
        if r.get("source")
    })

    groq_client = Groq(api_key=GROQ_API_KEY)
    messages = [
        {"role": "system", "content": CHAT_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"User question: {user_message}\n\n{context}\n\nRespond with the JSON format specified.",
        },
    ]

    raw_response = await loop.run_in_executor(None, _call_groq_chat_sync, groq_client, messages)

    # Parse JSON response
    try:
        # Strip markdown fences
        if "```" in raw_response:
            parts = raw_response.split("```")
            for p in parts:
                p = p.strip()
                if p.startswith("json"):
                    p = p[4:].strip()
                if p.startswith("{"):
                    raw_response = p
                    break
        start = raw_response.find("{")
        end = raw_response.rfind("}") + 1
        if start != -1 and end > start:
            parsed = json.loads(raw_response[start:end])
        else:
            parsed = {
                "topic": user_message[:50],
                "timeline": [],
                "summary": raw_response[:500],
                "sources": sources,
            }
    except json.JSONDecodeError:
        parsed = {
            "topic": user_message[:50],
            "timeline": [],
            "summary": raw_response[:500],
            "sources": sources,
        }

    parsed["sources"] = parsed.get("sources") or sources
    parsed["_meta"] = {
        "chroma_count": len(chroma_results),
        "ddg_count": len(ddg_results),
        "used_live_search": use_ddg,
    }

    await log_agent(
        "live_chat_agent",
        "chat_response",
        f"user={user_id} query={user_message[:60]}",
        f"chroma={len(chroma_results)} ddg={len(ddg_results)}",
    )

    return parsed
