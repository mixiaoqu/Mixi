from __future__ import annotations

import uuid
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, Field, field_validator


class MixiChatHistoryItem(BaseModel):
    role: str = Field(min_length=1, max_length=20)
    content: str = Field(min_length=1, max_length=4000)


class MixiChatRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=4000)
    history: list[MixiChatHistoryItem] = Field(default_factory=list, max_length=20)
    state: "MixiConversationState" = Field(default_factory=lambda: MixiConversationState())


class MixiConversationState(BaseModel):
    conversation_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    timezone: str = Field(default="UTC", max_length=64)
    active_intent: str | None = Field(default=None, max_length=120)
    awaiting_confirmation: bool = False
    missing_fields: list[str] = Field(default_factory=list)
    checkpoint_thread_id: str | None = Field(default=None, max_length=160)

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError("timezone must be a valid IANA timezone") from exc
        return value
