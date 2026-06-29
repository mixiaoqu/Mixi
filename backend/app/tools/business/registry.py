from __future__ import annotations

from collections.abc import Callable
from typing import Any

from openai import AsyncOpenAI

from app.tools.business.base import BusinessTool
from app.tools.business.dingtalk_send import DingTalkSendTool
from app.tools.business.time_range_resolve import TimeRangeResolveTool
from app.tools.business.worklog_refine import WorklogRefineTool
from app.tools.business.worklog_render import WorklogRenderTool


BusinessToolFactory = Callable[[AsyncOpenAI | None], BusinessTool[Any, Any]]

def _build_worklog_refine_tool(llm_client: AsyncOpenAI | None) -> BusinessTool[Any, Any]:
    if llm_client is None:
        raise ValueError("worklog_refine requires an llm_client")
    return WorklogRefineTool(llm_client)


BUSINESS_TOOL_REGISTRY: dict[str, BusinessToolFactory] = {
    TimeRangeResolveTool.key: lambda llm_client: TimeRangeResolveTool(),
    WorklogRenderTool.key: lambda llm_client: WorklogRenderTool(),
    DingTalkSendTool.key: lambda llm_client: DingTalkSendTool(),
    WorklogRefineTool.key: _build_worklog_refine_tool,
}


def build_business_tool(tool_id: str, llm_client: AsyncOpenAI | None) -> BusinessTool[Any, Any]:
    factory = BUSINESS_TOOL_REGISTRY.get(tool_id)
    if factory is None:
        raise ValueError(f"Unknown business tool: {tool_id}")
    return factory(llm_client)
