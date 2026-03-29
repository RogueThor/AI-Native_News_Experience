"""
pipeline/graph.py — Master LangGraph Orchestrator for NewsSpark.
Routes requests to agent pipeline. Now includes Critic Agent always after Briefing.
"""

from typing import Optional, List
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
    articles: List[dict]
    arc_data: Optional[dict]
    translated_text: Optional[str]
    briefing_text: Optional[str]
    answer_text: Optional[str]
    feed: Optional[list]
    critic_result: Optional[dict]
    critic_retry_count: int
    lenses: Optional[dict]
    chat_response: Optional[dict]


# ── Agent wrappers ────────────────────────────────────────────────────────────

async def _agent_fetch(state: NewsSparkState) -> NewsSparkState:
    from agents.fetcher_agent import run_fetcher
    return await run_fetcher(state)


async def _agent_vernacular(state: NewsSparkState) -> NewsSparkState:
    from agents.vernacular import run_vernacular
    return await run_vernacular(state)


async def _agent_story_arc(state: NewsSparkState) -> NewsSparkState:
    from agents.story_arc import run_story_arc
    return await run_story_arc(state)


async def _agent_personalize(state: NewsSparkState) -> NewsSparkState:
    from agents.personalize_agent import run_personalize
    return await run_personalize(state)


async def _agent_briefing(state: NewsSparkState) -> NewsSparkState:
    from agents.briefing_agent import run_briefing
    return await run_briefing(state)


async def _agent_critic(state: NewsSparkState) -> NewsSparkState:
    from agents.critic_agent import run_critic
    return await run_critic(state)


# ── Routing logic ─────────────────────────────────────────────────────────────

def _route(state: NewsSparkState) -> str:
    rt = state.get("request_type", "feed")
    if rt == "translate":
        return "vernacular"
    if rt == "feed":
        return "personalize"
    if rt in ("briefing", "ask"):
        return "briefing"
    if rt == "story_arc":
        return "story_arc"
    return "fetch"  # default -> full pipeline


# ── Build graph ───────────────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    builder = StateGraph(NewsSparkState)

    # Add nodes
    builder.add_node("fetch", _agent_fetch)
    builder.add_node("story_arc", _agent_story_arc)
    builder.add_node("personalize", _agent_personalize)
    builder.add_node("briefing", _agent_briefing)
    builder.add_node("critic", _agent_critic)
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

    # Feed pipeline: fetch -> story_arc -> personalize -> END
    builder.add_edge("fetch", "story_arc")
    builder.add_edge("story_arc", "personalize")
    builder.add_edge("personalize", END)

    # Briefing pipeline: briefing -> critic -> END (Critic NEVER skipped)
    builder.add_edge("briefing", "critic")
    builder.add_edge("critic", END)

    # Single-node pipelines
    builder.add_edge("vernacular", END)

    return builder.compile()


# Singleton compiled graph
graph = build_graph()


async def run_pipeline(state: dict) -> dict:
    """
    Execute the NewsSpark LangGraph pipeline with the given state.
    Returns the final state dict.
    """
    # Ensure required state fields have defaults
    full_state = {
        "request_type": "feed",
        "user_id": "",
        "user_profile": {},
        "article_id": None,
        "topic": None,
        "question": None,
        "language": "en",
        "articles": [],
        "arc_data": None,
        "translated_text": None,
        "briefing_text": None,
        "answer_text": None,
        "feed": None,
        "critic_result": None,
        "critic_retry_count": 0,
        "lenses": None,
        "chat_response": None,
        **state,
    }
    result = await graph.ainvoke(full_state)
    return result
