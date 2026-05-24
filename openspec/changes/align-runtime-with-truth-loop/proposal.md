## Why

The current AI sandbox can record a job tree, but the actual control flow is still a fixed runner pipeline. This conflicts with the truth source because job results, evidence, gaps, repairs, and follow-up work do not all re-enter one durable Xiang-Ye loop as new conditions for continued work.

## What Changes

- Add repository-wide governance rules that require implementation work to map truth-source principles into code invariants before coding.
- Require future runtime/orchestration changes to prove that jobs remain the only state-changing work contract, and that runners/CLI/sandbox code are only entry points or mirrors.
- Refactor the sandbox execution path so root generation, split registration, frontier dispatch, child review, parent integration, verification, repair, and feedback jobs are advanced through one resumable runtime cycle instead of a one-shot pipeline.
- Convert advancement limits from "finish the run" semantics into "pause with remaining runnable work" semantics.
- Record pause/resume evidence and active frontier state so any-size tasks can continue through repeated minimal-loop executions.
- Treat proxy port selection as environment/configuration-owned operational truth; support both the current `7897` and legacy `7890` GitHub proxy ports without hardcoding a single durable assumption into reusable runtime logic.

## Capabilities

### New Capabilities

- `truth-governance-rules`: Repository rules that stop code from drifting away from `truth/` by requiring truth-to-code invariants, no symptom-driven component growth, and verification evidence.
- `truth-aligned-runtime-loop`: A durable job-loop runtime capability where every candidate, evidence item, gap, repair, feedback request, and follow-up job re-enters the same job advancement cycle.

### Modified Capabilities

None.

## Impact

- `AGENTS.md` global implementation rules.
- `jingu/sandbox/runner.py` orchestration flow and runtime options semantics.
- Runtime flow event labels and log evidence for pause/resume and active frontier state.
- Tests that currently assert fixed one-shot pipeline behavior may need to be updated toward loop invariants.
- GitHub synchronization commands should use configurable proxy fallback when the local environment exposes multiple supported ports.
