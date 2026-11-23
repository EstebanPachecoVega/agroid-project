"""Logs estructurados en JSONL.

Cada línea es un evento independiente. Los campos mínimos permiten reconstruir
el turno, su traza de LangSmith, el consumo y las decisiones de seguridad.
"""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..config import get_settings

_lock = threading.Lock()
_logger: "JsonlLogger | None" = None
_path_override: Path | None = None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def truncate(value: Any, limit: int = 2000) -> str:
    text = "" if value is None else str(value)
    if len(text) <= limit:
        return text
    return text[:limit] + f"...[truncado {len(text) - limit} chars]"


class JsonlLogger:
    def __init__(
        self,
        path: str | Path | None = None,
        service: str = "agroid-huevos",
        environment: str = "local",
    ) -> None:
        self.path = Path(path) if path else _default_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.service = service
        self.environment = environment
        self._lock = threading.Lock()

    def log(self, event: str, level: str = "INFO", **fields: Any) -> dict[str, Any]:
        record: dict[str, Any] = {
            "timestamp": utc_now(),
            "level": level.upper(),
            "event": event,
            "service": self.service,
            "environment": self.environment,
        }
        for key, value in fields.items():
            if key in record:
                record[f"data_{key}"] = value
            else:
                record[key] = value
        line = json.dumps(record, ensure_ascii=False, default=str)
        with self._lock:
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")
        return record


def _default_path() -> Path:
    if _path_override is not None:
        return _path_override
    settings = get_settings()
    return settings.logs_dir / f"agroid-{datetime.now(timezone.utc).date().isoformat()}.jsonl"


def set_log_path(path: str | Path) -> Path:
    global _logger, _path_override
    _path_override = Path(path).expanduser().resolve()
    _path_override.parent.mkdir(parents=True, exist_ok=True)
    _logger = JsonlLogger(path=_path_override)
    return _path_override


def reset_log_path() -> None:
    global _logger, _path_override
    _path_override = None
    _logger = None


def get_logger() -> JsonlLogger:
    global _logger
    if _logger is None:
        _logger = JsonlLogger()
    return _logger


def log_event(event: str, level: str = "INFO", **fields: Any) -> dict[str, Any]:
    return get_logger().log(event, level=level, **fields)
