"""Local AI configuration loading."""

from __future__ import annotations

import os
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jingu.runtime.errors import JinguRuntimeError


CONFIG_FILENAME = ".env.deepseek.local"
API_KEY_NAME = "DEEPSEEK_API_KEY"
BASE_URL_NAME = "DEEPSEEK_BASE_URL"
MODEL_NAME = "DEEPSEEK_MODEL"
TIMEOUT_NAME = "DEEPSEEK_TIMEOUT_SECONDS"
TEMPERATURE_NAME = "DEEPSEEK_TEMPERATURE"
STREAM_NAME = "DEEPSEEK_STREAM"
STREAM_IDLE_TIMEOUT_NAME = "DEEPSEEK_STREAM_IDLE_TIMEOUT_SECONDS"
EXTRA_BODY_NAME = "DEEPSEEK_EXTRA_BODY_JSON"
DEFAULT_TIMEOUT_SECONDS = 60.0
DEFAULT_STREAM_IDLE_TIMEOUT_SECONDS = 300.0
PROTECTED_EXTRA_BODY_KEYS = {"messages", "model", "stream", "temperature"}
KNOWN_CONFIG_NAMES = {
    API_KEY_NAME,
    BASE_URL_NAME,
    MODEL_NAME,
    TIMEOUT_NAME,
    TEMPERATURE_NAME,
    STREAM_NAME,
    STREAM_IDLE_TIMEOUT_NAME,
    EXTRA_BODY_NAME,
}


@dataclass(frozen=True)
class AiConfig:
    api_key: str
    base_url: str
    model: str
    timeout_seconds: float
    temperature: float | None = None
    stream: bool = True
    stream_idle_timeout_seconds: float = DEFAULT_STREAM_IDLE_TIMEOUT_SECONDS
    extra_body: dict[str, Any] | None = None


def load_ai_config(config_path: Path | str | None = None) -> AiConfig:
    path = Path(config_path) if config_path is not None else Path.cwd() / CONFIG_FILENAME
    values = read_env_file(path)
    env_values = {key: os.environ[key] for key in KNOWN_CONFIG_NAMES if key in os.environ}
    merged = {**values, **env_values}

    missing = [name for name in (API_KEY_NAME, BASE_URL_NAME, MODEL_NAME) if not merged.get(name)]
    if missing:
        names = ", ".join(missing)
        raise JinguRuntimeError(f"missing AI configuration: {names}")

    timeout_seconds = parse_float(
        merged.get(TIMEOUT_NAME), default=DEFAULT_TIMEOUT_SECONDS, name=TIMEOUT_NAME
    )
    temperature = parse_optional_float(merged.get(TEMPERATURE_NAME), name=TEMPERATURE_NAME)
    stream = parse_bool(merged.get(STREAM_NAME), default=True, name=STREAM_NAME)
    stream_idle_timeout_seconds = parse_float(
        merged.get(STREAM_IDLE_TIMEOUT_NAME),
        default=DEFAULT_STREAM_IDLE_TIMEOUT_SECONDS,
        name=STREAM_IDLE_TIMEOUT_NAME,
    )
    extra_body = parse_extra_body(merged.get(EXTRA_BODY_NAME), name=EXTRA_BODY_NAME)
    return AiConfig(
        api_key=merged[API_KEY_NAME],
        base_url=merged[BASE_URL_NAME].rstrip("/"),
        model=merged[MODEL_NAME],
        timeout_seconds=timeout_seconds,
        temperature=temperature,
        stream=stream,
        stream_idle_timeout_seconds=stream_idle_timeout_seconds,
        extra_body=extra_body,
    )


def read_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        raise JinguRuntimeError(f"AI configuration file not found: {path}")

    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = unquote(value.strip())
    return values


def unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def parse_float(value: str | None, *, default: float, name: str) -> float:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except ValueError as exc:
        raise JinguRuntimeError(f"invalid numeric AI configuration: {name}") from exc


def parse_optional_float(value: str | None, *, name: str) -> float | None:
    if value is None or value == "":
        return None
    return parse_float(value, default=0.0, name=name)


def parse_bool(value: str | None, *, default: bool, name: str) -> bool:
    if value is None or value == "":
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise JinguRuntimeError(f"invalid boolean AI configuration: {name}")


def parse_extra_body(value: str | None, *, name: str) -> dict[str, Any] | None:
    if value is None or value.strip() == "":
        return None
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise JinguRuntimeError(f"invalid JSON AI configuration: {name}") from exc
    if not isinstance(parsed, dict):
        raise JinguRuntimeError(f"AI configuration must be a JSON object: {name}")
    protected = sorted(PROTECTED_EXTRA_BODY_KEYS.intersection(parsed))
    if protected:
        keys = ", ".join(protected)
        raise JinguRuntimeError(
            f"AI extra body cannot override runtime-owned request fields: {keys}"
        )
    return parsed
