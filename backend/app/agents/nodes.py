from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import TypedDict

from app.db.models import RunStatus
from app.db.repositories.workflow import WorkflowRunStepRepository
from app.schemas.worklog import WorklogGenerateRequest
from app.tools.base import ToolContext
from app.tools.git_repository import GitListCommitsInput, GitListCommitsOutput, GitListCommitsTool


class WorklogGraphState(TypedDict, total=False):
    agent_name: str
    user_prompt: str | None
    request: WorklogGenerateRequest
    tool_context: ToolContext
    git_input: GitListCommitsInput
    git_result: GitListCommitsOutput
    non_code_notes: list[str]
    title: str
    summary: str
    markdown: str


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
                "non_code_notes": normalize_non_code_notes(state["request"].non_code_notes),
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
            )
            steps.mark_succeeded(
                step,
                output_payload={
                    "title": title,
                    "summary": summary,
                    "status": RunStatus.succeeded.value,
                },
            )
            return {
                "title": title,
                "summary": summary,
                "markdown": markdown,
            }
        except Exception as exc:
            steps.mark_failed(step, error_message=str(exc))
            raise

    return compose_worklog


def normalize_non_code_notes(notes: list[str]) -> list[str]:
    normalized: list[str] = []
    for note in notes:
        stripped = note.strip()
        if stripped:
            normalized.append(stripped)
    return normalized


def compose_worklog_markdown(
    *,
    agent_name: str,
    request: WorklogGenerateRequest,
    git_result: GitListCommitsOutput,
    non_code_notes: list[str],
) -> tuple[str, str, str]:
    start_local = request.start_at.astimezone()
    end_local = request.end_at.astimezone()
    day_label = start_local.strftime("%Y-%m-%d")
    time_range = f"{start_local.strftime('%H:%M')} - {end_local.strftime('%H:%M')}"
    commit_count = len(git_result.commits)
    note_count = len(non_code_notes)

    summary_parts: list[str] = []
    if commit_count > 0:
        summary_parts.append(f"整理了 {commit_count} 条代码提交")
    if note_count > 0:
        summary_parts.append(f"补充了 {note_count} 项非代码事项")
    if not summary_parts:
        summary_parts.append("本时段未检测到新的代码提交，已保留人工补充入口")
    summary = "，".join(summary_parts) + "。"
    title = f"{day_label} 工作日志"

    lines = [
        f"# {title}",
        "",
        f"> 由 {agent_name} 生成，统计区间：{day_label} {time_range}",
    ]

    if request.user_prompt:
        lines.extend(["", "## 工作目标", request.user_prompt.strip()])

    lines.extend(["", "## 代码工作"])
    if git_result.commits:
        for commit in git_result.commits:
            commit_time = commit.authored_at.astimezone().strftime("%H:%M")
            lines.append(f"- `{commit.sha[:7]}` {commit.subject}（{commit.author_name}，{commit_time}）")
    else:
        lines.append("- 本时段未检测到新的 Git 提交。")

    lines.extend(["", "## 非代码工作"])
    if non_code_notes:
        for note in non_code_notes:
            lines.append(f"- {note}")
    else:
        lines.append("- 暂无补充的非代码事项。")

    lines.extend(
        [
            "",
            "## 工作小结",
            f"- 仓库：{git_result.repository_name}",
            f"- 分支：{git_result.branch}",
            f"- 代码提交数：{commit_count}",
            f"- 非代码事项数：{note_count}",
            f"- 总结：{summary}",
        ]
    )

    return title, summary, "\n".join(lines)
