from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from .nodes import (
    clarification,
    context,
    executor,
    final_response,
    intent,
    planner,
    reflection,
    route_after_clarification,
    route_after_reflection,
    route_after_router,
    router,
)
from .models import AgentRequest, AgentResponse, ConversationPatch
from .state import AgentGraphInput, AgentGraphOutput, AgentGraphState, AgentRuntimeContext
from .trace import trace_node, trace_route


class PlatformGraph:
    def __init__(self, *, checkpointer: Any | None = None):
        self._checkpointer = checkpointer
        self._graph = self._build_graph()

    async def ainvoke(
        self,
        request: AgentRequest,
        runtime: AgentRuntimeContext,
    ) -> AgentResponse:
        config, checkpoint_thread_id, should_resume = await self._build_config(request)
        payload: dict[str, AgentRequest] | Command
        if should_resume:
            payload = Command(resume=request.prompt, update={"request": request})
        else:
            payload = {"request": request}

        result = await self._graph.ainvoke(
            payload,
            context=runtime,
            config=config,
        )
        if interrupt_response := _response_from_interrupt(result, request, checkpoint_thread_id):
            return interrupt_response
        return result.get("response", AgentResponse(kind="none", request_id=request.request_id))

    async def _build_config(self, request: AgentRequest) -> tuple[dict[str, dict[str, str]], str, bool]:
        configured_thread_id = request.conversation.checkpoint_thread_id
        checkpoint_thread_id = configured_thread_id or _new_checkpoint_thread_id(request)
        config = _thread_config(checkpoint_thread_id)

        if self._checkpointer is None or not configured_thread_id:
            return config, checkpoint_thread_id, False

        snapshot = await self._graph.aget_state(config)
        if snapshot.interrupts:
            return config, checkpoint_thread_id, True

        checkpoint_thread_id = _new_checkpoint_thread_id(request)
        return _thread_config(checkpoint_thread_id), checkpoint_thread_id, False

    def _build_graph(self):
        graph = StateGraph(
            AgentGraphState,
            context_schema=AgentRuntimeContext,
            input_schema=AgentGraphInput,
            output_schema=AgentGraphOutput,
        )
        graph.add_node("context", trace_node("context", context))
        graph.add_node("intent", trace_node("intent", intent))
        graph.add_node("router", trace_node("router", router))
        graph.add_node("clarification", trace_node("clarification", clarification))
        graph.add_node("planner", trace_node("planner", planner))
        graph.add_node("executor", trace_node("executor", executor))
        graph.add_node("reflection", trace_node("reflection", reflection))
        graph.add_node("final", trace_node("final", final_response))

        graph.add_edge(START, "context")
        graph.add_edge("context", "intent")
        graph.add_edge("intent", "router")
        graph.add_conditional_edges(
            "router",
            trace_route("router", route_after_router),
            {
                "clarification": "clarification",
                "planner": "planner",
                "executor": "executor",
                "final": "final",
            },
        )
        graph.add_conditional_edges(
            "clarification",
            trace_route("clarification", route_after_clarification),
            {
                "intent": "intent",
                "planner": "planner",
                "final": "final",
            },
        )
        graph.add_edge("planner", "executor")
        graph.add_edge("executor", "reflection")
        graph.add_conditional_edges(
            "reflection",
            trace_route("reflection", route_after_reflection),
            {
                "executor": "executor",
                "planner": "planner",
                "clarification": "clarification",
                "final": "final",
            },
        )
        graph.add_edge("final", END)
        return graph.compile(checkpointer=self._checkpointer)


def _new_checkpoint_thread_id(request: AgentRequest) -> str:
    return f"{request.conversation.conversation_id}:{request.request_id}"


def _thread_config(checkpoint_thread_id: str) -> dict[str, dict[str, str]]:
    return {
        "configurable": {
            "thread_id": checkpoint_thread_id,
        }
    }


def _response_from_interrupt(
    result: dict[str, Any],
    request: AgentRequest,
    checkpoint_thread_id: str,
) -> AgentResponse | None:
    interrupts = result.get("__interrupt__")
    if not interrupts:
        return None

    value = interrupts[0].value if interrupts else {}
    if not isinstance(value, dict):
        return AgentResponse(
            kind="clarification",
            message="请补充任务所需的信息。",
            conversation_patch=ConversationPatch(checkpoint_thread_id=checkpoint_thread_id),
            request_id=request.request_id,
        )

    raw_patch = value.get("conversation_patch")
    patch = ConversationPatch.model_validate(raw_patch if isinstance(raw_patch, dict) else {})
    patch = patch.model_copy(update={"checkpoint_thread_id": checkpoint_thread_id})
    message = value.get("message")
    return AgentResponse(
        kind="clarification",
        message=message if isinstance(message, str) else "请补充任务所需的信息。",
        conversation_patch=patch,
        request_id=request.request_id,
    )
