## Why

A real DeepSeek long-delivery run exposed two violations of the truth-aligned loop: after an accepted child delivered measurable content, a parent integration note replaced the delivery count with a smaller number; and follow-ups already parked as non-critical work were later registered again as active siblings. Without correcting these semantics, long tasks cannot converge honestly through repeated minimal-loop execution.

## What Changes

- Make quantitative delivery progress derive from accepted, delivery-relevant result packages rather than whichever candidate text was most recently emitted.
- Preserve provenance and deduplication for accepted delivery contributions so parent integration cannot decrease accumulated progress or double count the same fruit.
- Gate split registration while a quantitative minimum remains unmet: retain only direct non-duplicate critical delivery advancement, and visibly park non-critical or duplicate sibling proposals.
- Record ledger provenance and frontier-gating decisions in the event/readable log for human diagnosis.

## Capabilities

### New Capabilities
- `accepted-delivery-frontier-convergence`: Truth-aligned accumulated delivery accounting and controlled critical frontier routing for incomplete quantitative work.

### Modified Capabilities

## Impact

- Affects the sandbox runtime orchestration, deterministic delivery ledger representation, flow log labels, runtime-owned job contract data, and regression tests.
- Does not add task-domain strings, provider defaults, or topic-specific branching to generic runtime code.
