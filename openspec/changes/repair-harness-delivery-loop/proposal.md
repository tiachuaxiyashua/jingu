# Change: repair-harness-delivery-loop

## Why

The current sandbox harness can expose failures and record checkpoints, but large quantitative deliverables can still fan out into many active child jobs without a root-level delivery ledger. This lets support, risk, and terminal integration work run before the root delivery target is met.

## What Changes

- Add deterministic parsing for Chinese quantity expressions such as `10万字到20万字`.
- Record a root delivery ledger whenever a quantitative text target is visible.
- Route parent integration gaps into active work only when they advance the current critical path.
- While a root quantitative delivery target is below its minimum, create at most one delivery-continuation child from parent integration and park non-critical gaps as visible backlog/risk evidence.
- Reject split proposals that require the root quantitative delivery target to already be complete while the current parent candidate is still below the minimum.

## Impact

- Long text tasks should continue by batch instead of treating a checkpoint as completion.
- Logs should show the delivery ledger and parked follow-ups, so the user can see why the harness is continuing production rather than expanding every gap into active work.
- Existing non-quantitative gap registration behavior remains available for tasks without a parsed delivery contract.
