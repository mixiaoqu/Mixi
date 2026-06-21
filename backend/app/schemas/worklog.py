from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from app.db.models import RunStatus


class WorklogGenerateRequest(BaseModel):
    data_source_id: uuid.UUID
    start_at: datetime
    end_at: datetime
    branch: str | None = Field(default=None, max_length=255)
    commit_limit: int = Field(default=20, ge=1, le=100)
    user_prompt: str | None = Field(default=None, max_length=2000)
    non_code_notes: list[str] = Field(default_factory=list, max_length=50)

    @model_validator(mode="after")
    def validate_range(self) -> "WorklogGenerateRequest":
        if self.start_at.tzinfo is None or self.end_at.tzinfo is None:
            raise ValueError("start_at and end_at must include a timezone")
        if self.end_at <= self.start_at:
            raise ValueError("end_at must be later than start_at")
        return self


class WorklogCommitRead(BaseModel):
    sha: str
    author_name: str
    authored_at: datetime
    subject: str


class WorklogGenerateResponse(BaseModel):
    workflow_run_id: uuid.UUID
    agent_id: uuid.UUID
    workspace_id: uuid.UUID
    status: RunStatus
    title: str
    summary: str
    markdown: str
    branch: str
    commit_count: int
    commits: list[WorklogCommitRead]
    non_code_notes: list[str]
