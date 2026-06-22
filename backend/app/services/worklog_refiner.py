from __future__ import annotations

import json
from dataclasses import dataclass, field

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
    commits: list[dict[str, object]] = field(default_factory=list)


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
            "commits": payload.commits,
        }
        completion = await self.client.chat.completions.create(
            model=settings.openai_model,
            temperature=0.2,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "你是工作日志整理助手。"
                        "请基于 Git 提交、changed_files、patch diff、用户补充事项和已有草稿生成一份结构化中文工作日志。"
                        "不要虚构事实，不要新增不存在的任务、风险或计划；缺失信息请写“暂未记录”。"
                        "重点分析 diff 体现出的功能变化、实现方式、解决的问题和产品/工程目的。"
                        "不要逐条罗列 commit，不要把提交信息作为主体，不要输出“参考信息”章节。"
                        "Markdown 必须包含这些二级标题：工作概览、完成功能、技术实现、目标和价值、风险或阻塞、后续可扩展方向。"
                        "只有用户补充了会议、沟通、排障等非代码事项时，才追加“备注”章节；没有补充时不要输出空备注。"
                        "后续可扩展方向必须基于已有 diff 能合理推出，不能凭空想象业务规划。"
                        "summary 要是一句话，概括做了什么功能和达到什么目的，不要只是统计提交数量。"
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
