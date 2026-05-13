# Architecture Review Checklist

Use this checklist after mapping the real path `trigger -> renderer -> IPC -> main -> persistence/runtime -> observable result`.

## 1. Boundary Integrity

- Does each layer have one coherent responsibility?
- Is the renderer only coordinating UI, or is it also carrying domain truth?
- Does any service look like a god-service?
- Does one file own multiple unrelated domains?
- Would moving one feature require touching too many unrelated places?

## 2. Source-of-Truth Uniqueness

- For each key object, is there exactly one authoritative owner?
- Are draft state and persisted state clearly separated?
- Are runtime records, evidence, and approval states persisted in one authoritative place?
- Do docs describe one storage target instead of "A or B"?

## 3. Execution-Path Closure

- Is the documented rule on the real execution path?
- Is trust checking actually invoked before install?
- Is side-effect approval actually invoked before execution?
- Is recovery actually reachable from failure?
- Is a documented gate enforced by runtime, or only described in docs?

## 4. Lifecycle Completeness

- Are create/read/update/delete flows all defined?
- Are import, repair, update, rollback, and delete paths covered?
- Does the module define versioning or upgrade behavior?
- Can the system survive restarts mid-operation?

## 5. Failure and Recovery

- What are the top failure points?
- What does the user see?
- What is persisted when failure happens?
- Can the system retry safely?
- Is there a damage boundary?
- Is there a repair or resume entry?

## 6. Scalability, Context, Durability

- For long conversations or long flows, how is context budget controlled?
- How are summaries, checkpoints, and traces persisted?
- Is there concurrency control or backpressure?
- Can multiple sessions, windows, or runs drift each other?

## 7. Docs-Code-Test Parity

- Is the design intent mirrored in code?
- Is the behavior enforced by test or runtime evidence?
- Are "未完成" items actually the missing architecture-critical pieces?
- Are there design objects with no implementation objects?

## 8. Migration Viability

- Is there a path from current implementation to target architecture?
- Can the refactor be staged without breaking user workflows?
- Are anti-corruption boundaries identified?
- Is there a stop-the-world dependency hidden in the design?

## Decision Rule

If any of the following are true, the architecture is not ready for broad feature expansion:

- source of truth is ambiguous
- trust/approval/recovery is defined but not on the runtime path
- a shell component or service has collapsed too many domains together
- docs require a capability but code only has a helper or placeholder
- tests prove success paths only and do not pin invariants
