## Why

A real long-delivery run proved that deterministic child-package guardrails can correctly reject false or malformed result packages, but the runtime currently stops at a visible block instead of turning the rejection into a repairable `业`. This leaves the truth loop incomplete: rejection evidence exists, yet failure does not flow back to an execution/repair actor while budget remains.

## What Changes

- Add a generic deterministic package-failure repair loop for child result packages rejected before independent AI review.
- Route parse/schema/tree-service guardrail failures into a repair child job with the original failure evidence, raw candidate, and package contract.
- Submit repaired packages through the same deterministic guardrails and independent review path as normal child results.
- Preserve the current visible blocked state when repair attempts are exhausted or the repair package is still invalid.
- Record repair request, response, submission, rejection, and limit events in the run log and job tree.

## Capabilities

### New Capabilities
- `deterministic-package-repair-loop`: Generic failure-to-repair routing for child result packages rejected by deterministic guardrails.

### Modified Capabilities

## Impact

- Affects sandbox runtime child dispatch, result-package failure handling, job-tree evidence, flow event logging, and regression tests.
- Does not add topic-, genre-, provider-, model-, or output-shape-specific branching to generic runtime code.
