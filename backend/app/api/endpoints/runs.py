from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.api.auth import CurrentUser
from app.api.deps import RepositoryDep
from app.api.permissions import require_workspace_access
from app.schemas.common import Page
from app.schemas.run import RunDetailRead, RunSummaryRead


router = APIRouter(prefix="/runs", tags=["runs"])


@router.get("", response_model=Page[RunSummaryRead])
def list_runs(
    current_user: CurrentUser,
    repositories: RepositoryDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    filters = {"initiated_by_user_id": current_user.id}
    items = repositories.workflow_runs.list(limit=limit, offset=offset, **filters)
    total = repositories.workflow_runs.count(**filters)
    return Page(items=items, total=total, limit=limit, offset=offset)


@router.get("/{run_id}", response_model=RunDetailRead)
def get_run(run_id: uuid.UUID, current_user: CurrentUser, repositories: RepositoryDep):
    run = repositories.workflow_runs.get(run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    require_workspace_access(run.workspace_id, current_user, repositories)
    return RunDetailRead.model_validate(
        {
            **RunSummaryRead.model_validate(run).model_dump(),
            "input_payload": run.input_payload,
            "output_payload": run.output_payload,
            "steps": repositories.workflow_run_steps.list_for_run(run.id),
        }
    )
