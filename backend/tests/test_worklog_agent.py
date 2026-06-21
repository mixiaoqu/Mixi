from __future__ import annotations

import asyncio
import unittest
import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock

from app.agents.graph import WorklogAgentRunner
from app.tools.base import ToolExecutionError
from app.tools.git_repository import GitListCommitsOutput, GitCommitResult
from app.schemas.worklog import WorklogGenerateRequest


class FakeGitTool:
    def __init__(self, result: GitListCommitsOutput | None = None, error: Exception | None = None):
        self.result = result
        self.error = error

    async def execute(self, payload, context):
        if self.error is not None:
            raise self.error
        return self.result


class WorklogAgentRunnerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.run = SimpleNamespace(id=uuid.uuid4(), output_payload={})
        self.git_step = SimpleNamespace(output_payload={})
        self.compose_step = SimpleNamespace(output_payload={})

        self.workflow_runs = Mock()
        self.workflow_runs.create_run.return_value = self.run
        self.workflow_runs.mark_running.side_effect = lambda run: run
        self.workflow_runs.mark_succeeded.side_effect = lambda run, output_payload=None: run
        self.workflow_runs.mark_failed.side_effect = lambda run, error_message: run

        self.workflow_run_steps = Mock()
        self.workflow_run_steps.create_step.side_effect = [self.git_step, self.compose_step]
        self.workflow_run_steps.mark_running.side_effect = lambda step: step
        self.workflow_run_steps.mark_succeeded.side_effect = lambda step, output_payload=None: step
        self.workflow_run_steps.mark_failed.side_effect = lambda step, error_message: step

        self.repositories = SimpleNamespace(
            workflow_runs=self.workflow_runs,
            workflow_run_steps=self.workflow_run_steps,
            git_data_sources=Mock(),
        )
        self.agent = SimpleNamespace(id=uuid.uuid4(), workspace_id=uuid.uuid4(), name="工作日志 Agent")
        self.user = SimpleNamespace(id=uuid.uuid4())
        self.request = WorklogGenerateRequest(
            data_source_id=uuid.uuid4(),
            start_at=datetime(2026, 6, 21, 9, 0, tzinfo=UTC),
            end_at=datetime(2026, 6, 21, 18, 0, tzinfo=UTC),
            non_code_notes=["补充周报说明", "和产品确认需求边界"],
            user_prompt="整理今天的开发与协作进展",
        )

    def test_run_generates_markdown_draft(self) -> None:
        git_result = GitListCommitsOutput(
            data_source_id=self.request.data_source_id,
            repository_name="agent-platform/main",
            branch="main",
            commits=[
                GitCommitResult(
                    sha="abcdef1234567890",
                    author_name="Michael",
                    author_email="michael@example.com",
                    authored_at=datetime(2026, 6, 21, 10, 30, tzinfo=UTC),
                    subject="feat: add worklog runner",
                )
            ],
        )
        runner = WorklogAgentRunner(self.repositories, git_tool=FakeGitTool(result=git_result))

        response = asyncio.run(runner.run(agent=self.agent, user=self.user, request=self.request))

        self.assertEqual(response.commit_count, 1)
        self.assertEqual(response.branch, "main")
        self.assertIn("feat: add worklog runner", response.markdown)
        self.assertIn("补充周报说明", response.markdown)
        self.assertEqual(response.non_code_notes, self.request.non_code_notes)
        self.workflow_runs.mark_succeeded.assert_called_once()

    def test_run_marks_workflow_failed_when_tool_errors(self) -> None:
        runner = WorklogAgentRunner(
            self.repositories,
            git_tool=FakeGitTool(error=ToolExecutionError("Git 数据源当前不可用")),
        )

        with self.assertRaises(ToolExecutionError):
            asyncio.run(runner.run(agent=self.agent, user=self.user, request=self.request))

        self.workflow_runs.mark_failed.assert_called_once()


if __name__ == "__main__":
    unittest.main()
