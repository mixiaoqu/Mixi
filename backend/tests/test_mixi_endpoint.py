from __future__ import annotations

import asyncio
import types
import unittest
import uuid
from unittest.mock import patch

from fastapi import HTTPException

from app.api.endpoints.mixi import sse_event, stream_mixi_chat
from app.schemas.mixi import MixiChatRequest


class SseEventTests(unittest.TestCase):
    def test_sse_event_keeps_unicode(self) -> None:
        event = sse_event("chunk", {"delta": "你好"})
        self.assertIn("event: chunk", event)
        self.assertIn('"你好"', event)


class MixiEndpointTests(unittest.TestCase):
    def test_worklog_request_returns_widget_with_draft(self) -> None:
        payload = MixiChatRequest(prompt="帮我生成今天的工作日志")
        user = types.SimpleNamespace(id=uuid.uuid4(), display_name="Michael")
        repositories = types.SimpleNamespace(
            git_data_sources=types.SimpleNamespace(list_by_user=lambda user_id: []),
        )

        async def run_test():
            with patch("app.api.endpoints.mixi.get_openai_client", side_effect=RuntimeError("OPENAI_API_KEY is not configured")):
                response = await stream_mixi_chat(payload, user, repositories)
                body: list[str] = []
                async for chunk in response.body_iterator:
                    body.append(chunk)
                text = "".join(body)
                self.assertIn("event: widget", text)
                self.assertIn('"type": "worklog_form"', text)
                self.assertIn('"draft"', text)

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
                    self.assertIn("event: chunk", text)
                    self.assertIn("event: completed", text)
                    self.assertIn('"message": "你好"', text)

        asyncio.run(run_test())
