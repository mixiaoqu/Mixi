from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.agent.subgraphs.worklog.nodes import (
    RunEventSink,
    WorklogGraphState,
    make_git_collection_node,
    make_request_analysis_node,
    make_worklog_composer_node,
    make_worklog_refinement_node,
    route_after_compose,
)
from app.core.config import settings
from app.core.llm import get_openai_client
from app.db.models import Agent, RunStatus, User
from app.db.repositories import Repositories
from app.schemas.worklog import WorklogCommitRead, WorklogGenerateRequest, WorklogGenerateResponse
from app.services.worklog_refiner import OpenAIWorklogRefiner, WorklogRefiner
from app.tools.agent.base import ToolContext, ToolError
from app.tools.agent.git_inspect import GitListCommitsInput, GitListCommitsTool

_DEFAULT_REFINER = object()


class WorklogGraph:
    def __init__(
        self,
        repositories: Repositories,
        *,
        git_tool: GitListCommitsTool | None = None,
        llm_refiner: WorklogRefiner | None | object = _DEFAULT_REFINER,
    ):
        self.repositories = repositories
        self.git_tool = git_tool or GitListCommitsTool(repositories.git_data_sources)
        self.llm_refiner = self._build_default_refiner() if llm_refiner is _DEFAULT_REFINER else llm_refiner

    async def run(
        self,
        *,
        agent: Agent,
        user: User,
        request: WorklogGenerateRequest,
        event_sink: RunEventSink | None = None,
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
        if event_sink is not None:
            await event_sink(
                "run.started",
                {
                    "run_id": str(run.id),
                    "capability": "worklog.generate",
                    "status": RunStatus.running.value,
                },
            )

        analyze_step = self.repositories.workflow_run_steps.create_step(
            workflow_run_id=run.id,
            sequence_no=1,
            step_key="analyze_request",
            step_name="分析日志请求",
        )
        git_step = self.repositories.workflow_run_steps.create_step(
            workflow_run_id=run.id,
            sequence_no=2,
            step_key="collect_git_activity",
            step_name="读取 Git 提交",
        )
        compose_step = self.repositories.workflow_run_steps.create_step(
            workflow_run_id=run.id,
            sequence_no=3,
            step_key="compose_worklog",
            step_name="生成日志草稿",
        )
        refine_step = None
        if self.llm_refiner is not None:
            refine_step = self.repositories.workflow_run_steps.create_step(
                workflow_run_id=run.id,
                sequence_no=4,
                step_key="refine_worklog",
                step_name="润色日志内容",
            )

        graph = self._build_graph(
            analyze_step=analyze_step,
            git_step=git_step,
            compose_step=compose_step,
            refine_step=refine_step,
            event_sink=event_sink,
        )
        initial_state: WorklogGraphState = {
            "agent_name": agent.name,
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
            if event_sink is not None:
                await event_sink("run.failed", {"run_id": str(run.id), "detail": str(exc)})
            raise
        except Exception as exc:
            self.repositories.workflow_runs.mark_failed(run, error_message=str(exc))
            if event_sink is not None:
                await event_sink("run.failed", {"run_id": str(run.id), "detail": str(exc)})
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

        response = WorklogGenerateResponse(
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
        if event_sink is not None:
            await event_sink("artifact.created", {"artifact": response.model_dump(mode="json")})
        return response

    def _build_graph(
        self,
        *,
        analyze_step: object,
        git_step: object,
        compose_step: object,
        refine_step: object | None,
        event_sink: RunEventSink | None,
    ):
        graph = StateGraph(WorklogGraphState)
        graph.add_node(
            "analyze_request",
            make_request_analysis_node(
                steps=self.repositories.workflow_run_steps,
                step_id_factory=lambda: analyze_step,
                llm_enabled=self.llm_refiner is not None,
                event_sink=event_sink,
            ),
        )
        graph.add_node(
            "collect_git_activity",
            make_git_collection_node(
                git_tool=self.git_tool,
                steps=self.repositories.workflow_run_steps,
                step_id_factory=lambda: git_step,
                event_sink=event_sink,
            ),
        )
        graph.add_node(
            "compose_worklog",
            make_worklog_composer_node(
                steps=self.repositories.workflow_run_steps,
                step_id_factory=lambda: compose_step,
                event_sink=event_sink,
            ),
        )
        if self.llm_refiner is not None and refine_step is not None:
            graph.add_node(
                "refine_worklog",
                make_worklog_refinement_node(
                    refiner=self.llm_refiner,
                    steps=self.repositories.workflow_run_steps,
                    step_id_factory=lambda: refine_step,
                    event_sink=event_sink,
                ),
            )

        graph.add_edge(START, "analyze_request")
        graph.add_edge("analyze_request", "collect_git_activity")
        graph.add_edge("collect_git_activity", "compose_worklog")
        if self.llm_refiner is not None:
            graph.add_conditional_edges(
                "compose_worklog",
                route_after_compose,
                {
                    "refine_worklog": "refine_worklog",
                    "end": END,
                },
            )
            graph.add_edge("refine_worklog", END)
        else:
            graph.add_edge("compose_worklog", END)
        return graph.compile()

    def _build_default_refiner(self) -> WorklogRefiner | None:
        if not settings.openai_api_key:
            return None
        return OpenAIWorklogRefiner(get_openai_client())
