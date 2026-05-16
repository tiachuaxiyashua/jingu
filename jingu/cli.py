"""Command-line interface for the minimal Jingu runtime."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from jingu.runtime.errors import JinguRuntimeError
from jingu.runtime.service import RuntimeService


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


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        print_json(run(args))
    except (JinguRuntimeError, ValueError, OSError) as exc:
        print_json({"error": str(exc)})
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
