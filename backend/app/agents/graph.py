from __future__ import annotations

import uuid
from types import SimpleNamespace

from langgraph.graph import END, START, StateGraph

from app.agents.nodes import WorklogGraphState, make_git_collection_node, make_worklog_composer_node
from app.db.models import Agent, RunStatus, User
from app.db.repositories import Repositories
from app.schemas.worklog import WorklogCommitRead, WorklogGenerateRequest, WorklogGenerateResponse
from app.tools.base import ToolContext, ToolError
from app.tools.git_repository import GitListCommitsInput, GitListCommitsTool


class WorklogAgentRunner:
    def __init__(
        self,
        repositories: Repositories,
        *,
        git_tool: GitListCommitsTool | None = None,
    ):
        self.repositories = repositories
        self.git_tool = git_tool or GitListCommitsTool(repositories.git_data_sources)

    async def run(
        self,
        *,
        agent: Agent,
        user: User,
        request: WorklogGenerateRequest,
    ) -> WorklogGenerateResponse:
        run = self.repositories.workflow_runs.create_run(
            workspace_id=agent.workspace_id,
            agent_id=agent.id,
            initiated_by_user_id=user.id,
            template_key="agent.worklog.generate",
            trigger_source="manual",
            input_payload=request.model_dump(mode="json"),
        )
        self.repositories.workflow_runs.mark_running(run)

        git_step = self.repositories.workflow_run_steps.create_step(
            workflow_run_id=run.id,
            sequence_no=1,
            step_key="collect_git_activity",
            step_name="读取 Git 提交",
        )
        compose_step = self.repositories.workflow_run_steps.create_step(
            workflow_run_id=run.id,
            sequence_no=2,
            step_key="compose_worklog",
            step_name="生成日志草稿",
        )

        graph = self._build_graph(git_step=git_step, compose_step=compose_step)
        initial_state: WorklogGraphState = {
            "agent_name": agent.name,
            "user_prompt": request.user_prompt,
            "request": request,
            "tool_context": ToolContext(
                user_id=user.id,
                run_id=run.id,
                allowed_data_source_ids=frozenset({request.data_source_id}),
            ),
            "git_input": GitListCommitsInput(
                data_source_id=request.data_source_id,
                start_at=request.start_at,
                end_at=request.end_at,
                branch=request.branch,
                limit=request.commit_limit,
            ),
        }

        try:
            result = await graph.ainvoke(initial_state)
        except ToolError as exc:
            self.repositories.workflow_runs.mark_failed(run, error_message=str(exc))
            raise
        except Exception as exc:
            self.repositories.workflow_runs.mark_failed(run, error_message=str(exc))
            raise

        self.repositories.workflow_runs.mark_succeeded(
            run,
            output_payload={
                "title": result["title"],
                "summary": result["summary"],
                "markdown": result["markdown"],
                "branch": result["git_result"].branch,
                "commit_count": len(result["git_result"].commits),
            },
        )

        return WorklogGenerateResponse(
            workflow_run_id=run.id,
            agent_id=agent.id,
            workspace_id=agent.workspace_id,
            status=RunStatus.succeeded,
            title=result["title"],
            summary=result["summary"],
            markdown=result["markdown"],
            branch=result["git_result"].branch,
            commit_count=len(result["git_result"].commits),
            commits=[
                WorklogCommitRead(
                    sha=commit.sha,
                    author_name=commit.author_name,
                    authored_at=commit.authored_at,
                    subject=commit.subject,
                )
                for commit in result["git_result"].commits
            ],
            non_code_notes=result["non_code_notes"],
        )

    def _build_graph(self, *, git_step: object, compose_step: object):
        graph = StateGraph(WorklogGraphState)
        graph.add_node(
            "collect_git_activity",
            make_git_collection_node(
                git_tool=self.git_tool,
                steps=self.repositories.workflow_run_steps,
                step_id_factory=lambda: git_step,
            ),
        )
        graph.add_node(
            "compose_worklog",
            make_worklog_composer_node(
                steps=self.repositories.workflow_run_steps,
                step_id_factory=lambda: compose_step,
            ),
        )
        graph.add_edge(START, "collect_git_activity")
        graph.add_edge("collect_git_activity", "compose_worklog")
        graph.add_edge("compose_worklog", END)
        return graph.compile()
