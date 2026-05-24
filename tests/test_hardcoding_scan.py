from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.scan_hardcoding import scan


class HardcodingScanTest(unittest.TestCase):
    def test_scan_flags_mutable_job_contract_literals_in_generic_runtime(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            runner = root / "jingu" / "sandbox" / "runner.py"
            runner.parent.mkdir(parents=True)
            runner.write_text(
                "\n".join(
                    [
                        "def bad(service):",
                        "    service.create_child_job(",
                        "        parent_job_id='job_1',",
                        "        target='直接写死一个可变业务目标',",
                        "        acceptance_criteria='直接写死可变验收标准，后续业务变化必须改代码',",
                        "    )",
                    ]
                ),
                encoding="utf-8",
            )

            findings = scan(root)

            self.assertTrue(
                any(finding.kind == "mutable-contract-literal" for finding in findings)
            )

    def test_scan_allows_contract_values_loaded_from_owned_data(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            runner = root / "jingu" / "sandbox" / "runner.py"
            runner.parent.mkdir(parents=True)
            runner.write_text(
                "\n".join(
                    [
                        "CONTRACT_TARGET = load_contract().target",
                        "def good(service):",
                        "    service.create_child_job(",
                        "        parent_job_id='job_1',",
                        "        target=CONTRACT_TARGET,",
                        "        acceptance_criteria=load_contract().acceptance_criteria,",
                        "    )",
                    ]
                ),
                encoding="utf-8",
            )

            findings = scan(root)

            self.assertEqual(findings, [])


if __name__ == "__main__":
    unittest.main()
