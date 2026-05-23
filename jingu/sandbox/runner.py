"""Ephemeral AI chat runner."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jingu.ai.client import ChatClient
from jingu.ai.config import load_ai_config
from jingu.runtime.constants import (
    EVENT_METHOD_CALL_FRAME_OPENED,
    STATE_ABANDONED,
    STATE_ACCEPTED,
    STATE_DRAFT,
    STATE_READY,
    STATE_REJECTED,
    STATE_REVIEWING,
    STATE_RUNNING,
)
from jingu.runtime.object_store import checksum_text
from jingu.runtime.repository import decode_json
from jingu.runtime.service import RuntimeService
from jingu.runtime.tree import TreeService
from jingu.sandbox.flow import (
    FLOW_AI_REQUEST_STARTED,
    FLOW_AI_RESPONSE_RECEIVED,
    FLOW_ACCEPTANCE_ROUTING_EVIDENCE_SUBMITTED,
    FLOW_ACCEPTANCE_ROUTING_RECEIVED,
    FLOW_ACCEPTANCE_ROUTING_REQUESTED,
    FLOW_ACCEPTANCE_ROUTING_SKIPPED,
    FLOW_ACCEPTED_PARENT_REEVALUATION_RECORDED,
    FLOW_ADVANCEMENT_LOOP_FINISHED,
    FLOW_ADVANCEMENT_WAVE_FINISHED,
    FLOW_ADVANCEMENT_WAVE_STARTED,
    FLOW_CANDIDATE_SUBMITTED,
    FLOW_CHILD_PACKAGE_REPAIR_LIMIT_REACHED,
    FLOW_CHILD_PACKAGE_REPAIR_PACKAGE_SUBMITTED,
    FLOW_CHILD_PACKAGE_REPAIR_REJECTED,
    FLOW_CHILD_PACKAGE_REPAIR_REQUESTED,
    FLOW_CHILD_PACKAGE_REPAIR_RESPONSE_RECEIVED,
    FLOW_CHILD_PACKAGE_REVIEW_ACCEPTED,
    FLOW_CHILD_PACKAGE_REVIEW_RECEIVED,
    FLOW_CHILD_PACKAGE_REVIEW_REJECTED,
    FLOW_CHILD_PACKAGE_REVIEW_REQUESTED,
    FLOW_CHILD_JOB_DISPATCH_STARTED,
    FLOW_CHILD_JOB_RESPONSE_RECEIVED,
    FLOW_CHILD_RESULT_PACKAGE_REJECTED,
    FLOW_CHILD_RESULT_PACKAGE_SUBMITTED,
    FLOW_CHAT_SESSION_FINISHED,
    FLOW_CHAT_SESSION_STARTED,
    FLOW_CHAT_TURN_FINISHED,
    FLOW_EVIDENCE_SUBMITTED,
    FLOW_FEEDBACK_JOB_CREATED,
    FLOW_HUMAN_DECISION_REQUESTED,
    FLOW_FRONTIER_DISPATCH_FINISHED,
    FLOW_FRONTIER_DISPATCH_SKIPPED,
    FLOW_FRONTIER_DISPATCH_STARTED,
    FLOW_INPUT_PROVENANCE_RECORDED,
    FLOW_JOB_READY,
    FLOW_JOB_RUNNING,
    FLOW_JOB_TREE_MANAGEMENT_RECORDED,
    FLOW_JOB_TREE_SNAPSHOT_RECORDED,
    FLOW_METHOD_CONTEXT_INJECTED,
    FLOW_METHOD_CONTEXT_LOADED,
    FLOW_METHOD_CALL_FRAME_OPENED,
    FLOW_METHOD_LAW_FRAGMENT_BOUND,
    FLOW_METHOD_LAW_FRAGMENT_LOADED,
    FLOW_METHOD_LEARNING_CANDIDATE_RECORDED,
    FLOW_METHOD_SELF_REVIEW_RECEIVED,
    FLOW_METHOD_SELF_REVIEW_REQUESTED,
    FLOW_METHOD_SOURCE_RESOLVED,
    FLOW_METHOD_STEP_CANDIDATE_RECORDED,
    FLOW_METHOD_STEP_CANDIDATE_SKIPPED,
    FLOW_METHOD_UPDATE_CANDIDATE_RECORDED,
    FLOW_SPLIT_PROPOSAL_ACCEPTED,
    FLOW_SPLIT_PROPOSAL_RECEIVED,
    FLOW_SPLIT_PROPOSAL_REJECTED,
    FLOW_SPLIT_PROPOSAL_REQUESTED,
    FLOW_SPLIT_PROPOSAL_SKIPPED,
    FLOW_PROCESS_STEP_RECORDED,
    FLOW_PROVIDER_MESSAGES_RECORDED,
    FLOW_PROVIDER_STREAM_DELTA_RECEIVED,
    FLOW_PROVIDER_STREAM_FINISHED,
    FLOW_PARENT_VERIFICATION_EVIDENCE_SUBMITTED,
    FLOW_PARENT_REEVALUATION_RECORDED,
    FLOW_PARENT_INTEGRATION_CANDIDATE_SUBMITTED,
    FLOW_PARENT_INTEGRATION_FOLLOWUP_REGISTRATION_FINISHED,
    FLOW_PARENT_INTEGRATION_JOB_CREATED,
    FLOW_PARENT_INTEGRATION_RECEIVED,
    FLOW_PARENT_INTEGRATION_REPAIR_ACCEPTED,
    FLOW_PARENT_INTEGRATION_REPAIR_JOB_CREATED,
    FLOW_PARENT_INTEGRATION_REPAIR_RECEIVED,
    FLOW_PARENT_INTEGRATION_REPAIR_REJECTED,
    FLOW_PARENT_INTEGRATION_REPAIR_REQUESTED,
    FLOW_PARENT_INTEGRATION_REJECTED,
    FLOW_PARENT_INTEGRATION_REQUESTED,
    FLOW_PARENT_INTEGRATION_SKIPPED,
    FLOW_RESULT_OUTPUT_RECORDED,
    FLOW_REPAIR_CANDIDATE_SUBMITTED,
    FLOW_REPAIR_JOB_CREATED,
    FLOW_REPAIR_LOOP_FINISHED,
    FLOW_REPAIR_REQUEST_PREPARED,
    FLOW_REPAIR_RESPONSE_RECEIVED,
    FLOW_RUN_FAILED,
    FLOW_ROOT_JOB_CREATED,
    FLOW_RUN_FINISHED,
    FLOW_RUNTIME_INITIALIZED,
    FLOW_RUNTIME_OPTIONS_RECORDED,
    FLOW_SANDBOX_CREATED,
    FLOW_SANDBOX_DESTROYED,
    FLOW_USER_INPUT_RECORDED,
    FLOW_VERIFICATION_EVIDENCE_SUBMITTED,
    FLOW_VERIFICATION_FEEDBACK_JOB_CREATED,
    FLOW_VERIFICATION_JOB_CREATED,
    FLOW_VERIFICATION_RESULT_RECORDED,
    FLOW_VERIFICATION_TOOL_STARTED,
    FlowWriter,
    input_provenance_fields,
    new_diagnostic_log_path,
    readable_log_path_for,
)
from jingu.sandbox.method import (
    MethodContext,
    build_method_review_messages,
    build_method_system_messages,
    load_method_context,
    method_evidence_payload,
)
from jingu.sandbox.paths import (
    latest_log_pointer_path,
    latest_readable_log_pointer_path,
    resolve_log_dir,
    resolve_sandbox_path,
)
from jingu.sandbox.verification import (
    build_parent_verification_evidence,
    verification_report_to_json,
    verify_candidate_text,
)


TERMINAL_JOB_STATES = {STATE_ACCEPTED, STATE_REJECTED, STATE_ABANDONED}
VERIFICATION_JOB_TARGET = "校验候选结果中的可判定文本约束"
VERIFICATION_JOB_ACCEPTANCE_CRITERIA = "输出结构化校验报告，记录可执行检查、实际计数、证据和无法自动判定的缺口。"
REPAIR_JOB_TARGET = "修复候选结果中的可判定校验失败"
REPAIR_JOB_ACCEPTANCE_CRITERIA = "输出修订后的完整候选结果，并让修订点可以被再次校验。"
ACCEPTANCE_REPAIR_JOB_TARGET = "修复验收路由打回的候选问题"
ACCEPTANCE_REPAIR_JOB_ACCEPTANCE_CRITERIA = "输出完整修订候选结果，覆盖验收路由指出的可修复问题，并保留原始任务意图。"
ACCEPTANCE_FEEDBACK_JOB_ACCEPTANCE_CRITERIA = "补齐验收路由显影的问题，形成可回流原业的反馈、裁决问题或下一步证据需求。"
VERIFICATION_FEEDBACK_JOB_TARGET = "处理候选校验未解决问题"
VERIFICATION_FEEDBACK_JOB_ACCEPTANCE_CRITERIA = "产出下一步修复方向、人工反馈问题或方法更新候选，并引用校验证据。"
DEFAULT_MAX_REPAIR_ATTEMPTS = 1
DEFAULT_MAX_FRONTIER_DISPATCHES = 2
DEFAULT_MAX_CHILD_PACKAGE_REPAIR_ATTEMPTS = 1
DEFAULT_MAX_ADVANCEMENT_WAVES = 1
DEFAULT_MAX_PARENT_INTEGRATION_REPAIR_ATTEMPTS = 1
DEFAULT_REGISTER_METHOD_STEP_CANDIDATES = False
ACCEPTANCE_ROUTE_ACTIONS = frozenset({"continue", "repair", "feedback"})
ACCEPTANCE_FEEDBACK_JOB_KINDS = frozenset({"high_value", "directional"})
CHILD_PACKAGE_REVIEW_ACTIONS = frozenset({"accept", "repair"})
PARENT_INTEGRATION_REQUIRED_FIELDS = (
    "integrated_candidate_text",
    "consumed_child_jobs",
    "evidence",
    "open_gaps",
    "suggested_follow_up_jobs",
    "parent_consumption_summary",
)
FRONTIER_DISPATCH_STATES = frozenset({STATE_DRAFT, STATE_READY, STATE_RUNNING})
CHILD_RESULT_PACKAGE_FIELDS = (
    "conclusion",
    "artifacts",
    "evidence_summary",
    "open_questions",
    "suggested_follow_up_jobs",
)
RESULT_PACKAGE_METADATA_KIND = "result_package"
REPAIRABLE_CHECK_KINDS = frozenset(
    {
        "cjk_length_range",
        "cjk_length_minimum",
        "cjk_length_maximum",
        "incomplete_output_signal",
    }
)


@dataclass(frozen=True)
class SandboxRuntimeOptions:
    max_repair_attempts: int = DEFAULT_MAX_REPAIR_ATTEMPTS
    max_frontier_dispatches: int = DEFAULT_MAX_FRONTIER_DISPATCHES
    max_child_package_repair_attempts: int = DEFAULT_MAX_CHILD_PACKAGE_REPAIR_ATTEMPTS
    max_advancement_waves: int = DEFAULT_MAX_ADVANCEMENT_WAVES
    max_parent_integration_repair_attempts: int = DEFAULT_MAX_PARENT_INTEGRATION_REPAIR_ATTEMPTS
    register_method_step_candidates: bool = DEFAULT_REGISTER_METHOD_STEP_CANDIDATES

    @classmethod
    def from_values(
        cls,
        *,
        max_repair_attempts: int = DEFAULT_MAX_REPAIR_ATTEMPTS,
        max_frontier_dispatches: int = DEFAULT_MAX_FRONTIER_DISPATCHES,
        max_child_package_repair_attempts: int = DEFAULT_MAX_CHILD_PACKAGE_REPAIR_ATTEMPTS,
        max_advancement_waves: int = DEFAULT_MAX_ADVANCEMENT_WAVES,
        max_parent_integration_repair_attempts: int = DEFAULT_MAX_PARENT_INTEGRATION_REPAIR_ATTEMPTS,
        register_method_step_candidates: bool = DEFAULT_REGISTER_METHOD_STEP_CANDIDATES,
    ) -> "SandboxRuntimeOptions":
        return cls(
            max_repair_attempts=normalize_max_repair_attempts(max_repair_attempts),
            max_frontier_dispatches=normalize_max_frontier_dispatches(max_frontier_dispatches),
            max_child_package_repair_attempts=normalize_max_child_package_repair_attempts(
                max_child_package_repair_attempts
            ),
            max_advancement_waves=normalize_max_advancement_waves(max_advancement_waves),
            max_parent_integration_repair_attempts=normalize_max_parent_integration_repair_attempts(
                max_parent_integration_repair_attempts
            ),
            register_method_step_candidates=bool(register_method_step_candidates),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "max_repair_attempts": self.max_repair_attempts,
            "max_frontier_dispatches": self.max_frontier_dispatches,
            "max_child_package_repair_attempts": self.max_child_package_repair_attempts,
            "max_advancement_waves": self.max_advancement_waves,
            "max_parent_integration_repair_attempts": self.max_parent_integration_repair_attempts,
            "register_method_step_candidates": self.register_method_step_candidates,
        }

    def log_fields(self) -> dict[str, str]:
        return {
            "runtime_options": json.dumps(self.as_dict(), ensure_ascii=False, sort_keys=True, indent=2),
            "repair_max_attempts": str(self.max_repair_attempts),
            "frontier_dispatch_limit": str(self.max_frontier_dispatches),
            "child_package_repair_limit": str(self.max_child_package_repair_attempts),
            "advancement_wave_limit": str(self.max_advancement_waves),
            "parent_integration_repair_limit": str(self.max_parent_integration_repair_attempts),
            "method_step_registration_enabled": str(self.register_method_step_candidates).lower(),
        }


def write_runtime_options_event(
    *,
    flow: FlowWriter,
    options: SandboxRuntimeOptions,
    step: str,
    turn: str | None = None,
) -> None:
    data = {**turn_field(turn), **options.log_fields()}
    flow.write(FLOW_RUNTIME_OPTIONS_RECORDED, "runtime options recorded", **data)
    write_process_step(
        flow=flow,
        step=step,
        phase="runtime",
        action="记录本次沙盒运行显式运行选项",
        **data,
    )


def write_process_step(
    *,
    flow: FlowWriter,
    step: str,
    phase: str,
    action: str,
    status: str = "completed",
    **data: Any,
) -> None:
    event_data = {
        "process_step": step,
        "process_phase": phase,
        "process_action": action,
        "process_status": status,
    }
    event_data.update({key: str(value) for key, value in data.items() if value is not None})
    flow.write(FLOW_PROCESS_STEP_RECORDED, "process step recorded", **event_data)


def write_provider_messages(
    *,
    flow: FlowWriter,
    call_kind: str,
    messages: list[dict[str, str]],
    turn: str | None = None,
    job_id: str | None = None,
) -> None:
    event_data = {
        "provider_call_kind": call_kind,
        "provider_message_count": str(len(messages)),
        "provider_message_roles": ",".join(message.get("role", "") for message in messages),
        "provider_messages": json.dumps(messages, ensure_ascii=False, indent=2),
    }
    if turn is not None:
        event_data["turn"] = turn
    if job_id is not None:
        event_data["job_id"] = job_id
    flow.write(FLOW_PROVIDER_MESSAGES_RECORDED, "provider messages recorded", **event_data)


def write_method_law_fragment_events(
    *,
    flow: FlowWriter,
    method: MethodContext,
    turn: str | None = None,
) -> None:
    for fragment in method.fragments:
        data = {
            "method_name": method.name,
            "method_checksum": method.checksum,
            **fragment.log_fields(),
        }
        if turn is not None:
            data["turn"] = turn
        flow.write(FLOW_METHOD_LAW_FRAGMENT_LOADED, "method law fragment loaded", **data)


def bind_method_law_fragments_to_job(
    *,
    flow: FlowWriter,
    service: RuntimeService,
    method: MethodContext,
    job_id: str,
    step: str,
    binding_reason: str,
    invocation_input: dict[str, Any],
    output_contract: str,
    acceptance_criteria: str,
    return_point: str,
    budget: dict[str, Any],
    depth: int,
    turn: str | None = None,
) -> None:
    call_frame = {
        "method_name": method.name,
        "method_path": str(method.path),
        "method_checksum": method.checksum,
        "binding_reason": binding_reason,
        "invocation_input": invocation_input,
        "output_contract": output_contract,
        "acceptance_criteria": acceptance_criteria,
        "return_point": return_point,
        "budget": budget,
        "depth": depth,
        "repeat_detection_key": checksum_text(
            json.dumps(
                {
                    "job_id": job_id,
                    "method_checksum": method.checksum,
                    "invocation_input": invocation_input,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        ),
    }
    result = service.bind_method_law_fragments(
        job_id,
        fragments=[fragment.binding_payload(method=method) for fragment in method.fragments],
        call_frame=call_frame,
    )
    refs = result["method_law_fragments"]
    data = {
        "job_id": job_id,
        "method_name": method.name,
        "method_checksum": method.checksum,
        "method_law_fragment_count": str(len(refs)),
        "method_law_appearance_refs": json.dumps(refs, ensure_ascii=False, sort_keys=True, indent=2),
    }
    if turn is not None:
        data["turn"] = turn
    flow.write(FLOW_METHOD_LAW_FRAGMENT_BOUND, "method law fragments bound", **data)
    frame_data = {
        **data,
        "method_binding_reason": binding_reason,
        "method_invocation_input": json.dumps(invocation_input, ensure_ascii=False, sort_keys=True, indent=2),
        "method_output_contract": output_contract,
        "method_return_point": return_point,
        "method_budget": json.dumps(budget, ensure_ascii=False, sort_keys=True, indent=2),
        "method_call_frame_depth": str(depth),
        "method_call_frame_repeat_key": call_frame["repeat_detection_key"],
        "method_call_frame": json.dumps(
            result["method_call_frame"], ensure_ascii=False, sort_keys=True, indent=2
        ),
    }
    flow.write(FLOW_METHOD_CALL_FRAME_OPENED, "method call frame opened", **frame_data)
    write_job_tree_mirror(
        flow=flow,
        service=service,
        turn=turn,
        job_id=job_id,
        action="method_call_frame_opened",
    )
    write_process_step(
        flow=flow,
        step=step,
        phase="method",
        action="bound method-law fragments to current job as appearances",
        **data,
    )
    write_process_step(
        flow=flow,
        step=f"{step}.call_frame",
        phase="method",
        action="opened method call frame for current job",
        **frame_data,
    )


def register_method_step_candidates(
    *,
    flow: FlowWriter,
    service: RuntimeService,
    method: MethodContext,
    parent_job_id: str,
    step_prefix: str,
    enabled: bool,
    turn: str | None = None,
) -> dict[str, Any]:
    if not enabled:
        data = {
            **turn_field(turn),
            "job_id": parent_job_id,
            "method_name": method.name,
            "method_checksum": method.checksum,
            "method_step_registration_enabled": "false",
            "reason": "runtime option register_method_step_candidates is false",
        }
        flow.write(FLOW_METHOD_STEP_CANDIDATE_SKIPPED, "method step candidate skipped", **data)
        write_process_step(
            flow=flow,
            step=f"{step_prefix}.skip",
            phase="method",
            action="运行选项未开启法步骤候选登记",
            status="skipped",
            **data,
        )
        return {"created": [], "skipped_reason": data["reason"]}

    created: list[dict[str, str]] = []
    for fragment in method.fragments:
        if not fragment.title or fragment.title == "method-body":
            continue
        child = service.create_child_job(
            parent_job_id=parent_job_id,
            target=f"执行法步骤候选：{fragment.title}",
            actor_id="system",
            acceptance_criteria=(
                "产出当前法片段在本业中的可消费局部果、证据、开放缺口和回流点；"
                "不得宣告父业或根业完成。"
            ),
            required_context_gaps=[],
        )
        child_job_id = str(child["job_id"])
        item = {
            "child_job_id": child_job_id,
            "method_law_id": fragment.fragment_id,
            "method_law_title": fragment.title,
            "method_law_checksum": fragment.checksum,
        }
        created.append(item)
        data = {
            **turn_field(turn),
            "job_id": parent_job_id,
            "parent_job_id": parent_job_id,
            "child_job_id": child_job_id,
            "method_name": method.name,
            "method_checksum": method.checksum,
            "method_law_id": fragment.fragment_id,
            "method_law_title": fragment.title,
            "method_law_checksum": fragment.checksum,
            "method_return_point": "父业法步骤候选回流",
        }
        flow.write(FLOW_METHOD_STEP_CANDIDATE_RECORDED, "method step candidate recorded", **data)
        write_job_tree_mirror(
            flow=flow,
            service=service,
            turn=turn,
            job_id=child_job_id,
            action="method_step_child_created",
            child_job_id=child_job_id,
        )
        write_process_step(
            flow=flow,
            step=f"{step_prefix}.create",
            phase="method",
            action="从已绑定法片段登记候选法步骤子业",
            **data,
        )

    summary = {
        **turn_field(turn),
        "job_id": parent_job_id,
        "method_step_registration_enabled": "true",
        "method_step_candidate_count": str(len(created)),
        "method_step_candidate_summary": json.dumps(created, ensure_ascii=False, sort_keys=True, indent=2),
    }
    if created:
        flow.write(FLOW_METHOD_STEP_CANDIDATE_RECORDED, "method step candidates recorded", **summary)
    else:
        summary["reason"] = "method fragments did not contain named step headings"
        flow.write(FLOW_METHOD_STEP_CANDIDATE_SKIPPED, "method step candidate skipped", **summary)
    return {"created": created, "skipped_reason": "" if created else summary.get("reason", "")}


def parse_method_update_candidates(review: str) -> list[Any]:
    try:
        payload = load_json_object(review, error_prefix="method self-review response")
    except RuntimeError:
        return []
    if not isinstance(payload, dict):
        return []
    candidates = payload.get("method_update_candidates") or []
    if isinstance(candidates, str):
        text = candidates.strip()
        return [text] if text else []
    if isinstance(candidates, list):
        return [item for item in candidates if str(item).strip()]
    if isinstance(candidates, dict):
        return [candidates]
    return []


def record_method_learning_candidate(
    *,
    flow: FlowWriter,
    service: RuntimeService,
    method: MethodContext,
    job_id: str,
    review: str,
    step_prefix: str,
    turn: str | None = None,
) -> dict[str, Any] | None:
    update_candidates = parse_method_update_candidates(review)
    if not update_candidates:
        return None
    payload = {
        "candidate_kind": "method_learning_candidate",
        "candidate_only": True,
        "method_name": method.name,
        "method_path": str(method.path),
        "method_checksum": method.checksum,
        "method_update_candidates": update_candidates,
        "source_review": review,
        "does_not_mutate_method_file": True,
    }
    candidate_text = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2)
    candidate = service.record_candidate_appearance(
        job_id,
        text=candidate_text,
        actor_id="method_self_review",
        metadata={
            "appearance_kind": "method_learning_candidate",
            "candidate_only": True,
            "method_name": method.name,
            "method_checksum": method.checksum,
        },
    )["candidate"]
    evidence_text = json.dumps(
        {
            "evidence_kind": "method_learning_candidate_observation",
            "evidence_hardness": "weak_ai",
            "method_learning_candidate_appearance_id": candidate["appearance_id"],
            "method_checksum": method.checksum,
            "candidate_only": True,
        },
        ensure_ascii=False,
        sort_keys=True,
        indent=2,
    )
    evidence = service.submit_evidence(
        job_id,
        text=evidence_text,
        actor_id="system",
        metadata={
            "evidence_kind": "method_learning_candidate_observation",
            "evidence_hardness": "weak_ai",
            "appearance_kind": "method_learning_candidate_evidence",
        },
    )["evidence"]
    data = {
        **turn_field(turn),
        "job_id": job_id,
        "method_name": method.name,
        "method_checksum": method.checksum,
        "method_learning_candidate_appearance_id": candidate["appearance_id"],
        "appearance_id": candidate["appearance_id"],
        "method_learning_candidate": candidate_text,
        "evidence_hardness": "weak_ai",
        "evidence_kind": "method_learning_candidate_observation",
        "candidate_only": "true",
        "reason": "method self-review returned method_update_candidates",
    }
    flow.write(FLOW_METHOD_LEARNING_CANDIDATE_RECORDED, "method learning candidate recorded", **data)
    write_job_tree_mirror(
        flow=flow,
        service=service,
        turn=turn,
        job_id=job_id,
        action="method_learning_candidate_recorded",
        appearance_id=candidate["appearance_id"],
        reason=data["reason"],
    )
    write_process_step(
        flow=flow,
        step=f"{step_prefix}.method_learning_candidate",
        phase="method",
        action="把方法自验中的法更新观察保存为候选相而不修改方法文件",
        **{
            **data,
            "evidence_id": evidence["appearance_id"],
        },
    )
    return {"candidate": candidate, "evidence": evidence, "payload": payload}


def discover_method_catalog(*, root_method: MethodContext) -> list[dict[str, str]]:
    catalog: dict[str, dict[str, str]] = {}

    def add_method(method: MethodContext, *, source: str) -> None:
        catalog[str(method.path.resolve())] = {
            "method_name": method.name,
            "method_path": str(method.path.resolve()),
            "method_checksum": method.checksum,
            "method_description": read_method_description(method.path),
            "source": source,
        }

    add_method(root_method, source="current_root_method")
    roots = [Path.cwd(), *root_method.path.resolve().parents]
    seen_roots: set[Path] = set()
    for root in roots:
        resolved_root = root.resolve()
        if resolved_root in seen_roots:
            continue
        seen_roots.add(resolved_root)
        skill_root = resolved_root / ".agents" / "skills"
        if not skill_root.exists():
            continue
        for skill_path in sorted(skill_root.glob("*/SKILL.md")):
            try:
                add_method(
                    load_method_context(method_path=skill_path),
                    source="workspace_skill",
                )
            except Exception:
                continue
    return sorted(catalog.values(), key=lambda item: (item["method_name"], item["method_path"]))


def read_method_description(path: Path) -> str:
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()[:40]
    except OSError:
        return ""
    in_frontmatter = False
    for index, raw_line in enumerate(lines):
        line = raw_line.strip()
        if index == 0 and line == "---":
            in_frontmatter = True
            continue
        if in_frontmatter and line == "---":
            return ""
        if in_frontmatter and line.startswith("description:"):
            return line.split(":", 1)[1].strip()
    return ""


def build_split_proposal_messages(
    *,
    method: MethodContext,
    parent_job_id: str,
    user_input: str,
    candidate_text: str,
    candidate_appearance_id: str,
    method_catalog: list[dict[str, str]],
    turn: str | None = None,
) -> list[dict[str, str]]:
    payload = {
        "task": user_input,
        "turn": turn or "",
        "parent_job_id": parent_job_id,
        "candidate": {
            "appearance_id": candidate_appearance_id,
            "text": candidate_text,
        },
        "root_method": {
            "method_name": method.name,
            "method_path": str(method.path),
            "method_checksum": method.checksum,
            "manifest": method.manifest(),
        },
        "available_method_catalog": method_catalog,
        "split_rules": [
            "只有当不拆分会阻塞父业执行、验收、证据生成或上下文控制时，才提出子业。",
            "禁止为了概念完整性、装饰性分类或复述父业目标而提出子业。",
            "子业必须有独立局部果、可验收输出契约和父业可消费的回流点。",
            "如果子业需要调用法，method_path 必须从 available_method_catalog 中选择并原样返回。",
            "子业只能供料证成，不能宣告父业或根业完成。",
        ],
        "response_contract": {
            "top_level": "JSON object",
            "required_key": "proposals",
            "field_types": {
                "target": "non-empty string",
                "blocking_reason": "non-empty string",
                "output_contract": "non-empty string",
                "acceptance_criteria": "non-empty string",
                "estimated_effort": "positive integer only; use 1, 2, 3... and do not use 高/中/低 or low/medium/high",
                "depth_limit": "positive integer only; use 1, 2, 3...",
                "required_context_gaps": "list of strings; use [] when current context is enough to execute the child now",
                "method_path": "empty string or one exact method_path from available_method_catalog",
                "method_binding_reason": "empty string unless method_path is set",
                "method_return_point": "empty string unless method_path is set",
            },
            "proposal_fields": [
                "target",
                "blocking_reason",
                "output_contract",
                "acceptance_criteria",
                "estimated_effort",
                "depth_limit",
                "required_context_gaps",
                "method_path",
                "method_binding_reason",
                "method_return_point",
            ],
            "method_fields_rule": (
                "method_path may be empty; if method_path is not empty, "
                "method_binding_reason and method_return_point are required."
            ),
            "runtime_effects": [
                "Qualitative effort words will be rejected by the code gatekeeper.",
                "A child job with required_context_gaps will be visible as blocked context and cannot enter running until gaps are resolved.",
            ],
        },
    }
    return [
        {
            "role": "system",
            "content": (
                "你是金箍运行时中的分业申请提议位。"
                "你只能提出候选分业申请，不能创建、接收、拒收或完成任何业。"
                "代码守门器会检查你的 JSON；不满足条件的申请会被拒绝。"
                "只返回 JSON，不要输出解释性正文。"
            ),
        },
        {
            "role": "user",
            "content": json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2),
        },
    ]


def run_split_proposal_registration(
    *,
    flow: FlowWriter,
    service: RuntimeService,
    client: ChatClient,
    method: MethodContext,
    parent_job_id: str,
    user_input: str,
    candidate_text: str,
    candidate_appearance_id: str,
    step_prefix: str,
    turn: str | None = None,
) -> dict[str, Any]:
    method_catalog = discover_method_catalog(root_method=method)
    messages = build_split_proposal_messages(
        method=method,
        parent_job_id=parent_job_id,
        user_input=user_input,
        candidate_text=candidate_text,
        candidate_appearance_id=candidate_appearance_id,
        method_catalog=method_catalog,
        turn=turn,
    )
    base_data = {
        **turn_field(turn),
        "job_id": parent_job_id,
        "candidate_appearance_id": candidate_appearance_id,
        "method_catalog": json.dumps(method_catalog, ensure_ascii=False, sort_keys=True, indent=2),
        "split_proposal_prompt": messages[-1]["content"],
        "provider_message_count": str(len(messages)),
    }
    flow.write(FLOW_SPLIT_PROPOSAL_REQUESTED, "split proposal requested", **base_data)
    write_provider_messages(
        flow=flow,
        call_kind="split_proposal_extraction",
        messages=messages,
        turn=turn,
        job_id=parent_job_id,
    )
    write_process_step(
        flow=flow,
        step=f"{step_prefix}.request",
        phase="split_proposal",
        action="向分业申请提议位发送候选结果和可用法目录",
        status="started",
        **base_data,
    )

    response = complete_with_provider_logging(
        flow=flow,
        client=client,
        messages=messages,
        call_kind="split_proposal_extraction",
        turn=turn,
        job_id=parent_job_id,
    )
    response_data = {
        **turn_field(turn),
        "job_id": parent_job_id,
        "split_proposal_response": response.content,
    }
    flow.write(FLOW_SPLIT_PROPOSAL_RECEIVED, "split proposal received", **response_data)
    write_process_step(
        flow=flow,
        step=f"{step_prefix}.receive",
        phase="split_proposal",
        action="收到分业申请提议位响应",
        **response_data,
    )

    try:
        proposals = parse_split_proposals(response.content)
    except RuntimeError as exc:
        skipped = {
            **turn_field(turn),
            "job_id": parent_job_id,
            "reason": str(exc),
            "split_proposal_response": response.content,
        }
        flow.write(FLOW_SPLIT_PROPOSAL_SKIPPED, "split proposal registration skipped", **skipped)
        write_job_tree_mirror(
            flow=flow,
            service=service,
            turn=turn,
            job_id=parent_job_id,
            action="split_proposal_skipped",
            reason=str(exc),
        )
        write_process_step(
            flow=flow,
            step=f"{step_prefix}.skip",
            phase="split_proposal",
            action="分业申请响应无法解析，跳过登记",
            status="skipped",
            **skipped,
        )
        return {"accepted": [], "rejected": [], "skipped_reason": str(exc)}

    if not proposals:
        skipped = {
            **turn_field(turn),
            "job_id": parent_job_id,
            "reason": "split proposal response contained no proposals",
            "split_proposal_count": "0",
        }
        flow.write(FLOW_SPLIT_PROPOSAL_SKIPPED, "split proposal registration skipped", **skipped)
        write_job_tree_mirror(
            flow=flow,
            service=service,
            turn=turn,
            job_id=parent_job_id,
            action="split_proposal_skipped",
            reason=skipped["reason"],
        )
        write_process_step(
            flow=flow,
            step=f"{step_prefix}.skip",
            phase="split_proposal",
            action="未收到分业申请，跳过登记",
            status="skipped",
            **skipped,
        )
        return {"accepted": [], "rejected": [], "skipped_reason": skipped["reason"]}

    catalog_by_path = {
        str(Path(entry["method_path"]).resolve()): entry
        for entry in method_catalog
    }
    tree_service = TreeService(service.paths.workspace)
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for index, proposal in enumerate(proposals, start=1):
        try:
            normalized = normalize_split_proposal(
                proposal,
                catalog_by_path=catalog_by_path,
            )
            result = tree_service.propose_child_job(
                parent_job_id=parent_job_id,
                target=normalized["target"],
                blocking_reason=normalized["blocking_reason"],
                output_contract=normalized["output_contract"],
                acceptance_criteria=normalized["acceptance_criteria"],
                estimated_effort=normalized["estimated_effort"],
                depth_limit=normalized["depth_limit"],
                required_context_gaps=normalized["required_context_gaps"],
                method_path=normalized.get("method_path") or None,
                method_binding_reason=normalized.get("method_binding_reason") or None,
                method_return_point=normalized.get("method_return_point") or None,
                actor_id="ai",
            )
            child = result["child"]
            accepted_item = {
                "proposal_index": index,
                "child_job_id": child["job_id"],
                "target": child["target"],
                "method_path": normalized.get("method_path", ""),
            }
            accepted.append(accepted_item)
            accepted_data = {
                **turn_field(turn),
                "job_id": parent_job_id,
                "child_job_id": child["job_id"],
                "split_proposal_index": str(index),
                "split_proposal_decision": "accepted",
                "split_proposal": json.dumps(normalized, ensure_ascii=False, sort_keys=True, indent=2),
                "split_registration_summary": json.dumps(
                    accepted_item, ensure_ascii=False, sort_keys=True, indent=2
                ),
            }
            flow.write(FLOW_SPLIT_PROPOSAL_ACCEPTED, "split proposal accepted", **accepted_data)
            write_job_tree_mirror(
                flow=flow,
                service=service,
                turn=turn,
                job_id=child["job_id"],
                action="split_proposal_child_created",
                child_job_id=child["job_id"],
            )
            write_process_step(
                flow=flow,
                step=f"{step_prefix}.accepted",
                phase="split_proposal",
                action="分业申请通过代码守门并登记为真实子业",
                **accepted_data,
            )
        except Exception as exc:
            rejected_item = {
                "proposal_index": index,
                "reason": str(exc),
                "proposal": proposal,
            }
            rejected.append(rejected_item)
            rejected_data = {
                **turn_field(turn),
                "job_id": parent_job_id,
                "split_proposal_index": str(index),
                "split_proposal_decision": "rejected",
                "split_proposal_rejection_reason": str(exc),
                "split_proposal": json.dumps(proposal, ensure_ascii=False, sort_keys=True, indent=2),
            }
            flow.write(FLOW_SPLIT_PROPOSAL_REJECTED, "split proposal rejected", **rejected_data)
            write_job_tree_mirror(
                flow=flow,
                service=service,
                turn=turn,
                job_id=parent_job_id,
                action="split_proposal_rejected",
                reason=str(exc),
            )
            write_process_step(
                flow=flow,
                step=f"{step_prefix}.rejected",
                phase="split_proposal",
                action="分业申请被代码守门器拒绝",
                status="rejected",
                **rejected_data,
            )
    return {"accepted": accepted, "rejected": rejected, "skipped_reason": ""}


def run_frontier_child_dispatch(
    *,
    flow: FlowWriter,
    service: RuntimeService,
    client: ChatClient,
    root_job_id: str,
    user_input: str,
    root_method: MethodContext,
    root_candidate_text: str,
    root_candidate_appearance_id: str,
    step_prefix: str,
    turn: str | None = None,
    max_child_dispatches: int = DEFAULT_MAX_FRONTIER_DISPATCHES,
    max_child_package_repair_attempts: int = DEFAULT_MAX_CHILD_PACKAGE_REPAIR_ATTEMPTS,
    max_parent_integration_repair_attempts: int = DEFAULT_MAX_PARENT_INTEGRATION_REPAIR_ATTEMPTS,
) -> dict[str, Any]:
    max_child_dispatches = normalize_max_frontier_dispatches(max_child_dispatches)
    max_child_package_repair_attempts = normalize_max_child_package_repair_attempts(
        max_child_package_repair_attempts
    )
    max_parent_integration_repair_attempts = normalize_max_parent_integration_repair_attempts(
        max_parent_integration_repair_attempts
    )
    tree_service = TreeService(service.paths.workspace)
    frontier_payload = tree_service.get_frontier(root_job_id)
    active_child_frontier = [
        job
        for job in frontier_payload["frontier"]
        if job.get("parent_job_id") and str(job.get("state")) in FRONTIER_DISPATCH_STATES
    ]
    base_data = {
        **turn_field(turn),
        "root_job_id": root_job_id,
        "frontier_job_count": str(len(active_child_frontier)),
        "frontier_dispatch_limit": str(max_child_dispatches),
    }
    flow.write(FLOW_FRONTIER_DISPATCH_STARTED, "frontier child dispatch started", **base_data)
    write_job_tree_mirror(
        flow=flow,
        service=service,
        turn=turn,
        job_id=root_job_id,
        action="frontier_dispatch_started",
    )
    write_process_step(
        flow=flow,
        step=f"{step_prefix}.start",
        phase="frontier_dispatch",
        action="读取当前活跃前沿子业并准备受控调度",
        status="started",
        **base_data,
    )

    if max_child_dispatches == 0 or not active_child_frontier:
        reason = (
            "frontier dispatch limit is zero"
            if max_child_dispatches == 0
            else "no active child frontier job"
        )
        summary = {
            "selected_child_jobs": [],
            "skipped_reason": reason,
            "frontier_job_count": len(active_child_frontier),
        }
        skipped_data = {
            **base_data,
            "reason": reason,
            "frontier_dispatch_summary": json.dumps(
                summary, ensure_ascii=False, sort_keys=True, indent=2
            ),
        }
        flow.write(FLOW_FRONTIER_DISPATCH_SKIPPED, "frontier child dispatch skipped", **skipped_data)
        write_job_tree_mirror(
            flow=flow,
            service=service,
            turn=turn,
            job_id=root_job_id,
            action="frontier_dispatch_skipped",
            reason=reason,
        )
        write_process_step(
            flow=flow,
            step=f"{step_prefix}.skip",
            phase="frontier_dispatch",
            action="没有可调度的前沿子业，保持根业候选主链路继续",
            status="skipped",
            **skipped_data,
        )
        return summary

    selected_children = active_child_frontier[:max_child_dispatches]
    dispatch_results: list[dict[str, Any]] = []
    parent_integration_results: list[dict[str, Any]] = []
    latest_root_integration: dict[str, Any] | None = None
    for index, child in enumerate(selected_children, start=1):
        child_job_id = str(child["job_id"])
        parent_job_id = str(child.get("parent_job_id") or root_job_id)
        child_state = str(child.get("state") or "")
        try:
            if child_state == STATE_DRAFT:
                ready_job = service.mark_ready(child_job_id, actor_id="system")
                child_state = str(ready_job["state"])
                ready_data = {**turn_field(turn), "job_id": child_job_id, "parent_job_id": parent_job_id}
                flow.write(FLOW_JOB_READY, "child job marked ready", **ready_data)
                write_job_tree_mirror(
                    flow=flow,
                    service=service,
                    turn=turn,
                    job_id=child_job_id,
                    action="job_ready",
                )
                write_process_step(
                    flow=flow,
                    step=f"{step_prefix}.child_{index}.ready",
                    phase="frontier_dispatch",
                    action="将选中的草稿子业置为就绪",
                    **ready_data,
                )
            if child_state == STATE_READY:
                running_job = service.start_job(child_job_id, actor_id="system")
                child_state = str(running_job["state"])
                running_data = {**turn_field(turn), "job_id": child_job_id, "parent_job_id": parent_job_id}
                flow.write(FLOW_JOB_RUNNING, "child job running", **running_data)
                write_job_tree_mirror(
                    flow=flow,
                    service=service,
                    turn=turn,
                    job_id=child_job_id,
                    action="job_running",
                )
                write_process_step(
                    flow=flow,
                    step=f"{step_prefix}.child_{index}.run",
                    phase="frontier_dispatch",
                    action="启动选中的前沿子业",
                    **running_data,
                )
        except Exception as exc:
            child_state = "transition_failed"
            transition_error = str(exc)
        else:
            transition_error = ""
        if child_state != STATE_RUNNING:
            reason = transition_error or f"child job state is not dispatchable after transition: {child_state}"
            rejected_data = {
                **turn_field(turn),
                "root_job_id": root_job_id,
                "parent_job_id": parent_job_id,
                "job_id": child_job_id,
                "child_job_id": child_job_id,
                "reason": reason,
            }
            flow.write(
                FLOW_CHILD_RESULT_PACKAGE_REJECTED,
                "child result package rejected",
                **rejected_data,
            )
            write_job_tree_mirror(
                flow=flow,
                service=service,
                turn=turn,
                job_id=child_job_id,
                action="child_package_rejected",
                reason=reason,
            )
            dispatch_results.append(
                {"child_job_id": child_job_id, "status": "rejected", "reason": reason}
            )
            continue

        parent_integration_result_for_child: dict[str, Any] | None = None
        child_method, child_method_source = load_child_dispatch_method(
            child_job=child,
            root_method=root_method,
        )
        messages = build_child_dispatch_messages(
            child_job=child,
            method=child_method,
            root_job_id=root_job_id,
            parent_job_id=parent_job_id,
            user_input=user_input,
            root_candidate_text=root_candidate_text,
            root_candidate_appearance_id=root_candidate_appearance_id,
        )
        dispatch_data = {
            **turn_field(turn),
            "root_job_id": root_job_id,
            "parent_job_id": parent_job_id,
            "job_id": child_job_id,
            "child_job_id": child_job_id,
            "job_target": str(child.get("target") or ""),
            "child_method_path": str(child_method.path),
            "reason": child_method_source,
            "provider_message_count": str(len(messages)),
        }
        flow.write(FLOW_CHILD_JOB_DISPATCH_STARTED, "child job dispatch started", **dispatch_data)
        write_job_tree_mirror(
            flow=flow,
            service=service,
            turn=turn,
            job_id=child_job_id,
            action="child_dispatch_started",
            child_job_id=child_job_id,
        )
        write_provider_messages(
            flow=flow,
            call_kind="child_job_execution",
            messages=messages,
            turn=turn,
            job_id=child_job_id,
        )
        write_process_step(
            flow=flow,
            step=f"{step_prefix}.child_{index}.request",
            phase="frontier_dispatch",
            action="向子业执行位发送业契约、法上下文和结构化果包契约",
            status="started",
            **dispatch_data,
        )

        response = complete_with_provider_logging(
            flow=flow,
            client=client,
            messages=messages,
            call_kind="child_job_execution",
            turn=turn,
            job_id=child_job_id,
        )
        response_data = {
            **turn_field(turn),
            "root_job_id": root_job_id,
            "parent_job_id": parent_job_id,
            "job_id": child_job_id,
            "child_job_id": child_job_id,
            "child_job_response": response.content,
        }
        flow.write(FLOW_CHILD_JOB_RESPONSE_RECEIVED, "child job response received", **response_data)
        write_process_step(
            flow=flow,
            step=f"{step_prefix}.child_{index}.receive",
            phase="frontier_dispatch",
            action="收到子业执行位响应",
            **response_data,
        )

        try:
            package = parse_child_result_package(response.content)
            package_text = json.dumps(package, ensure_ascii=False, sort_keys=True, indent=2)
            submitted = tree_service.submit_result_package(
                child_job_id,
                package=package,
                evidence_text=package_text,
                actor_id="ai",
            )
            candidate_id = str(submitted["candidate"]["appearance_id"])
            evidence_id = str(submitted["evidence"]["appearance_id"])
            package_data = {
                **turn_field(turn),
                "root_job_id": root_job_id,
                "parent_job_id": parent_job_id,
                "job_id": child_job_id,
                "child_job_id": child_job_id,
                "child_result_package": package_text,
                "child_result_package_candidate_id": candidate_id,
                "child_result_package_evidence_id": evidence_id,
                "evidence_kind": "result_package_evidence",
                "evidence_hardness": "ai_or_manual_package",
            }
            flow.write(
                FLOW_CHILD_RESULT_PACKAGE_SUBMITTED,
                "child result package submitted",
                **package_data,
            )
            write_job_tree_mirror(
                flow=flow,
                service=service,
                turn=turn,
                job_id=child_job_id,
                action="child_package_submitted",
                appearance_id=candidate_id,
                child_job_id=child_job_id,
            )
            write_process_step(
                flow=flow,
                step=f"{step_prefix}.child_{index}.package",
                phase="frontier_dispatch",
                action="通过业树服务提交子业果包候选和证据",
                **package_data,
            )

            review_result = run_child_package_review_loop(
                flow=flow,
                service=service,
                client=client,
                child_method=child_method,
                root_job_id=root_job_id,
                parent_job_id=parent_job_id,
                child_job=child,
                user_input=user_input,
                root_candidate_text=root_candidate_text,
                root_candidate_appearance_id=root_candidate_appearance_id,
                package=package,
                package_text=package_text,
                candidate_id=candidate_id,
                evidence_id=evidence_id,
                step_prefix=f"{step_prefix}.child_{index}.package_review",
                turn=turn,
                max_repair_attempts=max_child_package_repair_attempts,
            )
            child_split_result = {"accepted": [], "rejected": [], "skipped_reason": ""}
            if review_result.get("status") == "accept_ready":
                accepted_package_text = str(review_result["package_text"])
                accepted_candidate_id = str(review_result["candidate_id"])
                try:
                    child_split_result = run_split_proposal_registration(
                        flow=flow,
                        service=service,
                        client=client,
                        method=child_method,
                        parent_job_id=child_job_id,
                        user_input=user_input,
                        candidate_text=accepted_package_text,
                        candidate_appearance_id=accepted_candidate_id,
                        step_prefix=f"{step_prefix}.child_{index}.split_proposal",
                        turn=turn,
                    )
                except Exception as exc:
                    child_split_result = {"accepted": [], "rejected": [], "skipped_reason": str(exc)}
                accept_reviewed_child_package(
                    flow=flow,
                    service=service,
                    root_job_id=root_job_id,
                    parent_job_id=parent_job_id,
                    child_job_id=child_job_id,
                    candidate_id=accepted_candidate_id,
                    judgment=review_result["judgment"],
                    review_text=str(review_result["review_text"]),
                    step_prefix=f"{step_prefix}.child_{index}.package_review",
                    turn=turn,
                )
                try:
                    parent_integration_result = run_parent_integration(
                        flow=flow,
                        service=service,
                        client=client,
                        method=root_method if parent_job_id == root_job_id else child_method,
                        root_job_id=root_job_id,
                        parent_job_id=parent_job_id,
                        user_input=user_input,
                        root_candidate_text=root_candidate_text,
                        root_candidate_appearance_id=root_candidate_appearance_id,
                        step_prefix=f"{step_prefix}.child_{index}.parent_integration",
                        turn=turn,
                        max_repair_attempts=max_parent_integration_repair_attempts,
                    )
                except Exception as exc:
                    parent_integration_result = {"status": "rejected", "reason": str(exc)}
                    error_data = {
                        **turn_field(turn),
                        "root_job_id": root_job_id,
                        "parent_job_id": parent_job_id,
                        "job_id": parent_job_id,
                        "parent_integration_status": "rejected",
                        "reason": str(exc),
                    }
                    flow.write(
                        FLOW_PARENT_INTEGRATION_REJECTED,
                        "parent integration rejected",
                        **error_data,
                    )
                    write_job_tree_mirror(
                        flow=flow,
                        service=service,
                        turn=turn,
                        job_id=parent_job_id,
                        action="parent_integration_rejected",
                        reason=str(exc),
                    )
                    write_process_step(
                        flow=flow,
                        step=f"{step_prefix}.child_{index}.parent_integration.error",
                        phase="parent_integration",
                        action="父业整合运行异常，保持父业候选不变",
                        status="rejected",
                        **error_data,
                    )
                parent_integration_results.append(parent_integration_result)
                parent_integration_result_for_child = parent_integration_result
                if (
                    parent_job_id == root_job_id
                    and parent_integration_result.get("status") == "integrated"
                ):
                    latest_root_integration = parent_integration_result
            else:
                parent_reevaluation = tree_service.reevaluate_parent(parent_job_id)
                reevaluation_data = {
                    **turn_field(turn),
                    "root_job_id": root_job_id,
                    "parent_job_id": parent_job_id,
                    "job_id": parent_job_id,
                    "child_job_id": child_job_id,
                    "parent_reevaluation": json.dumps(
                        parent_reevaluation, ensure_ascii=False, sort_keys=True, indent=2
                    ),
                    "reason": str(review_result.get("reason") or review_result.get("status") or ""),
                }
                flow.write(
                    FLOW_PARENT_REEVALUATION_RECORDED,
                    "parent re-evaluation recorded",
                    **reevaluation_data,
                )
                write_job_tree_mirror(
                    flow=flow,
                    service=service,
                    turn=turn,
                    job_id=parent_job_id,
                    action="parent_reevaluation_recorded",
                    child_job_id=child_job_id,
                    reason=reevaluation_data["reason"],
                )
                write_process_step(
                    flow=flow,
                    step=f"{step_prefix}.child_{index}.parent_reevaluate_unresolved",
                    phase="frontier_dispatch",
                    action="记录未接收子业果包后的父业重评估",
                    status="rejected",
                    **reevaluation_data,
                )
            dispatch_results.append(
                {
                    "child_job_id": child_job_id,
                    "status": str(review_result.get("status") or "submitted"),
                    "candidate_appearance_id": review_result.get("candidate_id", candidate_id),
                    "evidence_appearance_id": review_result.get("evidence_id", evidence_id),
                    "child_split_result": child_split_result,
                    "parent_integration_result": parent_integration_result_for_child,
                }
            )
        except Exception as exc:
            rejected_data = {
                **turn_field(turn),
                "root_job_id": root_job_id,
                "parent_job_id": parent_job_id,
                "job_id": child_job_id,
                "child_job_id": child_job_id,
                "reason": str(exc),
                "child_job_response": response.content,
            }
            flow.write(
                FLOW_CHILD_RESULT_PACKAGE_REJECTED,
                "child result package rejected",
                **rejected_data,
            )
            write_job_tree_mirror(
                flow=flow,
                service=service,
                turn=turn,
                job_id=child_job_id,
                action="child_package_rejected",
                reason=str(exc),
            )
            write_process_step(
                flow=flow,
                step=f"{step_prefix}.child_{index}.package_rejected",
                phase="frontier_dispatch",
                action="子业响应未能通过结构化果包校验，保持候选隔离并记录拒绝",
                status="rejected",
                **rejected_data,
            )
            dispatch_results.append(
                {"child_job_id": child_job_id, "status": "rejected", "reason": str(exc)}
            )

    if selected_children and not parent_integration_results:
        try:
            parent_integration_result = run_parent_integration(
                flow=flow,
                service=service,
                client=client,
                method=root_method,
                root_job_id=root_job_id,
                parent_job_id=root_job_id,
                user_input=user_input,
                root_candidate_text=root_candidate_text,
                root_candidate_appearance_id=root_candidate_appearance_id,
                step_prefix=f"{step_prefix}.parent_integration",
                turn=turn,
                max_repair_attempts=max_parent_integration_repair_attempts,
            )
        except Exception as exc:
            parent_integration_result = {"status": "rejected", "reason": str(exc)}
            error_data = {
                **turn_field(turn),
                "root_job_id": root_job_id,
                "parent_job_id": root_job_id,
                "job_id": root_job_id,
                "parent_integration_status": "rejected",
                "reason": str(exc),
            }
            flow.write(
                FLOW_PARENT_INTEGRATION_REJECTED,
                "parent integration rejected",
                **error_data,
            )
            write_job_tree_mirror(
                flow=flow,
                service=service,
                turn=turn,
                job_id=root_job_id,
                action="parent_integration_rejected",
                reason=str(exc),
            )
            write_process_step(
                flow=flow,
                step=f"{step_prefix}.parent_integration.error",
                phase="parent_integration",
                action="父业整合运行异常，保持父业候选不变",
                status="rejected",
                **error_data,
            )
        parent_integration_results.append(parent_integration_result)
        if parent_integration_result.get("status") == "integrated":
            latest_root_integration = parent_integration_result

    summary = {
        "selected_child_jobs": [str(job["job_id"]) for job in selected_children],
        "dispatch_results": dispatch_results,
        "parent_integration_results": parent_integration_results,
        "latest_parent_candidate_text": (
            latest_root_integration.get("candidate_text") if latest_root_integration else ""
        ),
        "latest_parent_candidate_appearance_id": (
            latest_root_integration.get("candidate_appearance_id") if latest_root_integration else ""
        ),
        "frontier_job_count": len(active_child_frontier),
        "frontier_dispatch_limit": max_child_dispatches,
    }
    finish_data = {
        **turn_field(turn),
        "root_job_id": root_job_id,
        "frontier_dispatch_summary": json.dumps(
            summary, ensure_ascii=False, sort_keys=True, indent=2
        ),
    }
    flow.write(FLOW_FRONTIER_DISPATCH_FINISHED, "frontier child dispatch finished", **finish_data)
    write_job_tree_mirror(
        flow=flow,
        service=service,
        turn=turn,
        job_id=root_job_id,
        action="frontier_dispatch_finished",
    )
    write_process_step(
        flow=flow,
        step=f"{step_prefix}.finish",
        phase="frontier_dispatch",
        action="完成本轮前沿子业受控调度",
        **finish_data,
    )
    return summary


def run_advancement_loop(
    *,
    flow: FlowWriter,
    service: RuntimeService,
    client: ChatClient,
    root_job_id: str,
    user_input: str,
    root_method: MethodContext,
    root_candidate_text: str,
    root_candidate_appearance_id: str,
    step_prefix: str,
    turn: str | None = None,
    max_advancement_waves: int = DEFAULT_MAX_ADVANCEMENT_WAVES,
    max_child_dispatches: int = DEFAULT_MAX_FRONTIER_DISPATCHES,
    max_child_package_repair_attempts: int = DEFAULT_MAX_CHILD_PACKAGE_REPAIR_ATTEMPTS,
    max_parent_integration_repair_attempts: int = DEFAULT_MAX_PARENT_INTEGRATION_REPAIR_ATTEMPTS,
) -> dict[str, Any]:
    max_advancement_waves = normalize_max_advancement_waves(max_advancement_waves)
    latest_candidate_text = root_candidate_text
    latest_candidate_appearance_id = root_candidate_appearance_id
    wave_results: list[dict[str, Any]] = []
    stop_reason = "wave limit reached"

    if max_advancement_waves == 0:
        stop_reason = "advancement wave limit is zero"

    for wave in range(1, max_advancement_waves + 1):
        wave_data = {
            **turn_field(turn),
            "root_job_id": root_job_id,
            "job_id": root_job_id,
            "advancement_wave": str(wave),
            "advancement_wave_limit": str(max_advancement_waves),
        }
        flow.write(FLOW_ADVANCEMENT_WAVE_STARTED, "advancement wave started", **wave_data)
        write_process_step(
            flow=flow,
            step=f"{step_prefix}.wave_{wave}.start",
            phase="advancement",
            action="开始受控推进波次",
            status="started",
            **wave_data,
        )
        result = run_frontier_child_dispatch(
            flow=flow,
            service=service,
            client=client,
            root_job_id=root_job_id,
            user_input=user_input,
            root_method=root_method,
            root_candidate_text=latest_candidate_text,
            root_candidate_appearance_id=latest_candidate_appearance_id,
            step_prefix=f"{step_prefix}.wave_{wave}",
            turn=turn,
            max_child_dispatches=max_child_dispatches,
            max_child_package_repair_attempts=max_child_package_repair_attempts,
            max_parent_integration_repair_attempts=max_parent_integration_repair_attempts,
        )
        wave_results.append(result)
        if result.get("latest_parent_candidate_text") and result.get("latest_parent_candidate_appearance_id"):
            latest_candidate_text = str(result["latest_parent_candidate_text"])
            latest_candidate_appearance_id = str(result["latest_parent_candidate_appearance_id"])
        selected_child_jobs = result.get("selected_child_jobs") or []
        wave_finish_data = {
            **wave_data,
            "frontier_dispatch_summary": json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2),
        }
        flow.write(FLOW_ADVANCEMENT_WAVE_FINISHED, "advancement wave finished", **wave_finish_data)
        write_process_step(
            flow=flow,
            step=f"{step_prefix}.wave_{wave}.finish",
            phase="advancement",
            action="完成受控推进波次",
            **wave_finish_data,
        )
        if not selected_child_jobs:
            stop_reason = str(result.get("skipped_reason") or "no active frontier after wave")
            break

    summary = {
        "wave_results": wave_results,
        "advancement_wave_count": len(wave_results),
        "advancement_wave_limit": max_advancement_waves,
        "advancement_stop_reason": stop_reason,
        "latest_parent_candidate_text": latest_candidate_text,
        "latest_parent_candidate_appearance_id": latest_candidate_appearance_id,
    }
    finish_data = {
        **turn_field(turn),
        "root_job_id": root_job_id,
        "job_id": root_job_id,
        "advancement_wave_count": str(len(wave_results)),
        "advancement_wave_limit": str(max_advancement_waves),
        "advancement_stop_reason": stop_reason,
        "frontier_dispatch_summary": json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2),
    }
    flow.write(FLOW_ADVANCEMENT_LOOP_FINISHED, "advancement loop finished", **finish_data)
    write_process_step(
        flow=flow,
        step=f"{step_prefix}.finish",
        phase="advancement",
        action="受控推进循环结束",
        **finish_data,
    )
    return summary


def load_child_dispatch_method(
    *,
    child_job: dict[str, Any],
    root_method: MethodContext,
) -> tuple[MethodContext, str]:
    frames = child_job.get("method_call_frames") or []
    if isinstance(frames, list):
        for frame in reversed(frames):
            if not isinstance(frame, dict):
                continue
            method_path = str(frame.get("method_path") or "").strip()
            if not method_path:
                continue
            try:
                return load_method_context(method_path=Path(method_path)), "child_method_call_frame"
            except Exception as exc:
                return root_method, f"child_method_load_failed; fallback_to_root_method: {exc}"
    return root_method, "root_method_fallback"


def run_child_package_review_loop(
    *,
    flow: FlowWriter,
    service: RuntimeService,
    client: ChatClient,
    child_method: MethodContext,
    root_job_id: str,
    parent_job_id: str,
    child_job: dict[str, Any],
    user_input: str,
    root_candidate_text: str,
    root_candidate_appearance_id: str,
    package: dict[str, Any],
    package_text: str,
    candidate_id: str,
    evidence_id: str,
    step_prefix: str,
    turn: str | None = None,
    repair_attempt: int = 0,
    max_repair_attempts: int = DEFAULT_MAX_CHILD_PACKAGE_REPAIR_ATTEMPTS,
) -> dict[str, Any]:
    child_job_id = str(child_job["job_id"])
    messages = build_child_package_review_messages(
        child_job=child_job,
        package=package,
        package_candidate_id=candidate_id,
        package_evidence_id=evidence_id,
        root_job_id=root_job_id,
        parent_job_id=parent_job_id,
        user_input=user_input,
        root_candidate_text=root_candidate_text,
        root_candidate_appearance_id=root_candidate_appearance_id,
        repair_attempt=repair_attempt,
        max_repair_attempts=max_repair_attempts,
    )
    request_data = {
        **turn_field(turn),
        "root_job_id": root_job_id,
        "parent_job_id": parent_job_id,
        "job_id": child_job_id,
        "child_job_id": child_job_id,
        "child_result_package_candidate_id": candidate_id,
        "child_result_package_evidence_id": evidence_id,
        "child_package_repair_attempt": str(repair_attempt),
        "child_package_repair_limit": str(max_repair_attempts),
        "child_package_review_prompt": messages[-1]["content"],
        "provider_message_count": str(len(messages)),
    }
    flow.write(FLOW_CHILD_PACKAGE_REVIEW_REQUESTED, "child package review requested", **request_data)
    write_job_tree_mirror(
        flow=flow,
        service=service,
        turn=turn,
        job_id=child_job_id,
        action="child_package_review_requested",
        appearance_id=candidate_id,
        child_job_id=child_job_id,
    )
    write_provider_messages(
        flow=flow,
        call_kind="child_package_review",
        messages=messages,
        turn=turn,
        job_id=child_job_id,
    )
    write_process_step(
        flow=flow,
        step=f"{step_prefix}.review_{repair_attempt}.request",
        phase="child_package_review",
        action="向独立验收位发送子业果包、子业契约和父业消费要求",
        status="started",
        **request_data,
    )

    response = complete_with_provider_logging(
        flow=flow,
        client=client,
        messages=messages,
        call_kind="child_package_review",
        turn=turn,
        job_id=child_job_id,
    )
    response_data = {
        **turn_field(turn),
        "root_job_id": root_job_id,
        "parent_job_id": parent_job_id,
        "job_id": child_job_id,
        "child_job_id": child_job_id,
        "child_package_repair_attempt": str(repair_attempt),
        "child_package_review_judgment": response.content,
    }
    flow.write(FLOW_CHILD_PACKAGE_REVIEW_RECEIVED, "child package review received", **response_data)
    write_process_step(
        flow=flow,
        step=f"{step_prefix}.review_{repair_attempt}.receive",
        phase="child_package_review",
        action="收到独立验收位对子业果包的判断",
        **response_data,
    )

    try:
        judgment = parse_child_package_review_judgment(response.content)
    except RuntimeError as exc:
        rejected_data = {
            **response_data,
            "reason": str(exc),
        }
        flow.write(
            FLOW_CHILD_PACKAGE_REVIEW_REJECTED,
            "child package review rejected",
            **rejected_data,
        )
        write_job_tree_mirror(
            flow=flow,
            service=service,
            turn=turn,
            job_id=child_job_id,
            action="child_package_review_rejected",
            reason=str(exc),
        )
        write_process_step(
            flow=flow,
            step=f"{step_prefix}.review_{repair_attempt}.invalid",
            phase="child_package_review",
            action="子业果包验收响应不符合结构化契约，保持候选隔离",
            status="rejected",
            **rejected_data,
        )
        return {"status": "review_invalid", "reason": str(exc)}

    review_text = json.dumps(judgment, ensure_ascii=False, sort_keys=True, indent=2)
    if judgment["review_action"] == "accept":
        return {
            "status": "accept_ready",
            "child_job_id": child_job_id,
            "candidate_id": candidate_id,
            "evidence_id": evidence_id,
            "package": package,
            "package_text": package_text,
            "judgment": judgment,
            "review_text": review_text,
        }

    if repair_attempt >= max_repair_attempts:
        limit_data = {
            **turn_field(turn),
            "root_job_id": root_job_id,
            "parent_job_id": parent_job_id,
            "job_id": child_job_id,
            "child_job_id": child_job_id,
            "child_package_repair_attempt": str(repair_attempt),
            "child_package_repair_limit": str(max_repair_attempts),
            "child_package_review_action": judgment["review_action"],
            "child_package_review_judgment": review_text,
            "child_package_repair_instruction": judgment["repair_instruction"],
        }
        flow.write(
            FLOW_CHILD_PACKAGE_REPAIR_LIMIT_REACHED,
            "child package repair limit reached",
            **limit_data,
        )
        write_job_tree_mirror(
            flow=flow,
            service=service,
            turn=turn,
            job_id=child_job_id,
            action="child_package_repair_limit_reached",
            reason=judgment["repair_instruction"],
        )
        write_process_step(
            flow=flow,
            step=f"{step_prefix}.review_{repair_attempt}.repair_limit",
            phase="child_package_review",
            action="验收位要求修复但修复次数已达上限，保持子业未接收",
            status="rejected",
            **limit_data,
        )
        return {"status": "repair_limit", "judgment": judgment, "reason": judgment["repair_instruction"]}

    review_evidence = service.submit_evidence(
        child_job_id,
        text=review_text,
        actor_id="ai_reviewer",
        metadata={
            "evidence_kind": "child_package_review",
            "evidence_hardness": "weak_ai_review",
        },
    )["evidence"]
    service.reject_candidate(
        child_job_id,
        candidate_appearance_id=candidate_id,
        reason=judgment["repair_instruction"],
        actor_id="ai_reviewer",
    )
    repair_request_data = {
        **turn_field(turn),
        "root_job_id": root_job_id,
        "parent_job_id": parent_job_id,
        "job_id": child_job_id,
        "child_job_id": child_job_id,
        "child_package_review_action": judgment["review_action"],
        "child_package_review_judgment": review_text,
        "child_package_review_evidence_id": review_evidence["appearance_id"],
        "evidence_kind": "child_package_review",
        "evidence_hardness": "weak_ai_review",
        "child_package_repair_instruction": judgment["repair_instruction"],
        "child_package_repair_attempt": str(repair_attempt + 1),
        "child_package_repair_limit": str(max_repair_attempts),
    }
    flow.write(
        FLOW_CHILD_PACKAGE_REVIEW_REJECTED,
        "child package review rejected",
        **repair_request_data,
    )
    write_job_tree_mirror(
        flow=flow,
        service=service,
        turn=turn,
        job_id=child_job_id,
        action="child_package_review_rejected",
        appearance_id=candidate_id,
        child_job_id=child_job_id,
        reason=judgment["repair_instruction"],
    )

    repair_job = service.create_child_job(
        parent_job_id=child_job_id,
        target=f"修复子业果包：{child_job.get('target') or child_job_id}",
        acceptance_criteria=judgment["repair_instruction"],
        required_context_gaps=[],
        actor_id="system",
    )
    repair_job_id = str(repair_job["job_id"])
    write_job_tree_mirror(
        flow=flow,
        service=service,
        turn=turn,
        job_id=repair_job_id,
        action="child_package_repair_child_created",
        child_job_id=repair_job_id,
        reason=judgment["repair_instruction"],
    )
    service.mark_ready(repair_job_id, actor_id="system")
    service.start_job(repair_job_id, actor_id="system")
    write_job_tree_mirror(
        flow=flow,
        service=service,
        turn=turn,
        job_id=repair_job_id,
        action="child_package_repair_child_running",
        child_job_id=repair_job_id,
    )

    repair_messages = build_child_package_repair_messages(
        method=child_method,
        repair_job_id=repair_job_id,
        child_job=child_job,
        package=package,
        review_judgment=judgment,
        repair_attempt=repair_attempt + 1,
        max_repair_attempts=max_repair_attempts,
    )
    repair_prompt_data = {
        **repair_request_data,
        "job_id": repair_job_id,
        "child_package_repair_job_id": repair_job_id,
        "provider_message_count": str(len(repair_messages)),
    }
    flow.write(
        FLOW_CHILD_PACKAGE_REPAIR_REQUESTED,
        "child package repair requested",
        **repair_prompt_data,
    )
    write_provider_messages(
        flow=flow,
        call_kind="child_package_repair",
        messages=repair_messages,
        turn=turn,
        job_id=repair_job_id,
    )
    write_process_step(
        flow=flow,
        step=f"{step_prefix}.repair_{repair_attempt + 1}.request",
        phase="child_package_repair",
        action="创建修复业并向执行端发送子业果包修复指令",
        status="started",
        **repair_prompt_data,
    )

    repair_response = complete_with_provider_logging(
        flow=flow,
        client=client,
        messages=repair_messages,
        call_kind="child_package_repair",
        turn=turn,
        job_id=repair_job_id,
    )
    repair_response_data = {
        **turn_field(turn),
        "root_job_id": root_job_id,
        "parent_job_id": parent_job_id,
        "job_id": repair_job_id,
        "child_job_id": child_job_id,
        "child_package_repair_job_id": repair_job_id,
        "child_package_repair_attempt": str(repair_attempt + 1),
        "child_package_repair_response": repair_response.content,
    }
    flow.write(
        FLOW_CHILD_PACKAGE_REPAIR_RESPONSE_RECEIVED,
        "child package repair response received",
        **repair_response_data,
    )

    try:
        repaired_package = parse_child_result_package(repair_response.content)
    except RuntimeError as exc:
        repair_rejected_data = {**repair_response_data, "reason": str(exc)}
        flow.write(
            FLOW_CHILD_PACKAGE_REPAIR_REJECTED,
            "child package repair rejected",
            **repair_rejected_data,
        )
        write_job_tree_mirror(
            flow=flow,
            service=service,
            turn=turn,
            job_id=repair_job_id,
            action="child_package_repair_rejected",
            reason=str(exc),
        )
        return {"status": "repair_invalid", "reason": str(exc)}

    repair_evidence_text = json.dumps(
        {
            "repair_instruction": judgment["repair_instruction"],
            "repair_attempt": repair_attempt + 1,
            "source_child_job_id": child_job_id,
        },
        ensure_ascii=False,
        sort_keys=True,
        indent=2,
    )
    repair_candidate = service.submit_candidate(
        repair_job_id,
        text=repair_response.content,
        actor_id="ai",
        metadata={
            "appearance_kind": "child_package_repair_candidate",
            "candidate_only": True,
        },
    )["candidate"]
    repair_evidence = service.submit_evidence(
        repair_job_id,
        text=repair_evidence_text,
        actor_id="system",
        metadata={
            "evidence_kind": "child_package_repair",
            "evidence_hardness": "weak_ai",
        },
    )["evidence"]
    service.accept_candidate(
        repair_job_id,
        candidate_appearance_id=repair_candidate["appearance_id"],
        evidence_appearance_id=repair_evidence["appearance_id"],
        actor_id="ai_reviewer",
    )

    service.start_job(child_job_id, actor_id="system")
    repaired_package_text = json.dumps(repaired_package, ensure_ascii=False, sort_keys=True, indent=2)
    submitted = TreeService(service.paths.workspace).submit_result_package(
        child_job_id,
        package=repaired_package,
        evidence_text=repaired_package_text,
        actor_id="ai",
    )
    repaired_candidate_id = str(submitted["candidate"]["appearance_id"])
    repaired_evidence_id = str(submitted["evidence"]["appearance_id"])
    repaired_data = {
        **turn_field(turn),
        "root_job_id": root_job_id,
        "parent_job_id": parent_job_id,
        "job_id": child_job_id,
        "child_job_id": child_job_id,
        "child_package_repair_job_id": repair_job_id,
        "child_package_repair_attempt": str(repair_attempt + 1),
        "child_result_package": repaired_package_text,
        "child_result_package_candidate_id": repaired_candidate_id,
        "child_result_package_evidence_id": repaired_evidence_id,
        "evidence_kind": "result_package_evidence",
        "evidence_hardness": "ai_or_manual_package",
    }
    flow.write(
        FLOW_CHILD_PACKAGE_REPAIR_PACKAGE_SUBMITTED,
        "child package repair package submitted",
        **repaired_data,
    )
    write_job_tree_mirror(
        flow=flow,
        service=service,
        turn=turn,
        job_id=child_job_id,
        action="child_package_repair_package_submitted",
        appearance_id=repaired_candidate_id,
        child_job_id=repair_job_id,
    )
    write_process_step(
        flow=flow,
        step=f"{step_prefix}.repair_{repair_attempt + 1}.package",
        phase="child_package_repair",
        action="修复业产出的果包已重新提交回原子业",
        **repaired_data,
    )

    refreshed_child = service.get_status(child_job_id)
    return run_child_package_review_loop(
        flow=flow,
        service=service,
        client=client,
        child_method=child_method,
        root_job_id=root_job_id,
        parent_job_id=parent_job_id,
        child_job=refreshed_child,
        user_input=user_input,
        root_candidate_text=root_candidate_text,
        root_candidate_appearance_id=root_candidate_appearance_id,
        package=repaired_package,
        package_text=repaired_package_text,
        candidate_id=repaired_candidate_id,
        evidence_id=repaired_evidence_id,
        step_prefix=step_prefix,
        turn=turn,
        repair_attempt=repair_attempt + 1,
        max_repair_attempts=max_repair_attempts,
    )


def accept_reviewed_child_package(
    *,
    flow: FlowWriter,
    service: RuntimeService,
    root_job_id: str,
    parent_job_id: str,
    child_job_id: str,
    candidate_id: str,
    judgment: dict[str, Any],
    review_text: str,
    step_prefix: str,
    turn: str | None = None,
) -> dict[str, Any]:
    review_evidence = service.submit_evidence(
        child_job_id,
        text=review_text,
        actor_id="ai_reviewer",
        metadata={
            "evidence_kind": "child_package_review",
            "evidence_hardness": "weak_ai_review",
        },
    )["evidence"]
    accepted_job = service.accept_candidate(
        child_job_id,
        candidate_appearance_id=candidate_id,
        evidence_appearance_id=review_evidence["appearance_id"],
        actor_id="ai_reviewer",
    )
    accepted_data = {
        **turn_field(turn),
        "root_job_id": root_job_id,
        "parent_job_id": parent_job_id,
        "job_id": child_job_id,
        "child_job_id": child_job_id,
        "child_result_package_candidate_id": candidate_id,
        "child_package_review_action": judgment["review_action"],
        "child_package_review_checks": json.dumps(
            judgment["checks"], ensure_ascii=False, sort_keys=True, indent=2
        ),
        "child_package_review_evidence": json.dumps(
            judgment["evidence"], ensure_ascii=False, sort_keys=True, indent=2
        ),
        "child_package_review_evidence_id": review_evidence["appearance_id"],
        "evidence_kind": "child_package_review",
        "evidence_hardness": "weak_ai_review",
        "parent_consumption_summary": judgment["parent_consumption_summary"],
    }
    flow.write(
        FLOW_CHILD_PACKAGE_REVIEW_ACCEPTED,
        "child package review accepted",
        **accepted_data,
    )
    write_job_tree_mirror(
        flow=flow,
        service=service,
        turn=turn,
        job_id=child_job_id,
        action="child_package_accepted",
        appearance_id=candidate_id,
        child_job_id=child_job_id,
    )
    write_process_step(
        flow=flow,
        step=f"{step_prefix}.accept",
        phase="child_package_review",
        action="通过运行时服务接收已验收的子业果包",
        **accepted_data,
    )

    parent_reevaluation = TreeService(service.paths.workspace).reevaluate_parent(parent_job_id)
    reevaluation_data = {
        **turn_field(turn),
        "root_job_id": root_job_id,
        "parent_job_id": parent_job_id,
        "job_id": parent_job_id,
        "child_job_id": child_job_id,
        "accepted_parent_reevaluation": json.dumps(
            parent_reevaluation, ensure_ascii=False, sort_keys=True, indent=2
        ),
        "parent_consumption_summary": judgment["parent_consumption_summary"],
    }
    flow.write(
        FLOW_ACCEPTED_PARENT_REEVALUATION_RECORDED,
        "accepted parent re-evaluation recorded",
        **reevaluation_data,
    )
    write_job_tree_mirror(
        flow=flow,
        service=service,
        turn=turn,
        job_id=parent_job_id,
        action="accepted_parent_reevaluation_recorded",
        child_job_id=child_job_id,
    )
    write_process_step(
        flow=flow,
        step=f"{step_prefix}.parent_reevaluate_accepted",
        phase="child_package_review",
        action="记录已接收子业果包后的父业重评估",
        **reevaluation_data,
    )
    return {"job": accepted_job, "review_evidence": review_evidence, "parent_reevaluation": parent_reevaluation}


def read_accepted_child_packages(
    *,
    service: RuntimeService,
    parent_job_id: str,
) -> dict[str, Any]:
    packages: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    with service.repository.transaction() as connection:
        service.repository.require_job(connection, parent_job_id)
        children = service.repository.list_child_jobs(connection, parent_job_id)
        for child in children:
            child_job_id = str(child["job_id"])
            child_state = str(child.get("state") or "")
            if child_state != STATE_ACCEPTED:
                skipped.append(
                    {
                        "job_id": child_job_id,
                        "state": child_state,
                        "reason": "child is not accepted",
                    }
                )
                continue
            result_appearance_id = str(child.get("result_appearance_id") or "")
            evidence_appearance_id = str(child.get("evidence_appearance_id") or "")
            if not result_appearance_id:
                skipped.append(
                    {
                        "job_id": child_job_id,
                        "state": child_state,
                        "reason": "accepted child has no result appearance",
                    }
                )
                continue
            appearance = service.repository.get_appearance(connection, result_appearance_id)
            if not appearance or not appearance.get("location"):
                skipped.append(
                    {
                        "job_id": child_job_id,
                        "state": child_state,
                        "reason": "accepted child result appearance is missing location",
                    }
                )
                continue
            metadata = decode_json(appearance.get("metadata"), {})
            if metadata.get("kind") != RESULT_PACKAGE_METADATA_KIND:
                skipped.append(
                    {
                        "job_id": child_job_id,
                        "state": child_state,
                        "reason": "accepted child result is not a structured result package",
                    }
                )
                continue
            content_path = service.paths.resolve_runtime_location(str(appearance["location"]))
            if not content_path.exists():
                skipped.append(
                    {
                        "job_id": child_job_id,
                        "state": child_state,
                        "reason": "accepted child result object is missing",
                    }
                )
                continue
            try:
                package_text = content_path.read_text(encoding="utf-8")
                package = json.loads(package_text)
            except (OSError, json.JSONDecodeError) as exc:
                skipped.append(
                    {
                        "job_id": child_job_id,
                        "state": child_state,
                        "reason": f"accepted child result package cannot be read as JSON: {exc}",
                    }
                )
                continue
            if not isinstance(package, dict):
                skipped.append(
                    {
                        "job_id": child_job_id,
                        "state": child_state,
                        "reason": "accepted child result package is not a JSON object",
                    }
                )
                continue
            missing = [field for field in CHILD_RESULT_PACKAGE_FIELDS if field not in package]
            if missing:
                skipped.append(
                    {
                        "job_id": child_job_id,
                        "state": child_state,
                        "reason": "accepted child result package is missing fields: "
                        + ", ".join(sorted(missing)),
                    }
                )
                continue
            packages.append(
                {
                    "job_id": child_job_id,
                    "target": str(child.get("target") or ""),
                    "result_appearance_id": result_appearance_id,
                    "evidence_appearance_id": evidence_appearance_id,
                    "package": package,
                    "package_text": package_text,
                }
            )
    return {"packages": packages, "skipped": skipped}


def build_parent_integration_messages(
    *,
    method: MethodContext,
    parent_job: dict[str, Any],
    root_job_id: str,
    user_input: str,
    root_candidate_text: str,
    root_candidate_appearance_id: str,
    parent_reevaluation: dict[str, Any],
    accepted_child_packages: list[dict[str, Any]],
    turn: str | None = None,
) -> list[dict[str, str]]:
    child_job_ids = [item["job_id"] for item in accepted_child_packages]
    payload = {
        "turn": turn or "",
        "root_job_id": root_job_id,
        "parent_job": {
            "job_id": parent_job.get("job_id"),
            "parent_job_id": parent_job.get("parent_job_id"),
            "target": parent_job.get("target"),
            "state": parent_job.get("state"),
            "acceptance_criteria": parent_job.get("acceptance_criteria", ""),
            "required_context_gaps": parent_job.get("required_context_gaps", []),
        },
        "root_user_input": user_input,
        "root_candidate": {
            "candidate_appearance_id": root_candidate_appearance_id,
            "text": root_candidate_text,
        },
        "parent_reevaluation": parent_reevaluation,
        "accepted_child_packages": [
            {
                "job_id": item["job_id"],
                "target": item["target"],
                "result_appearance_id": item["result_appearance_id"],
                "evidence_appearance_id": item["evidence_appearance_id"],
                "package": item["package"],
            }
            for item in accepted_child_packages
        ],
        "integration_contract": {
            "top_level": "JSON object only",
            "required_fields": list(PARENT_INTEGRATION_REQUIRED_FIELDS),
            "field_types": {
                "integrated_candidate_text": "non-empty string; the complete parent-scope candidate after consuming accepted child packages",
                "consumed_child_jobs": "non-empty list of accepted child job ids consumed in this integration",
                "evidence": "non-empty list of strings explaining why each child package was used",
                "open_gaps": "list of remaining parent-level gaps or questions",
                "suggested_follow_up_jobs": "list of parent-level follow-up job targets if new blocking work is visible",
                "parent_consumption_summary": "non-empty string summarizing how the parent consumed child packages",
            },
            "allowed_consumed_child_jobs": child_job_ids,
            "boundaries": [
                "Do not accept, reject, or complete the parent job.",
                "Do not accept, reject, or complete the root job.",
                "Only consume child packages listed in accepted_child_packages.",
                "If a child package is insufficient, put the remaining problem in open_gaps or suggested_follow_up_jobs.",
                "Return complete parent-scope candidate text; do not return only a summary unless the parent target itself only asks for a summary.",
            ],
        },
    }
    return [
        *build_method_system_messages(method),
        {
            "role": "system",
            "content": (
                "你是金箍业树中的父业整合位。"
                "你只能把已接收子业果包整合成父业候选结果和证据，"
                "不能接收、拒收或宣告父业或根业完成。"
                "只返回 JSON，不要输出解释性正文。"
            ),
        },
        {
            "role": "user",
            "content": json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2),
        },
    ]


def parse_parent_integration_output(
    content: str,
    *,
    accepted_child_job_ids: set[str],
) -> dict[str, Any]:
    payload = load_json_object(content, error_prefix="parent integration response")
    if not isinstance(payload, dict):
        raise RuntimeError("parent integration response must be a JSON object")
    missing = [
        field
        for field in PARENT_INTEGRATION_REQUIRED_FIELDS
        if field not in payload
    ]
    if missing:
        raise RuntimeError(
            "parent integration response is missing fields: " + ", ".join(sorted(missing))
        )

    integrated_candidate_text = str(payload.get("integrated_candidate_text") or "").strip()
    if not integrated_candidate_text:
        raise RuntimeError("parent integration response integrated_candidate_text is required")
    consumed_child_jobs = normalize_string_list(
        payload.get("consumed_child_jobs") or [],
        field_name="consumed_child_jobs",
        error_prefix="parent integration response",
    )
    consumed_child_jobs = list(dict.fromkeys(consumed_child_jobs))
    if not consumed_child_jobs:
        raise RuntimeError("parent integration response consumed_child_jobs must be non-empty")
    invalid_consumed = [
        job_id for job_id in consumed_child_jobs if job_id not in accepted_child_job_ids
    ]
    if invalid_consumed:
        raise RuntimeError(
            "parent integration response consumed unaccepted child jobs: "
            + ", ".join(invalid_consumed)
        )

    evidence = normalize_string_list(
        payload.get("evidence") or [],
        field_name="evidence",
        error_prefix="parent integration response",
    )
    if not evidence:
        raise RuntimeError("parent integration response evidence must be non-empty")
    open_gaps = normalize_string_list(
        payload.get("open_gaps") or [],
        field_name="open_gaps",
        error_prefix="parent integration response",
    )
    suggested_follow_up_jobs = normalize_string_list(
        payload.get("suggested_follow_up_jobs") or [],
        field_name="suggested_follow_up_jobs",
        error_prefix="parent integration response",
    )
    parent_consumption_summary = str(payload.get("parent_consumption_summary") or "").strip()
    if not parent_consumption_summary:
        raise RuntimeError("parent integration response parent_consumption_summary is required")
    return {
        "integrated_candidate_text": integrated_candidate_text,
        "consumed_child_jobs": consumed_child_jobs,
        "evidence": evidence,
        "open_gaps": open_gaps,
        "suggested_follow_up_jobs": suggested_follow_up_jobs,
        "parent_consumption_summary": parent_consumption_summary,
        "does_not_auto_accept_or_reject": True,
    }


def build_parent_integration_evidence(
    *,
    integration: dict[str, Any],
    parent_candidate_appearance_id: str,
    accepted_child_packages: list[dict[str, Any]],
    parent_integration_job_id: str = "",
    parent_integration_repair_job_id: str = "",
) -> str:
    payload = {
        "evidence_kind": "parent_integration_evidence",
        "evidence_hardness": "weak_ai",
        "parent_integration_job_id": parent_integration_job_id,
        "parent_integration_repair_job_id": parent_integration_repair_job_id,
        "parent_integration_candidate_appearance_id": parent_candidate_appearance_id,
        "consumed_child_jobs": integration["consumed_child_jobs"],
        "integrator_evidence": integration["evidence"],
        "open_gaps": integration["open_gaps"],
        "suggested_follow_up_jobs": integration["suggested_follow_up_jobs"],
        "parent_consumption_summary": integration["parent_consumption_summary"],
        "accepted_child_package_refs": [
            {
                "job_id": item["job_id"],
                "result_appearance_id": item["result_appearance_id"],
                "evidence_appearance_id": item["evidence_appearance_id"],
            }
            for item in accepted_child_packages
            if item["job_id"] in set(integration["consumed_child_jobs"])
        ],
        "does_not_auto_accept_or_reject": True,
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2)


def build_parent_integration_lineage(
    *,
    root_candidate_appearance_id: str,
    parent_integration_job_id: str,
    parent_integration_repair_job_id: str,
    accepted_child_packages: list[dict[str, Any]],
    integration: dict[str, Any],
) -> dict[str, Any]:
    consumed = set(integration["consumed_child_jobs"])
    return {
        "upstream_candidate_appearance_id": root_candidate_appearance_id,
        "parent_integration_job_id": parent_integration_job_id,
        "parent_integration_repair_job_id": parent_integration_repair_job_id,
        "consumed_child_package_refs": [
            {
                "job_id": item["job_id"],
                "result_appearance_id": item["result_appearance_id"],
                "evidence_appearance_id": item["evidence_appearance_id"],
            }
            for item in accepted_child_packages
            if item["job_id"] in consumed
        ],
    }


def build_parent_integration_repair_messages(
    *,
    method: MethodContext,
    parent_job: dict[str, Any],
    root_job_id: str,
    parent_job_id: str,
    user_input: str,
    root_candidate_text: str,
    root_candidate_appearance_id: str,
    parent_reevaluation: dict[str, Any],
    accepted_child_packages: list[dict[str, Any]],
    invalid_response: str,
    validation_error: str,
    attempt: int,
    max_attempts: int,
    turn: str | None = None,
) -> list[dict[str, str]]:
    payload = {
        "turn": turn or "",
        "root_job_id": root_job_id,
        "parent_job_id": parent_job_id,
        "parent_job": {
            "job_id": parent_job.get("job_id"),
            "target": parent_job.get("target"),
            "state": parent_job.get("state"),
            "acceptance_criteria": parent_job.get("acceptance_criteria", ""),
        },
        "root_user_input": user_input,
        "root_candidate": {
            "candidate_appearance_id": root_candidate_appearance_id,
            "text": root_candidate_text,
        },
        "parent_reevaluation": parent_reevaluation,
        "accepted_child_packages": accepted_child_packages,
        "invalid_parent_integration_response": invalid_response,
        "validation_error": validation_error,
        "repair_budget": {
            "attempt": attempt,
            "max_attempts": max_attempts,
        },
        "integration_contract": {
            "top_level": "JSON object only",
            "required_fields": list(PARENT_INTEGRATION_REQUIRED_FIELDS),
            "allowed_consumed_child_jobs": [item["job_id"] for item in accepted_child_packages],
            "boundaries": [
                "Repair only the JSON contract and missing/invalid fields.",
                "Do not accept, reject, or complete the parent job.",
                "Only consume accepted_child_packages listed in this payload.",
                "Return complete corrected JSON only.",
            ],
        },
    }
    return [
        *build_method_system_messages(method),
        {
            "role": "system",
            "content": (
                "你是金箍业树中的父业整合修复位。"
                "你只能修复父业整合响应的结构化契约问题，不能改变父业状态或宣告完成。"
                "只返回 JSON。"
            ),
        },
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2)},
    ]


def create_running_child_job(
    *,
    flow: FlowWriter,
    service: RuntimeService,
    parent_job_id: str,
    target: str,
    acceptance_criteria: str,
    created_event_type: str,
    created_message: str,
    tree_action: str,
    step_prefix: str,
    phase: str,
    turn: str | None = None,
    extra_data: dict[str, str] | None = None,
) -> dict[str, Any]:
    job = service.create_child_job(
        parent_job_id=parent_job_id,
        target=target,
        acceptance_criteria=acceptance_criteria,
        required_context_gaps=[],
        actor_id="system",
    )
    child_job_id = str(job["job_id"])
    normalized_extra = {
        key: (child_job_id if value == "__child_job_id__" else value)
        for key, value in (extra_data or {}).items()
    }
    data = {
        **turn_field(turn),
        "job_id": parent_job_id,
        "parent_job_id": parent_job_id,
        "child_job_id": child_job_id,
        **normalized_extra,
    }
    flow.write(created_event_type, created_message, **data)
    write_job_tree_mirror(
        flow=flow,
        service=service,
        turn=turn,
        job_id=child_job_id,
        action=tree_action,
        child_job_id=child_job_id,
    )
    write_process_step(
        flow=flow,
        step=f"{step_prefix}.create",
        phase=phase,
        action="创建可观察子业",
        **data,
    )
    service.mark_ready(child_job_id, actor_id="system")
    service.start_job(child_job_id, actor_id="system")
    write_job_tree_mirror(
        flow=flow,
        service=service,
        turn=turn,
        job_id=child_job_id,
        action="job_running",
        child_job_id=child_job_id,
    )
    return job


def ensure_parent_running_for_integration(
    *,
    flow: FlowWriter,
    service: RuntimeService,
    parent_job_id: str,
    step_prefix: str,
    turn: str | None = None,
) -> None:
    status = service.get_status(parent_job_id)
    state = str(status["state"])
    if state == STATE_RUNNING:
        return
    if state in TERMINAL_JOB_STATES:
        raise RuntimeError("cannot submit parent integration candidate to terminal parent job")
    if state == STATE_DRAFT:
        service.mark_ready(parent_job_id, actor_id="system")
        ready_data = {**turn_field(turn), "job_id": parent_job_id}
        flow.write(FLOW_JOB_READY, "parent job marked ready for integration", **ready_data)
        write_job_tree_mirror(
            flow=flow,
            service=service,
            turn=turn,
            job_id=parent_job_id,
            action="job_ready",
        )
        write_process_step(
            flow=flow,
            step=f"{step_prefix}.parent_ready",
            phase="parent_integration",
            action="父业整合提交候选前将父业置为就绪",
            **ready_data,
        )
        state = STATE_READY
    if state in {STATE_READY, STATE_REVIEWING, STATE_REJECTED}:
        service.start_job(parent_job_id, actor_id="system")
        running_data = {**turn_field(turn), "job_id": parent_job_id}
        flow.write(FLOW_JOB_RUNNING, "parent job running for integration", **running_data)
        write_job_tree_mirror(
            flow=flow,
            service=service,
            turn=turn,
            job_id=parent_job_id,
            action="job_running",
        )
        write_process_step(
            flow=flow,
            step=f"{step_prefix}.parent_run",
            phase="parent_integration",
            action="父业整合提交候选前启动父业",
            **running_data,
        )
        return
    raise RuntimeError(f"parent job is not ready for integration candidate submission: {state}")


def run_parent_integration(
    *,
    flow: FlowWriter,
    service: RuntimeService,
    client: ChatClient,
    method: MethodContext,
    root_job_id: str,
    parent_job_id: str,
    user_input: str,
    root_candidate_text: str,
    root_candidate_appearance_id: str,
    step_prefix: str,
    turn: str | None = None,
    max_repair_attempts: int = DEFAULT_MAX_PARENT_INTEGRATION_REPAIR_ATTEMPTS,
) -> dict[str, Any]:
    max_repair_attempts = normalize_max_parent_integration_repair_attempts(max_repair_attempts)
    tree_service = TreeService(service.paths.workspace)
    parent_reevaluation = tree_service.reevaluate_parent(parent_job_id)
    package_read = read_accepted_child_packages(service=service, parent_job_id=parent_job_id)
    accepted_child_packages = package_read["packages"]
    skipped_child_packages = package_read["skipped"]
    base_data = {
        **turn_field(turn),
        "root_job_id": root_job_id,
        "parent_job_id": parent_job_id,
        "job_id": parent_job_id,
        "accepted_child_packages": json.dumps(
            accepted_child_packages,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        ),
        "parent_reevaluation": json.dumps(
            parent_reevaluation, ensure_ascii=False, sort_keys=True, indent=2
        ),
    }
    if skipped_child_packages:
        base_data["reason"] = json.dumps(
            skipped_child_packages, ensure_ascii=False, sort_keys=True, indent=2
        )

    if not accepted_child_packages:
        skipped_data = {
            **base_data,
            "parent_integration_status": "skipped",
            "reason": base_data.get("reason") or "no accepted child result packages",
        }
        flow.write(FLOW_PARENT_INTEGRATION_SKIPPED, "parent integration skipped", **skipped_data)
        write_job_tree_mirror(
            flow=flow,
            service=service,
            turn=turn,
            job_id=parent_job_id,
            action="parent_integration_skipped",
            reason=skipped_data["reason"],
        )
        write_process_step(
            flow=flow,
            step=f"{step_prefix}.skip",
            phase="parent_integration",
            action="没有已接收子业果包，跳过父业整合",
            status="skipped",
            **skipped_data,
        )
        return {"status": "skipped", "reason": skipped_data["reason"]}

    parent_job = service.get_status(parent_job_id)
    parent_target = str(parent_job.get("target") or parent_job_id)
    integration_job = create_running_child_job(
        flow=flow,
        service=service,
        parent_job_id=parent_job_id,
        target=f"整合已接收子业果包：{parent_target}",
        acceptance_criteria=(
            "把已接收子业果包整合为父业候选、证据、开放缺口和后续分业建议；"
            "不得接收、拒收或宣告父业/根业完成。"
        ),
        created_event_type=FLOW_PARENT_INTEGRATION_JOB_CREATED,
        created_message="parent integration job created",
        tree_action="parent_integration_job_created",
        step_prefix=f"{step_prefix}.job",
        phase="parent_integration",
        turn=turn,
        extra_data={
            "root_job_id": root_job_id,
            "parent_integration_job_id": "__child_job_id__",
            "job_target": f"整合已接收子业果包：{parent_target}",
        },
    )
    parent_integration_job_id = str(integration_job["job_id"])
    messages = build_parent_integration_messages(
        method=method,
        parent_job=parent_job,
        root_job_id=root_job_id,
        user_input=user_input,
        root_candidate_text=root_candidate_text,
        root_candidate_appearance_id=root_candidate_appearance_id,
        parent_reevaluation=parent_reevaluation,
        accepted_child_packages=accepted_child_packages,
        turn=turn,
    )
    request_data = {
        **base_data,
        "job_id": parent_integration_job_id,
        "parent_integration_job_id": parent_integration_job_id,
        "parent_integration_prompt": messages[-1]["content"],
        "parent_integration_repair_limit": str(max_repair_attempts),
        "provider_message_count": str(len(messages)),
    }
    flow.write(FLOW_PARENT_INTEGRATION_REQUESTED, "parent integration requested", **request_data)
    write_job_tree_mirror(
        flow=flow,
        service=service,
        turn=turn,
        job_id=parent_integration_job_id,
        action="parent_integration_requested",
    )
    write_provider_messages(
        flow=flow,
        call_kind="parent_job_integration",
        messages=messages,
        turn=turn,
        job_id=parent_integration_job_id,
    )
    write_process_step(
        flow=flow,
        step=f"{step_prefix}.request",
        phase="parent_integration",
        action="向父业整合位发送已接收子业果包和父业重评估",
        status="started",
        **request_data,
    )

    response = complete_with_provider_logging(
        flow=flow,
        client=client,
        messages=messages,
        call_kind="parent_job_integration",
        turn=turn,
        job_id=parent_integration_job_id,
    )
    response_data = {
        **base_data,
        "job_id": parent_integration_job_id,
        "parent_integration_job_id": parent_integration_job_id,
        "parent_integration_response": response.content,
    }
    flow.write(FLOW_PARENT_INTEGRATION_RECEIVED, "parent integration received", **response_data)
    write_process_step(
        flow=flow,
        step=f"{step_prefix}.receive",
        phase="parent_integration",
        action="收到父业整合位响应",
        **response_data,
    )

    accepted_child_job_ids = {item["job_id"] for item in accepted_child_packages}
    raw_integration_candidate = service.submit_candidate(
        parent_integration_job_id,
        text=response.content,
        actor_id="ai_integrator",
        metadata={
            "appearance_kind": "parent_integration_raw_response",
            "candidate_only": True,
        },
    )["candidate"]
    write_job_tree_mirror(
        flow=flow,
        service=service,
        turn=turn,
        job_id=parent_integration_job_id,
        action="candidate_attached",
        appearance_id=raw_integration_candidate["appearance_id"],
        child_job_id=parent_integration_job_id,
    )
    parent_integration_repair_job_id = ""
    try:
        integration = parse_parent_integration_output(
            response.content,
            accepted_child_job_ids=accepted_child_job_ids,
        )
    except RuntimeError as exc:
        parse_error = str(exc)
        rejected_data = {
            **response_data,
            "parent_integration_status": "rejected",
            "parent_integration_repair_limit": str(max_repair_attempts),
            "reason": parse_error,
        }
        flow.write(FLOW_PARENT_INTEGRATION_REJECTED, "parent integration rejected", **rejected_data)
        write_job_tree_mirror(
            flow=flow,
            service=service,
            turn=turn,
            job_id=parent_integration_job_id,
            action="parent_integration_rejected",
            reason=parse_error,
        )
        write_process_step(
            flow=flow,
            step=f"{step_prefix}.invalid",
            phase="parent_integration",
            action="父业整合响应不符合结构化契约，保持父业候选不变",
            status="rejected",
            **rejected_data,
        )
        if max_repair_attempts <= 0:
            invalid_evidence = service.submit_evidence(
                parent_integration_job_id,
                text=json.dumps(
                    {
                        "evidence_kind": "parent_integration_parse_failure",
                        "evidence_hardness": "deterministic",
                        "reason": parse_error,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                    indent=2,
                ),
                actor_id="system",
                metadata={
                    "evidence_kind": "parent_integration_parse_failure",
                    "evidence_hardness": "deterministic",
                },
            )["evidence"]
            service.reject_candidate(
                parent_integration_job_id,
                candidate_appearance_id=raw_integration_candidate["appearance_id"],
                reason=parse_error,
                actor_id="system",
            )
            return {
                "status": "rejected",
                "reason": parse_error,
                "parent_integration_job_id": parent_integration_job_id,
                "evidence_appearance_id": invalid_evidence["appearance_id"],
            }

        repair_job = create_running_child_job(
            flow=flow,
            service=service,
            parent_job_id=parent_job_id,
            target=f"修复父业整合响应：{parent_target}",
            acceptance_criteria=(
                "修复父业整合响应，使其满足整合 JSON 契约；"
                "不得改变父业完成状态，不得消费未接收子业。"
            ),
            created_event_type=FLOW_PARENT_INTEGRATION_REPAIR_JOB_CREATED,
            created_message="parent integration repair job created",
            tree_action="parent_integration_repair_child_created",
            step_prefix=f"{step_prefix}.repair_job",
            phase="parent_integration_repair",
            turn=turn,
            extra_data={
                "root_job_id": root_job_id,
                "parent_integration_job_id": parent_integration_job_id,
                "parent_integration_repair_job_id": "__child_job_id__",
                "reason": parse_error,
            },
        )
        parent_integration_repair_job_id = str(repair_job["job_id"])
        repair_messages = build_parent_integration_repair_messages(
            method=method,
            parent_job=parent_job,
            root_job_id=root_job_id,
            parent_job_id=parent_job_id,
            user_input=user_input,
            root_candidate_text=root_candidate_text,
            root_candidate_appearance_id=root_candidate_appearance_id,
            parent_reevaluation=parent_reevaluation,
            accepted_child_packages=accepted_child_packages,
            invalid_response=response.content,
            validation_error=parse_error,
            attempt=1,
            max_attempts=max_repair_attempts,
            turn=turn,
        )
        repair_request_data = {
            **turn_field(turn),
            "root_job_id": root_job_id,
            "job_id": parent_integration_repair_job_id,
            "parent_job_id": parent_job_id,
            "parent_integration_job_id": parent_integration_job_id,
            "parent_integration_repair_job_id": parent_integration_repair_job_id,
            "parent_integration_repair_attempt": "1",
            "parent_integration_repair_limit": str(max_repair_attempts),
            "parent_integration_repair_prompt": repair_messages[-1]["content"],
            "reason": parse_error,
            "provider_message_count": str(len(repair_messages)),
        }
        flow.write(
            FLOW_PARENT_INTEGRATION_REPAIR_REQUESTED,
            "parent integration repair requested",
            **repair_request_data,
        )
        write_provider_messages(
            flow=flow,
            call_kind="parent_integration_repair",
            messages=repair_messages,
            turn=turn,
            job_id=parent_integration_repair_job_id,
        )
        write_process_step(
            flow=flow,
            step=f"{step_prefix}.repair.request",
            phase="parent_integration_repair",
            action="向父业整合修复位发送无效响应、错误和修复契约",
            status="started",
            **repair_request_data,
        )
        repair_response = complete_with_provider_logging(
            flow=flow,
            client=client,
            messages=repair_messages,
            call_kind="parent_integration_repair",
            turn=turn,
            job_id=parent_integration_repair_job_id,
        )
        repair_response_data = {
            **repair_request_data,
            "parent_integration_repair_response": repair_response.content,
        }
        flow.write(
            FLOW_PARENT_INTEGRATION_REPAIR_RECEIVED,
            "parent integration repair received",
            **repair_response_data,
        )
        repair_candidate = service.submit_candidate(
            parent_integration_repair_job_id,
            text=repair_response.content,
            actor_id="ai_integrator_repair",
            metadata={
                "appearance_kind": "parent_integration_repair_response",
                "candidate_only": True,
            },
        )["candidate"]
        try:
            integration = parse_parent_integration_output(
                repair_response.content,
                accepted_child_job_ids=accepted_child_job_ids,
            )
        except RuntimeError as repair_exc:
            repair_error = str(repair_exc)
            repair_evidence = service.submit_evidence(
                parent_integration_repair_job_id,
                text=json.dumps(
                    {
                        "evidence_kind": "parent_integration_repair_parse_failure",
                        "evidence_hardness": "deterministic",
                        "reason": repair_error,
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                    indent=2,
                ),
                actor_id="system",
                metadata={
                    "evidence_kind": "parent_integration_repair_parse_failure",
                    "evidence_hardness": "deterministic",
                },
            )["evidence"]
            service.reject_candidate(
                parent_integration_repair_job_id,
                candidate_appearance_id=repair_candidate["appearance_id"],
                reason=repair_error,
                actor_id="system",
            )
            service.reject_candidate(
                parent_integration_job_id,
                candidate_appearance_id=raw_integration_candidate["appearance_id"],
                reason=parse_error,
                actor_id="system",
            )
            repair_rejected = {
                **repair_response_data,
                "parent_integration_status": "repair_rejected",
                "appearance_id": repair_candidate["appearance_id"],
                "evidence_id": repair_evidence["appearance_id"],
                "evidence_hardness": "deterministic",
                "evidence_kind": "parent_integration_repair_parse_failure",
                "reason": repair_error,
            }
            flow.write(
                FLOW_PARENT_INTEGRATION_REPAIR_REJECTED,
                "parent integration repair rejected",
                **repair_rejected,
            )
            write_job_tree_mirror(
                flow=flow,
                service=service,
                turn=turn,
                job_id=parent_integration_repair_job_id,
                action="parent_integration_repair_rejected",
                appearance_id=repair_candidate["appearance_id"],
                reason=repair_error,
            )
            return {
                "status": "rejected",
                "reason": repair_error,
                "parent_integration_job_id": parent_integration_job_id,
                "parent_integration_repair_job_id": parent_integration_repair_job_id,
            }

        repair_evidence_text = json.dumps(
            {
                "evidence_kind": "parent_integration_repair_validation",
                "evidence_hardness": "deterministic",
                "original_error": parse_error,
                "repaired_contract_valid": True,
                "consumed_child_jobs": integration["consumed_child_jobs"],
            },
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
        repair_evidence = service.submit_evidence(
            parent_integration_repair_job_id,
            text=repair_evidence_text,
            actor_id="system",
            metadata={
                "evidence_kind": "parent_integration_repair_validation",
                "evidence_hardness": "deterministic",
            },
        )["evidence"]
        service.accept_candidate(
            parent_integration_repair_job_id,
            candidate_appearance_id=repair_candidate["appearance_id"],
            evidence_appearance_id=repair_evidence["appearance_id"],
            completion_scope="self",
            actor_id="system",
        )
        flow.write(
            FLOW_PARENT_INTEGRATION_REPAIR_ACCEPTED,
            "parent integration repair accepted",
            **{
                **repair_response_data,
                "appearance_id": repair_candidate["appearance_id"],
                "evidence_id": repair_evidence["appearance_id"],
                "evidence_hardness": "deterministic",
                "evidence_kind": "parent_integration_repair_validation",
                "parent_integration_status": "repair_accepted",
            },
        )
        write_job_tree_mirror(
            flow=flow,
            service=service,
            turn=turn,
            job_id=parent_integration_repair_job_id,
            action="parent_integration_repair_accepted",
            appearance_id=repair_candidate["appearance_id"],
        )
        service.start_job(parent_integration_job_id, actor_id="system")
        repaired_integration_candidate = service.submit_candidate(
            parent_integration_job_id,
            text=repair_response.content,
            actor_id="ai_integrator_repair",
            metadata={
                "appearance_kind": "parent_integration_repaired_response",
                "candidate_only": True,
            },
        )["candidate"]
        raw_integration_candidate = repaired_integration_candidate

    integration_job_evidence_text = json.dumps(
        {
            "evidence_kind": "parent_integration_contract_validation",
            "evidence_hardness": "deterministic",
            "parent_integration_job_id": parent_integration_job_id,
            "parent_integration_repair_job_id": parent_integration_repair_job_id,
            "contract_valid": True,
            "consumed_child_jobs": integration["consumed_child_jobs"],
        },
        ensure_ascii=False,
        sort_keys=True,
        indent=2,
    )
    integration_job_evidence = service.submit_evidence(
        parent_integration_job_id,
        text=integration_job_evidence_text,
        actor_id="system",
        metadata={
            "evidence_kind": "parent_integration_contract_validation",
            "evidence_hardness": "deterministic",
        },
    )["evidence"]
    service.accept_candidate(
        parent_integration_job_id,
        candidate_appearance_id=raw_integration_candidate["appearance_id"],
        evidence_appearance_id=integration_job_evidence["appearance_id"],
        completion_scope="self",
        actor_id="system",
    )

    ensure_parent_running_for_integration(
        flow=flow,
        service=service,
        parent_job_id=parent_job_id,
        step_prefix=step_prefix,
        turn=turn,
    )
    candidate_lineage = build_parent_integration_lineage(
        root_candidate_appearance_id=root_candidate_appearance_id,
        parent_integration_job_id=parent_integration_job_id,
        parent_integration_repair_job_id=parent_integration_repair_job_id,
        accepted_child_packages=accepted_child_packages,
        integration=integration,
    )
    parent_candidate = service.submit_candidate(
        parent_job_id,
        text=integration["integrated_candidate_text"],
        actor_id="ai_integrator",
        metadata={
            "appearance_kind": "parent_integration_candidate",
            "candidate_lineage": candidate_lineage,
            "candidate_only": True,
        },
    )["candidate"]
    parent_evidence_text = build_parent_integration_evidence(
        integration=integration,
        parent_candidate_appearance_id=parent_candidate["appearance_id"],
        accepted_child_packages=accepted_child_packages,
        parent_integration_job_id=parent_integration_job_id,
        parent_integration_repair_job_id=parent_integration_repair_job_id,
    )
    parent_evidence = service.submit_evidence(
        parent_job_id,
        text=parent_evidence_text,
        actor_id="system",
        metadata={
            "evidence_kind": "parent_integration_evidence",
            "evidence_hardness": "weak_ai",
            "parent_integration_job_id": parent_integration_job_id,
        },
    )["evidence"]
    submitted_data = {
        **turn_field(turn),
        "root_job_id": root_job_id,
        "parent_job_id": parent_job_id,
        "job_id": parent_job_id,
        "parent_integration_job_id": parent_integration_job_id,
        "parent_integration_repair_job_id": parent_integration_repair_job_id,
        "parent_integration_status": "integrated",
        "parent_integration_candidate": integration["integrated_candidate_text"],
        "parent_integration_candidate_appearance_id": parent_candidate["appearance_id"],
        "parent_integration_evidence": parent_evidence_text,
        "parent_integration_evidence_appearance_id": parent_evidence["appearance_id"],
        "candidate_lineage": json.dumps(candidate_lineage, ensure_ascii=False, sort_keys=True, indent=2),
        "evidence_hardness": "weak_ai",
        "evidence_kind": "parent_integration_evidence",
        "consumed_child_jobs": json.dumps(
            integration["consumed_child_jobs"], ensure_ascii=False, sort_keys=True
        ),
        "integration_open_gaps": json.dumps(
            integration["open_gaps"], ensure_ascii=False, sort_keys=True
        ),
        "parent_integration_summary": integration["parent_consumption_summary"],
    }
    flow.write(
        FLOW_PARENT_INTEGRATION_CANDIDATE_SUBMITTED,
        "parent integration candidate submitted",
        **submitted_data,
    )
    write_job_tree_mirror(
        flow=flow,
        service=service,
        turn=turn,
        job_id=parent_job_id,
        action="parent_integration_candidate_submitted",
        appearance_id=parent_candidate["appearance_id"],
    )
    write_process_step(
        flow=flow,
        step=f"{step_prefix}.candidate_submit",
        phase="parent_integration",
        action="提交父业整合候选和证据，但不接收父业或根业",
        **submitted_data,
    )

    try:
        split_result = run_split_proposal_registration(
            flow=flow,
            service=service,
            client=client,
            method=method,
            parent_job_id=parent_job_id,
            user_input=user_input,
            candidate_text=integration["integrated_candidate_text"],
            candidate_appearance_id=parent_candidate["appearance_id"],
            step_prefix=f"{step_prefix}.split_proposal",
            turn=turn,
        )
    except Exception as exc:
        split_result = {"accepted": [], "rejected": [], "skipped_reason": str(exc)}
    followup_data = {
        **turn_field(turn),
        "root_job_id": root_job_id,
        "parent_job_id": parent_job_id,
        "job_id": parent_job_id,
        "parent_integration_status": "followup_registered",
        "split_registration_summary": json.dumps(
            split_result, ensure_ascii=False, sort_keys=True, indent=2
        ),
    }
    flow.write(
        FLOW_PARENT_INTEGRATION_FOLLOWUP_REGISTRATION_FINISHED,
        "parent integration follow-up registration finished",
        **followup_data,
    )
    write_job_tree_mirror(
        flow=flow,
        service=service,
        turn=turn,
        job_id=parent_job_id,
        action="parent_integration_followup_registered",
    )
    write_process_step(
        flow=flow,
        step=f"{step_prefix}.followup_registration",
        phase="parent_integration",
        action="父业整合候选已交给分业申请链路登记后续阻塞点",
        **followup_data,
    )
    return {
        "status": "integrated",
        "parent_job_id": parent_job_id,
        "parent_integration_job_id": parent_integration_job_id,
        "parent_integration_repair_job_id": parent_integration_repair_job_id,
        "candidate_text": integration["integrated_candidate_text"],
        "candidate_appearance_id": parent_candidate["appearance_id"],
        "evidence_appearance_id": parent_evidence["appearance_id"],
        "candidate_lineage": candidate_lineage,
        "integration": integration,
        "split_result": split_result,
    }


def build_child_dispatch_messages(
    *,
    child_job: dict[str, Any],
    method: MethodContext,
    root_job_id: str,
    parent_job_id: str,
    user_input: str,
    root_candidate_text: str,
    root_candidate_appearance_id: str,
) -> list[dict[str, str]]:
    package_contract = {
        "required_fields": list(CHILD_RESULT_PACKAGE_FIELDS),
        "field_meaning": {
            "conclusion": "当前子业在自身责任范围内形成的结论或局部成果摘要。",
            "artifacts": "可被父业消费的局部产物、引用、清单或正文片段数组。",
            "evidence_summary": "为什么认为这些局部产物能支撑父业继续推进的证据摘要。",
            "open_questions": "仍然阻塞当前子业或父业的开放问题数组。",
            "suggested_follow_up_jobs": "需要后续另立业处理的候选事项数组。",
        },
        "hard_boundaries": [
            "只返回 JSON 对象，不输出解释性正文。",
            "只能提交当前子业的候选果包，不能接收、拒收或完成任何业。",
            "不能宣告父业或根业完成。",
            "没有证据的结论必须进入 open_questions 或 suggested_follow_up_jobs。",
        ],
    }
    payload = {
        "root_job_id": root_job_id,
        "parent_job_id": parent_job_id,
        "child_job": {
            "job_id": child_job.get("job_id"),
            "target": child_job.get("target"),
            "acceptance_criteria": child_job.get("acceptance_criteria", ""),
            "required_context_gaps": child_job.get("required_context_gaps", []),
            "method_call_frames": child_job.get("method_call_frames", []),
        },
        "root_user_input": user_input,
        "root_candidate": {
            "candidate_appearance_id": root_candidate_appearance_id,
            "text": root_candidate_text,
        },
        "method_manifest": method.manifest(),
        "package_contract": package_contract,
    }
    return [
        *build_method_system_messages(method),
        {
            "role": "system",
            "content": (
                "你是金箍业树中的子业执行位。"
                "你只在当前子业责任范围内产生候选果包和证据，"
                "状态迁移、接收、拒收和完成声明只能由运行时守门器处理。"
            ),
        },
        {
            "role": "user",
            "content": json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2),
        },
    ]


def build_child_package_review_messages(
    *,
    child_job: dict[str, Any],
    package: dict[str, Any],
    package_candidate_id: str,
    package_evidence_id: str,
    root_job_id: str,
    parent_job_id: str,
    user_input: str,
    root_candidate_text: str,
    root_candidate_appearance_id: str,
    repair_attempt: int,
    max_repair_attempts: int,
) -> list[dict[str, str]]:
    payload = {
        "root_job_id": root_job_id,
        "parent_job_id": parent_job_id,
        "child_job": {
            "job_id": child_job.get("job_id"),
            "target": child_job.get("target"),
            "acceptance_criteria": child_job.get("acceptance_criteria", ""),
            "required_context_gaps": child_job.get("required_context_gaps", []),
            "method_call_frames": child_job.get("method_call_frames", []),
        },
        "root_user_input": user_input,
        "root_candidate": {
            "candidate_appearance_id": root_candidate_appearance_id,
            "text": root_candidate_text,
        },
        "child_result_package": {
            "candidate_appearance_id": package_candidate_id,
            "evidence_appearance_id": package_evidence_id,
            "package": package,
        },
        "repair_budget": {
            "current_repair_attempt": repair_attempt,
            "max_repair_attempts": max_repair_attempts,
        },
        "review_contract": {
            "top_level": "JSON object only",
            "required_fields": [
                "review_action",
                "checks",
                "evidence",
                "reason",
                "repair_instruction",
                "parent_consumption_summary",
            ],
            "review_action_values": ["accept", "repair"],
            "field_types": {
                "review_action": "accept or repair",
                "checks": "list of objects with check_id, criterion, status, evidence",
                "evidence": "list of strings",
                "reason": "non-empty string",
                "repair_instruction": "non-empty string when review_action is repair; empty string when accept",
                "parent_consumption_summary": "non-empty string explaining how the parent can consume the package or why it cannot yet consume it",
            },
            "accept_rule": "Use accept only when the package satisfies the child acceptance criteria and is safe for the parent job to consume as a child-scope result.",
            "repair_rule": "Use repair when the package is incomplete, unverifiable, lacks measurable evidence, or leaves blocking open questions.",
            "boundaries": [
                "Do not accept or reject the parent or root job.",
                "Do not claim final task completion.",
                "If a high-value or human-only decision is needed, choose repair and put the decision need in repair_instruction.",
            ],
        },
    }
    return [
        {
            "role": "system",
            "content": (
                "你是金箍业树中的独立子业果包验收位。"
                "你不执行子业，不接收父业或根业，只对当前子业候选果包给出结构化验收判断。"
                "只返回 JSON，不要输出解释性正文。"
            ),
        },
        {
            "role": "user",
            "content": json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2),
        },
    ]


def build_child_package_repair_messages(
    *,
    method: MethodContext,
    repair_job_id: str,
    child_job: dict[str, Any],
    package: dict[str, Any],
    review_judgment: dict[str, Any],
    repair_attempt: int,
    max_repair_attempts: int,
) -> list[dict[str, str]]:
    payload = {
        "repair_job_id": repair_job_id,
        "source_child_job": {
            "job_id": child_job.get("job_id"),
            "target": child_job.get("target"),
            "acceptance_criteria": child_job.get("acceptance_criteria", ""),
            "required_context_gaps": child_job.get("required_context_gaps", []),
        },
        "previous_package": package,
        "review_judgment": review_judgment,
        "repair_instruction": review_judgment["repair_instruction"],
        "repair_budget": {
            "current_repair_attempt": repair_attempt,
            "max_repair_attempts": max_repair_attempts,
        },
        "return_contract": {
            "top_level": "JSON object only",
            "required_fields": list(CHILD_RESULT_PACKAGE_FIELDS),
            "boundaries": [
                "Return the complete repaired child result package.",
                "Do not accept, reject, or complete any job.",
                "Do not return commentary outside JSON.",
            ],
        },
    }
    return [
        *build_method_system_messages(method),
        {
            "role": "system",
            "content": (
                "你是金箍业树中的子业果包修复执行位。"
                "你只根据验收位的打回理由修复当前子业果包，并返回完整结构化果包。"
            ),
        },
        {
            "role": "user",
            "content": json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2),
        },
    ]


def parse_child_result_package(content: str) -> dict[str, Any]:
    payload = load_json_object(content, error_prefix="child result package response")
    if not isinstance(payload, dict):
        raise RuntimeError("child result package response must be a JSON object")
    return payload


def parse_child_package_review_judgment(content: str) -> dict[str, Any]:
    payload = load_json_object(content, error_prefix="child package review response")
    if not isinstance(payload, dict):
        raise RuntimeError("child package review response must be a JSON object")
    action = str(payload.get("review_action") or "").strip()
    if action not in CHILD_PACKAGE_REVIEW_ACTIONS:
        raise RuntimeError("child package review response review_action must be accept or repair")
    checks = payload.get("checks")
    if not isinstance(checks, list) or not checks:
        raise RuntimeError("child package review response checks must be a non-empty list")
    normalized_checks: list[dict[str, str]] = []
    for index, item in enumerate(checks, start=1):
        if not isinstance(item, dict):
            raise RuntimeError("child package review response checks must contain objects")
        criterion = str(item.get("criterion") or "").strip()
        status = str(item.get("status") or "").strip()
        evidence = str(item.get("evidence") or "").strip()
        if not criterion or not status or not evidence:
            raise RuntimeError("child package review response check requires criterion, status, and evidence")
        normalized_checks.append(
            {
                "check_id": str(item.get("check_id") or f"check_{index}").strip(),
                "criterion": criterion,
                "status": status,
                "evidence": evidence,
            }
        )
    evidence_items = normalize_string_list(
        payload.get("evidence") or [],
        field_name="evidence",
        error_prefix="child package review response",
    )
    if not evidence_items:
        raise RuntimeError("child package review response evidence must be a non-empty list")
    reason = str(payload.get("reason") or "").strip()
    parent_consumption_summary = str(payload.get("parent_consumption_summary") or "").strip()
    repair_instruction = str(payload.get("repair_instruction") or "").strip()
    if not reason:
        raise RuntimeError("child package review response reason is required")
    if not parent_consumption_summary:
        raise RuntimeError("child package review response parent_consumption_summary is required")
    if action == "repair" and not repair_instruction:
        raise RuntimeError("child package review response repair action requires repair_instruction")
    if action == "accept":
        repair_instruction = ""
    return {
        "review_action": action,
        "checks": normalized_checks,
        "evidence": evidence_items,
        "reason": reason,
        "repair_instruction": repair_instruction,
        "parent_consumption_summary": parent_consumption_summary,
    }


def parse_split_proposals(content: str) -> list[dict[str, Any]]:
    payload = load_json_object(content, error_prefix="split proposal response")
    if not isinstance(payload, dict):
        raise RuntimeError("split proposal response must be a JSON object")
    proposals = payload.get("proposals")
    if proposals is None:
        raise RuntimeError("split proposal response must include proposals")
    if not isinstance(proposals, list):
        raise RuntimeError("split proposal response proposals must be a list")
    normalized: list[dict[str, Any]] = []
    for item in proposals:
        if not isinstance(item, dict):
            raise RuntimeError("each split proposal must be a JSON object")
        normalized.append(item)
    return normalized


def normalize_split_proposal(
    proposal: dict[str, Any],
    *,
    catalog_by_path: dict[str, dict[str, str]],
) -> dict[str, Any]:
    required = [
        "target",
        "blocking_reason",
        "output_contract",
        "acceptance_criteria",
        "estimated_effort",
        "depth_limit",
    ]
    missing = [
        field
        for field in required
        if proposal.get(field) is None or str(proposal.get(field) or "").strip() == ""
    ]
    if missing:
        raise RuntimeError(f"split proposal is missing fields: {', '.join(missing)}")

    normalized = {
        "target": str(proposal["target"]).strip(),
        "blocking_reason": str(proposal["blocking_reason"]).strip(),
        "output_contract": str(proposal["output_contract"]).strip(),
        "acceptance_criteria": str(proposal["acceptance_criteria"]).strip(),
        "estimated_effort": normalize_positive_integer_field(
            proposal["estimated_effort"],
            field_name="estimated_effort",
            error_prefix="split proposal",
        ),
        "depth_limit": normalize_positive_integer_field(
            proposal["depth_limit"],
            field_name="depth_limit",
            error_prefix="split proposal",
        ),
        "required_context_gaps": normalize_string_list(
            proposal.get("required_context_gaps") or [],
            field_name="required_context_gaps",
            error_prefix="split proposal",
        ),
    }
    method_path = str(proposal.get("method_path") or "").strip()
    method_binding_reason = str(proposal.get("method_binding_reason") or "").strip()
    method_return_point = str(proposal.get("method_return_point") or "").strip()
    if method_path:
        resolved_method_path = resolve_catalog_method_path(method_path, catalog_by_path)
        if not method_binding_reason or not method_return_point:
            raise RuntimeError(
                "split proposal method binding requires method_binding_reason and method_return_point"
            )
        normalized["method_path"] = resolved_method_path
        normalized["method_binding_reason"] = method_binding_reason
        normalized["method_return_point"] = method_return_point
    elif method_binding_reason or method_return_point:
        raise RuntimeError("split proposal method binding fields require method_path")
    else:
        normalized["method_path"] = ""
        normalized["method_binding_reason"] = ""
        normalized["method_return_point"] = ""
    return normalized


def normalize_positive_integer_field(
    value: Any,
    *,
    field_name: str,
    error_prefix: str,
) -> int:
    if isinstance(value, bool):
        raise RuntimeError(f"{error_prefix} field must be a positive integer: {field_name}")
    if isinstance(value, int):
        number = value
    elif isinstance(value, str) and value.strip().isdigit():
        number = int(value.strip())
    else:
        raise RuntimeError(f"{error_prefix} field must be a positive integer: {field_name}")
    if number < 1:
        raise RuntimeError(f"{error_prefix} field must be a positive integer: {field_name}")
    return number


def resolve_catalog_method_path(
    method_path: str,
    catalog_by_path: dict[str, dict[str, str]],
) -> str:
    raw = Path(method_path)
    candidates = [raw.resolve() if raw.is_absolute() else (Path.cwd() / raw).resolve()]
    for candidate in candidates:
        key = str(candidate)
        if key in catalog_by_path:
            return key
    raise RuntimeError(f"split proposal method is not in catalog: {method_path}")


def run_candidate_verification(
    *,
    flow: FlowWriter,
    service: RuntimeService,
    parent_job_id: str,
    user_input: str,
    candidate_text: str,
    parent_candidate_appearance_id: str,
    step_prefix: str,
    turn: str | None = None,
) -> dict[str, Any]:
    base_data: dict[str, str] = {}
    if turn is not None:
        base_data["turn"] = turn

    verification_job = service.create_child_job(
        parent_job_id=parent_job_id,
        target=VERIFICATION_JOB_TARGET,
        actor_id="system",
        acceptance_criteria=VERIFICATION_JOB_ACCEPTANCE_CRITERIA,
    )
    verification_job_id = verification_job["job_id"]
    created_data = {
        **base_data,
        "job_id": parent_job_id,
        "parent_job_id": parent_job_id,
        "verification_child_job_id": verification_job_id,
        "verification_job_id": verification_job_id,
        "verification_target": VERIFICATION_JOB_TARGET,
        "appearance_id": parent_candidate_appearance_id,
    }
    child_job_data = {
        **base_data,
        "job_id": verification_job_id,
        "parent_job_id": parent_job_id,
        "verification_child_job_id": verification_job_id,
        "verification_job_id": verification_job_id,
        "verification_target": VERIFICATION_JOB_TARGET,
        "appearance_id": parent_candidate_appearance_id,
    }
    flow.write(
        FLOW_VERIFICATION_JOB_CREATED,
        "verification job created",
        **created_data,
    )
    write_job_tree_mirror(
        flow=flow,
        service=service,
        turn=turn,
        job_id=verification_job_id,
        action="verification_child_created",
        child_job_id=verification_job_id,
        appearance_id=parent_candidate_appearance_id,
    )
    write_process_step(
        flow=flow,
        step=f"{step_prefix}.create",
        phase="verification",
        action="创建候选校验子业",
        **created_data,
    )

    service.mark_ready(verification_job_id, actor_id="system")
    flow.write(FLOW_JOB_READY, "verification job marked ready", **child_job_data)
    write_job_tree_mirror(
        flow=flow,
        service=service,
        turn=turn,
        job_id=verification_job_id,
        action="verification_child_ready",
        child_job_id=verification_job_id,
    )
    write_process_step(
        flow=flow,
        step=f"{step_prefix}.ready",
        phase="verification",
        action="标记候选校验子业就绪",
        **child_job_data,
    )

    service.start_job(verification_job_id, actor_id="system")
    flow.write(FLOW_JOB_RUNNING, "verification job running", **child_job_data)
    write_job_tree_mirror(
        flow=flow,
        service=service,
        turn=turn,
        job_id=verification_job_id,
        action="verification_child_running",
        child_job_id=verification_job_id,
    )
    write_process_step(
        flow=flow,
        step=f"{step_prefix}.run",
        phase="verification",
        action="启动确定性候选校验工具",
        status="started",
        **child_job_data,
    )
    flow.write(
        FLOW_VERIFICATION_TOOL_STARTED,
        "verification tool started",
        **child_job_data,
    )

    report = verify_candidate_text(
        task_text=user_input,
        candidate_text=candidate_text,
        candidate_appearance_id=parent_candidate_appearance_id,
    )
    report_json = verification_report_to_json(report)
    verification_candidate = service.submit_candidate(
        verification_job_id,
        text=report_json,
        actor_id="system",
        metadata={
            "appearance_kind": "candidate_verification_report",
            "candidate_only": True,
            "evidence_hardness": "deterministic",
        },
    )["candidate"]
    result_data = {
        **child_job_data,
        "verification_status": str(report["overall_status"]),
        "verification_check_count": str(len(report["checks"])),
        "verification_candidate_appearance_id": verification_candidate["appearance_id"],
        "verification_report": report_json,
        "verification_gaps": json.dumps(report["gaps"], ensure_ascii=False, sort_keys=True),
        "evidence_hardness": "deterministic",
        "evidence_kind": "candidate_verification_report",
    }
    flow.write(
        FLOW_VERIFICATION_RESULT_RECORDED,
        "verification result recorded",
        **result_data,
    )
    write_job_tree_mirror(
        flow=flow,
        service=service,
        turn=turn,
        job_id=verification_job_id,
        action="verification_candidate_attached",
        appearance_id=verification_candidate["appearance_id"],
        child_job_id=verification_job_id,
    )
    write_process_step(
        flow=flow,
        step=f"{step_prefix}.result",
        phase="verification",
        action="记录候选校验报告为校验子业候选结果",
        status=str(report["overall_status"]),
        **result_data,
    )

    verification_evidence = service.submit_evidence(
        verification_job_id,
        text=report_json,
        actor_id="system",
        metadata={
            "evidence_kind": "candidate_verification_report",
            "evidence_hardness": "deterministic",
        },
    )["evidence"]
    child_evidence_data = {
        **child_job_data,
        "verification_status": str(report["overall_status"]),
        "verification_candidate_appearance_id": verification_candidate["appearance_id"],
        "verification_evidence_appearance_id": verification_evidence["appearance_id"],
        "evidence_hardness": "deterministic",
        "evidence_kind": "candidate_verification_report",
    }
    flow.write(
        FLOW_VERIFICATION_EVIDENCE_SUBMITTED,
        "verification evidence submitted",
        **child_evidence_data,
    )
    write_job_tree_mirror(
        flow=flow,
        service=service,
        turn=turn,
        job_id=verification_job_id,
        action="verification_evidence_attached",
        appearance_id=verification_evidence["appearance_id"],
        child_job_id=verification_job_id,
    )
    write_process_step(
        flow=flow,
        step=f"{step_prefix}.evidence",
        phase="verification",
        action="提交校验报告为校验子业证据",
        **child_evidence_data,
    )

    parent_evidence_text = build_parent_verification_evidence(
        report=report,
        verification_job_id=verification_job_id,
        verification_candidate_appearance_id=verification_candidate["appearance_id"],
        verification_evidence_appearance_id=verification_evidence["appearance_id"],
        parent_candidate_appearance_id=parent_candidate_appearance_id,
    )
    parent_evidence = service.submit_evidence(
        parent_job_id,
        text=parent_evidence_text,
        actor_id="system",
        metadata={
            "evidence_kind": "candidate_verification_summary",
            "evidence_hardness": "deterministic",
        },
    )["evidence"]
    parent_evidence_data = {
        **base_data,
        "job_id": parent_job_id,
        "parent_job_id": parent_job_id,
        "verification_job_id": verification_job_id,
        "verification_child_job_id": verification_job_id,
        "verification_status": str(report["overall_status"]),
        "verification_parent_evidence_appearance_id": parent_evidence["appearance_id"],
        "verification_parent_evidence": parent_evidence_text,
        "evidence_hardness": "deterministic",
        "evidence_kind": "candidate_verification_summary",
    }
    flow.write(
        FLOW_PARENT_VERIFICATION_EVIDENCE_SUBMITTED,
        "parent verification evidence submitted",
        **parent_evidence_data,
    )
    write_job_tree_mirror(
        flow=flow,
        service=service,
        turn=turn,
        job_id=parent_job_id,
        action="parent_verification_evidence_attached",
        appearance_id=parent_evidence["appearance_id"],
        child_job_id=verification_job_id,
    )
    write_process_step(
        flow=flow,
        step=f"{step_prefix}.parent_evidence",
        phase="verification",
        action="将候选校验摘要证据回流到父业",
        **parent_evidence_data,
    )
    return {
        "verification_job_id": verification_job_id,
        "verification_candidate_appearance_id": verification_candidate["appearance_id"],
        "verification_evidence_appearance_id": verification_evidence["appearance_id"],
        "parent_evidence_appearance_id": parent_evidence["appearance_id"],
        "report": report,
    }


def normalize_max_repair_attempts(value: int) -> int:
    if value < 0:
        raise ValueError("max repair attempts must be zero or greater")
    return value


def normalize_max_frontier_dispatches(value: int) -> int:
    if value < 0:
        raise ValueError("max frontier dispatches must be zero or greater")
    return value


def normalize_max_child_package_repair_attempts(value: int) -> int:
    if value < 0:
        raise ValueError("max child package repair attempts must be zero or greater")
    return value


def normalize_max_advancement_waves(value: int) -> int:
    if value < 0:
        raise ValueError("max advancement waves must be zero or greater")
    return value


def normalize_max_parent_integration_repair_attempts(value: int) -> int:
    if value < 0:
        raise ValueError("max parent integration repair attempts must be zero or greater")
    return value


def repairable_failed_checks(report: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        check
        for check in report.get("checks") or []
        if check.get("status") == "failed" and check.get("check_kind") in REPAIRABLE_CHECK_KINDS
    ]


def compact_verification_check(check: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in {
            "check_id": check.get("check_id"),
            "check_kind": check.get("check_kind"),
            "status": check.get("status"),
            "source_text": check.get("source_text"),
            "actual_cjk_characters": check.get("actual_cjk_characters"),
            "min_cjk_characters": check.get("min_cjk_characters"),
            "max_cjk_characters": check.get("max_cjk_characters"),
            "signals": check.get("signals"),
        }.items()
        if value is not None and value != ""
    }


def compact_verification_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "overall_status": report.get("overall_status"),
        "verification_kind": report.get("verification_kind"),
        "candidate_appearance_id": report.get("candidate_appearance_id"),
        "selected_region": (report.get("facts") or {}).get("selected_region"),
        "checks": [compact_verification_check(check) for check in report.get("checks") or []],
        "gaps": report.get("gaps") or [],
    }


def build_candidate_repair_messages(
    *,
    method: MethodContext,
    user_input: str,
    previous_candidate_text: str,
    verification_result: dict[str, Any],
    attempt: int,
    max_attempts: int,
    repair_source: str = "deterministic_verification",
    repair_instruction: str | None = None,
    routing_judgment: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    repair_payload = {
        "task": user_input,
        "attempt": attempt,
        "max_attempts": max_attempts,
        "repair_source": repair_source,
        "previous_candidate": previous_candidate_text,
        "verification_report": compact_verification_report(verification_result["report"]),
        "repairable_failed_checks": [
            compact_verification_check(check)
            for check in repairable_failed_checks(verification_result["report"])
        ],
        "acceptance_repair_instruction": repair_instruction or "",
        "acceptance_routing_judgment": routing_judgment or {},
        "requirements": [
            "保持用户原始任务意图，不自行改写目标。",
            "只针对校验报告中的具体失败项或验收路由打回指令修订候选结果。",
            "输出完整修订候选结果，不输出省略、占位或只说明修改思路。",
            "不要声明候选已被接收或最终完成。",
        ],
    }
    return [
        *build_method_system_messages(method),
        {
            "role": "system",
            "content": (
                "你是金箍运行时中的候选修复行者。"
                "你只能提交修订候选结果，不能接收、拒收或宣告父业完成。"
            ),
        },
        {
            "role": "user",
            "content": json.dumps(repair_payload, ensure_ascii=False, sort_keys=True, indent=2),
        },
    ]


def run_candidate_repair_loop(
    *,
    flow: FlowWriter,
    service: RuntimeService,
    client: ChatClient,
    method: MethodContext,
    parent_job_id: str,
    user_input: str,
    initial_candidate_text: str,
    initial_candidate_appearance_id: str,
    initial_verification_result: dict[str, Any],
    max_repair_attempts: int,
    step_prefix: str,
    turn: str | None = None,
) -> dict[str, Any]:
    max_attempts = normalize_max_repair_attempts(max_repair_attempts)
    latest_candidate_text = initial_candidate_text
    latest_candidate_appearance_id = initial_candidate_appearance_id
    latest_verification_result = initial_verification_result
    attempts: list[dict[str, Any]] = []
    feedback_job_id: str | None = None
    outcome = "not_needed"
    reason = "verification did not expose a repairable failed check"

    while True:
        report = latest_verification_result["report"]
        status = str(report.get("overall_status") or "")
        repairable_checks = repairable_failed_checks(report)

        if status == "passed":
            outcome = "verification_passed"
            reason = "latest candidate passed deterministic verification"
            break
        if status != "failed":
            outcome = "not_repairable"
            reason = "verification did not fail with a concrete repairable check"
            break
        if not repairable_checks:
            outcome = "not_repairable"
            reason = "failed verification contains no repairable check kind"
            break
        if len(attempts) >= max_attempts:
            outcome = "attempt_limit_exhausted"
            reason = "configured repair attempt limit reached"
            break

        attempt_number = len(attempts) + 1
        repair_result = run_single_repair_attempt(
            flow=flow,
            service=service,
            client=client,
            method=method,
            parent_job_id=parent_job_id,
            user_input=user_input,
            previous_candidate_text=latest_candidate_text,
            previous_candidate_appearance_id=latest_candidate_appearance_id,
            previous_verification_result=latest_verification_result,
            attempt=attempt_number,
            max_attempts=max_attempts,
            step_prefix=step_prefix,
            turn=turn,
        )
        attempts.append(repair_result)
        latest_candidate_text = repair_result["candidate_text"]
        latest_candidate_appearance_id = repair_result["candidate_appearance_id"]
        latest_verification_result = repair_result["verification_result"]

    if should_create_verification_feedback_job(
        latest_verification_result=latest_verification_result,
        attempts=attempts,
        outcome=outcome,
    ):
        feedback_job_id = create_verification_feedback_job(
            flow=flow,
            service=service,
            parent_job_id=parent_job_id,
            latest_verification_result=latest_verification_result,
            attempts=attempts,
            outcome=outcome,
            reason=reason,
            turn=turn,
            step_prefix=step_prefix,
        )

    summary_text = build_repair_loop_summary_evidence(
        latest_verification_result=latest_verification_result,
        latest_candidate_appearance_id=latest_candidate_appearance_id,
        attempts=attempts,
        outcome=outcome,
        reason=reason,
        feedback_job_id=feedback_job_id,
        max_attempts=max_attempts,
    )
    summary_evidence = service.submit_evidence(
        parent_job_id,
        text=summary_text,
        actor_id="system",
        metadata={
            "evidence_kind": "candidate_repair_loop_summary",
            "evidence_hardness": "deterministic",
        },
    )["evidence"]
    event_data = {
        **turn_field(turn),
        "job_id": parent_job_id,
        "repair_loop_outcome": outcome,
        "repair_reason": reason,
        "repair_attempt_count": str(len(attempts)),
        "repair_max_attempts": str(max_attempts),
        "repair_latest_status": str(latest_verification_result["report"].get("overall_status")),
        "repair_latest_candidate_appearance_id": latest_candidate_appearance_id,
        "repair_loop_summary": summary_text,
        "appearance_id": summary_evidence["appearance_id"],
        "evidence_kind": "candidate_repair_loop_summary",
        "evidence_hardness": "deterministic",
    }
    if feedback_job_id is not None:
        event_data["repair_feedback_job_id"] = feedback_job_id
    flow.write(FLOW_REPAIR_LOOP_FINISHED, "repair loop finished", **event_data)
    write_job_tree_mirror(
        flow=flow,
        service=service,
        turn=turn,
        job_id=parent_job_id,
        action="repair_verification_evidence_attached",
        appearance_id=summary_evidence["appearance_id"],
        child_job_id=feedback_job_id,
        reason=reason,
    )
    write_process_step(
        flow=flow,
        step=f"{step_prefix}.repair_loop.finish",
        phase="repair",
        action="记录候选修复循环摘要证据",
        **event_data,
    )

    return {
        "latest_candidate_text": latest_candidate_text,
        "latest_candidate_appearance_id": latest_candidate_appearance_id,
        "latest_verification_result": latest_verification_result,
        "attempts": attempts,
        "outcome": outcome,
        "reason": reason,
        "feedback_job_id": feedback_job_id,
        "summary_evidence_appearance_id": summary_evidence["appearance_id"],
    }


def run_single_repair_attempt(
    *,
    flow: FlowWriter,
    service: RuntimeService,
    client: ChatClient,
    method: MethodContext,
    parent_job_id: str,
    user_input: str,
    previous_candidate_text: str,
    previous_candidate_appearance_id: str,
    previous_verification_result: dict[str, Any],
    attempt: int,
    max_attempts: int,
    step_prefix: str,
    turn: str | None = None,
    repair_source: str = "deterministic_verification",
    repair_instruction: str | None = None,
    routing_judgment: dict[str, Any] | None = None,
) -> dict[str, Any]:
    repair_checks = repairable_failed_checks(previous_verification_result["report"])
    is_acceptance_repair = repair_source == "acceptance_routing"
    repair_job = service.create_child_job(
        parent_job_id=parent_job_id,
        target=ACCEPTANCE_REPAIR_JOB_TARGET if is_acceptance_repair else REPAIR_JOB_TARGET,
        actor_id="system",
        acceptance_criteria=(
            ACCEPTANCE_REPAIR_JOB_ACCEPTANCE_CRITERIA
            if is_acceptance_repair
            else REPAIR_JOB_ACCEPTANCE_CRITERIA
        ),
    )
    repair_job_id = repair_job["job_id"]
    base_data = {
        **turn_field(turn),
        "job_id": repair_job_id,
        "parent_job_id": parent_job_id,
        "repair_child_job_id": repair_job_id,
        "repair_attempt": str(attempt),
        "repair_max_attempts": str(max_attempts),
        "repair_source": repair_source,
        "repairable_check_count": str(len(repair_checks)),
        "repairable_checks": json.dumps(
            [compact_verification_check(check) for check in repair_checks],
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        ),
        "appearance_id": previous_candidate_appearance_id,
    }
    if repair_instruction:
        base_data["acceptance_repair_instruction"] = repair_instruction
    if routing_judgment:
        base_data["acceptance_routing_judgment"] = json.dumps(
            routing_judgment, ensure_ascii=False, sort_keys=True, indent=2
        )
    flow.write(FLOW_REPAIR_JOB_CREATED, "repair job created", **base_data)
    write_job_tree_mirror(
        flow=flow,
        service=service,
        turn=turn,
        job_id=repair_job_id,
        action="repair_child_created",
        child_job_id=repair_job_id,
        appearance_id=previous_candidate_appearance_id,
    )
    write_process_step(
        flow=flow,
        step=f"{step_prefix}.repair_{attempt}.create",
        phase="repair",
        action="创建候选修复子业",
        **base_data,
    )

    service.mark_ready(repair_job_id, actor_id="system")
    flow.write(FLOW_JOB_READY, "repair job marked ready", **base_data)
    write_job_tree_mirror(
        flow=flow,
        service=service,
        turn=turn,
        job_id=repair_job_id,
        action="repair_child_ready",
        child_job_id=repair_job_id,
    )
    write_process_step(
        flow=flow,
        step=f"{step_prefix}.repair_{attempt}.ready",
        phase="repair",
        action="标记候选修复子业就绪",
        **base_data,
    )

    service.start_job(repair_job_id, actor_id="system")
    flow.write(FLOW_JOB_RUNNING, "repair job running", **base_data)
    write_job_tree_mirror(
        flow=flow,
        service=service,
        turn=turn,
        job_id=repair_job_id,
        action="repair_child_running",
        child_job_id=repair_job_id,
    )
    write_process_step(
        flow=flow,
        step=f"{step_prefix}.repair_{attempt}.run",
        phase="repair",
        action="启动候选修复子业",
        status="started",
        **base_data,
    )

    repair_messages = build_candidate_repair_messages(
        method=method,
        user_input=user_input,
        previous_candidate_text=previous_candidate_text,
        verification_result=previous_verification_result,
        attempt=attempt,
        max_attempts=max_attempts,
        repair_source=repair_source,
        repair_instruction=repair_instruction,
        routing_judgment=routing_judgment,
    )
    flow.write(
        FLOW_REPAIR_REQUEST_PREPARED,
        "repair request prepared",
        **{
            **base_data,
            "repair_prompt": repair_messages[-1]["content"],
            "provider_message_count": str(len(repair_messages)),
        },
    )
    write_provider_messages(
        flow=flow,
        call_kind="acceptance_repair" if is_acceptance_repair else "candidate_repair",
        messages=repair_messages,
        turn=turn,
        job_id=repair_job_id,
    )
    write_process_step(
        flow=flow,
        step=f"{step_prefix}.repair_{attempt}.provider_request",
        phase="repair",
        action="向 AI 行者发送候选修复请求",
        status="started",
        **base_data,
    )
    repair_response = complete_with_provider_logging(
        flow=flow,
        client=client,
        messages=repair_messages,
        call_kind="acceptance_repair" if is_acceptance_repair else "candidate_repair",
        turn=turn,
        job_id=repair_job_id,
    )
    flow.write(
        FLOW_REPAIR_RESPONSE_RECEIVED,
        "repair response received",
        **{**base_data, "repair_response": repair_response.content},
    )
    write_process_step(
        flow=flow,
        step=f"{step_prefix}.repair_{attempt}.provider_response",
        phase="repair",
        action="收到候选修复响应",
        **base_data,
    )

    repair_candidate = service.submit_candidate(
        repair_job_id,
        text=repair_response.content,
        actor_id="ai",
        metadata={
            "appearance_kind": "candidate_repair_result",
            "candidate_only": True,
            "repair_source": repair_source,
        },
    )["candidate"]
    candidate_data = {
        **base_data,
        "repair_candidate_appearance_id": repair_candidate["appearance_id"],
        "appearance_id": repair_candidate["appearance_id"],
    }
    flow.write(FLOW_CANDIDATE_SUBMITTED, "repair candidate submitted", **candidate_data)
    flow.write(FLOW_REPAIR_CANDIDATE_SUBMITTED, "repair candidate submitted", **candidate_data)
    write_job_tree_mirror(
        flow=flow,
        service=service,
        turn=turn,
        job_id=repair_job_id,
        action="repair_candidate_attached",
        appearance_id=repair_candidate["appearance_id"],
        child_job_id=repair_job_id,
    )
    write_process_step(
        flow=flow,
        step=f"{step_prefix}.repair_{attempt}.candidate_submit",
        phase="repair",
        action="提交修复响应为修复子业候选结果",
        **candidate_data,
    )

    repair_verification = run_candidate_verification(
        flow=flow,
        service=service,
        parent_job_id=repair_job_id,
        user_input=user_input,
        candidate_text=repair_response.content,
        parent_candidate_appearance_id=repair_candidate["appearance_id"],
        step_prefix=f"{step_prefix}.repair_{attempt}.verify",
        turn=turn,
    )
    return {
        "attempt": attempt,
        "repair_job_id": repair_job_id,
        "candidate_text": repair_response.content,
        "candidate_appearance_id": repair_candidate["appearance_id"],
        "verification_result": repair_verification,
    }


def should_create_verification_feedback_job(
    *,
    latest_verification_result: dict[str, Any],
    attempts: list[dict[str, Any]],
    outcome: str,
) -> bool:
    status = str(latest_verification_result["report"].get("overall_status") or "")
    if status == "passed":
        return False
    if not attempts and status != "failed":
        return False
    return outcome in {"attempt_limit_exhausted", "not_repairable"}


def create_verification_feedback_job(
    *,
    flow: FlowWriter,
    service: RuntimeService,
    parent_job_id: str,
    latest_verification_result: dict[str, Any],
    attempts: list[dict[str, Any]],
    outcome: str,
    reason: str,
    step_prefix: str,
    turn: str | None = None,
) -> str:
    feedback_job = service.create_child_job(
        parent_job_id=parent_job_id,
        target=VERIFICATION_FEEDBACK_JOB_TARGET,
        actor_id="system",
        acceptance_criteria=VERIFICATION_FEEDBACK_JOB_ACCEPTANCE_CRITERIA,
        required_context_gaps=verification_feedback_gaps(
            latest_verification_result["report"], outcome=outcome, reason=reason
        ),
    )
    feedback_job_id = feedback_job["job_id"]
    data = {
        **turn_field(turn),
        "job_id": parent_job_id,
        "feedback_job_id": feedback_job_id,
        "repair_feedback_job_id": feedback_job_id,
        "feedback_job_kind": "verification_unresolved",
        "feedback_job_target": VERIFICATION_FEEDBACK_JOB_TARGET,
        "repair_loop_outcome": outcome,
        "repair_reason": reason,
        "repair_attempt_count": str(len(attempts)),
        "verification_status": str(latest_verification_result["report"].get("overall_status")),
    }
    flow.write(
        FLOW_VERIFICATION_FEEDBACK_JOB_CREATED,
        "verification feedback job created",
        **data,
    )
    write_job_tree_mirror(
        flow=flow,
        service=service,
        turn=turn,
        job_id=feedback_job_id,
        action="verification_feedback_child_created",
        child_job_id=feedback_job_id,
        feedback_job_kind="verification_unresolved",
        reason=reason,
    )
    feedback_evidence_text = build_verification_feedback_evidence(
        latest_verification_result=latest_verification_result,
        attempts=attempts,
        outcome=outcome,
        reason=reason,
    )
    evidence = service.submit_evidence(
        feedback_job_id,
        text=feedback_evidence_text,
        actor_id="system",
        metadata={
            "evidence_kind": "verification_feedback",
            "evidence_hardness": "deterministic",
        },
    )["evidence"]
    flow.write(
        FLOW_EVIDENCE_SUBMITTED,
        "verification feedback evidence submitted",
        **{
            **turn_field(turn),
            "job_id": feedback_job_id,
            "parent_job_id": parent_job_id,
            "appearance_id": evidence["appearance_id"],
            "repair_loop_outcome": outcome,
            "repair_reason": reason,
            "verification_feedback_evidence": feedback_evidence_text,
            "evidence_kind": "verification_feedback",
            "evidence_hardness": "deterministic",
        },
    )
    write_job_tree_mirror(
        flow=flow,
        service=service,
        turn=turn,
        job_id=feedback_job_id,
        action="evidence_attached",
        appearance_id=evidence["appearance_id"],
        child_job_id=feedback_job_id,
    )
    write_process_step(
        flow=flow,
        step=f"{step_prefix}.feedback_decision.create",
        phase="feedback",
        action="创建候选校验未解决反馈裁决业并提交证据",
        **data,
    )
    return feedback_job_id


def verification_feedback_gaps(report: dict[str, Any], *, outcome: str, reason: str) -> list[str]:
    gaps = [str(item) for item in report.get("gaps") or [] if str(item).strip()]
    failed_checks = [
        compact_verification_check(check)
        for check in report.get("checks") or []
        if check.get("status") == "failed"
    ]
    for check in failed_checks:
        gaps.append("未解决校验项：" + json.dumps(check, ensure_ascii=False, sort_keys=True))
    gaps.append("修复循环停止原因：" + outcome + " / " + reason)
    return gaps


def build_verification_feedback_evidence(
    *,
    latest_verification_result: dict[str, Any],
    attempts: list[dict[str, Any]],
    outcome: str,
    reason: str,
) -> str:
    payload = {
        "evidence_kind": "verification_feedback_decision_context",
        "repair_loop_outcome": outcome,
        "repair_reason": reason,
        "attempts": repair_attempt_summaries(attempts),
        "latest_verification": compact_verification_report(latest_verification_result["report"]),
        "does_not_auto_accept_or_reject": True,
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2)


def build_repair_loop_summary_evidence(
    *,
    latest_verification_result: dict[str, Any],
    latest_candidate_appearance_id: str,
    attempts: list[dict[str, Any]],
    outcome: str,
    reason: str,
    feedback_job_id: str | None,
    max_attempts: int,
) -> str:
    payload = {
        "evidence_kind": "candidate_repair_loop_summary",
        "repair_loop_outcome": outcome,
        "repair_reason": reason,
        "repair_attempt_count": len(attempts),
        "repair_max_attempts": max_attempts,
        "latest_candidate_appearance_id": latest_candidate_appearance_id,
        "latest_verification": compact_verification_report(latest_verification_result["report"]),
        "attempts": repair_attempt_summaries(attempts),
        "feedback_job_id": feedback_job_id,
        "does_not_auto_accept_or_reject": True,
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2)


def repair_attempt_summaries(attempts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "attempt": attempt["attempt"],
            "repair_job_id": attempt["repair_job_id"],
            "candidate_appearance_id": attempt["candidate_appearance_id"],
            "verification_job_id": attempt["verification_result"]["verification_job_id"],
            "verification_status": attempt["verification_result"]["report"].get("overall_status"),
        }
        for attempt in attempts
    ]


def compact_repair_loop_result(repair_result: dict[str, Any]) -> dict[str, Any]:
    return {
        "repair_loop_outcome": repair_result.get("outcome"),
        "repair_reason": repair_result.get("reason"),
        "repair_attempt_count": len(repair_result.get("attempts") or []),
        "feedback_job_id": repair_result.get("feedback_job_id"),
        "summary_evidence_appearance_id": repair_result.get("summary_evidence_appearance_id"),
        "latest_candidate_appearance_id": repair_result.get("latest_candidate_appearance_id"),
        "latest_verification": compact_verification_report(
            repair_result["latest_verification_result"]["report"]
        ),
        "attempts": repair_attempt_summaries(repair_result.get("attempts") or []),
    }


def build_acceptance_routing_messages(
    *,
    method: MethodContext,
    parent_job_id: str,
    user_input: str,
    latest_candidate_text: str,
    latest_candidate_appearance_id: str,
    latest_verification_result: dict[str, Any],
    repair_result: dict[str, Any],
    turn: str | None = None,
) -> list[dict[str, str]]:
    method_manifest = {
        "method_name": method.name,
        "method_checksum": method.checksum,
        "method_law_fragment_count": len(method.fragments),
        "bound_law_titles": [fragment.title for fragment in method.fragments],
    }
    routing_payload = {
        "task": user_input,
        "turn": turn or "",
        "parent_job_id": parent_job_id,
        "candidate": {
            "appearance_id": latest_candidate_appearance_id,
            "text": latest_candidate_text,
        },
        "deterministic_verification": compact_verification_report(
            latest_verification_result["report"]
        ),
        "method_context": method_manifest,
        "repair_loop": compact_repair_loop_result(repair_result),
        "routing_rules": [
            "continue 只用于没有语义修复、没有方向问题、没有高价值问题、没有人类授权缺口的候选。",
            "candidate 里只要保留了需要愿主、人类授权、责任归属或方向裁决的问题，就必须选择 feedback，把问题登记成反馈业。",
            "repair 用于候选问题可以由执行端直接改写且不需要愿主价值裁决的情况。",
        ],
        "routing_contract": {
            "route_action": sorted(ACCEPTANCE_ROUTE_ACTIONS),
            "feedback_job_kind": ["none", *sorted(ACCEPTANCE_FEEDBACK_JOB_KINDS)],
            "required_keys": [
                "route_action",
                "feedback_job_kind",
                "feedback_job_summary",
                "required_context_gaps",
                "repair_instruction",
                "reason",
                "evidence",
            ],
            "does_not_auto_accept_or_reject": True,
        },
    }
    return [
        {
            "role": "system",
            "content": (
                "你是金箍运行时中的验收路由位。"
                "你不能接收、拒收或宣告父业完成，只能选择下一步路由。"
                "若候选存在可由执行端直接修正的问题，选择 repair 并给出可执行修复指令。"
                "若候选暴露高价值、方向性、授权、价值冲突或关键缺口，选择 feedback 并显影成反馈业。"
                "只要候选中仍有需要愿主、人类授权或方向裁决的问题，就必须选择 feedback 登记为子业；"
                "不要因为候选已经文字描述了该问题就选择 continue。"
                "若无需打回或显影，选择 continue。"
                "evidence 必须是字符串数组，每个元素是一条可核查证据。"
                "只返回 JSON，不要输出解释性正文。"
            ),
        },
        {
            "role": "system",
            "content": (
                "当前调用只做验收路由，不重新执行完整方法。"
                "方法全文已经在父业候选生成阶段绑定；本轮只读取候选、校验、修复摘要和路由规则。"
            ),
        },
        {
            "role": "user",
            "content": json.dumps(routing_payload, ensure_ascii=False, sort_keys=True, indent=2),
        },
    ]


def run_acceptance_routing(
    *,
    flow: FlowWriter,
    service: RuntimeService,
    client: ChatClient,
    method: MethodContext,
    parent_job_id: str,
    user_input: str,
    repair_result: dict[str, Any],
    step_prefix: str,
    turn: str | None = None,
) -> dict[str, Any]:
    latest_candidate_text = str(repair_result["latest_candidate_text"])
    latest_candidate_appearance_id = str(repair_result["latest_candidate_appearance_id"])
    latest_verification_result = repair_result["latest_verification_result"]
    routing_messages = build_acceptance_routing_messages(
        method=method,
        parent_job_id=parent_job_id,
        user_input=user_input,
        latest_candidate_text=latest_candidate_text,
        latest_candidate_appearance_id=latest_candidate_appearance_id,
        latest_verification_result=latest_verification_result,
        repair_result=repair_result,
        turn=turn,
    )
    base_data = {
        **turn_field(turn),
        "job_id": parent_job_id,
        "acceptance_latest_candidate_appearance_id": latest_candidate_appearance_id,
        "verification_status": str(latest_verification_result["report"].get("overall_status")),
        "repair_loop_outcome": str(repair_result.get("outcome")),
        "acceptance_routing_prompt": routing_messages[-1]["content"],
        "provider_message_count": str(len(routing_messages)),
    }
    flow.write(
        FLOW_ACCEPTANCE_ROUTING_REQUESTED,
        "acceptance routing requested",
        **base_data,
    )
    write_provider_messages(
        flow=flow,
        call_kind="acceptance_routing",
        messages=routing_messages,
        turn=turn,
        job_id=parent_job_id,
    )
    write_process_step(
        flow=flow,
        step=f"{step_prefix}.acceptance_route.request",
        phase="acceptance",
        action="向验收路由位发送候选、校验和修复证据",
        status="started",
        **base_data,
    )

    routing_response = complete_with_provider_logging(
        flow=flow,
        client=client,
        messages=routing_messages,
        call_kind="acceptance_routing",
        turn=turn,
        job_id=parent_job_id,
    )
    judgment = parse_acceptance_routing_judgment(routing_response.content)
    judgment_text = json.dumps(judgment, ensure_ascii=False, sort_keys=True, indent=2)
    received_data = {
        **base_data,
        "acceptance_route_action": judgment["route_action"],
        "acceptance_route_kind": judgment["feedback_job_kind"],
        "acceptance_routing_judgment": judgment_text,
        "reason": judgment["reason"],
    }
    if judgment["repair_instruction"]:
        received_data["acceptance_repair_instruction"] = judgment["repair_instruction"]
    flow.write(
        FLOW_ACCEPTANCE_ROUTING_RECEIVED,
        "acceptance routing received",
        **received_data,
    )
    write_process_step(
        flow=flow,
        step=f"{step_prefix}.acceptance_route.receive",
        phase="acceptance",
        action="收到验收路由位判断",
        **received_data,
    )

    evidence_text = build_acceptance_routing_evidence(
        judgment=judgment,
        latest_candidate_appearance_id=latest_candidate_appearance_id,
        latest_verification_result=latest_verification_result,
        repair_result=repair_result,
    )
    evidence = service.submit_evidence(
        parent_job_id,
        text=evidence_text,
        actor_id="system",
        metadata={
            "evidence_kind": "acceptance_routing_judgment",
            "evidence_hardness": "weak_ai_review",
        },
    )["evidence"]
    evidence_data = {
        **turn_field(turn),
        "job_id": parent_job_id,
        "appearance_id": evidence["appearance_id"],
        "acceptance_routing_evidence_appearance_id": evidence["appearance_id"],
        "acceptance_route_action": judgment["route_action"],
        "acceptance_route_kind": judgment["feedback_job_kind"],
        "acceptance_routing_evidence": evidence_text,
        "evidence_kind": "acceptance_routing_judgment",
        "evidence_hardness": "weak_ai_review",
    }
    flow.write(
        FLOW_ACCEPTANCE_ROUTING_EVIDENCE_SUBMITTED,
        "acceptance routing evidence submitted",
        **evidence_data,
    )
    write_job_tree_mirror(
        flow=flow,
        service=service,
        turn=turn,
        job_id=parent_job_id,
        action="evidence_attached",
        appearance_id=evidence["appearance_id"],
        reason=judgment["reason"],
    )
    write_process_step(
        flow=flow,
        step=f"{step_prefix}.acceptance_route.evidence",
        phase="acceptance",
        action="提交验收路由判断为父业证据",
        **evidence_data,
    )

    if judgment["route_action"] == "continue":
        flow.write(
            FLOW_ACCEPTANCE_ROUTING_SKIPPED,
            "acceptance routing skipped child job creation",
            **{
                **turn_field(turn),
                "job_id": parent_job_id,
                "acceptance_route_action": judgment["route_action"],
                "acceptance_route_kind": judgment["feedback_job_kind"],
                "reason": judgment["reason"],
            },
        )
        write_job_tree_mirror(
            flow=flow,
            service=service,
            turn=turn,
            job_id=parent_job_id,
            action="acceptance_route_continued",
            reason=judgment["reason"],
        )
        write_process_step(
            flow=flow,
            step=f"{step_prefix}.acceptance_route.continue",
            phase="acceptance",
            action="验收路由未创建子业，继续返回候选结果",
            turn=turn,
            job_id=parent_job_id,
            reason=judgment["reason"],
        )
        return {
            "judgment": judgment,
            "latest_candidate_text": latest_candidate_text,
            "latest_candidate_appearance_id": latest_candidate_appearance_id,
            "latest_verification_result": latest_verification_result,
            "acceptance_repair_result": None,
            "feedback_job_id": None,
            "evidence_appearance_id": evidence["appearance_id"],
        }

    if judgment["route_action"] == "repair":
        repair_attempt = run_single_repair_attempt(
            flow=flow,
            service=service,
            client=client,
            method=method,
            parent_job_id=parent_job_id,
            user_input=user_input,
            previous_candidate_text=latest_candidate_text,
            previous_candidate_appearance_id=latest_candidate_appearance_id,
            previous_verification_result=latest_verification_result,
            attempt=1,
            max_attempts=1,
            step_prefix=f"{step_prefix}.acceptance_route",
            turn=turn,
            repair_source="acceptance_routing",
            repair_instruction=judgment["repair_instruction"],
            routing_judgment=judgment,
        )
        feedback_job_id = None
        repaired_status = str(repair_attempt["verification_result"]["report"].get("overall_status"))
        if repaired_status == "failed":
            feedback_job_id = create_verification_feedback_job(
                flow=flow,
                service=service,
                parent_job_id=repair_attempt["repair_job_id"],
                latest_verification_result=repair_attempt["verification_result"],
                attempts=[repair_attempt],
                outcome="acceptance_repair_unresolved",
                reason="acceptance routed repair still failed deterministic verification",
                step_prefix=f"{step_prefix}.acceptance_route.repair",
                turn=turn,
            )
        return {
            "judgment": judgment,
            "latest_candidate_text": repair_attempt["candidate_text"],
            "latest_candidate_appearance_id": repair_attempt["candidate_appearance_id"],
            "latest_verification_result": repair_attempt["verification_result"],
            "acceptance_repair_result": repair_attempt,
            "feedback_job_id": feedback_job_id,
            "evidence_appearance_id": evidence["appearance_id"],
        }

    feedback_job_id = create_acceptance_feedback_job(
        flow=flow,
        service=service,
        parent_job_id=parent_job_id,
        judgment=judgment,
        routing_evidence_text=evidence_text,
        step_prefix=step_prefix,
        turn=turn,
    )
    return {
        "judgment": judgment,
        "latest_candidate_text": latest_candidate_text,
        "latest_candidate_appearance_id": latest_candidate_appearance_id,
        "latest_verification_result": latest_verification_result,
        "acceptance_repair_result": None,
        "feedback_job_id": feedback_job_id,
        "evidence_appearance_id": evidence["appearance_id"],
    }


def parse_acceptance_routing_judgment(content: str) -> dict[str, Any]:
    payload = load_json_object(content, error_prefix="acceptance routing response")
    if not isinstance(payload, dict):
        raise RuntimeError("acceptance routing response must be a JSON object")

    route_action = str(payload.get("route_action") or "").strip()
    if route_action not in ACCEPTANCE_ROUTE_ACTIONS:
        raise RuntimeError("acceptance routing response must choose continue, repair, or feedback")

    feedback_job_kind = str(payload.get("feedback_job_kind") or "none").strip()
    feedback_job_summary = str(payload.get("feedback_job_summary") or "").strip()
    repair_instruction = str(payload.get("repair_instruction") or "").strip()
    reason = str(payload.get("reason") or "").strip()
    required_context_gaps = normalize_string_list(
        payload.get("required_context_gaps") or [],
        field_name="required_context_gaps",
        error_prefix="acceptance routing response",
    )
    evidence = normalize_string_list(
        payload.get("evidence") or [],
        field_name="evidence",
        error_prefix="acceptance routing response",
    )

    if route_action == "repair":
        if not repair_instruction:
            raise RuntimeError("acceptance routing repair must include repair_instruction")
        feedback_job_kind = "none"
        feedback_job_summary = ""
    elif route_action == "feedback":
        if feedback_job_kind not in ACCEPTANCE_FEEDBACK_JOB_KINDS:
            raise RuntimeError("acceptance routing feedback must choose high_value or directional")
        if not feedback_job_summary:
            raise RuntimeError("acceptance routing feedback must include feedback_job_summary")
        repair_instruction = ""
    else:
        feedback_job_kind = "none"
        feedback_job_summary = ""
        repair_instruction = ""

    return {
        "route_action": route_action,
        "feedback_job_kind": feedback_job_kind,
        "feedback_job_summary": feedback_job_summary,
        "required_context_gaps": required_context_gaps,
        "repair_instruction": repair_instruction,
        "reason": reason,
        "evidence": evidence,
        "does_not_auto_accept_or_reject": True,
    }


def normalize_string_list(value: Any, *, field_name: str, error_prefix: str) -> list[str]:
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if isinstance(value, dict):
        return [json.dumps(value, ensure_ascii=False, sort_keys=True)]
    if not isinstance(value, list):
        raise RuntimeError(f"{error_prefix} must include {field_name} as a list or text")
    normalized: list[str] = []
    for item in value:
        if isinstance(item, (dict, list)):
            text = json.dumps(item, ensure_ascii=False, sort_keys=True)
        else:
            text = str(item)
        text = text.strip()
        if text:
            normalized.append(text)
    return normalized


def build_acceptance_routing_evidence(
    *,
    judgment: dict[str, Any],
    latest_candidate_appearance_id: str,
    latest_verification_result: dict[str, Any],
    repair_result: dict[str, Any],
) -> str:
    payload = {
        "evidence_kind": "acceptance_routing_judgment",
        "route_action": judgment["route_action"],
        "feedback_job_kind": judgment["feedback_job_kind"],
        "feedback_job_summary": judgment["feedback_job_summary"],
        "required_context_gaps": judgment["required_context_gaps"],
        "repair_instruction": judgment["repair_instruction"],
        "reason": judgment["reason"],
        "router_evidence": judgment["evidence"],
        "latest_candidate_appearance_id": latest_candidate_appearance_id,
        "latest_verification": compact_verification_report(latest_verification_result["report"]),
        "repair_loop": compact_repair_loop_result(repair_result),
        "does_not_auto_accept_or_reject": True,
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2)


def create_acceptance_feedback_job(
    *,
    flow: FlowWriter,
    service: RuntimeService,
    parent_job_id: str,
    judgment: dict[str, Any],
    routing_evidence_text: str,
    step_prefix: str,
    turn: str | None = None,
) -> str:
    feedback_job = service.create_child_job(
        parent_job_id=parent_job_id,
        target=judgment["feedback_job_summary"],
        actor_id="system",
        acceptance_criteria=ACCEPTANCE_FEEDBACK_JOB_ACCEPTANCE_CRITERIA,
        required_context_gaps=judgment["required_context_gaps"],
    )
    feedback_job_id = feedback_job["job_id"]
    data = {
        **turn_field(turn),
        "job_id": parent_job_id,
        "feedback_job_id": feedback_job_id,
        "acceptance_feedback_job_id": feedback_job_id,
        "feedback_job_kind": judgment["feedback_job_kind"],
        "feedback_job_target": judgment["feedback_job_summary"],
        "feedback_job_summary": judgment["feedback_job_summary"],
        "required_context_gaps": json.dumps(
            judgment["required_context_gaps"], ensure_ascii=False, sort_keys=True
        ),
        "acceptance_route_action": judgment["route_action"],
        "acceptance_route_kind": judgment["feedback_job_kind"],
        "reason": judgment["reason"],
    }
    flow.write(FLOW_FEEDBACK_JOB_CREATED, "feedback job created", **data)
    write_job_tree_mirror(
        flow=flow,
        service=service,
        turn=turn,
        job_id=feedback_job_id,
        action="feedback_child_created",
        child_job_id=feedback_job_id,
        feedback_job_kind=judgment["feedback_job_kind"],
        reason=judgment["reason"],
    )
    if judgment["feedback_job_kind"] in ACCEPTANCE_FEEDBACK_JOB_KINDS:
        decision_data = {
            **data,
            "job_id": feedback_job_id,
            "parent_job_id": parent_job_id,
            "human_decision_request_kind": judgment["feedback_job_kind"],
        }
        flow.write(FLOW_HUMAN_DECISION_REQUESTED, "human decision requested", **decision_data)
        write_job_tree_mirror(
            flow=flow,
            service=service,
            turn=turn,
            job_id=feedback_job_id,
            action="human_decision_child_created",
            child_job_id=feedback_job_id,
            feedback_job_kind=judgment["feedback_job_kind"],
            reason=judgment["reason"],
        )
    evidence = service.submit_evidence(
        feedback_job_id,
        text=routing_evidence_text,
        actor_id="system",
        metadata={
            "evidence_kind": "acceptance_feedback_seed",
            "evidence_hardness": "weak_ai_review",
        },
    )["evidence"]
    flow.write(
        FLOW_EVIDENCE_SUBMITTED,
        "feedback job evidence submitted",
        **{
            **turn_field(turn),
            "job_id": feedback_job_id,
            "parent_job_id": parent_job_id,
            "appearance_id": evidence["appearance_id"],
            "acceptance_route_action": judgment["route_action"],
            "acceptance_route_kind": judgment["feedback_job_kind"],
            "acceptance_routing_evidence": routing_evidence_text,
            "evidence_kind": "acceptance_feedback_seed",
            "evidence_hardness": "weak_ai_review",
        },
    )
    write_job_tree_mirror(
        flow=flow,
        service=service,
        turn=turn,
        job_id=feedback_job_id,
        action="evidence_attached",
        appearance_id=evidence["appearance_id"],
        child_job_id=feedback_job_id,
        feedback_job_kind=judgment["feedback_job_kind"],
    )
    write_process_step(
        flow=flow,
        step=f"{step_prefix}.acceptance_route.feedback_job.create",
        phase="feedback",
        action="创建验收路由显影反馈业并提交路由证据",
        **data,
    )
    return feedback_job_id


def load_json_object(content: str, *, error_prefix: str) -> Any:
    stripped = content.strip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError as first_error:
        if stripped.startswith("```"):
            lines = stripped.splitlines()
            if len(lines) >= 3 and lines[-1].strip() == "```":
                fenced = "\n".join(lines[1:-1]).strip()
                try:
                    return json.loads(fenced)
                except json.JSONDecodeError:
                    pass

        start = stripped.find("{")
        end = stripped.rfind("}")
        if 0 <= start < end:
            try:
                return json.loads(stripped[start : end + 1])
            except json.JSONDecodeError:
                pass

        raise RuntimeError(f"{error_prefix} must be valid JSON") from first_error


def turn_field(turn: str | None) -> dict[str, str]:
    return {"turn": turn} if turn is not None else {}


def complete_with_provider_logging(
    *,
    flow: FlowWriter,
    client: ChatClient,
    messages: list[dict[str, str]],
    call_kind: str,
    turn: str | None = None,
    job_id: str | None = None,
):
    def on_stream_event(event: dict[str, str]) -> None:
        data = {
            "provider_call_kind": call_kind,
            **{key: str(value) for key, value in event.items() if key != "event"},
        }
        if turn is not None:
            data["turn"] = turn
        if job_id is not None:
            data["job_id"] = job_id
        event_kind = event.get("event")
        if event_kind == "stream_finished":
            flow.write(FLOW_PROVIDER_STREAM_FINISHED, "provider stream finished", **data)
            return
        flow.write(
            FLOW_PROVIDER_STREAM_DELTA_RECEIVED,
            "provider stream delta received",
            **data,
        )

    return client.complete_messages(messages, on_stream_event=on_stream_event)


def write_job_tree_mirror(
    *,
    flow: FlowWriter,
    service: RuntimeService,
    job_id: str,
    action: str,
    turn: str | None = None,
    appearance_id: str | None = None,
    child_job_id: str | None = None,
    feedback_job_kind: str | None = None,
    reason: str | None = None,
) -> None:
    job = service.get_status(job_id)
    root_job_id = str(job["root_job_id"])
    event_data = {
        "job_tree_action": action,
        "job_id": str(job["job_id"]),
        "root_job_id": root_job_id,
        "job_state": str(job["state"]),
        "job_target": str(job["target"]),
    }
    optional_fields = {
        "turn": turn,
        "parent_job_id": job.get("parent_job_id"),
        "appearance_id": appearance_id,
        "child_job_id": child_job_id,
        "feedback_job_kind": feedback_job_kind,
        "reason": reason,
    }
    event_data.update({key: str(value) for key, value in optional_fields.items() if value})
    flow.write(
        FLOW_JOB_TREE_MANAGEMENT_RECORDED,
        "job tree management recorded",
        **event_data,
    )
    flow.write(
        FLOW_JOB_TREE_SNAPSHOT_RECORDED,
        "job tree snapshot recorded",
        **{
            key: value
            for key, value in {
                "turn": turn,
                "job_id": str(job["job_id"]),
                "root_job_id": root_job_id,
                "tree_snapshot": json.dumps(
                    job_tree_snapshot(service, root_job_id),
                    ensure_ascii=False,
                    sort_keys=True,
                    indent=2,
                ),
            }.items()
            if value
        },
    )


def job_tree_snapshot(service: RuntimeService, root_job_id: str) -> dict[str, Any]:
    with service.repository.transaction() as connection:
        rows = service.repository.list_jobs_by_root(connection, root_job_id)
        nodes = [
            job_tree_node(
                row,
                method_call_frames=[
                    event["payload"]
                    for event in service.repository.list_events(connection, str(row["job_id"]))
                    if event["event_type"] == EVENT_METHOD_CALL_FRAME_OPENED
                ],
            )
            for row in rows
        ]

    active_job_ids = {
        str(node["job_id"])
        for node in nodes
        if str(node["state"]) not in TERMINAL_JOB_STATES
    }
    active_parent_ids = {
        str(node["parent_job_id"])
        for node in nodes
        if node.get("parent_job_id") and str(node["job_id"]) in active_job_ids
    }
    return {
        "root_job_id": root_job_id,
        "nodes": nodes,
        "links": [
            {"parent_job_id": node["parent_job_id"], "child_job_id": node["job_id"]}
            for node in nodes
            if node.get("parent_job_id")
        ],
        "frontier_job_ids": [
            node["job_id"]
            for node in nodes
            if node["job_id"] in active_job_ids and node["job_id"] not in active_parent_ids
        ],
    }


def job_tree_node(
    job: dict[str, Any],
    *,
    method_call_frames: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "job_id": job["job_id"],
        "parent_job_id": job.get("parent_job_id"),
        "root_job_id": job["root_job_id"],
        "state": job["state"],
        "target": job["target"],
        "candidate_appearance_id": job.get("candidate_appearance_id"),
        "evidence_appearance_id": job.get("evidence_appearance_id"),
        "result_appearance_id": job.get("result_appearance_id"),
        "required_context_gaps": decode_json(job.get("required_context_gaps"), []),
        "method_call_frames": method_call_frames or [],
    }


class AiSandboxRunner:
    def __init__(
        self,
        *,
        sandbox_path: Path | str | None = None,
        log_dir: Path | str | None = None,
        config_path: Path | str | None = None,
        method_path: Path | str | None = None,
        client: ChatClient | None = None,
        max_repair_attempts: int = DEFAULT_MAX_REPAIR_ATTEMPTS,
        max_frontier_dispatches: int = DEFAULT_MAX_FRONTIER_DISPATCHES,
        max_child_package_repair_attempts: int = DEFAULT_MAX_CHILD_PACKAGE_REPAIR_ATTEMPTS,
        max_advancement_waves: int = DEFAULT_MAX_ADVANCEMENT_WAVES,
        max_parent_integration_repair_attempts: int = DEFAULT_MAX_PARENT_INTEGRATION_REPAIR_ATTEMPTS,
        register_method_step_candidates: bool = DEFAULT_REGISTER_METHOD_STEP_CANDIDATES,
    ) -> None:
        self.sandbox_path = resolve_sandbox_path(sandbox_path)
        self.log_dir = resolve_log_dir(log_dir)
        self.diagnostic_log_path = new_diagnostic_log_path(self.log_dir)
        self.readable_log_path = readable_log_path_for(self.diagnostic_log_path)
        self.config_path = Path(config_path) if config_path is not None else None
        self.method_path = Path(method_path) if method_path is not None else None
        self.client = client
        self.runtime_options = SandboxRuntimeOptions.from_values(
            max_repair_attempts=max_repair_attempts,
            max_frontier_dispatches=max_frontier_dispatches,
            max_child_package_repair_attempts=max_child_package_repair_attempts,
            max_advancement_waves=max_advancement_waves,
            max_parent_integration_repair_attempts=max_parent_integration_repair_attempts,
            register_method_step_candidates=register_method_step_candidates,
        )
        self.max_repair_attempts = self.runtime_options.max_repair_attempts
        self.max_frontier_dispatches = self.runtime_options.max_frontier_dispatches
        self.max_child_package_repair_attempts = self.runtime_options.max_child_package_repair_attempts
        self.max_advancement_waves = self.runtime_options.max_advancement_waves
        self.max_parent_integration_repair_attempts = (
            self.runtime_options.max_parent_integration_repair_attempts
        )
        self.register_method_step_candidates = self.runtime_options.register_method_step_candidates
        self.flow = FlowWriter(
            self.sandbox_path,
            self.diagnostic_log_path,
            self.readable_log_path,
        )

    def run(self, message: str) -> str:
        self._reset_sandbox()
        try:
            self.sandbox_path.mkdir(parents=True, exist_ok=True)
            self._write_latest_log_pointer()
            self.flow.write(
                FLOW_SANDBOX_CREATED,
                "sandbox created",
                sandbox_path=str(self.sandbox_path),
                log_path=str(self.diagnostic_log_path),
                readable_log_path=str(self.readable_log_path),
            )
            write_process_step(
                flow=self.flow,
                step="sandbox.create",
                phase="sandbox",
                action="created ephemeral sandbox and log files",
                sandbox_path=str(self.sandbox_path),
                log_path=str(self.diagnostic_log_path),
                readable_log_path=str(self.readable_log_path),
            )
            self.flow.write(FLOW_USER_INPUT_RECORDED, "user input recorded", input=message)
            self.flow.write(
                FLOW_INPUT_PROVENANCE_RECORDED,
                "input provenance recorded",
                **input_provenance_fields(message, input_source="ai_run_message"),
            )
            write_process_step(
                flow=self.flow,
                step="input.record",
                phase="input",
                action="recorded user input and provenance",
            )

            service = RuntimeService(self.sandbox_path)
            service.initialize()
            self.flow.write(FLOW_RUNTIME_INITIALIZED, "runtime initialized")
            write_process_step(
                flow=self.flow,
                step="runtime.initialize",
                phase="runtime",
                action="initialized runtime repository inside sandbox",
            )
            write_runtime_options_event(
                flow=self.flow,
                options=self.runtime_options,
                step="runtime.options",
            )
            method = self._load_method_for_turn()

            root = service.create_root_job(wish=message, target=message, actor_id="human")
            job_id = root["job_id"]
            self.flow.write(FLOW_ROOT_JOB_CREATED, "root job created", job_id=job_id)
            write_job_tree_mirror(
                flow=self.flow,
                service=service,
                job_id=job_id,
                action="root_created",
            )
            write_process_step(
                flow=self.flow,
                step="job.root_create",
                phase="job",
                action="created root job from user input",
                job_id=job_id,
            )
            bind_method_law_fragments_to_job(
                flow=self.flow,
                service=service,
                method=method,
                job_id=job_id,
                step="method.law.bind",
                binding_reason="当前根业通过显式 method 参数绑定此法。",
                invocation_input={"job_id": job_id, "user_input": message},
                output_contract="候选结果、方法自验、校验证据和验收路由证据。",
                acceptance_criteria="候选结果必须保留原始愿望，并提交可追踪证据，不得自行接收或宣告完成。",
                return_point="当前根业候选提交、校验和验收路由。",
                budget={"max_repair_attempts": self.max_repair_attempts},
                depth=0,
            )
            register_method_step_candidates(
                flow=self.flow,
                service=service,
                method=method,
                parent_job_id=job_id,
                step_prefix="method.step_candidates",
                enabled=self.register_method_step_candidates,
            )

            service.mark_ready(job_id, actor_id="system")
            self.flow.write(FLOW_JOB_READY, "job marked ready", job_id=job_id)
            write_job_tree_mirror(
                flow=self.flow,
                service=service,
                job_id=job_id,
                action="job_ready",
            )
            write_process_step(
                flow=self.flow,
                step="job.ready",
                phase="job",
                action="marked root job ready",
                job_id=job_id,
            )

            service.start_job(job_id, actor_id="system")
            self.flow.write(FLOW_JOB_RUNNING, "job running", job_id=job_id)
            write_job_tree_mirror(
                flow=self.flow,
                service=service,
                job_id=job_id,
                action="job_running",
            )
            write_process_step(
                flow=self.flow,
                step="job.run",
                phase="job",
                action="started root job execution",
                job_id=job_id,
            )

            client = self.client or ChatClient(load_ai_config(self.config_path))
            method_messages = build_method_system_messages(method)
            messages = [*method_messages, {"role": "user", "content": message}]
            self.flow.write(
                FLOW_METHOD_CONTEXT_INJECTED,
                "method context injected",
                job_id=job_id,
                method_name=method.name,
                method_path=str(method.path),
                method_checksum=method.checksum,
                method_law_fragment_count=str(len(method.fragments)),
                message_count=str(len(messages)),
            )
            write_process_step(
                flow=self.flow,
                step="method.inject",
                phase="method",
                action="assembled provider messages with method context",
                job_id=job_id,
                message_count=str(len(messages)),
                method_law_fragment_count=str(len(method.fragments)),
            )
            self.flow.write(FLOW_AI_REQUEST_STARTED, "AI request started", job_id=job_id)
            write_provider_messages(
                flow=self.flow,
                call_kind="candidate_generation",
                messages=messages,
                job_id=job_id,
            )
            write_process_step(
                flow=self.flow,
                step="provider.request",
                phase="provider",
                action="sent messages to AI provider",
                status="started",
                job_id=job_id,
                message_count=str(len(messages)),
            )
            response = complete_with_provider_logging(
                flow=self.flow,
                client=client,
                messages=messages,
                call_kind="candidate_generation",
                job_id=job_id,
            )
            self.flow.write(
                FLOW_AI_RESPONSE_RECEIVED,
                "AI response received",
                job_id=job_id,
                response=response.content,
            )
            write_process_step(
                flow=self.flow,
                step="provider.response",
                phase="provider",
                action="received AI provider response",
                job_id=job_id,
            )

            candidate = service.submit_candidate(
                job_id,
                text=response.content,
                actor_id="ai",
                metadata={
                    "appearance_kind": "root_candidate",
                    "candidate_only": True,
                },
            )["candidate"]
            self.flow.write(
                FLOW_CANDIDATE_SUBMITTED,
                "candidate submitted",
                job_id=job_id,
                appearance_id=candidate["appearance_id"],
            )
            write_job_tree_mirror(
                flow=self.flow,
                service=service,
                job_id=job_id,
                action="candidate_attached",
                appearance_id=candidate["appearance_id"],
            )
            write_process_step(
                flow=self.flow,
                step="candidate.submit",
                phase="candidate",
                action="stored AI response as candidate result",
                job_id=job_id,
                appearance_id=candidate["appearance_id"],
            )

            review = self._request_method_self_review(
                client=client,
                method=method,
                job_id=job_id,
                user_input=message,
                assistant_response=response.content,
            )
            record_method_learning_candidate(
                flow=self.flow,
                service=service,
                method=method,
                job_id=job_id,
                review=review,
                step_prefix="method.self_review",
            )
            evidence = service.submit_evidence(
                job_id,
                text=method_evidence_payload(method=method, review=review),
                actor_id="system",
                metadata={
                    "evidence_kind": "method_self_review",
                    "evidence_hardness": "weak_ai",
                },
            )["evidence"]
            self.flow.write(
                FLOW_EVIDENCE_SUBMITTED,
                "evidence submitted",
                job_id=job_id,
                appearance_id=evidence["appearance_id"],
                evidence_kind="method_self_review",
                evidence_hardness="weak_ai",
            )
            write_job_tree_mirror(
                flow=self.flow,
                service=service,
                job_id=job_id,
                action="evidence_attached",
                appearance_id=evidence["appearance_id"],
            )
            write_process_step(
                flow=self.flow,
                step="evidence.submit",
                phase="evidence",
                action="stored method self-review as evidence",
                job_id=job_id,
                appearance_id=evidence["appearance_id"],
            )
            run_split_proposal_registration(
                flow=self.flow,
                service=service,
                client=client,
                method=method,
                parent_job_id=job_id,
                user_input=message,
                candidate_text=response.content,
                candidate_appearance_id=candidate["appearance_id"],
                step_prefix="split_proposal",
            )
            frontier_result = run_advancement_loop(
                flow=self.flow,
                service=service,
                client=client,
                root_job_id=job_id,
                user_input=message,
                root_method=method,
                root_candidate_text=response.content,
                root_candidate_appearance_id=candidate["appearance_id"],
                step_prefix="advancement",
                max_advancement_waves=self.max_advancement_waves,
                max_child_dispatches=self.max_frontier_dispatches,
                max_child_package_repair_attempts=self.max_child_package_repair_attempts,
                max_parent_integration_repair_attempts=self.max_parent_integration_repair_attempts,
            )
            verification_candidate_text = str(
                frontier_result.get("latest_parent_candidate_text") or response.content
            )
            verification_candidate_appearance_id = str(
                frontier_result.get("latest_parent_candidate_appearance_id")
                or candidate["appearance_id"]
            )
            verification_result = run_candidate_verification(
                flow=self.flow,
                service=service,
                parent_job_id=job_id,
                user_input=message,
                candidate_text=verification_candidate_text,
                parent_candidate_appearance_id=verification_candidate_appearance_id,
                step_prefix="candidate.verify",
            )
            repair_result = run_candidate_repair_loop(
                flow=self.flow,
                service=service,
                client=client,
                method=method,
                parent_job_id=job_id,
                user_input=message,
                initial_candidate_text=verification_candidate_text,
                initial_candidate_appearance_id=verification_candidate_appearance_id,
                initial_verification_result=verification_result,
                max_repair_attempts=self.max_repair_attempts,
                step_prefix="candidate.verify",
            )
            routing_result = run_acceptance_routing(
                flow=self.flow,
                service=service,
                client=client,
                method=method,
                parent_job_id=job_id,
                user_input=message,
                repair_result=repair_result,
                step_prefix="candidate.verify",
            )
            output_text = str(routing_result["latest_candidate_text"])

            self.flow.write(FLOW_RESULT_OUTPUT_RECORDED, "result output recorded", result=output_text)
            write_process_step(
                flow=self.flow,
                step="output.record",
                phase="output",
                action="recorded result output for CLI return",
                job_id=job_id,
            )
            self.flow.write(FLOW_RUN_FINISHED, "run finished", job_id=job_id)
            return output_text
        except Exception as exc:
            write_process_step(
                flow=self.flow,
                step="run.fail",
                phase="error",
                action="run failed before normal completion",
                status="failed",
                process_detail=str(exc),
            )
            self.flow.write(FLOW_RUN_FAILED, "run failed", error=str(exc))
            raise
        finally:
            write_process_step(
                flow=self.flow,
                step="sandbox.destroy",
                phase="cleanup",
                action="destroyed ephemeral sandbox",
                sandbox_path=str(self.sandbox_path),
                log_path=str(self.diagnostic_log_path),
                readable_log_path=str(self.readable_log_path),
            )
            self.flow.write(
                FLOW_SANDBOX_DESTROYED,
                "sandbox destroyed",
                sandbox_path=str(self.sandbox_path),
                log_path=str(self.diagnostic_log_path),
                readable_log_path=str(self.readable_log_path),
            )
            shutil.rmtree(self.sandbox_path, ignore_errors=True)

    def _reset_sandbox(self) -> None:
        if self.sandbox_path.exists():
            shutil.rmtree(self.sandbox_path)

    def _load_method_for_turn(self, *, turn: str | None = None) -> MethodContext:
        method = load_method_context(method_path=self.method_path)
        data = {"method_path": str(method.path), "method_checksum": method.checksum}
        if turn is not None:
            data["turn"] = turn
        self.flow.write(FLOW_METHOD_SOURCE_RESOLVED, "method source resolved", **data)
        self.flow.write(FLOW_METHOD_CONTEXT_LOADED, "method context loaded", **method.log_fields())
        write_method_law_fragment_events(flow=self.flow, method=method, turn=turn)
        write_process_step(
            flow=self.flow,
            step="method.load",
            phase="method",
            action="loaded method source",
            status="completed",
            turn=turn,
            method_path=str(method.path),
            method_checksum=method.checksum,
        )
        return method

    def _request_method_self_review(
        self,
        *,
        client: ChatClient,
        method: MethodContext,
        job_id: str,
        user_input: str,
        assistant_response: str,
        turn: str | None = None,
    ) -> str:
        data = {
            "job_id": job_id,
            "method_name": method.name,
            "method_checksum": method.checksum,
        }
        if turn is not None:
            data["turn"] = turn
        self.flow.write(FLOW_METHOD_SELF_REVIEW_REQUESTED, "method self-review requested", **data)
        write_process_step(
            flow=self.flow,
            step="method.self_review.request",
            phase="method",
            action="requested method self-review for candidate",
            status="started",
            **data,
        )
        review_messages = build_method_review_messages(
            method=method,
            user_input=user_input,
            assistant_response=assistant_response,
        )
        write_provider_messages(
            flow=self.flow,
            call_kind="method_self_review",
            messages=review_messages,
            turn=turn,
            job_id=job_id,
        )
        review = complete_with_provider_logging(
            flow=self.flow,
            client=client,
            messages=review_messages,
            call_kind="method_self_review",
            turn=turn,
            job_id=job_id,
        )
        received = {**data, "review": review.content}
        self.flow.write(FLOW_METHOD_SELF_REVIEW_RECEIVED, "method self-review received", **received)
        self.flow.write(
            FLOW_METHOD_UPDATE_CANDIDATE_RECORDED,
            "method update candidate recorded",
            **received,
        )
        write_process_step(
            flow=self.flow,
            step="method.self_review.receive",
            phase="method",
            action="recorded method self-review and update candidates",
            **data,
        )
        return review.content

    def _write_latest_log_pointer(self) -> None:
        self.log_dir.mkdir(parents=True, exist_ok=True)
        latest_log_pointer_path(self.log_dir).write_text(
            str(self.diagnostic_log_path), encoding="utf-8"
        )
        latest_readable_log_pointer_path(self.log_dir).write_text(
            str(self.readable_log_path), encoding="utf-8"
        )


class AiSandboxChatSession:
    def __init__(
        self,
        *,
        sandbox_path: Path | str | None = None,
        log_dir: Path | str | None = None,
        config_path: Path | str | None = None,
        method_path: Path | str | None = None,
        client: ChatClient | None = None,
        max_repair_attempts: int = DEFAULT_MAX_REPAIR_ATTEMPTS,
        max_frontier_dispatches: int = DEFAULT_MAX_FRONTIER_DISPATCHES,
        max_child_package_repair_attempts: int = DEFAULT_MAX_CHILD_PACKAGE_REPAIR_ATTEMPTS,
        max_advancement_waves: int = DEFAULT_MAX_ADVANCEMENT_WAVES,
        max_parent_integration_repair_attempts: int = DEFAULT_MAX_PARENT_INTEGRATION_REPAIR_ATTEMPTS,
        register_method_step_candidates: bool = DEFAULT_REGISTER_METHOD_STEP_CANDIDATES,
    ) -> None:
        self.sandbox_path = resolve_sandbox_path(sandbox_path)
        self.log_dir = resolve_log_dir(log_dir)
        self.diagnostic_log_path = new_diagnostic_log_path(self.log_dir)
        self.readable_log_path = readable_log_path_for(self.diagnostic_log_path)
        self.config_path = Path(config_path) if config_path is not None else None
        self.method_path = Path(method_path) if method_path is not None else None
        self.client = client
        self.runtime_options = SandboxRuntimeOptions.from_values(
            max_repair_attempts=max_repair_attempts,
            max_frontier_dispatches=max_frontier_dispatches,
            max_child_package_repair_attempts=max_child_package_repair_attempts,
            max_advancement_waves=max_advancement_waves,
            max_parent_integration_repair_attempts=max_parent_integration_repair_attempts,
            register_method_step_candidates=register_method_step_candidates,
        )
        self.max_repair_attempts = self.runtime_options.max_repair_attempts
        self.max_frontier_dispatches = self.runtime_options.max_frontier_dispatches
        self.max_child_package_repair_attempts = self.runtime_options.max_child_package_repair_attempts
        self.max_advancement_waves = self.runtime_options.max_advancement_waves
        self.max_parent_integration_repair_attempts = (
            self.runtime_options.max_parent_integration_repair_attempts
        )
        self.register_method_step_candidates = self.runtime_options.register_method_step_candidates
        self.flow = FlowWriter(
            self.sandbox_path,
            self.diagnostic_log_path,
            self.readable_log_path,
        )
        self.history: list[dict[str, str]] = []
        self.service: RuntimeService | None = None
        self.turn_count = 0
        self.last_job_id: str | None = None
        self.last_feedback_job_id: str | None = None
        self.last_feedback_judgment: dict[str, Any] | None = None

    def start(self) -> None:
        self._reset_sandbox()
        self.history = []
        self.service = None
        self.turn_count = 0
        self.last_job_id = None
        self.last_feedback_job_id = None
        self.last_feedback_judgment = None
        self.sandbox_path.mkdir(parents=True, exist_ok=True)
        self._write_latest_log_pointer()
        self.flow.write(
            FLOW_SANDBOX_CREATED,
            "sandbox created",
            sandbox_path=str(self.sandbox_path),
            log_path=str(self.diagnostic_log_path),
            readable_log_path=str(self.readable_log_path),
        )
        write_process_step(
            flow=self.flow,
            step="chat.sandbox.create",
            phase="sandbox",
            action="created interactive chat sandbox and log files",
            sandbox_path=str(self.sandbox_path),
            log_path=str(self.diagnostic_log_path),
            readable_log_path=str(self.readable_log_path),
        )
        self.service = RuntimeService(self.sandbox_path)
        self.service.initialize()
        self.flow.write(FLOW_RUNTIME_INITIALIZED, "runtime initialized")
        write_runtime_options_event(
            flow=self.flow,
            options=self.runtime_options,
            step="chat.runtime.options",
        )
        self.flow.write(FLOW_CHAT_SESSION_STARTED, "chat session started")
        write_process_step(
            flow=self.flow,
            step="chat.session.start",
            phase="runtime",
            action="initialized interactive chat session",
        )

    def ask(self, user_input: str) -> str:
        if self.service is None:
            raise RuntimeError("chat session has not started")

        self.turn_count += 1
        turn = str(self.turn_count)
        self.last_feedback_job_id = None
        self.last_feedback_judgment = None
        self.flow.write(FLOW_USER_INPUT_RECORDED, "user input recorded", turn=turn, input=user_input)
        self.flow.write(
            FLOW_INPUT_PROVENANCE_RECORDED,
            "input provenance recorded",
            turn=turn,
            **input_provenance_fields(user_input, input_source="ai_chat_message"),
        )
        write_process_step(
            flow=self.flow,
            step="chat.input.record",
            phase="input",
            action="recorded chat turn input and provenance",
            turn=turn,
        )
        method = self._load_method_for_turn(turn=turn)

        root = self.service.create_root_job(wish=user_input, target=user_input, actor_id="human")
        job_id = root["job_id"]
        self.last_job_id = job_id
        self.flow.write(FLOW_ROOT_JOB_CREATED, "root job created", turn=turn, job_id=job_id)
        write_job_tree_mirror(
            flow=self.flow,
            service=self.service,
            turn=turn,
            job_id=job_id,
            action="root_created",
        )
        write_process_step(
            flow=self.flow,
            step="chat.job.root_create",
            phase="job",
            action="created root job for chat turn",
            turn=turn,
            job_id=job_id,
        )
        bind_method_law_fragments_to_job(
            flow=self.flow,
            service=self.service,
            method=method,
            job_id=job_id,
            step="chat.method.law.bind",
            binding_reason="当前对话轮根业通过显式 method 参数绑定此法。",
            invocation_input={"job_id": job_id, "turn": turn, "user_input": user_input},
            output_contract="对话候选结果、方法自验、校验证据和验收路由证据。",
            acceptance_criteria="候选结果必须保留当前轮原始输入，并提交可追踪证据，不得自行接收或宣告完成。",
            return_point="当前对话轮根业候选提交、校验和验收路由。",
            budget={"max_repair_attempts": self.max_repair_attempts, "turn": turn},
            depth=0,
            turn=turn,
        )
        register_method_step_candidates(
            flow=self.flow,
            service=self.service,
            method=method,
            parent_job_id=job_id,
            step_prefix="chat.method.step_candidates",
            enabled=self.register_method_step_candidates,
            turn=turn,
        )

        self.service.mark_ready(job_id, actor_id="system")
        self.flow.write(FLOW_JOB_READY, "job marked ready", turn=turn, job_id=job_id)
        write_job_tree_mirror(
            flow=self.flow,
            service=self.service,
            turn=turn,
            job_id=job_id,
            action="job_ready",
        )
        write_process_step(
            flow=self.flow,
            step="chat.job.ready",
            phase="job",
            action="marked chat turn job ready",
            turn=turn,
            job_id=job_id,
        )

        self.service.start_job(job_id, actor_id="system")
        self.flow.write(FLOW_JOB_RUNNING, "job running", turn=turn, job_id=job_id)
        write_job_tree_mirror(
            flow=self.flow,
            service=self.service,
            turn=turn,
            job_id=job_id,
            action="job_running",
        )
        write_process_step(
            flow=self.flow,
            step="chat.job.run",
            phase="job",
            action="started chat turn job execution",
            turn=turn,
            job_id=job_id,
        )

        self.history.append({"role": "user", "content": user_input})
        client = self.client or ChatClient(load_ai_config(self.config_path))
        method_messages = build_method_system_messages(method)
        messages = [*method_messages, *self.history]
        self.flow.write(
            FLOW_METHOD_CONTEXT_INJECTED,
            "method context injected",
            turn=turn,
            job_id=job_id,
            method_name=method.name,
            method_path=str(method.path),
            method_checksum=method.checksum,
            method_law_fragment_count=str(len(method.fragments)),
            message_count=str(len(messages)),
        )
        write_process_step(
            flow=self.flow,
            step="chat.method.inject",
            phase="method",
            action="assembled chat provider messages with method context and history",
            turn=turn,
            job_id=job_id,
            message_count=str(len(messages)),
            method_law_fragment_count=str(len(method.fragments)),
        )
        self.flow.write(
            FLOW_AI_REQUEST_STARTED,
            "AI request started",
            turn=turn,
            job_id=job_id,
            message_count=str(len(messages)),
        )
        write_provider_messages(
            flow=self.flow,
            call_kind="candidate_generation",
            messages=messages,
            turn=turn,
            job_id=job_id,
        )
        write_process_step(
            flow=self.flow,
            step="chat.provider.request",
            phase="provider",
            action="sent chat turn messages to AI provider",
            status="started",
            turn=turn,
            job_id=job_id,
            message_count=str(len(messages)),
        )
        response = complete_with_provider_logging(
            flow=self.flow,
            client=client,
            messages=messages,
            call_kind="candidate_generation",
            turn=turn,
            job_id=job_id,
        )
        self.history.append({"role": "assistant", "content": response.content})
        self.flow.write(
            FLOW_AI_RESPONSE_RECEIVED,
            "AI response received",
            turn=turn,
            job_id=job_id,
            response=response.content,
        )
        write_process_step(
            flow=self.flow,
            step="chat.provider.response",
            phase="provider",
            action="received chat turn provider response",
            turn=turn,
            job_id=job_id,
        )

        candidate = self.service.submit_candidate(
            job_id,
            text=response.content,
            actor_id="ai",
            metadata={
                "appearance_kind": "root_candidate",
                "candidate_only": True,
            },
        )["candidate"]
        self.flow.write(
            FLOW_CANDIDATE_SUBMITTED,
            "candidate submitted",
            turn=turn,
            job_id=job_id,
            appearance_id=candidate["appearance_id"],
        )
        write_job_tree_mirror(
            flow=self.flow,
            service=self.service,
            turn=turn,
            job_id=job_id,
            action="candidate_attached",
            appearance_id=candidate["appearance_id"],
        )
        write_process_step(
            flow=self.flow,
            step="chat.candidate.submit",
            phase="candidate",
            action="stored chat response as candidate result",
            turn=turn,
            job_id=job_id,
            appearance_id=candidate["appearance_id"],
        )

        review = self._request_method_self_review(
            client=client,
            method=method,
            turn=turn,
            job_id=job_id,
            user_input=user_input,
            assistant_response=response.content,
        )
        record_method_learning_candidate(
            flow=self.flow,
            service=self.service,
            method=method,
            job_id=job_id,
            review=review,
            step_prefix="chat.method.self_review",
            turn=turn,
        )
        evidence = self.service.submit_evidence(
            job_id,
            text=method_evidence_payload(method=method, review=review),
            actor_id="system",
            metadata={
                "evidence_kind": "method_self_review",
                "evidence_hardness": "weak_ai",
            },
        )["evidence"]
        self.flow.write(
            FLOW_EVIDENCE_SUBMITTED,
            "evidence submitted",
            turn=turn,
            job_id=job_id,
            appearance_id=evidence["appearance_id"],
            evidence_kind="method_self_review",
            evidence_hardness="weak_ai",
        )
        write_job_tree_mirror(
            flow=self.flow,
            service=self.service,
            turn=turn,
            job_id=job_id,
            action="evidence_attached",
            appearance_id=evidence["appearance_id"],
        )
        write_process_step(
            flow=self.flow,
            step="chat.evidence.submit",
            phase="evidence",
            action="stored chat method self-review as evidence",
            turn=turn,
            job_id=job_id,
            appearance_id=evidence["appearance_id"],
        )
        run_split_proposal_registration(
            flow=self.flow,
            service=self.service,
            client=client,
            method=method,
            parent_job_id=job_id,
            user_input=user_input,
            candidate_text=response.content,
            candidate_appearance_id=candidate["appearance_id"],
            step_prefix="chat.split_proposal",
            turn=turn,
        )
        frontier_result = run_advancement_loop(
            flow=self.flow,
            service=self.service,
            client=client,
            root_job_id=job_id,
            user_input=user_input,
            root_method=method,
            root_candidate_text=response.content,
            root_candidate_appearance_id=candidate["appearance_id"],
            step_prefix="chat.advancement",
            turn=turn,
            max_advancement_waves=self.max_advancement_waves,
            max_child_dispatches=self.max_frontier_dispatches,
            max_child_package_repair_attempts=self.max_child_package_repair_attempts,
            max_parent_integration_repair_attempts=self.max_parent_integration_repair_attempts,
        )
        verification_candidate_text = str(
            frontier_result.get("latest_parent_candidate_text") or response.content
        )
        verification_candidate_appearance_id = str(
            frontier_result.get("latest_parent_candidate_appearance_id")
            or candidate["appearance_id"]
        )
        verification_result = run_candidate_verification(
            flow=self.flow,
            service=self.service,
            parent_job_id=job_id,
            user_input=user_input,
            candidate_text=verification_candidate_text,
            parent_candidate_appearance_id=verification_candidate_appearance_id,
            step_prefix="chat.candidate.verify",
            turn=turn,
        )
        repair_result = run_candidate_repair_loop(
            flow=self.flow,
            service=self.service,
            client=client,
            method=method,
            parent_job_id=job_id,
            user_input=user_input,
            initial_candidate_text=verification_candidate_text,
            initial_candidate_appearance_id=verification_candidate_appearance_id,
            initial_verification_result=verification_result,
            max_repair_attempts=self.max_repair_attempts,
            step_prefix="chat.candidate.verify",
            turn=turn,
        )
        routing_result = run_acceptance_routing(
            flow=self.flow,
            service=self.service,
            client=client,
            method=method,
            parent_job_id=job_id,
            user_input=user_input,
            repair_result=repair_result,
            step_prefix="chat.candidate.verify",
            turn=turn,
        )
        self.last_feedback_judgment = routing_result["judgment"]
        self.last_feedback_job_id = routing_result["feedback_job_id"]
        output_text = str(routing_result["latest_candidate_text"])
        if self.history and self.history[-1].get("role") == "assistant":
            self.history[-1]["content"] = output_text

        self.flow.write(
            FLOW_RESULT_OUTPUT_RECORDED,
            "result output recorded",
            turn=turn,
            result=output_text,
        )
        write_process_step(
            flow=self.flow,
            step="chat.output.record",
            phase="output",
            action="recorded chat result output",
            turn=turn,
            job_id=job_id,
        )

        self.flow.write(FLOW_CHAT_TURN_FINISHED, "chat turn finished", turn=turn, job_id=job_id)
        write_process_step(
            flow=self.flow,
            step="chat.turn.finish",
            phase="chat",
            action="finished chat turn",
            turn=turn,
            job_id=job_id,
        )
        return output_text

    def finish(self) -> None:
        self.flow.write(FLOW_CHAT_SESSION_FINISHED, "chat session finished")
        write_process_step(
            flow=self.flow,
            step="chat.session.finish",
            phase="chat",
            action="finished interactive chat session",
        )
        write_process_step(
            flow=self.flow,
            step="chat.sandbox.destroy",
            phase="cleanup",
            action="destroyed interactive chat sandbox",
            sandbox_path=str(self.sandbox_path),
            log_path=str(self.diagnostic_log_path),
            readable_log_path=str(self.readable_log_path),
        )
        self.flow.write(
            FLOW_SANDBOX_DESTROYED,
            "sandbox destroyed",
            sandbox_path=str(self.sandbox_path),
            log_path=str(self.diagnostic_log_path),
            readable_log_path=str(self.readable_log_path),
        )
        shutil.rmtree(self.sandbox_path, ignore_errors=True)
        self.service = None

    def fail(self, exc: Exception) -> None:
        write_process_step(
            flow=self.flow,
            step="chat.session.fail",
            phase="error",
            action="chat session failed before normal completion",
            status="failed",
            process_detail=str(exc),
        )
        self.flow.write(FLOW_RUN_FAILED, "chat session failed", error=str(exc))
        self.finish()

    def _reset_sandbox(self) -> None:
        if self.sandbox_path.exists():
            shutil.rmtree(self.sandbox_path)

    def _write_latest_log_pointer(self) -> None:
        self.log_dir.mkdir(parents=True, exist_ok=True)
        latest_log_pointer_path(self.log_dir).write_text(
            str(self.diagnostic_log_path), encoding="utf-8"
        )
        latest_readable_log_pointer_path(self.log_dir).write_text(
            str(self.readable_log_path), encoding="utf-8"
        )

    def _load_method_for_turn(self, *, turn: str) -> MethodContext:
        method = load_method_context(method_path=self.method_path)
        self.flow.write(
            FLOW_METHOD_SOURCE_RESOLVED,
            "method source resolved",
            turn=turn,
            method_path=str(method.path),
            method_checksum=method.checksum,
        )
        self.flow.write(
            FLOW_METHOD_CONTEXT_LOADED,
            "method context loaded",
            turn=turn,
            **method.log_fields(),
        )
        write_method_law_fragment_events(flow=self.flow, method=method, turn=turn)
        write_process_step(
            flow=self.flow,
            step="chat.method.load",
            phase="method",
            action="loaded method source for chat turn",
            turn=turn,
            method_path=str(method.path),
            method_checksum=method.checksum,
        )
        return method

    def _request_method_self_review(
        self,
        *,
        client: ChatClient,
        method: MethodContext,
        turn: str,
        job_id: str,
        user_input: str,
        assistant_response: str,
    ) -> str:
        data = {
            "turn": turn,
            "job_id": job_id,
            "method_name": method.name,
            "method_checksum": method.checksum,
        }
        self.flow.write(FLOW_METHOD_SELF_REVIEW_REQUESTED, "method self-review requested", **data)
        write_process_step(
            flow=self.flow,
            step="chat.method.self_review.request",
            phase="method",
            action="requested chat method self-review for candidate",
            status="started",
            **data,
        )
        review_messages = build_method_review_messages(
            method=method,
            user_input=user_input,
            assistant_response=assistant_response,
        )
        write_provider_messages(
            flow=self.flow,
            call_kind="method_self_review",
            messages=review_messages,
            turn=turn,
            job_id=job_id,
        )
        review = complete_with_provider_logging(
            flow=self.flow,
            client=client,
            messages=review_messages,
            call_kind="method_self_review",
            turn=turn,
            job_id=job_id,
        )
        received = {**data, "review": review.content}
        self.flow.write(FLOW_METHOD_SELF_REVIEW_RECEIVED, "method self-review received", **received)
        self.flow.write(
            FLOW_METHOD_UPDATE_CANDIDATE_RECORDED,
            "method update candidate recorded",
            **received,
        )
        write_process_step(
            flow=self.flow,
            step="chat.method.self_review.receive",
            phase="method",
            action="recorded chat method self-review and update candidates",
            **data,
        )
        return review.content
