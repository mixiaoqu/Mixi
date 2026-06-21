from __future__ import annotations

import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from app.api.auth import CurrentUser
from app.core.llm import get_openai_client
from app.schemas.mixi import MixiChatRequest
from app.services.mixi import MixiChatService


router = APIRouter(tags=["mixi"])


def sse_event(event: str, data: dict[str, object]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/mixi/stream")
async def stream_mixi_chat(payload: MixiChatRequest, current_user: CurrentUser) -> StreamingResponse:
    if not payload.prompt.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Prompt cannot be empty")

    try:
        service = MixiChatService(get_openai_client())
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    async def event_stream() -> AsyncIterator[str]:
        full_text = ""
        try:
            async for delta in service.stream_reply(prompt=payload.prompt.strip(), user=current_user):
                full_text += delta
                yield sse_event("chunk", {"delta": delta})
            yield sse_event("completed", {"message": full_text})
        except Exception as exc:
            yield sse_event("error", {"detail": str(exc)})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
