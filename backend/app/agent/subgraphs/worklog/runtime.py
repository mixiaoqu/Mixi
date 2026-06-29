from __future__ import annotations

from app.db.models import AgentStatus
from app.schemas.worklog import WorklogGenerateRequest, WorklogGenerateResponse

from ..base import RunEventSink, SubgraphContext
from .graph import WorklogGraph


class WorklogSubgraph:
    id = "worklog"

    async def run(
        self,
        *,
        context: SubgraphContext,
        request: WorklogGenerateRequest,
        event_sink: RunEventSink | None = None,
    ) -> WorklogGenerateResponse:
        agent = self.ensure_agent(context)
        runner = WorklogGraph(context.repositories)
        return await runner.run(
            agent=agent,
            user=context.current_user,
            request=request,
            event_sink=event_sink,
        )

    @staticmethod
    def ensure_agent(context: SubgraphContext):
        current_user = context.current_user
        repositories = context.repositories
        workspaces = repositories.workspaces.list_for_user(current_user.id, limit=1)
        if workspaces:
            workspace = workspaces[0]
        else:
            workspace = repositories.workspaces.create_workspace(
                owner_user_id=current_user.id,
                slug=f"personal-{current_user.id.hex[:12]}",
                name=f"{current_user.display_name} 鐨勫伐浣滃尯",
                description="涓汉鏅鸿兘浣撳伐浣滃尯",
            )

        agent = repositories.agents.get_by_slug(workspace.id, "worklog-agent")
        if agent is None:
            agent = repositories.agents.create_agent(
                workspace_id=workspace.id,
                slug="worklog-agent",
                name="宸ヤ綔鏃ュ織 Agent",
                description="姹囨€?Git 鎻愪氦鍜岄潪浠ｇ爜浜嬮」锛岀敓鎴愬伐浣滄棩蹇楄崏绋裤€?",
                config={"agent_type": "system", "workflow": "worklog"},
            )
            repositories.agents.update(agent, status=AgentStatus.active)
        return agent
