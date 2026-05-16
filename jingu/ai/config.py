"""Local AI configuration loading."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from jingu.runtime.errors import JinguRuntimeError


CONFIG_FILENAME = ".env.deepseek.local"
API_KEY_NAME = "DEEPSEEK_API_KEY"
BASE_URL_NAME = "DEEPSEEK_BASE_URL"
MODEL_NAME = "DEEPSEEK_MODEL"
TIMEOUT_NAME = "DEEPSEEK_TIMEOUT_SECONDS"
TEMPERATURE_NAME = "DEEPSEEK_TEMPERATURE"


@dataclass(frozen=True)
class AiConfig:
    api_key: str
    base_url: str
    model: str
    timeout_seconds: float
    temperature: float | None = None


def load_ai_config(config_path: Path | str | None = None) -> AiConfig:
    path = Path(config_path) if config_path is not None else Path.cwd() / CONFIG_FILENAME
    values = read_env_file(path)
    merged = {**values, **{key: value for key, value in os.environ.items() if key in values}}

    missing = [name for name in (API_KEY_NAME, BASE_URL_NAME, MODEL_NAME) if not merged.get(name)]
    if missing:
        names = ", ".join(missing)
        raise JinguRuntimeError(f"missing AI configuration: {names}")

    timeout_seconds = parse_float(merged.get(TIMEOUT_NAME), default=60.0, name=TIMEOUT_NAME)
    temperature = parse_optional_float(merged.get(TEMPERATURE_NAME), name=TEMPERATURE_NAME)
    return AiConfig(
        api_key=merged[API_KEY_NAME],
        base_url=merged[BASE_URL_NAME].rstrip("/"),
        model=merged[MODEL_NAME],
        timeout_seconds=timeout_seconds,
        temperature=temperature,
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
