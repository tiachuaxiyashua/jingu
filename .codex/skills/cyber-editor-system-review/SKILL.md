---
name: cyber-editor-system-review
description: System-level review of Cyber Editor product scope, feature hierarchy, UI information architecture, four-layer architecture, orchestration semantics, AI harness/context engineering, contracts, safety, cohesion/coupling, tests, and traceability. Use when auditing whether docs and code are complete, aligned, implementation-ready, or safe to extend.
---

# Cyber Editor System Review

Use this skill when the task is to review Cyber Editor at the system level rather than only one module.

Apply it for questions such as:

- "Can this project safely continue implementation?"
- "Do the docs and code still align?"
- "What review dimensions are still missing?"
- "Is the current system complete enough for another team or AI to reproduce?"
- "Where are the highest-risk product, architecture, or runtime gaps?"

Do not use this as a generic style review. Focus on system truth: product boundary, object model, runtime ownership, failure handling, and proof.

## Source of Truth Order

Read only what is needed, but keep this precedence:

1. `docs/README.md` for the documentation entry and reading order
2. `docs/01-需求与PRD/` for product definition, journeys, scope, and priority
3. `docs/02-产品设计/` for page hierarchy, interaction rules, and reachable UI
4. `docs/03-架构实现/` for architecture, runtime, data contracts, security, and owner boundaries
5. `docs/04-测试验收/` for gates, journey tests, packaged-app proof, and traceability
6. `docs/05-项目规则/` for AI collaboration, change flow, and completion definition
7. `src/` for runtime reality
8. `tests/` for enforcement evidence

Treat:

- `docs/` as intended system behavior
- `src/` as actual implementation
- `tests/` as proof

If the three disagree, say which layer is ahead and which layers are missing.

## Core Rule

A capability is not system-complete unless all four exist:

1. requirement and feature ownership in docs
2. concrete owner in code
3. observable user path or internal trigger
4. test or runtime proof

If one is missing, treat it as a system gap, not a polish gap.

## Review Workflow

### 1. Frame the review

State:

- review scope
- primary user path
- primary system objects
- irreversible failure cost
- completion bar being judged

### 2. Build the system boundary map

For the target area, identify:

- page or UI owner
- renderer state owner
- IPC owner
- main-process owner
- persistence owner
- recovery owner
- governance owner
- test owner

Write the main path as:

`trigger -> renderer -> IPC -> main service -> persistence/runtime -> observable result`

If more than one layer appears to own the same truth, flag it.

### 3. Run the full-dimension sweep

Use `references/checklist.md`.

Do not stop at architecture only. This skill must check:

- product boundary
- feature completeness
- UI information architecture
- orchestration semantics
- harness/context engineering
- contracts
- recovery
- governance
- cohesion/coupling
- test coverage
- traceability

### 4. Verify doc-code-test parity

For each major finding, collect:

- at least one doc reference
- at least one code reference or explicit missing-code fact
- at least one test reference or missing-test fact

No vague findings. No "probably". Mark inferences explicitly.

### 5. Decide severity

Use:

- `critical`: the system can materially violate product intent, corrupt state, bypass trust/governance, or cause two implementers to build incompatible systems
- `high`: a major capability is only partially real, a boundary is unstable, or a promised path lacks recovery/proof
- `medium`: direction is correct but enforcement is weak, drift is likely, or important unhappy paths are under-specified
- `low`: not a blocker today, but structurally likely to decay

### 6. Produce a system decision

End with explicit judgments:

1. whether the docs are sufficient for product alignment
2. whether the implementation boundaries are healthy enough for extension
3. whether the system is ready for broad feature development
4. what must be fixed first

## Review Heuristics

Common Cyber Editor system failures:

- docs define a platform the code does not actually execute
- feature list marks critical M/S/A items unfinished while architecture claims readiness
- renderer shells retain too much domain logic
- IPC becomes a second business layer
- orchestration UI exists but execution semantics are partial
- harness/context design exists but indexing, provenance, or budget controls are not real
- approvals, trust, or side-effect rules exist as metadata only
- tests prove happy paths while system promises rely on missing failure-path proofs
- traceability matrices exist but do not close to code and tests

## Output Contract

Output in this order:

1. findings sorted by severity
2. open questions or assumptions
3. overall assessment
4. immediate next actions

Use `references/findings-template.md`.

## Do Not Do

- do not confuse a design placeholder with an implemented capability
- do not mark a capability complete because a UI shell exists
- do not ignore feature inventory status when it contradicts summary claims
- do not accept missing test proof for destructive, privileged, or long-running paths
- do not blur product completeness, architecture completeness, and code completeness into one claim
