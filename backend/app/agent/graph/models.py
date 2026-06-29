from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, Field, JsonValue

from app.schemas.mixi import MixiChatHistoryItem, MixiConversationState

class AgentRequest(BaseModel):
    request_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    prompt: str = Field(min_length=1, max_length=4000)
    history: list[MixiChatHistoryItem] = Field(default_factory=list, max_length=20)
    conversation: MixiConversationState = Field(default_factory=MixiConversationState)


class PolicyAssessment(BaseModel):
    status: Literal["allow", "confirm", "deny"] = "allow"
    reason: str | None = None
    blocked_capabilities: list[str] = Field(default_factory=list)


class CapabilityAvailability(BaseModel):
    capability: str
    name: str | None = None
    description: str | None = None
    available: bool | None = None
    missing_requirements: list[str] = Field(default_factory=list)


class ContextSnapshot(BaseModel):
    recent_messages: list[MixiChatHistoryItem] = Field(default_factory=list)
    conversation_summary: str | None = None
    long_term_memories: list[str] = Field(default_factory=list)
    capabilities: list[CapabilityAvailability] = Field(default_factory=list)
    policy: PolicyAssessment = Field(default_factory=PolicyAssessment)


class SemanticIntent(BaseModel):
    action: str
    objects: list[str] = Field(default_factory=list)
    filters: dict[str, list[str]] = Field(default_factory=dict)


class CapabilityCandidate(BaseModel):
    capability: str
    confidence: float = Field(ge=0, le=1)


class CapabilityRuleMatch(BaseModel):
    rule_id: str
    goal: str
    intents: list[SemanticIntent] = Field(default_factory=list)
    extracted_slots: dict[str, JsonValue] = Field(default_factory=dict)
    missing_slots: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    terminal: bool = True
    requested_action: Literal["route", "confirm", "cancel"] = "route"


class IntentResult(BaseModel):
    goal: str
    intents: list[SemanticIntent] = Field(default_factory=list)
    candidate_capabilities: list[CapabilityCandidate] = Field(default_factory=list)
    extracted_slots: dict[str, JsonValue] = Field(default_factory=dict)
    missing_slots: list[str] = Field(default_factory=list)
    ambiguities: list[str] = Field(default_factory=list)
    complexity: Literal["simple", "complex"] = "simple"
    confidence: float = Field(default=0, ge=0, le=1)
    requested_action: Literal["route", "confirm", "cancel"] = "route"
    recognition_source: Literal["rule", "context", "llm", "fallback"] = "fallback"
    matched_rules: list[str] = Field(default_factory=list)


class RouteDecision(BaseModel):
    target: Literal["clarification", "planner", "executor", "final"]
    selected_capability: str | None = None
    reason_code: str
    reason: str
    policy: Literal["allow", "confirm", "deny"] = "allow"


class ClarificationQuestion(BaseModel):
    field: str
    prompt: str
    required: bool = True
    choices: list[str] = Field(default_factory=list)


class ClarificationState(BaseModel):
    status: Literal["pending", "resolved"]
    questions: list[ClarificationQuestion] = Field(default_factory=list)
    answers: dict[str, JsonValue] = Field(default_factory=dict)
    resume_target: Literal["intent", "planner"] = "intent"


class RetryPolicy(BaseModel):
    max_attempts: int = Field(default=1, ge=1, le=5)
    idempotent: bool = False
    retryable_errors: list[str] = Field(default_factory=list)


class PlanStep(BaseModel):
    id: str
    title: str
    kind: Literal["subgraph", "tool"]
    target: str
    capability: str
    input_payload: dict[str, JsonValue] = Field(default_factory=dict)
    depends_on: list[str] = Field(default_factory=list)
    side_effect: Literal["none", "reversible", "irreversible"] = "none"
    retry_policy: RetryPolicy = Field(default_factory=RetryPolicy)


class ConversationPatch(BaseModel):
    active_intent: str | None = None
    awaiting_confirmation: bool = False
    missing_fields: list[str] = Field(default_factory=list)
    checkpoint_thread_id: str | None = None


class PlanResult(BaseModel):
    plan_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    status: Literal["ready", "blocked", "failed"]
    objective: str
    mode: Literal["single", "parallel", "sequential", "hybrid"] = "single"
    steps: list[PlanStep] = Field(default_factory=list)
    missing_requirements: list[str] = Field(default_factory=list)
    clarification_message: str | None = None
    conversation_patch: ConversationPatch | None = None
    attempt: int = Field(default=1, ge=1)


class ExecutionError(BaseModel):
    code: str
    message: str
    retryable: bool = False
    step_id: str | None = None


class Artifact(BaseModel):
    kind: str
    data: dict[str, JsonValue]


class StepResult(BaseModel):
    step_id: str
    status: Literal["succeeded", "failed", "skipped"]
    attempt: int = Field(default=1, ge=1)
    output: dict[str, JsonValue] | None = None
    error: ExecutionError | None = None


class ExecutionReport(BaseModel):
    status: Literal["succeeded", "partial", "failed", "blocked"]
    attempt: int = Field(default=1, ge=1)
    step_results: list[StepResult] = Field(default_factory=list)
    artifacts: list[Artifact] = Field(default_factory=list)
    error: ExecutionError | None = None
    conversation_patch: ConversationPatch | None = None


class ReflectionResult(BaseModel):
    verdict: Literal["finish", "retry", "replan", "clarify"]
    next_node: Literal["executor", "planner", "clarification", "final"]
    reason: str
    failed_step_id: str | None = None
    feedback: list[str] = Field(default_factory=list)


class AgentResponse(BaseModel):
    kind: Literal["none", "message", "clarification", "task", "artifact", "error"]
    message: str | None = None
    task: dict[str, JsonValue] | None = None
    artifacts: list[Artifact] = Field(default_factory=list)
    conversation_patch: ConversationPatch = Field(default_factory=ConversationPatch)
    request_id: uuid.UUID | None = None
