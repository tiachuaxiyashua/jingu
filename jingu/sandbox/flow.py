"""JSONL flow event stream for sandbox runs."""

from __future__ import annotations

import json
import re
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
SUSPICIOUS_QUESTION_MARKS = re.compile(r"\?{4,}")

EVENT_LABELS = {
    FLOW_SANDBOX_CREATED: "沙盒已创建",
    FLOW_RUNTIME_INITIALIZED: "运行库已初始化",
    FLOW_CHAT_SESSION_STARTED: "对话会话已开始",
    FLOW_METHOD_SOURCE_RESOLVED: "方法来源已解析",
    FLOW_METHOD_CONTEXT_LOADED: "方法上下文已加载",
    FLOW_METHOD_CONTEXT_INJECTED: "方法上下文已注入",
    FLOW_ROOT_JOB_CREATED: "根业已创建",
    FLOW_JOB_READY: "业已就绪",
    FLOW_JOB_RUNNING: "业运行中",
    FLOW_USER_INPUT_RECORDED: "用户输入已记录",
    FLOW_AI_REQUEST_STARTED: "AI 请求已开始",
    FLOW_AI_RESPONSE_RECEIVED: "AI 响应已收到",
    FLOW_CANDIDATE_SUBMITTED: "候选结果已提交",
    FLOW_EVIDENCE_SUBMITTED: "证据已提交",
    FLOW_FEEDBACK_JUDGMENT_REQUESTED: "反馈判断已请求",
    FLOW_FEEDBACK_JUDGMENT_RECEIVED: "反馈判断已收到",
    FLOW_FEEDBACK_JOB_CREATED: "反馈业已创建",
    FLOW_FEEDBACK_JOB_SKIPPED: "反馈业已跳过",
    FLOW_METHOD_SELF_REVIEW_REQUESTED: "方法自验已请求",
    FLOW_METHOD_SELF_REVIEW_RECEIVED: "方法自验已收到",
    FLOW_METHOD_UPDATE_CANDIDATE_RECORDED: "方法更新候选已记录",
    FLOW_RESULT_OUTPUT_RECORDED: "结果输出已记录",
    FLOW_CHAT_TURN_FINISHED: "对话轮次已完成",
    FLOW_CHAT_SESSION_FINISHED: "对话会话已结束",
    FLOW_RUN_FAILED: "运行失败",
    FLOW_RUN_FINISHED: "运行已完成",
    FLOW_SANDBOX_DESTROYED: "沙盒已销毁",
}

FIELD_LABELS = {
    "appearance_id": "相编号",
    "error": "错误",
    "feedback_job_id": "反馈业编号",
    "feedback_job_kind": "反馈业类型",
    "feedback_job_summary": "反馈业摘要",
    "feedback_job_target": "反馈业目标",
    "input": "输入内容",
    "job_id": "业编号",
    "judgment": "判断结果",
    "log_path": "JSONL 日志路径",
    "message_count": "消息数量",
    "method_checksum": "方法校验码",
    "method_content": "方法全文",
    "method_name": "方法名称",
    "method_path": "方法路径",
    "method_size": "方法大小",
    "readable_log_path": "可读日志路径",
    "reason": "原因",
    "required_context_gaps": "缺失上下文",
    "response": "AI 响应",
    "result": "结果输出",
    "review": "方法自验",
    "sandbox_path": "沙盒路径",
    "turn": "轮次",
}


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
                        "# 金箍 AI 沙盒可读日志\n\n"
                        f"- JSONL 机器日志：`{jsonl_path}`\n"
                        f"- 沙盒实时事件流：`{self.path}`\n"
                        f"- 人类可读日志：`{self.readable_log_path}`\n"
                        "- 文件编码：UTF-8 with BOM\n\n"
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
    event_label = EVENT_LABELS.get(event_type, event_type)
    message = readable_message(event_type, str(event.get("message", "")))
    data = event.get("data") or {}
    if not isinstance(data, dict):
        data = {"data": data}

    lines = [f"## {timestamp} | {event_label}（{event_type}）", "", f"说明：{message}"]
    if data:
        lines.append("")
        for key in sorted(data):
            value = "" if data[key] is None else str(data[key])
            label = readable_field_label(str(key))
            if _should_render_as_block(key, value):
                lines.append(f"### {label}")
                lines.append("")
                lines.extend(_encoding_warning_lines(value))
                fence = _dynamic_fence(value)
                lines.append(f"{fence}text")
                lines.append(value)
                lines.append(f"{fence}")
                lines.append("")
            else:
                warning = " 编码警告：该字段包含连续问号，原始中文可能在进入系统前已经损坏。" if has_suspicious_question_marks(value) else ""
                lines.append(f"- {label}: {value}{warning}")
    else:
        lines.append("")
        lines.append("- 数据：无")
    return "\n".join(lines).rstrip() + "\n"


def readable_message(event_type: str, fallback: str) -> str:
    return EVENT_LABELS.get(event_type, fallback)


def readable_field_label(key: str) -> str:
    label = FIELD_LABELS.get(key, key)
    return f"{label}（{key}）"


def has_suspicious_question_marks(value: str) -> bool:
    return bool(SUSPICIOUS_QUESTION_MARKS.search(value))


def _encoding_warning_lines(value: str) -> list[str]:
    if not has_suspicious_question_marks(value):
        return []
    return [
        "编码警告：该字段包含连续问号，原始中文可能在进入系统前已经损坏。",
        "",
    ]


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
