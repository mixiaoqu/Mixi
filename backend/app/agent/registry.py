from __future__ import annotations

from app.agent.base import Capability
from app.agent.graph.models import AgentRequest, CapabilityRuleMatch
from app.agent.worklog import WorklogCapability


class CapabilityRegistry:
    def __init__(self, capabilities: list[Capability]):
        self._capabilities = {capability.id: capability for capability in capabilities}

    def all(self) -> list[Capability]:
        return list(self._capabilities.values())

    def get(self, capability_id: str | None) -> Capability | None:
        if capability_id is None:
            return None
        return self._capabilities.get(capability_id)

    def for_active_intent(self, active_intent: str | None) -> Capability | None:
        if active_intent is None:
            return None
        return next(
            (capability for capability in self._capabilities.values() if capability.active_intent == active_intent),
            None,
        )

    def match(self, request: AgentRequest) -> tuple[Capability, CapabilityRuleMatch] | None:
        matches = [
            (capability, match)
            for capability in self._capabilities.values()
            if (match := capability.match(request)) is not None
        ]
        return max(matches, key=lambda item: item[1].confidence, default=None)


def create_default_capability_registry() -> CapabilityRegistry:
    return CapabilityRegistry([WorklogCapability()])
