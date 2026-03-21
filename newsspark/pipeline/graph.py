"""
Master LangGraph Orchestrator for NewsSpark.
Routes requests to the appropriate agent pipeline.
"""

from typing import Optional
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, END


# ── State definition ──────────────────────────────────────────────────────────

class NewsSparkState(TypedDict):
    request_type: str
    user_id: str
    user_profile: dict
    article_id: Optional[str]
    topic: Optional[str]
    question: Optional[str]
    language: Optional[str]
    articles: list
    arc_data: Optional[dict]
    translated_text: Optional[str]
    briefing_text: Optional[str]
    answer_text: Optional[str]
    feed: Optional[list]


# ── Import agents lazily to avoid circular imports ────────────────────────────

async def _agent_fetch(state: NewsSparkState) -> NewsSparkState:
    from agents.fetcher import run_fetcher
    return await run_fetcher(state)


async def _agent_vernacular(state: NewsSparkState) -> NewsSparkState:
    from agents.vernacular import run_vernacular
    return await run_vernacular(state)


async def _agent_story_arc(state: NewsSparkState) -> NewsSparkState:
    from agents.story_arc import run_story_arc
    return await run_story_arc(state)


async def _agent_personalize(state: NewsSparkState) -> NewsSparkState:
    from agents.personalize import run_personalize
    return await run_personalize(state)


async def _agent_briefing(state: NewsSparkState) -> NewsSparkState:
    from agents.briefing import run_briefing
    return await run_briefing(state)


# ── Routing logic ─────────────────────────────────────────────────────────────

def _route(state: NewsSparkState) -> str:
    rt = state.get("request_type", "feed")
    if rt == "translate":
        return "vernacular"
    if rt == "feed":
        return "personalize"
    if rt in ("briefing", "ask"):
        return "briefing"
    return "fetch"  # default → background/full pipeline


# ── Build graph ───────────────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    builder = StateGraph(NewsSparkState)

    # Add nodes
    builder.add_node("fetch", _agent_fetch)
    builder.add_node("story_arc", _agent_story_arc)
    builder.add_node("personalize", _agent_personalize)
    builder.add_node("briefing", _agent_briefing)
    builder.add_node("vernacular", _agent_vernacular)

    # Conditional entry from __start__
    builder.set_conditional_entry_point(
        _route,
        {
            "fetch": "fetch",
            "vernacular": "vernacular",
            "story_arc": "story_arc",
            "briefing": "briefing",
            "personalize": "personalize",
        },
    )

    # Feed pipeline: fetch → story_arc → personalize → END
    builder.add_edge("fetch", "story_arc")
    builder.add_edge("story_arc", "personalize")
    builder.add_edge("personalize", END)

    # Single-node pipelines
    builder.add_edge("vernacular", END)
    builder.add_edge("briefing", END)

    return builder.compile()


# Singleton compiled graph
graph = build_graph()


async def run_pipeline(state: dict) -> dict:
    """
    Execute the NewsSpark LangGraph pipeline with the given state.
    Returns the final state dict.
    """
    result = await graph.ainvoke(state)
    return result
