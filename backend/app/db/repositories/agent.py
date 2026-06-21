from __future__ import annotations

import uuid

from sqlalchemy import select

from app.db.models import Agent
from app.db.repositories.base import BaseRepository


class AgentRepository(BaseRepository[Agent]):
    model = Agent

    def get_by_slug(self, workspace_id: uuid.UUID, slug: str) -> Agent | None:
        return self.get_by(workspace_id=workspace_id, slug=slug)

    def list_by_workspace(self, workspace_id: uuid.UUID, *, limit: int = 50, offset: int = 0) -> list[Agent]:
        stmt = (
            select(Agent)
            .where(Agent.workspace_id == workspace_id)
            .order_by(Agent.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.execute(stmt).scalars().all())

    def create_agent(
        self,
        *,
        workspace_id: uuid.UUID,
        slug: str,
        name: str,
        description: str | None = None,
        system_prompt: str | None = None,
        llm_model: str = "gpt-4.1-mini",
        config: dict | None = None,
    ) -> Agent:
        return self.create(
            workspace_id=workspace_id,
            slug=slug,
            name=name,
            description=description,
            system_prompt=system_prompt,
            llm_model=llm_model,
            config=config or {},
        )
