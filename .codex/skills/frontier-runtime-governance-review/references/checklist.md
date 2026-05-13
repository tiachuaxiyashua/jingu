# Runtime Governance Review Checklist

## 1. Approval gating

- Is every risky side effect previewed before execution?
- Is approval bound to the exact preview and expiry window?
- Is approval one-time or scope-limited?

## 2. Capability boundaries

- Are local and remote capabilities scoped explicitly?
- Are filesystem roots constrained?
- Are tool/skill/package trust states enforced in runtime, not only displayed?

## 3. Recovery and rollback

- Are destructive restores staged?
- Can failures preserve the prior good state?
- Are checkpoints sufficient for resume?

## 4. Audit and evidence

- Are approvals, blocked paths, runtime events, and context packs all persisted?
- Can a reviewer reconstruct the executed path?
- Are errors actionable and structured?

## 5. Test proof

- Are destructive paths covered?
- Are replay, expiry, mismatch, corruption, and blocked cases covered?
- Are packaged/runtime realities checked, not only unit happy paths?

## 6. Review threshold

Mark `high` if any of these are true:
- approvals can be replayed or mismatched
- destructive recovery is non-transactional
- capability boundaries rely on UI instead of runtime gates
- blocked or damaged resources can still execute
