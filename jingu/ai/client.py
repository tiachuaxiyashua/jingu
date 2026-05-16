"""Standard-library chat client."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from jingu.ai.config import AiConfig
from jingu.runtime.errors import JinguRuntimeError


CHAT_COMPLETIONS_PATH = "/chat/completions"


@dataclass(frozen=True)
class ChatResponse:
    content: str
    raw: dict[str, Any]


class ChatClient:
    def __init__(self, config: AiConfig) -> None:
        self.config = config

    def complete(self, message: str) -> ChatResponse:
        return self.complete_messages([{"role": "user", "content": message}])

    def complete_messages(self, messages: list[dict[str, str]]) -> ChatResponse:
        body: dict[str, Any] = {
            "model": self.config.model,
            "messages": messages,
        }
        if self.config.temperature is not None:
            body["temperature"] = self.config.temperature

        request = urllib.request.Request(
            url=self.endpoint,
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise JinguRuntimeError(f"AI provider request failed: {exc.code} {detail}") from exc
        except urllib.error.URLError as exc:
            raise JinguRuntimeError(f"AI provider connection failed: {exc.reason}") from exc

        return ChatResponse(content=extract_content(payload), raw=payload)

    @property
    def endpoint(self) -> str:
        if self.config.base_url.endswith(CHAT_COMPLETIONS_PATH):
            return self.config.base_url
        return f"{self.config.base_url}{CHAT_COMPLETIONS_PATH}"


def extract_content(payload: dict[str, Any]) -> str:
    try:
        content = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise JinguRuntimeError("AI provider response did not contain message content") from exc
    if not isinstance(content, str) or not content.strip():
        raise JinguRuntimeError("AI provider response content was empty")
    return content
