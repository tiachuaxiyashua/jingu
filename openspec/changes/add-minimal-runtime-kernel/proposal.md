## Why

Jingu's current truth source defines the 相业 architecture, but the repository has no executable runtime that can enforce its root laws. This change builds the first runnable kernel so the architecture can be tested as code before adding models, UI, or complex orchestration.

## What Changes

- Add a minimal local runtime backed by SQLite and a filesystem object store.
- Add the first persistent carriers required by the truth source: jobs, appearances, and append-only events.
- Add a guardrail layer that rejects illegal state transitions before they enter the event ledger.
- Add a small command-line interface for initializing the runtime and manually driving a single-root-job workflow.
- Add automated tests proving the first-stage hard failures are blocked.
- Exclude local runtime state from version control.

## Capabilities

### New Capabilities

- `minimal-runtime-kernel`: Local 相业 runtime kernel covering job creation, appearance registration, append-only events, state transitions, candidate isolation, evidence-backed acceptance, and root-law guardrails.

### Modified Capabilities

None.

## Impact

- Adds Python runtime code under `jingu/`.
- Adds tests under `tests/`.
- Adds project packaging and test configuration.
- Adds OpenSpec artifacts under `openspec/`.
- Updates ignore rules so `.金箍/运行态/` and other local runtime artifacts are not committed.
