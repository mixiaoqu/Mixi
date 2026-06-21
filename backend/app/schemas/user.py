from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class UserCreate(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    display_name: str = Field(min_length=1, max_length=120)
    avatar_url: str | None = Field(default=None, max_length=512)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized.count("@") != 1 or " " in normalized:
            raise ValueError("must be a valid email address")
        return normalized


class UserUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    avatar_url: str | None = Field(default=None, max_length=512)

    @field_validator("display_name")
    @classmethod
    def display_name_cannot_be_null(cls, value: str | None) -> str | None:
        if value is None:
            raise ValueError("cannot be null")
        return value


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    display_name: str
    auth_provider: str
    avatar_url: str | None
    last_login_at: datetime | None
    created_at: datetime
    updated_at: datetime
