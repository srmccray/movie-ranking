"""Request-id, access-log middleware and unhandled-exception handler."""

import logging
import re
import time
import uuid
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.observability.logging_config import request_id_var, request_log_context_var

access_logger = logging.getLogger("app.access")
error_logger = logging.getLogger("app.errors")

REQUEST_ID_HEADER = "X-Request-ID"
_VALID_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{8,64}$")


def _resolve_request_id(scope: Scope) -> str:
    """Use a valid inbound id, then API Gateway's id, else generate one."""
    headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope["headers"]}
    aws_event = scope.get("aws.event") or {}
    candidates = [
        headers.get("x-request-id"),
        (aws_event.get("requestContext") or {}).get("requestId"),
        headers.get("x-amzn-requestid"),
    ]
    for candidate in candidates:
        if candidate and _VALID_REQUEST_ID.match(candidate):
            return candidate
    return uuid.uuid4().hex


class RequestIdMiddleware:
    """Pure ASGI middleware: sets the request id and logs one access record."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = _resolve_request_id(scope)
        scope.setdefault("state", {})["request_id"] = request_id
        log_context: dict[str, Any] = {}
        id_token = request_id_var.set(request_id)
        ctx_token = request_log_context_var.set(log_context)
        start = time.perf_counter()
        status_holder = {"status": 500}

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                status_holder["status"] = message["status"]
                name = REQUEST_ID_HEADER.lower().encode()
                headers = [(k, v) for k, v in message.get("headers", []) if k.lower() != name]
                headers.append((REQUEST_ID_HEADER.encode(), request_id.encode()))
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            extra: dict[str, Any] = {
                "method": scope["method"],
                "path": scope["path"],  # never the query string (may hold OAuth code/state)
                "status": status_holder["status"],
                "duration_ms": round((time.perf_counter() - start) * 1000, 2),
            }
            if "user_id" in log_context:
                extra["user_id"] = log_context["user_id"]
            access_logger.info("request", extra=extra)
            request_log_context_var.reset(ctx_token)
            request_id_var.reset(id_token)


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Log an unhandled error once and return the standard 500 JSON body."""
    request_id = getattr(request.state, "request_id", None)
    # Runs outside the middleware (ServerErrorMiddleware), so bind the id explicitly.
    token = request_id_var.set(request_id)
    try:
        error_logger.error(
            "unhandled_exception",
            exc_info=(type(exc), exc, exc.__traceback__),
            extra={
                "exception_type": type(exc).__name__,
                "method": request.method,
                "path": request.url.path,
            },
        )
    finally:
        request_id_var.reset(token)
    headers = {REQUEST_ID_HEADER: request_id} if request_id else {}
    return JSONResponse(
        status_code=500, content={"detail": "Internal server error"}, headers=headers
    )


def install_observability(app: FastAPI) -> None:
    """Add request-id/access-log middleware and the unhandled-exception handler."""
    app.add_middleware(RequestIdMiddleware)
    app.add_exception_handler(Exception, unhandled_exception_handler)
