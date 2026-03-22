"""
agents/multi_lens_agent.py — Multi-Perspective Analysis Agent (Feature 8)
Generates 3 parallel Groq perspectives: Common Man, Investor, Student.
"""

import os
import asyncio

from groq import Groq
from dotenv import load_dotenv
from langsmith import traceable

from db.sqlite import log_agent

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

LENSES_PROMPTS = {
    "common_man": """You are explaining Indian news to an average Indian citizen.
In exactly 3 simple Hindi-friendly English sentences, explain how this news affects daily life, prices, jobs, or routine:

{article_text}

Write only the 3 sentences, nothing else.""",

    "investor": """You are a SEBI-registered financial analyst.
In exactly 3 sentences, explain the market impact, which stocks/sectors are affected, and what action an Indian retail investor should consider:

{article_text}

Write only the 3 sentences, nothing else.""",

    "student": """You are a career counselor for Indian college students.
In exactly 3 sentences, explain what this news means for education, jobs, career paths, or skill development:

{article_text}

Write only the 3 sentences, nothing else.""",
}


def _call_groq_sync(groq_client: Groq, lens: str, article_text: str) -> tuple[str, str]:
    """Synchronous single-lens Groq call — runs in executor."""
    prompt = LENSES_PROMPTS[lens].replace("{article_text}", article_text[:1500])
    try:
        resp = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
            max_tokens=200,
        )
        return lens, resp.choices[0].message.content.strip()
    except Exception as e:
        return lens, f"[Error generating {lens} perspective: {e}]"


@traceable(name="multi_lens_agent", metadata={"agent": "multi_lens"})
async def generate_lenses(article_id: str, article_text: str) -> dict:
    """
    Generate 3 parallel perspectives for an article.
    All 3 Groq calls fire simultaneously via asyncio.gather.
    Results are cached in MongoDB.
    """
    # Check MongoDB cache first
    from db.mongo import get_article_lenses, update_article_lenses

    cached = await get_article_lenses(article_id)
    if cached:
        print(f"[MultiLens] Returning cached lenses for {article_id}")
        return cached

    groq_client = Groq(api_key=GROQ_API_KEY)
    loop = asyncio.get_event_loop()

    # Fire all 3 Groq calls simultaneously
    tasks = [
        loop.run_in_executor(None, _call_groq_sync, groq_client, lens, article_text)
        for lens in ("common_man", "investor", "student")
    ]
    results = await asyncio.gather(*tasks)

    lenses = {lens: text for lens, text in results}

    # Cache in MongoDB
    try:
        await update_article_lenses(article_id, lenses)
    except Exception as e:
        print(f"[MultiLens] Cache save error: {e}")

    await log_agent(
        "multi_lens_agent",
        "generate_lenses",
        f"article_id={article_id}",
        f"lenses={list(lenses.keys())}",
    )

    return lenses
