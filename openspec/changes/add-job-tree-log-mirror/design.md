## Context

The AI sandbox writes a machine JSONL event stream and a Chinese-readable Markdown mirror. The current events show individual actions, but they do not make the job tree legible: a user can see that a feedback job was created, yet cannot easily see the parent-child relationship, current node states, or how the tree changed after each management action.

The truth source treats `镜` as a human-facing projection, not as the source of truth. The runtime database and event ledger remain authoritative; this change only adds a readable tree projection derived from runtime state at selected checkpoints.

## Goals / Non-Goals

**Goals:**

- Emit explicit flow events for job-tree state changes during AI sandbox runs and chats.
- Include a compact tree snapshot after meaningful tree mutations.
- Preserve all raw identifiers so logs remain useful for debugging and replay.
- Keep the JSONL event stream and Markdown projection aligned.

**Non-Goals:**

- Do not add a new persistence table.
- Do not change runtime job state semantics.
- Do not auto-accept, auto-reject, or add new human verdict behavior.
- Do not hardcode Neidan Method workflow decisions into the logging layer.

## Decisions

1. **Use flow events, not a separate log format.**
   The sandbox already writes JSONL plus a readable projection. Adding tree-specific flow events keeps monitoring, saved logs, and tests on one path. A separate tree log was rejected because it would create another source to reconcile.

2. **Snapshot through `RuntimeService.get_status` and event-derived fields.**
   The runner can ask the runtime for status after each meaningful change and write a compact JSON snapshot. This avoids duplicating database truth in the sandbox. A full DB dump was rejected because it would be noisy and harder for humans to scan.

3. **Keep tree projection generic.**
   The mirror records job ids, parent ids, root ids, states, targets, candidate/evidence/result ids, and child job ids. It does not mention specific methods, domains, or business workflows unless those are already in runtime state.

4. **Render tree snapshots as readable multiline blocks.**
   The Markdown mirror should show tree snapshots as formatted JSON blocks with Chinese labels, while preserving raw event names and field ids.

## Risks / Trade-offs

- Extra log volume -> Keep snapshots compact and emit only at meaningful tree checkpoints.
- Tree mirror drift -> Generate snapshots from runtime status immediately after the runtime mutation that caused the event.
- Misreading mirror as truth -> Label it as a mirror/snapshot and keep source identifiers in every event.
