## 1. OpenSpec And Flow Contract

- [x] 1.1 Create proposal, design, specs, and tasks for candidate verification jobs.
- [x] 1.2 Add verification flow event constants, readable labels, and fields.

## 2. Deterministic Verification Tool

- [x] 2.1 Implement a generic text verifier that extracts marker-delimited regions and CJK length ranges from task text.
- [x] 2.2 Return structured pass/fail/unsupported evidence with counts, applied checks, and gaps.

## 3. Sandbox Integration

- [x] 3.1 Create verification child jobs after candidate submission in one-shot AI runs.
- [x] 3.2 Create verification child jobs after candidate submission in interactive AI chat turns.
- [x] 3.3 Submit verification report evidence to the child job and compact verification evidence to the parent job without auto-accepting.
- [x] 3.4 Log verification execution, result, evidence回流, and job-tree snapshots.

## 4. Verification

- [x] 4.1 Add tests for passing and failing CJK length checks, marker extraction, verification child jobs, parent evidence回流, and logs.
- [x] 4.2 Run OpenSpec validation, unit tests, compile check, and hardcoding scan.
