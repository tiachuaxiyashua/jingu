# Design: repair-harness-delivery-loop

## Truth Alignment

This change follows the current truth source:

- `愿源保真律`: the original wish remains the source of the quantitative delivery target.
- `立业变更律`: continuation work is represented as child jobs, not silent prompt continuation.
- `候选隔离律`: continuation children submit candidate packages only.
- `缘备显缺律`: unsupported gaps are parked and logged instead of being hidden.
- `证成归属律`: terminal acceptance remains blocked until the root delivery ledger is satisfied.

## Runtime Shape

The implementation stays within the existing small kernel:

- Deterministic text contract parsing lives with candidate verification.
- Parent integration continues to be the point where accepted child packages update the parent candidate.
- Follow-up registration becomes critical-path aware. It does not introduce a new persistent component.

## Delivery Ledger

The ledger is derived from:

- task text
- current candidate text
- parsed deterministic text-length constraints

It records:

- whether a quantitative text contract exists
- selected counting region
- current CJK count
- required minimum
- allowed maximum
- remaining minimum count
- status

## Follow-up Triage

When the ledger is below its minimum:

- one delivery-continuation child may be registered
- open gaps and suggested follow-ups are parked as visible backlog/risk evidence
- active child jobs that require full root-length completion are rejected until the parent candidate reaches the minimum

When no delivery contract is present, existing open-gap and follow-up registration remains unchanged.
