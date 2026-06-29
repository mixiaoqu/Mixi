from __future__ import annotations

from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from app.services.worklog_refiner import OpenAIWorklogRefiner, WorklogRefinementInput, WorklogRefinementResult
from app.tools.business.base import BusinessTool


class WorklogRefinePayload(BaseModel):
    agent_name: str = Field(min_length=1, max_length=255)
    title: str = Field(min_length=1, max_length=255)
    summary: str = Field(min_length=1, max_length=2000)
    markdown: str = Field(min_length=1, max_length=50000)
    user_prompt: str | None = Field(default=None, max_length=4000)
    repository_name: str = Field(min_length=1, max_length=255)
    branch: str = Field(min_length=1, max_length=255)
    commit_count: int = Field(ge=0, le=10000)
    non_code_notes: list[str] = Field(default_factory=list)
    commits: list[dict[str, object]] = Field(default_factory=list)


class WorklogRefineTool(BusinessTool[WorklogRefinePayload, WorklogRefinementResult]):
    key = "worklog_refine"
    name = "Refine Worklog"
    description = "Refine a worklog draft with an LLM."
    input_schema = WorklogRefinePayload

    def __init__(self, client: AsyncOpenAI):
        self.refiner = OpenAIWorklogRefiner(client)

    async def execute(self, payload: WorklogRefinePayload) -> WorklogRefinementResult:
        return await self.refiner.refine(
            WorklogRefinementInput(
                agent_name=payload.agent_name,
                title=payload.title,
                summary=payload.summary,
                markdown=payload.markdown,
                user_prompt=payload.user_prompt,
                repository_name=payload.repository_name,
                branch=payload.branch,
                commit_count=payload.commit_count,
                non_code_notes=list(payload.non_code_notes),
                commits=list(payload.commits),
            )
        )
