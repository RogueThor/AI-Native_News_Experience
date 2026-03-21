"""Pydantic model for a Story Arc."""

from pydantic import BaseModel
from typing import List, Optional


class TimelineEntry(BaseModel):
    date: str
    headline: str
    sentiment: str


class SentimentPoint(BaseModel):
    date: str
    score: float


class StoryArc(BaseModel):
    id: str  # topic key (snake_case)
    topic_name: str
    timeline: List[TimelineEntry] = []
    key_players: List[str] = []
    sentiment_trend: List[SentimentPoint] = []
    what_to_watch_next: Optional[str] = ""
    last_updated: Optional[str] = ""
