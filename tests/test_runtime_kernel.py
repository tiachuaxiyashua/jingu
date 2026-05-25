from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from jingu.runtime.constants import (
    APPEARANCE_STATE_ACCEPTED,
    APPEARANCE_STATE_CANDIDATE,
    STATE_ACCEPTED,
    STATE_BLOCKED,
    STATE_READY,
    STATE_REVIEWING,
    STATE_RUNNING,
    STATE_WAITING_HUMAN,
)
from jingu.runtime.errors import GuardrailViolation, NotFoundError
from jingu.runtime.service import RuntimeService


ACCEPTANCE = "candidate has evidence and stays within this job scope"
EVIDENCE_METADATA = {
    "evidence_kind": "manual_test",
    "evidence_hardness": "manual",
}


class RuntimeKernelTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = TemporaryDirectory()
        self.workspace = Path(self.tmp.name)
        self.service = RuntimeService(self.workspace)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_initialize_is_idempotent(self) -> None:
        first = self.service.initialize()
        second = self.service.initialize()

        self.assertEqual(first["database_path"], second["database_path"])
        self.assertTrue(Path(first["database_path"]).exists())
        self.assertTrue(Path(first["object_store_root"]).exists())

    def test_root_job_preserves_original_wish_separately_from_target(self) -> None:
        job = self.service.create_root_job(wish="rough wish", target="clear target")

        self.assertEqual(job["state"], "draft")
        self.assertEqual(job["target"], "clear target")
        self.assertEqual(job["original_wish"]["summary"], "rough wish")
        self.assertNotEqual(job["original_wish"]["summary"], job["target"])

    def test_events_are_append_only_and_ordered(self) -> None:
        job = self.service.create_root_job(wish="wish", acceptance_criteria=ACCEPTANCE)
        job_id = job["job_id"]
        self.service.mark_ready(job_id)
        self.service.start_job(job_id)

        events = self.service.list_events(job_id)

        self.assertEqual(
            [event["event_type"] for event in events],
            ["root_job_created", "job_marked_ready", "job_started"],
        )
        self.assertEqual(events[0]["previous_checksum"], "")
        self.assertEqual(events[1]["previous_checksum"], events[0]["checksum"])
        self.assertEqual(events[2]["previous_checksum"], events[1]["checksum"])

    def test_ready_job_can_enter_running_when_context_is_complete(self) -> None:
        job = self.service.create_root_job(wish="wish", acceptance_criteria=ACCEPTANCE)
        self.service.mark_ready(job["job_id"])
        running = self.service.start_job(job["job_id"])

        self.assertEqual(running["state"], STATE_RUNNING)

    def test_readiness_requires_acceptance_criteria(self) -> None:
        job = self.service.create_root_job(wish="wish")
        before = len(self.service.list_events(job["job_id"]))

        with self.assertRaises(GuardrailViolation):
            self.service.mark_ready(job["job_id"])

        self.assertEqual(len(self.service.list_events(job["job_id"])), before)

    def test_readiness_is_blocked_when_required_context_has_gaps(self) -> None:
        job = self.service.create_root_job(
            wish="wish",
            acceptance_criteria=ACCEPTANCE,
            required_context_gaps=["missing source"],
        )
        before = len(self.service.list_events(job["job_id"]))

        with self.assertRaises(GuardrailViolation):
            self.service.mark_ready(job["job_id"])

        self.assertEqual(len(self.service.list_events(job["job_id"])), before)

    def test_candidate_remains_isolated_until_acceptance(self) -> None:
        job_id = self._running_job()
        result = self.service.submit_candidate(job_id, text="candidate body")
        status = self.service.get_status(job_id)

        self.assertEqual(status["state"], STATE_REVIEWING)
        self.assertIsNone(status["result_appearance_id"])
        self.assertEqual(result["candidate"]["state"], APPEARANCE_STATE_CANDIDATE)

    def test_acceptance_requires_evidence(self) -> None:
        job_id = self._running_job()
        candidate = self.service.submit_candidate(job_id, text="candidate body")["candidate"]
        before = len(self.service.list_events(job_id))

        with self.assertRaises(GuardrailViolation):
            self.service.accept_candidate(job_id, candidate_appearance_id=candidate["appearance_id"])

        self.assertEqual(len(self.service.list_events(job_id)), before)
        self.assertNotEqual(self.service.get_status(job_id)["state"], STATE_ACCEPTED)

    def test_evidence_requires_kind_and_hardness(self) -> None:
        job_id = self._running_job()
        before = len(self.service.list_events(job_id))

        with self.assertRaises(GuardrailViolation):
            self.service.submit_evidence(job_id, text="unclassified evidence")

        self.assertEqual(len(self.service.list_events(job_id)), before)

    def test_acceptance_marks_job_and_candidate_accepted(self) -> None:
        job_id = self._running_job()
        candidate = self.service.submit_candidate(job_id, text="candidate body")["candidate"]
        evidence = self.service.submit_evidence(
            job_id,
            text="evidence body",
            metadata=EVIDENCE_METADATA,
        )["evidence"]

        accepted = self.service.accept_candidate(
            job_id,
            candidate_appearance_id=candidate["appearance_id"],
            evidence_appearance_id=evidence["appearance_id"],
        )

        self.assertEqual(accepted["state"], STATE_ACCEPTED)
        self.assertEqual(accepted["result_appearance_id"], candidate["appearance_id"])
        self.assertEqual(accepted["result"]["state"], APPEARANCE_STATE_ACCEPTED)

    def test_terminal_job_rejects_late_evidence_rewrite(self) -> None:
        job_id = self._running_job()
        candidate = self.service.submit_candidate(job_id, text="candidate body")["candidate"]
        evidence = self.service.submit_evidence(
            job_id,
            text="evidence body",
            metadata=EVIDENCE_METADATA,
        )["evidence"]
        self.service.accept_candidate(
            job_id,
            candidate_appearance_id=candidate["appearance_id"],
            evidence_appearance_id=evidence["appearance_id"],
        )
        before = len(self.service.list_events(job_id))

        with self.assertRaises(GuardrailViolation):
            self.service.submit_evidence(
                job_id,
                text="late evidence",
                metadata=EVIDENCE_METADATA,
            )

        status = self.service.get_status(job_id)
        self.assertEqual(len(self.service.list_events(job_id)), before)
        self.assertEqual(status["evidence_appearance_id"], evidence["appearance_id"])

    def test_missing_job_operation_does_not_append_event(self) -> None:
        self.service.initialize()
        before = self._count_rows("events")

        with self.assertRaises(NotFoundError):
            self.service.submit_candidate("missing-job", text="candidate")

        self.assertEqual(self._count_rows("events"), before)
        self.assertEqual(self._count_rows("appearances"), 0)

    def test_repository_rejects_event_without_job(self) -> None:
        self.service.initialize()
        with self.service.repository.transaction() as connection:
            with self.assertRaises(NotFoundError):
                self.service.repository.append_event(
                    connection,
                    job_id="missing-job",
                    event_type="candidate_submitted",
                    payload={},
                )
            count = connection.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        self.assertEqual(count, 0)

    def test_child_job_cannot_complete_root_scope(self) -> None:
        root = self.service.create_root_job(wish="root wish")
        child = self.service.create_child_job(
            parent_job_id=root["job_id"],
            target="child target",
            acceptance_criteria=ACCEPTANCE,
        )
        self.service.mark_ready(child["job_id"])
        self.service.start_job(child["job_id"])
        candidate = self.service.submit_candidate(child["job_id"], text="candidate")["candidate"]
        evidence = self.service.submit_evidence(
            child["job_id"],
            text="evidence",
            metadata=EVIDENCE_METADATA,
        )["evidence"]
        before = len(self.service.list_events(child["job_id"]))

        with self.assertRaises(GuardrailViolation):
            self.service.accept_candidate(
                child["job_id"],
                candidate_appearance_id=candidate["appearance_id"],
                evidence_appearance_id=evidence["appearance_id"],
                completion_scope="root",
            )

        self.assertEqual(len(self.service.list_events(child["job_id"])), before)
        self.assertNotEqual(self.service.get_status(root["job_id"])["state"], STATE_ACCEPTED)

    def test_broken_appearance_reference_is_rejected(self) -> None:
        job_id = self._running_job()
        candidate = self.service.submit_candidate(job_id, text="candidate")["candidate"]
        evidence = self.service.submit_evidence(
            job_id,
            text="evidence",
            metadata=EVIDENCE_METADATA,
        )["evidence"]
        candidate_path = self.service.paths.resolve_runtime_location(candidate["location"])
        candidate_path.write_text("tampered", encoding="utf-8")
        before = len(self.service.list_events(job_id))

        with self.assertRaises(GuardrailViolation):
            self.service.accept_candidate(
                job_id,
                candidate_appearance_id=candidate["appearance_id"],
                evidence_appearance_id=evidence["appearance_id"],
            )

        self.assertEqual(len(self.service.list_events(job_id)), before)

    def test_cli_manual_happy_path(self) -> None:
        base = [sys.executable, "-m", "jingu.cli", "--workspace", str(self.workspace)]

        def run(*args: str) -> dict:
            completed = subprocess.run(
                [*base, *args],
                check=True,
                text=True,
                capture_output=True,
            )
            return json.loads(completed.stdout)

        run("init")
        root = run(
            "root",
            "create",
            "--wish",
            "wish",
            "--target",
            "target",
            "--acceptance-criteria",
            ACCEPTANCE,
        )
        job_id = root["job_id"]
        run("job", "ready", job_id)
        run("job", "run", job_id)
        candidate = run("candidate", "submit", job_id, "--text", "candidate")["candidate"]
        evidence = run(
            "evidence",
            "submit",
            job_id,
            "--text",
            "evidence",
            "--evidence-kind",
            "manual_test",
            "--evidence-hardness",
            "manual",
        )["evidence"]
        accepted = run(
            "accept",
            job_id,
            "--candidate",
            candidate["appearance_id"],
            "--evidence",
            evidence["appearance_id"],
        )
        events = run("events", job_id)

        self.assertEqual(accepted["state"], STATE_ACCEPTED)
        self.assertEqual(len(events), 6)

    def test_human_decision_return_is_recorded_as_evidence(self) -> None:
        root = self.service.create_root_job(wish="wish")
        decision_job = self.service.create_child_job(
            parent_job_id=root["job_id"],
            target="Clarify direction",
            acceptance_criteria="Record returned human decision.",
        )

        result = self.service.record_human_decision(
            decision_job["job_id"],
            decision_text="Use branch A and keep branch B as a fallback.",
        )
        events = self.service.list_events(decision_job["job_id"])
        event_types = [event["event_type"] for event in events]

        self.assertIn("human_decision_returned", event_types)
        self.assertEqual(
            result["decision_evidence"]["metadata"],
            json.dumps(
                {
                    "evidence_hardness": "human_decision",
                    "evidence_kind": "human_decision_return",
                    "size": len("Use branch A and keep branch B as a fallback.".encode("utf-8")),
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
        )

    def test_context_gap_resolution_clears_gaps_and_marks_ready(self) -> None:
        job = self.service.create_root_job(
            wish="wish",
            acceptance_criteria=ACCEPTANCE,
            required_context_gaps=["missing source", "missing threshold"],
        )
        blocked = self.service.mark_blocked(job["job_id"], reason="missing context")
        self.assertEqual(blocked["state"], STATE_BLOCKED)

        partial = self.service.resolve_context_gaps(
            job["job_id"],
            resolution_text="source is now attached",
            resolved_gaps=["missing source"],
        )
        self.assertEqual(partial["resolved_gaps"], ["missing source"])
        self.assertEqual(partial["remaining_gaps"], ["missing threshold"])
        self.assertEqual(partial["job"]["state"], STATE_BLOCKED)

        full = self.service.resolve_context_gaps(
            job["job_id"],
            resolution_text="threshold is now defined",
        )
        self.assertEqual(full["remaining_gaps"], [])
        self.assertEqual(full["job"]["state"], STATE_READY)
        event_types = [event["event_type"] for event in self.service.list_events(job["job_id"])]
        self.assertIn("context_gaps_resolved", event_types)
        self.assertEqual(event_types[-1], "job_marked_ready")

    def test_human_decision_return_moves_waiting_job_to_ready_when_no_gaps(self) -> None:
        root = self.service.create_root_job(wish="wish")
        decision_job = self.service.create_child_job(
            parent_job_id=root["job_id"],
            target="Clarify direction",
            acceptance_criteria=ACCEPTANCE,
        )
        waiting = self.service.mark_waiting_human(decision_job["job_id"], reason="needs owner")
        self.assertEqual(waiting["state"], STATE_WAITING_HUMAN)

        result = self.service.record_human_decision(
            decision_job["job_id"],
            decision_text="Use branch A.",
        )

        self.assertEqual(result["job"]["state"], STATE_READY)
        event_types = [event["event_type"] for event in self.service.list_events(decision_job["job_id"])]
        self.assertEqual(event_types[-1], "job_marked_ready")

    def _running_job(self) -> str:
        job = self.service.create_root_job(wish="wish", acceptance_criteria=ACCEPTANCE)
        self.service.mark_ready(job["job_id"])
        self.service.start_job(job["job_id"])
        return job["job_id"]

    def _count_rows(self, table: str) -> int:
        with self.service.repository.transaction() as connection:
            return int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


if __name__ == "__main__":
    unittest.main()
