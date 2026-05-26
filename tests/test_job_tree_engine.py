from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from jingu.runtime.constants import STATE_ACCEPTED, STATE_REVIEWING
from jingu.runtime.errors import GuardrailViolation
from jingu.runtime.service import RuntimeService
from jingu.runtime.tree import TreeService


def package_payload(**overrides):
    payload = {
        "conclusion": "local result is usable",
        "artifacts": [{"kind": "text", "ref": "artifact-1"}],
        "delivery_contributions": [],
        "evidence_summary": "manual evidence was provided",
        "open_questions": [],
        "suggested_follow_up_jobs": [],
    }
    payload.update(overrides)
    return payload


def split_law(**overrides):
    law = {
        "blocks_parent_execution": True,
        "blocks_parent_acceptance": False,
        "needs_distinct_capability": False,
        "has_independent_result_package": True,
        "has_high_value_or_risk": False,
        "reason": "parent cannot continue without the child result package",
    }
    law.update(overrides)
    return law


def split_law_json(**overrides):
    return json.dumps(split_law(**overrides), ensure_ascii=False)


class JobTreeEngineTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = TemporaryDirectory()
        self.workspace = Path(self.tmp.name)
        self.runtime = RuntimeService(self.workspace)
        self.tree = TreeService(self.workspace)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_guarded_child_proposal_creates_real_child_job(self) -> None:
        root = self.runtime.create_root_job(wish="validate a method")

        result = self.tree.propose_child_job(
            parent_job_id=root["job_id"],
            target="check reusable inputs",
            blocking_reason="parent cannot validate without input inventory",
            output_contract="inventory with evidence",
            acceptance_criteria="inventory names every required input",
            estimated_effort=1,
            depth_limit=3,
            split_law=split_law(),
        )

        child = result["child"]
        self.assertEqual(child["parent_job_id"], root["job_id"])
        self.assertEqual(child["root_job_id"], root["job_id"])
        self.assertEqual(child["acceptance_criteria"], "inventory names every required input")
        self.assertEqual(result["proposal"]["split_law"]["law_name"], "分业判定律")
        self.assertTrue(result["proposal"]["split_law"]["blocks_parent_execution"])
        self.assertTrue(result["proposal"]["split_law"]["has_independent_result_package"])
        self.assertEqual(
            [event["event_type"] for event in self.runtime.list_events(root["job_id"])],
            ["root_job_created", "split_proposal_accepted"],
        )
        self.assertEqual(
            [event["event_type"] for event in self.runtime.list_events(child["job_id"])],
            ["child_job_created"],
        )

    def test_child_proposal_requires_explicit_split_law(self) -> None:
        root = self.runtime.create_root_job(wish="validate a method")

        with self.assertRaises(GuardrailViolation) as context:
            self.tree.propose_child_job(
                parent_job_id=root["job_id"],
                target="check reusable inputs",
                blocking_reason="parent cannot validate without input inventory",
                output_contract="inventory with evidence",
                acceptance_criteria="inventory names every required input",
                estimated_effort=1,
                depth_limit=3,
            )

        self.assertIn("split decision law is required", str(context.exception))
        self.assertEqual(len(self.tree.get_tree(root["job_id"])["jobs"]), 1)

    def test_vague_child_proposal_is_rejected_without_creating_child(self) -> None:
        root = self.runtime.create_root_job(wish="validate a method")

        with self.assertRaises(GuardrailViolation):
            self.tree.propose_child_job(
                parent_job_id=root["job_id"],
                target="check reusable inputs",
                blocking_reason="",
                output_contract="inventory",
                acceptance_criteria="complete enough",
                estimated_effort=1,
                depth_limit=2,
            )

        tree = self.tree.get_tree(root["job_id"])
        self.assertEqual(len(tree["jobs"]), 1)

    def test_split_decision_law_rejects_decorative_child(self) -> None:
        root = self.runtime.create_root_job(wish="validate a method")

        with self.assertRaises(GuardrailViolation) as context:
            self.tree.propose_child_job(
                parent_job_id=root["job_id"],
                target="name related concepts",
                blocking_reason="these concepts are interesting but not blocking",
                output_contract="concept list",
                acceptance_criteria="list exists",
                estimated_effort=1,
                depth_limit=2,
                split_law={
                    "blocks_parent_execution": False,
                    "blocks_parent_acceptance": False,
                    "needs_distinct_capability": False,
                    "has_independent_result_package": True,
                    "has_high_value_or_risk": False,
                    "reason": "all split triggers are false",
                },
            )

        self.assertIn("split decision law requires", str(context.exception))
        self.assertEqual(len(self.tree.get_tree(root["job_id"])["jobs"]), 1)

    def test_split_decision_law_rejects_child_without_independent_package(self) -> None:
        root = self.runtime.create_root_job(wish="validate a method")

        with self.assertRaises(GuardrailViolation) as context:
            self.tree.propose_child_job(
                parent_job_id=root["job_id"],
                target="mention a risk inline",
                blocking_reason="parent needs the risk noted",
                output_contract="inline note only",
                acceptance_criteria="note is present",
                estimated_effort=1,
                depth_limit=2,
                split_law={
                    "blocks_parent_execution": True,
                    "blocks_parent_acceptance": False,
                    "needs_distinct_capability": False,
                    "has_independent_result_package": False,
                    "has_high_value_or_risk": False,
                    "reason": "the result cannot be consumed as an independent package",
                },
            )

        self.assertIn("independent result package", str(context.exception))
        self.assertEqual(len(self.tree.get_tree(root["job_id"])["jobs"]), 1)

    def test_duplicate_sibling_target_is_rejected(self) -> None:
        root = self.runtime.create_root_job(wish="validate a method")
        kwargs = {
            "parent_job_id": root["job_id"],
            "target": "check reusable inputs",
            "blocking_reason": "parent cannot validate without input inventory",
            "output_contract": "inventory with evidence",
            "acceptance_criteria": "inventory names every required input",
            "estimated_effort": 1,
            "depth_limit": 3,
            "split_law": split_law(),
        }
        self.tree.propose_child_job(**kwargs)

        with self.assertRaises(GuardrailViolation):
            self.tree.propose_child_job(**{**kwargs, "target": "  CHECK reusable   inputs "})

        self.assertEqual(len(self.tree.get_tree(root["job_id"])["jobs"]), 2)

    def test_tree_projection_preserves_grandchild_hierarchy(self) -> None:
        root = self.runtime.create_root_job(wish="root")
        child = self._child(root["job_id"], "child")
        grandchild = self._child(child["job_id"], "grandchild")

        tree = self.tree.get_tree(grandchild["job_id"])
        links = {(link["parent_job_id"], link["child_job_id"]) for link in tree["links"]}

        self.assertIn((root["job_id"], child["job_id"]), links)
        self.assertIn((child["job_id"], grandchild["job_id"]), links)
        self.assertEqual(len(tree["jobs"]), 3)

    def test_frontier_returns_active_leaf_jobs_with_gaps(self) -> None:
        root = self.runtime.create_root_job(wish="root")
        active = self._child(root["job_id"], "active child", gaps=["missing source"])
        accepted = self._child(root["job_id"], "accepted child")
        self._accept_job(accepted["job_id"])

        frontier = self.tree.get_frontier(root["job_id"])["frontier"]

        self.assertEqual([job["job_id"] for job in frontier], [active["job_id"]])
        self.assertEqual(frontier[0]["required_context_gaps"], ["missing source"])

    def test_structured_package_submission_records_candidate_and_evidence(self) -> None:
        root = self.runtime.create_root_job(wish="root")
        child = self._child(root["job_id"], "child")
        self.runtime.mark_ready(child["job_id"])
        self.runtime.start_job(child["job_id"])

        result = self.tree.submit_result_package(child["job_id"], package=package_payload())

        self.assertEqual(result["job"]["state"], STATE_REVIEWING)
        self.assertEqual(result["candidate"]["appearance_type"], "candidate_result")
        self.assertEqual(result["evidence"]["appearance_type"], "evidence")
        self.assertEqual(
            [event["event_type"] for event in self.runtime.list_events(child["job_id"])],
            [
                "child_job_created",
                "job_marked_ready",
                "job_started",
                "candidate_submitted",
                "evidence_submitted",
                "result_package_submitted",
            ],
        )

    def test_incomplete_package_is_rejected_before_candidate_creation(self) -> None:
        root = self.runtime.create_root_job(wish="root")
        child = self._child(root["job_id"], "child")
        self.runtime.mark_ready(child["job_id"])
        self.runtime.start_job(child["job_id"])

        with self.assertRaises(GuardrailViolation):
            self.tree.submit_result_package(
                child["job_id"],
                package={"artifacts": [], "evidence_summary": "missing conclusion"},
            )

        self.assertEqual(self.runtime.get_status(child["job_id"])["state"], "running")

    def test_delivery_contribution_rejects_count_claim_without_matching_content(self) -> None:
        root = self.runtime.create_root_job(wish="root")
        child = self._child(root["job_id"], "child")
        self.runtime.mark_ready(child["job_id"])
        self.runtime.start_job(child["job_id"])

        with self.assertRaises(GuardrailViolation) as context:
            self.tree.submit_result_package(
                child["job_id"],
                package=package_payload(
                    delivery_contributions=[
                        {
                            "contribution_id": "chapter_1",
                            "content": "第一章完整正文，3000字。",
                            "counts_toward_parent_delivery": True,
                            "evidence": "经统计正文字数3000。",
                        }
                    ]
                ),
            )

        self.assertIn("shorter than its stated count", str(context.exception))
        self.assertEqual(self.runtime.get_status(child["job_id"])["state"], "running")

    def test_delivery_contribution_rejects_inflated_count_claim_near_real_run_gap(self) -> None:
        root = self.runtime.create_root_job(wish="root")
        child = self._child(root["job_id"], "child")
        self.runtime.mark_ready(child["job_id"])
        self.runtime.start_job(child["job_id"])

        with self.assertRaises(GuardrailViolation) as context:
            self.tree.submit_result_package(
                child["job_id"],
                package=package_payload(
                    delivery_contributions=[
                        {
                            "contribution_id": "chapter_2",
                            "content": "字" * 2678,
                            "counts_toward_parent_delivery": True,
                            "evidence": "本章正文字数3127字，可直接累加入父业。",
                        }
                    ]
                ),
            )

        self.assertIn("shorter than its stated count", str(context.exception))
        self.assertEqual(self.runtime.get_status(child["job_id"])["state"], "running")

    def test_parent_reevaluation_reports_unresolved_and_accepted_child_results(self) -> None:
        root = self.runtime.create_root_job(wish="root")
        unresolved = self._child(root["job_id"], "unresolved", gaps=["source"])
        accepted = self._child(root["job_id"], "accepted")
        self._accept_job(accepted["job_id"], package_payload(open_questions=["check scope"]))

        reevaluation = self.tree.reevaluate_parent(root["job_id"])

        self.assertFalse(reevaluation["ready_for_completion"])
        self.assertEqual([child["job_id"] for child in reevaluation["unresolved_children"]], [unresolved["job_id"]])
        self.assertEqual(reevaluation["accepted_results"][0]["job_id"], accepted["job_id"])
        self.assertEqual(reevaluation["open_questions"], [{"job_id": accepted["job_id"], "question": "check scope"}])

    def test_method_validation_is_represented_as_user_data_not_engine_behavior(self) -> None:
        root = self.runtime.create_root_job(
            wish="validate a user supplied method",
            target="validate method with a real tree",
            acceptance_criteria="method validation has child outputs and evidence",
        )
        child = self._child(root["job_id"], "validate method decomposition")
        self._accept_job(
            child["job_id"],
            package_payload(
                method_payload={
                    "method_name": "neidan-method",
                    "phase_names": ["reuse scan", "concept drilldown", "self validation"],
                }
            ),
        )

        tree = self.tree.get_tree(root["job_id"])
        reevaluation = self.tree.reevaluate_parent(root["job_id"])

        self.assertEqual(len(tree["jobs"]), 2)
        self.assertEqual(reevaluation["accepted_results"][0]["job_id"], child["job_id"])
        self.assertEqual(reevaluation["unresolved_children"], [])

    def test_child_proposal_can_bind_method_to_child_call_frame(self) -> None:
        method_path = self.workspace / "pdca.md"
        method_path.write_text(
            "---\nname: test-pdca\n---\n# PDCA\n\nUse Plan Do Check Act.",
            encoding="utf-8",
        )
        root = self.runtime.create_root_job(wish="write a story")

        result = self.tree.propose_child_job(
            parent_job_id=root["job_id"],
            target="make protagonist vivid",
            blocking_reason="parent cannot draft a strong story without a vivid protagonist",
            output_contract="protagonist card with measurable traits and evidence",
            acceptance_criteria="card lists traits, conflict, scene proof, and open risks",
            estimated_effort=2,
            depth_limit=4,
            method_path=method_path,
            method_binding_reason="this child needs iterative Plan Do Check Act refinement",
            method_return_point="return the protagonist card to the parent story plan",
            split_law=split_law(needs_distinct_capability=True),
        )

        child = result["child"]
        tree = self.tree.get_tree(root["job_id"])
        parent_summary = next(job for job in tree["jobs"] if job["job_id"] == root["job_id"])
        child_summary = next(job for job in tree["jobs"] if job["job_id"] == child["job_id"])
        reevaluation = self.tree.reevaluate_parent(root["job_id"])
        child_events = [event["event_type"] for event in self.runtime.list_events(child["job_id"])]
        parent_events = [event["event_type"] for event in self.runtime.list_events(root["job_id"])]

        self.assertEqual(parent_summary["method_call_frames"], [])
        self.assertEqual(len(child_summary["method_call_frames"]), 1)
        self.assertEqual(child_summary["method_call_frames"][0]["method_name"], "test-pdca")
        self.assertEqual(
            child_summary["method_call_frames"][0]["return_point"],
            "return the protagonist card to the parent story plan",
        )
        self.assertIn("method_law_bound", child_events)
        self.assertIn("method_call_frame_opened", child_events)
        self.assertNotIn("method_call_frame_opened", parent_events)
        self.assertEqual(
            reevaluation["child_method_call_frames"][0]["job_id"],
            child["job_id"],
        )
        self.assertEqual(result["method_binding"]["method_call_frame"]["method_name"], "test-pdca")

    def test_incomplete_method_binding_is_rejected_before_child_creation(self) -> None:
        method_path = self.workspace / "pdca.md"
        method_path.write_text(
            "---\nname: test-pdca\n---\n# PDCA\n\nUse Plan Do Check Act.",
            encoding="utf-8",
        )
        root = self.runtime.create_root_job(wish="write a story")

        with self.assertRaises(GuardrailViolation):
            self.tree.propose_child_job(
                parent_job_id=root["job_id"],
                target="make protagonist vivid",
                blocking_reason="parent cannot draft a strong story without a vivid protagonist",
                output_contract="protagonist card with evidence",
                acceptance_criteria="card lists traits",
                estimated_effort=1,
                depth_limit=4,
                method_path=method_path,
                method_return_point="return to parent",
                split_law=split_law(needs_distinct_capability=True),
            )

        self.assertEqual(len(self.tree.get_tree(root["job_id"])["jobs"]), 1)

    def test_cli_manual_tree_workflow(self) -> None:
        base = [sys.executable, "-m", "jingu.cli", "--workspace", str(self.workspace)]

        def run(*args: str) -> dict:
            completed = subprocess.run(
                [*base, *args],
                check=True,
                text=True,
                capture_output=True,
            )
            return json.loads(completed.stdout)

        package_path = self.workspace / "package.json"
        package_path.write_bytes(
            b"\xef\xbb\xbf" + json.dumps(package_payload(), ensure_ascii=False).encode("utf-8")
        )

        root = run("root", "create", "--wish", "wish", "--target", "target")
        child = run(
            "tree",
            "propose-child",
            root["job_id"],
            "--target",
            "child target",
            "--blocking-reason",
            "parent needs child output",
            "--output-contract",
            "structured child package",
            "--acceptance-criteria",
            "package has evidence",
            "--estimated-effort",
            "1",
            "--depth-limit",
            "3",
            "--split-law-json",
            split_law_json(),
        )["child"]
        run("job", "ready", child["job_id"])
        run("job", "run", child["job_id"])
        package_result = run("tree", "submit-package", child["job_id"], "--file", str(package_path))
        tree = run("tree", "show", root["job_id"])
        frontier = run("tree", "frontier", root["job_id"])

        self.assertEqual(package_result["job"]["state"], STATE_REVIEWING)
        self.assertEqual(len(tree["jobs"]), 2)
        self.assertEqual(frontier["frontier"][0]["job_id"], child["job_id"])

    def test_cli_propose_child_requires_explicit_split_law(self) -> None:
        base = [sys.executable, "-m", "jingu.cli", "--workspace", str(self.workspace)]
        root = subprocess.run(
            [*base, "root", "create", "--wish", "wish", "--target", "target"],
            check=True,
            text=True,
            capture_output=True,
        )
        root_job_id = json.loads(root.stdout)["job_id"]

        completed = subprocess.run(
            [
                *base,
                "tree",
                "propose-child",
                root_job_id,
                "--target",
                "child target",
                "--blocking-reason",
                "parent needs child output",
                "--output-contract",
                "structured child package",
                "--acceptance-criteria",
                "package has evidence",
                "--estimated-effort",
                "1",
                "--depth-limit",
                "3",
            ],
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(completed.returncode, 1)
        self.assertIn("explicit split decision law", completed.stdout)

    def test_cli_child_method_binding_workflow(self) -> None:
        base = [sys.executable, "-m", "jingu.cli", "--workspace", str(self.workspace)]

        def run(*args: str) -> dict:
            completed = subprocess.run(
                [*base, *args],
                check=True,
                text=True,
                capture_output=True,
            )
            return json.loads(completed.stdout)

        method_path = self.workspace / "dialectical.md"
        method_path.write_text(
            "---\nname: test-dialectical\n---\n# Dialectic\n\nFind contradiction.",
            encoding="utf-8",
        )

        root = run("root", "create", "--wish", "wish", "--target", "target")
        child = run(
            "tree",
            "propose-child",
            root["job_id"],
            "--target",
            "analyze tension",
            "--blocking-reason",
            "parent needs contradiction analysis",
            "--output-contract",
            "contradiction table",
            "--acceptance-criteria",
            "table separates facts from value decisions",
            "--estimated-effort",
            "1",
            "--depth-limit",
            "3",
            "--method",
            str(method_path),
            "--method-reason",
            "this child needs contradiction analysis",
            "--method-return-point",
            "return contradiction table to parent",
            "--split-law-json",
            split_law_json(needs_distinct_capability=True),
        )["child"]
        tree = run("tree", "show", root["job_id"])
        child_summary = next(job for job in tree["jobs"] if job["job_id"] == child["job_id"])

        self.assertEqual(child_summary["method_call_frames"][0]["method_name"], "test-dialectical")
        self.assertEqual(child_summary["method_call_frames"][0]["output_contract"], "contradiction table")

    def _child(self, parent_job_id: str, target: str, gaps: list[str] | None = None) -> dict:
        return self.tree.propose_child_job(
            parent_job_id=parent_job_id,
            target=target,
            blocking_reason=f"{target} blocks the parent",
            output_contract=f"{target} produces a structured package",
            acceptance_criteria=f"{target} has evidence",
            estimated_effort=1,
            depth_limit=4,
            required_context_gaps=gaps,
            split_law=split_law(needs_distinct_capability=bool(gaps)),
        )["child"]

    def _accept_job(self, job_id: str, package: dict | None = None) -> dict:
        self.runtime.mark_ready(job_id)
        self.runtime.start_job(job_id)
        package_result = self.tree.submit_result_package(
            job_id,
            package=package or package_payload(),
        )
        accepted = self.runtime.accept_candidate(
            job_id,
            candidate_appearance_id=package_result["candidate"]["appearance_id"],
            evidence_appearance_id=package_result["evidence"]["appearance_id"],
        )
        self.assertEqual(accepted["state"], STATE_ACCEPTED)
        return accepted


if __name__ == "__main__":
    unittest.main()
