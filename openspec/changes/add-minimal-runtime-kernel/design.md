## Context

Jingu currently has a truth source but no executable runtime. The first implementation must prove the architectural root laws in code before any model runner, UI, or multi-agent workflow is added.

The truth source requires the first runtime shape to stay small: a local runtime database, an object store for large results, append-only events, candidate isolation, evidence-backed acceptance, and guardrails that block illegal state changes before they become durable state.

## Goals / Non-Goals

**Goals:**

- Implement a local runtime kernel that can be initialized in a repository or workspace.
- Persist jobs, appearances, and append-only events.
- Preserve original human wishes as immutable source appearances.
- Allow manual candidate result and evidence submission.
- Require evidence before a job can be accepted as complete.
- Keep candidate results isolated until the responsible job accepts them.
- Reject state transitions that violate first-stage root-law checks.
- Provide a small CLI for driving and inspecting the first manual workflow.
- Cover the hard failure cases with automated tests.

**Non-Goals:**

- No model provider integration.
- No graphical UI.
- No automatic decomposition, parallel job scheduling, or multi-agent message bus.
- No stable law/method/role registry beyond the generic appearance table.
- No networked service or remote synchronization.

## Decisions

### Use Python and SQLite for the first kernel

The first implementation will use Python with the standard `sqlite3` library. SQLite directly matches the local runtime library in the truth source, requires no daemon, supports transactions, and is simple to test.

Alternatives considered:

- Node/TypeScript: useful later for desktop UI integration, but it adds package and runtime choices before the kernel semantics are proven.
- PostgreSQL: stronger for concurrent services, but too heavy for a local first-stage harness.

### Store semantic objects in three core tables

The runtime will implement:

- `jobs`: job contract and current state fields.
- `appearances`: all first-stage semantic objects, including original wishes, candidate results, accepted results, and evidence.
- `events`: append-only ledger of durable transitions.

This keeps physical carriers minimal while still allowing many semantic object classes through `appearance_type`.

### Treat events as the durable audit source

Every state-changing operation records an event in the append-only ledger. Operational fields on `jobs` and `appearances` are updated transactionally for simple querying, but the event table remains the audit trail and records a hash chain.

Deleting or rewriting events is out of scope for normal runtime APIs.

### Enforce guardrails before event insertion

The guardkeeper runs before the event is inserted. It rejects missing job references, invalid state transitions, missing evidence on acceptance, missing required context before running, child jobs attempting to complete parent/root scope, broken appearance references, and attempts to promote candidates without acceptance.

The first guardkeeper is deterministic code, not model self-discipline.

### Keep object content outside the core database when needed

Small summaries and metadata live in SQLite. Submitted files are copied into `.金箍/运行态/果库/<appearance_id>/`, and the database stores their path, checksum, summary, type, version, and source job.

The object store is local runtime state and must not be committed.

### CLI is a thin adapter over runtime services

The CLI will expose enough commands to initialize and manually exercise the kernel:

- `init`
- `root create`
- `job ready`
- `job run`
- `candidate submit`
- `evidence submit`
- `accept`
- `reject`
- `status`
- `events`

The CLI must not bypass repository, state machine, or guardkeeper logic.

## Risks / Trade-offs

- Minimal schema may feel too small for later semantics -> Keep semantic expansion in `appearance_type`, JSON metadata, and event payloads; only split tables when query, permission, migration, or concurrency pressure appears.
- Event replay is not fully implemented in stage one -> Keep events append-only and hash-chained now, and update query fields transactionally; full replay can be added without changing the external contract.
- CLI-first experience is not a product UI -> This is intentional for stage one; the goal is proving root-law enforcement before user-facing workflow.
- JSON fields can hide schema drift -> Keep payloads small, validate required fields in service methods, and cover expected payloads with tests.
- Unicode runtime path may expose platform issues -> Centralize path creation in the runtime path resolver and test initialization in temporary directories.

## Migration Plan

This is the first runtime implementation, so no existing runtime data needs migration.

Implementation steps:

1. Add project packaging, ignore rules, and Python package structure.
2. Add SQLite schema creation and runtime path initialization.
3. Add repository, object store, state machine, and guardkeeper services.
4. Add CLI commands for the manual single-root-job workflow.
5. Add automated tests for happy path and hard failure cases.

Rollback is file-level: remove the new package, tests, OpenSpec change, and ignore additions before any runtime data is relied on.

## Open Questions

- Whether future archived specs should live only under OpenSpec or also be mirrored into `truth/` after implementation.
- Whether accepted candidate appearances should change state in place or produce a separate accepted appearance in later stages. Stage one uses in-place state transition with event evidence.
