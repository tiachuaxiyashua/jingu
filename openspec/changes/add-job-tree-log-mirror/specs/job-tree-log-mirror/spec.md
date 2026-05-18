## ADDED Requirements

### Requirement: Job Tree Change Events
The AI sandbox SHALL emit readable flow events for meaningful job-tree changes, including root job creation, state transitions, candidate/evidence attachment, feedback child job creation, and feedback child job skipping.

#### Scenario: Root job lifecycle is visible
- **WHEN** an AI sandbox turn creates and starts a root job
- **THEN** the flow log contains job-tree events that identify the root job id, parent job id if any, root job id, current state, and target summary.

#### Scenario: Candidate and evidence attachment is visible
- **WHEN** an AI sandbox turn submits a candidate result and evidence for a job
- **THEN** the flow log contains job-tree events that identify the affected job and attached appearance ids.

### Requirement: Job Tree Snapshot Mirror
The AI sandbox SHALL include compact job-tree snapshots after meaningful tree management actions so the monitor and saved readable log show current parent-child relationships and node states.

#### Scenario: Feedback child job creates a tree snapshot
- **WHEN** a feedback judgment creates a child job
- **THEN** the flow log contains a tree snapshot with the parent job and child job relationship.

#### Scenario: Feedback child job is skipped
- **WHEN** a feedback judgment does not create a child job
- **THEN** the flow log contains a tree management event that records the skip reason without fabricating a child node.

### Requirement: Mirror Is Not Source Of Truth
The job-tree log mirror SHALL be derived from runtime state and SHALL NOT replace the runtime database, event ledger, or runtime guardkeeper decisions.

#### Scenario: Snapshot fields are derived after mutation
- **WHEN** the sandbox writes a tree snapshot after a runtime mutation
- **THEN** the snapshot reflects the runtime state after that mutation and preserves raw runtime identifiers for later debugging.
