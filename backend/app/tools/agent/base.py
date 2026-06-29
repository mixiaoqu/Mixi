from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar, Generic, TypeVar

from pydantic import BaseModel


InputT = TypeVar("InputT", bound=BaseModel)
OutputT = TypeVar("OutputT", bound=BaseModel)


class ToolError(Exception):
    pass


class ToolPermissionError(ToolError):
    pass


class ToolExecutionError(ToolError):
    pass


@dataclass(frozen=True, slots=True)
class ToolContext:
    user_id: uuid.UUID
    run_id: uuid.UUID
    allowed_data_source_ids: frozenset[uuid.UUID]


class AgentTool(ABC, Generic[InputT, OutputT]):
    key: ClassVar[str]
    name: ClassVar[str]
    description: ClassVar[str]
    input_schema: ClassVar[type[BaseModel]]

    @abstractmethod
    async def execute(self, payload: InputT, context: ToolContext) -> OutputT:
        raise NotImplementedError
