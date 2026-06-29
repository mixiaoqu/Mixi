from __future__ import annotations

from collections.abc import AsyncIterator

from openai import AsyncOpenAI

from app.core.config import settings
from app.db.models import User


class MixiChatService:
    def __init__(self, client: AsyncOpenAI):
        self.client = client

    async def stream_reply(self, *, prompt: str, user: User) -> AsyncIterator[str]:
        stream = await self.client.chat.completions.create(
            model=settings.openai_model,
            stream=True,
            temperature=0.5,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are Mixi, the user's calm, modern AI workspace assistant. "
                        "Reply in Chinese by default. Be concise, practical, and friendly. "
                        "When the user's request sounds like a work-log, knowledge-base, or workflow task, "
                        "briefly acknowledge it and explain the next best action inside the platform. "
                        "Do not invent data source results or tool outputs."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Current user display name: {user.display_name}\nUser request: {prompt}",
                },
            ],
        )

        async for chunk in stream:
            delta = chunk.choices[0].delta.content or ""
            if delta:
                yield delta
