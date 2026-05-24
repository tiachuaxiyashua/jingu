"""Command-line interface for the minimal Jingu runtime."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from jingu.runtime.errors import JinguRuntimeError
from jingu.runtime.service import RuntimeService
from jingu.runtime.tree import TreeService
from jingu.sandbox.flow import format_readable_event, tail_flow_events
from jingu.sandbox.paths import (
    latest_log_pointer_path,
    latest_readable_log_pointer_path,
    resolve_log_dir,
    resolve_sandbox_path,
)
from jingu.sandbox.runner import (
    DEFAULT_MAX_ADVANCEMENT_WAVES,
    DEFAULT_MAX_CHILD_PACKAGE_REPAIR_ATTEMPTS,
    DEFAULT_MAX_FRONTIER_DISPATCHES,
    DEFAULT_MAX_PARENT_INTEGRATION_REPAIR_ATTEMPTS,
    DEFAULT_MAX_REPAIR_ATTEMPTS,
    DEFAULT_REGISTER_METHOD_STEP_CANDIDATES,
    AiSandboxChatSession,
    AiSandboxRunner,
)


def print_json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def configure_text_io() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        options = {"errors": "replace"}
        if getattr(stream, "isatty", lambda: False)():
            options["encoding"] = "utf-8"
        try:
            reconfigure(**options)
        except (OSError, ValueError):
            continue


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="jingu")
    parser.add_argument("--workspace", default=".", help="Workspace root for local runtime state.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init", help="Initialize local runtime state.")

    root_parser = subparsers.add_parser("root", help="Root job commands.")
    root_subparsers = root_parser.add_subparsers(dest="root_command", required=True)
    root_create = root_subparsers.add_parser("create", help="Create a root job from an original wish.")
    root_create.add_argument("--wish", required=True)
    root_create.add_argument("--target")
    root_create.add_argument("--acceptance-criteria", default="")
    root_create.add_argument("--gap", action="append", default=[])

    job_parser = subparsers.add_parser("job", help="Job state commands.")
    job_subparsers = job_parser.add_subparsers(dest="job_command", required=True)
    job_ready = job_subparsers.add_parser("ready", help="Mark a job ready.")
    job_ready.add_argument("job_id")
    job_run = job_subparsers.add_parser("run", help="Start a ready job.")
    job_run.add_argument("job_id")
    job_resolve_gaps = job_subparsers.add_parser(
        "resolve-gaps", help="Record context that resolves one or more required gaps."
    )
    job_resolve_gaps.add_argument("job_id")
    job_resolve_gaps.add_argument("--text", required=True)
    job_resolve_gaps.add_argument("--gap", action="append", default=[])

    candidate_parser = subparsers.add_parser("candidate", help="Candidate result commands.")
    candidate_subparsers = candidate_parser.add_subparsers(dest="candidate_command", required=True)
    candidate_submit = candidate_subparsers.add_parser("submit", help="Submit a candidate result.")
    candidate_submit.add_argument("job_id")
    add_content_arguments(candidate_submit)

    evidence_parser = subparsers.add_parser("evidence", help="Evidence commands.")
    evidence_subparsers = evidence_parser.add_subparsers(dest="evidence_command", required=True)
    evidence_submit = evidence_subparsers.add_parser("submit", help="Submit evidence.")
    evidence_submit.add_argument("job_id")
    add_content_arguments(evidence_submit)

    decision_parser = subparsers.add_parser("decision", help="Human decision return commands.")
    decision_subparsers = decision_parser.add_subparsers(dest="decision_command", required=True)
    decision_return = decision_subparsers.add_parser("return", help="Record a returned human decision as evidence.")
    decision_return.add_argument("job_id")
    decision_return.add_argument("--text", required=True)

    accept_parser = subparsers.add_parser("accept", help="Accept a candidate result with evidence.")
    accept_parser.add_argument("job_id")
    accept_parser.add_argument("--candidate")
    accept_parser.add_argument("--evidence")
    accept_parser.add_argument("--completion-scope", default="self")

    reject_parser = subparsers.add_parser("reject", help="Reject a candidate result.")
    reject_parser.add_argument("job_id")
    reject_parser.add_argument("--candidate")
    reject_parser.add_argument("--reason", required=True)

    status_parser = subparsers.add_parser("status", help="Show job status.")
    status_parser.add_argument("job_id")

    events_parser = subparsers.add_parser("events", help="Show job event ledger.")
    events_parser.add_argument("job_id")

    tree_parser = subparsers.add_parser("tree", help="Job tree commands.")
    tree_subparsers = tree_parser.add_subparsers(dest="tree_command", required=True)
    tree_propose_child = tree_subparsers.add_parser(
        "propose-child", help="Create a guarded child job from a split proposal."
    )
    tree_propose_child.add_argument("parent_job_id")
    tree_propose_child.add_argument("--target", required=True)
    tree_propose_child.add_argument("--blocking-reason", required=True)
    tree_propose_child.add_argument("--output-contract", required=True)
    tree_propose_child.add_argument("--acceptance-criteria", required=True)
    tree_propose_child.add_argument("--estimated-effort", type=int, required=True)
    tree_propose_child.add_argument("--depth-limit", type=int, required=True)
    tree_propose_child.add_argument("--gap", action="append", default=[])
    tree_propose_child.add_argument("--method", type=Path)
    tree_propose_child.add_argument("--method-reason")
    tree_propose_child.add_argument("--method-return-point")

    tree_show = tree_subparsers.add_parser("show", help="Show a root job tree.")
    tree_show.add_argument("job_id")
    tree_frontier = tree_subparsers.add_parser("frontier", help="Show active leaf jobs.")
    tree_frontier.add_argument("job_id")
    tree_package = tree_subparsers.add_parser(
        "submit-package", help="Submit a structured result package."
    )
    tree_package.add_argument("job_id")
    tree_package.add_argument("--file", type=Path, required=True)
    tree_package.add_argument("--evidence-text")
    tree_reevaluate = tree_subparsers.add_parser(
        "reevaluate", help="Show parent re-evaluation data."
    )
    tree_reevaluate.add_argument("job_id")

    ai_parser = subparsers.add_parser("ai", help="AI sandbox commands.")
    ai_subparsers = ai_parser.add_subparsers(dest="ai_command", required=True)
    ai_run = ai_subparsers.add_parser("run", help="Run one AI chat in an ephemeral sandbox.")
    ai_run.add_argument("--message", required=True)
    ai_run.add_argument("--sandbox", type=Path)
    ai_run.add_argument("--log-dir", type=Path)
    ai_run.add_argument("--config", type=Path)
    ai_run.add_argument("--method", type=Path)
    ai_run.add_argument("--max-repair-attempts", type=int, default=DEFAULT_MAX_REPAIR_ATTEMPTS)
    ai_run.add_argument(
        "--max-frontier-dispatches",
        type=int,
        default=DEFAULT_MAX_FRONTIER_DISPATCHES,
    )
    ai_run.add_argument(
        "--max-child-package-repair-attempts",
        type=int,
        default=DEFAULT_MAX_CHILD_PACKAGE_REPAIR_ATTEMPTS,
    )
    ai_run.add_argument("--max-advancement-waves", type=int, default=DEFAULT_MAX_ADVANCEMENT_WAVES)
    ai_run.add_argument(
        "--max-parent-integration-repair-attempts",
        type=int,
        default=DEFAULT_MAX_PARENT_INTEGRATION_REPAIR_ATTEMPTS,
    )
    ai_run.add_argument(
        "--register-method-step-candidates",
        action="store_true",
        default=DEFAULT_REGISTER_METHOD_STEP_CANDIDATES,
    )
    ai_resume = ai_subparsers.add_parser("resume", help="Resume an AI sandbox run from a runtime checkpoint.")
    ai_resume.add_argument("--checkpoint", type=Path, required=True)
    ai_resume.add_argument("--sandbox", type=Path)
    ai_resume.add_argument("--log-dir", type=Path)
    ai_resume.add_argument("--config", type=Path)
    ai_resume.add_argument("--method", type=Path)
    ai_resume.add_argument("--human-response")
    ai_resume.add_argument("--feedback-job-id")
    ai_resume.add_argument("--resolve-gap", action="append", default=[])
    ai_resume.add_argument("--context-only", action="store_true")
    ai_resume.add_argument("--max-repair-attempts", type=int, default=DEFAULT_MAX_REPAIR_ATTEMPTS)
    ai_resume.add_argument(
        "--max-frontier-dispatches",
        type=int,
        default=DEFAULT_MAX_FRONTIER_DISPATCHES,
    )
    ai_resume.add_argument(
        "--max-child-package-repair-attempts",
        type=int,
        default=DEFAULT_MAX_CHILD_PACKAGE_REPAIR_ATTEMPTS,
    )
    ai_resume.add_argument("--max-advancement-waves", type=int, default=DEFAULT_MAX_ADVANCEMENT_WAVES)
    ai_resume.add_argument(
        "--max-parent-integration-repair-attempts",
        type=int,
        default=DEFAULT_MAX_PARENT_INTEGRATION_REPAIR_ATTEMPTS,
    )
    ai_resume.add_argument(
        "--register-method-step-candidates",
        action="store_true",
        default=DEFAULT_REGISTER_METHOD_STEP_CANDIDATES,
    )
    ai_monitor = ai_subparsers.add_parser("monitor", help="Monitor the current AI sandbox flow.")
    ai_monitor.add_argument("--sandbox", type=Path)
    ai_monitor.add_argument("--log-dir", type=Path)
    ai_monitor.add_argument("--wait-seconds", type=float, default=30.0)
    ai_chat = ai_subparsers.add_parser("chat", help="Start an interactive AI chat session.")
    ai_chat.add_argument("--sandbox", type=Path)
    ai_chat.add_argument("--log-dir", type=Path)
    ai_chat.add_argument("--config", type=Path)
    ai_chat.add_argument("--method", type=Path)
    ai_chat.add_argument("--max-repair-attempts", type=int, default=DEFAULT_MAX_REPAIR_ATTEMPTS)
    ai_chat.add_argument(
        "--max-frontier-dispatches",
        type=int,
        default=DEFAULT_MAX_FRONTIER_DISPATCHES,
    )
    ai_chat.add_argument(
        "--max-child-package-repair-attempts",
        type=int,
        default=DEFAULT_MAX_CHILD_PACKAGE_REPAIR_ATTEMPTS,
    )
    ai_chat.add_argument("--max-advancement-waves", type=int, default=DEFAULT_MAX_ADVANCEMENT_WAVES)
    ai_chat.add_argument(
        "--max-parent-integration-repair-attempts",
        type=int,
        default=DEFAULT_MAX_PARENT_INTEGRATION_REPAIR_ATTEMPTS,
    )
    ai_chat.add_argument(
        "--register-method-step-candidates",
        action="store_true",
        default=DEFAULT_REGISTER_METHOD_STEP_CANDIDATES,
    )

    return parser


def add_content_arguments(parser: argparse.ArgumentParser) -> None:
    content_group = parser.add_mutually_exclusive_group(required=True)
    content_group.add_argument("--file", type=Path)
    content_group.add_argument("--text")


def run(args: argparse.Namespace) -> Any:
    service = RuntimeService(args.workspace)
    tree_service = TreeService(args.workspace)

    if args.command == "init":
        return service.initialize()

    if args.command == "root" and args.root_command == "create":
        return service.create_root_job(
            wish=args.wish,
            target=args.target,
            acceptance_criteria=args.acceptance_criteria,
            required_context_gaps=args.gap,
        )

    if args.command == "job" and args.job_command == "ready":
        return service.mark_ready(args.job_id)

    if args.command == "job" and args.job_command == "run":
        return service.start_job(args.job_id)

    if args.command == "job" and args.job_command == "resolve-gaps":
        return service.resolve_context_gaps(
            args.job_id,
            resolution_text=args.text,
            resolved_gaps=args.gap or None,
            actor_id="human",
        )

    if args.command == "candidate" and args.candidate_command == "submit":
        return service.submit_candidate(args.job_id, file_path=args.file, text=args.text)

    if args.command == "evidence" and args.evidence_command == "submit":
        return service.submit_evidence(args.job_id, file_path=args.file, text=args.text)

    if args.command == "decision" and args.decision_command == "return":
        return service.record_human_decision(args.job_id, decision_text=args.text, actor_id="human")

    if args.command == "accept":
        return service.accept_candidate(
            args.job_id,
            candidate_appearance_id=args.candidate,
            evidence_appearance_id=args.evidence,
            completion_scope=args.completion_scope,
        )

    if args.command == "reject":
        return service.reject_candidate(
            args.job_id,
            candidate_appearance_id=args.candidate,
            reason=args.reason,
        )

    if args.command == "status":
        return service.get_status(args.job_id)

    if args.command == "events":
        return service.list_events(args.job_id)

    if args.command == "tree" and args.tree_command == "propose-child":
        return tree_service.propose_child_job(
            parent_job_id=args.parent_job_id,
            target=args.target,
            blocking_reason=args.blocking_reason,
            output_contract=args.output_contract,
            acceptance_criteria=args.acceptance_criteria,
            estimated_effort=args.estimated_effort,
            depth_limit=args.depth_limit,
            required_context_gaps=args.gap,
            method_path=args.method,
            method_binding_reason=args.method_reason,
            method_return_point=args.method_return_point,
            actor_id="human",
        )

    if args.command == "tree" and args.tree_command == "show":
        return tree_service.get_tree(args.job_id)

    if args.command == "tree" and args.tree_command == "frontier":
        return tree_service.get_frontier(args.job_id)

    if args.command == "tree" and args.tree_command == "submit-package":
        return tree_service.submit_result_package(
            args.job_id,
            package=read_json_file(args.file),
            evidence_text=args.evidence_text,
            actor_id="human",
        )

    if args.command == "tree" and args.tree_command == "reevaluate":
        return tree_service.reevaluate_parent(args.job_id)

    raise JinguRuntimeError("unknown command")


def read_json_file(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("JSON file must contain an object")
    return payload


def run_result_only(args: argparse.Namespace) -> str:
    if args.command == "ai" and args.ai_command == "run":
        return AiSandboxRunner(
            sandbox_path=args.sandbox,
            log_dir=args.log_dir,
            config_path=args.config,
            method_path=args.method,
            max_repair_attempts=args.max_repair_attempts,
            max_frontier_dispatches=args.max_frontier_dispatches,
            max_child_package_repair_attempts=args.max_child_package_repair_attempts,
            max_advancement_waves=args.max_advancement_waves,
            max_parent_integration_repair_attempts=args.max_parent_integration_repair_attempts,
            register_method_step_candidates=args.register_method_step_candidates,
        ).run(args.message)
    if args.command == "ai" and args.ai_command == "resume":
        return AiSandboxRunner(
            sandbox_path=args.sandbox,
            log_dir=args.log_dir,
            config_path=args.config,
            method_path=args.method,
            max_repair_attempts=args.max_repair_attempts,
            max_frontier_dispatches=args.max_frontier_dispatches,
            max_child_package_repair_attempts=args.max_child_package_repair_attempts,
            max_advancement_waves=args.max_advancement_waves,
            max_parent_integration_repair_attempts=args.max_parent_integration_repair_attempts,
            register_method_step_candidates=args.register_method_step_candidates,
        ).resume(
            checkpoint_path=args.checkpoint,
            human_response=args.human_response,
            feedback_job_id=args.feedback_job_id,
            resolved_gaps=args.resolve_gap or None,
            treat_as_decision=not args.context_only,
        )
    raise JinguRuntimeError("unknown result-only command")


def run_monitor(args: argparse.Namespace) -> None:
    sandbox_path = resolve_sandbox_path(args.sandbox)
    log_dir = resolve_log_dir(args.log_dir)
    log_pointer = latest_log_pointer_path(log_dir)
    readable_pointer = latest_readable_log_pointer_path(log_dir)
    if log_pointer.exists():
        print(f"jsonl_log_path={log_pointer.read_text(encoding='utf-8').strip()}", flush=True)
    if readable_pointer.exists():
        print(
            f"readable_log_path={readable_pointer.read_text(encoding='utf-8').strip()}",
            flush=True,
        )
    for event in tail_flow_events(sandbox_path, wait_seconds=args.wait_seconds):
        sys.stdout.write(format_readable_event(event))
        sys.stdout.flush()


def run_chat(args: argparse.Namespace) -> None:
    session = AiSandboxChatSession(
        sandbox_path=args.sandbox,
        log_dir=args.log_dir,
        config_path=args.config,
        method_path=args.method,
        max_repair_attempts=args.max_repair_attempts,
        max_frontier_dispatches=args.max_frontier_dispatches,
        max_child_package_repair_attempts=args.max_child_package_repair_attempts,
        max_advancement_waves=args.max_advancement_waves,
        max_parent_integration_repair_attempts=args.max_parent_integration_repair_attempts,
        register_method_step_candidates=args.register_method_step_candidates,
    )
    session.start()
    print("Jingu AI chat started. Type /exit to finish.", flush=True)
    try:
        while True:
            user_input = input("You> ").strip()
            if not user_input:
                continue
            if user_input.lower() in {"/exit", "/quit", "exit", "quit"}:
                session.finish()
                print("Session closed.", flush=True)
                return
            answer = session.ask(user_input)
            print(f"AI> {answer}", flush=True)
    except (KeyboardInterrupt, EOFError):
        session.finish()
        print("\nSession closed.", flush=True)
    except Exception as exc:
        session.fail(exc)
        raise


def main(argv: list[str] | None = None) -> int:
    configure_text_io()
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "ai" and args.ai_command in {"run", "resume"}:
            print(run_result_only(args))
            return 0
        if args.command == "ai" and args.ai_command == "chat":
            run_chat(args)
            return 0
        if args.command == "ai" and args.ai_command == "monitor":
            run_monitor(args)
            return 0
        print_json(run(args))
    except (JinguRuntimeError, RuntimeError, ValueError, OSError) as exc:
        if getattr(args, "command", None) == "ai":
            print(str(exc), file=sys.stderr)
        else:
            print_json({"error": str(exc)})
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
