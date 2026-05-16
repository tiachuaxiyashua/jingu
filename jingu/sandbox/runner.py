"""Ephemeral AI chat runner."""

from __future__ import annotations

import shutil
from pathlib import Path

from jingu.ai.client import ChatClient
from jingu.ai.config import load_ai_config
from jingu.runtime.service import RuntimeService
from jingu.sandbox.flow import (
    FLOW_AI_REQUEST_STARTED,
    FLOW_AI_RESPONSE_RECEIVED,
    FLOW_CANDIDATE_SUBMITTED,
    FLOW_EVIDENCE_SUBMITTED,
    FLOW_JOB_ACCEPTED,
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

            service.accept_candidate(
                job_id,
                candidate_appearance_id=candidate["appearance_id"],
                evidence_appearance_id=evidence["appearance_id"],
                actor_id="system",
            )
            self.flow.write(FLOW_JOB_ACCEPTED, "job accepted", job_id=job_id)
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
