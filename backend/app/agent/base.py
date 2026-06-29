from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Protocol

from openai import AsyncOpenAI

from app.api.auth import CurrentUser
from app.api.deps import RepositoryDep
from app.schemas.mixi import MixiChatHistoryItem, MixiConversationState

if TYPE_CHECKING:
    from .graph.models import (
        AgentRequest,
        Artifact,
        CapabilityAvailability,
        CapabilityRuleMatch,
        ClarificationQuestion,
        ConversationPatch,
        IntentResult,
        PlanResult,
        PlanStep,
    )


@dataclass(frozen=True, slots=True)
class CapabilityRuntime:
    current_user: CurrentUser
    repositories: RepositoryDep
    llm_client: AsyncOpenAI | None


@dataclass(frozen=True, slots=True)
class IntakeContext:
    prompt: str
    history: list[MixiChatHistoryItem]
    state: MixiConversationState
    now: datetime
    current_user: CurrentUser
    repositories: RepositoryDep
    llm_client: AsyncOpenAI | None


class Capability(Protocol):
    id: str
    name: str
    description: str
    active_intent: str

    def catalog_entry(self) -> CapabilityAvailability:
        ...

    def match(self, request: AgentRequest) -> CapabilityRuleMatch | None:
        ...

    def check_availability(self, runtime: CapabilityRuntime) -> CapabilityAvailability:
        ...

    async def plan(
        self,
        context: IntakeContext,
        intent: IntentResult,
        *,
        attempt: int,
    ) -> PlanResult:
        ...

    def build_clarification(
        self,
        *,
        reason_code: str,
        missing_requirements: list[str],
        plan: PlanResult | None,
    ) -> tuple[str, list[ClarificationQuestion], ConversationPatch]:
        ...

    async def execute(
        self,
        step: PlanStep,
        payload: dict[str, object],
        runtime: CapabilityRuntime,
    ) -> Artifact:
        ...
