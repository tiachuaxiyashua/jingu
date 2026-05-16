"""Sandbox path helpers."""

from __future__ import annotations

import tempfile
from pathlib import Path


DEFAULT_SANDBOX_NAME = "jingu-ai-sandbox-current"
DEFAULT_LOG_DIR_NAME = "jingu-ai-logs"
FLOW_EVENTS_FILENAME = "flow-events.jsonl"
LATEST_LOG_POINTER_FILENAME = "latest-log.txt"


def default_sandbox_path() -> Path:
    return Path(tempfile.gettempdir()) / DEFAULT_SANDBOX_NAME


def resolve_sandbox_path(path: Path | str | None = None) -> Path:
    return Path(path).resolve() if path is not None else default_sandbox_path().resolve()


def flow_events_path(sandbox_path: Path) -> Path:
    return sandbox_path / FLOW_EVENTS_FILENAME


def default_log_dir() -> Path:
    return Path(tempfile.gettempdir()) / DEFAULT_LOG_DIR_NAME


def resolve_log_dir(path: Path | str | None = None) -> Path:
    return Path(path).resolve() if path is not None else default_log_dir().resolve()


def latest_log_pointer_path(log_dir: Path) -> Path:
    return log_dir / LATEST_LOG_POINTER_FILENAME
