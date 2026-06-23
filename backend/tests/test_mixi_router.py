from __future__ import annotations

import asyncio
from types import SimpleNamespace

from app.schemas.mixi import MixiConversationState
from app.services.mixi import MixiRouter


def test_router_recognizes_natural_work_summary_request() -> None:
    decision = asyncio.run(MixiRouter().route(
        prompt="帮我整理这周的项目进展",
        state=MixiConversationState(),
    ))

    assert decision.intent == "worklog"
    assert decision.capability == "worklog.generate"


def test_router_does_not_confuse_error_logs_with_worklog() -> None:
    decision = asyncio.run(MixiRouter().route(
        prompt="分析最近的 API 错误日志",
        state=MixiConversationState(),
    ))

    assert decision.intent == "general_chat"


def test_router_uses_explicit_state_for_repository_follow_up() -> None:
    decision = asyncio.run(MixiRouter().route(
        prompt="agent-platform",
        state=MixiConversationState(active_intent="worklog", missing_fields=["data_source"]),
    ))

    assert decision.intent == "worklog"


def test_router_asks_for_confirmation_on_medium_confidence() -> None:
    async def create(**kwargs):
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content='{"intent":"worklog","confidence":"medium"}'))]
        )

    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    decision = asyncio.run(MixiRouter(client).route(
        prompt="把最近做的事情整理一下",
        state=MixiConversationState(),
    ))

    assert decision.action == "confirm"


def test_router_clears_active_task_on_cancel() -> None:
    decision = asyncio.run(MixiRouter().route(
        prompt="算了",
        state=MixiConversationState(active_intent="worklog", missing_fields=["time_range"]),
    ))

    assert decision.action == "cancel"


def test_router_allows_switching_away_from_active_worklog() -> None:
    async def create(**kwargs):
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content='{"intent":"general_chat","confidence":"high"}'))]
        )

    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    decision = asyncio.run(MixiRouter(client).route(
        prompt="帮我查看天气",
        state=MixiConversationState(active_intent="worklog", missing_fields=["data_source"]),
    ))

    assert decision.intent == "general_chat"
