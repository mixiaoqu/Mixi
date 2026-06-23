from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from app.agents.graph import WorklogAgentRunner
from app.api.auth import CurrentUser
from app.api.deps import RepositoryDep
from app.core.llm import get_openai_client
from app.db.models import AgentStatus
from app.schemas.mixi import MixiChatRequest, MixiConversationState
from app.schemas.worklog import WorklogGenerateRequest, WorklogGenerateResponse
from app.services.mixi import MixiChatService, MixiRouter
from app.services.worklog_intake import WorklogIntakeExtractor


router = APIRouter(tags=["mixi"])


def sse_event(event: str, data: dict[str, object]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _cleared_state(state: MixiConversationState) -> MixiConversationState:
    return state.model_copy(
        update={
            "active_intent": None,
            "awaiting_confirmation": False,
            "missing_fields": [],
        }
    )


def _ensure_worklog_agent(current_user: CurrentUser, repositories: RepositoryDep):
    workspaces = repositories.workspaces.list_for_user(current_user.id, limit=1)
    if workspaces:
        workspace = workspaces[0]
    else:
        workspace = repositories.workspaces.create_workspace(
            owner_user_id=current_user.id,
            slug=f"personal-{current_user.id.hex[:12]}",
            name=f"{current_user.display_name} 的工作区",
            description="个人智能体工作区",
        )

    agent = repositories.agents.get_by_slug(workspace.id, "worklog-agent")
    if agent is None:
        agent = repositories.agents.create_agent(
            workspace_id=workspace.id,
            slug="worklog-agent",
            name="工作日志 Agent",
            description="汇总 Git 提交和非代码事项，生成工作日志草稿。",
            config={"agent_type": "system", "workflow": "worklog"},
        )
        repositories.agents.update(agent, status=AgentStatus.active)
    return agent


def _build_worklog_follow_up_message(*, intake, has_data_sources: bool) -> str:
    if not has_data_sources:
        return "你还没有连接 Git 数据源。先去数据源页面连接一个仓库，然后再让我生成工作日志。"

    parts: list[str] = []
    if intake.data_source_id:
        parts.append("我已经识别到仓库")
    if intake.start_at and intake.end_at:
        if intake.start_at.date() == intake.end_at.date():
            parts.append(f"时间是 {intake.start_at.strftime('%Y-%m-%d')}")
        else:
            parts.append(
                f"时间范围是 {intake.start_at.strftime('%Y-%m-%d')} 到 {intake.end_at.strftime('%Y-%m-%d')}"
            )
    if intake.non_code_notes:
        parts.append(f"还提取到了 {len(intake.non_code_notes)} 项非代码事项")

    missing_prompts: list[str] = []
    if "data_source" in intake.missing_fields:
        missing_prompts.append("请告诉我要使用哪个 Git 数据源")
    if "time_range" in intake.missing_fields:
        missing_prompts.append("请告诉我要生成今天、昨天还是本周的日志")

    prefix = "，".join(parts)
    question = "；".join(missing_prompts) if missing_prompts else "请继续补充信息。"
    return f"{prefix}。{question}" if prefix else question


def _build_worklog_proposal_payload(*, intake) -> dict[str, object]:
    return {
        "type": "worklog",
        "capability": "worklog.generate",
        "title": "确认工作日志参数",
        "description": intake.description,
        "draft": {
            "data_source_id": intake.data_source_id,
            "branch": intake.branch,
            "start_at": intake.start_at.isoformat() if intake.start_at else None,
            "end_at": intake.end_at.isoformat() if intake.end_at else None,
            "user_prompt": intake.user_prompt,
            "non_code_notes": intake.non_code_notes,
            "missing_fields": intake.missing_fields,
            "auto_run": False,
        },
    }


@router.post("/mixi/stream")
async def stream_mixi_chat(
    payload: MixiChatRequest,
    current_user: CurrentUser,
    repositories: RepositoryDep,
) -> StreamingResponse:
    if not payload.prompt.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Prompt cannot be empty")

    try:
        client = get_openai_client()
    except RuntimeError:
        client = None

    decision = await MixiRouter(client).route(prompt=payload.prompt, state=payload.state)

    if decision.action == "cancel":
        async def cancelled_event_stream() -> AsyncIterator[str]:
            yield sse_event("conversation.state", _cleared_state(payload.state).model_dump(mode="json"))
            yield sse_event("message.completed", {"message": "好的，已取消当前任务。你可以直接告诉我接下来想做什么。"})

        return StreamingResponse(cancelled_event_stream(), media_type="text/event-stream")

    if decision.action == "confirm":
        async def confirmation_event_stream() -> AsyncIterator[str]:
            next_state = payload.state.model_copy(
                update={"active_intent": "worklog", "awaiting_confirmation": True, "missing_fields": []}
            )
            yield sse_event("conversation.state", next_state.model_dump(mode="json"))
            yield sse_event("message.completed", {"message": "你是想根据工作内容或 Git 提交生成一份工作日志吗？"})

        return StreamingResponse(confirmation_event_stream(), media_type="text/event-stream")

    if decision.intent == "worklog":
        history = list(payload.history)
        data_sources = repositories.git_data_sources.list_by_user(current_user.id)
        extractor = WorklogIntakeExtractor(client)

        intake = await extractor.extract(
            prompt=payload.prompt.strip(),
            history=history,
            data_sources=data_sources,
            now=datetime.now(ZoneInfo(payload.state.timezone)),
        )

        async def worklog_event_stream() -> AsyncIterator[str]:
            if not intake.auto_run:
                next_state = payload.state.model_copy(
                    update={
                        "active_intent": "worklog",
                        "awaiting_confirmation": False,
                        "missing_fields": intake.missing_fields,
                    }
                )
                yield sse_event("conversation.state", next_state.model_dump(mode="json"))
                yield sse_event(
                    "message.completed",
                    {"message": _build_worklog_follow_up_message(intake=intake, has_data_sources=bool(data_sources))},
                )
                return

            yield sse_event("conversation.state", _cleared_state(payload.state).model_dump(mode="json"))
            yield sse_event("task.proposed", _build_worklog_proposal_payload(intake=intake))

        return StreamingResponse(worklog_event_stream(), media_type="text/event-stream")

    if client is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="OPENAI_API_KEY is not configured")
    service = MixiChatService(client)

    async def event_stream() -> AsyncIterator[str]:
        full_text = ""
        try:
            yield sse_event("conversation.state", _cleared_state(payload.state).model_dump(mode="json"))
            async for delta in service.stream_reply(prompt=payload.prompt.strip(), user=current_user):
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
    agent = _ensure_worklog_agent(current_user, repositories)

    async def event_stream() -> AsyncIterator[str]:
        queue: asyncio.Queue[tuple[str, dict[str, object]] | None] = asyncio.Queue()

        async def emit(event: str, data: dict[str, object]) -> None:
            await queue.put((event, data))

        async def execute() -> None:
            try:
                runner = WorklogAgentRunner(repositories)
                await runner.run(agent=agent, user=current_user, request=payload, event_sink=emit)
            except Exception:
                pass
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
    agent = _ensure_worklog_agent(current_user, repositories)
    runner = WorklogAgentRunner(repositories)
    return await runner.run(agent=agent, user=current_user, request=payload)
