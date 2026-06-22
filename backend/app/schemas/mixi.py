from __future__ import annotations

from pydantic import BaseModel, Field


class MixiChatHistoryItem(BaseModel):
    role: str = Field(min_length=1, max_length=20)
    content: str = Field(min_length=1, max_length=4000)


class MixiChatRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=4000)
    history: list[MixiChatHistoryItem] = Field(default_factory=list, max_length=20)
