"""Runtime service API for the minimal Xiang-Ye kernel."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jingu.runtime.constants import (
    APPEARANCE_CANDIDATE_RESULT,
    APPEARANCE_EVIDENCE,
    APPEARANCE_METHOD_LAW_FRAGMENT,
    APPEARANCE_ORIGINAL_WISH,
    APPEARANCE_STATE_ACCEPTED,
    APPEARANCE_STATE_CANDIDATE,
    APPEARANCE_STATE_REJECTED,
    APPEARANCE_STATE_STABLE,
    EVENT_CANDIDATE_ACCEPTED,
    EVENT_CANDIDATE_REJECTED,
    EVENT_CANDIDATE_SUBMITTED,
    EVENT_CHILD_JOB_CREATED,
    EVENT_EVIDENCE_SUBMITTED,
    EVENT_METHOD_CALL_FRAME_OPENED,
    EVENT_JOB_MARKED_READY,
    EVENT_JOB_STARTED,
    EVENT_METHOD_LAW_BOUND,
    EVENT_ROOT_JOB_CREATED,
    STATE_ACCEPTED,
    STATE_DRAFT,
    STATE_READY,
    STATE_REJECTED,
    STATE_REVIEWING,
    STATE_RUNNING,
)
from jingu.runtime.gatekeeper import Guardkeeper
from jingu.runtime.object_store import ObjectStore, checksum_text
from jingu.runtime.repository import RuntimeRepository, decode_json, encode_json, new_id


class RuntimeService:
    def __init__(self, workspace: Path | str = ".") -> None:
        self.repository = RuntimeRepository(workspace)
        self.object_store = ObjectStore(self.repository.paths)
        self.guardkeeper = Guardkeeper(self.object_store)

    @property
    def paths(self):
        return self.repository.paths

    def initialize(self) -> dict[str, str]:
        self.repository.initialize()
        return {
            "runtime_root": str(self.paths.runtime_root),
            "database_path": str(self.paths.database_path),
            "object_store_root": str(self.paths.object_store_root),
        }

    def create_root_job(
        self,
        *,
        wish: str,
        target: str | None = None,
        actor_id: str = "human",
        acceptance_criteria: str = "",
        required_context_gaps: list[str] | None = None,
    ) -> dict[str, Any]:
        job_id = new_id("job")
        appearance_id = new_id("appearance")
        root_target = target or wish
        with self.repository.transaction() as connection:
            self.repository.create_job(
                connection,
                job_id=job_id,
                root_job_id=job_id,
                target=root_target,
                state=STATE_DRAFT,
                acceptance_criteria=acceptance_criteria,
                required_context_gaps=required_context_gaps,
            )
            self.repository.create_appearance(
                connection,
                appearance_id=appearance_id,
                appearance_type=APPEARANCE_ORIGINAL_WISH,
                state=APPEARANCE_STATE_STABLE,
                checksum=checksum_text(wish),
                summary=wish,
                source_job_id=job_id,
            )
            job = self.repository.update_job(
                connection, job_id, original_wish_appearance_id=appearance_id
            )
            self.repository.append_event(
                connection,
                job_id=job_id,
                event_type=EVENT_ROOT_JOB_CREATED,
                actor_id=actor_id,
                payload={
                    "original_wish_appearance_id": appearance_id,
                    "target": root_target,
                },
            )
            return self._hydrate_job(connection, job)

    def create_child_job(
        self,
        *,
        parent_job_id: str,
        target: str,
        actor_id: str = "system",
        acceptance_criteria: str = "",
        required_context_gaps: list[str] | None = None,
    ) -> dict[str, Any]:
        job_id = new_id("job")
        with self.repository.transaction() as connection:
            parent = self.repository.require_job(connection, parent_job_id)
            job = self.repository.create_job(
                connection,
                job_id=job_id,
                parent_job_id=parent_job_id,
                root_job_id=parent["root_job_id"],
                target=target,
                state=STATE_DRAFT,
                original_wish_appearance_id=parent["original_wish_appearance_id"],
                acceptance_criteria=acceptance_criteria,
                required_context_gaps=required_context_gaps,
            )
            self.repository.append_event(
                connection,
                job_id=job_id,
                event_type=EVENT_CHILD_JOB_CREATED,
                actor_id=actor_id,
                payload={"parent_job_id": parent_job_id, "target": target},
            )
            return self._hydrate_job(connection, job)

    def mark_ready(self, job_id: str, *, actor_id: str = "human") -> dict[str, Any]:
        return self._transition_job(
            job_id=job_id,
            next_state=STATE_READY,
            event_type=EVENT_JOB_MARKED_READY,
            actor_id=actor_id,
            payload={},
        )

    def start_job(self, job_id: str, *, actor_id: str = "human") -> dict[str, Any]:
        return self._transition_job(
            job_id=job_id,
            next_state=STATE_RUNNING,
            event_type=EVENT_JOB_STARTED,
            actor_id=actor_id,
            payload={},
        )

    def bind_method_law_fragments(
        self,
        job_id: str,
        *,
        fragments: list[dict[str, Any]],
        call_frame: dict[str, Any] | None = None,
        actor_id: str = "system",
    ) -> dict[str, Any]:
        if not fragments:
            raise ValueError("fragments are required")

        appearance_refs: list[dict[str, Any]] = []
        with self.repository.transaction() as connection:
            self.repository.require_job(connection, job_id)
            for fragment in fragments:
                content = str(fragment.get("content") or "")
                if not content.strip():
                    raise ValueError("method law fragment content is required")
                appearance_id = new_id("appearance")
                stored = self.object_store.write_text(appearance_id, content, suffix=".md")
                metadata = {
                    key: value
                    for key, value in fragment.items()
                    if key != "content" and value is not None
                }
                appearance = self.repository.create_appearance(
                    connection,
                    appearance_id=appearance_id,
                    appearance_type=APPEARANCE_METHOD_LAW_FRAGMENT,
                    state=APPEARANCE_STATE_STABLE,
                    checksum=stored.checksum,
                    location=stored.location,
                    summary=str(fragment.get("method_law_title") or fragment.get("method_law_id") or ""),
                    source_job_id=job_id,
                    applicable_scope="method_law_fragment",
                    metadata=metadata,
                )
                appearance_refs.append(
                    {
                        "appearance_id": appearance["appearance_id"],
                        "method_law_id": fragment.get("method_law_id"),
                        "method_law_title": fragment.get("method_law_title"),
                        "checksum": appearance["checksum"],
                    }
                )

            self.repository.append_event(
                connection,
                job_id=job_id,
                event_type=EVENT_METHOD_LAW_BOUND,
                actor_id=actor_id,
                payload={
                    "method_law_fragment_count": len(appearance_refs),
                    "method_law_fragment_refs": appearance_refs,
                },
            )
            call_frame_payload = None
            if call_frame is not None:
                call_frame_payload = self._validate_method_call_frame(call_frame, appearance_refs)
                self.repository.append_event(
                    connection,
                    job_id=job_id,
                    event_type=EVENT_METHOD_CALL_FRAME_OPENED,
                    actor_id=actor_id,
                    payload=call_frame_payload,
                )
            return {
                "job": self._hydrate_job(connection, self.repository.require_job(connection, job_id)),
                "method_law_fragments": appearance_refs,
                "method_call_frame": call_frame_payload,
            }

    def submit_candidate(
        self,
        job_id: str,
        *,
        file_path: Path | str | None = None,
        text: str | None = None,
        actor_id: str = "human",
    ) -> dict[str, Any]:
        appearance_id = new_id("appearance")
        with self.repository.transaction() as connection:
            job = self.repository.require_job(connection, job_id)
            self.guardkeeper.ensure_candidate_submission(job)
            stored = self._store_content(appearance_id, file_path=file_path, text=text)
            appearance = self.repository.create_appearance(
                connection,
                appearance_id=appearance_id,
                appearance_type=APPEARANCE_CANDIDATE_RESULT,
                state=APPEARANCE_STATE_CANDIDATE,
                checksum=stored["checksum"],
                location=stored["location"],
                summary=stored["summary"],
                source_job_id=job_id,
                metadata={"size": stored["size"]},
            )
            updated = self.repository.update_job(
                connection,
                job_id,
                state=STATE_REVIEWING,
                candidate_appearance_id=appearance_id,
            )
            self.repository.append_event(
                connection,
                job_id=job_id,
                event_type=EVENT_CANDIDATE_SUBMITTED,
                actor_id=actor_id,
                payload={"candidate_appearance_id": appearance_id},
            )
            return {"job": self._hydrate_job(connection, updated), "candidate": appearance}

    def submit_evidence(
        self,
        job_id: str,
        *,
        file_path: Path | str | None = None,
        text: str | None = None,
        actor_id: str = "human",
    ) -> dict[str, Any]:
        appearance_id = new_id("appearance")
        with self.repository.transaction() as connection:
            self.repository.require_job(connection, job_id)
            stored = self._store_content(appearance_id, file_path=file_path, text=text)
            appearance = self.repository.create_appearance(
                connection,
                appearance_id=appearance_id,
                appearance_type=APPEARANCE_EVIDENCE,
                state=APPEARANCE_STATE_STABLE,
                checksum=stored["checksum"],
                location=stored["location"],
                summary=stored["summary"],
                source_job_id=job_id,
                metadata={"size": stored["size"]},
            )
            job = self.repository.update_job(connection, job_id, evidence_appearance_id=appearance_id)
            self.repository.append_event(
                connection,
                job_id=job_id,
                event_type=EVENT_EVIDENCE_SUBMITTED,
                actor_id=actor_id,
                payload={"evidence_appearance_id": appearance_id},
            )
            return {"job": self._hydrate_job(connection, job), "evidence": appearance}

    def accept_candidate(
        self,
        job_id: str,
        *,
        candidate_appearance_id: str | None = None,
        evidence_appearance_id: str | None = None,
        completion_scope: str = "self",
        actor_id: str = "human",
    ) -> dict[str, Any]:
        with self.repository.transaction() as connection:
            job = self.repository.require_job(connection, job_id)
            candidate_id = candidate_appearance_id or job.get("candidate_appearance_id")
            evidence_id = evidence_appearance_id or job.get("evidence_appearance_id")
            candidate = (
                self.repository.get_appearance(connection, candidate_id) if candidate_id else None
            )
            evidence = self.repository.get_appearance(connection, evidence_id) if evidence_id else None
            self.guardkeeper.ensure_acceptance(
                job=job,
                candidate=candidate,
                evidence=evidence,
                completion_scope=completion_scope,
            )
            assert candidate is not None
            assert evidence is not None
            self.repository.update_appearance(
                connection, candidate["appearance_id"], state=APPEARANCE_STATE_ACCEPTED
            )
            updated = self.repository.update_job(
                connection,
                job_id,
                state=STATE_ACCEPTED,
                candidate_appearance_id=candidate["appearance_id"],
                evidence_appearance_id=evidence["appearance_id"],
                result_appearance_id=candidate["appearance_id"],
            )
            self.repository.append_event(
                connection,
                job_id=job_id,
                event_type=EVENT_CANDIDATE_ACCEPTED,
                actor_id=actor_id,
                payload={
                    "candidate_appearance_id": candidate["appearance_id"],
                    "evidence_appearance_id": evidence["appearance_id"],
                    "completion_scope": completion_scope,
                },
            )
            return self._hydrate_job(connection, updated)

    def reject_candidate(
        self,
        job_id: str,
        *,
        reason: str,
        candidate_appearance_id: str | None = None,
        actor_id: str = "human",
    ) -> dict[str, Any]:
        with self.repository.transaction() as connection:
            job = self.repository.require_job(connection, job_id)
            self.guardkeeper.ensure_transition(job, STATE_REJECTED)
            candidate_id = candidate_appearance_id or job.get("candidate_appearance_id")
            if candidate_id:
                candidate = self.repository.require_appearance(connection, candidate_id)
                self.guardkeeper.ensure_valid_appearance(candidate)
                self.repository.update_appearance(
                    connection, candidate_id, state=APPEARANCE_STATE_REJECTED
                )
            updated = self.repository.update_job(connection, job_id, state=STATE_REJECTED)
            self.repository.append_event(
                connection,
                job_id=job_id,
                event_type=EVENT_CANDIDATE_REJECTED,
                actor_id=actor_id,
                payload={"candidate_appearance_id": candidate_id, "reason": reason},
            )
            return self._hydrate_job(connection, updated)

    def get_status(self, job_id: str) -> dict[str, Any]:
        with self.repository.transaction() as connection:
            job = self.repository.require_job(connection, job_id)
            return self._hydrate_job(connection, job)

    def list_events(self, job_id: str) -> list[dict[str, Any]]:
        with self.repository.transaction() as connection:
            return self.repository.list_events(connection, job_id)

    def _transition_job(
        self,
        *,
        job_id: str,
        next_state: str,
        event_type: str,
        actor_id: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        with self.repository.transaction() as connection:
            job = self.repository.require_job(connection, job_id)
            self.guardkeeper.ensure_transition(job, next_state)
            updated = self.repository.update_job(connection, job_id, state=next_state)
            self.repository.append_event(
                connection,
                job_id=job_id,
                event_type=event_type,
                actor_id=actor_id,
                payload=payload,
            )
            return self._hydrate_job(connection, updated)

    def _store_content(
        self,
        appearance_id: str,
        *,
        file_path: Path | str | None,
        text: str | None,
    ) -> dict[str, Any]:
        if file_path is None and text is None:
            raise ValueError("file_path or text is required")
        if file_path is not None and text is not None:
            raise ValueError("only one of file_path or text is allowed")
        if file_path is not None:
            stored = self.object_store.write_file(appearance_id, Path(file_path))
            summary = Path(file_path).name
        else:
            assert text is not None
            stored = self.object_store.write_text(appearance_id, text)
            summary = text[:200]
        return {"location": stored.location, "checksum": stored.checksum, "size": stored.size, "summary": summary}

    @staticmethod
    def _validate_method_call_frame(
        call_frame: dict[str, Any],
        appearance_refs: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if not isinstance(call_frame, dict):
            raise ValueError("method call frame must be a JSON object")
        required_text_fields = (
            "method_name",
            "method_path",
            "method_checksum",
            "binding_reason",
            "output_contract",
            "acceptance_criteria",
            "return_point",
            "repeat_detection_key",
        )
        missing = [
            field
            for field in required_text_fields
            if not str(call_frame.get(field) or "").strip()
        ]
        for field in ("invocation_input", "budget"):
            value = call_frame.get(field)
            if value is None or (isinstance(value, str) and not value.strip()):
                missing.append(field)
        if "depth" not in call_frame:
            missing.append("depth")
        if missing:
            raise ValueError(
                f"method call frame is missing fields: {', '.join(sorted(set(missing)))}"
            )

        try:
            depth = int(call_frame["depth"])
        except (TypeError, ValueError) as exc:
            raise ValueError("method call frame depth must be an integer") from exc
        if depth < 0:
            raise ValueError("method call frame depth must be zero or greater")

        payload = dict(call_frame)
        payload["depth"] = depth
        payload["method_law_fragment_refs"] = appearance_refs
        return payload

    def _hydrate_job(self, connection, job: dict[str, Any]) -> dict[str, Any]:
        hydrated = dict(job)
        hydrated["required_context_gaps"] = decode_json(job.get("required_context_gaps"), [])
        for field in ("original_wish_appearance_id", "candidate_appearance_id", "evidence_appearance_id", "result_appearance_id"):
            appearance_id = job.get(field)
            if appearance_id:
                hydrated[field.removesuffix("_appearance_id")] = self.repository.get_appearance(
                    connection, appearance_id
                )
        return hydrated
