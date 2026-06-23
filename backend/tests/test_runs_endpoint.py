from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import HTTPException

from app.api.endpoints.runs import get_run, list_runs
from app.db.models import RunStatus


def make_run(*, user_id: uuid.UUID):
    now = datetime(2026, 6, 23, 10, 0, tzinfo=UTC)
    return SimpleNamespace(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        agent_id=uuid.uuid4(),
        initiated_by_user_id=user_id,
        template_key="agent.worklog.generate",
        trigger_source="manual",
        status=RunStatus.succeeded,
        input_payload={"branch": "main"},
        output_payload={"markdown": "# 工作日志"},
        error_message=None,
        started_at=now,
        finished_at=now,
        created_at=now,
    )


def test_list_runs_returns_only_current_users_runs() -> None:
    user = SimpleNamespace(id=uuid.uuid4())
    run = make_run(user_id=user.id)
    workflow_runs = Mock()
    workflow_runs.list.return_value = [run]
    workflow_runs.count.return_value = 1
    repositories = SimpleNamespace(workflow_runs=workflow_runs)

    page = list_runs(user, repositories, limit=20, offset=0)

    assert page.total == 1
    assert page.items[0].id == run.id
    workflow_runs.list.assert_called_once_with(limit=20, offset=0, initiated_by_user_id=user.id)
    workflow_runs.count.assert_called_once_with(initiated_by_user_id=user.id)


def test_get_run_returns_steps_and_output_for_workspace_member() -> None:
    user = SimpleNamespace(id=uuid.uuid4())
    run = make_run(user_id=user.id)
    step = SimpleNamespace(
        id=uuid.uuid4(),
        sequence_no=1,
        step_key="compose_worklog",
        step_name="生成日志草稿",
        status=RunStatus.succeeded,
        output_payload={},
        error_message=None,
        started_at=run.started_at,
        finished_at=run.finished_at,
    )
    repositories = SimpleNamespace(
        workflow_runs=SimpleNamespace(get=lambda run_id: run),
        workflow_run_steps=SimpleNamespace(list_for_run=lambda run_id: [step]),
        workspaces=SimpleNamespace(get_for_user=lambda workspace_id, user_id: object()),
    )

    detail = get_run(run.id, user, repositories)

    assert detail.output_payload["markdown"] == "# 工作日志"
    assert detail.steps[0].step_key == "compose_worklog"


def test_get_run_hides_runs_outside_accessible_workspaces() -> None:
    user = SimpleNamespace(id=uuid.uuid4())
    run = make_run(user_id=uuid.uuid4())
    repositories = SimpleNamespace(
        workflow_runs=SimpleNamespace(get=lambda run_id: run),
        workspaces=SimpleNamespace(get_for_user=lambda workspace_id, user_id: None),
    )

    with pytest.raises(HTTPException) as exc_info:
        get_run(run.id, user, repositories)

    assert exc_info.value.status_code == 404
