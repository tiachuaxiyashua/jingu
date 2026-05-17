"""JSONL flow event stream for sandbox runs."""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from jingu.sandbox.paths import flow_events_path


FLOW_SANDBOX_CREATED = "sandbox_created"
FLOW_RUNTIME_INITIALIZED = "runtime_initialized"
FLOW_CHAT_SESSION_STARTED = "chat_session_started"
FLOW_METHOD_SOURCE_RESOLVED = "method_source_resolved"
FLOW_METHOD_CONTEXT_LOADED = "method_context_loaded"
FLOW_METHOD_CONTEXT_INJECTED = "method_context_injected"
FLOW_ROOT_JOB_CREATED = "root_job_created"
FLOW_JOB_READY = "job_ready"
FLOW_JOB_RUNNING = "job_running"
FLOW_USER_INPUT_RECORDED = "user_input_recorded"
FLOW_AI_REQUEST_STARTED = "ai_request_started"
FLOW_AI_RESPONSE_RECEIVED = "ai_response_received"
FLOW_CANDIDATE_SUBMITTED = "candidate_submitted"
FLOW_EVIDENCE_SUBMITTED = "evidence_submitted"
FLOW_FEEDBACK_JUDGMENT_REQUESTED = "feedback_judgment_requested"
FLOW_FEEDBACK_JUDGMENT_RECEIVED = "feedback_judgment_received"
FLOW_FEEDBACK_JOB_CREATED = "feedback_job_created"
FLOW_FEEDBACK_JOB_SKIPPED = "feedback_job_skipped"
FLOW_METHOD_SELF_REVIEW_REQUESTED = "method_self_review_requested"
FLOW_METHOD_SELF_REVIEW_RECEIVED = "method_self_review_received"
FLOW_METHOD_UPDATE_CANDIDATE_RECORDED = "method_update_candidate_recorded"
FLOW_RESULT_OUTPUT_RECORDED = "result_output_recorded"
FLOW_CHAT_TURN_FINISHED = "chat_turn_finished"
FLOW_CHAT_SESSION_FINISHED = "chat_session_finished"
FLOW_RUN_FAILED = "run_failed"
FLOW_RUN_FINISHED = "run_finished"
FLOW_SANDBOX_DESTROYED = "sandbox_destroyed"

TERMINAL_EVENTS = {FLOW_RUN_FINISHED, FLOW_CHAT_SESSION_FINISHED, FLOW_SANDBOX_DESTROYED}


@dataclass(frozen=True)
class FlowEvent:
    event_type: str
    message: str
    timestamp: str
    data: dict[str, str]

    def to_json(self) -> str:
        return json.dumps(
            {
                "event_type": self.event_type,
                "message": self.message,
                "timestamp": self.timestamp,
                "data": self.data,
            },
            ensure_ascii=False,
            sort_keys=True,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "event_type": self.event_type,
            "message": self.message,
            "timestamp": self.timestamp,
            "data": self.data,
        }


class FlowWriter:
    def __init__(
        self,
        sandbox_path: Path,
        diagnostic_log_path: Path | None = None,
        readable_log_path: Path | None = None,
    ) -> None:
        self.path = flow_events_path(sandbox_path)
        self.diagnostic_log_path = diagnostic_log_path
        self.readable_log_path = readable_log_path
        self._readable_header_written = False

    def write(self, event_type: str, message: str, **data: str) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        event = FlowEvent(
            event_type=event_type,
            message=message,
            timestamp=datetime.now(timezone.utc).isoformat(),
            data=data,
        )
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(event.to_json())
            stream.write("\n")
        if self.diagnostic_log_path is not None:
            self.diagnostic_log_path.parent.mkdir(parents=True, exist_ok=True)
            with self.diagnostic_log_path.open("a", encoding="utf-8") as stream:
                stream.write(event.to_json())
                stream.write("\n")
        if self.readable_log_path is not None:
            self._write_readable_event(event)

    def _write_readable_event(self, event: FlowEvent) -> None:
        self.readable_log_path.parent.mkdir(parents=True, exist_ok=True)
        if not self._readable_header_written:
            fresh = not self.readable_log_path.exists()
            with self.readable_log_path.open(
                "a", encoding="utf-8-sig" if fresh else "utf-8"
            ) as stream:
                if fresh:
                    jsonl_path = self.diagnostic_log_path or self.path
                    stream.write(
                        "# Jingu AI Sandbox Readable Log\n\n"
                        f"- JSONL log: `{jsonl_path}`\n"
                        f"- Live event stream: `{self.path}`\n"
                        f"- Readable log: `{self.readable_log_path}`\n"
                        "- Encoding: UTF-8 with BOM\n\n"
                    )
            self._readable_header_written = True

        with self.readable_log_path.open("a", encoding="utf-8") as stream:
            stream.write(format_readable_event(event.to_dict()))
            stream.write("\n")


def new_diagnostic_log_path(log_dir: Path) -> Path:
    log_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    return log_dir / f"ai-run-{timestamp}-{uuid.uuid4().hex}.jsonl"


def readable_log_path_for(diagnostic_log_path: Path) -> Path:
    return diagnostic_log_path.with_suffix(".md")


def format_readable_event(event: dict[str, object]) -> str:
    timestamp = str(event.get("timestamp", ""))
    event_type = str(event.get("event_type", ""))
    message = str(event.get("message", ""))
    data = event.get("data") or {}
    if not isinstance(data, dict):
        data = {"data": data}

    lines = [f"## {timestamp} | {event_type}", "", f"{message}"]
    if data:
        lines.append("")
        for key in sorted(data):
            value = "" if data[key] is None else str(data[key])
            if _should_render_as_block(key, value):
                lines.append(f"### {key}")
                lines.append("")
                fence = _dynamic_fence(value)
                lines.append(f"{fence}text")
                lines.append(value)
                lines.append(f"{fence}")
                lines.append("")
            else:
                lines.append(f"- {key}: {value}")
    else:
        lines.append("")
        lines.append("- data: (none)")
    return "\n".join(lines).rstrip() + "\n"


def _should_render_as_block(key: str, value: str) -> bool:
    if "\n" in value:
        return True
    if len(value) > 120:
        return True
    return key in {
        "input",
        "response",
        "result",
        "review",
        "method_content",
        "judgment",
        "required_context_gaps",
        "feedback_job_target",
        "feedback_job_summary",
    }


def _dynamic_fence(value: str) -> str:
    longest_run = 0
    current = 0
    for char in value:
        if char == "`":
            current += 1
            longest_run = max(longest_run, current)
        else:
            current = 0
    return "`" * max(3, longest_run + 1)


def tail_flow_events(
    sandbox_path: Path,
    *,
    poll_seconds: float = 0.2,
    wait_seconds: float = 30.0,
) -> Iterator[dict]:
    path = flow_events_path(sandbox_path)
    deadline = time.monotonic() + wait_seconds
    position = 0
    seen_terminal = False

    while True:
        if path.exists():
            deadline = time.monotonic() + wait_seconds
            with path.open("r", encoding="utf-8") as stream:
                stream.seek(position)
                while True:
                    line = stream.readline()
                    if not line:
                        break
                    position = stream.tell()
                    if not line.strip():
                        continue
                    event = json.loads(line)
                    yield event
                    if event.get("event_type") in TERMINAL_EVENTS:
                        seen_terminal = True
                if seen_terminal:
                    return
        elif seen_terminal or (not sandbox_path.exists() and time.monotonic() > deadline):
            return

        if time.monotonic() > deadline and not sandbox_path.exists():
            return
        time.sleep(poll_seconds)
