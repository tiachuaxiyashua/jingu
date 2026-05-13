---
name: cyber-editor-closure-gate
description: Use when closing review findings, user-reported defects, hardcode cleanup batches, or any multi-item fix where partial completion could be misreported as done.
---

# Cyber Editor Closure Gate

## Overview
This skill prevents false closure. Every review finding, bug report, and promised follow-up must be tracked to a concrete closure state with evidence.

## When to Use
- A review produced multiple findings.
- A user listed several defects or gaps in one turn.
- A hardcode cleanup or architecture cleanup spans several modules.
- A batch was “mostly fixed” but still has open or partial items.

Do not use this only for one isolated typo or one-file formatting cleanup.

## Required Closure Ledger
Create a closure ledger before coding. Each item must include:
- `source`: where the finding came from, such as `review:hardcode`, `user-report`, `architecture-review`
- `id`: stable short id
- `expected result`: what “closed” means
- `evidence`: test, build, review gate, screenshot, or runtime proof
- `status`: `open` | `partial` | `closed` | `blocked`

If one source produced 7 findings, the ledger must contain 7 rows. Never collapse them into one sentence.

## Execution Rules
1. Copy every finding into the ledger before implementation.
2. Fix items one by one or in small related groups.
3. Re-run the originating gate or review after fixes.
4. Update each row using evidence, not intuition.
5. Final reporting must separate:
- `closed`
- `partial`
- `open`
- `blocked`

## Forbidden Behaviors
- Saying “done” when any item is still `partial`, `open`, or `blocked`
- Treating “major findings fixed” as “all findings fixed”
- Closing a batch without re-running the original review or validation gate
- Replacing evidence with vague claims such as “should be solved now”

## Minimum Final Report
- Total findings
- Closed count
- Partial count
- Open count
- Blocked count
- Re-run commands
- Re-run result
- Explicit next actions for anything not closed

## Common Failure Pattern
Failure:
- Remove one template-specific hardcode, leave platform-level semantic assets in service code, then report the whole hardcode batch as finished.

Correct behavior:
- Mark template-specific hardcoding as `closed`
- Mark remaining assetization as `partial`
- Re-run `review:hardcode`
- Report that the review is green but deeper assetization is still open if that was part of the promised scope
