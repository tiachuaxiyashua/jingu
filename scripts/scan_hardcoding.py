"""Scan runtime code for mutable truth hardcoded into generic code."""

from __future__ import annotations

import argparse
import ast
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


SCAN_DIRS = ("jingu", "scripts", "tests", "tools")
SKIP_DIRS = {".git", ".pytest_cache", "__pycache__", ".金箍", "openspec"}

SELF_PATH = Path("scripts/scan_hardcoding.py")

PATTERNS = (
    ("absolute-windows-path", re.compile(r"[A-Za-z]:[\\/][^'\"\s]+")),
    ("absolute-user-path", re.compile(r"/(?:Users|home|var|tmp)/[^\s'\"]+")),
    ("url-literal", re.compile(r"https?://[^\s'\"]+")),
    ("secret-looking-value", re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"][^'\"]+['\"]")),
    ("model-literal", re.compile(r"(?i)\b(gpt-\d|deepseek|claude-|gemini-|qwen)\b")),
)

MUTABLE_CONTRACT_CALLS = {
    "create_child_job",
    "create_running_child_job",
    "propose_child_job",
}

MUTABLE_CONTRACT_KEYWORDS = {
    "acceptance_criteria",
    "blocking_reason",
    "output_contract",
    "target",
}

MUTABLE_CONTRACT_FILES = {
    Path("jingu/sandbox/runner.py"),
    Path("jingu/runtime/tree.py"),
}

OWNED_PROTOCOL_LITERALS = {
    ".金箍",
    "运行态",
    "金箍运行库.sqlite",
    "果库",
    "draft",
    "ready",
    "running",
    "blocked",
    "reviewing",
    "accepted",
    "rejected",
    "waiting_human",
    "abandoned",
    "original_wish",
    "candidate_result",
    "evidence",
    "stable",
    "candidate",
    "root_job_created",
    "child_job_created",
    "job_marked_ready",
    "job_started",
    "candidate_submitted",
    "evidence_submitted",
    "candidate_accepted",
    "candidate_rejected",
    ".env.deepseek.local",
}


@dataclass(frozen=True)
class Finding:
    path: Path
    line: int
    kind: str
    value: str


def iter_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for scan_dir in SCAN_DIRS:
        base = root / scan_dir
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if any(part in SKIP_DIRS for part in path.parts):
                continue
            if path.as_posix().endswith(SELF_PATH.as_posix()):
                continue
            if path.suffix in {".py", ".js", ".html", ".css", ".toml", ".md"} and path.is_file():
                files.append(path)
    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        files.append(pyproject)
    return sorted(set(files))


def scan_python(path: Path) -> list[Finding]:
    source = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        return [Finding(path, exc.lineno or 1, "syntax-error", exc.msg)]

    findings: list[Finding] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            value = node.value
            if value in OWNED_PROTOCOL_LITERALS:
                continue
            findings.extend(match_value(path, node.lineno, value))
        if is_mutable_contract_file(path) and isinstance(node, ast.Call):
            findings.extend(scan_mutable_contract_call(path, node))
    return findings


def is_mutable_contract_file(path: Path) -> bool:
    normalized = Path(path.as_posix())
    return any(normalized.as_posix().endswith(item.as_posix()) for item in MUTABLE_CONTRACT_FILES)


def scan_mutable_contract_call(path: Path, node: ast.Call) -> list[Finding]:
    call_name = call_func_name(node.func)
    if call_name not in MUTABLE_CONTRACT_CALLS:
        return []
    findings: list[Finding] = []
    for keyword in node.keywords:
        if keyword.arg not in MUTABLE_CONTRACT_KEYWORDS:
            continue
        for literal in literal_segments(keyword.value):
            if looks_like_mutable_business_literal(literal):
                findings.append(
                    Finding(
                        path,
                        getattr(keyword.value, "lineno", node.lineno),
                        "mutable-contract-literal",
                        f"{keyword.arg}={literal}",
                    )
                )
    return findings


def call_func_name(func: ast.AST) -> str:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return ""


def literal_segments(node: ast.AST) -> Iterable[str]:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        yield node.value
        return
    if isinstance(node, ast.JoinedStr):
        for value in node.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                yield value.value


def looks_like_mutable_business_literal(value: str) -> bool:
    text = value.strip()
    if not text:
        return False
    if text in OWNED_PROTOCOL_LITERALS:
        return False
    if len(text) < 12 and cjk_count(text) < 6:
        return False
    if text.isidentifier():
        return False
    return any("\u4e00" <= char <= "\u9fff" for char in text) or " " in text


def cjk_count(value: str) -> int:
    return sum(1 for char in value if "\u4e00" <= char <= "\u9fff")


def scan_text(path: Path) -> list[Finding]:
    findings: list[Finding] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        findings.extend(match_value(path, line_number, line))
    return findings


def match_value(path: Path, line: int, value: str) -> list[Finding]:
    findings: list[Finding] = []
    for kind, pattern in PATTERNS:
        for match in pattern.finditer(value):
            findings.append(Finding(path, line, kind, match.group(0)))
    return findings


def scan(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for path in iter_files(root):
        if path.suffix == ".py":
            findings.extend(scan_python(path))
        else:
            findings.extend(scan_text(path))
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)

    findings = scan(args.root.resolve())
    if findings:
        for finding in findings:
            rel = finding.path.relative_to(args.root.resolve())
            print(f"{rel}:{finding.line}: {finding.kind}: {finding.value}")
        return 1

    print("No hardcoding findings detected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
