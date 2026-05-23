## 1. Runtime Options And Metadata

- [x] 1.1 Add explicit sandbox runtime options for advancement waves, integration repair attempts, method-step registration, and existing loop limits.
- [x] 1.2 Add CLI flags and process-log fields for the runtime options.
- [x] 1.3 Extend evidence and candidate submissions with metadata for hardness, kind, lineage, and candidate-only learning records.

## 2. Parent Integration Closure

- [x] 2.1 Represent parent integration as an observable child job linked to the parent.
- [x] 2.2 Add integration repair job creation, repair prompt, repair response parsing, and non-mutating failure handling.
- [x] 2.3 Add candidate lineage metadata for integration candidates.

## 3. Continuous Advancement And Method Steps

- [x] 3.1 Add bounded advancement waves that repeatedly dispatch active frontier work until no progress, no frontier, or wave limit.
- [x] 3.2 Register method-step candidates from bound method fragments as traceable child jobs or skip events.
- [x] 3.3 Ensure child/root completion authority remains separate across all new loop paths.

## 4. Human Decision And Learning Candidates

- [x] 4.1 Add human decision request/return events and runtime helper for recording returned human decisions as evidence.
- [x] 4.2 Record method self-review update observations as candidate method-learning appearances without changing method files.
- [x] 4.3 Attach evidence hardness and weak-evidence risk fields to relevant logs.

## 5. Trace Debugger

- [x] 5.1 Add viewer controls for search, phase/type/job filters, and appearance id filtering.
- [x] 5.2 Extend viewer projection for integration repair, human decision, evidence hardness, lineage, and learning-candidate milestones.
- [x] 5.3 Update viewer validation to assert filters and new milestones.

## 6. Validation

- [x] 6.1 Add Python tests for integration repair, continuous advancement, metadata lineage, human decision return, and method learning candidates.
- [x] 6.2 Add viewer projection tests for filters, appearance trace following, repair milestones, and evidence hardness.
- [x] 6.3 Run OpenSpec validation, Python tests, viewer validation, compile checks, hardcoding scan, and manual UTF-8 log verification.
