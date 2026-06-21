from __future__ import annotations

from pydantic import BaseModel, Field


class MixiChatRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=4000)
