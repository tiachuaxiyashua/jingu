"""Safety guards for ephemeral sandbox lifecycle operations."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from jingu.runtime.errors import JinguRuntimeError


SANDBOX_MARKER_FILENAME = ".jingu-sandbox-marker.json"
SANDBOX_MARKER_KIND = "jingu-ai-sandbox"


def prepare_sandbox_directory(sandbox_path: Path, *, log_dir: Path | None = None) -> None:
    sandbox_path = sandbox_path.resolve()
    assert_sandbox_path_is_safe(sandbox_path, log_dir=log_dir)
    if sandbox_path.exists():
        if not sandbox_path.is_dir():
            raise JinguRuntimeError(f"sandbox path is not a directory: {sandbox_path}")
        if has_valid_sandbox_marker(sandbox_path):
            shutil.rmtree(sandbox_path)
        elif any(sandbox_path.iterdir()):
            raise JinguRuntimeError(
                "refusing to reset unmarked non-empty sandbox path: "
                f"{sandbox_path}. Choose an empty path or a Jingu-created sandbox."
            )
        else:
            sandbox_path.rmdir()
    sandbox_path.mkdir(parents=True, exist_ok=False)
    write_sandbox_marker(sandbox_path)


def destroy_sandbox_directory(sandbox_path: Path) -> None:
    sandbox_path = sandbox_path.resolve()
    if not sandbox_path.exists():
        return
    if not sandbox_path.is_dir():
        raise JinguRuntimeError(f"sandbox path is not a directory: {sandbox_path}")
    if not has_valid_sandbox_marker(sandbox_path):
        raise JinguRuntimeError(
            "refusing to destroy unmarked sandbox path: "
            f"{sandbox_path}. The path was not created by the Jingu sandbox launcher."
        )
    shutil.rmtree(sandbox_path)


def assert_sandbox_path_is_safe(sandbox_path: Path, *, log_dir: Path | None = None) -> None:
    sandbox_path = sandbox_path.resolve()
    if sandbox_path == sandbox_path.parent:
        raise JinguRuntimeError(f"refusing to use filesystem root as sandbox: {sandbox_path}")
    if sandbox_path == Path.cwd().resolve():
        raise JinguRuntimeError(f"refusing to use current workspace as sandbox: {sandbox_path}")
    try:
        home = Path.home().resolve()
    except RuntimeError:
        home = None
    if home is not None and sandbox_path == home:
        raise JinguRuntimeError(f"refusing to use user home as sandbox: {sandbox_path}")
    if log_dir is not None:
        resolved_log_dir = log_dir.resolve()
        if sandbox_path == resolved_log_dir:
            raise JinguRuntimeError("sandbox path and log directory must be different")
        if sandbox_path in resolved_log_dir.parents:
            raise JinguRuntimeError(
                "log directory must not be inside the ephemeral sandbox; "
                "cleanup would delete persistent logs"
            )


def marker_path(sandbox_path: Path) -> Path:
    return sandbox_path / SANDBOX_MARKER_FILENAME


def write_sandbox_marker(sandbox_path: Path) -> None:
    marker_path(sandbox_path).write_text(
        json.dumps({"kind": SANDBOX_MARKER_KIND}, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )


def has_valid_sandbox_marker(sandbox_path: Path) -> bool:
    path = marker_path(sandbox_path)
    if not path.is_file():
        return False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return isinstance(payload, dict) and payload.get("kind") == SANDBOX_MARKER_KIND
