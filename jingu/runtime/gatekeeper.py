"""Guardkeeper checks for first-stage root laws."""

from __future__ import annotations

from typing import Any

from jingu.runtime.constants import (
    APPEARANCE_CANDIDATE_RESULT,
    APPEARANCE_EVIDENCE,
    APPEARANCE_STATE_CANDIDATE,
    STRUCTURE_VERSION,
    STATE_ABANDONED,
    STATE_ACCEPTED,
    STATE_REJECTED,
    STATE_READY,
    STATE_RUNNING,
)
from jingu.runtime.errors import GuardrailViolation
from jingu.runtime.object_store import ObjectStore
from jingu.runtime.repository import decode_json
from jingu.runtime.state_machine import validate_transition


TERMINAL_JOB_STATES = {STATE_ACCEPTED, STATE_REJECTED, STATE_ABANDONED}


class Guardkeeper:
    def __init__(self, object_store: ObjectStore) -> None:
        self.object_store = object_store

    def ensure_transition(self, job: dict[str, Any], next_state: str) -> None:
        validate_transition(str(job["state"]), next_state)
        if next_state in {STATE_READY, STATE_RUNNING}:
            if not str(job.get("target") or "").strip():
                raise GuardrailViolation("job target is required before readiness")
            if not str(job.get("acceptance_criteria") or "").strip():
                raise GuardrailViolation("job acceptance criteria are required before readiness")
            gaps = decode_json(job.get("required_context_gaps"), [])
            if gaps:
                raise GuardrailViolation("cannot enter ready or running with required context gaps")

    def ensure_candidate_submission(self, job: dict[str, Any]) -> None:
        if job["state"] not in {"running"}:
            raise GuardrailViolation("candidate submission requires a running job")

    def ensure_evidence_submission(self, job: dict[str, Any]) -> None:
        if str(job["state"]) in TERMINAL_JOB_STATES:
            raise GuardrailViolation("evidence submission is not allowed for terminal jobs")

    def ensure_evidence_metadata(self, metadata: dict[str, Any] | None) -> None:
        if not isinstance(metadata, dict):
            raise GuardrailViolation("evidence metadata is required")
        for field in ("evidence_kind", "evidence_hardness"):
            if not str(metadata.get(field) or "").strip():
                raise GuardrailViolation(f"evidence metadata field is required: {field}")

    def ensure_valid_appearance(self, appearance: dict[str, Any]) -> None:
        if appearance["structure_version"] != STRUCTURE_VERSION:
            raise GuardrailViolation("appearance structure version is incompatible")
        location = appearance.get("location")
        if location and not self.object_store.verify(location, str(appearance["checksum"])):
            raise GuardrailViolation("appearance checksum verification failed")

    def ensure_acceptance(
        self,
        *,
        job: dict[str, Any],
        candidate: dict[str, Any] | None,
        evidence: dict[str, Any] | None,
        completion_scope: str,
    ) -> None:
        if completion_scope != "self":
            raise GuardrailViolation("a job can only accept its own responsibility scope")
        if candidate is None:
            raise GuardrailViolation("acceptance requires a candidate result")
        if evidence is None:
            raise GuardrailViolation("acceptance requires evidence")
        if candidate["appearance_type"] != APPEARANCE_CANDIDATE_RESULT:
            raise GuardrailViolation("acceptance candidate must be a candidate result")
        if evidence["appearance_type"] != APPEARANCE_EVIDENCE:
            raise GuardrailViolation("acceptance evidence must be evidence")
        if candidate["source_job_id"] != job["job_id"]:
            raise GuardrailViolation("candidate belongs to a different job")
        if evidence["source_job_id"] != job["job_id"]:
            raise GuardrailViolation("evidence belongs to a different job")
        if candidate["state"] != APPEARANCE_STATE_CANDIDATE:
            raise GuardrailViolation("candidate is not isolated in candidate state")

        self.ensure_valid_appearance(candidate)
        self.ensure_valid_appearance(evidence)
        self.ensure_transition(job, "accepted")
