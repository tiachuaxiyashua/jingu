## ADDED Requirements

### Requirement: Trace debugger filters
The static job tree viewer SHALL provide local filtering by search text, event phase, event type, job id, and appearance id without modifying the loaded log.

#### Scenario: User filters by phase
- **WHEN** the user selects a phase filter
- **THEN** the timeline shows only matching events while the graph projection remains based on the current replay cursor.

### Requirement: Appearance trace following
The viewer SHALL highlight or list all current-event fields that reference a selected appearance id.

#### Scenario: User searches an appearance id
- **WHEN** the user enters an appearance id in the viewer search
- **THEN** matching input, output, evidence, state, and raw JSON fields are visible and highlighted.

### Requirement: Failure-chain visibility
The viewer SHALL expose integration repair, rejection, human decision, weak evidence, and learning-candidate milestones in summary and step details.

#### Scenario: Integration repair appears in logs
- **WHEN** a log contains integration repair events
- **THEN** the viewer summary and timeline show the repair milestone and the selected step displays its input/output/evidence/state panes.
