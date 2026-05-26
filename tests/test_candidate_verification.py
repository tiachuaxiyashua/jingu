from __future__ import annotations

import unittest

from jingu.sandbox.verification import (
    build_text_delivery_ledger,
    extract_marker_regions,
    verify_candidate_text,
)


class CandidateVerificationTest(unittest.TestCase):
    def test_cjk_length_range_passes_inside_marker_region(self) -> None:
        body = "汉" * 5000
        report = verify_candidate_text(
            task_text="请输出4500-6000中文字符。",
            candidate_text=f"前置说明\n<<<正文开始>>>\n{body}\n<<<正文结束>>>\n附注",
        )

        self.assertEqual(report["overall_status"], "passed")
        selected_region = report["facts"]["selected_region"]
        self.assertEqual(selected_region["region_kind"], "marker_pair")
        self.assertEqual(selected_region["cjk_character_count"], 5000)
        length_checks = [
            check for check in report["checks"] if check["check_kind"] == "cjk_length_range"
        ]
        self.assertEqual(len(length_checks), 1)
        self.assertEqual(length_checks[0]["status"], "passed")
        self.assertEqual(length_checks[0]["actual_cjk_characters"], 5000)

    def test_cjk_length_range_fails_when_candidate_is_short(self) -> None:
        report = verify_candidate_text(
            task_text="请输出4500到6000汉字。",
            candidate_text="字" * 2600,
        )

        self.assertEqual(report["overall_status"], "failed")
        length_check = next(
            check for check in report["checks"] if check["check_kind"] == "cjk_length_range"
        )
        self.assertEqual(length_check["status"], "failed")
        self.assertEqual(length_check["actual_cjk_characters"], 2600)
        self.assertEqual(length_check["min_cjk_characters"], 4500)
        self.assertEqual(length_check["max_cjk_characters"], 6000)

    def test_cjk_length_range_supports_chinese_magnitude_units(self) -> None:
        report = verify_candidate_text(
            task_text="请输出10万字到20万字左右的完整正文。",
            candidate_text="字" * 11500,
        )

        length_check = next(
            check for check in report["checks"] if check["check_kind"] == "cjk_length_range"
        )
        self.assertEqual(length_check["status"], "failed")
        self.assertEqual(length_check["actual_cjk_characters"], 11500)
        self.assertEqual(length_check["min_cjk_characters"], 100000)
        self.assertEqual(length_check["max_cjk_characters"], 200000)

        ledger = build_text_delivery_ledger(
            task_text="请输出10万字到20万字左右的完整正文。",
            candidate_text="字" * 11500,
        )
        self.assertEqual(ledger["delivery_status"], "below_minimum")
        self.assertEqual(ledger["remaining_min_cjk_characters"], 88500)

    def test_delivery_ledger_counts_accepted_contributions_not_candidate_summary(self) -> None:
        ledger = build_text_delivery_ledger(
            task_text="请输出1万字到2万字的完整正文。",
            candidate_text="整合说明",
            accepted_delivery_contributions=[
                {
                    "source_job_id": "job_child",
                    "source_result_appearance_id": "appearance_child",
                    "contribution_id": "body_1",
                    "content": "字" * 3000,
                    "counts_toward_parent_delivery": True,
                    "evidence": "accepted body text",
                }
            ],
        )

        self.assertEqual(ledger["accounting_basis"], "accepted_delivery_contributions")
        self.assertEqual(ledger["actual_cjk_characters"], 3000)
        self.assertEqual(ledger["candidate_diagnostic_cjk_characters"], 4)
        self.assertEqual(ledger["remaining_min_cjk_characters"], 7000)
        self.assertEqual(
            ledger["accepted_delivery_contributions"][0]["source_result_appearance_id"],
            "appearance_child",
        )

    def test_delivery_ledger_excludes_support_material_contributions(self) -> None:
        ledger = build_text_delivery_ledger(
            task_text="请输出1万字到2万字的完整正文。",
            candidate_text="整合说明",
            accepted_delivery_contributions=[
                {
                    "source_job_id": "job_child",
                    "source_result_appearance_id": "appearance_child",
                    "contribution_id": "report",
                    "content": "这是很长的检查报告" * 100,
                    "counts_toward_parent_delivery": False,
                    "evidence": "support material only",
                },
                {
                    "source_job_id": "job_child",
                    "source_result_appearance_id": "appearance_child",
                    "contribution_id": "body",
                    "content": "字" * 1200,
                    "counts_toward_parent_delivery": True,
                    "evidence": "accepted body text",
                },
            ],
        )

        self.assertEqual(ledger["actual_cjk_characters"], 1200)
        self.assertEqual(len(ledger["accepted_delivery_contributions"]), 1)
        self.assertEqual(len(ledger["skipped_delivery_contributions"]), 1)

    def test_marker_extraction_is_based_on_generic_boundary_labels(self) -> None:
        regions = extract_marker_regions(
            "<<<交付物开始>>>\n可验证正文\n<<<交付物结束>>>\n"
            "<<<appendix>>>\n附录\n<<<appendix>>>"
        )

        self.assertEqual(len(regions), 2)
        self.assertEqual(regions[0].base_label, "交付物")
        self.assertEqual(regions[0].cjk_character_count, 5)
        self.assertEqual(regions[1].base_label, "appendix")

    def test_no_supported_constraint_records_unsupported_gap(self) -> None:
        report = verify_candidate_text(
            task_text="解释这个概念。",
            candidate_text="这是一个普通回答。",
        )

        self.assertEqual(report["overall_status"], "unsupported")
        self.assertEqual(report["checks"], [])
        self.assertIn("未提取到当前工具支持的确定性文本约束。", report["gaps"])

    def test_approximate_length_target_is_observed_but_not_auto_judged(self) -> None:
        report = verify_candidate_text(
            task_text="请写一篇大概5000字左右的文章。",
            candidate_text="字" * 2600,
        )

        self.assertEqual(report["overall_status"], "unsupported")
        observations = report["facts"]["observed_unbounded_length_targets"]
        self.assertEqual(len(observations), 1)
        self.assertEqual(observations[0]["target_cjk_characters"], 5000)
        self.assertEqual(observations[0]["actual_cjk_characters"], 2600)
        self.assertEqual(observations[0]["status"], "unsupported_without_explicit_bounds")
        self.assertIn("不自行假设容差", report["gaps"][0])


if __name__ == "__main__":
    unittest.main()
