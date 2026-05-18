"""Method source loading for sandbox AI task turns."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jingu.runtime.errors import JinguRuntimeError
from jingu.runtime.object_store import checksum_text


METHOD_POINTER_FILENAME = "jingu-method-source.txt"
MARKDOWN_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")


@dataclass(frozen=True)
class MethodLawFragment:
    fragment_id: str
    title: str
    heading_level: int
    order: int
    content: str
    checksum: str

    def log_fields(self) -> dict[str, str]:
        return {
            "method_law_id": self.fragment_id,
            "method_law_title": self.title,
            "method_law_level": str(self.heading_level),
            "method_law_order": str(self.order),
            "method_law_checksum": self.checksum,
            "method_law_content": self.content,
        }

    def binding_payload(self, *, method: "MethodContext") -> dict[str, Any]:
        return {
            "method_name": method.name,
            "method_path": str(method.path),
            "method_checksum": method.checksum,
            "method_law_id": self.fragment_id,
            "method_law_title": self.title,
            "method_law_level": self.heading_level,
            "method_law_order": self.order,
            "method_law_checksum": self.checksum,
            "content": self.content,
        }


@dataclass(frozen=True)
class MethodContext:
    name: str
    path: Path
    content: str
    checksum: str
    size: int
    fragments: tuple[MethodLawFragment, ...]

    def log_fields(self) -> dict[str, str]:
        return {
            "method_name": self.name,
            "method_path": str(self.path),
            "method_checksum": self.checksum,
            "method_size": str(self.size),
            "method_law_fragment_count": str(len(self.fragments)),
            "method_law_manifest": json.dumps(
                self.manifest(), ensure_ascii=False, sort_keys=True, indent=2
            ),
        }

    def manifest(self) -> dict[str, Any]:
        return {
            "method_name": self.name,
            "method_path": str(self.path),
            "method_checksum": self.checksum,
            "method_size": self.size,
            "method_law_fragment_count": len(self.fragments),
            "method_law_fragments": [
                {
                    "method_law_id": fragment.fragment_id,
                    "title": fragment.title,
                    "heading_level": fragment.heading_level,
                    "order": fragment.order,
                    "checksum": fragment.checksum,
                }
                for fragment in self.fragments
            ],
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
    fragments = parse_method_law_fragments(strip_frontmatter(content))
    return MethodContext(
        name=infer_method_name(content, path),
        path=path,
        content=content,
        checksum=checksum_text(content),
        size=len(content.encode("utf-8")),
        fragments=tuple(fragments),
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


def parse_method_law_fragments(content: str) -> list[MethodLawFragment]:
    lines = content.splitlines()
    sections: list[tuple[int, str, list[str]]] = []
    current_level = 0
    current_title = ""
    current_lines: list[str] = []

    for line in lines:
        heading = MARKDOWN_HEADING.match(line)
        if heading:
            if current_title or any(item.strip() for item in current_lines):
                sections.append((current_level, current_title, current_lines))
            current_level = len(heading.group(1))
            current_title = heading.group(2).strip()
            current_lines = [line]
            continue
        if current_title or line.strip():
            current_lines.append(line)

    if current_title or any(item.strip() for item in current_lines):
        sections.append((current_level, current_title, current_lines))

    if not sections:
        body = content.strip()
        return [build_method_law_fragment(order=1, heading_level=0, title="method-body", content=body)]

    fragments: list[MethodLawFragment] = []
    for order, (heading_level, title, section_lines) in enumerate(sections, start=1):
        body = "\n".join(section_lines).strip()
        if not body:
            continue
        fragments.append(
            build_method_law_fragment(
                order=order,
                heading_level=heading_level,
                title=title or "method-body",
                content=body,
            )
        )
    if not fragments:
        body = content.strip()
        return [build_method_law_fragment(order=1, heading_level=0, title="method-body", content=body)]
    return fragments


def strip_frontmatter(content: str) -> str:
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return content
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return "\n".join(lines[index + 1 :]).strip()
    return content


def build_method_law_fragment(
    *,
    order: int,
    heading_level: int,
    title: str,
    content: str,
) -> MethodLawFragment:
    digest = checksum_text(content)
    return MethodLawFragment(
        fragment_id=f"method_law_{order:03d}_{digest[:12]}",
        title=title,
        heading_level=heading_level,
        order=order,
        content=content,
        checksum=digest,
    )


def build_method_system_messages(method: MethodContext) -> list[dict[str, str]]:
    manifest = json.dumps(method.manifest(), ensure_ascii=False, sort_keys=True, indent=2)
    messages = [
        {
            "role": "system",
            "content": "\n".join(
                [
                    "Jingu method-law driven sandbox task.",
                    "Use the bound method-law fragments as the execution method for the user's task.",
                    "Treat each method_law_id as a separate 法相 bound to the current 业.",
                    "Preserve the user's original wish; produce a candidate result with evidence, gaps, and method-update observations when relevant.",
                    "Do not accept or reject the candidate, and do not edit the method file.",
                    "When describing method usage, reference the relevant method_law_id values.",
                    "Method manifest:",
                    manifest,
                ]
            ),
        }
    ]
    for fragment in method.fragments:
        messages.append(
            {
                "role": "system",
                "content": "\n".join(
                    [
                        "Jingu method-law fragment.",
                        f"Method name: {method.name}",
                        f"Method checksum: {method.checksum}",
                        f"Method law id: {fragment.fragment_id}",
                        f"Method law title: {fragment.title}",
                        f"Method law checksum: {fragment.checksum}",
                        "Method law content:",
                        fragment.content,
                    ]
                ),
            }
        )
    return messages


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
            "manifest": method.manifest(),
        },
        "user_input": user_input,
        "assistant_response": assistant_response,
        "requested_fields": [
            "method_use_summary",
            "method_law_trace",
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
                "record observations, method_law_id usage, and update candidates."
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
        "method_law_fragment_count": len(method.fragments),
        "method_law_fragment_ids": [fragment.fragment_id for fragment in method.fragments],
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
