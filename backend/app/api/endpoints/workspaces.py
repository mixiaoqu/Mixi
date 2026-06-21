from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response, status

from app.api.auth import CurrentUser
from app.api.deps import RepositoryDep
from app.api.permissions import require_workspace_access, require_workspace_editor
from app.schemas.common import Page
from app.schemas.workspace import WorkspaceCreate, WorkspaceRead, WorkspaceUpdate


router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.post("", response_model=WorkspaceRead, status_code=status.HTTP_201_CREATED)
def create_workspace(payload: WorkspaceCreate, current_user: CurrentUser, repositories: RepositoryDep):
    if repositories.workspaces.get_by_slug(payload.slug) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Workspace slug already exists")
    return repositories.workspaces.create_workspace(owner_user_id=current_user.id, **payload.model_dump())


@router.get("", response_model=Page[WorkspaceRead])
def list_workspaces(
    repositories: RepositoryDep,
    current_user: CurrentUser,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    items = repositories.workspaces.list_for_user(current_user.id, limit=limit, offset=offset)
    total = repositories.workspaces.count_for_user(current_user.id)
    return Page(items=items, total=total, limit=limit, offset=offset)


@router.get("/{workspace_id}", response_model=WorkspaceRead)
def get_workspace(workspace_id: uuid.UUID, current_user: CurrentUser, repositories: RepositoryDep):
    return require_workspace_access(workspace_id, current_user, repositories)


@router.patch("/{workspace_id}", response_model=WorkspaceRead)
def update_workspace(
    workspace_id: uuid.UUID,
    payload: WorkspaceUpdate,
    current_user: CurrentUser,
    repositories: RepositoryDep,
):
    workspace = require_workspace_editor(workspace_id, current_user, repositories)
    return repositories.workspaces.update(workspace, **payload.model_dump(exclude_unset=True))


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workspace(
    workspace_id: uuid.UUID,
    current_user: CurrentUser,
    repositories: RepositoryDep,
) -> Response:
    workspace = require_workspace_access(workspace_id, current_user, repositories)
    if workspace.owner_user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the workspace owner can delete it")
    repositories.workspaces.delete(workspace)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
