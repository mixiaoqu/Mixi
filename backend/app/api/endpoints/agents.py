from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response, status

from app.api.auth import CurrentUser
from app.api.deps import RepositoryDep
from app.api.permissions import require_workspace_access, require_workspace_editor
from app.db.models import AgentStatus
from app.schemas.agent import AgentCreate, AgentRead, AgentUpdate
from app.schemas.common import Page
from app.schemas.worklog import WorklogGenerateRequest, WorklogGenerateResponse
from app.agent.subgraphs.worklog import WorklogGraph


router = APIRouter(tags=["agents"])


@router.post("/workspaces/{workspace_id}/agents", response_model=AgentRead, status_code=status.HTTP_201_CREATED)
def create_agent(
    workspace_id: uuid.UUID,
    payload: AgentCreate,
    current_user: CurrentUser,
    repositories: RepositoryDep,
):
    require_workspace_editor(workspace_id, current_user, repositories)
    if repositories.agents.get_by_slug(workspace_id, payload.slug) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Agent slug already exists in this workspace")
    return repositories.agents.create_agent(workspace_id=workspace_id, **payload.model_dump())


@router.get("/workspaces/{workspace_id}/agents", response_model=Page[AgentRead])
def list_agents(
    workspace_id: uuid.UUID,
    repositories: RepositoryDep,
    current_user: CurrentUser,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    require_workspace_access(workspace_id, current_user, repositories)
    agents = repositories.agents.list_by_workspace(workspace_id, limit=limit, offset=offset)
    total = repositories.agents.count(workspace_id=workspace_id)
    return Page(items=agents, total=total, limit=limit, offset=offset)


@router.get("/agents/{agent_id}", response_model=AgentRead)
def get_agent(agent_id: uuid.UUID, current_user: CurrentUser, repositories: RepositoryDep):
    agent = repositories.agents.get(agent_id)
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    require_workspace_access(agent.workspace_id, current_user, repositories)
    return agent


@router.patch("/agents/{agent_id}", response_model=AgentRead)
def update_agent(
    agent_id: uuid.UUID,
    payload: AgentUpdate,
    current_user: CurrentUser,
    repositories: RepositoryDep,
):
    agent = repositories.agents.get(agent_id)
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    require_workspace_editor(agent.workspace_id, current_user, repositories)
    return repositories.agents.update(agent, **payload.model_dump(exclude_unset=True))


@router.delete("/agents/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_agent(agent_id: uuid.UUID, current_user: CurrentUser, repositories: RepositoryDep) -> Response:
    agent = repositories.agents.get(agent_id)
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    require_workspace_editor(agent.workspace_id, current_user, repositories)
    repositories.agents.delete(agent)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/agents/{agent_id}/runs/worklog", response_model=WorklogGenerateResponse, status_code=status.HTTP_201_CREATED)
async def run_worklog_agent(
    agent_id: uuid.UUID,
    payload: WorklogGenerateRequest,
    current_user: CurrentUser,
    repositories: RepositoryDep,
):
    agent = repositories.agents.get(agent_id)
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    require_workspace_access(agent.workspace_id, current_user, repositories)
    if agent.status in {AgentStatus.paused, AgentStatus.archived}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Agent is not available for execution")

    runner = WorklogGraph(repositories)
    return await runner.run(agent=agent, user=current_user, request=payload)
