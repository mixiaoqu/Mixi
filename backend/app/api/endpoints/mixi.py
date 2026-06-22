from __future__ import annotations

import json
from collections.abc import AsyncIterator
from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from app.agents.graph import WorklogAgentRunner
from app.api.auth import CurrentUser
from app.api.deps import RepositoryDep
from app.core.llm import get_openai_client
from app.db.models import AgentStatus
from app.schemas.mixi import MixiChatRequest
from app.schemas.worklog import WorklogGenerateRequest, WorklogGenerateResponse
from app.services.mixi import MixiChatService, is_worklog_request
from app.services.worklog_intake import WorklogIntakeExtractor


router = APIRouter(tags=["mixi"])


def sse_event(event: str, data: dict[str, object]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/mixi/stream")
async def stream_mixi_chat(
    payload: MixiChatRequest,
    current_user: CurrentUser,
    repositories: RepositoryDep,
) -> StreamingResponse:
    if not payload.prompt.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Prompt cannot be empty")

    if is_worklog_request(payload.prompt):
        history = [item.content for item in payload.history if item.role == "user"]
        data_sources = repositories.git_data_sources.list_by_user(current_user.id)

        try:
            extractor = WorklogIntakeExtractor(get_openai_client())
        except RuntimeError:
            extractor = WorklogIntakeExtractor()

        intake = await extractor.extract(
            prompt=payload.prompt.strip(),
            history=history,
            data_sources=data_sources,
            now=datetime.now().astimezone(),
        )

        async def worklog_event_stream() -> AsyncIterator[str]:
            yield sse_event(
                "widget",
                {
                    "type": "worklog_form",
                    "title": intake.title,
                    "description": intake.description,
                    "draft": {
                        "data_source_id": intake.data_source_id,
                        "branch": intake.branch,
                        "start_at": intake.start_at.isoformat() if intake.start_at else None,
                        "end_at": intake.end_at.isoformat() if intake.end_at else None,
                        "user_prompt": intake.user_prompt,
                        "non_code_notes": intake.non_code_notes,
                        "missing_fields": intake.missing_fields,
                        "auto_run": intake.auto_run,
                    },
                },
            )
            yield sse_event("completed", {"message": ""})

        return StreamingResponse(worklog_event_stream(), media_type="text/event-stream")

    try:
        service = MixiChatService(get_openai_client())
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    async def event_stream() -> AsyncIterator[str]:
        full_text = ""
        try:
            async for delta in service.stream_reply(prompt=payload.prompt.strip(), user=current_user):
                full_text += delta
                yield sse_event("chunk", {"delta": delta})
            yield sse_event("completed", {"message": full_text})
        except Exception as exc:
            yield sse_event("error", {"detail": str(exc)})

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

    runner = WorklogAgentRunner(repositories)
    return await runner.run(agent=agent, user=current_user, request=payload)
