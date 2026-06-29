from __future__ import annotations

from typing import Any

from app.agent.registry import create_default_capability_registry
from app.tools.business import build_business_tool

from .models import (
    AgentRequest,
    Artifact,
    ConversationPatch,
    ExecutionError,
    ExecutionReport,
    PlanResult,
    PlanStep,
    StepResult,
)
from .state import AgentRuntimeContext


async def execute_plan(
    request: AgentRequest,
    plan: PlanResult,
    runtime: AgentRuntimeContext,
    *,
    attempt: int,
) -> ExecutionReport:
    if plan.status != "ready":
        return ExecutionReport(
            status="blocked",
            attempt=attempt,
            error=ExecutionError(
                code="plan_not_ready",
                message=plan.clarification_message or "执行计划尚未准备完成",
            ),
        )
    if plan.mode == "single" and len(plan.steps) != 1:
        return _invalid_plan_report(attempt, "单任务计划必须且只能包含一个步骤")
    if plan.mode not in {"single", "sequential"}:
        return _invalid_plan_report(attempt, f"暂不支持执行模式：{plan.mode}")

    results: dict[str, dict[str, object]] = {}
    step_results: list[StepResult] = []
    artifacts: list[Artifact] = []
    for step in plan.steps:
        try:
            artifact = await _execute_step(request, step, runtime, results=results)
        except Exception as exc:
            retryable = isinstance(exc, (TimeoutError, ConnectionError)) and step.retry_policy.idempotent
            error = ExecutionError(
                code=type(exc).__name__,
                message=str(exc),
                retryable=retryable,
                step_id=step.id,
            )
            step_results.append(StepResult(step_id=step.id, status="failed", attempt=attempt, error=error))
            return ExecutionReport(
                status="failed",
                attempt=attempt,
                step_results=step_results,
                artifacts=artifacts,
                error=error,
            )

        artifacts.append(artifact)
        results[step.id] = artifact.data
        step_results.append(
            StepResult(
                step_id=step.id,
                status="succeeded",
                attempt=attempt,
                output=artifact.data,
            )
        )

    return ExecutionReport(
        status="succeeded",
        attempt=attempt,
        step_results=step_results,
        artifacts=artifacts,
        conversation_patch=ConversationPatch(),
    )


async def _execute_step(
    request: AgentRequest,
    step: PlanStep,
    runtime: AgentRuntimeContext,
    *,
    results: dict[str, dict[str, object]],
) -> Artifact:
    payload = _resolve_payload(step.input_payload, results)
    if step.kind == "subgraph":
        return await _execute_subgraph(step, payload, runtime)
    if step.kind == "tool":
        return await _execute_tool(step, payload, runtime)
    raise ValueError(f"不支持的步骤类型：{step.kind}")


async def _execute_subgraph(
    step: PlanStep,
    payload: dict[str, object],
    runtime: AgentRuntimeContext,
) -> Artifact:
    capability = create_default_capability_registry().get(step.capability)
    if capability is None:
        raise ValueError(f"未注册执行能力：{step.capability}")
    return await capability.execute(step, payload, runtime)


async def _execute_tool(
    step: PlanStep,
    payload: dict[str, object],
    runtime: AgentRuntimeContext,
) -> Artifact:
    tool = build_business_tool(step.target, runtime.llm_client)
    validated_payload = tool.input_schema.model_validate(payload)
    result = await tool.execute(validated_payload)
    return Artifact(
        kind="tool_result",
        data={
            "type": "tool_result",
            "tool": step.target,
            "capability": step.capability,
            "output": _dump_tool_output(result),
        },
    )


def _invalid_plan_report(attempt: int, message: str) -> ExecutionReport:
    return ExecutionReport(
        status="failed",
        attempt=attempt,
        error=ExecutionError(code="invalid_plan", message=message),
    )


def _dump_tool_output(result: Any) -> dict[str, object]:
    if hasattr(result, "model_dump"):
        return result.model_dump(mode="json")
    if isinstance(result, dict):
        return result
    raise TypeError("工具结果必须是字典或支持 model_dump()")


def _resolve_payload(
    payload: dict[str, object],
    results: dict[str, dict[str, object]],
) -> dict[str, object]:
    resolved = _resolve_value(payload, results)
    if not isinstance(resolved, dict):
        raise TypeError("解析后的步骤输入必须是字典")
    return resolved


def _resolve_value(value: object, results: dict[str, dict[str, object]]) -> object:
    if isinstance(value, dict):
        ref = value.get("$from")
        if isinstance(ref, str):
            return _resolve_ref(ref, results)
        return {key: _resolve_value(item, results) for key, item in value.items()}
    if isinstance(value, list):
        return [_resolve_value(item, results) for item in value]
    return value


def _resolve_ref(ref: str, results: dict[str, dict[str, object]]) -> object:
    parts = ref.split(".")
    if len(parts) < 2:
        raise ValueError(f"无效的任务引用：{ref}")
    current: object = results[parts[0]]
    for part in parts[1:]:
        if not isinstance(current, dict):
            raise ValueError(f"任务引用没有指向对象：{ref}")
        current = current[part]
    return current
