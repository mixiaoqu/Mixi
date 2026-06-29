from __future__ import annotations

import json
from datetime import datetime
from zoneinfo import ZoneInfo

from langgraph.runtime import Runtime
from langgraph.types import interrupt

from app.agent.base import IntakeContext
from app.agent.registry import create_default_capability_registry
from app.core.config import settings

from .models import (
    AgentRequest,
    AgentResponse,
    CapabilityAvailability,
    CapabilityCandidate,
    CapabilityRuleMatch,
    ClarificationQuestion,
    ClarificationState,
    ContextSnapshot,
    ConversationPatch,
    ExecutionError,
    ExecutionReport,
    IntentResult,
    PlanResult,
    PolicyAssessment,
    ReflectionResult,
    RouteDecision,
    SemanticIntent,
)
from .runtime import execute_plan
from .state import AgentGraphState, AgentRuntimeContext

DELETE_ADMIN_CAPABILITY = "admin.user.delete"


async def context(
    state: AgentGraphState,
    runtime: Runtime[AgentRuntimeContext],
) -> AgentGraphState:
    request = state["request"]
    registry = create_default_capability_registry()
    policy = await _assess_policy(request.prompt, runtime.context.llm_client)
    return {
        "context": ContextSnapshot(
            recent_messages=request.history[-6:],
            capabilities=[capability.catalog_entry() for capability in registry.all()],
            policy=policy,
        )
    }


async def intent(
    state: AgentGraphState,
    runtime: Runtime[AgentRuntimeContext],
) -> AgentGraphState:
    request = state["request"]
    registry = create_default_capability_registry()
    control_match = _match_control_rule(request, registry)
    if control_match is not None:
        capability = registry.for_active_intent(request.conversation.active_intent)
        return {"intent": _intent_from_rule(control_match, capability_id=None if capability is None else capability.id)}

    capability_match = registry.match(request)
    if capability_match is not None:
        capability, match = capability_match
        if match.terminal and match.confidence >= 0.9:
            source = "context" if match.rule_id.endswith("context_follow_up") else "rule"
            return {"intent": _intent_from_rule(match, capability_id=capability.id, source=source)}

    recognized = await _recognize_with_llm(request, registry, runtime.context.llm_client)
    return {"intent": recognized}


def router(
    state: AgentGraphState,
    runtime: Runtime[AgentRuntimeContext],
) -> AgentGraphState:
    context_snapshot = state["context"]
    intent_result = state["intent"]
    policy = context_snapshot.policy
    registry = create_default_capability_registry()

    if intent_result.requested_action == "cancel":
        decision = RouteDecision(
            target="final",
            reason_code="user_cancelled",
            reason="用户请求取消当前任务",
        )
    elif policy.status == "deny":
        decision = RouteDecision(
            target="final",
            reason_code="policy_denied",
            reason=policy.reason or "请求被安全策略拦截",
            policy="deny",
        )
    elif policy.status == "confirm" or intent_result.requested_action == "confirm":
        decision = RouteDecision(
            target="clarification",
            selected_capability=_first_capability(intent_result),
            reason_code="confirmation_required",
            reason=policy.reason or "执行前需要用户确认",
            policy="confirm",
        )
    elif not intent_result.candidate_capabilities:
        decision = RouteDecision(
            target="final",
            reason_code="general_chat",
            reason="请求属于普通对话",
        )
    else:
        capability = _first_capability(intent_result)
        handler = registry.get(capability)
        availability = None if handler is None else handler.check_availability(runtime.context)
        if availability is not None:
            entries = [item for item in context_snapshot.capabilities if item.capability != availability.capability]
            context_snapshot = context_snapshot.model_copy(update={"capabilities": [*entries, availability]})
        if availability is not None and not availability.available:
            decision = RouteDecision(
                target="clarification",
                selected_capability=capability,
                reason_code="capability_requirements_missing",
                reason="执行能力缺少必要前置条件",
            )
        elif state.get("plan") is not None and state["plan"].status == "ready":
            decision = RouteDecision(
                target="executor",
                selected_capability=capability,
                reason_code="existing_plan_ready",
                reason="已有可执行计划",
            )
        else:
            decision = RouteDecision(
                target="planner",
                selected_capability=capability,
                reason_code="planning_required",
                reason="请求需要生成执行计划",
            )
    return {"context": context_snapshot, "route": decision}


def route_after_router(state: AgentGraphState) -> str:
    return state["route"].target


def clarification(
    state: AgentGraphState,
    runtime: Runtime[AgentRuntimeContext],
) -> AgentGraphState:
    request = state["request"]
    route = state["route"]
    plan = state.get("plan")
    registry = create_default_capability_registry()
    capability = registry.get(route.selected_capability)
    missing = list(state["intent"].missing_slots)
    availability = _find_capability(state["context"], route.selected_capability)
    if availability is not None:
        missing.extend(item for item in availability.missing_requirements if item not in missing)
    if plan is not None:
        missing.extend(item for item in plan.missing_requirements if item not in missing)

    if capability is not None:
        message, questions, patch = capability.build_clarification(
            reason_code=route.reason_code,
            missing_requirements=missing,
            plan=plan,
        )
    else:
        message = route.reason if route.reason_code == "confirmation_required" else "请补充任务所需的信息。"
        questions = [ClarificationQuestion(field="request", prompt=message)]
        patch = ConversationPatch(awaiting_confirmation=route.reason_code == "confirmation_required")

    resume_target = "planner" if route.selected_capability else "intent"
    answer = interrupt(
        {
            "message": message,
            "questions": [question.model_dump(mode="json") for question in questions],
            "conversation_patch": patch.model_dump(mode="json"),
        }
    )
    answer_text = _resume_text(answer)
    if _is_cancel_or_negative(answer_text):
        return {
            "clarification": ClarificationState(
                status="pending",
                questions=questions,
                resume_target=resume_target,
            ),
            "response": AgentResponse(
                kind="message",
                message="好的，已取消当前任务。你可以直接告诉我接下来想做什么。",
                conversation_patch=ConversationPatch(),
                request_id=request.request_id,
            ),
        }

    return {
        "clarification": ClarificationState(
            status="resolved",
            questions=questions,
            answers={"response": answer_text},
            resume_target=resume_target,
        )
    }


def route_after_clarification(state: AgentGraphState) -> str:
    clarification_state = state["clarification"]
    if clarification_state.status == "pending":
        return "final"
    return clarification_state.resume_target


async def planner(
    state: AgentGraphState,
    runtime: Runtime[AgentRuntimeContext],
) -> AgentGraphState:
    request = state["request"]
    route = state["route"]
    capability_id = route.selected_capability
    attempt = 1 if state.get("plan") is None else state["plan"].attempt + 1
    capability = create_default_capability_registry().get(capability_id)
    if capability is None:
        return {
            "plan": PlanResult(
                status="failed",
                objective=state["intent"].goal,
                clarification_message="当前没有可处理该请求的能力。",
                attempt=attempt,
            )
        }

    plan_result = await capability.plan(
        IntakeContext(
            prompt=request.prompt,
            history=request.history,
            state=request.conversation,
            now=datetime.now(ZoneInfo(request.conversation.timezone)),
            current_user=runtime.context.current_user,
            repositories=runtime.context.repositories,
            llm_client=runtime.context.llm_client,
        ),
        state["intent"],
        attempt=attempt,
    )
    return {"plan": plan_result}


async def executor(
    state: AgentGraphState,
    runtime: Runtime[AgentRuntimeContext],
) -> AgentGraphState:
    plan = state.get("plan")
    if plan is None:
        return {
            "execution": ExecutionReport(
                status="failed",
                error=ExecutionError(code="missing_plan", message="没有可执行计划"),
            )
        }
    previous = state.get("execution")
    attempt = 1 if previous is None else previous.attempt + 1
    report = await execute_plan(state["request"], plan, runtime.context, attempt=attempt)
    return {"execution": report}


def reflection(
    state: AgentGraphState,
    runtime: Runtime[AgentRuntimeContext],
) -> AgentGraphState:
    del runtime
    plan = state.get("plan")
    execution = state.get("execution")
    if execution is None:
        result = ReflectionResult(
            verdict="finish",
            next_node="final",
            reason="没有需要验证的执行结果",
        )
    elif execution.status == "succeeded":
        result = ReflectionResult(
            verdict="finish",
            next_node="final",
            reason="所有计划步骤执行成功",
        )
    elif execution.status == "blocked":
        result = ReflectionResult(
            verdict="clarify",
            next_node="clarification",
            reason="执行计划缺少必要信息",
        )
    elif execution.error is not None and execution.error.retryable and _can_retry(plan, execution):
        result = ReflectionResult(
            verdict="retry",
            next_node="executor",
            reason="执行出现可重试错误",
            failed_step_id=execution.error.step_id,
        )
    elif plan is not None and plan.attempt < 2:
        result = ReflectionResult(
            verdict="replan",
            next_node="planner",
            reason="执行失败，重新生成一次计划",
            failed_step_id=None if execution.error is None else execution.error.step_id,
        )
    else:
        result = ReflectionResult(
            verdict="clarify",
            next_node="clarification",
            reason="自动执行与重规划均未解决问题，需要用户补充信息",
            failed_step_id=None if execution.error is None else execution.error.step_id,
        )
    return {"reflection": result}


def route_after_reflection(state: AgentGraphState) -> str:
    return state["reflection"].next_node


def final_response(
    state: AgentGraphState,
    runtime: Runtime[AgentRuntimeContext],
) -> AgentGraphState:
    del runtime
    if state.get("response") is not None:
        return {}
    request = state["request"]
    route = state["route"]
    execution = state.get("execution")
    if route.reason_code == "user_cancelled":
        response = AgentResponse(
            kind="message",
            message="好的，已取消当前任务。你可以直接告诉我接下来想做什么。",
            request_id=request.request_id,
        )
    elif route.reason_code == "policy_denied":
        response = AgentResponse(
            kind="error",
            message=route.reason,
            request_id=request.request_id,
        )
    elif route.reason_code == "general_chat":
        response = AgentResponse(kind="none", request_id=request.request_id)
    elif execution is not None and execution.status == "succeeded":
        response = AgentResponse(
            kind="artifact",
            artifacts=execution.artifacts,
            conversation_patch=execution.conversation_patch or ConversationPatch(),
            request_id=request.request_id,
        )
    else:
        response = AgentResponse(
            kind="error",
            message="任务未能完成，请检查输入后重试。",
            request_id=request.request_id,
        )
    return {"response": response}


async def _assess_policy(prompt: str, client) -> PolicyAssessment:
    if _contains_delete_admin_signal(prompt):
        return PolicyAssessment(
            status="deny",
            reason="请求包含高风险不可逆操作：删除管理员用户",
            blocked_capabilities=[DELETE_ADMIN_CAPABILITY],
        )
    if client is None:
        return PolicyAssessment(reason="未配置可用模型，已使用本地安全规则")
    try:
        completion = await client.chat.completions.create(
            model=settings.openai_model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "你是安全策略节点。只输出 JSON，字段为 status、reason、blocked_capabilities。"
                        "status 只能是 allow、confirm、deny。明显破坏性或越权请求返回 deny。"
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        )
        payload = json.loads(completion.choices[0].message.content or "{}")
        status = payload.get("status")
        if status not in {"allow", "confirm", "deny"}:
            raise ValueError("invalid policy status")
        if status == "confirm" and not _contains_confirmation_required_signal(prompt):
            status = "allow"
        blocked = payload.get("blocked_capabilities")
        return PolicyAssessment(
            status=status,
            reason=payload.get("reason") if isinstance(payload.get("reason"), str) else None,
            blocked_capabilities=[str(item) for item in blocked] if isinstance(blocked, list) else [],
        )
    except Exception:
        return PolicyAssessment(reason="安全判断调用模型失败，已使用本地安全规则")


def _match_control_rule(request: AgentRequest, registry) -> CapabilityRuleMatch | None:
    normalized = request.prompt.strip().lower()
    cancel_tokens = ("取消", "算了", "不用了", "停止", "cancel", "stop")
    negative_tokens = ("不是", "不对", "不要", "不确认")
    affirmative_tokens = ("是", "对", "确认", "继续", "可以")
    if any(token in normalized for token in cancel_tokens):
        return CapabilityRuleMatch(
            rule_id="control.cancel",
            goal="取消当前任务",
            intents=[SemanticIntent(action="cancel", objects=["current_task"])],
            confidence=1.0,
            requested_action="cancel",
        )
    if request.conversation.awaiting_confirmation:
        if any(token in normalized for token in negative_tokens):
            return CapabilityRuleMatch(
                rule_id="control.confirm_no",
                goal="拒绝执行当前任务",
                intents=[SemanticIntent(action="cancel", objects=["current_task"])],
                confidence=1.0,
                requested_action="cancel",
            )
        if any(token == normalized or token in normalized for token in affirmative_tokens):
            capability = registry.for_active_intent(request.conversation.active_intent)
            return CapabilityRuleMatch(
                rule_id="control.confirm_yes",
                goal="确认执行当前任务",
                intents=[
                    SemanticIntent(
                        action="confirm",
                        objects=["current_task" if capability is None else capability.id],
                    )
                ],
                confidence=1.0,
                requested_action="route",
            )
    return None


def _intent_from_rule(
    match: CapabilityRuleMatch,
    *,
    capability_id: str | None,
    source: str = "rule",
) -> IntentResult:
    candidates = [] if capability_id is None else [
        CapabilityCandidate(capability=capability_id, confidence=match.confidence)
    ]
    return IntentResult(
        goal=match.goal,
        intents=match.intents,
        candidate_capabilities=candidates,
        extracted_slots=match.extracted_slots,
        missing_slots=match.missing_slots,
        complexity="complex" if len(match.intents) > 1 else "simple",
        confidence=match.confidence,
        requested_action=match.requested_action,
        recognition_source=source,
        matched_rules=[match.rule_id],
    )


async def _recognize_with_llm(request: AgentRequest, registry, client) -> IntentResult:
    if client is None:
        return _fallback_intent(request)
    capability_catalog = [
        {
            "id": capability.id,
            "name": capability.name,
            "description": capability.description,
        }
        for capability in registry.all()
    ]
    try:
        completion = await client.chat.completions.create(
            model=settings.openai_model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "你是通用智能体平台的意图识别器。只输出 JSON："
                        "goal、intents、capability、confidence、needs_clarification。"
                        "intents 每项包含 action、objects、filters。"
                        "capability 必须从候选能力 ID 中选择，无法匹配时返回 null。"
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "prompt": request.prompt,
                            "history": [item.model_dump() for item in request.history[-6:]],
                            "conversation": request.conversation.model_dump(mode="json"),
                            "capabilities": capability_catalog,
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
        )
        payload = json.loads(completion.choices[0].message.content or "{}")
        parsed = _parse_llm_intent(payload, registry)
        if parsed is not None:
            return parsed
    except Exception:
        pass
    return _fallback_intent(request)


def _parse_llm_intent(payload: object, registry) -> IntentResult | None:
    if not isinstance(payload, dict) or not isinstance(payload.get("goal"), str):
        return None
    raw_intents = payload.get("intents")
    if not isinstance(raw_intents, list):
        return None
    intents: list[SemanticIntent] = []
    extracted_slots: dict[str, list[str]] = {}
    for item in raw_intents:
        if not isinstance(item, dict) or not isinstance(item.get("objects"), list):
            continue
        action = str(item.get("action") or "").strip()
        if not action:
            continue
        filters = _normalize_filters(item.get("filters"))
        extracted_slots.update(filters)
        intents.append(
            SemanticIntent(
                action=action,
                objects=[str(value) for value in item["objects"]],
                filters=filters,
            )
        )
    if not intents:
        return None
    capability_id = payload.get("capability")
    capability = registry.get(capability_id if isinstance(capability_id, str) else None)
    confidence = _normalize_confidence(payload.get("confidence"))
    needs_clarification = payload.get("needs_clarification") is True
    return IntentResult(
        goal=payload["goal"],
        intents=intents,
        candidate_capabilities=[]
        if capability is None
        else [CapabilityCandidate(capability=capability.id, confidence=confidence)],
        extracted_slots=extracted_slots,
        ambiguities=["模型判断该请求需要澄清"] if needs_clarification else [],
        complexity="complex" if len(intents) > 1 else "simple",
        confidence=confidence,
        requested_action="confirm" if needs_clarification and capability is not None else "route",
        recognition_source="llm",
    )


def _fallback_intent(request: AgentRequest) -> IntentResult:
    return IntentResult(
        goal=request.prompt,
        intents=[SemanticIntent(action="chat", objects=["general_request"])],
        confidence=0.3,
        recognition_source="fallback",
    )


def _find_capability(context_snapshot: ContextSnapshot, capability: str | None) -> CapabilityAvailability | None:
    return next((item for item in context_snapshot.capabilities if item.capability == capability), None)


def _first_capability(intent_result: IntentResult) -> str | None:
    return intent_result.candidate_capabilities[0].capability if intent_result.candidate_capabilities else None


def _can_retry(plan: PlanResult | None, execution: ExecutionReport) -> bool:
    if plan is None or execution.error is None or execution.error.step_id is None:
        return False
    step = next((item for item in plan.steps if item.id == execution.error.step_id), None)
    return step is not None and execution.attempt < step.retry_policy.max_attempts


def _normalize_confidence(value: object) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


def _normalize_filters(value: object) -> dict[str, list[str]]:
    if not isinstance(value, dict):
        return {}
    return {
        str(key): [str(item) for item in values]
        for key, values in value.items()
        if isinstance(values, list) and values
    }


def _contains_delete_admin_signal(prompt: str) -> bool:
    lower = prompt.lower()
    return (
        any(token in lower for token in ("删除", "删掉", "移除", "delete", "remove"))
        and any(token in lower for token in ("管理员", "admin"))
        and any(token in lower for token in ("用户", "user"))
    )


def _contains_confirmation_required_signal(prompt: str) -> bool:
    lower = prompt.lower()
    return any(
        token in lower
        for token in (
            "删除",
            "删掉",
            "移除",
            "修改",
            "更新",
            "发送",
            "钉钉",
            "webhook",
            "delete",
            "remove",
            "update",
            "send",
        )
    )


def _resume_text(value: object) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        for key in ("response", "answer", "message", "prompt"):
            item = value.get(key)
            if isinstance(item, str):
                return item.strip()
    return str(value).strip()


def _is_cancel_or_negative(value: str) -> bool:
    normalized = value.lower()
    return any(
        token in normalized
        for token in ("取消", "算了", "不用了", "停止", "不是", "不对", "不要", "不确认", "cancel", "stop", "no")
    )
