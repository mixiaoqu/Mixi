from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.services.time_range import resolve_named_kind, resolve_time_range
from app.tools.business.base import BusinessTool


class TimeRangeResolveInput(BaseModel):
    texts: list[str] = Field(default_factory=list, min_length=1)
    now: datetime
    named_kind: str | None = Field(default=None, max_length=64)


class TimeRangeResolveOutput(BaseModel):
    start_at: datetime | None = None
    end_at: datetime | None = None
    label: str | None = None
    source_text: str | None = None
    matched: bool


class TimeRangeResolveTool(BusinessTool[TimeRangeResolveInput, TimeRangeResolveOutput]):
    key = "time_range_resolve"
    name = "Resolve Time Range"
    description = "Resolve natural-language time expressions into a concrete time range."
    input_schema = TimeRangeResolveInput

    async def execute(self, payload: TimeRangeResolveInput) -> TimeRangeResolveOutput:
        current = payload.now.astimezone()
        resolved = resolve_time_range(payload.texts, current)
        if resolved is None and payload.named_kind:
            resolved = resolve_named_kind(payload.named_kind, current, payload.texts[0])
        if resolved is None:
            return TimeRangeResolveOutput(matched=False)
        return TimeRangeResolveOutput(
            start_at=resolved.start_at,
            end_at=resolved.end_at,
            label=resolved.label,
            source_text=resolved.source_text,
            matched=True,
        )
