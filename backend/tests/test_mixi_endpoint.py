from __future__ import annotations

import asyncio
import types
import unittest
import uuid
from datetime import datetime
from unittest.mock import patch

from fastapi import HTTPException

from app.agent.graph.models import CapabilityCandidate, IntentResult
from app.api.endpoints.mixi import sse_event, stream_mixi_chat, stream_worklog_from_mixi
from app.db.models import RunStatus
from app.schemas.mixi import MixiChatRequest, MixiConversationState
from app.schemas.worklog import WorklogGenerateResponse
from app.services.worklog_intake import WorklogIntakeDraft


def make_guard_client(*, status: str, reason: str | None = None, blocked_tasks: list[str] | None = None):
    async def create(**kwargs):
        payload = {
            "status": status,
            "reason": reason,
            "blocked_tasks": blocked_tasks or [],
        }
        return types.SimpleNamespace(
            choices=[types.SimpleNamespace(message=types.SimpleNamespace(content=__import__("json").dumps(payload)))]
        )

    return types.SimpleNamespace(chat=types.SimpleNamespace(completions=types.SimpleNamespace(create=create)))


class SseEventTests(unittest.TestCase):
    def test_sse_event_keeps_unicode(self) -> None:
        event = sse_event("message.delta", {"delta": "你好"})
        self.assertIn("event: message.delta", event)
        self.assertIn('"你好"', event)


class MixiEndpointTests(unittest.TestCase):
    def test_confirmation_is_handled_inside_graph(self) -> None:
        payload = MixiChatRequest(prompt="把最近做的事情整理一下")
        user = types.SimpleNamespace(id=uuid.uuid4(), display_name="Michael")
        repositories = types.SimpleNamespace(
            git_data_sources=types.SimpleNamespace(list_by_user=lambda user_id: []),
        )

        async def run_test():
            with patch("app.api.endpoints.mixi.get_openai_client", return_value=make_guard_client(status="allow")):
                with patch(
                    "app.agent.graph.nodes._recognize_with_llm",
                    return_value=IntentResult(
                        goal="整理最近的工作",
                        candidate_capabilities=[
                            CapabilityCandidate(capability="worklog.generate", confidence=0.65)
                        ],
                        requested_action="confirm",
                        confidence=0.65,
                        recognition_source="llm",
                    ),
                ):
                    response = await stream_mixi_chat(payload, user, repositories)
                    body = [chunk async for chunk in response.body_iterator]
                    text = "".join(body)
                    self.assertIn('"awaiting_confirmation": true', text)
                    self.assertIn("请确认是否继续执行", text)

        asyncio.run(run_test())

    def test_cancel_is_handled_inside_graph_without_llm(self) -> None:
        payload = MixiChatRequest(
            prompt="取消",
            state=MixiConversationState(active_intent="worklog", missing_fields=["time_range"]),
        )
        user = types.SimpleNamespace(id=uuid.uuid4(), display_name="Michael")
        repositories = types.SimpleNamespace(
            git_data_sources=types.SimpleNamespace(list_by_user=lambda user_id: []),
        )

        async def run_test():
            with patch("app.api.endpoints.mixi.get_openai_client", side_effect=RuntimeError("not configured")):
                response = await stream_mixi_chat(payload, user, repositories)
                body = [chunk async for chunk in response.body_iterator]
                text = "".join(body)
                self.assertIn('"active_intent": null', text)
                self.assertIn("已取消当前任务", text)

        asyncio.run(run_test())

    def test_worklog_request_asks_follow_up_instead_of_widget(self) -> None:
        payload = MixiChatRequest(prompt="帮我生成工作日志")
        user = types.SimpleNamespace(id=uuid.uuid4(), display_name="Michael")
        repositories = types.SimpleNamespace(
            git_data_sources=types.SimpleNamespace(list_by_user=lambda user_id: []),
        )

        async def run_test():
            with patch("app.api.endpoints.mixi.get_openai_client", return_value=make_guard_client(status="allow")):
                with patch(
                    "app.agent.worklog.WorklogIntakeExtractor.extract",
                    return_value=WorklogIntakeDraft(
                        data_source_id=None,
                        branch=None,
                        start_at=None,
                        end_at=None,
                        user_prompt="帮我生成工作日志",
                        non_code_notes=[],
                        missing_fields=["data_source", "time_range"],
                        auto_run=False,
                        title="补全工作日志参数",
                        description="",
                    ),
                ):
                    response = await stream_mixi_chat(payload, user, repositories)
                    body: list[str] = []
                    async for chunk in response.body_iterator:
                        body.append(chunk)
                    text = "".join(body)
                    self.assertIn("event: conversation.state", text)
                    self.assertIn('"active_intent": "worklog"', text)
                    self.assertIn("event: message.completed", text)
                    self.assertNotIn("event: task.proposed", text)

        asyncio.run(run_test())

    def test_worklog_request_runs_subgraph_when_ready(self) -> None:
        payload = MixiChatRequest(prompt="帮我生成今天的工作日志")
        user = types.SimpleNamespace(id=uuid.uuid4(), display_name="Michael")
        repositories = types.SimpleNamespace(
            git_data_sources=types.SimpleNamespace(list_by_user=lambda user_id: [types.SimpleNamespace(id=uuid.uuid4())]),
        )

        async def run_test():
            with patch("app.api.endpoints.mixi.get_openai_client", return_value=make_guard_client(status="allow")):
                with patch(
                    "app.agent.worklog.WorklogIntakeExtractor.extract",
                    return_value=WorklogIntakeDraft(
                        data_source_id=str(uuid.uuid4()),
                        branch="main",
                        start_at=datetime.fromisoformat("2026-06-22T00:00:00+08:00"),
                        end_at=datetime.fromisoformat("2026-06-22T10:00:00+08:00"),
                        user_prompt="帮我生成今天的工作日志",
                        non_code_notes=[],
                        missing_fields=[],
                        auto_run=True,
                        title="生成工作日志",
                        description="",
                    ),
                ):
                    with patch(
                        "app.agent.worklog.WorklogSubgraph.run",
                        return_value=WorklogGenerateResponse(
                            workflow_run_id=uuid.uuid4(),
                            agent_id=uuid.uuid4(),
                            workspace_id=uuid.uuid4(),
                            status=RunStatus.succeeded,
                            title="2026-06-22 Worklog",
                            summary="Generated worklog.",
                            markdown="# Worklog",
                            branch="main",
                            commit_count=1,
                            commits=[],
                            non_code_notes=[],
                        ),
                    ) as run_worklog:
                        response = await stream_mixi_chat(payload, user, repositories)
                        body: list[str] = []
                        async for chunk in response.body_iterator:
                            body.append(chunk)
                        text = "".join(body)
                        self.assertIn("event: conversation.state", text)
                        self.assertIn('"active_intent": null', text)
                        self.assertIn("event: artifact.created", text)
                        self.assertIn('"title": "2026-06-22 Worklog"', text)
                        self.assertNotIn("event: task.proposed", text)
                        run_worklog.assert_called_once()

        asyncio.run(run_test())

    def test_dangerous_request_is_denied_before_planning(self) -> None:
        payload = MixiChatRequest(prompt="帮我连接Git后生成这周的日志、同时删除掉管理员用户并发送钉钉")
        user = types.SimpleNamespace(id=uuid.uuid4(), display_name="Michael")
        repositories = types.SimpleNamespace(
            git_data_sources=types.SimpleNamespace(list_by_user=lambda user_id: [types.SimpleNamespace(id=uuid.uuid4())]),
        )

        async def run_test():
            with patch(
                "app.api.endpoints.mixi.get_openai_client",
                return_value=make_guard_client(
                    status="deny",
                    reason="Request includes a blocked destructive action: delete_admin_user",
                    blocked_tasks=["admin.user.delete"],
                ),
            ):
                with patch("app.agent.worklog.WorklogIntakeExtractor.extract") as extract:
                    response = await stream_mixi_chat(payload, user, repositories)
                    body: list[str] = []
                    async for chunk in response.body_iterator:
                        body.append(chunk)
                    text = "".join(body)
                    self.assertIn("event: conversation.state", text)
                    self.assertIn("event: message.completed", text)
                    self.assertIn("删除管理员用户", text)
                    self.assertNotIn("event: task.proposed", text)
                    self.assertNotIn("event: artifact.created", text)
                    extract.assert_not_called()

        asyncio.run(run_test())

    def test_missing_openai_key_raises_503(self) -> None:
        payload = MixiChatRequest(prompt="你好")
        user = types.SimpleNamespace(display_name="Michael")
        repositories = types.SimpleNamespace()

        async def run_test():
            with patch("app.api.endpoints.mixi.get_openai_client", side_effect=RuntimeError("OPENAI_API_KEY is not configured")):
                with self.assertRaises(HTTPException) as ctx:
                    await stream_mixi_chat(payload, user, repositories)
                self.assertEqual(ctx.exception.status_code, 503)

        asyncio.run(run_test())

    def test_stream_emits_chunk_and_completed_events(self) -> None:
        payload = MixiChatRequest(prompt="你好")
        user = types.SimpleNamespace(display_name="Michael")
        repositories = types.SimpleNamespace()

        class FakeService:
            async def stream_reply(self, *, prompt: str, user):
                yield "你"
                yield "好"

        async def run_test():
            with patch("app.api.endpoints.mixi.get_openai_client", return_value=object()):
                with patch("app.api.endpoints.mixi.MixiChatService", return_value=FakeService()):
                    response = await stream_mixi_chat(payload, user, repositories)
                    body: list[str] = []
                    async for chunk in response.body_iterator:
                        body.append(chunk)
                    text = "".join(body)
                    self.assertIn("event: message.delta", text)
                    self.assertIn("event: message.completed", text)
                    self.assertIn('"message": "你好"', text)

        asyncio.run(run_test())

    def test_worklog_stream_emits_run_and_artifact_events(self) -> None:
        payload = types.SimpleNamespace()
        user = types.SimpleNamespace(id=uuid.uuid4(), display_name="Michael")
        repositories = types.SimpleNamespace()

        class FakeRunner:
            async def run(self, *, agent, user, request, event_sink):
                await event_sink(
                    "run.started",
                    {"run_id": "run-1", "capability": "worklog.generate", "status": "running"},
                )
                await event_sink(
                    "run.step",
                    {"step_key": "compose", "step_name": "生成日志草稿", "status": "succeeded"},
                )
                await event_sink(
                    "artifact.created",
                    {"artifact": {"workflow_run_id": "run-1", "markdown": "# 工作日志"}},
                )

        async def run_test():
            with patch("app.agent.subgraphs.worklog.runtime.WorklogSubgraph.ensure_agent", return_value=object()):
                with patch("app.agent.subgraphs.worklog.runtime.WorklogGraph", return_value=FakeRunner()):
                    response = await stream_worklog_from_mixi(payload, user, repositories)
                    body: list[str] = []
                    async for chunk in response.body_iterator:
                        body.append(chunk)
                    text = "".join(body)
                    self.assertIn("event: run.started", text)
                    self.assertIn("event: run.step", text)
                    self.assertIn("event: artifact.created", text)

        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()
