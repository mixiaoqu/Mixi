from __future__ import annotations

import uuid

from fastapi import HTTPException, status

from app.db.models import MembershipRole, User, Workspace
from app.db.repositories import Repositories


def require_workspace_access(
    workspace_id: uuid.UUID,
    user: User,
    repositories: Repositories,
) -> Workspace:
    workspace = repositories.workspaces.get_for_user(workspace_id, user.id)
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    return workspace


def require_workspace_editor(
    workspace_id: uuid.UUID,
    user: User,
    repositories: Repositories,
) -> Workspace:
    workspace = require_workspace_access(workspace_id, user, repositories)
    if workspace.owner_user_id == user.id:
        return workspace
    membership = repositories.workspace_memberships.get_by(workspace_id=workspace_id, user_id=user.id)
    if membership is None or membership.role not in {
        MembershipRole.owner,
        MembershipRole.admin,
        MembershipRole.editor,
    }:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Workspace editor access required")
    return workspace
