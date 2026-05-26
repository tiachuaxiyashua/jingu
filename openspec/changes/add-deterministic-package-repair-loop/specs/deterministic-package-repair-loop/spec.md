## ADDED Requirements

### Requirement: Deterministic package rejection creates repair work
When a child result package is rejected by deterministic parsing, schema, or tree-service guardrails before independent review, the sandbox SHALL create a repair job for the original child package if package-repair attempts remain.

#### Scenario: Deterministic failure routes to repair job
- **GIVEN** a child job returns a malformed or guardrail-rejected result package
- **AND** package repair attempts remain
- **WHEN** the sandbox handles the child result
- **THEN** it records the deterministic rejection evidence
- **AND** it creates a repair child job targeting the original child job instead of immediately marking the original child blocked.

#### Scenario: Repair budget exhaustion blocks visibly
- **GIVEN** a child job returns a deterministic package failure
- **AND** no package repair attempts remain
- **WHEN** the sandbox handles the child result
- **THEN** it blocks the original child job
- **AND** it records the latest failure reason in the event log and readable log.

### Requirement: Repaired package follows normal acceptance path
A repaired child package SHALL be parsed, submitted, and reviewed through the same deterministic guardrails and independent package review path as a normal child result package.

#### Scenario: Repaired package passes deterministic checks
- **GIVEN** a deterministic package failure has created a repair job
- **WHEN** the repair actor returns a valid repaired package for the original child
- **THEN** the sandbox submits the repaired package to the original child job
- **AND** the package proceeds to independent package review before it can be accepted.

#### Scenario: Repaired package fails deterministic checks
- **GIVEN** a deterministic package failure has created a repair job
- **WHEN** the repair actor returns another malformed or guardrail-rejected package
- **THEN** the sandbox records the repair rejection evidence
- **AND** it either creates another repair attempt when budget remains or blocks the original child when the limit is reached.

### Requirement: Repair routing is observable
The sandbox SHALL log deterministic repair request, repair response, repaired package submission, repair rejection, and repair limit events with target job, repair job, attempt index, failure reason, and failure source.

#### Scenario: Human can inspect repair chain
- **WHEN** a deterministic child-package failure enters the repair loop
- **THEN** the machine log contains structured events for the rejection and repair chain
- **AND** the readable log explains in Chinese which child job failed, which repair job was created, and whether the repaired package was submitted, rejected, accepted, or blocked.
