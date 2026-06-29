from __future__ import annotations

import json
import logging
from dataclasses import asdict, is_dataclass
from typing import Any

from pydantic import BaseModel


def configure_logging() -> None:
    root_logger = logging.getLogger()
    if root_logger.handlers:
        return

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def log_event(logger: logging.Logger, event: str, payload: Any) -> None:
    logger.info("%s %s", event, json.dumps(_to_jsonable(payload), ensure_ascii=False, default=str))


def log_pretty_event(logger: logging.Logger, event: str, payload: Any) -> None:
    logger.info("%s\n%s", event, json.dumps(_to_jsonable(payload), ensure_ascii=False, default=str, indent=2))


def _to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return {key: _to_jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_to_jsonable(item) for item in value]
    return value
