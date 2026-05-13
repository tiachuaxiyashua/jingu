---
name: defensive-programming-review
description: Review or harden Cyber Editor defensive programming, failure handling, cohesion, coupling, and hidden test blind spots. Use when auditing robustness before implementation, after a defect review, or before marking a risky runtime path complete.
---

# Defensive Programming Review

Use this skill for Cyber Editor when the task is to do one or more of the following:

- find hidden failure paths behind a working happy path
- check whether a destructive or privileged action is safely gated
- verify malformed input, partial write, timeout, and retry behavior
- assess whether a module is drifting toward low cohesion or high coupling
- decide whether current tests would catch real regressions
- turn review findings into concrete hardening changes

This is not a generic style review. Focus on runtime safety, trust boundaries, recovery, and proof.

## Inputs To Read

Read only the minimum needed, in this order:

1. the target requirement or design doc in `docs/`
2. the real runtime path in `src/`
3. the proof path in `tests/`

Treat:

- `docs/` as intended behavior
- `src/` as runtime reality
- `tests/` as enforcement evidence

If they disagree, say which layer is ahead and which layer is missing.

## Review Workflow

### 1. Frame the risky path

State:

- the user-visible action
- the exact runtime entry point
- the irreversible or expensive failure mode
- the trust boundary crossed

Write the path as:

`trigger -> renderer -> IPC -> main service -> persistence/runtime -> observable result`

### 2. Run the defensive checklist

Use `references/checklist.md`.

Do not stop at the first bug. Scan all checklist axes for the same path.

### 3. Check cohesion and coupling

For the target code, answer:

- what is the single owner of truth?
- which module owns validation?
- which module owns persistence?
- which module owns recovery?
- which module owns user-facing error mapping?

Flag:

- one file owning unrelated domains
- renderer code deciding trust or persistence rules
- service methods mixing validation, mutation, side effects, and formatting
- duplicate schema or error semantics in multiple layers

### 4. Check the unhappy path

For each risky operation, explicitly look for:

- malformed input
- missing file or missing field
- expired or replayed approval
- partial write or interrupted copy
- retry and idempotency behavior
- stale state or cross-request leakage
- rollback or recovery behavior

If a path is destructive, verify the failure path before trusting the success path.

### 5. Check the test trap

Ask:

- do tests only prove the happy path?
- is there a negative-path test for each high-risk guard?
- does any test assert the wrong thing indirectly?
- could structural rot grow while current tests still pass?

Absence of a test on a risky path is itself a finding.

### 6. Produce repair-ready findings

Use `references/findings-template.md`.

Each finding must include:

- severity
- failure scenario
- why the current behavior is unsafe
- exact file references
- missing or weak tests
- the concrete hardening direction

## Hardening Rules

Prefer these repair patterns:

- bind approvals, tokens, and permissions to a concrete scope
- enforce expiry on time-bound authorization
- convert destructive restore operations to staged or rollback-safe flows
- normalize malformed external input into structured errors
- keep one owner for schema validation and one owner for side-effect execution
- add targeted negative-path tests before broad refactors

Do not hide risk by adding comments alone.

## Output Contract

Output in this order:

1. findings sorted by severity
2. open questions or assumptions
3. recommended hardening change scope
4. validation plan

If asked to fix the issues, convert the top findings into a bounded change with tasks that map one-to-one to code and tests.
