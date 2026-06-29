from __future__ import annotations

from typing import TypedDict

from app.agent.base import CapabilityRuntime

from .models import (
    AgentRequest,
    AgentResponse,
    ClarificationState,
    ContextSnapshot,
    ExecutionReport,
    IntentResult,
    PlanResult,
    ReflectionResult,
    RouteDecision,
)


AgentRuntimeContext = CapabilityRuntime


class AgentGraphState(TypedDict, total=False):
    request: AgentRequest
    context: ContextSnapshot
    intent: IntentResult
    route: RouteDecision
    clarification: ClarificationState
    plan: PlanResult
    execution: ExecutionReport
    reflection: ReflectionResult
    response: AgentResponse


class AgentGraphInput(TypedDict):
    request: AgentRequest


class AgentGraphOutput(TypedDict, total=False):
    response: AgentResponse
