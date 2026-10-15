"""Executable API conventions checked against the public OpenAPI document."""

from typing import Any

from app.main import app

# Documented exceptions to the trailing-slash rule. Adding one is a reviewed change.
TRAILING_SLASH_EXCEPTIONS = {"/api/v1/auth/register", "/api/v1/auth/login"}
HTTP_METHODS = {"get", "post", "put", "patch", "delete"}


def _operations() -> list[tuple[str, str, dict[str, Any]]]:
    paths = app.openapi()["paths"]
    return [
        (path, method, op)
        for path, item in paths.items()
        if path.startswith("/api/v1")
        for method, op in item.items()
        if method in HTTP_METHODS
    ]


def test_api_v1_paths_end_with_trailing_slash() -> None:
    paths = app.openapi()["paths"]
    offenders = [
        p
        for p in paths
        if p.startswith("/api/v1") and not p.endswith("/") and p not in TRAILING_SLASH_EXCEPTIONS
    ]
    assert not offenders, f"Routes missing trailing slash: {sorted(offenders)}"


def test_every_operation_declares_its_success_response() -> None:
    offenders = []
    for path, method, op in _operations():
        successes = {c: r for c, r in op["responses"].items() if c.startswith("2")}
        redirects = [c for c in op["responses"] if c.startswith("3")]
        has_json_schema = any(
            r.get("content", {}).get("application/json", {}).get("schema")
            for r in successes.values()
        )
        if not (redirects or "204" in successes or has_json_schema):
            offenders.append(f"{method.upper()} {path}")
    assert not offenders, f"Operations without a declared response: {sorted(offenders)}"
