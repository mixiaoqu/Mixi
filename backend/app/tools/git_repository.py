from __future__ import annotations

import asyncio
import uuid
from datetime import datetime

from cryptography.fernet import InvalidToken
from pydantic import BaseModel, Field, model_validator

from app.db.repositories.git_data_source import GitDataSourceRepository
from app.services.git_remote import GitConnectionError, decrypt_credential, list_remote_commits
from app.tools.base import AgentTool, ToolContext, ToolExecutionError, ToolPermissionError


class GitListCommitsInput(BaseModel):
    data_source_id: uuid.UUID
    start_at: datetime
    end_at: datetime
    branch: str | None = Field(default=None, max_length=255)
    limit: int = Field(default=50, ge=1, le=100)

    @model_validator(mode="after")
    def validate_range(self) -> "GitListCommitsInput":
        if self.start_at.tzinfo is None or self.end_at.tzinfo is None:
            raise ValueError("start_at and end_at must include a timezone")
        if self.end_at <= self.start_at:
            raise ValueError("end_at must be later than start_at")
        return self


class GitCommitResult(BaseModel):
    sha: str
    author_name: str
    author_email: str
    authored_at: datetime
    subject: str


class GitListCommitsOutput(BaseModel):
    data_source_id: uuid.UUID
    repository_name: str
    branch: str
    commits: list[GitCommitResult]


class GitListCommitsTool(AgentTool[GitListCommitsInput, GitListCommitsOutput]):
    key = "git_list_commits"
    name = "读取 Git 提交"
    description = "读取本次任务已授权 Git 数据源在指定时间范围内的提交记录。"
    input_schema = GitListCommitsInput

    def __init__(self, data_sources: GitDataSourceRepository):
        self.data_sources = data_sources

    async def execute(self, payload: GitListCommitsInput, context: ToolContext) -> GitListCommitsOutput:
        if payload.data_source_id not in context.allowed_data_source_ids:
            raise ToolPermissionError("当前任务未授权此 Git 数据源")

        source = self.data_sources.get(payload.data_source_id)
        if source is None or source.user_id != context.user_id:
            raise ToolPermissionError("Git 数据源不存在或不属于当前用户")
        if source.status != "connected":
            raise ToolExecutionError("Git 数据源当前不可用")

        try:
            credential = decrypt_credential(source.encrypted_credential)
            commits = await asyncio.to_thread(
                list_remote_commits,
                repository_url=source.repository_url,
                auth_type=source.auth_type,
                credential=credential,
                branch=payload.branch or source.default_branch,
                start_at=payload.start_at,
                end_at=payload.end_at,
                limit=payload.limit,
            )
        except InvalidToken as exc:
            raise ToolExecutionError("Git 数据源凭证无法解密") from exc
        except GitConnectionError as exc:
            raise ToolExecutionError(str(exc)) from exc

        branch = payload.branch or source.default_branch
        return GitListCommitsOutput(
            data_source_id=source.id,
            repository_name=source.name,
            branch=branch,
            commits=[GitCommitResult.model_validate(commit, from_attributes=True) for commit in commits],
        )
