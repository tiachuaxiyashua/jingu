"""Runtime path resolution."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from jingu.runtime.constants import DATABASE_FILENAME, OBJECT_STORE_DIR, RUNTIME_DIR, RUNTIME_STATE_DIR


@dataclass(frozen=True)
class RuntimePaths:
    workspace: Path
    runtime_root: Path
    database_path: Path
    object_store_root: Path

    @classmethod
    def resolve(cls, workspace: Path | str) -> "RuntimePaths":
        root = Path(workspace).resolve()
        runtime_root = root / RUNTIME_DIR / RUNTIME_STATE_DIR
        return cls(
            workspace=root,
            runtime_root=runtime_root,
            database_path=runtime_root / DATABASE_FILENAME,
            object_store_root=runtime_root / OBJECT_STORE_DIR,
        )

    def initialize(self) -> None:
        self.runtime_root.mkdir(parents=True, exist_ok=True)
        self.object_store_root.mkdir(parents=True, exist_ok=True)

    def relative_to_runtime(self, path: Path) -> str:
        return path.resolve().relative_to(self.runtime_root.resolve()).as_posix()

    def resolve_runtime_location(self, location: str) -> Path:
        return self.runtime_root / location
