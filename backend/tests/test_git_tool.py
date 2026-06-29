from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase, TestCase
from unittest.mock import Mock, patch

from pydantic import ValidationError

from app.services.git_remote import GIT_OUTPUT_ENCODING, GitCommit, _run_git, list_remote_commits
from app.tools.agent.base import ToolContext, ToolPermissionError
from app.tools.agent.git_inspect import GitListCommitsInput, GitListCommitsTool


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

        with patch("app.tools.agent.git_inspect.list_remote_commits", return_value=[commit]):
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

    def test_list_remote_commits_returns_empty_list_when_log_has_no_records(self) -> None:
        start_at = datetime(2026, 6, 21, 16, 0, tzinfo=UTC)
        end_at = datetime(2026, 6, 22, 16, 0, tzinfo=UTC)
        completed_process = SimpleNamespace(returncode=0, stdout="")

        with patch("app.services.git_remote._validate_public_host"):
            with patch("app.services.git_remote.subprocess.run", return_value=completed_process) as run_mock:
                commits = list_remote_commits(
                    repository_url="https://example.com/owner/repository.git",
                    auth_type="public",
                    credential=None,
                    branch="main",
                    start_at=start_at,
                    end_at=end_at,
                    limit=50,
                )

        clone_args = run_mock.call_args_list[0].args[0]
        log_args = run_mock.call_args_list[1].args[0]

        self.assertEqual(commits, [])
        self.assertFalse(any(arg.startswith("--shallow-since=") for arg in clone_args))
        self.assertIn(f"--since={start_at.isoformat()}", log_args)
        self.assertIn(f"--until={end_at.isoformat()}", log_args)

    def test_list_remote_commits_includes_changed_files_and_patch(self) -> None:
        start_at = datetime(2026, 6, 21, 16, 0, tzinfo=UTC)
        end_at = datetime(2026, 6, 22, 16, 0, tzinfo=UTC)
        authored_at = "2026-06-22T10:00:00+00:00"
        log_output = f"abc123\x1fMichael\x1fmichael@example.com\x1f{authored_at}\x1fAdd parser\x1e"
        changed_files_output = "backend/app/parser.py\nbackend/tests/test_parser.py\n"
        patch_output = "diff --git a/backend/app/parser.py b/backend/app/parser.py\n+def parse():\n+    return True\n"

        with patch("app.services.git_remote._validate_public_host"):
            with patch(
                "app.services.git_remote.subprocess.run",
                side_effect=[
                    SimpleNamespace(returncode=0, stdout=""),
                    SimpleNamespace(returncode=0, stdout=log_output),
                    SimpleNamespace(returncode=0, stdout=changed_files_output),
                    SimpleNamespace(returncode=0, stdout=patch_output),
                ],
            ) as run_mock:
                commits = list_remote_commits(
                    repository_url="https://example.com/owner/repository.git",
                    auth_type="public",
                    credential=None,
                    branch="main",
                    start_at=start_at,
                    end_at=end_at,
                    limit=50,
                )

        self.assertEqual(commits[0].changed_files, ["backend/app/parser.py", "backend/tests/test_parser.py"])
        self.assertIn("def parse", commits[0].patch)
        self.assertIn("--name-only", run_mock.call_args_list[2].args[0])
        self.assertIn("--unified=3", run_mock.call_args_list[3].args[0])
