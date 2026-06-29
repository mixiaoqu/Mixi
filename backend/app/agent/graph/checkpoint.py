from __future__ import annotations

import asyncio
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer

from app.core.config import settings

from . import models


if sys.platform == "win32" and hasattr(asyncio, "WindowsSelectorEventLoopPolicy"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def psycopg_database_url() -> str:
    database_url = settings.resolved_database_url
    if database_url.startswith("postgresql+psycopg://"):
        return database_url.replace("postgresql+psycopg://", "postgresql://", 1)
    return database_url


def graph_state_serializer() -> JsonPlusSerializer:
    return JsonPlusSerializer(
        allowed_msgpack_modules=[
            models.AgentRequest,
            models.AgentResponse,
            models.Artifact,
            models.CapabilityAvailability,
            models.CapabilityCandidate,
            models.CapabilityRuleMatch,
            models.ClarificationQuestion,
            models.ClarificationState,
            models.ContextSnapshot,
            models.ConversationPatch,
            models.ExecutionError,
            models.ExecutionReport,
            models.IntentResult,
            models.PlanResult,
            models.PlanStep,
            models.PolicyAssessment,
            models.ReflectionResult,
            models.RetryPolicy,
            models.RouteDecision,
            models.SemanticIntent,
            models.StepResult,
        ]
    )


@asynccontextmanager
async def postgres_checkpointer() -> AsyncIterator[Any]:
    try:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "PostgreSQL LangGraph checkpointing requires the "
            "langgraph-checkpoint-postgres package. Install project dependencies before startup."
        ) from exc

    async with AsyncPostgresSaver.from_conn_string(
        psycopg_database_url(),
        serde=graph_state_serializer(),
    ) as checkpointer:
        await checkpointer.setup()
        yield checkpointer
