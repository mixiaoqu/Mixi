from __future__ import annotations

import json
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Literal

from openai import AsyncOpenAI

from app.core.config import settings
from app.db.models import User
from app.schemas.mixi import MixiConversationState

WORKLOG_KEYWORDS = ("工作日志", "工作日记", "日报", "周报")
WORKLOG_ACTION_KEYWORDS = ("总结", "整理", "汇总", "生成", "写一份", "回顾")
WORKLOG_OBJECT_KEYWORDS = ("工作", "进展", "提交", "代码变更", "开发内容", "项目进度")
NON_WORKLOG_LOG_KEYWORDS = ("错误日志", "系统日志", "访问日志", "运行日志", "审计日志", "api 日志")
GENERAL_TASK_KEYWORDS = ("知识库", "设置", "错误分析", "搜索", "创建智能体")
CANCEL_KEYWORDS = ("取消", "算了", "不用了", "停止")
AFFIRMATIVE_KEYWORDS = ("是", "对", "确认", "没错", "可以")
NEGATIVE_KEYWORDS = ("不是", "不对", "不用", "取消", "算了")


@dataclass(frozen=True, slots=True)
class MixiRouteDecision:
    intent: Literal["worklog", "general_chat"]
    action: Literal["route", "confirm", "cancel"]
    confidence: Literal["high", "medium", "low"]
    capability: str | None = None


def contains_explicit_worklog_intent(text: str) -> bool:
    normalized = text.strip().lower()
    if any(keyword in normalized for keyword in NON_WORKLOG_LOG_KEYWORDS):
        return False
    if any(keyword in normalized for keyword in WORKLOG_KEYWORDS):
        return True
    return (
        any(keyword in normalized for keyword in WORKLOG_ACTION_KEYWORDS)
        and any(keyword in normalized for keyword in WORKLOG_OBJECT_KEYWORDS)
    )


class MixiRouter:
    def __init__(self, client: AsyncOpenAI | None = None):
        self.client = client

    async def route(self, *, prompt: str, state: MixiConversationState) -> MixiRouteDecision:
        normalized = prompt.strip().lower()

        if any(keyword in normalized for keyword in CANCEL_KEYWORDS):
            return MixiRouteDecision(intent="general_chat", action="cancel", confidence="high")

        if state.awaiting_confirmation:
            if any(keyword == normalized or keyword in normalized for keyword in NEGATIVE_KEYWORDS):
                return MixiRouteDecision(intent="general_chat", action="cancel", confidence="high")
            if any(keyword == normalized or keyword in normalized for keyword in AFFIRMATIVE_KEYWORDS):
                return MixiRouteDecision(
                    intent="worklog",
                    action="route",
                    confidence="high",
                    capability="worklog.generate",
                )

        if contains_explicit_worklog_intent(normalized):
            return MixiRouteDecision(
                intent="worklog",
                action="route",
                confidence="high",
                capability="worklog.generate",
            )

        if any(keyword in normalized for keyword in NON_WORKLOG_LOG_KEYWORDS + GENERAL_TASK_KEYWORDS):
            return MixiRouteDecision(intent="general_chat", action="route", confidence="high")

        if state.active_intent == "worklog" and state.missing_fields:
            if self.client is None:
                return MixiRouteDecision(
                    intent="worklog",
                    action="route",
                    confidence="high",
                    capability="worklog.generate",
                )
            return await self._route_with_llm(prompt, state)

        if self.client is None:
            return MixiRouteDecision(intent="general_chat", action="route", confidence="low")

        return await self._route_with_llm(prompt, state)

    async def _route_with_llm(self, prompt: str, state: MixiConversationState) -> MixiRouteDecision:
        try:
            completion = await self.client.chat.completions.create(
                model=settings.openai_model,
                temperature=0,
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Classify the user's intent. Return JSON only with keys intent and confidence. "
                            "intent must be worklog or general_chat. confidence must be high, medium, or low. "
                            "Worklog means summarizing the user's work, project progress, or Git activity into a report. "
                            "If an active worklog is waiting for fields, a plausible repository name or date answer is worklog. "
                            "A clearly new request is general_chat even when a worklog was active. "
                            "Operational logs, error logs, and generic analysis are general_chat."
                        ),
                    },
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "prompt": prompt,
                                "active_intent": state.active_intent,
                                "missing_fields": state.missing_fields,
                            },
                            ensure_ascii=False,
                        ),
                    },
                ],
            )
            payload = json.loads(completion.choices[0].message.content or "{}")
            intent = payload.get("intent")
            confidence = payload.get("confidence")
            if intent == "worklog" and confidence == "high":
                return MixiRouteDecision(
                    intent="worklog",
                    action="route",
                    confidence="high",
                    capability="worklog.generate",
                )
            if intent == "worklog" and confidence == "medium" and state.active_intent == "worklog":
                return MixiRouteDecision(
                    intent="worklog",
                    action="route",
                    confidence="medium",
                    capability="worklog.generate",
                )
            if intent == "worklog" and confidence == "medium":
                return MixiRouteDecision(
                    intent="worklog",
                    action="confirm",
                    confidence="medium",
                    capability="worklog.generate",
                )
        except Exception:
            pass
        return MixiRouteDecision(intent="general_chat", action="route", confidence="low")


class MixiChatService:
    def __init__(self, client: AsyncOpenAI):
        self.client = client

    async def stream_reply(self, *, prompt: str, user: User) -> AsyncIterator[str]:
        stream = await self.client.chat.completions.create(
            model=settings.openai_model,
            stream=True,
            temperature=0.5,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are Mixi, the user's calm, modern AI workspace assistant. "
                        "Reply in Chinese by default. Be concise, practical, and friendly. "
                        "When the user's request sounds like a work-log, knowledge-base, or workflow task, "
                        "briefly acknowledge it and explain the next best action inside the platform. "
                        "Do not invent data source results or tool outputs."
                    ),
                },
                {
                    "role": "user",
                    "content": f"当前用户显示名称：{user.display_name}\n用户请求：{prompt}",
                },
            ],
        )

        async for chunk in stream:
            delta = chunk.choices[0].delta.content or ""
            if delta:
                yield delta
