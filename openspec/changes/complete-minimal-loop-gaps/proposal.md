## Why

The current Jingu loop can produce child packages, review them, and integrate accepted material, but the remaining gaps still leave too much responsibility in a one-pass runtime path and in log interpretation. This change completes a minimal verifiable loop across repair, integration-as-job, bounded continuation, method-step visibility, human decision return, evidence hardness, trace debugging, lineage, learning candidates, and runtime configuration.

## What Changes

- Add integration and repair as first-class job-visible work units instead of hidden helper-only actions.
- Add bounded continuous advancement so one run can keep dispatching frontier work until a configured stopping condition is reached.
- Add method-step projection from bound method fragments so法调用 can visibly produce candidate sub-work without hardcoding a specific法.
- Add human decision request and return recording as stateful evidence that can flow back to the source job.
- Add evidence hardness metadata and expose weak evidence risks in logs and viewer projection.
- Add stronger candidate lineage metadata linking parent candidates to consumed child packages and upstream candidate/evidence refs.
- Add method learning candidates as versioned runtime appearances, kept isolated until accepted by later work.
- Move loop limits and strategy toggles into a runtime options object and CLI flags.
- Expand the trace viewer with filtering/search and clickable appearance-focused raw traces.

## Capabilities

### New Capabilities
- `minimal-loop-gap-closure`: Covers the runtime behavior needed to close the ten identified minimal-loop gaps without claiming mature product completeness.
- `trace-debugger-controls`: Covers the viewer behavior needed to inspect, filter, search, and follow the precise inputs/outputs/evidence/state changes of each step.

### Modified Capabilities
- None.

## Impact

- Runtime orchestration in `jingu/sandbox/runner.py`, flow labels in `jingu/sandbox/flow.py`, and runtime appearance metadata in `jingu/runtime/service.py`.
- CLI option parsing in `jingu/cli.py`.
- Job tree log viewer files under `tools/job-tree-log-viewer/` and validation script `scripts/validate_job_tree_viewer.js`.
- Unit tests under `tests/`.
