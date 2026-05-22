## Why

Jingu already records job-tree growth, candidate isolation, verification, repair, feedback, and sandbox teardown in JSONL logs, but the user still has to read long event files to understand how a run evolved. A local visual replay page will make the event ledger inspectable without changing runtime truth or adding a server.

## What Changes

- Add a browser-based job-tree log viewer that loads a selected JSONL log file from the user's machine.
- Reconstruct job nodes, parent-child links, state changes, evidence/candidate attachments, provider calls, and run closure from append-only events.
- Provide step-by-step replay controls so the user can click through the exact sequence of job-tree growth and closed-loop events.
- Show the current event, timeline, visible job tree, selected job details, and loop summary in Chinese.
- Keep the viewer read-only: it must not mutate logs, create jobs, call AI providers, or become a parallel truth source.

## Capabilities

### New Capabilities
- `job-tree-log-viewer`: Load Jingu JSONL flow logs in a static web page and replay job-tree growth and closure events step by step.

### Modified Capabilities
- None.

## Impact

- Adds a static HTML/CSS/JavaScript tool under a repo-owned viewer path.
- Adds OpenSpec requirements for local log loading, event replay, graph projection, and human-readable Chinese UI.
- Does not change runtime event generation, AI provider behavior, secrets, `.env` files, or log persistence.
