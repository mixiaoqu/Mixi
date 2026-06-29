from __future__ import annotations

import asyncio
import types
import unittest
import uuid
from unittest.mock import AsyncMock, patch

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.runtime import Runtime

from app.agent.graph import PlatformGraph
from app.agent.graph.checkpoint import graph_state_serializer
from app.agent.graph.models import (
    AgentRequest,
    CapabilityCandidate,
    ContextSnapshot,
    ExecutionError,
    ExecutionReport,
    IntentResult,
    PlanResult,
    PlanStep,
    PolicyAssessment,
    RetryPolicy,
    RouteDecision,
    SemanticIntent,
)
from app.agent.graph.nodes import (
    intent,
    reflection,
    route_after_clarification,
    route_after_reflection,
    route_after_router,
    router,
)
from app.agent.graph.runtime import execute_plan
from app.agent.graph.state import AgentRuntimeContext
from app.schemas.mixi import MixiConversationState


def make_runtime(*, data_sources=None, llm_client=None):
    repositories = types.SimpleNamespace(
        git_data_sources=types.SimpleNamespace(list_by_user=lambda user_id: data_sources or []),
    )
    context = AgentRuntimeContext(
        current_user=types.SimpleNamespace(id=uuid.uuid4()),
        repositories=repositories,
        llm_client=llm_client,
    )
    return Runtime(context=context)


class PlatformGraphTests(unittest.TestCase):
    def test_platform_graph_uses_expected_nodes_and_edges(self) -> None:
        graph = PlatformGraph()._graph.get_graph()
        nodes = {node for node in graph.nodes if not node.startswith("__")}
        edges = {(edge.source, edge.target) for edge in graph.edges}

        self.assertEqual(
            nodes,
            {"context", "intent", "router", "clarification", "planner", "executor", "reflection", "final"},
        )
        self.assertTrue(
            {
                ("__start__", "context"),
                ("context", "intent"),
                ("intent", "router"),
                ("planner", "executor"),
                ("executor", "reflection"),
                ("final", "__end__"),
            }.issubset(edges)
        )

    def test_graph_state_is_partitioned_and_runtime_is_external(self) -> None:
        request = AgentRequest(prompt="你好")
        payload = request.model_dump(mode="json")

        self.assertIn("request_id", payload)
        self.assertIn("conversation", payload)
        self.assertNotIn("repositories", payload)
        self.assertNotIn("llm_client", payload)

    def test_graph_uses_task_scoped_checkpoint_thread_id(self) -> None:
        class FakeCompiledGraph:
            def __init__(self):
                self.config = None

            async def ainvoke(self, state, *, context, config):
                del state, context
                self.config = config
                return {}

        graph = PlatformGraph()
        fake_graph = FakeCompiledGraph()
        graph._graph = fake_graph
        request = AgentRequest(prompt="你好")

        response = asyncio.run(graph.ainvoke(request, make_runtime().context))

        self.assertEqual(response.kind, "none")
        self.assertEqual(
            fake_graph.config["configurable"]["thread_id"],
            f"{request.conversation.conversation_id}:{request.request_id}",
        )

    def test_graph_resumes_pending_interrupt_with_checkpoint_thread_id(self) -> None:
        async def run_test():
            request = AgentRequest(prompt="帮我生成工作日志")
            runtime = make_runtime()
            graph = PlatformGraph(checkpointer=InMemorySaver(serde=graph_state_serializer()))

            first = await graph.ainvoke(request, runtime.context)
            self.assertEqual(first.kind, "clarification")
            self.assertIsNotNone(first.conversation_patch.checkpoint_thread_id)

            follow_up = AgentRequest(
                prompt="取消",
                history=request.history,
                conversation=request.conversation.model_copy(
                    update=first.conversation_patch.model_dump()
                ),
            )
            second = await graph.ainvoke(follow_up, runtime.context)
            self.assertEqual(second.kind, "message")
            self.assertIsNone(second.conversation_patch.checkpoint_thread_id)

        asyncio.run(run_test())

    def test_intent_creates_semantic_result_without_route_state(self) -> None:
        result = asyncio.run(
            intent(
                {
                    "request": AgentRequest(prompt="帮我生成本周工作日志"),
                    "context": ContextSnapshot(),
                },
                make_runtime(),
            )
        )

        intent_result = result["intent"]
        self.assertEqual(intent_result.intents[0].action, "generate")
        self.assertEqual(intent_result.candidate_capabilities[0].capability, "worklog.generate")
        self.assertEqual(intent_result.recognition_source, "rule")
        self.assertEqual(intent_result.matched_rules, ["worklog.explicit"])
        self.assertNotIn("route", result)

    def test_high_confidence_capability_rule_skips_intent_llm(self) -> None:
        create = AsyncMock()
        client = types.SimpleNamespace(
            chat=types.SimpleNamespace(completions=types.SimpleNamespace(create=create)),
        )

        result = asyncio.run(
            intent(
                {
                    "request": AgentRequest(prompt="生成今天的工作日志"),
                    "context": ContextSnapshot(),
                },
                make_runtime(llm_client=client),
            )
        )

        self.assertEqual(result["intent"].recognition_source, "rule")
        create.assert_not_awaited()

    def test_operational_log_does_not_match_worklog_rule(self) -> None:
        result = asyncio.run(
            intent(
                {
                    "request": AgentRequest(prompt="分析最近的 API 错误日志"),
                    "context": ContextSnapshot(),
                },
                make_runtime(),
            )
        )

        self.assertEqual(result["intent"].candidate_capabilities, [])
        self.assertEqual(result["intent"].recognition_source, "fallback")

    def test_generic_log_generation_matches_worklog_rule(self) -> None:
        result = asyncio.run(
            intent(
                {
                    "request": AgentRequest(prompt="帮我生成这两周的日志"),
                    "context": ContextSnapshot(),
                },
                make_runtime(),
            )
        )

        intent_result = result["intent"]
        self.assertEqual(intent_result.candidate_capabilities[0].capability, "worklog.generate")
        self.assertEqual(intent_result.extracted_slots["time_range"], ["last_2_weeks"])
        self.assertEqual(intent_result.recognition_source, "rule")

    def test_router_selects_expected_targets(self) -> None:
        base_context = ContextSnapshot(
            policy=PolicyAssessment(status="allow"),
        )
        cases = (
            (
                IntentResult(goal="聊天", intents=[SemanticIntent(action="chat")]),
                "final",
            ),
            (
                IntentResult(
                    goal="生成日志",
                    intents=[SemanticIntent(action="generate", objects=["worklog"])],
                    candidate_capabilities=[CapabilityCandidate(capability="worklog.generate", confidence=0.9)],
                ),
                "planner",
            ),
            (
                IntentResult(
                    goal="确认日志",
                    requested_action="confirm",
                    candidate_capabilities=[CapabilityCandidate(capability="worklog.generate", confidence=0.6)],
                ),
                "clarification",
            ),
        )

        for intent_result, expected in cases:
            with self.subTest(expected=expected):
                update = router(
                    {
                        "request": AgentRequest(prompt="test"),
                        "context": base_context,
                        "intent": intent_result,
                    },
                    make_runtime(data_sources=[types.SimpleNamespace()]),
                )
                self.assertEqual(route_after_router(update), expected)

    def test_router_sends_ready_existing_plan_to_executor(self) -> None:
        state = {
            "request": AgentRequest(prompt="生成日志"),
            "context": ContextSnapshot(),
            "intent": IntentResult(
                goal="生成日志",
                candidate_capabilities=[CapabilityCandidate(capability="worklog.generate", confidence=0.9)],
            ),
            "plan": PlanResult(status="ready", objective="生成日志", steps=[]),
        }

        result = router(state, make_runtime(data_sources=[types.SimpleNamespace()]))

        self.assertEqual(result["route"].target, "executor")

    def test_reflection_routes_retry_replan_clarify_and_finish(self) -> None:
        step = PlanStep(
            id="step",
            title="读取数据",
            kind="tool",
            target="time_range_resolve",
            capability="time_range.resolve",
            retry_policy=RetryPolicy(max_attempts=2, idempotent=True),
        )
        cases = (
            (
                PlanResult(status="ready", objective="test", steps=[step]),
                ExecutionReport(
                    status="failed",
                    attempt=1,
                    error=ExecutionError(code="TimeoutError", message="timeout", retryable=True, step_id="step"),
                ),
                "executor",
            ),
            (
                PlanResult(status="ready", objective="test", steps=[step], attempt=1),
                ExecutionReport(status="failed", error=ExecutionError(code="failed", message="failed")),
                "planner",
            ),
            (
                PlanResult(status="ready", objective="test", steps=[step], attempt=2),
                ExecutionReport(status="failed", error=ExecutionError(code="failed", message="failed")),
                "clarification",
            ),
            (
                PlanResult(status="ready", objective="test", steps=[step]),
                ExecutionReport(status="succeeded"),
                "final",
            ),
        )

        for plan, execution, expected in cases:
            with self.subTest(expected=expected):
                update = reflection(
                    {
                        "request": AgentRequest(prompt="test"),
                        "plan": plan,
                        "execution": execution,
                    },
                    make_runtime(),
                )
                self.assertEqual(route_after_reflection(update), expected)

    def test_clarification_routes_pending_to_final_and_resolved_to_resume_target(self) -> None:
        from app.agent.graph.models import ClarificationState

        self.assertEqual(
            route_after_clarification({"clarification": ClarificationState(status="pending")}),
            "final",
        )
        self.assertEqual(
            route_after_clarification(
                {"clarification": ClarificationState(status="resolved", resume_target="planner")}
            ),
            "planner",
        )

    def test_execute_plan_returns_structured_tool_report(self) -> None:
        request = AgentRequest(prompt="解析最近一周")
        plan = PlanResult(
            status="ready",
            objective="解析时间",
            steps=[
                PlanStep(
                    id="time-range",
                    title="解析时间",
                    kind="tool",
                    target="time_range_resolve",
                    capability="time_range.resolve",
                    input_payload={
                        "texts": ["最近一周"],
                        "now": "2026-06-28T14:00:00+08:00",
                        "named_kind": None,
                    },
                )
            ],
        )

        report = asyncio.run(execute_plan(request, plan, make_runtime().context, attempt=1))

        self.assertEqual(report.status, "succeeded")
        self.assertEqual(report.step_results[0].status, "succeeded")
        self.assertEqual(report.artifacts[0].data["tool"], "time_range_resolve")

    def test_execute_plan_resolves_sequential_step_references(self) -> None:
        request = AgentRequest(prompt="生成日志")
        plan = PlanResult(
            status="ready",
            objective="生成日志",
            mode="sequential",
            steps=[
                PlanStep(
                    id="resolve-range",
                    title="解析时间",
                    kind="tool",
                    target="time_range_resolve",
                    capability="time_range.resolve",
                    input_payload={
                        "texts": ["last week"],
                        "now": "2026-06-28T14:00:00+08:00",
                        "named_kind": "last_week",
                    },
                ),
                PlanStep(
                    id="render",
                    title="渲染日志",
                    kind="tool",
                    target="worklog_render",
                    capability="worklog.render",
                    input_payload={
                        "agent_name": "Worklog Agent",
                        "start_at": {"$from": "resolve-range.output.start_at"},
                        "end_at": {"$from": "resolve-range.output.end_at"},
                        "commits": [],
                        "non_code_notes": [],
                        "report_kind": "period",
                    },
                ),
            ],
        )

        report = asyncio.run(execute_plan(request, plan, make_runtime().context, attempt=1))

        self.assertEqual(report.status, "succeeded")
        self.assertEqual(report.artifacts[-1].data["tool"], "worklog_render")

    def test_execute_plan_supports_llm_business_tool(self) -> None:
        fake_tool = types.SimpleNamespace(
            input_schema=types.SimpleNamespace(model_validate=lambda payload: payload),
            execute=AsyncMock(return_value={"title": "Refined"}),
        )
        plan = PlanResult(
            status="ready",
            objective="润色",
            steps=[
                PlanStep(
                    id="refine",
                    title="润色",
                    kind="tool",
                    target="worklog_refine",
                    capability="worklog.refine",
                    input_payload={"title": "Draft"},
                )
            ],
        )

        with patch("app.agent.graph.runtime.build_business_tool", return_value=fake_tool):
            report = asyncio.run(
                execute_plan(AgentRequest(prompt="润色"), plan, make_runtime(llm_client=object()).context, attempt=1)
            )

        self.assertEqual(report.status, "succeeded")
        self.assertEqual(report.artifacts[0].data["output"]["title"], "Refined")

    def test_graph_prints_readable_chinese_node_trace(self) -> None:
        request = AgentRequest(prompt="你好")
        runtime = make_runtime().context

        with self.assertLogs("app.agent.graph", level="INFO") as captured:
            response = asyncio.run(PlatformGraph().ainvoke(request, runtime))

        output = "\n".join(captured.output)
        self.assertEqual(response.kind, "none")
        self.assertIn("智能体节点开始", output)
        self.assertIn("智能体节点完成", output)
        self.assertIn("智能体路由选择", output)
        self.assertIn("上下文加载（Context）", output)
        self.assertIn("意图解析（Intent）", output)
        self.assertIn("路由决策（Router）", output)
        self.assertIn("最终响应（Final）", output)


if __name__ == "__main__":
    unittest.main()
