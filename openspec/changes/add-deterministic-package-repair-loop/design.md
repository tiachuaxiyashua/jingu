## Context

The child dispatch path already has two kinds of rejection. Independent AI package review can request repair and the runtime creates a repair job. Earlier deterministic failures, including JSON/package parsing, schema validation, and tree-service acceptance rules, currently record rejection evidence and block the child immediately.

The truth source requires rejection to become a control signal: failure must enter repair, rollback,補证, arbitration, or废弃 instead of ending as a comment. For deterministic package failures the correct minimal loop is repair first, block only when the configured repair budget is exhausted.

## Goals / Non-Goals

**Goals:**

- Convert deterministic child-package failures into repair jobs when repair attempts remain.
- Preserve candidate isolation: the rejected package is never accepted, and a repaired package must pass the same deterministic and independent review path.
- Record failure reason, original raw candidate, repair prompt, repair response, repaired package submission, and final accept/reject path in logs.
- Keep repair generic across task domains and quantitative/non-quantitative jobs.
- Respect existing repair-attempt budget and existing flow event vocabulary where possible.

**Non-Goals:**

- Add domain-specific fallback logic for novels, chapters, word counts, platforms, or provider behavior.
- Let the repairing actor bypass deterministic guardrails or independent review.
- Change parent integration, delivery ledger, or split decision law semantics beyond routing rejected child packages back into repair.

## Decisions

### Treat deterministic guardrail rejection as repairable evidence

Package parse, schema, and tree-service submission errors are wrapped as a deterministic failure record. If the child has remaining package-repair attempts, the runtime creates a repair child job that targets the original child package and includes the failure evidence plus the original raw candidate.

This is preferred to immediately blocking because the truth loop says refusal and rejection should drive state-machine回流. It is also preferred to silently retrying the same child job because the repair job has explicit cause, target, evidence, and budget.

### Reuse the package repair channel but keep failure source visible

The repair job uses the same package-repair event family as AI-review repair, with payload fields identifying the source as deterministic guardrail failure. Logs therefore show one repair mechanism while still distinguishing why repair was requested.

This is preferred to inventing a new permanent “deterministic repair器”; the behavior is a律/状态机 consequence, not a separate architectural object.

### Validate repaired output through the original path

The repaired response is parsed and submitted as the original child job's result package. If it passes deterministic checks, it proceeds into the existing independent child-package review loop. If it fails again or the budget is exhausted, the original child is blocked with the latest failure evidence.

This preserves the three-power separation: repair produces a candidate, the deterministic guardrail controls state mutation, and the reviewer/parent owns acceptance within scope.

## Risks / Trade-offs

- [Risk] A repair prompt may repeat a malformed package. -> Mitigation: count attempts, preserve rejection evidence, and block visibly after the configured limit.
- [Risk] Logs may become noisy for repeated failures. -> Mitigation: keep repair events structured and tied to the original child job and repair attempt index.
- [Risk] Reusing AI-review repair events may blur source semantics. -> Mitigation: include explicit `failure_source` / `repair_reason` fields in machine payloads and Chinese readable summaries.

## Migration Plan

1. Add the deterministic repair helper to the child dispatch path.
2. Add regression tests for successful deterministic repair and exhausted deterministic repair.
3. Run OpenSpec validation, compile, full tests, and hardcoding scan.
4. Rollback consists of reverting this change; no persisted runtime-state migration is required.

## Open Questions

- Future law versions may choose different repair actors or escalation policies based on failure class. This change keeps one generic repair path with a bounded attempt budget.
