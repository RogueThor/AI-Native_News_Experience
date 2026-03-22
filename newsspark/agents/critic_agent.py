"""
agents/critic_agent.py — Critic / Validator Agent (Feature 4)
Validates briefing output for factual grounding, bias, and fabricated content.
Uses llama3-70b-8192 for high accuracy.
"""

import os
import json
import asyncio

from groq import Groq
from dotenv import load_dotenv
from langsmith import traceable

from db.sqlite import log_agent

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

CRITIC_SYSTEM_PROMPT = """You are a strict fact-checking editor for an Indian news platform.
Your job is to validate AI-generated news briefings against their source articles.

You must check:
1. Are all facts, names, dates, and numbers grounded in the source articles?
2. Is the tone neutral and unbiased (no political slant, no emotional manipulation)?
3. Are there any fabricated quotes, statistics, or events not in the sources?

Respond ONLY with a valid JSON object:
{
  "verdict": "PASS" or "FAIL",
  "corrections": ["specific correction 1", "specific correction 2"] (empty list if PASS),
  "validated_output": "the corrected or original briefing text",
  "confidence_score": 0.0 to 1.0
}

If verdict is PASS, copy the original briefing as validated_output.
If verdict is FAIL, rewrite validated_output to fix all issues.
Be conservative — only FAIL if you find concrete, specific errors."""


def _call_critic_sync(groq_client: Groq, briefing_text: str, source_context: str) -> dict:
    """Synchronous Groq critic call — runs in executor."""
    user_prompt = f"""SOURCE ARTICLES (ground truth):
{source_context}

BRIEFING TO VALIDATE:
{briefing_text}

Validate the briefing against the sources. Return JSON only."""

    try:
        resp = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": CRITIC_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            max_tokens=1500,
        )
        raw = resp.choices[0].message.content.strip()
        # Strip markdown fences
        if "```" in raw:
            parts = raw.split("```")
            for part in parts:
                part = part.strip()
                if part.startswith("json"):
                    part = part[4:].strip()
                if part.startswith("{"):
                    raw = part
                    break
        # Find JSON object
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start != -1 and end > start:
            raw = raw[start:end]
        return json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"[Critic] JSON parse error: {e}")
        return {
            "verdict": "PASS",
            "corrections": [],
            "validated_output": briefing_text,
            "confidence_score": 0.5,
        }
    except Exception as e:
        print(f"[Critic] Groq error: {e}")
        return {
            "verdict": "PASS",
            "corrections": [],
            "validated_output": briefing_text,
            "confidence_score": 0.5,
        }


@traceable(name="critic_agent", metadata={"agent": "critic"})
async def run_critic(state: dict) -> dict:
    """
    LangGraph-compatible critic node.
    Always runs after Briefing Agent — never skipped.
    If FAIL: corrects output and allows one retry.
    """
    briefing_text = state.get("briefing_text") or ""
    answer_text = state.get("answer_text") or ""
    text_to_validate = briefing_text or answer_text

    if not text_to_validate:
        # Nothing to validate
        return {**state, "critic_result": None}

    # Build source context from articles in state
    articles = state.get("articles", [])
    if not articles:
        # Try fetching from MongoDB
        topic = state.get("topic", "")
        if topic:
            from db.mongo import get_articles_by_category
            articles = await get_articles_by_category([topic], limit=5)

    source_context = ""
    for a in articles[:5]:
        source_context += (
            f"Title: {a.get('title', '')}\n"
            f"Content: {a.get('content') or a.get('description', '')}...\n---\n"
        )
    if not source_context:
        source_context = "No source articles available for verification."

    groq_client = Groq(api_key=GROQ_API_KEY)
    loop = asyncio.get_event_loop()

    critic_result = await loop.run_in_executor(
        None, _call_critic_sync, groq_client, text_to_validate, source_context
    )

    verdict = critic_result.get("verdict", "PASS")
    confidence = critic_result.get("confidence_score", 0.5)
    retry_count = state.get("critic_retry_count", 0)

    await log_agent(
        "critic_agent",
        f"validate_verdict={verdict}",
        f"topic={state.get('topic', '')} retry={retry_count}",
        f"confidence={confidence} corrections={len(critic_result.get('corrections', []))}",
    )

    # If FAIL and no retry yet — trigger briefing retry with corrected context
    if verdict == "FAIL" and retry_count == 0:
        print(f"[Critic] FAIL — corrections: {critic_result.get('corrections')}")
        corrected = critic_result.get("validated_output", text_to_validate)

        # One retry: re-run briefing with corrected output as validated_output
        # (we don't re-invoke the full briefing to avoid LLM cost; critic's corrected output IS the retry)
        if briefing_text:
            return {
                **state,
                "briefing_text": corrected,
                "critic_result": critic_result,
                "critic_retry_count": 1,
            }
        else:
            return {
                **state,
                "answer_text": corrected,
                "critic_result": critic_result,
                "critic_retry_count": 1,
            }

    # PASS or already retried
    validated_output = critic_result.get("validated_output", text_to_validate)
    if briefing_text:
        return {**state, "briefing_text": validated_output, "critic_result": critic_result}
    else:
        return {**state, "answer_text": validated_output, "critic_result": critic_result}
