"""Ephemeral AI chat runner."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from jingu.ai.client import ChatClient
from jingu.ai.config import load_ai_config
from jingu.runtime.constants import STATE_ABANDONED, STATE_ACCEPTED, STATE_REJECTED
from jingu.runtime.repository import decode_json
from jingu.runtime.service import RuntimeService
from jingu.sandbox.flow import (
    FLOW_AI_REQUEST_STARTED,
    FLOW_AI_RESPONSE_RECEIVED,
    FLOW_CANDIDATE_SUBMITTED,
    FLOW_CHAT_SESSION_FINISHED,
    FLOW_CHAT_SESSION_STARTED,
    FLOW_CHAT_TURN_FINISHED,
    FLOW_EVIDENCE_SUBMITTED,
    FLOW_FEEDBACK_JUDGMENT_RECEIVED,
    FLOW_FEEDBACK_JUDGMENT_REQUESTED,
    FLOW_FEEDBACK_JOB_CREATED,
    FLOW_FEEDBACK_JOB_SKIPPED,
    FLOW_INPUT_PROVENANCE_RECORDED,
    FLOW_JOB_READY,
    FLOW_JOB_RUNNING,
    FLOW_JOB_TREE_MANAGEMENT_RECORDED,
    FLOW_JOB_TREE_SNAPSHOT_RECORDED,
    FLOW_METHOD_CONTEXT_INJECTED,
    FLOW_METHOD_CONTEXT_LOADED,
    FLOW_METHOD_LAW_FRAGMENT_BOUND,
    FLOW_METHOD_LAW_FRAGMENT_LOADED,
    FLOW_METHOD_SELF_REVIEW_RECEIVED,
    FLOW_METHOD_SELF_REVIEW_REQUESTED,
    FLOW_METHOD_SOURCE_RESOLVED,
    FLOW_METHOD_UPDATE_CANDIDATE_RECORDED,
    FLOW_PROCESS_STEP_RECORDED,
    FLOW_PROVIDER_MESSAGES_RECORDED,
    FLOW_PROVIDER_STREAM_DELTA_RECEIVED,
    FLOW_PROVIDER_STREAM_FINISHED,
    FLOW_PARENT_VERIFICATION_EVIDENCE_SUBMITTED,
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
VERIFICATION_FEEDBACK_JOB_TARGET = "处理候选校验未解决问题"
VERIFICATION_FEEDBACK_JOB_ACCEPTANCE_CRITERIA = "产出下一步修复方向、人工反馈问题或方法更新候选，并引用校验证据。"
DEFAULT_MAX_REPAIR_ATTEMPTS = 1
REPAIRABLE_CHECK_KINDS = frozenset(
    {
        "cjk_length_range",
        "cjk_length_minimum",
        "cjk_length_maximum",
        "incomplete_output_signal",
    }
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
    turn: str | None = None,
) -> None:
    result = service.bind_method_law_fragments(
        job_id,
        fragments=[fragment.binding_payload(method=method) for fragment in method.fragments],
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
    write_process_step(
        flow=flow,
        step=step,
        phase="method",
        action="bound method-law fragments to current job as appearances",
        **data,
    )


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
    )["candidate"]
    result_data = {
        **child_job_data,
        "verification_status": str(report["overall_status"]),
        "verification_check_count": str(len(report["checks"])),
        "verification_candidate_appearance_id": verification_candidate["appearance_id"],
        "verification_report": report_json,
        "verification_gaps": json.dumps(report["gaps"], ensure_ascii=False, sort_keys=True),
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
    )["evidence"]
    child_evidence_data = {
        **child_job_data,
        "verification_status": str(report["overall_status"]),
        "verification_candidate_appearance_id": verification_candidate["appearance_id"],
        "verification_evidence_appearance_id": verification_evidence["appearance_id"],
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
) -> list[dict[str, str]]:
    repair_payload = {
        "task": user_input,
        "attempt": attempt,
        "max_attempts": max_attempts,
        "previous_candidate": previous_candidate_text,
        "verification_report": compact_verification_report(verification_result["report"]),
        "repairable_failed_checks": [
            compact_verification_check(check)
            for check in repairable_failed_checks(verification_result["report"])
        ],
        "requirements": [
            "保持用户原始任务意图，不自行改写目标。",
            "只针对校验报告中的具体失败项修订候选结果。",
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
) -> dict[str, Any]:
    repair_checks = repairable_failed_checks(previous_verification_result["report"])
    repair_job = service.create_child_job(
        parent_job_id=parent_job_id,
        target=REPAIR_JOB_TARGET,
        actor_id="system",
        acceptance_criteria=REPAIR_JOB_ACCEPTANCE_CRITERIA,
    )
    repair_job_id = repair_job["job_id"]
    base_data = {
        **turn_field(turn),
        "job_id": repair_job_id,
        "parent_job_id": parent_job_id,
        "repair_child_job_id": repair_job_id,
        "repair_attempt": str(attempt),
        "repair_max_attempts": str(max_attempts),
        "repairable_check_count": str(len(repair_checks)),
        "repairable_checks": json.dumps(
            [compact_verification_check(check) for check in repair_checks],
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        ),
        "appearance_id": previous_candidate_appearance_id,
    }
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
        call_kind="candidate_repair",
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
        call_kind="candidate_repair",
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

    nodes = [job_tree_node(row) for row in rows]
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


def job_tree_node(job: dict[str, Any]) -> dict[str, Any]:
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
    ) -> None:
        self.sandbox_path = resolve_sandbox_path(sandbox_path)
        self.log_dir = resolve_log_dir(log_dir)
        self.diagnostic_log_path = new_diagnostic_log_path(self.log_dir)
        self.readable_log_path = readable_log_path_for(self.diagnostic_log_path)
        self.config_path = Path(config_path) if config_path is not None else None
        self.method_path = Path(method_path) if method_path is not None else None
        self.client = client
        self.max_repair_attempts = normalize_max_repair_attempts(max_repair_attempts)
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
            evidence = service.submit_evidence(
                job_id,
                text=method_evidence_payload(method=method, review=review),
                actor_id="system",
            )["evidence"]
            self.flow.write(
                FLOW_EVIDENCE_SUBMITTED,
                "evidence submitted",
                job_id=job_id,
                appearance_id=evidence["appearance_id"],
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
            verification_result = run_candidate_verification(
                flow=self.flow,
                service=service,
                parent_job_id=job_id,
                user_input=message,
                candidate_text=response.content,
                parent_candidate_appearance_id=candidate["appearance_id"],
                step_prefix="candidate.verify",
            )
            repair_result = run_candidate_repair_loop(
                flow=self.flow,
                service=service,
                client=client,
                method=method,
                parent_job_id=job_id,
                user_input=message,
                initial_candidate_text=response.content,
                initial_candidate_appearance_id=candidate["appearance_id"],
                initial_verification_result=verification_result,
                max_repair_attempts=self.max_repair_attempts,
                step_prefix="candidate.verify",
            )
            output_text = str(repair_result["latest_candidate_text"])

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
    ) -> None:
        self.sandbox_path = resolve_sandbox_path(sandbox_path)
        self.log_dir = resolve_log_dir(log_dir)
        self.diagnostic_log_path = new_diagnostic_log_path(self.log_dir)
        self.readable_log_path = readable_log_path_for(self.diagnostic_log_path)
        self.config_path = Path(config_path) if config_path is not None else None
        self.method_path = Path(method_path) if method_path is not None else None
        self.client = client
        self.max_repair_attempts = normalize_max_repair_attempts(max_repair_attempts)
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
        evidence = self.service.submit_evidence(
            job_id,
            text=method_evidence_payload(method=method, review=review),
            actor_id="system",
        )["evidence"]
        self.flow.write(
            FLOW_EVIDENCE_SUBMITTED,
            "evidence submitted",
            turn=turn,
            job_id=job_id,
            appearance_id=evidence["appearance_id"],
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
        verification_result = run_candidate_verification(
            flow=self.flow,
            service=self.service,
            parent_job_id=job_id,
            user_input=user_input,
            candidate_text=response.content,
            parent_candidate_appearance_id=candidate["appearance_id"],
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
            initial_candidate_text=response.content,
            initial_candidate_appearance_id=candidate["appearance_id"],
            initial_verification_result=verification_result,
            max_repair_attempts=self.max_repair_attempts,
            step_prefix="chat.candidate.verify",
            turn=turn,
        )
        output_text = str(repair_result["latest_candidate_text"])
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

        judgment = self._request_feedback_judgment(
            client=client,
            turn=turn,
            job_id=job_id,
            user_input=user_input,
            assistant_response=output_text,
        )
        self.last_feedback_judgment = judgment
        if judgment["needs_feedback_job"]:
            feedback_job = self.service.create_child_job(
                parent_job_id=job_id,
                target=judgment["feedback_job_summary"],
                actor_id="ai",
                required_context_gaps=judgment["required_context_gaps"],
            )
            self.last_feedback_job_id = feedback_job["job_id"]
            self.flow.write(
                FLOW_FEEDBACK_JOB_CREATED,
                "feedback job created",
                turn=turn,
                job_id=job_id,
                feedback_job_id=feedback_job["job_id"],
                feedback_job_kind=judgment["feedback_job_kind"],
                feedback_job_target=judgment["feedback_job_summary"],
                required_context_gaps=json.dumps(
                    judgment["required_context_gaps"], ensure_ascii=False, sort_keys=True
                ),
            )
            write_job_tree_mirror(
                flow=self.flow,
                service=self.service,
                turn=turn,
                job_id=feedback_job["job_id"],
                action="feedback_child_created",
                child_job_id=feedback_job["job_id"],
                feedback_job_kind=judgment["feedback_job_kind"],
            )
            write_process_step(
                flow=self.flow,
                step="chat.feedback_job.create",
                phase="feedback",
                action="created feedback child job from AI judgment",
                turn=turn,
                job_id=job_id,
                feedback_job_id=feedback_job["job_id"],
                feedback_job_kind=judgment["feedback_job_kind"],
            )
        else:
            self.flow.write(
                FLOW_FEEDBACK_JOB_SKIPPED,
                "feedback job skipped",
                turn=turn,
                job_id=job_id,
                feedback_job_kind=judgment["feedback_job_kind"],
                reason=judgment["reason"],
            )
            write_job_tree_mirror(
                flow=self.flow,
                service=self.service,
                turn=turn,
                job_id=job_id,
                action="feedback_child_skipped",
                feedback_job_kind=judgment["feedback_job_kind"],
                reason=judgment["reason"],
            )
            write_process_step(
                flow=self.flow,
                step="chat.feedback_job.skip",
                phase="feedback",
                action="skipped feedback child job from AI judgment",
                turn=turn,
                job_id=job_id,
                feedback_job_kind=judgment["feedback_job_kind"],
                reason=judgment["reason"],
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

    def _request_feedback_judgment(
        self,
        *,
        client: ChatClient,
        turn: str,
        job_id: str,
        user_input: str,
        assistant_response: str,
    ) -> dict[str, Any]:
        system_prompt = (
            "You judge whether the latest turn needs a feedback job. "
            "Return compact JSON only with keys: needs_feedback_job, feedback_job_kind, "
            "feedback_job_summary, required_context_gaps, reason. "
            "Use feedback_job_kind=high_value for decisive or high-risk follow-up, "
            "directional for guidance or correction, and none when no feedback job is needed."
        )
        request_payload = {
            "turn": turn,
            "job_id": job_id,
            "user_input": user_input,
            "assistant_response": assistant_response,
            "conversation_size": len(self.history),
        }
        self.flow.write(
            FLOW_FEEDBACK_JUDGMENT_REQUESTED,
            "feedback judgment requested",
            turn=turn,
            job_id=job_id,
            message_count=str(len(self.history)),
        )
        feedback_messages = [
            {"role": "system", "content": system_prompt},
            *self.history,
            {"role": "user", "content": json.dumps(request_payload, ensure_ascii=False, sort_keys=True)},
        ]
        write_provider_messages(
            flow=self.flow,
            call_kind="feedback_judgment",
            messages=feedback_messages,
            turn=turn,
            job_id=job_id,
        )
        write_process_step(
            flow=self.flow,
            step="chat.feedback_judgment.request",
            phase="feedback",
            action="requested AI judgment about feedback child job",
            status="started",
            turn=turn,
            job_id=job_id,
            message_count=str(len(self.history)),
        )
        judgment_response = complete_with_provider_logging(
            flow=self.flow,
            client=client,
            messages=feedback_messages,
            call_kind="feedback_judgment",
            turn=turn,
            job_id=job_id,
        )
        self.flow.write(
            FLOW_FEEDBACK_JUDGMENT_RECEIVED,
            "feedback judgment received",
            turn=turn,
            job_id=job_id,
            judgment=judgment_response.content,
        )
        write_process_step(
            flow=self.flow,
            step="chat.feedback_judgment.receive",
            phase="feedback",
            action="received AI judgment about feedback child job",
            turn=turn,
            job_id=job_id,
        )
        return self._parse_feedback_judgment(judgment_response.content)

    @staticmethod
    def _parse_feedback_judgment(content: str) -> dict[str, Any]:
        payload = AiSandboxChatSession._load_json_object(content)
        if not isinstance(payload, dict):
            raise RuntimeError("feedback judgment response must be a JSON object")

        needs_feedback_job = bool(payload.get("needs_feedback_job"))
        feedback_job_kind = str(payload.get("feedback_job_kind") or "none").strip()
        feedback_job_summary = str(payload.get("feedback_job_summary") or "").strip()
        reason = str(payload.get("reason") or "").strip()
        raw_gaps = payload.get("required_context_gaps") or []
        if not isinstance(raw_gaps, list):
            raise RuntimeError("feedback judgment response must include required_context_gaps as a list")

        required_context_gaps = [str(item).strip() for item in raw_gaps if str(item).strip()]

        if needs_feedback_job:
            if feedback_job_kind not in {"high_value", "directional"}:
                raise RuntimeError(
                    "feedback judgment response must choose high_value or directional"
                )
            if not feedback_job_summary:
                raise RuntimeError(
                    "feedback judgment response must include feedback_job_summary"
                )
        else:
            feedback_job_kind = "none"
            feedback_job_summary = ""

        return {
            "needs_feedback_job": needs_feedback_job,
            "feedback_job_kind": feedback_job_kind,
            "feedback_job_summary": feedback_job_summary,
            "required_context_gaps": required_context_gaps,
            "reason": reason,
        }

    @staticmethod
    def _load_json_object(content: str) -> Any:
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

            raise RuntimeError("feedback judgment response must be valid JSON") from first_error
