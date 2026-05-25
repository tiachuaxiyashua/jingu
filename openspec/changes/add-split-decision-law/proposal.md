## Why

Jingu's job-tree growth can look too shallow when split requests are conservative, but adding more standalone "engines" or "detectors" would violate the project's simple-rule direction. The split decision should be a law enforced by the existing job-tree path, not another component.

## What Changes

- Add an explicit split decision law to the truth source and runtime split-registration path.
- Require AI split proposals to include the five split-law judgments.
- Require manual child-job creation to submit the five split-law judgments explicitly, instead of letting code derive a default law.
- Record the split law in JSONL and readable logs so the user can inspect why a child job was or was not allowed.
- Reject decorative child jobs that have no execution, acceptance, capability, or high-value/risk ground, and reject child jobs that cannot produce an independent parent-consumable result package.

## Capabilities

### New Capabilities

- `split-decision-law`: Enforces split decisions as a law in the existing tree service and AI proposal flow.

## Impact

- Truth source split mechanism wording.
- `jingu/runtime/tree.py` child-job proposal guardrails.
- `jingu/sandbox/runner.py` AI split proposal contract and normalization.
- Flow/viewer labels for split-law visibility.
- Unit tests for law acceptance and rejection.
