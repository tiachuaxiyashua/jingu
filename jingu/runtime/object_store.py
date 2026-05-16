"""Filesystem object store for large appearance bodies."""

from __future__ import annotations

import hashlib
import shutil
from dataclasses import dataclass
from pathlib import Path

from jingu.runtime.paths import RuntimePaths


@dataclass(frozen=True)
class StoredObject:
    location: str
    checksum: str
    size: int


def checksum_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def checksum_text(content: str) -> str:
    return checksum_bytes(content.encode("utf-8"))


class ObjectStore:
    def __init__(self, paths: RuntimePaths) -> None:
        self.paths = paths

    def write_file(self, appearance_id: str, source: Path) -> StoredObject:
        source_path = Path(source)
        content = source_path.read_bytes()
        suffix = source_path.suffix
        target_dir = self.paths.object_store_root / appearance_id
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / f"content{suffix}"
        shutil.copyfile(source_path, target)
        return StoredObject(
            location=self.paths.relative_to_runtime(target),
            checksum=checksum_bytes(content),
            size=len(content),
        )

    def write_text(self, appearance_id: str, content: str, suffix: str = ".txt") -> StoredObject:
        encoded = content.encode("utf-8")
        target_dir = self.paths.object_store_root / appearance_id
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / f"content{suffix}"
        target.write_bytes(encoded)
        return StoredObject(
            location=self.paths.relative_to_runtime(target),
            checksum=checksum_bytes(encoded),
            size=len(encoded),
        )

    def verify(self, location: str, expected_checksum: str) -> bool:
        path = self.paths.resolve_runtime_location(location)
        if not path.exists() or not path.is_file():
            return False
        return checksum_bytes(path.read_bytes()) == expected_checksum
