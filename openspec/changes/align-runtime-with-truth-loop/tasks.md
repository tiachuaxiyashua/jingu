## 1. Governance Rules

- [x] 1.1 Add truth-to-code invariant rules to `AGENTS.md`.
- [x] 1.2 Add proxy fallback guidance that supports `7897` and `7890` without runtime hardcoding.

## 2. Runtime Loop Semantics

- [x] 2.1 Add structured advancement outcome helpers for `completed`, `paused`, and `blocked`.
- [x] 2.2 Refactor frontier dispatch to classify blocked jobs separately from rejected result packages.
- [x] 2.3 Refactor advancement to continue while new frontier work appears and to pause when budgets are exhausted with active work remaining.
- [x] 2.4 Make sandbox runner record paused/blocked outcomes honestly in output and logs.

## 3. Logging And Visibility

- [x] 3.1 Add readable log labels for loop outcome, remaining frontier, and blocked frontier fields.
- [x] 3.2 Ensure job-tree mirror snapshots expose active frontier after pause or block.

## 4. Validation

- [x] 4.1 Add unit tests for budget exhaustion producing `paused` with remaining frontier.
- [x] 4.2 Add unit tests for context-gap jobs producing `blocked` instead of generic package rejection.
- [x] 4.3 Add unit tests showing parent integration follow-up jobs re-enter advancement.
- [x] 4.4 Run OpenSpec validation, Python tests, compile checks, viewer validation, and hardcoding scan.
