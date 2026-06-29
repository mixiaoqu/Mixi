from __future__ import annotations

import httpx
from pydantic import BaseModel, Field

from app.tools.business.base import BusinessTool


class DingTalkSendInput(BaseModel):
    webhook_url: str = Field(min_length=1, max_length=2000)
    title: str = Field(min_length=1, max_length=200)
    markdown: str = Field(min_length=1, max_length=20000)


class DingTalkSendOutput(BaseModel):
    ok: bool
    status_code: int
    errcode: int | None = None
    errmsg: str | None = None


class DingTalkSendTool(BusinessTool[DingTalkSendInput, DingTalkSendOutput]):
    key = "dingtalk_send"
    name = "Send DingTalk Message"
    description = "Send a markdown message through a DingTalk webhook."
    input_schema = DingTalkSendInput

    async def execute(self, payload: DingTalkSendInput) -> DingTalkSendOutput:
        body = {
            "msgtype": "markdown",
            "markdown": {
                "title": payload.title,
                "text": payload.markdown,
            },
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(payload.webhook_url, json=body)
        data: dict[str, object] = {}
        if response.headers.get("content-type", "").startswith("application/json"):
            try:
                parsed = response.json()
            except ValueError:
                parsed = {}
            if isinstance(parsed, dict):
                data = parsed
        errcode = data.get("errcode") if isinstance(data, dict) else None
        errmsg = data.get("errmsg") if isinstance(data, dict) else None
        return DingTalkSendOutput(
            ok=response.is_success and (errcode in {None, 0}),
            status_code=response.status_code,
            errcode=errcode,
            errmsg=errmsg,
        )
