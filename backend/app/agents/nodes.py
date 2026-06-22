from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Literal, TypedDict

from app.db.models import RunStatus
from app.db.repositories.workflow import WorkflowRunStepRepository
from app.schemas.worklog import WorklogGenerateRequest
from app.services.worklog_refiner import WorklogRefinementInput, WorklogRefinementResult, WorklogRefiner
from app.tools.base import ToolContext
from app.tools.git_repository import GitListCommitsInput, GitListCommitsOutput, GitListCommitsTool


class WorklogGraphState(TypedDict, total=False):
    agent_name: str
    request: WorklogGenerateRequest
    tool_context: ToolContext
    git_input: GitListCommitsInput
    git_result: GitListCommitsOutput
    non_code_notes: list[str]
    report_kind: Literal["daily", "period"]
    should_refine: bool
    title: str
    summary: str
    markdown: str


def make_request_analysis_node(
    *,
    steps: WorkflowRunStepRepository,
    step_id_factory: Callable[[], object],
    llm_enabled: bool,
) -> Callable[[WorklogGraphState], Awaitable[WorklogGraphState]]:
    async def analyze_request(state: WorklogGraphState) -> WorklogGraphState:
        step = step_id_factory()
        steps.mark_running(step)
        request = state["request"]
        non_code_notes = normalize_non_code_notes(request.non_code_notes)
        report_kind: Literal["daily", "period"] = (
            "daily"
            if request.start_at.astimezone().date() == request.end_at.astimezone().date()
            else "period"
        )
        should_refine = llm_enabled and bool(non_code_notes or request.user_prompt)

        steps.mark_succeeded(
            step,
            output_payload={
                "report_kind": report_kind,
                "non_code_note_count": len(non_code_notes),
                "should_refine": should_refine,
            },
        )
        return {
            "non_code_notes": non_code_notes,
            "report_kind": report_kind,
            "should_refine": should_refine,
        }

    return analyze_request


def make_git_collection_node(
    *,
    git_tool: GitListCommitsTool,
    steps: WorkflowRunStepRepository,
    step_id_factory: Callable[[], object],
) -> Callable[[WorklogGraphState], Awaitable[WorklogGraphState]]:
    async def collect_git_activity(state: WorklogGraphState) -> WorklogGraphState:
        step = step_id_factory()
        steps.mark_running(step)
        try:
            git_result = await git_tool.execute(state["git_input"], state["tool_context"])
            steps.mark_succeeded(
                step,
                output_payload={
                    "repository_name": git_result.repository_name,
                    "branch": git_result.branch,
                    "commit_count": len(git_result.commits),
                },
            )
            return {
                "git_result": git_result,
                "should_refine": state.get("should_refine", False) or bool(git_result.commits),
            }
        except Exception as exc:
            steps.mark_failed(step, error_message=str(exc))
            raise

    return collect_git_activity


def make_worklog_composer_node(
    *,
    steps: WorkflowRunStepRepository,
    step_id_factory: Callable[[], object],
) -> Callable[[WorklogGraphState], Awaitable[WorklogGraphState]]:
    async def compose_worklog(state: WorklogGraphState) -> WorklogGraphState:
        step = step_id_factory()
        steps.mark_running(step)
        try:
            title, summary, markdown = compose_worklog_markdown(
                agent_name=state["agent_name"],
                request=state["request"],
                git_result=state["git_result"],
                non_code_notes=state["non_code_notes"],
                report_kind=state["report_kind"],
            )
            steps.mark_succeeded(
                step,
                output_payload={
                    "title": title,
                    "summary": summary,
                    "status": RunStatus.succeeded.value,
                },
            )
            return {"title": title, "summary": summary, "markdown": markdown}
        except Exception as exc:
            steps.mark_failed(step, error_message=str(exc))
            raise

    return compose_worklog


def make_worklog_refinement_node(
    *,
    refiner: WorklogRefiner,
    steps: WorkflowRunStepRepository,
    step_id_factory: Callable[[], object],
) -> Callable[[WorklogGraphState], Awaitable[WorklogGraphState]]:
    async def refine_worklog(state: WorklogGraphState) -> WorklogGraphState:
        step = step_id_factory()
        steps.mark_running(step)
        try:
            refinement = await refiner.refine(
                WorklogRefinementInput(
                    agent_name=state["agent_name"],
                    title=state["title"],
                    summary=state["summary"],
                    markdown=state["markdown"],
                    user_prompt=state["request"].user_prompt,
                    repository_name=state["git_result"].repository_name,
                    branch=state["git_result"].branch,
                    commit_count=len(state["git_result"].commits),
                    non_code_notes=state["non_code_notes"],
                    commits=[
                        {
                            "sha": commit.sha,
                            "author_name": commit.author_name,
                            "authored_at": commit.authored_at.isoformat(),
                            "subject": commit.subject,
                            "changed_files": commit.changed_files,
                            "patch": commit.patch,
                        }
                        for commit in state["git_result"].commits
                    ],
                )
            )
            steps.mark_succeeded(
                step,
                output_payload={
                    "title": refinement.title,
                    "summary": refinement.summary,
                    "refined": True,
                },
            )
            return {
                "title": refinement.title,
                "summary": refinement.summary,
                "markdown": refinement.markdown,
            }
        except Exception as exc:
            steps.mark_failed(step, error_message=str(exc))
            return {}

    return refine_worklog


def route_after_compose(state: WorklogGraphState) -> str:
    return "refine_worklog" if state.get("should_refine") else "end"


def normalize_non_code_notes(notes: list[str]) -> list[str]:
    return [note.strip() for note in notes if note.strip()]


def compose_worklog_markdown(
    *,
    agent_name: str,
    request: WorklogGenerateRequest,
    git_result: GitListCommitsOutput,
    non_code_notes: list[str],
    report_kind: Literal["daily", "period"],
) -> tuple[str, str, str]:
    start_local = request.start_at.astimezone()
    end_local = request.end_at.astimezone()
    day_label = start_local.strftime("%Y-%m-%d")
    period_label = f"{start_local.strftime('%Y-%m-%d')} 至 {end_local.strftime('%Y-%m-%d')}"
    time_range = f"{start_local.strftime('%H:%M')} - {end_local.strftime('%H:%M')}"
    commit_count = len(git_result.commits)
    note_count = len(non_code_notes)

    summary_parts: list[str] = []
    if commit_count:
        summary_parts.append(f"整理了 {commit_count} 条代码提交")
    if note_count:
        summary_parts.append(f"补充了 {note_count} 项非代码事项")
    if not summary_parts:
        summary_parts.append("本次时间范围内未检测到新的代码提交，已保留人工补充入口")

    summary = "，".join(summary_parts) + "。"
    title = f"{day_label} 工作日志" if report_kind == "daily" else f"{period_label} 工作记录"
    lines = [
        f"# {title}",
        "",
        f"> 由 {agent_name} 生成，统计区间：{day_label if report_kind == 'daily' else period_label} {time_range}",
    ]

    lines.extend(["", "## 工作概览"])
    if commit_count:
        lines.append(f"- 基于 {commit_count} 条代码提交整理本次开发工作，启用 LLM 后会结合 diff 归纳主要方向、功能成果和价值。")
    else:
        lines.append("- 本时间范围内未检测到新的代码提交。")

    lines.extend(["", "## 完成功能"])
    if git_result.commits:
        for commit in git_result.commits:
            files = "、".join(commit.changed_files[:3])
            suffix = f"；涉及 {files}" if files else ""
            lines.append(f"- {commit.subject}{suffix}")
    else:
        lines.append("- 本时间范围内未检测到新的 Git 提交。")

    lines.extend(["", "## 技术实现"])
    if git_result.commits:
        lines.append("- 已收集提交 diff，启用 LLM 后会基于代码变化整理关键实现点。")
    else:
        lines.append("- 暂未记录新的代码实现变化。")

    lines.extend(["", "## 目标和价值"])
    lines.append("- 暂未记录明确目标，可结合功能上下文补充。")

    lines.extend(
        [
            "",
            "## 风险或阻塞",
            "- 暂未记录明确风险或阻塞。",
            "",
            "## 后续可扩展方向",
            "- 暂未记录后续可扩展方向，可在草稿中补充。",
        ]
    )

    if non_code_notes:
        lines.extend(["", "## 备注"])
        lines.extend(f"- {note}" for note in non_code_notes)

    return title, summary, "\n".join(lines)
