## ADDED Requirements

### Requirement: Local JSONL Log Loading
The viewer SHALL allow the user to load a Jingu JSONL flow log from the local browser without uploading it to a server.

#### Scenario: User loads a valid log
- **WHEN** the user selects a valid `.jsonl` file containing Jingu flow events
- **THEN** the viewer MUST parse the events, show the file name, event count, and enable replay controls.

#### Scenario: User loads malformed input
- **WHEN** the selected file contains malformed JSONL lines
- **THEN** the viewer MUST show a readable Chinese error with the failing line number and MUST NOT silently render a false graph.

### Requirement: Step Replay
The viewer SHALL replay the event stream as an append-only sequence.

#### Scenario: Step forward
- **WHEN** the user clicks the next-step control
- **THEN** the viewer MUST advance by one event and update the graph, timeline, counters, and current-event detail from events up to that step.

#### Scenario: Step backward
- **WHEN** the user clicks the previous-step control
- **THEN** the viewer MUST move back by one event and recompute the graph projection for the earlier prefix.

#### Scenario: Jump controls
- **WHEN** the user clicks start or end
- **THEN** the viewer MUST jump to the first or final event prefix without mutating the source log.

### Requirement: Job Tree Projection
The viewer SHALL reconstruct a human-visible job tree projection from flow events.

#### Scenario: Job tree management event appears
- **WHEN** a `job_tree_management_recorded` event contains job, parent, root, state, target, action, child, or appearance fields
- **THEN** the viewer MUST update the corresponding node, parent-child edge, state label, action history, and attachment counts.

#### Scenario: Child job appears
- **WHEN** an event contains a parent job id and a child job id or job id for a child
- **THEN** the viewer MUST show the child under its parent and preserve the root linkage when present.

#### Scenario: Missing projection fields
- **WHEN** an event lacks optional tree fields
- **THEN** the viewer MUST keep the event in the timeline and current-event detail while avoiding invented job ids or parent links.

### Requirement: Closed Loop Visibility
The viewer SHALL make verification, repair, feedback, acceptance routing, result output, run finish, and sandbox teardown visible as loop milestones.

#### Scenario: Repair branch log is loaded
- **WHEN** the log includes acceptance routing with `route_action=repair`, repair job creation, repair candidate submission, and a later verification result
- **THEN** the viewer MUST show those milestones in the loop summary and the job tree.

#### Scenario: Feedback branch log is loaded
- **WHEN** the log includes acceptance routing with `route_action=feedback` and feedback job creation
- **THEN** the viewer MUST show the feedback child job and the feedback route reason.

#### Scenario: Run closes
- **WHEN** `run_finished`, `chat_session_finished`, or `sandbox_destroyed` appears
- **THEN** the viewer MUST mark the run closure status in the summary without declaring human acceptance.

### Requirement: Human Readable Chinese Interface
The viewer SHALL present primary controls, labels, status summaries, and empty/error states in Chinese.

#### Scenario: No file loaded
- **WHEN** the page first opens
- **THEN** the viewer MUST explain in Chinese that the user should load a Jingu JSONL log and MUST show no fake sample graph.

#### Scenario: Event selected
- **WHEN** the replay cursor points to an event
- **THEN** the viewer MUST show the event type, Chinese label, timestamp, key fields, and raw JSON for audit.
