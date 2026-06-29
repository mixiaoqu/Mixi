from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Protocol

from app.api.auth import CurrentUser
from app.api.deps import RepositoryDep


RunEventSink = Callable[[str, dict[str, object]], Awaitable[None]]


@dataclass(frozen=True, slots=True)
class SubgraphContext:
    current_user: CurrentUser
    repositories: RepositoryDep


class Subgraph(Protocol):
    id: str
