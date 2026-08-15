"""Structured logging helpers separate from the canonical event trace."""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from typing import Any


class JsonFormatter(logging.Formatter):
    """Format log records as one JSON object per line."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in ("run_id", "session_id", "round_id", "node_id", "component_id"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, sort_keys=True)


class ContextLogger(logging.LoggerAdapter):
    """Attach stable simulation context fields to ordinary Python logs."""

    def process(
        self,
        msg: Any,
        kwargs: dict[str, Any],
    ) -> tuple[Any, dict[str, Any]]:
        extra = dict(self.extra or {})
        extra.update(kwargs.get("extra", {}))
        kwargs["extra"] = extra
        return msg, kwargs

    def child(self, **context: object) -> "ContextLogger":
        """Return a logger with additional immutable context fields."""
        merged = dict(self.extra or {})
        merged.update(context)
        return ContextLogger(self.logger, merged)


def configure_logging(level: int = logging.WARNING, *, json_output: bool = False) -> None:
    """Configure the package root logger without touching the canonical trace."""
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter() if json_output else logging.Formatter("%(levelname)s %(name)s %(message)s"))
    root = logging.getLogger("qorchsim")
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
    root.propagate = False


def get_logger(name: str, context: Mapping[str, object] | None = None) -> ContextLogger:
    """Create a context-aware package logger."""
    return ContextLogger(logging.getLogger(name), dict(context or {}))
