"""Pydantic model for a news article."""

from pydantic import BaseModel, Field
from typing import Optional


class Article(BaseModel):
    title: str
    url: str
    description: Optional[str] = ""
    raw_text: Optional[str] = ""
    category: Optional[str] = "other"
    sentiment: Optional[str] = "neutral"
    story_cluster_id: Optional[str] = ""
    image_url: Optional[str] = None
    published_at: Optional[str] = ""
    source: Optional[str] = ""
