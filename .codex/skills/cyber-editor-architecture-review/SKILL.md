---
name: cyber-editor-architecture-review
description: Use when reviewing Cyber Editor architecture holes, boundary drift, design-doc feasibility, or code-vs-doc mismatches before implementation.
---

# Cyber Editor Architecture Review

Use this skill when the user asks any of the following:

- "Does the architecture still have holes?"
- "Is it safe to start implementation now?"
- "Review the design docs and current code for architecture issues."
- "Check whether the docs can be implemented without drift."
- "Check whether implementation has drifted from the design."

This is not a general code review skill. It is for architecture-level failure modes: wrong boundaries, wrong ownership, missing durability, missing recovery, and design promises that are not on the real execution path.

## Source of Truth

Read in this order unless the task is tightly scoped:

1. the docs entry at `docs/README.md`
2. the product requirements under `docs/01-需求与PRD/`
3. the product/UI decisions under `docs/02-产品设计/`
4. the architecture and owner docs under `docs/03-架构实现/`
5. the acceptance and test gates under `docs/04-测试验收/`
6. the project rules under `docs/05-项目规则/`
7. Current code paths in `src/`
8. Current tests in `tests/`

Treat:

- `docs/` as the architectural baseline
- `src/` as runtime reality
- `tests/` as proof of enforcement

If docs and code disagree, every finding must say which side is ahead and which side is missing.

## Core Rule

Do not accept a capability as "architecturally present" unless all three exist:

1. A clear owner in design docs
2. A concrete owner in code
3. A proof path in tests or explicit runtime evidence

If one layer is missing, treat it as an architecture gap, not a polish issue.

## Review Workflow

### Step 1. Frame the review

Define:

- review scope
- target user path
- target object model
- critical failure cost

At minimum answer:

- What must remain stable?
- What can cause irreversible damage?
- What would make later implementation diverge?

### Step 2. Draw the real boundary map

For the target module, identify:

- UI owner
- state owner
- orchestration owner
- persistence owner
- recovery owner
- governance owner
- external side-effect owner

Write the current path as:

`trigger -> renderer -> IPC -> main service -> persistence/runtime -> observable result`

If two different layers appear to own the same truth, flag it.

### Step 3. Run the eight-axis check

Use the checklist in `references/checklist.md`.

The eight axes are:

1. Boundary integrity
2. Authoritative source-of-truth uniqueness
3. Execution-path closure
4. Lifecycle completeness
5. Failure and recovery completeness
6. Scalability, context, and durability
7. Docs-code-test parity
8. Migration viability

### Step 4. Collect hard evidence

Every finding must cite:

- at least one design-doc file and line or section
- at least one code file and line or missing-code fact
- when relevant, one test or lack-of-test fact

No vague findings. No "probably". If a claim is inferential, say so explicitly.

### Step 5. Score severity

Use these rules:

- `critical`:
  - can cause wrong product behavior despite docs being "correct"
  - can bypass governance, trust, approval, or persistence
  - makes ownership ambiguous enough that two programmers could build different systems
  - can cause unrecoverable corruption, silent drift, or fake completion
- `high`:
  - module boundary is wrong but damage is still containable
  - runtime path exists but recovery, migration, or observability is missing
  - docs promise a system that current code only partially represents
- `medium`:
  - architecture intent is visible but enforcement is weak
  - missing invariants or tests can allow future drift
- `low`:
  - not a current blocker, but likely to rot into a blocker later

### Step 6. Produce a decision

End with four decisions:

1. `Can the docs still guide implementation?`
2. `Can the codebase still be extended on the current boundaries?`
3. `Is broad continued development safe right now?`
4. `What are the top three architecture issues to fix first?`

## What To Look For

Common architecture smells in Cyber Editor:

- `App.tsx` or a page shell owning too many unrelated domains
- one main-process service mixing project IO, runtime orchestration, template authoring, and governance
- docs saying "directory or store" / "for now here, later there" without one authoritative target
- governance objects defined in docs but not instantiated on the real call chain
- recovery promises that only exist as docs, not persisted checkpoints or error records
- trust / approval / side-effect rules that are metadata only, not execution gates
- tests proving happy paths but not architectural invariants
- features marked "partial" where the missing half is actually the architecture-critical half

## Output Contract

The review output must contain, in this order:

1. Findings first, sorted by severity
2. Open questions or assumptions
3. Overall decision
4. Immediate next actions

Use the structure in `references/findings-template.md`.

## Do Not Do

- Do not downgrade an architecture issue into a UI issue
- Do not say "already considered in docs" if the runtime path is absent
- Do not confuse a helper function with a full architecture capability
- Do not mark a design as implementation-ready if persistence, recovery, or ownership is still ambiguous
- Do not accept "future store" or "later abstract out" as a finished design
