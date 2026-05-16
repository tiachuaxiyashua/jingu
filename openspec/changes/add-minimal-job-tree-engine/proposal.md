## Why

The current runtime proves a single-job candidate and evidence loop, but it cannot yet preserve a real job tree. The truth source says step 4 is a minimum true tree: root job, parent job, child job, completion ownership, structured result packages, and parent re-evaluation.

This change makes the runtime capable of functional validation for method-driven work such as Neidan Method without hardcoding any specific method into the engine.

## What Changes

- Add guarded child-job proposal and registration so actors can propose decomposition, while code checks whether the split is useful and non-decorative.
- Add a tree projection that shows root, parent, children, active frontier, and parent re-evaluation data.
- Add structured result package submission for child jobs, stored as candidate result plus evidence without auto-accepting.
- Add CLI commands to manually drive the minimal job tree workflow.
- Add tests that prove child jobs cannot claim parent completion, split proposals must satisfy guard fields, and a method-validation job can be represented as a real tree.
- Keep method identity, validation criteria, and example content as user-provided data, not engine-owned hardcoded truth.

## Capabilities

### New Capabilities

- `minimal-job-tree-engine`: Create and inspect a real parent-child job tree, guard child-job proposals, submit structured child result packages, and expose a parent re-evaluation view.

### Modified Capabilities

None.

## Impact

- Affected code: `jingu/runtime/*`, `jingu/cli.py`, tests under `tests/`.
- Affected specs: new `minimal-job-tree-engine` spec.
- Dependencies: no new runtime dependency.
- Hardcoding boundary: the engine must not encode Neidan Method steps, sample wishes, provider details, or business examples; those are supplied by the user, tests, or external data.
