from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from jingu.runtime.errors import JinguRuntimeError
from jingu.sandbox.safety import (
    destroy_sandbox_directory,
    prepare_sandbox_directory,
)


class SandboxSafetyTest(unittest.TestCase):
    def test_unmarked_non_empty_sandbox_is_not_deleted(self) -> None:
        with TemporaryDirectory() as tmp:
            sandbox = Path(tmp) / "sandbox"
            sandbox.mkdir()
            protected = sandbox / "keep.txt"
            protected.write_text("do not delete", encoding="utf-8")

            with self.assertRaises(JinguRuntimeError):
                prepare_sandbox_directory(sandbox, log_dir=Path(tmp) / "logs")

            self.assertEqual(protected.read_text(encoding="utf-8"), "do not delete")

    def test_marked_sandbox_can_be_destroyed(self) -> None:
        with TemporaryDirectory() as tmp:
            sandbox = Path(tmp) / "sandbox"
            prepare_sandbox_directory(sandbox, log_dir=Path(tmp) / "logs")
            (sandbox / "runtime.txt").write_text("temporary", encoding="utf-8")

            destroy_sandbox_directory(sandbox)

            self.assertFalse(sandbox.exists())

    def test_log_directory_cannot_be_inside_sandbox(self) -> None:
        with TemporaryDirectory() as tmp:
            sandbox = Path(tmp) / "sandbox"
            log_dir = sandbox / "logs"

            with self.assertRaises(JinguRuntimeError):
                prepare_sandbox_directory(sandbox, log_dir=log_dir)


if __name__ == "__main__":
    unittest.main()
