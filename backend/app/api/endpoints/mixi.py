from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from langgraph.checkpoint.memory import InMemorySaver

from app.api.auth import CurrentUser
from app.api.deps import RepositoryDep
from app.agent.graph.checkpoint import graph_state_serializer
from app.core.llm import get_openai_client
from app.agent.graph import PlatformGraph
from app.agent.graph.models import AgentRequest
from app.agent.graph.state import AgentRuntimeContext
from app.agent.subgraphs.base import SubgraphContext
from app.agent.subgraphs.worklog import WorklogSubgraph
from app.schemas.mixi import MixiChatRequest, MixiConversationState
from app.schemas.worklog import WorklogGenerateRequest, WorklogGenerateResponse
from app.services.mixi import MixiChatService


router = APIRouter(tags=["mixi"])
_fallback_platform_graph = PlatformGraph(checkpointer=InMemorySaver(serde=graph_state_serializer()))


def sse_event(event: str, data: dict[str, object]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _cleared_state(state: MixiConversationState) -> MixiConversationState:
    return state.model_copy(
        update={
            "active_intent": None,
            "awaiting_confirmation": False,
            "missing_fields": [],
            "checkpoint_thread_id": None,
        }
    )


def _get_platform_graph(request: Request | None) -> PlatformGraph:
    if request is not None:
        graph = getattr(request.app.state, "platform_graph", None)
        if isinstance(graph, PlatformGraph):
            return graph
    return _fallback_platform_graph


@router.post("/mixi/stream")
async def stream_mixi_chat(
    payload: MixiChatRequest,
    current_user: CurrentUser,
    repositories: RepositoryDep,
    request: Request = None,
) -> StreamingResponse:
    prompt = payload.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Prompt cannot be empty")

    try:
        client = get_openai_client()
    except RuntimeError:
        client = None

    agent_response = await _get_platform_graph(request).ainvoke(
        AgentRequest(
            prompt=prompt,
            history=list(payload.history),
            conversation=payload.state,
        ),
        AgentRuntimeContext(
            current_user=current_user,
            repositories=repositories,
            llm_client=client,
        ),
    )
    if agent_response.kind != "none":
        response_state = payload.state.model_copy(update=agent_response.conversation_patch.model_dump())

        async def platform_event_stream() -> AsyncIterator[str]:
            yield sse_event("conversation.state", response_state.model_dump(mode="json"))
            if agent_response.artifacts:
                yield sse_event("artifact.created", {"artifact": agent_response.artifacts[0].data})
                return
            if agent_response.message is not None:
                yield sse_event("message.completed", {"message": agent_response.message})
                return
            if agent_response.task is not None:
                yield sse_event("task.proposed", agent_response.task)
                return

        return StreamingResponse(platform_event_stream(), media_type="text/event-stream")

    if client is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="OPENAI_API_KEY is not configured")
    service = MixiChatService(client)

    async def event_stream() -> AsyncIterator[str]:
        full_text = ""
        try:
            yield sse_event("conversation.state", _cleared_state(payload.state).model_dump(mode="json"))
            async for delta in service.stream_reply(prompt=prompt, user=current_user):
                full_text += delta
                yield sse_event("message.delta", {"delta": delta})
            yield sse_event("message.completed", {"message": full_text})
        except Exception as exc:
            yield sse_event("stream.error", {"detail": str(exc)})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/mixi/worklog/stream")
async def stream_worklog_from_mixi(
    payload: WorklogGenerateRequest,
    current_user: CurrentUser,
    repositories: RepositoryDep,
) -> StreamingResponse:
    domain = WorklogSubgraph()
    context = SubgraphContext(current_user=current_user, repositories=repositories)

    async def event_stream() -> AsyncIterator[str]:
        queue: asyncio.Queue[tuple[str, dict[str, object]] | None] = asyncio.Queue()

        async def emit(event: str, data: dict[str, object]) -> None:
            await queue.put((event, data))

        async def execute() -> None:
            try:
                await domain.run(context=context, request=payload, event_sink=emit)
            except Exception as exc:
                await emit("run.failed", {"detail": str(exc)})
            finally:
                await queue.put(None)

        asyncio.create_task(execute())

        while True:
            item = await queue.get()
            if item is None:
                break
            event, data = item
            yield sse_event(event, data)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/mixi/worklog", response_model=WorklogGenerateResponse, status_code=status.HTTP_201_CREATED)
async def run_worklog_from_mixi(
    payload: WorklogGenerateRequest,
    current_user: CurrentUser,
    repositories: RepositoryDep,
):
    domain = WorklogSubgraph()
    context = SubgraphContext(current_user=current_user, repositories=repositories)
    return await domain.run(context=context, request=payload)
