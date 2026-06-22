from __future__ import annotations

from collections.abc import AsyncIterator, Sequence

from openai import AsyncOpenAI

from app.core.config import settings
from app.db.models import User
from app.schemas.mixi import MixiChatHistoryItem

WORKLOG_KEYWORDS = ("工作日志", "工作日记", "日报", "周报")
WORKLOG_SLOT_KEYWORDS = (
    "今天",
    "今日",
    "昨天",
    "本周",
    "这周",
    "本月",
    "这个月",
    "仓库",
    "分支",
    "补充",
    "另外",
    "还有",
)
WORKLOG_FOLLOW_UP_HINTS = (
    "git 数据源",
    "日志时间范围",
    "今天、昨天还是本周",
    "生成工作日志",
)


def contains_worklog_keyword(text: str) -> bool:
    normalized = text.strip().lower()
    return any(keyword in normalized for keyword in WORKLOG_KEYWORDS)


def is_worklog_request(prompt: str, history: Sequence[MixiChatHistoryItem] | None = None) -> bool:
    if contains_worklog_keyword(prompt):
        return True

    if not history:
        return False

    recent_items = list(history)[-6:]
    has_recent_worklog_context = any(contains_worklog_keyword(item.content) for item in recent_items)
    if not has_recent_worklog_context:
        has_recent_worklog_context = any(
            item.role == "assistant" and any(hint in item.content.lower() for hint in WORKLOG_FOLLOW_UP_HINTS)
            for item in recent_items
        )
    if not has_recent_worklog_context:
        return False

    normalized_prompt = prompt.strip().lower()
    return any(keyword in normalized_prompt for keyword in WORKLOG_SLOT_KEYWORDS) or len(normalized_prompt) <= 24


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
