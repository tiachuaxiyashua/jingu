"""Standard-library chat client."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Iterable

from jingu.ai.config import AiConfig
from jingu.runtime.errors import JinguRuntimeError


CHAT_COMPLETIONS_PATH = "/chat/completions"
STREAM_DONE = "[DONE]"
STREAM_DATA_PREFIX = "data:"

StreamEventHandler = Callable[[dict[str, str]], None]


@dataclass(frozen=True)
class ChatResponse:
    content: str
    raw: dict[str, Any]
    reasoning_content: str = ""


class ChatClient:
    def __init__(self, config: AiConfig) -> None:
        self.config = config

    def complete(self, message: str) -> ChatResponse:
        return self.complete_messages([{"role": "user", "content": message}])

    def complete_messages(
        self,
        messages: list[dict[str, str]],
        *,
        on_stream_event: StreamEventHandler | None = None,
    ) -> ChatResponse:
        body: dict[str, Any] = {
            "model": self.config.model,
            "messages": messages,
        }
        if self.config.extra_body:
            body.update(self.config.extra_body)
        if self.config.temperature is not None:
            body["temperature"] = self.config.temperature
        if self.config.stream:
            body["stream"] = True

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
            timeout = (
                self.config.stream_idle_timeout_seconds
                if self.config.stream
                else self.config.timeout_seconds
            )
            with urllib.request.urlopen(request, timeout=timeout) as response:
                if self.config.stream:
                    return self._read_streaming_response(response, on_stream_event)
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise JinguRuntimeError(f"AI provider request failed: {exc.code} {detail}") from exc
        except urllib.error.URLError as exc:
            raise JinguRuntimeError(f"AI provider connection failed: {exc.reason}") from exc
        except TimeoutError as exc:
            raise JinguRuntimeError(
                f"AI provider stream idle timeout after "
                f"{self.config.stream_idle_timeout_seconds:g} seconds without content"
            ) from exc

        return ChatResponse(content=extract_content(payload), raw=payload)

    def _read_streaming_response(
        self,
        response: Any,
        on_stream_event: StreamEventHandler | None,
    ) -> ChatResponse:
        content_parts: list[str] = []
        reasoning_parts: list[str] = []
        chunks: list[dict[str, Any]] = []
        finish_reason = ""
        chunk_index = 0
        last_progress = time.monotonic()

        try:
            for payload in iter_sse_payloads(response):
                if payload == STREAM_DONE:
                    break
                chunk = parse_stream_chunk(payload)
                chunks.append(chunk)
                choice = first_choice(chunk)
                delta = choice.get("delta") if isinstance(choice, dict) else None
                if not isinstance(delta, dict):
                    delta = {}

                reasoning_delta = text_or_empty(delta.get("reasoning_content"))
                content_delta = text_or_empty(delta.get("content"))
                finish_reason = text_or_empty(choice.get("finish_reason")) or finish_reason
                if reasoning_delta:
                    chunk_index += 1
                    reasoning_parts.append(reasoning_delta)
                    last_progress = time.monotonic()
                    emit_stream_delta(
                        on_stream_event,
                        index=chunk_index,
                        kind="reasoning",
                        text=reasoning_delta,
                    )
                if content_delta:
                    chunk_index += 1
                    content_parts.append(content_delta)
                    last_progress = time.monotonic()
                    emit_stream_delta(
                        on_stream_event,
                        index=chunk_index,
                        kind="content",
                        text=content_delta,
                    )
                if time.monotonic() - last_progress > self.config.stream_idle_timeout_seconds:
                    raise TimeoutError
        except TimeoutError:
            raise
        except OSError as exc:
            raise JinguRuntimeError(f"AI provider stream failed: {exc}") from exc

        content = "".join(content_parts)
        reasoning_content = "".join(reasoning_parts)
        emit_stream_finished(
            on_stream_event,
            chunk_count=chunk_index,
            finish_reason=finish_reason,
            content_character_count=len(content),
            reasoning_character_count=len(reasoning_content),
        )
        if not content.strip():
            raise JinguRuntimeError("AI provider response content was empty")
        return ChatResponse(
            content=content,
            reasoning_content=reasoning_content,
            raw={
                "stream": True,
                "chunk_count": chunk_index,
                "finish_reason": finish_reason,
                "chunks": chunks,
            },
        )

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


def iter_sse_payloads(response: Any) -> Iterable[str]:
    while True:
        raw_line = response.readline()
        if raw_line == b"" or raw_line == "":
            return
        line = decode_stream_line(raw_line).strip()
        if not line or line.startswith(":"):
            continue
        if not line.startswith(STREAM_DATA_PREFIX):
            continue
        yield line[len(STREAM_DATA_PREFIX) :].strip()


def decode_stream_line(raw_line: bytes | str) -> str:
    if isinstance(raw_line, bytes):
        return raw_line.decode("utf-8", errors="replace")
    return raw_line


def parse_stream_chunk(payload: str) -> dict[str, Any]:
    try:
        chunk = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise JinguRuntimeError("AI provider stream emitted invalid JSON") from exc
    if not isinstance(chunk, dict):
        raise JinguRuntimeError("AI provider stream emitted a non-object chunk")
    return chunk


def first_choice(chunk: dict[str, Any]) -> dict[str, Any]:
    choices = chunk.get("choices")
    if not isinstance(choices, list) or not choices:
        return {}
    choice = choices[0]
    return choice if isinstance(choice, dict) else {}


def text_or_empty(value: Any) -> str:
    return value if isinstance(value, str) else ""


def emit_stream_delta(
    handler: StreamEventHandler | None,
    *,
    index: int,
    kind: str,
    text: str,
) -> None:
    if handler is None:
        return
    handler(
        {
            "event": "stream_delta",
            "provider_delta_index": str(index),
            "provider_delta_kind": kind,
            "provider_delta_text": text,
            "provider_delta_character_count": str(len(text)),
        }
    )


def emit_stream_finished(
    handler: StreamEventHandler | None,
    *,
    chunk_count: int,
    finish_reason: str,
    content_character_count: int,
    reasoning_character_count: int,
) -> None:
    if handler is None:
        return
    handler(
        {
            "event": "stream_finished",
            "provider_stream_chunk_count": str(chunk_count),
            "provider_finish_reason": finish_reason,
            "provider_content_character_count": str(content_character_count),
            "provider_reasoning_character_count": str(reasoning_character_count),
        }
    )
