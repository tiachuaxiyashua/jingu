## Why

Jingu can now create candidate verification jobs, but a failed verification still stops at evidence and depends on an external operator to decide the next repair run. This leaves the system short of the truth-source expectation that work contracts produce visible child jobs, evidence, repair paths, and only escalate high-value or direction-changing questions to the human.

## What Changes

- Add a generic verification repair loop after candidate verification fails.
- Create repair child jobs for deterministic, repairable verification failures instead of silently retrying inside the parent job.
- Ask the configured AI provider to produce a revised candidate from the original task, prior candidate, and verification evidence.
- Re-run candidate verification on each repair candidate and record the lineage in the job tree, readable log, structured event log, and summary.
- Create a feedback-decision child job when the system cannot repair within the configured attempt limit or the verification result is not safely repairable.
- Keep parent candidates isolated: repair candidates and verification evidence are recorded as candidates/evidence, not as automatic accept/reject decisions.
- Add configurable repair attempt limits for `ai run` and `ai chat`.

## Capabilities

### New Capabilities

- `candidate-repair-loop`: Defines how failed candidate verification creates repair jobs, revised candidates, repeated verification, and feedback-decision jobs without hardcoded domain behavior.

### Modified Capabilities

- `candidate-verification-jobs`: Verification results now feed a bounded repair/feedback job chain instead of ending the flow when deterministic checks fail.

## Impact

- Affects `jingu/sandbox/runner.py`, `jingu/sandbox/flow.py`, `jingu/cli.py`, and AI sandbox tests.
- Adds no new provider dependency and no provider/model hardcoding.
- Adds user-visible CLI parameters for repair attempt bounds.
- Extends logs and summaries with repair lineage and feedback-decision evidence.
