## 1. Delivery Contribution Contract

- [x] 1.1 Extend child result package schema/prompts with `delivery_contributions` and validate new submissions without losing read compatibility for older accepted packages.
- [x] 1.2 Extend deterministic delivery ledger construction to support accepted contribution accounting with provenance and diagnostic current-candidate counts.

## 2. Runtime Routing

- [x] 2.1 Use accepted contribution accounting in parent integration follow-up routing and split proposal prompts.
- [x] 2.2 Gate incomplete quantitative split registration to one critical delivery frontier and park non-critical or duplicate proposals visibly.
- [x] 2.3 Skip duplicate generic split extraction after parent integration has already registered a delivery-continuation child.

## 3. Evidence And Verification

- [x] 3.1 Add regression coverage for non-decreasing accepted delivery counts and support-material exclusion.
- [x] 3.2 Add regression coverage for parked duplicate/non-critical incomplete-delivery proposals.
- [x] 3.3 Run tests, OpenSpec validation, compile check, and hardcoding scan.
- [x] 3.4 Prevent accepted child packages from self-recursing on the root quantitative contract before returning to the parent.
- [x] 3.5 Keep parent integration reference-based and prevent intermediate integration from rewriting large delivery bodies.
- [x] 3.6 Pause auto-continued quantitative delivery after an accepted measurable batch and persist a checkpoint.
- [x] 3.7 Keep JSONL stream deltas complete while compacting the human-readable log projection.
- [x] 3.8 Re-run the original DeepSeek long-delivery task and inspect the logs for accumulated delivery and active-frontier behavior.

Evidence: real DeepSeek reruns were recorded under `local-ai-logs/delivery-loop-rerun-20260526-fixed-attempt6` through `attempt9`. Attempt9 confirmed that an inflated delivery count claim is blocked, checkpointed, and sandbox cleanup is recorded instead of being integrated as accepted progress.
