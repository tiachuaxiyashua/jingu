"""Command-line interface for the minimal Jingu runtime."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from jingu.runtime.errors import JinguRuntimeError
from jingu.runtime.service import RuntimeService
from jingu.sandbox.flow import tail_flow_events
from jingu.sandbox.paths import latest_log_pointer_path, resolve_log_dir, resolve_sandbox_path
from jingu.sandbox.runner import AiSandboxRunner


def print_json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


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

    ai_parser = subparsers.add_parser("ai", help="AI sandbox commands.")
    ai_subparsers = ai_parser.add_subparsers(dest="ai_command", required=True)
    ai_run = ai_subparsers.add_parser("run", help="Run one AI chat in an ephemeral sandbox.")
    ai_run.add_argument("--message", required=True)
    ai_run.add_argument("--sandbox", type=Path)
    ai_run.add_argument("--log-dir", type=Path)
    ai_run.add_argument("--config", type=Path)
    ai_monitor = ai_subparsers.add_parser("monitor", help="Monitor the current AI sandbox flow.")
    ai_monitor.add_argument("--sandbox", type=Path)
    ai_monitor.add_argument("--log-dir", type=Path)
    ai_monitor.add_argument("--wait-seconds", type=float, default=30.0)

    return parser


def add_content_arguments(parser: argparse.ArgumentParser) -> None:
    content_group = parser.add_mutually_exclusive_group(required=True)
    content_group.add_argument("--file", type=Path)
    content_group.add_argument("--text")


def run(args: argparse.Namespace) -> Any:
    service = RuntimeService(args.workspace)

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

    if args.command == "candidate" and args.candidate_command == "submit":
        return service.submit_candidate(args.job_id, file_path=args.file, text=args.text)

    if args.command == "evidence" and args.evidence_command == "submit":
        return service.submit_evidence(args.job_id, file_path=args.file, text=args.text)

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

    raise JinguRuntimeError("unknown command")


def run_result_only(args: argparse.Namespace) -> str:
    if args.command == "ai" and args.ai_command == "run":
        return AiSandboxRunner(
            sandbox_path=args.sandbox,
            log_dir=args.log_dir,
            config_path=args.config,
        ).run(args.message)
    raise JinguRuntimeError("unknown result-only command")


def run_monitor(args: argparse.Namespace) -> None:
    sandbox_path = resolve_sandbox_path(args.sandbox)
    log_dir = resolve_log_dir(args.log_dir)
    log_pointer = latest_log_pointer_path(log_dir)
    if log_pointer.exists():
        print(f"log_path={log_pointer.read_text(encoding='utf-8').strip()}", flush=True)
    for event in tail_flow_events(sandbox_path, wait_seconds=args.wait_seconds):
        print(format_flow_event(event), flush=True)


def format_flow_event(event: dict[str, Any]) -> str:
    data = event.get("data") or {}
    data_text = " ".join(f"{key}={value}" for key, value in sorted(data.items()))
    suffix = f" {data_text}" if data_text else ""
    return f"{event.get('timestamp', '')} {event.get('event_type', '')}: {event.get('message', '')}{suffix}"


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "ai" and args.ai_command == "run":
            print(run_result_only(args))
            return 0
        if args.command == "ai" and args.ai_command == "monitor":
            run_monitor(args)
            return 0
        print_json(run(args))
    except (JinguRuntimeError, ValueError, OSError) as exc:
        if getattr(args, "command", None) == "ai":
            print(str(exc), file=sys.stderr)
        else:
            print_json({"error": str(exc)})
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
