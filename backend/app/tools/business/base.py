from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar, Generic, TypeVar


InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")


class BusinessTool(ABC, Generic[InputT, OutputT]):
    key: ClassVar[str]
    name: ClassVar[str]
    description: ClassVar[str]
    input_schema: ClassVar[type[Any]]

    @abstractmethod
    async def execute(self, payload: InputT) -> OutputT:
        raise NotImplementedError
