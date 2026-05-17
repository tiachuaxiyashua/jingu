"""Method source loading for sandbox AI task turns."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from jingu.runtime.errors import JinguRuntimeError
from jingu.runtime.object_store import checksum_text


METHOD_POINTER_FILENAME = "jingu-method-source.txt"


@dataclass(frozen=True)
class MethodContext:
    name: str
    path: Path
    content: str
    checksum: str
    size: int

    def log_fields(self) -> dict[str, str]:
        return {
            "method_name": self.name,
            "method_path": str(self.path),
            "method_checksum": self.checksum,
            "method_size": str(self.size),
            "method_content": self.content,
        }


def load_method_context(
    *,
    method_path: Path | str | None = None,
    pointer_path: Path | str | None = None,
    workspace: Path | str | None = None,
) -> MethodContext:
    path = resolve_method_path(
        method_path=method_path,
        pointer_path=pointer_path,
        workspace=workspace,
    )
    try:
        content = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise JinguRuntimeError(f"method source could not be read: {path}") from exc
    if not content.strip():
        raise JinguRuntimeError(f"method source is empty: {path}")
    return MethodContext(
        name=infer_method_name(content, path),
        path=path,
        content=content,
        checksum=checksum_text(content),
        size=len(content.encode("utf-8")),
    )


def resolve_method_path(
    *,
    method_path: Path | str | None = None,
    pointer_path: Path | str | None = None,
    workspace: Path | str | None = None,
) -> Path:
    base = Path(workspace).resolve() if workspace is not None else Path.cwd().resolve()
    if method_path is not None:
        return require_file(resolve_relative(Path(method_path), base), "method source")

    pointer = resolve_relative(Path(pointer_path), base) if pointer_path is not None else base / METHOD_POINTER_FILENAME
    if not pointer.exists():
        raise JinguRuntimeError(
            f"method source is not configured: pass --method or create {pointer}"
        )
    if not pointer.is_file():
        raise JinguRuntimeError(f"method pointer is not a file: {pointer}")

    raw_target = read_pointer_target(pointer)
    target = resolve_relative(Path(raw_target), pointer.parent)
    return require_file(target, "method source")


def read_pointer_target(pointer: Path) -> str:
    try:
        lines = pointer.read_text(encoding="utf-8-sig").splitlines()
    except OSError as exc:
        raise JinguRuntimeError(f"method pointer could not be read: {pointer}") from exc
    for raw_line in lines:
        line = raw_line.strip()
        if line and not line.startswith("#"):
            return line
    raise JinguRuntimeError(f"method pointer does not contain a method path: {pointer}")


def build_method_system_message(method: MethodContext) -> dict[str, str]:
    content = "\n".join(
        [
            "Jingu method-driven sandbox task.",
            "Use the loaded method as the execution method for the user's task.",
            "Preserve the user's original wish; produce a candidate result with evidence, gaps, and method-update observations when relevant.",
            "Do not accept or reject the candidate, and do not edit the method file.",
            f"Method name: {method.name}",
            f"Method source path: {method.path}",
            f"Method checksum: {method.checksum}",
            "Method content:",
            method.content,
        ]
    )
    return {"role": "system", "content": content}


def build_method_review_messages(
    *,
    method: MethodContext,
    user_input: str,
    assistant_response: str,
) -> list[dict[str, str]]:
    review_request = {
        "method": {
            "name": method.name,
            "path": str(method.path),
            "checksum": method.checksum,
        },
        "user_input": user_input,
        "assistant_response": assistant_response,
        "requested_fields": [
            "method_use_summary",
            "evidence",
            "gaps",
            "observed_failure_modes",
            "method_update_candidates",
        ],
    }
    return [
        {
            "role": "system",
            "content": (
                "Review the latest candidate against the loaded method. "
                "Return JSON only. Do not accept, reject, or mutate any method; "
                "record observations and update candidates."
            ),
        },
        {"role": "user", "content": json.dumps(review_request, ensure_ascii=False, sort_keys=True)},
    ]


def method_evidence_payload(
    *,
    method: MethodContext,
    review: str,
) -> str:
    payload = {
        "evidence_kind": "method_driven_provider_response",
        "method_name": method.name,
        "method_path": str(method.path),
        "method_checksum": method.checksum,
        "provider_response_received": True,
        "method_self_review": review,
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def infer_method_name(content: str, path: Path) -> str:
    in_frontmatter = False
    for index, raw_line in enumerate(content.splitlines()[:20]):
        line = raw_line.strip()
        if index == 0 and line == "---":
            in_frontmatter = True
            continue
        if in_frontmatter and line == "---":
            break
        if line.startswith("name:"):
            name = line.split(":", 1)[1].strip()
            if name:
                return name
    return path.stem


def resolve_relative(path: Path, base: Path) -> Path:
    return path.resolve() if path.is_absolute() else (base / path).resolve()


def require_file(path: Path, label: str) -> Path:
    if not path.exists():
        raise JinguRuntimeError(f"{label} not found: {path}")
    if not path.is_file():
        raise JinguRuntimeError(f"{label} is not a file: {path}")
    return path
