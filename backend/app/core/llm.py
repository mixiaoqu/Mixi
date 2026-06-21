from __future__ import annotations

from functools import lru_cache

from openai import AsyncOpenAI

from app.core.config import settings


@lru_cache(maxsize=1)
def get_openai_client() -> AsyncOpenAI:
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")
    return AsyncOpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url or None,
    )
