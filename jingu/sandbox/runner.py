"""Ephemeral AI chat runner."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from jingu.ai.client import ChatClient
from jingu.ai.config import load_ai_config
from jingu.runtime.service import RuntimeService
from jingu.sandbox.flow import (
    FLOW_AI_REQUEST_STARTED,
    FLOW_AI_RESPONSE_RECEIVED,
    FLOW_CANDIDATE_SUBMITTED,
    FLOW_CHAT_SESSION_FINISHED,
    FLOW_CHAT_SESSION_STARTED,
    FLOW_CHAT_TURN_FINISHED,
    FLOW_EVIDENCE_SUBMITTED,
    FLOW_FEEDBACK_JUDGMENT_RECEIVED,
    FLOW_FEEDBACK_JUDGMENT_REQUESTED,
    FLOW_FEEDBACK_JOB_CREATED,
    FLOW_FEEDBACK_JOB_SKIPPED,
    FLOW_JOB_READY,
    FLOW_JOB_RUNNING,
    FLOW_RESULT_OUTPUT_RECORDED,
    FLOW_RUN_FAILED,
    FLOW_ROOT_JOB_CREATED,
    FLOW_RUN_FINISHED,
    FLOW_RUNTIME_INITIALIZED,
    FLOW_SANDBOX_CREATED,
    FLOW_SANDBOX_DESTROYED,
    FLOW_USER_INPUT_RECORDED,
    FlowWriter,
    new_diagnostic_log_path,
)
from jingu.sandbox.paths import latest_log_pointer_path, resolve_log_dir, resolve_sandbox_path


class AiSandboxRunner:
    def __init__(
        self,
        *,
        sandbox_path: Path | str | None = None,
        log_dir: Path | str | None = None,
        config_path: Path | str | None = None,
        client: ChatClient | None = None,
    ) -> None:
        self.sandbox_path = resolve_sandbox_path(sandbox_path)
        self.log_dir = resolve_log_dir(log_dir)
        self.diagnostic_log_path = new_diagnostic_log_path(self.log_dir)
        self.config_path = Path(config_path) if config_path is not None else None
        self.client = client
        self.flow = FlowWriter(self.sandbox_path, self.diagnostic_log_path)

    def run(self, message: str) -> str:
        self._reset_sandbox()
        try:
            self.sandbox_path.mkdir(parents=True, exist_ok=True)
            self._write_latest_log_pointer()
            self.flow.write(
                FLOW_SANDBOX_CREATED,
                "sandbox created",
                sandbox_path=str(self.sandbox_path),
                log_path=str(self.diagnostic_log_path),
            )
            self.flow.write(FLOW_USER_INPUT_RECORDED, "user input recorded", input=message)

            service = RuntimeService(self.sandbox_path)
            service.initialize()
            self.flow.write(FLOW_RUNTIME_INITIALIZED, "runtime initialized")

            root = service.create_root_job(wish=message, target=message, actor_id="human")
            job_id = root["job_id"]
            self.flow.write(FLOW_ROOT_JOB_CREATED, "root job created", job_id=job_id)

            service.mark_ready(job_id, actor_id="system")
            self.flow.write(FLOW_JOB_READY, "job marked ready", job_id=job_id)

            service.start_job(job_id, actor_id="system")
            self.flow.write(FLOW_JOB_RUNNING, "job running", job_id=job_id)

            client = self.client or ChatClient(load_ai_config(self.config_path))
            self.flow.write(FLOW_AI_REQUEST_STARTED, "AI request started", job_id=job_id)
            response = client.complete(message)
            self.flow.write(
                FLOW_AI_RESPONSE_RECEIVED,
                "AI response received",
                job_id=job_id,
                response=response.content,
            )

            candidate = service.submit_candidate(
                job_id,
                text=response.content,
                actor_id="ai",
            )["candidate"]
            self.flow.write(
                FLOW_CANDIDATE_SUBMITTED,
                "candidate submitted",
                job_id=job_id,
                appearance_id=candidate["appearance_id"],
            )

            evidence = service.submit_evidence(
                job_id,
                text="provider_response_received",
                actor_id="system",
            )["evidence"]
            self.flow.write(
                FLOW_EVIDENCE_SUBMITTED,
                "evidence submitted",
                job_id=job_id,
                appearance_id=evidence["appearance_id"],
            )

            self.flow.write(FLOW_RESULT_OUTPUT_RECORDED, "result output recorded", result=response.content)
            self.flow.write(FLOW_RUN_FINISHED, "run finished", job_id=job_id)
            return response.content
        except Exception as exc:
            self.flow.write(FLOW_RUN_FAILED, "run failed", error=str(exc))
            raise
        finally:
            self.flow.write(
                FLOW_SANDBOX_DESTROYED,
                "sandbox destroyed",
                sandbox_path=str(self.sandbox_path),
                log_path=str(self.diagnostic_log_path),
            )
            shutil.rmtree(self.sandbox_path, ignore_errors=True)

    def _reset_sandbox(self) -> None:
        if self.sandbox_path.exists():
            shutil.rmtree(self.sandbox_path)

    def _write_latest_log_pointer(self) -> None:
        self.log_dir.mkdir(parents=True, exist_ok=True)
        latest_log_pointer_path(self.log_dir).write_text(
            str(self.diagnostic_log_path), encoding="utf-8"
        )


class AiSandboxChatSession:
    def __init__(
        self,
        *,
        sandbox_path: Path | str | None = None,
        log_dir: Path | str | None = None,
        config_path: Path | str | None = None,
        client: ChatClient | None = None,
    ) -> None:
        self.sandbox_path = resolve_sandbox_path(sandbox_path)
        self.log_dir = resolve_log_dir(log_dir)
        self.diagnostic_log_path = new_diagnostic_log_path(self.log_dir)
        self.config_path = Path(config_path) if config_path is not None else None
        self.client = client
        self.flow = FlowWriter(self.sandbox_path, self.diagnostic_log_path)
        self.history: list[dict[str, str]] = []
        self.service: RuntimeService | None = None
        self.turn_count = 0
        self.last_job_id: str | None = None
        self.last_feedback_job_id: str | None = None
        self.last_feedback_judgment: dict[str, Any] | None = None

    def start(self) -> None:
        self._reset_sandbox()
        self.history = []
        self.service = None
        self.turn_count = 0
        self.last_job_id = None
        self.last_feedback_job_id = None
        self.last_feedback_judgment = None
        self.sandbox_path.mkdir(parents=True, exist_ok=True)
        self._write_latest_log_pointer()
        self.flow.write(
            FLOW_SANDBOX_CREATED,
            "sandbox created",
            sandbox_path=str(self.sandbox_path),
            log_path=str(self.diagnostic_log_path),
        )
        self.service = RuntimeService(self.sandbox_path)
        self.service.initialize()
        self.flow.write(FLOW_RUNTIME_INITIALIZED, "runtime initialized")
        self.flow.write(FLOW_CHAT_SESSION_STARTED, "chat session started")

    def ask(self, user_input: str) -> str:
        if self.service is None:
            raise RuntimeError("chat session has not started")

        self.turn_count += 1
        turn = str(self.turn_count)
        self.last_feedback_job_id = None
        self.last_feedback_judgment = None
        self.flow.write(FLOW_USER_INPUT_RECORDED, "user input recorded", turn=turn, input=user_input)

        root = self.service.create_root_job(wish=user_input, target=user_input, actor_id="human")
        job_id = root["job_id"]
        self.last_job_id = job_id
        self.flow.write(FLOW_ROOT_JOB_CREATED, "root job created", turn=turn, job_id=job_id)

        self.service.mark_ready(job_id, actor_id="system")
        self.flow.write(FLOW_JOB_READY, "job marked ready", turn=turn, job_id=job_id)

        self.service.start_job(job_id, actor_id="system")
        self.flow.write(FLOW_JOB_RUNNING, "job running", turn=turn, job_id=job_id)

        self.history.append({"role": "user", "content": user_input})
        client = self.client or ChatClient(load_ai_config(self.config_path))
        self.flow.write(
            FLOW_AI_REQUEST_STARTED,
            "AI request started",
            turn=turn,
            job_id=job_id,
            message_count=str(len(self.history)),
        )
        response = client.complete_messages(self.history)
        self.history.append({"role": "assistant", "content": response.content})
        self.flow.write(
            FLOW_AI_RESPONSE_RECEIVED,
            "AI response received",
            turn=turn,
            job_id=job_id,
            response=response.content,
        )

        candidate = self.service.submit_candidate(
            job_id,
            text=response.content,
            actor_id="ai",
        )["candidate"]
        self.flow.write(
            FLOW_CANDIDATE_SUBMITTED,
            "candidate submitted",
            turn=turn,
            job_id=job_id,
            appearance_id=candidate["appearance_id"],
        )

        evidence = self.service.submit_evidence(
            job_id,
            text="provider_response_received",
            actor_id="system",
        )["evidence"]
        self.flow.write(
            FLOW_EVIDENCE_SUBMITTED,
            "evidence submitted",
            turn=turn,
            job_id=job_id,
            appearance_id=evidence["appearance_id"],
        )

        self.flow.write(
            FLOW_RESULT_OUTPUT_RECORDED,
            "result output recorded",
            turn=turn,
            result=response.content,
        )

        judgment = self._request_feedback_judgment(
            client=client,
            turn=turn,
            job_id=job_id,
            user_input=user_input,
            assistant_response=response.content,
        )
        self.last_feedback_judgment = judgment
        if judgment["needs_feedback_job"]:
            feedback_job = self.service.create_child_job(
                parent_job_id=job_id,
                target=judgment["feedback_job_summary"],
                actor_id="ai",
                required_context_gaps=judgment["required_context_gaps"],
            )
            self.last_feedback_job_id = feedback_job["job_id"]
            self.flow.write(
                FLOW_FEEDBACK_JOB_CREATED,
                "feedback job created",
                turn=turn,
                job_id=job_id,
                feedback_job_id=feedback_job["job_id"],
                feedback_job_kind=judgment["feedback_job_kind"],
                feedback_job_target=judgment["feedback_job_summary"],
                required_context_gaps=json.dumps(
                    judgment["required_context_gaps"], ensure_ascii=False, sort_keys=True
                ),
            )
        else:
            self.flow.write(
                FLOW_FEEDBACK_JOB_SKIPPED,
                "feedback job skipped",
                turn=turn,
                job_id=job_id,
                feedback_job_kind=judgment["feedback_job_kind"],
                reason=judgment["reason"],
            )

        self.flow.write(FLOW_CHAT_TURN_FINISHED, "chat turn finished", turn=turn, job_id=job_id)
        return response.content

    def finish(self) -> None:
        self.flow.write(FLOW_CHAT_SESSION_FINISHED, "chat session finished")
        self.flow.write(
            FLOW_SANDBOX_DESTROYED,
            "sandbox destroyed",
            sandbox_path=str(self.sandbox_path),
            log_path=str(self.diagnostic_log_path),
        )
        shutil.rmtree(self.sandbox_path, ignore_errors=True)
        self.service = None

    def fail(self, exc: Exception) -> None:
        self.flow.write(FLOW_RUN_FAILED, "chat session failed", error=str(exc))
        self.finish()

    def _reset_sandbox(self) -> None:
        if self.sandbox_path.exists():
            shutil.rmtree(self.sandbox_path)

    def _write_latest_log_pointer(self) -> None:
        self.log_dir.mkdir(parents=True, exist_ok=True)
        latest_log_pointer_path(self.log_dir).write_text(
            str(self.diagnostic_log_path), encoding="utf-8"
        )

    def _request_feedback_judgment(
        self,
        *,
        client: ChatClient,
        turn: str,
        job_id: str,
        user_input: str,
        assistant_response: str,
    ) -> dict[str, Any]:
        system_prompt = (
            "You judge whether the latest turn needs a feedback job. "
            "Return compact JSON only with keys: needs_feedback_job, feedback_job_kind, "
            "feedback_job_summary, required_context_gaps, reason. "
            "Use feedback_job_kind=high_value for decisive or high-risk follow-up, "
            "directional for guidance or correction, and none when no feedback job is needed."
        )
        request_payload = {
            "turn": turn,
            "job_id": job_id,
            "user_input": user_input,
            "assistant_response": assistant_response,
            "conversation_size": len(self.history),
        }
        self.flow.write(
            FLOW_FEEDBACK_JUDGMENT_REQUESTED,
            "feedback judgment requested",
            turn=turn,
            job_id=job_id,
            message_count=str(len(self.history)),
        )
        judgment_response = client.complete_messages(
            [
                {"role": "system", "content": system_prompt},
                *self.history,
                {"role": "user", "content": json.dumps(request_payload, ensure_ascii=False, sort_keys=True)},
            ]
        )
        self.flow.write(
            FLOW_FEEDBACK_JUDGMENT_RECEIVED,
            "feedback judgment received",
            turn=turn,
            job_id=job_id,
            judgment=judgment_response.content,
        )
        return self._parse_feedback_judgment(judgment_response.content)

    @staticmethod
    def _parse_feedback_judgment(content: str) -> dict[str, Any]:
        payload = AiSandboxChatSession._load_json_object(content)
        if not isinstance(payload, dict):
            raise RuntimeError("feedback judgment response must be a JSON object")

        needs_feedback_job = bool(payload.get("needs_feedback_job"))
        feedback_job_kind = str(payload.get("feedback_job_kind") or "none").strip()
        feedback_job_summary = str(payload.get("feedback_job_summary") or "").strip()
        reason = str(payload.get("reason") or "").strip()
        raw_gaps = payload.get("required_context_gaps") or []
        if not isinstance(raw_gaps, list):
            raise RuntimeError("feedback judgment response must include required_context_gaps as a list")

        required_context_gaps = [str(item).strip() for item in raw_gaps if str(item).strip()]

        if needs_feedback_job:
            if feedback_job_kind not in {"high_value", "directional"}:
                raise RuntimeError(
                    "feedback judgment response must choose high_value or directional"
                )
            if not feedback_job_summary:
                raise RuntimeError(
                    "feedback judgment response must include feedback_job_summary"
                )
        else:
            feedback_job_kind = "none"
            feedback_job_summary = ""

        return {
            "needs_feedback_job": needs_feedback_job,
            "feedback_job_kind": feedback_job_kind,
            "feedback_job_summary": feedback_job_summary,
            "required_context_gaps": required_context_gaps,
            "reason": reason,
        }

    @staticmethod
    def _load_json_object(content: str) -> Any:
        stripped = content.strip()
        try:
            return json.loads(stripped)
        except json.JSONDecodeError as first_error:
            if stripped.startswith("```"):
                lines = stripped.splitlines()
                if len(lines) >= 3 and lines[-1].strip() == "```":
                    fenced = "\n".join(lines[1:-1]).strip()
                    try:
                        return json.loads(fenced)
                    except json.JSONDecodeError:
                        pass

            start = stripped.find("{")
            end = stripped.rfind("}")
            if 0 <= start < end:
                try:
                    return json.loads(stripped[start : end + 1])
                except json.JSONDecodeError:
                    pass

            raise RuntimeError("feedback judgment response must be valid JSON") from first_error
