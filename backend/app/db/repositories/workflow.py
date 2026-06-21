from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select

from app.db.models import RunStatus, WorkflowRun, WorkflowRunStep
from app.db.repositories.base import BaseRepository


class WorkflowRunRepository(BaseRepository[WorkflowRun]):
    model = WorkflowRun

    def create_run(
        self,
        *,
        workspace_id: uuid.UUID,
        template_key: str,
        agent_id: uuid.UUID | None = None,
        initiated_by_user_id: uuid.UUID | None = None,
        trigger_source: str = "manual",
        input_payload: dict | None = None,
    ) -> WorkflowRun:
        return self.create(
            workspace_id=workspace_id,
            template_key=template_key,
            agent_id=agent_id,
            initiated_by_user_id=initiated_by_user_id,
            trigger_source=trigger_source,
            input_payload=input_payload or {},
        )

    def list_by_workspace(self, workspace_id: uuid.UUID, limit: int = 100) -> list[WorkflowRun]:
        stmt = (
            select(WorkflowRun)
            .where(WorkflowRun.workspace_id == workspace_id)
            .order_by(WorkflowRun.created_at.desc())
            .limit(limit)
        )
        return list(self.session.execute(stmt).scalars().all())

    def mark_running(self, run: WorkflowRun, at: datetime | None = None) -> WorkflowRun:
        return self.update(run, status=RunStatus.running, started_at=at or datetime.utcnow(), error_message=None)

    def mark_succeeded(self, run: WorkflowRun, *, output_payload: dict | None = None, at: datetime | None = None) -> WorkflowRun:
        return self.update(
            run,
            status=RunStatus.succeeded,
            output_payload=output_payload or run.output_payload,
            finished_at=at or datetime.utcnow(),
            error_message=None,
        )

    def mark_failed(self, run: WorkflowRun, *, error_message: str, at: datetime | None = None) -> WorkflowRun:
        return self.update(
            run,
            status=RunStatus.failed,
            error_message=error_message,
            finished_at=at or datetime.utcnow(),
        )


class WorkflowRunStepRepository(BaseRepository[WorkflowRunStep]):
    model = WorkflowRunStep

    def create_step(
        self,
        *,
        workflow_run_id: uuid.UUID,
        sequence_no: int,
        step_key: str,
        step_name: str,
        status: RunStatus = RunStatus.queued,
        input_payload: dict | None = None,
    ) -> WorkflowRunStep:
        return self.create(
            workflow_run_id=workflow_run_id,
            sequence_no=sequence_no,
            step_key=step_key,
            step_name=step_name,
            status=status,
            input_payload=input_payload or {},
        )

    def list_for_run(self, workflow_run_id: uuid.UUID) -> list[WorkflowRunStep]:
        stmt = (
            select(WorkflowRunStep)
            .where(WorkflowRunStep.workflow_run_id == workflow_run_id)
            .order_by(WorkflowRunStep.sequence_no.asc())
        )
        return list(self.session.execute(stmt).scalars().all())

    def mark_running(self, step: WorkflowRunStep, at: datetime | None = None) -> WorkflowRunStep:
        return self.update(step, status=RunStatus.running, started_at=at or datetime.utcnow(), error_message=None)

    def mark_succeeded(
        self,
        step: WorkflowRunStep,
        *,
        output_payload: dict | None = None,
        at: datetime | None = None,
    ) -> WorkflowRunStep:
        return self.update(
            step,
            status=RunStatus.succeeded,
            output_payload=output_payload or step.output_payload,
            finished_at=at or datetime.utcnow(),
            error_message=None,
        )

    def mark_failed(self, step: WorkflowRunStep, *, error_message: str, at: datetime | None = None) -> WorkflowRunStep:
        return self.update(
            step,
            status=RunStatus.failed,
            error_message=error_message,
            finished_at=at or datetime.utcnow(),
        )
