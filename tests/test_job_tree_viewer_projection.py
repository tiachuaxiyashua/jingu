from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


class JobTreeViewerProjectionTest(unittest.TestCase):
    def test_viewer_projects_step_io_child_review_and_parent_integration(self) -> None:
        with TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "trace.jsonl"
            events = [
                {
                    "event_type": "root_job_created",
                    "message": "root job created",
                    "timestamp": "2026-05-23T00:00:00Z",
                    "data": {"job_id": "job_root"},
                },
                {
                    "event_type": "child_package_review_requested",
                    "message": "child package review requested",
                    "timestamp": "2026-05-23T00:00:01Z",
                    "data": {
                        "job_id": "job_child",
                        "parent_job_id": "job_root",
                        "child_job_id": "job_child",
                        "child_package_review_prompt": json.dumps(
                            {"child_result_package": {"package": {"conclusion": "局部果"}}},
                            ensure_ascii=False,
                        ),
                    },
                },
                {
                    "event_type": "child_package_review_received",
                    "message": "child package review received",
                    "timestamp": "2026-05-23T00:00:02Z",
                    "data": {
                        "job_id": "job_child",
                        "parent_job_id": "job_root",
                        "child_job_id": "job_child",
                        "child_package_review_judgment": json.dumps(
                            {"review_action": "accept", "evidence": ["可消费"]},
                            ensure_ascii=False,
                        ),
                    },
                },
                {
                    "event_type": "parent_integration_requested",
                    "message": "parent integration requested",
                    "timestamp": "2026-05-23T00:00:03Z",
                    "data": {
                        "job_id": "job_root",
                        "parent_job_id": "job_root",
                        "parent_integration_prompt": json.dumps(
                            {"accepted_child_packages": [{"job_id": "job_child"}]},
                            ensure_ascii=False,
                        ),
                    },
                },
                {
                    "event_type": "parent_integration_candidate_submitted",
                    "message": "parent integration candidate submitted",
                    "timestamp": "2026-05-23T00:00:04Z",
                    "data": {
                        "job_id": "job_root",
                        "parent_job_id": "job_root",
                        "parent_integration_status": "integrated",
                        "parent_integration_candidate": "整合后的父业候选",
                        "parent_integration_candidate_appearance_id": "appearance_candidate",
                        "parent_integration_evidence": "整合证据",
                        "parent_integration_evidence_appearance_id": "appearance_evidence",
                    },
                },
                {
                    "event_type": "run_finished",
                    "message": "run finished",
                    "timestamp": "2026-05-23T00:00:05Z",
                    "data": {"job_id": "job_root"},
                },
                {
                    "event_type": "sandbox_destroyed",
                    "message": "sandbox destroyed",
                    "timestamp": "2026-05-23T00:00:06Z",
                    "data": {"sandbox_path": "sandbox"},
                },
            ]
            log_path.write_text(
                "\n".join(json.dumps(event, ensure_ascii=False) for event in events),
                encoding="utf-8",
            )

            completed = subprocess.run(
                [
                    "node",
                    "scripts/validate_job_tree_viewer.js",
                    "--expect-child-review",
                    str(log_path),
                    "--expect-parent-integration",
                    str(log_path),
                    "--expect-closure",
                    str(log_path),
                ],
                cwd=Path(__file__).resolve().parents[1],
                text=True,
                encoding="utf-8",
                capture_output=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)


if __name__ == "__main__":
    unittest.main()
