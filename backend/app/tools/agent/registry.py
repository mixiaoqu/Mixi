from __future__ import annotations

from collections.abc import Callable

from app.db.repositories import Repositories
from app.tools.agent.base import AgentTool
from app.tools.agent.git_inspect import GitListCommitsTool


ToolFactory = Callable[[Repositories], AgentTool]


TOOL_REGISTRY: dict[str, ToolFactory] = {
    GitListCommitsTool.key: lambda repositories: GitListCommitsTool(repositories.git_data_sources),
}


def build_tools(tool_ids: list[str], repositories: Repositories) -> list[AgentTool]:
    unknown = sorted(set(tool_ids) - TOOL_REGISTRY.keys())
    if unknown:
        raise ValueError(f"Unknown tools: {', '.join(unknown)}")
    return [TOOL_REGISTRY[tool_id](repositories) for tool_id in tool_ids]
