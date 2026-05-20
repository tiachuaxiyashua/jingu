## 1. Repair Loop Runtime

- [x] 1.1 Add generic repairability classification and repair prompt construction from verification reports.
- [x] 1.2 Add bounded repair-loop orchestration that creates repair child jobs, records provider calls, submits repair candidates, and re-runs verification.
- [x] 1.3 Add unresolved verification routing that creates feedback-decision child jobs without auto-accepting or auto-rejecting candidates.

## 2. CLI And Logs

- [x] 2.1 Add configurable maximum repair attempts to `ai run` and `ai chat`.
- [x] 2.2 Extend structured and readable logs with repair loop events, repair lineage, and unresolved feedback-decision evidence.
- [x] 2.3 Include repair outcome summaries in AI sandbox run/chat output records.

## 3. Verification

- [x] 3.1 Add tests for a failed candidate repaired into a passing candidate.
- [x] 3.2 Add tests for exhausted repair attempts producing a feedback-decision job.
- [x] 3.3 Run OpenSpec validation, unit tests, compile checks, and the hardcoding scanner.
