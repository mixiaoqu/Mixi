from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.db.models import AgentStatus


class AgentCreate(BaseModel):
    slug: str = Field(min_length=1, max_length=80, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None
    system_prompt: str | None = None
    llm_model: str = Field(default="gpt-4.1-mini", min_length=1, max_length=80)
    config: dict = Field(default_factory=dict)


class AgentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    system_prompt: str | None = None
    llm_model: str | None = Field(default=None, min_length=1, max_length=80)
    status: AgentStatus | None = None
    config: dict | None = None

    @field_validator("name", "llm_model", "status", "config")
    @classmethod
    def required_fields_cannot_be_null(cls, value: object) -> object:
        if value is None:
            raise ValueError("cannot be null")
        return value


class AgentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    slug: str
    name: str
    description: str | None
    system_prompt: str | None
    llm_model: str
    status: AgentStatus
    config: dict
    created_at: datetime
    updated_at: datetime
