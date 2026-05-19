## Why

The AI sandbox can load methods and submit candidate results, but recent story generation showed that model self-review and external Codex shell checks are not Jingu verification. Deterministic acceptance checks such as text length and required output markers must run inside Jingu as an independent verification job that produces evidence and can drive repair.

## What Changes

- Add a minimal candidate verification job after AI candidate submission in one-shot runs and chat turns.
- Add a deterministic text verifier that extracts verifiable text constraints from the user task and candidate output.
- Verify marker-delimited deliverables, CJK character counts, total character counts, and obvious incomplete-output signals when those constraints are present.
- Store verification results as evidence on a child verification job and also on the parent job so the parent has hard evidence before completion decisions.
- Log verification job creation, tool execution, pass/fail result, evidence submission, and job-tree snapshots in JSONL and readable Markdown logs.
- Keep AI self-review as weak evidence only; deterministic verifier output becomes the hard evidence for supported checks.

## Capabilities

### New Capabilities

- `candidate-verification-jobs`: Independent tool-backed verification jobs for AI sandbox candidate results, with evidence回流 to the parent job.

### Modified Capabilities

None. The archived OpenSpec spec set is currently empty.

## Impact

- Adds deterministic verifier code under the sandbox/runtime area.
- Extends `AiSandboxRunner` and `AiSandboxChatSession` to create verification child jobs after candidate submission.
- Extends flow events and readable logs with verification-specific events and fields.
- Adds tests for pass/fail verification, evidence回流, job-tree visibility, and no reliance on AI self-review for deterministic checks.
