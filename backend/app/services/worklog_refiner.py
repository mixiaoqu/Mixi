from __future__ import annotations

import json
from dataclasses import dataclass

from openai import AsyncOpenAI

from app.core.config import settings


@dataclass(frozen=True, slots=True)
class WorklogRefinementInput:
    agent_name: str
    title: str
    summary: str
    markdown: str
    user_prompt: str | None
    repository_name: str
    branch: str
    commit_count: int
    non_code_notes: list[str]


@dataclass(frozen=True, slots=True)
class WorklogRefinementResult:
    title: str
    summary: str
    markdown: str


class WorklogRefiner:
    async def refine(self, payload: WorklogRefinementInput) -> WorklogRefinementResult:
        raise NotImplementedError


class OpenAIWorklogRefiner(WorklogRefiner):
    def __init__(self, client: AsyncOpenAI):
        self.client = client

    async def refine(self, payload: WorklogRefinementInput) -> WorklogRefinementResult:
        prompt = {
            "agent_name": payload.agent_name,
            "title": payload.title,
            "summary": payload.summary,
            "markdown": payload.markdown,
            "user_prompt": payload.user_prompt,
            "repository_name": payload.repository_name,
            "branch": payload.branch,
            "commit_count": payload.commit_count,
            "non_code_notes": payload.non_code_notes,
        }
        completion = await self.client.chat.completions.create(
            model=settings.openai_model,
            temperature=0.2,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "你是工作日志润色助手。"
                        "请基于已有草稿做轻量优化，不要虚构新的事实，不要新增不存在的任务。"
                        "保留 Markdown 结构，只优化表达、顺序和可读性。"
                        "返回 JSON 对象，字段必须为 title、summary、markdown。"
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(prompt, ensure_ascii=False),
                },
            ],
        )
        content = completion.choices[0].message.content or "{}"
        data = json.loads(content)
        return WorklogRefinementResult(
            title=str(data.get("title") or payload.title).strip() or payload.title,
            summary=str(data.get("summary") or payload.summary).strip() or payload.summary,
            markdown=str(data.get("markdown") or payload.markdown).strip() or payload.markdown,
        )
