"""JSON logging configuration and request-scoped context for observability."""

import json
import logging
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any

# Request id for the request currently being handled (None outside a request).
request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)

# Mutable per-request holder so values set in dependencies (which may run in a
# copied context) remain visible to the middleware that logs the access line.
request_log_context_var: ContextVar[dict[str, Any] | None] = ContextVar(
    "request_log_context", default=None
)

# Attributes present on every LogRecord; anything else came from ``extra=``.
_STANDARD_ATTRS = frozenset(
    logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys()
) | {"message", "asctime", "taskName"}

_JSON_MARKER = "_movie_ranking_json"


def bind_user_id(user_id: Any) -> None:
    """Record the authenticated user id for the current request's access log."""
    context = request_log_context_var.get()
    if context is not None:
        context["user_id"] = str(user_id)


class JsonFormatter(logging.Formatter):
    """Format log records as one JSON object per line."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(
                timespec="milliseconds"
            ),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_var.get(),
        }
        for key, value in record.__dict__.items():
            if key not in _STANDARD_ATTRS and key not in payload:
                payload[key] = value
        if record.exc_info and record.exc_info[0] is not None:
            payload.setdefault("exception_type", record.exc_info[0].__name__)
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: int = logging.INFO) -> None:
    """Install the JSON formatter on the root logger (idempotent).

    Lambda pre-installs a root handler, so its formatter is replaced rather
    than adding a second handler that would duplicate every line.
    """
    root = logging.getLogger()
    root.setLevel(level)
    if not root.handlers:
        root.addHandler(logging.StreamHandler())
    for handler in root.handlers:
        handler.setFormatter(JsonFormatter())
        setattr(handler, _JSON_MARKER, True)
