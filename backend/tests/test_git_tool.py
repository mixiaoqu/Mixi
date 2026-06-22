from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import Mock, patch

from pydantic import ValidationError

from app.services.git_remote import GIT_OUTPUT_ENCODING, GitCommit, _run_git
from app.tools.base import ToolContext, ToolPermissionError
from app.tools.git_repository import GitListCommitsInput, GitListCommitsTool


class GitListCommitsInputTests(TestCase):
    def test_rejects_invalid_time_range(self) -> None:
        now = datetime.now(UTC)
        with self.assertRaises(ValidationError):
            GitListCommitsInput(
                data_source_id=uuid.uuid4(),
                start_at=now,
                end_at=now - timedelta(minutes=1),
            )


class GitListCommitsToolTests(IsolatedAsyncioTestCase):
    async def test_rejects_data_source_outside_run_scope(self) -> None:
        repository = Mock()
        tool = GitListCommitsTool(repository)
        source_id = uuid.uuid4()
        payload = GitListCommitsInput(
            data_source_id=source_id,
            start_at=datetime.now(UTC) - timedelta(days=1),
            end_at=datetime.now(UTC),
        )
        context = ToolContext(user_id=uuid.uuid4(), run_id=uuid.uuid4(), allowed_data_source_ids=frozenset())

        with self.assertRaises(ToolPermissionError):
            await tool.execute(payload, context)
        repository.get.assert_not_called()

    async def test_returns_commits_from_authorized_source(self) -> None:
        user_id = uuid.uuid4()
        source_id = uuid.uuid4()
        source = SimpleNamespace(
            id=source_id,
            user_id=user_id,
            name="agent-platform",
            repository_url="https://example.com/owner/agent-platform.git",
            auth_type="public",
            encrypted_credential=None,
            default_branch="main",
            status="connected",
        )
        repository = Mock()
        repository.get.return_value = source
        tool = GitListCommitsTool(repository)
        now = datetime.now(UTC)
        payload = GitListCommitsInput(
            data_source_id=source_id,
            start_at=now - timedelta(days=1),
            end_at=now,
        )
        context = ToolContext(
            user_id=user_id,
            run_id=uuid.uuid4(),
            allowed_data_source_ids=frozenset({source_id}),
        )
        commit = GitCommit(
            sha="a" * 40,
            author_name="Michael",
            author_email="michael@example.com",
            authored_at=now,
            subject="Add Git tool",
        )

        with patch("app.tools.git_repository.list_remote_commits", return_value=[commit]):
            result = await tool.execute(payload, context)

        self.assertEqual(result.repository_name, "agent-platform")
        self.assertEqual(result.branch, "main")
        self.assertEqual(result.commits[0].subject, "Add Git tool")


class GitRemoteProcessTests(TestCase):
    def test_run_git_reads_output_as_utf8_and_handles_empty_stdout(self) -> None:
        completed_process = SimpleNamespace(returncode=0, stdout=None)

        with patch("app.services.git_remote.subprocess.run", return_value=completed_process) as run_mock:
            result = _run_git(["status"], env={}, timeout=5)

        self.assertEqual(result, "")
        self.assertEqual(run_mock.call_args.kwargs["encoding"], GIT_OUTPUT_ENCODING)
        self.assertEqual(run_mock.call_args.kwargs["errors"], "replace")
