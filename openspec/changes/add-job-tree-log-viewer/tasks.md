## 1. Viewer Contract

- [x] 1.1 Create the static viewer files under a repo-owned tool path.
- [x] 1.2 Implement local JSONL file loading, parsing errors, and Chinese empty states.

## 2. Replay And Projection

- [x] 2.1 Implement prefix-based event replay with start, previous, next, end, and play/pause controls.
- [x] 2.2 Reconstruct job nodes, parent-child edges, states, attachments, action history, and loop milestones from log events.
- [x] 2.3 Render graph, timeline, selected job details, current event details, and loop summary without writing back to logs.

## 3. Validation

- [x] 3.1 Add a lightweight validation script for parsed logs and expected milestones.
- [x] 3.2 Validate the viewer against real repair and feedback logs.
- [x] 3.3 Run OpenSpec validation, syntax checks, hardcoding scan, and final git review.
