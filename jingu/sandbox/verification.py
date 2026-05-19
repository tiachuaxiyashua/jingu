"""Deterministic candidate verification for sandbox runs."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from typing import Any


CJK_CHARACTER = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
MARKER_PATTERN = re.compile(r"<<<\s*(?P<label>[^<>\r\n]{1,120}?)\s*>>>")
TEXT_UNIT = r"(?:中文字符|中文字|汉字|中文|字)"
RANGE_SEPARATOR = r"(?:-|~|至|到|—|–)"
RANGE_PATTERNS = (
    re.compile(
        rf"(?P<min>\d{{2,7}})\s*{RANGE_SEPARATOR}\s*(?P<max>\d{{2,7}})\s*(?P<unit>{TEXT_UNIT})"
    ),
    re.compile(
        rf"(?P<unit>{TEXT_UNIT})\s*(?P<min>\d{{2,7}})\s*{RANGE_SEPARATOR}\s*(?P<max>\d{{2,7}})"
    ),
)
MIN_PATTERNS = (
    re.compile(rf"(?:至少|不少于|不低于|大于等于)\s*(?P<min>\d{{2,7}})\s*(?P<unit>{TEXT_UNIT})"),
    re.compile(rf"(?P<min>\d{{2,7}})\s*(?P<unit>{TEXT_UNIT})\s*(?:以上|起)"),
)
MAX_PATTERNS = (
    re.compile(rf"(?:最多|不超过|不高于|小于等于)\s*(?P<max>\d{{2,7}})\s*(?P<unit>{TEXT_UNIT})"),
    re.compile(rf"(?P<max>\d{{2,7}})\s*(?P<unit>{TEXT_UNIT})\s*(?:以内|以下)"),
)
TARGET_PATTERN = re.compile(
    rf"(?P<prefix>大概|大约|约|约莫|接近)?\s*"
    rf"(?P<target>\d{{2,7}})\s*(?P<unit>{TEXT_UNIT})\s*"
    rf"(?P<suffix>左右|上下|附近|大概|大约|约)?"
)
INCOMPLETE_SIGNAL_PATTERNS = (
    re.compile(r"(?:此处|这里|以下|中间).{0,12}(?:省略|略去)"),
    re.compile(r"(?:省略|略去).{0,12}(?:部分|内容|正文|后续)"),
    re.compile(r"(?:待补充|稍后补充|后续补充|未完待续)"),
    re.compile(r"因篇幅(?:限制|原因)"),
    re.compile(r"(?i)(?:omitted for brevity|content omitted|to be continued|todo)"),
)


@dataclass(frozen=True)
class Marker:
    label: str
    start: int
    end: int
    role: str
    base_label: str


@dataclass(frozen=True)
class MarkerRegion:
    start_label: str
    end_label: str
    base_label: str
    content_start: int
    content_end: int
    character_count: int
    cjk_character_count: int


@dataclass(frozen=True)
class LengthConstraint:
    constraint_kind: str
    min_cjk_characters: int | None
    max_cjk_characters: int | None
    source_text: str
    source_start: int
    source_end: int
    unit: str


def verify_candidate_text(
    *,
    task_text: str,
    candidate_text: str,
    candidate_appearance_id: str | None = None,
) -> dict[str, Any]:
    """Verify deterministic text constraints that can be extracted without AI judgment."""

    marker_pairs = extract_marker_regions(candidate_text)
    selected_region = select_count_region(candidate_text, marker_pairs)
    region_text = selected_region["text"]
    actual_cjk_count = count_cjk_characters(region_text)
    constraints = extract_cjk_length_constraints(task_text)
    target_observations = observe_unbounded_length_targets(
        task_text=task_text,
        occupied_spans=[(item.source_start, item.source_end) for item in constraints],
        actual_cjk_count=actual_cjk_count,
    )
    incomplete_signals = find_incomplete_signals(candidate_text)
    checks: list[dict[str, Any]] = []

    if marker_pairs:
        checks.append(
            {
                "check_id": "marker_region_1",
                "check_kind": "marker_delimited_region",
                "status": "passed",
                "fact": "候选结果包含可配对的通用边界标记。",
                "used_region": selected_region_without_text(selected_region),
            }
        )

    for index, constraint in enumerate(constraints, start=1):
        checks.append(build_length_check(index, constraint, actual_cjk_count, selected_region))

    if incomplete_signals:
        checks.append(
            {
                "check_id": "incomplete_output_signal_1",
                "check_kind": "incomplete_output_signal",
                "status": "failed",
                "fact": "候选结果包含显式未完成或省略信号。",
                "signals": incomplete_signals,
            }
        )

    gaps: list[str] = []
    if target_observations:
        gaps.append("任务包含没有明确上下界的长度目标；校验器记录实际计数，但不自行假设容差。")
    if not checks:
        gaps.append("未提取到当前工具支持的确定性文本约束。")

    overall_status = summarize_overall_status(checks)
    if overall_status == "passed" and target_observations and not constraints:
        overall_status = "unsupported"

    return {
        "evidence_kind": "candidate_verification_report",
        "verification_kind": "deterministic_text_constraints",
        "overall_status": overall_status,
        "candidate_appearance_id": candidate_appearance_id,
        "facts": {
            "task_character_count": len(task_text),
            "candidate_character_count": len(candidate_text),
            "candidate_total_cjk_character_count": count_cjk_characters(candidate_text),
            "selected_region": selected_region_without_text(selected_region),
            "detected_marker_pairs": [asdict(region) for region in marker_pairs],
            "observed_unbounded_length_targets": target_observations,
        },
        "assumptions": [
            "只对任务文本中能解析出明确上下界或单边界的中文长度约束作通过/失败判断。",
            "若候选结果含完整边界标记，长度计数使用第一个完整标记区域；否则使用完整候选文本。",
        ],
        "inferences": [
            "同一候选的文学质量、平台传播性、价值取向不属于本确定性校验器的判断范围。",
        ],
        "logic_chain": [
            "读取任务文本，提取中文长度范围或单边界约束。",
            "读取候选文本，定位可配对边界标记并选择计数区域。",
            "统计计数区域内实际 CJK 字符数。",
            "用实际计数逐条比对可执行约束，并记录无法自动判定的缺口。",
        ],
        "checks": checks,
        "gaps": gaps,
    }


def build_parent_verification_evidence(
    *,
    report: dict[str, Any],
    verification_job_id: str,
    verification_candidate_appearance_id: str,
    verification_evidence_appearance_id: str,
    parent_candidate_appearance_id: str,
) -> str:
    checks = report.get("checks") or []
    compact_checks = [
        {
            "check_id": check.get("check_id"),
            "check_kind": check.get("check_kind"),
            "status": check.get("status"),
            "actual_cjk_characters": check.get("actual_cjk_characters"),
            "min_cjk_characters": check.get("min_cjk_characters"),
            "max_cjk_characters": check.get("max_cjk_characters"),
        }
        for check in checks
    ]
    payload = {
        "evidence_kind": "candidate_verification_summary",
        "verification_kind": report.get("verification_kind"),
        "overall_status": report.get("overall_status"),
        "verification_job_id": verification_job_id,
        "parent_candidate_appearance_id": parent_candidate_appearance_id,
        "verification_candidate_appearance_id": verification_candidate_appearance_id,
        "verification_evidence_appearance_id": verification_evidence_appearance_id,
        "selected_region": (report.get("facts") or {}).get("selected_region"),
        "checks": compact_checks,
        "gaps": report.get("gaps") or [],
        "does_not_auto_accept_or_reject": True,
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def verification_report_to_json(report: dict[str, Any]) -> str:
    return json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2)


def extract_marker_regions(candidate_text: str) -> list[MarkerRegion]:
    markers = [build_marker(match) for match in MARKER_PATTERN.finditer(candidate_text)]
    regions: list[MarkerRegion] = []
    used_end_indexes: set[int] = set()
    for start_index, start_marker in enumerate(markers):
        if start_marker.role not in {"start", "boundary"}:
            continue
        for end_index in range(start_index + 1, len(markers)):
            if end_index in used_end_indexes:
                continue
            end_marker = markers[end_index]
            if markers_form_pair(start_marker, end_marker):
                used_end_indexes.add(end_index)
                content = candidate_text[start_marker.end : end_marker.start]
                regions.append(
                    MarkerRegion(
                        start_label=start_marker.label,
                        end_label=end_marker.label,
                        base_label=start_marker.base_label,
                        content_start=start_marker.end,
                        content_end=end_marker.start,
                        character_count=len(content),
                        cjk_character_count=count_cjk_characters(content),
                    )
                )
                break
    return regions


def extract_cjk_length_constraints(task_text: str) -> list[LengthConstraint]:
    constraints: list[LengthConstraint] = []
    occupied: list[tuple[int, int]] = []
    for pattern in RANGE_PATTERNS:
        for match in pattern.finditer(task_text):
            if overlaps_existing(match.span(), occupied):
                continue
            minimum = int(match.group("min"))
            maximum = int(match.group("max"))
            if minimum <= maximum:
                constraints.append(
                    LengthConstraint(
                        constraint_kind="cjk_length_range",
                        min_cjk_characters=minimum,
                        max_cjk_characters=maximum,
                        source_text=match.group(0),
                        source_start=match.start(),
                        source_end=match.end(),
                        unit=match.group("unit"),
                    )
                )
            occupied.append(match.span())

    for pattern in MIN_PATTERNS:
        for match in pattern.finditer(task_text):
            if overlaps_existing(match.span(), occupied):
                continue
            constraints.append(
                LengthConstraint(
                    constraint_kind="cjk_length_minimum",
                    min_cjk_characters=int(match.group("min")),
                    max_cjk_characters=None,
                    source_text=match.group(0),
                    source_start=match.start(),
                    source_end=match.end(),
                    unit=match.group("unit"),
                )
            )
            occupied.append(match.span())

    for pattern in MAX_PATTERNS:
        for match in pattern.finditer(task_text):
            if overlaps_existing(match.span(), occupied):
                continue
            constraints.append(
                LengthConstraint(
                    constraint_kind="cjk_length_maximum",
                    min_cjk_characters=None,
                    max_cjk_characters=int(match.group("max")),
                    source_text=match.group(0),
                    source_start=match.start(),
                    source_end=match.end(),
                    unit=match.group("unit"),
                )
            )
            occupied.append(match.span())
    return constraints


def observe_unbounded_length_targets(
    *,
    task_text: str,
    occupied_spans: list[tuple[int, int]],
    actual_cjk_count: int,
) -> list[dict[str, Any]]:
    observations: list[dict[str, Any]] = []
    for match in TARGET_PATTERN.finditer(task_text):
        if overlaps_existing(match.span(), occupied_spans):
            continue
        has_approximation = bool(match.group("prefix") or match.group("suffix"))
        if not has_approximation:
            continue
        target = int(match.group("target"))
        observations.append(
            {
                "source_text": match.group(0),
                "target_cjk_characters": target,
                "actual_cjk_characters": actual_cjk_count,
                "actual_minus_target": actual_cjk_count - target,
                "actual_to_target_ratio": round(actual_cjk_count / target, 4) if target else None,
                "status": "unsupported_without_explicit_bounds",
            }
        )
    return observations


def find_incomplete_signals(candidate_text: str) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []
    for pattern in INCOMPLETE_SIGNAL_PATTERNS:
        for match in pattern.finditer(candidate_text):
            signals.append(
                {
                    "text": match.group(0),
                    "start": match.start(),
                    "end": match.end(),
                }
            )
    return signals


def count_cjk_characters(text: str) -> int:
    return len(CJK_CHARACTER.findall(text))


def select_count_region(candidate_text: str, marker_pairs: list[MarkerRegion]) -> dict[str, Any]:
    if marker_pairs:
        region = marker_pairs[0]
        return {
            "region_kind": "marker_pair",
            "start_label": region.start_label,
            "end_label": region.end_label,
            "base_label": region.base_label,
            "content_start": region.content_start,
            "content_end": region.content_end,
            "text": candidate_text[region.content_start : region.content_end],
        }
    return {
        "region_kind": "full_candidate",
        "start_label": "",
        "end_label": "",
        "base_label": "",
        "content_start": 0,
        "content_end": len(candidate_text),
        "text": candidate_text,
    }


def selected_region_without_text(selected_region: dict[str, Any]) -> dict[str, Any]:
    text = str(selected_region.get("text") or "")
    return {
        key: value
        for key, value in {
            "region_kind": selected_region.get("region_kind"),
            "start_label": selected_region.get("start_label"),
            "end_label": selected_region.get("end_label"),
            "base_label": selected_region.get("base_label"),
            "content_start": selected_region.get("content_start"),
            "content_end": selected_region.get("content_end"),
            "character_count": len(text),
            "cjk_character_count": count_cjk_characters(text),
        }.items()
        if value not in {None, ""}
    }


def build_length_check(
    index: int,
    constraint: LengthConstraint,
    actual_cjk_count: int,
    selected_region: dict[str, Any],
) -> dict[str, Any]:
    minimum = constraint.min_cjk_characters
    maximum = constraint.max_cjk_characters
    passed_min = minimum is None or actual_cjk_count >= minimum
    passed_max = maximum is None or actual_cjk_count <= maximum
    return {
        "check_id": f"cjk_length_{index}",
        "check_kind": constraint.constraint_kind,
        "status": "passed" if passed_min and passed_max else "failed",
        "source_text": constraint.source_text,
        "unit": constraint.unit,
        "min_cjk_characters": minimum,
        "max_cjk_characters": maximum,
        "actual_cjk_characters": actual_cjk_count,
        "used_region": selected_region_without_text(selected_region),
    }


def summarize_overall_status(checks: list[dict[str, Any]]) -> str:
    if any(check.get("status") == "failed" for check in checks):
        return "failed"
    if any(check.get("status") == "passed" for check in checks):
        return "passed"
    return "unsupported"


def build_marker(match: re.Match[str]) -> Marker:
    label = match.group("label").strip()
    role, base_label = classify_marker_label(label)
    return Marker(
        label=label,
        start=match.start(),
        end=match.end(),
        role=role,
        base_label=base_label,
    )


def classify_marker_label(label: str) -> tuple[str, str]:
    normalized = re.sub(r"\s+", "", label)
    lowered = normalized.lower()
    for suffix in ("开始", "起始", "start", "begin"):
        if lowered.endswith(suffix):
            return "start", normalized[: -len(suffix)].strip(":：-_ ")
    for suffix in ("结束", "终止", "end", "finish", "stop"):
        if lowered.endswith(suffix):
            return "end", normalized[: -len(suffix)].strip(":：-_ ")
    for prefix in ("开始", "起始", "start", "begin"):
        if lowered.startswith(prefix):
            return "start", normalized[len(prefix) :].strip(":：-_ ")
    for prefix in ("结束", "终止", "end", "finish", "stop"):
        if lowered.startswith(prefix):
            return "end", normalized[len(prefix) :].strip(":：-_ ")
    return "boundary", normalized


def markers_form_pair(start_marker: Marker, end_marker: Marker) -> bool:
    if start_marker.role == "start":
        return end_marker.role == "end" and start_marker.base_label == end_marker.base_label
    return end_marker.role == "boundary" and start_marker.base_label == end_marker.base_label


def overlaps_existing(span: tuple[int, int], occupied: list[tuple[int, int]]) -> bool:
    start, end = span
    return any(start < existing_end and existing_start < end for existing_start, existing_end in occupied)
