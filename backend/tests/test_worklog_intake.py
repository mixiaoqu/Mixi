from __future__ import annotations

import unittest
import uuid
from datetime import datetime
from types import SimpleNamespace

from app.schemas.mixi import MixiChatHistoryItem
from app.services.worklog_intake import WorklogIntakeExtractor


class WorklogIntakeExtractorTests(unittest.IsolatedAsyncioTestCase):
    async def test_rule_extractor_auto_selects_single_source_and_today(self) -> None:
        source = SimpleNamespace(
            id=uuid.uuid4(),
            name="agent-platform",
            default_branch="main",
            repository_url="https://example.com/team/agent-platform.git",
        )
        extractor = WorklogIntakeExtractor()

        result = await extractor.extract(
            prompt="帮我生成今天的工作日志",
            history=[],
            data_sources=[source],
            now=datetime.fromisoformat("2026-06-22T10:00:00+08:00"),
        )

        self.assertEqual(result.data_source_id, str(source.id))
        self.assertTrue(result.auto_run)
        self.assertEqual(result.branch, "main")
        self.assertEqual(result.start_at.date().isoformat(), "2026-06-22")

    async def test_rule_extractor_requests_missing_source_when_multiple(self) -> None:
        sources = [
            SimpleNamespace(
                id=uuid.uuid4(),
                name="agent-platform",
                default_branch="main",
                repository_url="https://example.com/team/agent-platform.git",
            ),
            SimpleNamespace(
                id=uuid.uuid4(),
                name="infra-console",
                default_branch="master",
                repository_url="https://example.com/team/infra-console.git",
            ),
        ]
        extractor = WorklogIntakeExtractor()

        result = await extractor.extract(
            prompt="帮我生成今天的工作日志",
            history=[],
            data_sources=sources,
            now=datetime.fromisoformat("2026-06-22T10:00:00+08:00"),
        )

        self.assertFalse(result.auto_run)
        self.assertIn("data_source", result.missing_fields)

    async def test_follow_up_uses_latest_time_range_instead_of_older_today(self) -> None:
        source = SimpleNamespace(
            id=uuid.uuid4(),
            name="ai-synapseflow",
            default_branch="v2.0.0",
            repository_url="https://example.com/team/ai-synapseflow.git",
        )
        extractor = WorklogIntakeExtractor()

        result = await extractor.extract(
            prompt="本周的",
            history=[
                MixiChatHistoryItem(role="user", content="帮我生成今天的工作日志"),
                MixiChatHistoryItem(role="assistant", content="请告诉我要生成今天、昨天还是本周的日志"),
            ],
            data_sources=[source],
            now=datetime.fromisoformat("2026-06-22T10:00:00+08:00"),
        )

        self.assertTrue(result.auto_run)
        self.assertEqual(result.start_at.date().isoformat(), "2026-06-22")

    async def test_rule_extractor_uses_history_to_resolve_follow_up(self) -> None:
        source = SimpleNamespace(
            id=uuid.uuid4(),
            name="agent-platform",
            default_branch="main",
            repository_url="https://example.com/team/agent-platform.git",
        )
        extractor = WorklogIntakeExtractor()

        result = await extractor.extract(
            prompt="另外还有下午的评审会",
            history=[MixiChatHistoryItem(role="user", content="帮我生成今天 agent-platform 的工作日志")],
            data_sources=[source],
            now=datetime.fromisoformat("2026-06-22T10:00:00+08:00"),
        )

        self.assertTrue(result.auto_run)
        self.assertIn("下午的评审会", result.non_code_notes[0])
