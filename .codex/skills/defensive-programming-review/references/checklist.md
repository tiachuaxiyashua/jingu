# Defensive Checklist

Use this checklist on the exact runtime path under review.

## 1. External Input Handling

- Is every file, JSON payload, IPC argument, and model output validated once by a clear owner?
- Does malformed input return a structured error instead of a raw exception?
- Are schema upgrades, missing fields, and unknown fields handled deliberately?

## 2. Trust And Approval Boundaries

- Are privileged or destructive actions gated before execution?
- Is approval bound to the exact object being approved?
- Can old approvals, stale previews, or copied identifiers be replayed?
- Is expiry enforced?

## 3. Destructive Mutation Safety

- Does the code mutate live state directly?
- Is there a stage-copy-validate-switch or rollback path?
- What happens on interrupted copy, permission error, or disk-full?

## 4. State Ownership And Coupling

- Is there one source of truth for state?
- Is renderer logic leaking persistence or trust decisions?
- Is one file coordinating too many unrelated domains?
- Are schema and error semantics duplicated across modules?

## 5. Error Contract And Recovery

- Is every important failure mapped to a stable error code or structured result?
- Does the user get a repairable next action?
- Can the system recover without manual file surgery?
- Is a damaged state detectable?

## 6. Durability And Idempotency

- Can the same action be retried safely?
- Can a partial prior action corrupt the next run?
- Are timestamps, IDs, and temp paths scoped tightly enough?

## 7. Test Blind Spots

- Is there a negative-path test for each high-risk guard?
- Do tests cover malformed input, expired approval, replay, partial write, and restore failure?
- Could code structure decay while tests still pass?

## 8. Docs-Code-Test Parity

- Do docs promise stronger guarantees than code provides?
- Do tests enforce the documented guarantee?
- Is the implemented behavior explicit enough that another engineer would build the same thing?
