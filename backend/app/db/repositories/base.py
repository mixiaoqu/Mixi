from __future__ import annotations

import uuid
from typing import Any, Generic, TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.db.models import BaseModel

ModelT = TypeVar("ModelT", bound=BaseModel)


class BaseRepository(Generic[ModelT]):
    model: type[ModelT]

    def __init__(self, session: Session):
        self.session = session

    def base_query(self) -> Select[tuple[ModelT]]:
        return select(self.model)

    def get(self, record_id: uuid.UUID) -> ModelT | None:
        return self.session.get(self.model, record_id)

    def get_by(self, **filters: Any) -> ModelT | None:
        stmt = self.base_query().filter_by(**filters)
        return self.session.execute(stmt).scalar_one_or_none()

    def list(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        **filters: Any,
    ) -> list[ModelT]:
        stmt = self.base_query().filter_by(**filters).order_by(self.model.created_at.desc()).limit(limit).offset(offset)
        return list(self.session.execute(stmt).scalars().all())

    def count(self, **filters: Any) -> int:
        stmt = select(func.count()).select_from(self.model).filter_by(**filters)
        return int(self.session.execute(stmt).scalar_one())

    def exists(self, **filters: Any) -> bool:
        return self.get_by(**filters) is not None

    def create(self, **values: Any) -> ModelT:
        instance = self.model(**values)
        self.session.add(instance)
        self.session.flush()
        self.session.refresh(instance)
        return instance

    def update(self, instance: ModelT, **changes: Any) -> ModelT:
        for field, value in changes.items():
            setattr(instance, field, value)
        self.session.add(instance)
        self.session.flush()
        self.session.refresh(instance)
        return instance

    def delete(self, instance: ModelT) -> None:
        self.session.delete(instance)
        self.session.flush()
