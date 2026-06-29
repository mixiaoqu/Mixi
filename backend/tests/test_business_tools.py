from __future__ import annotations

from datetime import datetime
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, Mock, patch

from app.services.worklog_refiner import WorklogRefinementResult
from app.tools.business.dingtalk_send import DingTalkSendInput, DingTalkSendTool
from app.tools.business.time_range_resolve import TimeRangeResolveInput, TimeRangeResolveTool
from app.tools.business.worklog_refine import WorklogRefinePayload, WorklogRefineTool
from app.tools.business.worklog_render import WorklogRenderCommit, WorklogRenderInput, WorklogRenderTool


class TimeRangeResolveToolTests(IsolatedAsyncioTestCase):
    async def test_resolves_named_kind_when_text_does_not_match(self) -> None:
        tool = TimeRangeResolveTool()
        payload = TimeRangeResolveInput(
            texts=["unrelated text"],
            now=datetime.fromisoformat("2026-06-28T14:00:00+08:00"),
            named_kind="last_week",
        )

        result = await tool.execute(payload)

        self.assertTrue(result.matched)
        self.assertIsNotNone(result.start_at)
        self.assertIsNotNone(result.end_at)


class WorklogRenderToolTests(IsolatedAsyncioTestCase):
    async def test_renders_markdown_from_commits_and_notes(self) -> None:
        tool = WorklogRenderTool()
        payload = WorklogRenderInput(
            agent_name="Worklog Agent",
            start_at=datetime.fromisoformat("2026-06-28T09:00:00+08:00"),
            end_at=datetime.fromisoformat("2026-06-28T18:00:00+08:00"),
            commits=[
                WorklogRenderCommit(
                    sha="a" * 40,
                    author_name="Michael",
                    authored_at=datetime.fromisoformat("2026-06-28T10:00:00+08:00"),
                    subject="feat: add worklog tools",
                    changed_files=["backend/app/tools/business/worklog_render.py"],
                )
            ],
            non_code_notes=["aligned naming with the team"],
        )

        result = await tool.execute(payload)

        self.assertEqual(result.report_kind, "daily")
        self.assertIn("feat: add worklog tools", result.markdown)
        self.assertIn("aligned naming with the team", result.markdown)
        self.assertIn("## Notes", result.markdown)


class WorklogRefineToolTests(IsolatedAsyncioTestCase):
    async def test_maps_payload_into_refiner_input(self) -> None:
        tool = WorklogRefineTool(client=object())
        tool.refiner = AsyncMock()
        tool.refiner.refine.return_value = WorklogRefinementResult(
            title="Refined title",
            summary="Refined summary",
            markdown="# Refined",
        )
        payload = WorklogRefinePayload(
            agent_name="Worklog Agent",
            title="Draft title",
            summary="Draft summary",
            markdown="# Draft",
            user_prompt="Generate my worklog",
            repository_name="agent-platform",
            branch="main",
            commit_count=2,
            non_code_notes=["note"],
            commits=[{"subject": "feat: add worklog tools"}],
        )

        result = await tool.execute(payload)

        self.assertEqual(result.title, "Refined title")
        forwarded = tool.refiner.refine.await_args.args[0]
        self.assertEqual(forwarded.repository_name, "agent-platform")
        self.assertEqual(forwarded.commit_count, 2)
        self.assertEqual(forwarded.non_code_notes, ["note"])


class DingTalkSendToolTests(IsolatedAsyncioTestCase):
    async def test_sends_markdown_payload(self) -> None:
        tool = DingTalkSendTool()
        payload = DingTalkSendInput(
            webhook_url="https://example.com/webhook",
            title="Worklog",
            markdown="# Worklog",
        )

        response = Mock()
        response.is_success = True
        response.status_code = 200
        response.headers = {"content-type": "application/json"}
        response.json.return_value = {"errcode": 0, "errmsg": "ok"}

        client = AsyncMock()
        client.post.return_value = response
        client.__aenter__.return_value = client
        client.__aexit__.return_value = None

        with patch("app.tools.business.dingtalk_send.httpx.AsyncClient", return_value=client):
            result = await tool.execute(payload)

        self.assertTrue(result.ok)
        self.assertEqual(result.errcode, 0)
        client.post.assert_awaited_once()
