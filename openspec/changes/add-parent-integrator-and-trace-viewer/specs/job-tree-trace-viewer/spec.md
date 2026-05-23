## ADDED Requirements

### Requirement: Viewer displays step-level input output traces
The job tree log viewer SHALL present each log event as a step with categorized inputs, outputs, actions, state changes, and evidence.

#### Scenario: Show current step details
- **WHEN** a user advances to a log event
- **THEN** the viewer displays the event label, job identifiers, action summary, input fields, output fields, evidence fields, state changes, and raw JSON for that event

#### Scenario: Show provider request and response
- **WHEN** the current event records provider messages or provider responses
- **THEN** the viewer displays the provider call kind and the relevant prompt or response content in readable blocks

### Requirement: Viewer highlights integration and review milestones
The job tree log viewer SHALL highlight child package review, repair, accepted parent re-evaluation, and parent integration milestones.

#### Scenario: Highlight child package review loop
- **WHEN** logs contain child package review, repair, acceptance, or accepted parent re-evaluation events
- **THEN** the viewer shows these events as key timeline steps and updates job node status accordingly

#### Scenario: Highlight parent integration
- **WHEN** logs contain parent integration request, response, candidate submission, rejection, or skip events
- **THEN** the viewer shows these events as key timeline steps and exposes the integrated candidate or rejection reason

### Requirement: Viewer remains a read-only local mirror
The job tree log viewer SHALL remain a static read-only local parser of JSONL logs.

#### Scenario: Load log locally
- **WHEN** a user loads a JSONL file in the browser
- **THEN** the viewer parses and renders it locally without uploading, calling providers, creating jobs, or modifying runtime state

#### Scenario: Unknown event fallback
- **WHEN** a log contains an unknown event type
- **THEN** the viewer still displays the event in the timeline and raw JSON panel without failing the whole projection
