"""Tests for loading settings from SSM Parameter Store (ADR-0008).

The SSM network boundary is stubbed by replacing ``app.config._ssm_client``.
"""

import logging
import os
import subprocess
import sys
from typing import Any

import pytest

from app import config

PREFIX = "/movie-ranking/prod/"
REQUIRED = ["DATABASE_URL", "SECRET_KEY", "TMDB_API_KEY"]

FIVE = {
    "DATABASE_URL": "postgresql+asyncpg://u:p@h/db",
    "SECRET_KEY": "ssm-secret",
    "TMDB_API_KEY": "ssm-tmdb",
    "GOOGLE_CLIENT_ID": "ssm-gid",
    "GOOGLE_CLIENT_SECRET": "ssm-gsecret",
}


class StubSsm:
    """Fake SSM client serving parameters in pages of ``page_size``."""

    def __init__(self, params: dict[str, str], page_size: int = 100) -> None:
        self.params = params
        self.page_size = page_size
        self.calls: list[dict[str, Any]] = []

    def get_parameters_by_path(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(dict(kwargs))
        items = [{"Name": PREFIX + k, "Value": v} for k, v in self.params.items()]
        start = int(kwargs.get("NextToken", 0))
        page = items[start : start + self.page_size]
        resp: dict[str, Any] = {"Parameters": page}
        if start + self.page_size < len(items):
            resp["NextToken"] = str(start + self.page_size)
        return resp


@pytest.fixture
def ssm_env(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    """Clear secret env vars and set the SSM prefix."""
    for key in REQUIRED + ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"]:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("SSM_PARAMETER_PREFIX", PREFIX)
    return monkeypatch


def _stub(monkeypatch: pytest.MonkeyPatch, stub: StubSsm) -> StubSsm:
    monkeypatch.setattr(config, "_ssm_client", lambda: stub)
    return stub


def test_settings_populated_from_ssm(ssm_env: pytest.MonkeyPatch) -> None:
    stub = _stub(ssm_env, StubSsm(FIVE))
    s = config.Settings(_env_file=None)
    for key, value in FIVE.items():
        assert getattr(s, key) == value
    assert stub.calls[0]["Path"] == PREFIX
    assert stub.calls[0]["WithDecryption"] is True
    assert stub.calls[0]["Recursive"] is False


def test_environment_beats_ssm(ssm_env: pytest.MonkeyPatch) -> None:
    _stub(ssm_env, StubSsm(FIVE))
    ssm_env.setenv("SECRET_KEY", "env-secret")
    s = config.Settings(_env_file=None)
    assert s.SECRET_KEY == "env-secret"
    assert s.TMDB_API_KEY == "ssm-tmdb"


def test_pagination_reads_all_pages(ssm_env: pytest.MonkeyPatch) -> None:
    stub = _stub(ssm_env, StubSsm(FIVE, page_size=3))
    s = config.Settings(_env_file=None)
    assert len(stub.calls) == 2
    assert s.GOOGLE_CLIENT_SECRET == "ssm-gsecret"


def test_missing_parameter_logs_prefix_and_key_without_values(
    ssm_env: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    tmp_path: Any,
) -> None:
    ssm_env.chdir(tmp_path)  # keep a developer's local .env out of Settings()
    partial = {k: v for k, v in FIVE.items() if k != "TMDB_API_KEY"}
    _stub(ssm_env, StubSsm(partial))
    with caplog.at_level(logging.ERROR, logger="app.config"):
        with pytest.raises(Exception) as excinfo:
            config.load_settings()
    assert excinfo.type.__name__ == "ValidationError"
    assert "TMDB_API_KEY" in caplog.text
    assert PREFIX in caplog.text
    for value in FIVE.values():
        assert value not in caplog.text


def test_ssm_failure_raises_runtime_error_naming_prefix(
    ssm_env: pytest.MonkeyPatch,
) -> None:
    def boom() -> Any:
        raise OSError("no network")

    ssm_env.setattr(config, "_ssm_client", boom)
    with pytest.raises(RuntimeError, match=PREFIX):
        config.Settings(_env_file=None)


def test_prefix_unset_never_imports_boto3() -> None:
    env = {k: v for k, v in os.environ.items() if k != "SSM_PARAMETER_PREFIX"}
    code = "import sys; import app.config; assert 'boto3' not in sys.modules"
    result = subprocess.run(
        [sys.executable, "-c", code], env=env, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
