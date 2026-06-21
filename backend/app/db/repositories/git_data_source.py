from __future__ import annotations

import uuid

from app.db.models import GitDataSource
from app.db.repositories.base import BaseRepository


class GitDataSourceRepository(BaseRepository[GitDataSource]):
    model = GitDataSource

    def list_by_user(self, user_id: uuid.UUID) -> list[GitDataSource]:
        return self.list(user_id=user_id, limit=100)
