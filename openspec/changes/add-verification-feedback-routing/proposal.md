## Why

The sandbox can already repair mechanical verification failures, but high-value, directional, and semantic acceptance failures still do not reliably surface in the same run flow, especially in `ai run`. We need a verification-aware acceptance routing step so the AI in the acceptance role can either push a candidate back to the executor as a repair job or expose the issue as a feedback/decision job instead of leaving it buried in candidate text or logs.

## What Changes

- Add a verification-aware AI acceptance routing step after candidate verification and any bounded deterministic repair loop.
- Feed the router with the final candidate, deterministic verification report, repair summary, and task context so it can judge semantic repair needs, directional issues, or high-value decision points.
- Create an execution repair child job when the acceptance router judges that the issue is repairable without human value裁决.
- Create a feedback child job when the AI judges that the candidate still needs directional correction or a high-value decision point.
- Record the routing judgment, evidence, and skip reasons in readable logs, JSONL logs, and job-tree snapshots.
- Reuse the same routing behavior in `ai run` and `ai chat` instead of keeping chat-only judgment logic.

## Capabilities

### New Capabilities

- `verification-feedback-routing`: After verification and repair, the system asks an AI acceptance router whether the candidate should continue, be pushed back to an executor repair job, or surface as a high-value/directional feedback job.

### Modified Capabilities

- `ai-sandbox-chat`: Chat turn feedback judgment now consumes verification and repair evidence, not only the raw assistant response, and may create repair or feedback jobs from that richer context.

## Impact

- Affects `jingu/sandbox/runner.py`, `jingu/sandbox/flow.py`, `jingu/cli.py`, and AI sandbox tests.
- Reuses existing feedback-job concepts and job-tree persistence; no new external provider is required.
- Improves observability for acceptance-role打回 and high-value rejection paths without changing the no-auto-accept/no-auto-reject rule.
