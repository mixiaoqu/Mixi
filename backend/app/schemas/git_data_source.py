from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


AuthType = Literal["public", "token", "ssh"]


class GitConnectionInput(BaseModel):
    repository_url: str = Field(min_length=1, max_length=1024)
    auth_type: AuthType = "public"
    credential: str | None = Field(default=None, max_length=20_000)

    @model_validator(mode="after")
    def require_credential(self) -> "GitConnectionInput":
        if self.auth_type != "public" and not self.credential:
            raise ValueError("Credential is required for the selected authentication method")
        return self


class GitConnectionTest(GitConnectionInput):
    pass


class GitConnectionTestResult(BaseModel):
    repository_name: str
    branches: list[str]
    default_branch: str


class GitDataSourceCreate(GitConnectionInput):
    default_branch: str = Field(min_length=1, max_length=255)


class GitDataSourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    repository_url: str
    auth_type: AuthType
    default_branch: str
    status: str
    created_at: datetime
