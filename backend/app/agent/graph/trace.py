from __future__ import annotations

import inspect
import logging
from collections.abc import Awaitable, Callable
from time import perf_counter

from langgraph.errors import GraphInterrupt
from langgraph.runtime import Runtime

from app.observability.logging import log_pretty_event

from .state import AgentGraphState, AgentRuntimeContext

NodeCallable = Callable[
    [AgentGraphState, Runtime[AgentRuntimeContext]],
    AgentGraphState | Awaitable[AgentGraphState],
]
RouteCallable = Callable[[AgentGraphState], str]

logger = logging.getLogger("app.agent.graph")

NODE_LABELS = {
    "context": "1. 上下文加载（Context）",
    "intent": "2. 意图解析（Intent）",
    "router": "3. 路由决策（Router）",
    "clarification": "4. 信息澄清（Clarification）",
    "planner": "5. 任务规划（Planner）",
    "executor": "6. 任务执行（Executor）",
    "reflection": "7. 结果反思（Reflection）",
    "final": "8. 最终响应（Final）",
}

ROUTE_LABELS = {
    "intent": "意图解析（Intent）",
    "clarification": "信息澄清（Clarification）",
    "planner": "任务规划（Planner）",
    "executor": "任务执行（Executor）",
    "reflection": "结果反思（Reflection）",
    "final": "最终响应（Final）",
}


def trace_node(node_key: str, node: NodeCallable) -> NodeCallable:
    async def traced(
        state: AgentGraphState,
        runtime: Runtime[AgentRuntimeContext],
    ) -> AgentGraphState:
        conversation_id = str(state["request"].conversation.conversation_id)
        label = NODE_LABELS[node_key]
        log_pretty_event(
            logger,
            "智能体节点开始",
            {
                "会话ID": conversation_id,
                "节点": label,
                "输入摘要": _summarize_input(node_key, state),
            },
        )
        started_at = perf_counter()
        try:
            result = node(state, runtime)
            update = await result if inspect.isawaitable(result) else result
        except GraphInterrupt:
            raise
        except Exception:
            elapsed_ms = round((perf_counter() - started_at) * 1000, 2)
            logger.exception(
                "智能体节点失败 会话ID=%s 节点=%s 耗时=%sms",
                conversation_id,
                label,
                elapsed_ms,
            )
            raise

        merged_state: AgentGraphState = {**state, **update}
        log_pretty_event(
            logger,
            "智能体节点完成",
            {
                "会话ID": conversation_id,
                "节点": label,
                "状态": "成功",
                "耗时毫秒": round((perf_counter() - started_at) * 1000, 2),
                "结果摘要": _summarize_node(node_key, merged_state),
            },
        )
        return update

    return traced


def trace_route(source_key: str, route: RouteCallable) -> RouteCallable:
    def traced(state: AgentGraphState) -> str:
        target_key = route(state)
        log_pretty_event(
            logger,
            "智能体路由选择",
            {
                "会话ID": str(state["request"].conversation.conversation_id),
                "来源节点": NODE_LABELS[source_key],
                "目标节点": ROUTE_LABELS.get(target_key, target_key),
                "路由标识": target_key,
            },
        )
        return target_key

    return traced


def _summarize_node(node_key: str, state: AgentGraphState) -> dict[str, object]:
    if node_key == "context":
        snapshot = state["context"]
        return {
            "安全判断": _label(snapshot.policy.status),
            "安全原因": snapshot.policy.reason,
            "能力状态": [
                {
                    "能力": item.capability,
                    "可用": item.available,
                    "缺失条件": item.missing_requirements,
                }
                for item in snapshot.capabilities
            ],
        }
    if node_key == "intent":
        result = state["intent"]
        return {
            "用户目标": result.goal,
            "意图": [
                {
                    "动作": _label(item.action),
                    "对象": item.objects,
                    "筛选条件": item.filters,
                }
                for item in result.intents
            ],
            "候选能力": [item.model_dump(mode="json") for item in result.candidate_capabilities],
            "已提取参数": result.extracted_slots,
            "歧义": result.ambiguities,
            "置信度": result.confidence,
            "识别来源": _label(result.recognition_source),
            "命中规则": result.matched_rules,
        }
    if node_key == "router":
        route = state["route"]
        return {
            "目标节点": ROUTE_LABELS.get(route.target, route.target),
            "选择能力": route.selected_capability,
            "原因编码": route.reason_code,
            "原因": route.reason,
            "安全策略": _label(route.policy),
        }
    if node_key == "clarification":
        clarification = state["clarification"]
        return {
            "状态": _label(clarification.status),
            "问题": [item.model_dump(mode="json") for item in clarification.questions],
            "恢复目标": ROUTE_LABELS.get(clarification.resume_target, clarification.resume_target),
        }
    if node_key == "planner":
        plan = state["plan"]
        return {
            "计划ID": str(plan.plan_id),
            "状态": _label(plan.status),
            "目标": plan.objective,
            "规划次数": plan.attempt,
            "缺失条件": plan.missing_requirements,
            "步骤": [
                {
                    "步骤ID": item.id,
                    "标题": item.title,
                    "类型": _label(item.kind),
                    "能力": item.capability,
                    "副作用": _label(item.side_effect),
                }
                for item in plan.steps
            ],
        }
    if node_key == "executor":
        report = state["execution"]
        return {
            "状态": _label(report.status),
            "执行次数": report.attempt,
            "步骤结果": [
                {"步骤ID": item.step_id, "状态": _label(item.status), "错误": item.error}
                for item in report.step_results
            ],
            "产物类型": [item.kind for item in report.artifacts],
            "错误": report.error,
        }
    if node_key == "reflection":
        reflection = state["reflection"]
        return {
            "结论": _label(reflection.verdict),
            "下一节点": ROUTE_LABELS.get(reflection.next_node, reflection.next_node),
            "原因": reflection.reason,
            "失败步骤": reflection.failed_step_id,
        }
    response = state.get("response")
    return {
        "响应类型": None if response is None else _label(response.kind),
        "消息摘要": None if response is None or response.message is None else _truncate(response.message),
        "产物类型": [] if response is None else [item.kind for item in response.artifacts],
    }


def _summarize_input(node_key: str, state: AgentGraphState) -> dict[str, object]:
    request = state["request"]
    if node_key == "context":
        return {
            "请求ID": str(request.request_id),
            "用户输入": _truncate(request.prompt),
            "历史消息数": len(request.history),
            "当前意图": request.conversation.active_intent,
            "待补字段": request.conversation.missing_fields,
        }
    if node_key == "intent":
        snapshot = state["context"]
        return {
            "用户输入": _truncate(request.prompt),
            "安全状态": _label(snapshot.policy.status),
            "已注册能力": [item.capability for item in snapshot.capabilities],
        }
    if node_key == "router":
        result = state["intent"]
        return {
            "用户目标": result.goal,
            "候选能力": [item.capability for item in result.candidate_capabilities],
            "缺失参数": result.missing_slots,
            "歧义": result.ambiguities,
        }
    if node_key == "clarification":
        route = state["route"]
        reflection = state.get("reflection")
        return {
            "路由原因": route.reason,
            "选择能力": route.selected_capability,
            "计划状态": None if state.get("plan") is None else _label(state["plan"].status),
            "反思结论": None if reflection is None else _label(reflection.verdict),
        }
    if node_key == "planner":
        route = state["route"]
        return {
            "用户目标": state["intent"].goal,
            "选择能力": route.selected_capability,
            "已提取参数": state["intent"].extracted_slots,
            "规划次数": 0 if state.get("plan") is None else state["plan"].attempt,
        }
    if node_key == "executor":
        plan = state.get("plan")
        return {
            "计划ID": None if plan is None else str(plan.plan_id),
            "计划状态": None if plan is None else _label(plan.status),
            "执行步骤": [] if plan is None else [item.id for item in plan.steps],
            "上次执行次数": 0 if state.get("execution") is None else state["execution"].attempt,
        }
    if node_key == "reflection":
        execution = state.get("execution")
        return {
            "计划状态": None if state.get("plan") is None else _label(state["plan"].status),
            "执行状态": None if execution is None else _label(execution.status),
            "执行错误": None if execution is None else execution.error,
        }
    route = state.get("route")
    reflection = state.get("reflection")
    return {
        "路由原因": None if route is None else route.reason_code,
        "反思结论": None if reflection is None else _label(reflection.verdict),
        "执行状态": None if state.get("execution") is None else _label(state["execution"].status),
        "已有响应": state.get("response") is not None,
    }


def _truncate(value: str, limit: int = 120) -> str:
    return value if len(value) <= limit else f"{value[:limit]}..."


def _label(value: str) -> str:
    return {
        "allow": "放行",
        "confirm": "需要确认",
        "deny": "拦截",
        "chat": "普通对话",
        "generate": "生成",
        "compare": "比较",
        "send": "发送",
        "pending": "等待用户补充",
        "resolved": "已解决",
        "ready": "可执行",
        "blocked": "被阻塞",
        "failed": "失败",
        "succeeded": "成功",
        "partial": "部分成功",
        "skipped": "已跳过",
        "subgraph": "子图",
        "tool": "工具",
        "none": "无直接响应",
        "reversible": "可逆",
        "irreversible": "不可逆",
        "finish": "完成",
        "retry": "重试",
        "replan": "重新规划",
        "clarify": "请求澄清",
        "message": "消息",
        "clarification": "澄清问题",
        "task": "任务提案",
        "artifact": "执行产物",
        "error": "错误",
        "rule": "能力规则",
        "context": "会话上下文",
        "llm": "大模型",
        "fallback": "兜底",
    }.get(value, value)
