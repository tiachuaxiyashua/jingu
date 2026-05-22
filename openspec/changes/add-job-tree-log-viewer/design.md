## Context

Jingu flow logs are append-only JSONL event streams. Current runs already emit machine events for root job creation, job-tree management records, snapshots, candidate and evidence attachments, deterministic verification, repair, feedback, provider calls, and terminal sandbox events. The user needs a human-facing mirror that can replay those events visually and expose where the loop grew, repaired, escalated, or closed.

The truth source treats `镜` as a projection, not truth. Therefore the viewer must reconstruct state from selected logs and remain read-only.

## Goals / Non-Goals

**Goals:**

- Load a user-selected `.jsonl` flow log directly in a browser.
- Rebuild a visible job tree from `job_tree_management_recorded` events and fall back to `job_tree_snapshot_recorded` snapshots when useful.
- Let the user step forward, step backward, jump to start/end, or play through the event sequence.
- Show a Chinese timeline, current event detail, loop counters, selected job detail, and graph edges.
- Highlight closed-loop milestones: candidate, verification, repair, feedback, acceptance routing, run finish, and sandbox destroy.

**Non-Goals:**

- No runtime mutation, job creation, acceptance, rejection, or AI calls.
- No server, database, remote upload, or persistent browser storage.
- No attempt to replace the JSONL log or runtime event ledger as truth.
- No fixed sample log path or provider-specific assumptions.

## Decisions

1. **Static local page**

   The viewer will live under `tools/job-tree-log-viewer/` and run from `index.html`. The browser File API loads the selected log. This avoids secrets, server setup, and path hardcoding.

   Alternative considered: a Python or Node dev server. Rejected for the first version because the user specifically needs direct log inspection, and a server would add lifecycle and sandbox concerns that are not needed.

2. **Client-side replay model**

   The page parses JSONL into ordered events, then applies events from index `0..N` into an in-memory projection. Each click on “下一步” replays one additional event. This matches append-only event semantics and keeps the graph explainable.

   Alternative considered: render only the latest `tree_snapshot`. Rejected because it cannot show growth over time.

3. **Use management records as primary graph events**

   `job_tree_management_recorded` carries `job_id`, `parent_job_id`, `root_job_id`, `job_state`, `job_target`, `child_job_id`, `appearance_id`, and `job_tree_action`. The viewer uses those fields as the primary source for nodes, edges, state, and attachments. Snapshot events are parsed and made visible as evidence but do not override the incremental projection unless the graph has missing nodes.

4. **Chinese human-facing UI**

   Labels, counters, actions, and empty/error states are Chinese. Raw JSON remains available in a detail panel so debugging evidence is not hidden.

5. **No external dependencies**

   Use plain HTML, CSS, and JavaScript. This keeps the viewer portable and reviewable in the repo without package installation.

## Risks / Trade-offs

- [Risk] Old or malformed logs may omit fields needed for a perfect tree. → Mitigation: tolerate missing fields, display warnings, and still show the raw event.
- [Risk] Very large provider stream logs can be slow if every event is rendered. → Mitigation: render timeline summaries and keep full detail only for the selected current event.
- [Risk] Graph layout may get crowded for deep trees. → Mitigation: use level-based columns by parent depth and make the job detail panel the precise inspection surface.
- [Risk] A projection can be mistaken for source truth. → Mitigation: UI labels call it “日志镜像/投影”, and raw event evidence stays visible.
