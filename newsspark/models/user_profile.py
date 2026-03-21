"""Pydantic model for a User Profile."""

from pydantic import BaseModel
from typing import List, Optional


class UserProfile(BaseModel):
    user_id: str
    name: str
    role: str
    language_pref: str = "en"
    avatar: Optional[str] = "👤"
    interests: List[str] = []
    reading_history: List[str] = []
