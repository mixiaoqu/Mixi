from __future__ import annotations

import uuid

from sqlalchemy import func, or_, select

from app.db.models import MembershipRole, Workspace, WorkspaceMembership
from app.db.repositories.base import BaseRepository


class WorkspaceRepository(BaseRepository[Workspace]):
    model = Workspace

    def get_by_slug(self, slug: str) -> Workspace | None:
        return self.get_by(slug=slug)

    def get_for_user(self, workspace_id: uuid.UUID, user_id: uuid.UUID) -> Workspace | None:
        stmt = (
            select(Workspace)
            .outerjoin(WorkspaceMembership, WorkspaceMembership.workspace_id == Workspace.id)
            .where(
                Workspace.id == workspace_id,
                or_(
                    Workspace.owner_user_id == user_id,
                    WorkspaceMembership.user_id == user_id,
                ),
            )
        )
        return self.session.execute(stmt).scalars().unique().one_or_none()

    def create_workspace(
        self,
        *,
        owner_user_id: uuid.UUID,
        slug: str,
        name: str,
        description: str | None = None,
    ) -> Workspace:
        return self.create(
            owner_user_id=owner_user_id,
            slug=slug,
            name=name,
            description=description,
        )

    def list_for_user(self, user_id: uuid.UUID, *, limit: int = 50, offset: int = 0) -> list[Workspace]:
        stmt = (
            select(Workspace)
            .outerjoin(WorkspaceMembership, WorkspaceMembership.workspace_id == Workspace.id)
            .where(
                or_(
                    Workspace.owner_user_id == user_id,
                    WorkspaceMembership.user_id == user_id,
                )
            )
            .order_by(Workspace.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.execute(stmt).scalars().unique().all())

    def count_for_user(self, user_id: uuid.UUID) -> int:
        stmt = (
            select(func.count(func.distinct(Workspace.id)))
            .outerjoin(WorkspaceMembership, WorkspaceMembership.workspace_id == Workspace.id)
            .where(
                or_(
                    Workspace.owner_user_id == user_id,
                    WorkspaceMembership.user_id == user_id,
                )
            )
        )
        return int(self.session.execute(stmt).scalar_one())


class WorkspaceMembershipRepository(BaseRepository[WorkspaceMembership]):
    model = WorkspaceMembership

    def add_member(
        self,
        *,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        role: MembershipRole = MembershipRole.viewer,
    ) -> WorkspaceMembership:
        existing = self.get_by(workspace_id=workspace_id, user_id=user_id)
        if existing is not None:
            return self.update(existing, role=role)
        return self.create(workspace_id=workspace_id, user_id=user_id, role=role)

    def list_members(self, workspace_id: uuid.UUID) -> list[WorkspaceMembership]:
        return self.list(limit=200, workspace_id=workspace_id)
