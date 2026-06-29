from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.tools.business.base import BusinessTool


class WorklogRenderCommit(BaseModel):
    sha: str
    author_name: str
    authored_at: datetime
    subject: str
    changed_files: list[str] = Field(default_factory=list)


class WorklogRenderInput(BaseModel):
    agent_name: str = Field(min_length=1, max_length=255)
    start_at: datetime
    end_at: datetime
    commits: list[WorklogRenderCommit] = Field(default_factory=list)
    non_code_notes: list[str] = Field(default_factory=list)
    report_kind: Literal["daily", "period"] | None = None

    @model_validator(mode="after")
    def validate_range(self) -> "WorklogRenderInput":
        if self.start_at.tzinfo is None or self.end_at.tzinfo is None:
            raise ValueError("start_at and end_at must include a timezone")
        if self.end_at <= self.start_at:
            raise ValueError("end_at must be later than start_at")
        return self


class WorklogRenderOutput(BaseModel):
    title: str
    summary: str
    markdown: str
    report_kind: Literal["daily", "period"]


class WorklogRenderTool(BusinessTool[WorklogRenderInput, WorklogRenderOutput]):
    key = "worklog_render"
    name = "Render Worklog"
    description = "Generate a worklog draft from commits and non-code notes."
    input_schema = WorklogRenderInput

    async def execute(self, payload: WorklogRenderInput) -> WorklogRenderOutput:
        report_kind = payload.report_kind or infer_report_kind(payload.start_at, payload.end_at)
        title, summary, markdown = compose_worklog_markdown(
            agent_name=payload.agent_name,
            start_at=payload.start_at,
            end_at=payload.end_at,
            commits=payload.commits,
            non_code_notes=normalize_non_code_notes(payload.non_code_notes),
            report_kind=report_kind,
        )
        return WorklogRenderOutput(
            title=title,
            summary=summary,
            markdown=markdown,
            report_kind=report_kind,
        )


def infer_report_kind(start_at: datetime, end_at: datetime) -> Literal["daily", "period"]:
    return "daily" if start_at.astimezone().date() == end_at.astimezone().date() else "period"


def normalize_non_code_notes(notes: list[str]) -> list[str]:
    return [note.strip() for note in notes if note.strip()]


def compose_worklog_markdown(
    *,
    agent_name: str,
    start_at: datetime,
    end_at: datetime,
    commits: list[WorklogRenderCommit],
    non_code_notes: list[str],
    report_kind: Literal["daily", "period"],
) -> tuple[str, str, str]:
    start_local = start_at.astimezone()
    end_local = end_at.astimezone()
    day_label = start_local.strftime("%Y-%m-%d")
    period_label = f"{start_local.strftime('%Y-%m-%d')} to {end_local.strftime('%Y-%m-%d')}"
    time_range = f"{start_local.strftime('%H:%M')} - {end_local.strftime('%H:%M')}"
    commit_count = len(commits)
    note_count = len(non_code_notes)

    summary_parts: list[str] = []
    if commit_count:
        summary_parts.append(f"Summarized {commit_count} code commits")
    if note_count:
        summary_parts.append(f"captured {note_count} non-code notes")
    if not summary_parts:
        summary_parts.append("No new code activity was detected in the selected time range")

    summary = "; ".join(summary_parts) + "."
    title = f"{day_label} Worklog" if report_kind == "daily" else f"{period_label} Worklog"
    lines = [
        f"# {title}",
        "",
        f"> Generated for {agent_name}; window: {day_label if report_kind == 'daily' else period_label} {time_range}",
        "",
        "## Overview",
    ]
    if commit_count:
        lines.append(f"- Built from {commit_count} commit records in the selected time range.")
    else:
        lines.append("- No Git commits were detected in the selected time range.")

    lines.extend(["", "## Completed Work"])
    if commits:
        for commit in commits:
            files = ", ".join(commit.changed_files[:3])
            suffix = f" (files: {files})" if files else ""
            lines.append(f"- {commit.subject}{suffix}")
    else:
        lines.append("- No code changes were collected from Git.")

    lines.extend(["", "## Technical Notes"])
    if commits:
        lines.append("- Commit metadata is available and can be extended with diff-level analysis.")
    else:
        lines.append("- No new implementation details were observed in the selected window.")

    lines.extend(["", "## Goals And Value"])
    lines.append("- Goal details can be expanded with task context when needed.")

    lines.extend(
        [
            "",
            "## Risks Or Blockers",
            "- No explicit risks or blockers were captured in the current draft.",
            "",
            "## Follow-up",
            "- Add next-step details if the workflow or task context requires them.",
        ]
    )

    if non_code_notes:
        lines.extend(["", "## Notes"])
        lines.extend(f"- {note}" for note in non_code_notes)

    return title, summary, "\n".join(lines)
