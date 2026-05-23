## ADDED Requirements

### Requirement: Parent integration repair jobs
The runtime SHALL create an observable repair job when parent integration output is invalid and SHALL NOT mutate the parent candidate unless the repaired integration output passes validation.

#### Scenario: Invalid integration creates repair work
- **WHEN** a parent integration response is invalid JSON or violates the integration contract
- **THEN** the runtime records a parent integration rejection and creates an integration repair job with the invalid response, accepted child packages, and repair contract.

#### Scenario: Invalid repair keeps parent unchanged
- **WHEN** the integration repair response is still invalid
- **THEN** the runtime records the repair failure and the parent candidate appearance remains the previous candidate.

### Requirement: Integration is visible as work
The runtime SHALL represent parent integration as observable work linked to the parent job, with its own job id, inputs, outputs, evidence, and lineage.

#### Scenario: Accepted packages are integrated
- **WHEN** accepted child packages exist for a parent
- **THEN** the runtime creates or records a parent integration job and logs the accepted packages, integration prompt, response, candidate, evidence, and consumed child refs.

### Requirement: Bounded continuous advancement
The runtime SHALL support a configured bounded advancement loop that repeatedly dispatches active frontier jobs until no progress is made, no frontier remains, or the configured wave limit is reached.

#### Scenario: Follow-up child is processed in a later wave
- **WHEN** a child package or parent integration creates a follow-up child job
- **THEN** the next configured advancement wave can dispatch that child without requiring a new top-level user turn.

### Requirement: Method-step job visibility
The runtime SHALL expose method-step candidates from bound method fragments as child jobs or trace events without hardcoding a specific method.

#### Scenario: Method fragment contains step headings
- **WHEN** a bound method fragment contains ordered section headings
- **THEN** the runtime records method-step candidates with method law ids and return points, while preserving candidate isolation.

### Requirement: Human decision request and return
The runtime SHALL allow high-value or directional feedback jobs to be recorded as human decision requests and SHALL allow human decisions to return as evidence on the same job.

#### Scenario: Human decision is recorded
- **WHEN** a human decision payload is submitted for a decision job
- **THEN** the runtime records a decision-return event and evidence that references the original decision job.

### Requirement: Evidence hardness metadata
The runtime SHALL store evidence hardness metadata for evidence appearances and SHALL expose weak evidence risks in logs.

#### Scenario: Evidence is submitted with hardness
- **WHEN** evidence is submitted with a hardness classification
- **THEN** the appearance metadata includes the hardness and the flow log exposes it.

### Requirement: Candidate lineage metadata
The runtime SHALL store lineage metadata for parent integration candidates, including upstream candidate refs, consumed child refs, integration job id, and evidence refs.

#### Scenario: Parent integration candidate is submitted
- **WHEN** a parent integration candidate is accepted by parser validation and submitted
- **THEN** its appearance metadata records the upstream root candidate, consumed child package refs, and integration job id.

### Requirement: Candidate method learning
The runtime SHALL record method update observations as candidate appearances and evidence without modifying stable method files.

#### Scenario: Method self-review suggests updates
- **WHEN** method self-review contains update candidates
- **THEN** the runtime records a method learning candidate appearance and evidence marked as candidate-only.

### Requirement: Runtime options
The runtime SHALL accept explicit options for repair attempts, child package repair attempts, frontier dispatches, advancement waves, integration repair attempts, and method-step registration.

#### Scenario: Options override defaults
- **WHEN** a runner or CLI is created with explicit loop options
- **THEN** those values control runtime behavior and appear in process logs.
