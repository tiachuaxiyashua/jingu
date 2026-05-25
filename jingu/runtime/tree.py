"""Minimal job tree engine over the runtime kernel."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jingu.runtime.constants import (
    EVENT_CHILD_JOB_CREATED,
    EVENT_METHOD_CALL_FRAME_OPENED,
    EVENT_RESULT_PACKAGE_SUBMITTED,
    EVENT_SPLIT_PROPOSAL_ACCEPTED,
    STATE_ABANDONED,
    STATE_ACCEPTED,
    STATE_DRAFT,
    STATE_REJECTED,
    STATE_REVIEWING,
    STATE_RUNNING,
)
from jingu.runtime.errors import GuardrailViolation
from jingu.runtime.object_store import checksum_text
from jingu.runtime.repository import decode_json, new_id
from jingu.runtime.service import RuntimeService
from jingu.sandbox.method import MethodContext, load_method_context


TERMINAL_STATES = {STATE_ACCEPTED, STATE_REJECTED, STATE_ABANDONED}
PACKAGE_REQUIRED_FIELDS = {
    "conclusion",
    "artifacts",
    "evidence_summary",
    "open_questions",
    "suggested_follow_up_jobs",
}
PACKAGE_METADATA_KIND = "result_package"
SPLIT_DECISION_LAW_FIELDS = (
    "blocks_parent_execution",
    "blocks_parent_acceptance",
    "needs_distinct_capability",
    "has_independent_result_package",
    "has_high_value_or_risk",
)
SPLIT_DECISION_TRIGGER_FIELDS = (
    "blocks_parent_execution",
    "blocks_parent_acceptance",
    "needs_distinct_capability",
    "has_high_value_or_risk",
)
SPLIT_DECISION_LAW_NAME = "分业判定律"


class TreeService:
    def __init__(self, workspace: Path | str = ".") -> None:
        self.runtime = RuntimeService(workspace)

    def propose_child_job(
        self,
        *,
        parent_job_id: str,
        target: str,
        blocking_reason: str,
        output_contract: str,
        acceptance_criteria: str,
        estimated_effort: int,
        depth_limit: int,
        required_context_gaps: list[str] | None = None,
        method_path: Path | str | None = None,
        method_binding_reason: str | None = None,
        method_return_point: str | None = None,
        split_law: dict[str, Any] | None = None,
        actor_id: str = "ai",
    ) -> dict[str, Any]:
        target = self._require_text("target", target)
        blocking_reason = self._require_text("blocking_reason", blocking_reason)
        output_contract = self._require_text("output_contract", output_contract)
        acceptance_criteria = self._require_text("acceptance_criteria", acceptance_criteria)
        method_context = self._load_optional_method_binding(
            method_path=method_path,
            method_binding_reason=method_binding_reason,
            method_return_point=method_return_point,
        )
        if estimated_effort < 1:
            raise GuardrailViolation("estimated effort must be positive")
        if depth_limit < 1:
            raise GuardrailViolation("depth limit must be positive")
        split_law = self._normalize_split_decision_law(
            split_law=split_law,
            blocking_reason=blocking_reason,
        )

        with self.runtime.repository.transaction() as connection:
            parent = self.runtime.repository.require_job(connection, parent_job_id)
            if parent["state"] in TERMINAL_STATES:
                raise GuardrailViolation("cannot split a terminal job")

            current_depth = self._job_depth(connection, parent)
            child_depth = current_depth + 1
            if child_depth > depth_limit:
                raise GuardrailViolation("split exceeds depth limit")

            siblings = self.runtime.repository.list_child_jobs(connection, parent_job_id)
            normalized_target = self._normalize_text(target)
            if any(self._normalize_text(str(sibling["target"])) == normalized_target for sibling in siblings):
                raise GuardrailViolation("duplicate sibling target")

            proposal_payload = {
                "parent_job_id": parent_job_id,
                "target": target,
                "blocking_reason": blocking_reason,
                "output_contract": output_contract,
                "acceptance_criteria": acceptance_criteria,
                "estimated_effort": estimated_effort,
                "depth_limit": depth_limit,
                "child_depth": child_depth,
                "required_context_gaps": required_context_gaps or [],
                "split_law": split_law,
            }
            self.runtime.repository.append_event(
                connection,
                job_id=parent_job_id,
                event_type=EVENT_SPLIT_PROPOSAL_ACCEPTED,
                actor_id=actor_id,
                payload=proposal_payload,
            )

            child_job_id = new_id("job")
            child = self.runtime.repository.create_job(
                connection,
                job_id=child_job_id,
                parent_job_id=parent_job_id,
                root_job_id=parent["root_job_id"],
                target=target,
                state=STATE_DRAFT,
                original_wish_appearance_id=parent["original_wish_appearance_id"],
                acceptance_criteria=acceptance_criteria,
                required_context_gaps=required_context_gaps,
            )
            self.runtime.repository.append_event(
                connection,
                job_id=child_job_id,
                event_type=EVENT_CHILD_JOB_CREATED,
                actor_id=actor_id,
                payload={
                    "parent_job_id": parent_job_id,
                    "target": target,
                    "blocking_reason": blocking_reason,
                    "output_contract": output_contract,
                    "split_law": split_law,
                },
            )
            result = {
                "proposal": proposal_payload,
                "child": self.runtime._hydrate_job(connection, child),
            }

        if method_context is not None:
            assert method_binding_reason is not None
            assert method_return_point is not None
            binding = self._bind_method_to_child_job(
                child_job_id=child_job_id,
                parent_job_id=parent_job_id,
                method=method_context,
                binding_reason=self._require_text(
                    "method_binding_reason", method_binding_reason
                ),
                invocation_input={
                    "parent_job_id": parent_job_id,
                    "target": target,
                    "blocking_reason": blocking_reason,
                    "required_context_gaps": required_context_gaps or [],
                    "split_law": split_law,
                },
                output_contract=output_contract,
                acceptance_criteria=acceptance_criteria,
                return_point=self._require_text("method_return_point", method_return_point),
                budget={
                    "estimated_effort": estimated_effort,
                    "depth_limit": depth_limit,
                },
                depth=child_depth,
                actor_id=actor_id,
            )
            result["method_binding"] = binding
        return result

    def _normalize_split_decision_law(
        self,
        *,
        split_law: dict[str, Any] | None,
        blocking_reason: str,
    ) -> dict[str, Any]:
        if split_law is None:
            raise GuardrailViolation("split decision law is required")
        else:
            if not isinstance(split_law, dict):
                raise GuardrailViolation("split law must be a JSON object")
            normalized = {"law_name": str(split_law.get("law_name") or SPLIT_DECISION_LAW_NAME)}
            for field in SPLIT_DECISION_LAW_FIELDS:
                if field not in split_law:
                    raise GuardrailViolation(f"split law is missing field: {field}")
                value = split_law[field]
                if not isinstance(value, bool):
                    raise GuardrailViolation(f"split law field must be boolean: {field}")
                normalized[field] = value
            normalized["reason"] = self._require_text(
                "split_law.reason",
                str(split_law.get("reason") or blocking_reason),
            )

        if not normalized["has_independent_result_package"]:
            raise GuardrailViolation(
                "split decision law requires an independent result package consumable by the parent"
            )
        if not any(bool(normalized[field]) for field in SPLIT_DECISION_TRIGGER_FIELDS):
            raise GuardrailViolation(
                "split decision law requires execution, acceptance, capability, or high-value/risk grounds"
            )
        return normalized

    def _load_optional_method_binding(
        self,
        *,
        method_path: Path | str | None,
        method_binding_reason: str | None,
        method_return_point: str | None,
    ) -> MethodContext | None:
        has_binding_field = any(
            value is not None
            for value in (method_path, method_binding_reason, method_return_point)
        )
        if not has_binding_field:
            return None
        if method_path is None:
            raise GuardrailViolation("method path is required when binding a method")
        self._require_text("method_binding_reason", method_binding_reason or "")
        self._require_text("method_return_point", method_return_point or "")
        try:
            return load_method_context(
                method_path=method_path,
                workspace=self.runtime.paths.workspace,
            )
        except Exception as exc:
            raise GuardrailViolation(str(exc)) from exc

    def _bind_method_to_child_job(
        self,
        *,
        child_job_id: str,
        parent_job_id: str,
        method: MethodContext,
        binding_reason: str,
        invocation_input: dict[str, Any],
        output_contract: str,
        acceptance_criteria: str,
        return_point: str,
        budget: dict[str, Any],
        depth: int,
        actor_id: str,
    ) -> dict[str, Any]:
        call_frame = {
            "method_name": method.name,
            "method_path": str(method.path),
            "method_checksum": method.checksum,
            "binding_reason": binding_reason,
            "invocation_input": invocation_input,
            "output_contract": output_contract,
            "acceptance_criteria": acceptance_criteria,
            "return_point": return_point,
            "budget": budget,
            "depth": depth,
            "repeat_detection_key": checksum_text(
                json.dumps(
                    {
                        "parent_job_id": parent_job_id,
                        "child_job_id": child_job_id,
                        "method_checksum": method.checksum,
                        "target": invocation_input.get("target"),
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
            ),
        }
        return self.runtime.bind_method_law_fragments(
            child_job_id,
            fragments=[fragment.binding_payload(method=method) for fragment in method.fragments],
            call_frame=call_frame,
            actor_id=actor_id,
        )

    def get_tree(self, job_id: str) -> dict[str, Any]:
        with self.runtime.repository.transaction() as connection:
            job = self.runtime.repository.require_job(connection, job_id)
            root_job_id = str(job["root_job_id"])
            rows = self.runtime.repository.list_jobs_by_root(connection, root_job_id)
            jobs = [self._job_summary(connection, row) for row in rows]
            return {
                "root_job_id": root_job_id,
                "jobs": jobs,
                "links": [
                    {"parent_job_id": row["parent_job_id"], "child_job_id": row["job_id"]}
                    for row in rows
                    if row.get("parent_job_id")
                ],
            }

    def get_frontier(self, job_id: str) -> dict[str, Any]:
        tree = self.get_tree(job_id)
        active_jobs = {
            job["job_id"]: job
            for job in tree["jobs"]
            if job["state"] not in TERMINAL_STATES
        }
        active_parents = {
            link["parent_job_id"]
            for link in tree["links"]
            if link["child_job_id"] in active_jobs
        }
        frontier = [
            job
            for job_id_value, job in active_jobs.items()
            if job_id_value not in active_parents
        ]
        return {"root_job_id": tree["root_job_id"], "frontier": frontier}

    def submit_result_package(
        self,
        job_id: str,
        *,
        package: dict[str, Any],
        evidence_text: str | None = None,
        actor_id: str = "human",
    ) -> dict[str, Any]:
        validated = self._validate_package(package)
        serialized = json.dumps(validated, ensure_ascii=False, sort_keys=True)
        candidate_result = self.runtime.submit_candidate(
            job_id,
            text=serialized,
            actor_id=actor_id,
            metadata={"kind": PACKAGE_METADATA_KIND, "appearance_kind": PACKAGE_METADATA_KIND},
        )
        evidence_body = evidence_text or str(validated["evidence_summary"])
        evidence_result = self.runtime.submit_evidence(
            job_id,
            text=evidence_body,
            actor_id=actor_id,
            metadata={
                "evidence_kind": "result_package_evidence",
                "evidence_hardness": "ai_or_manual_package",
            },
        )

        candidate = candidate_result["candidate"]
        evidence = evidence_result["evidence"]
        with self.runtime.repository.transaction() as connection:
            self.runtime.repository.append_event(
                connection,
                job_id=job_id,
                event_type=EVENT_RESULT_PACKAGE_SUBMITTED,
                actor_id=actor_id,
                payload={
                    "candidate_appearance_id": candidate["appearance_id"],
                    "evidence_appearance_id": evidence["appearance_id"],
                    "package_kind": PACKAGE_METADATA_KIND,
                },
            )

        return {
            "job": self.runtime.get_status(job_id),
            "candidate": candidate,
            "evidence": evidence,
            "package": validated,
        }

    def reevaluate_parent(self, job_id: str) -> dict[str, Any]:
        with self.runtime.repository.transaction() as connection:
            parent = self.runtime.repository.require_job(connection, job_id)
            children = self.runtime.repository.list_child_jobs(connection, job_id)
            unresolved_children: list[dict[str, Any]] = []
            accepted_results: list[dict[str, Any]] = []
            open_questions: list[dict[str, Any]] = []
            required_context_gaps: list[dict[str, Any]] = []
            child_method_call_frames: list[dict[str, Any]] = []

            for child in children:
                summary = self._job_summary(connection, child)
                gaps = summary["required_context_gaps"]
                method_call_frames = summary["method_call_frames"]
                if method_call_frames:
                    child_method_call_frames.append(
                        {
                            "job_id": child["job_id"],
                            "method_call_frames": method_call_frames,
                        }
                    )
                if child["state"] not in TERMINAL_STATES:
                    unresolved_children.append(summary)
                if gaps:
                    required_context_gaps.append(
                        {"job_id": child["job_id"], "required_context_gaps": gaps}
                    )
                if child["state"] == STATE_ACCEPTED:
                    accepted_results.append(
                        {
                            "job_id": child["job_id"],
                            "result_appearance_id": child.get("result_appearance_id"),
                            "evidence_appearance_id": child.get("evidence_appearance_id"),
                        }
                    )
                    package = self._read_package_from_job(connection, child)
                    if package:
                        for question in package.get("open_questions", []):
                            open_questions.append({"job_id": child["job_id"], "question": question})

            return {
                "parent_job_id": job_id,
                "root_job_id": parent["root_job_id"],
                "ready_for_completion": bool(children) and not unresolved_children,
                "unresolved_children": unresolved_children,
                "accepted_results": accepted_results,
                "required_context_gaps": required_context_gaps,
                "open_questions": open_questions,
                "child_method_call_frames": child_method_call_frames,
            }

    def _read_package_from_job(
        self, connection: Any, job: dict[str, Any]
    ) -> dict[str, Any] | None:
        appearance_id = job.get("candidate_appearance_id") or job.get("result_appearance_id")
        if not appearance_id:
            return None
        appearance = self.runtime.repository.get_appearance(connection, str(appearance_id))
        if not appearance or not appearance.get("location"):
            return None
        location = str(appearance["location"])
        content_path = self.runtime.paths.resolve_runtime_location(location)
        if not content_path.exists():
            return None
        try:
            payload = json.loads(content_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None
        return payload if isinstance(payload, dict) else None

    def _job_summary(self, connection: Any, job: dict[str, Any]) -> dict[str, Any]:
        return {
            "job_id": job["job_id"],
            "parent_job_id": job.get("parent_job_id"),
            "root_job_id": job["root_job_id"],
            "state": job["state"],
            "target": job["target"],
            "acceptance_criteria": job.get("acceptance_criteria", ""),
            "required_context_gaps": decode_json(job.get("required_context_gaps"), []),
            "candidate_appearance_id": job.get("candidate_appearance_id"),
            "evidence_appearance_id": job.get("evidence_appearance_id"),
            "result_appearance_id": job.get("result_appearance_id"),
            "method_call_frames": self._method_call_frames_for_job(connection, str(job["job_id"])),
        }

    def _method_call_frames_for_job(self, connection: Any, job_id: str) -> list[dict[str, Any]]:
        return [
            event["payload"]
            for event in self.runtime.repository.list_events(connection, job_id)
            if event["event_type"] == EVENT_METHOD_CALL_FRAME_OPENED
        ]

    def _job_depth(self, connection: Any, job: dict[str, Any]) -> int:
        depth = 0
        current = job
        while current.get("parent_job_id"):
            parent_id = str(current["parent_job_id"])
            current = self.runtime.repository.require_job(connection, parent_id)
            depth += 1
        return depth

    @staticmethod
    def _validate_package(package: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(package, dict):
            raise GuardrailViolation("result package must be a JSON object")
        missing = [field for field in PACKAGE_REQUIRED_FIELDS if field not in package]
        if missing:
            raise GuardrailViolation(f"result package is missing fields: {', '.join(sorted(missing))}")
        for field in ("conclusion", "evidence_summary"):
            TreeService._require_text(field, str(package.get(field) or ""))
        for field in ("artifacts", "open_questions", "suggested_follow_up_jobs"):
            if not isinstance(package.get(field), list):
                raise GuardrailViolation(f"result package field must be a list: {field}")
        return package

    @staticmethod
    def _require_text(name: str, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise GuardrailViolation(f"{name} is required")
        return stripped

    @staticmethod
    def _normalize_text(value: str) -> str:
        return " ".join(value.casefold().split())
