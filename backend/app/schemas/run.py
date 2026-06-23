from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.db.models import RunStatus


class RunStepRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sequence_no: int
    step_key: str
    step_name: str
    status: RunStatus
    output_payload: dict
    error_message: str | None
    started_at: datetime | None
    finished_at: datetime | None


class RunSummaryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    agent_id: uuid.UUID | None
    template_key: str
    trigger_source: str
    status: RunStatus
    error_message: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime


class RunDetailRead(RunSummaryRead):
    input_payload: dict
    output_payload: dict
    steps: list[RunStepRead]
