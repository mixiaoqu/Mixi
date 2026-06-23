from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import PurePosixPath
from urllib.parse import urlparse

from openai import AsyncOpenAI

from app.core.config import settings
from app.db.models import GitDataSource
from app.schemas.mixi import MixiChatHistoryItem
from app.services.time_range import resolve_named_kind, resolve_time_range


@dataclass(frozen=True, slots=True)
class WorklogIntakeDraft:
    data_source_id: str | None
    branch: str | None
    start_at: datetime | None
    end_at: datetime | None
    user_prompt: str | None
    non_code_notes: list[str]
    missing_fields: list[str]
    auto_run: bool
    title: str
    description: str


class WorklogIntakeExtractor:
    def __init__(self, client: AsyncOpenAI | None = None):
        self.client = client

    async def extract(
        self,
        *,
        prompt: str,
        history: list[MixiChatHistoryItem],
        data_sources: list[GitDataSource],
        now: datetime,
    ) -> WorklogIntakeDraft:
        extracted = await self._extract_with_optional_llm(
            prompt=prompt,
            history=history,
            data_sources=data_sources,
            now=now,
        )
        data_source_id = self._resolve_data_source_id(
            extracted.get("data_source_id"),
            extracted.get("repository_hint"),
            data_sources,
            prompt=prompt,
            history=history,
        )
        start_at, end_at = self._resolve_time_range(prompt=prompt, history=history, extracted=extracted, now=now)
        non_code_notes = normalize_notes(extracted.get("non_code_notes"))
        branch = extracted.get("branch") or self._default_branch_for(data_source_id, data_sources)
        user_prompt = str(extracted.get("user_prompt") or prompt).strip() or None

        missing_fields: list[str] = []
        if data_source_id is None:
            missing_fields.append("data_source")
        if start_at is None or end_at is None:
            missing_fields.append("time_range")

        auto_run = not missing_fields
        title = "生成工作日志" if auto_run else "补全工作日志参数"
        description = self._build_description(
            data_source_id=data_source_id,
            data_sources=data_sources,
            start_at=start_at,
            end_at=end_at,
            non_code_notes=non_code_notes,
            missing_fields=missing_fields,
            auto_run=auto_run,
        )
        return WorklogIntakeDraft(
            data_source_id=data_source_id,
            branch=branch,
            start_at=start_at,
            end_at=end_at,
            user_prompt=user_prompt,
            non_code_notes=non_code_notes,
            missing_fields=missing_fields,
            auto_run=auto_run,
            title=title,
            description=description,
        )

    async def _extract_with_optional_llm(
        self,
        *,
        prompt: str,
        history: list[MixiChatHistoryItem],
        data_sources: list[GitDataSource],
        now: datetime,
    ) -> dict[str, object]:
        if self.client is None:
            return self._extract_with_rules(prompt=prompt, history=history)

        source_options = [
            {
                "id": str(source.id),
                "name": source.name,
                "default_branch": source.default_branch,
                "repository_url": source.repository_url,
            }
            for source in data_sources
        ]
        conversation = [{"role": item.role, "content": item.content} for item in history]
        conversation.append({"role": "user", "content": prompt})
        schema = {
            "data_source_id": "string | empty",
            "repository_hint": "string | empty",
            "branch": "string | empty",
            "time_range": "today | yesterday | this_week | last_week | this_month | last_month | custom | unknown",
            "start_at": "ISO8601 string | empty",
            "end_at": "ISO8601 string | empty",
            "user_prompt": "string | empty",
            "non_code_notes": ["string"],
        }

        try:
            completion = await self.client.chat.completions.create(
                model=settings.openai_model,
                temperature=0,
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a worklog intake extractor. "
                            "Return one JSON object only. "
                            "The result must be valid JSON and follow the schema keys exactly. "
                            "When multiple turns mention different dates, prefer the latest explicit user date. "
                            "Choose data_source_id only from the provided options."
                        ),
                    },
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "task": "Extract worklog parameters from the conversation and return JSON.",
                                "now": now.isoformat(),
                                "schema": schema,
                                "data_sources": source_options,
                                "conversation": conversation,
                            },
                            ensure_ascii=False,
                        ),
                    },
                ],
            )
            content = completion.choices[0].message.content or "{}"
            payload = json.loads(content)
            if isinstance(payload, dict):
                return payload
        except Exception:
            pass

        return self._extract_with_rules(prompt=prompt, history=history)

    def _extract_with_rules(self, *, prompt: str, history: list[MixiChatHistoryItem]) -> dict[str, object]:
        latest = prompt.strip()

        notes: list[str] = []
        for marker in ("另外", "还有", "并且", "以及", "补充"):
            if marker in latest:
                tail = latest.split(marker, 1)[1].strip("：:，,。 ")
                if tail:
                    notes = [segment.strip() for segment in split_notes(tail) if segment.strip()]
                    break

        return {
            "time_range": "unknown",
            "repository_hint": latest,
            "non_code_notes": notes,
            "user_prompt": latest,
        }

    def _resolve_data_source_id(
        self,
        extracted_id: object,
        repository_hint: object,
        data_sources: list[GitDataSource],
        *,
        prompt: str,
        history: list[MixiChatHistoryItem],
    ) -> str | None:
        if isinstance(extracted_id, str) and any(str(source.id) == extracted_id for source in data_sources):
            return extracted_id
        if len(data_sources) == 1:
            return str(data_sources[0].id)

        haystack = " ".join([*(item.content for item in history), prompt, str(repository_hint or "")]).lower()
        matches: list[str] = []
        for source in data_sources:
            candidates = {
                source.name.lower(),
                source.default_branch.lower(),
                source.repository_url.lower(),
                repository_basename(source.repository_url).lower(),
            }
            if any(candidate and candidate in haystack for candidate in candidates):
                matches.append(str(source.id))
        return matches[0] if len(matches) == 1 else None

    def _resolve_time_range(
        self,
        *,
        prompt: str,
        history: list[MixiChatHistoryItem],
        extracted: dict[str, object],
        now: datetime,
    ) -> tuple[datetime | None, datetime | None]:
        current = now.astimezone()
        user_texts = [prompt, *[item.content for item in reversed(history) if item.role == "user"]]
        resolved = resolve_time_range(user_texts, current)
        if resolved is not None:
            return resolved.start_at, resolved.end_at

        range_kind = str(extracted.get("time_range") or "unknown")
        named = resolve_named_kind(range_kind, current, prompt)
        if named is not None:
            return named.start_at, named.end_at
        if range_kind == "custom":
            start_at = normalize_datetime(parse_datetime(extracted.get("start_at")), current)
            end_at = normalize_datetime(parse_datetime(extracted.get("end_at")), current)
            if start_at and end_at:
                if end_at > current:
                    if end_at.date() == current.date():
                        end_at = current
                    else:
                        return None, None
                if start_at < end_at:
                    return start_at, end_at
        return None, None

    def _default_branch_for(self, data_source_id: str | None, data_sources: list[GitDataSource]) -> str | None:
        if data_source_id is None:
            return None
        for source in data_sources:
            if str(source.id) == data_source_id:
                return source.default_branch
        return None

    def _build_description(
        self,
        *,
        data_source_id: str | None,
        data_sources: list[GitDataSource],
        start_at: datetime | None,
        end_at: datetime | None,
        non_code_notes: list[str],
        missing_fields: list[str],
        auto_run: bool,
    ) -> str:
        source_name = next((source.name for source in data_sources if str(source.id) == data_source_id), None)
        parts: list[str] = []
        if source_name:
            parts.append(f"已识别仓库：{source_name}")
        if start_at and end_at:
            if start_at.date() == end_at.date():
                parts.append(f"已识别日期：{start_at.strftime('%Y-%m-%d')}")
            else:
                parts.append(f"已识别区间：{start_at.strftime('%Y-%m-%d')} 至 {end_at.strftime('%Y-%m-%d')}")
        if non_code_notes:
            parts.append(f"已提取 {len(non_code_notes)} 项非代码事项")
        if auto_run:
            parts.append("参数已齐全，确认后将调用工作日志 Agent。")
            return "；".join(parts)
        if "data_source" in missing_fields and "time_range" in missing_fields:
            parts.append("我还需要确认 Git 数据源和日志时间范围。")
        elif "data_source" in missing_fields:
            parts.append("我还需要确认要读取哪个 Git 数据源。")
        elif "time_range" in missing_fields:
            parts.append("我还需要确认日志的时间范围，比如今天、昨天或本周。")
        return "；".join(parts)


def normalize_notes(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def parse_datetime(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def normalize_datetime(value: datetime | None, now: datetime) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=now.tzinfo)
    return value.astimezone(now.tzinfo)


def split_notes(text: str) -> list[str]:
    normalized = text.replace("；", "，").replace(";", "，")
    return normalized.split("，")


def repository_basename(repository_url: str) -> str:
    path = urlparse(repository_url).path
    return PurePosixPath(path).name.removesuffix(".git")
