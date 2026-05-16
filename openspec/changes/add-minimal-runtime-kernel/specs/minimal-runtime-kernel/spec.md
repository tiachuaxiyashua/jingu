## ADDED Requirements

### Requirement: Runtime initialization
The system SHALL initialize a local Jingu runtime directory containing a SQLite runtime database and object store without committing local runtime state to version control.

#### Scenario: Initialize runtime in an empty workspace
- **WHEN** the user runs runtime initialization for a workspace
- **THEN** the system creates the runtime database, required schema tables, and object store directory

#### Scenario: Reinitialize existing runtime
- **WHEN** the user runs runtime initialization after the runtime already exists
- **THEN** the system keeps existing data and leaves the runtime usable

### Requirement: Root job creation preserves original wish
The system SHALL create a root job from a human wish by preserving the original wish as an immutable appearance and linking the job to that appearance.

#### Scenario: Create root job
- **WHEN** the user creates a root job with a wish and target
- **THEN** the system stores the original wish as an `original_wish` appearance and creates a draft root job referencing it

#### Scenario: Original wish is not overwritten by target text
- **WHEN** the root job target differs from the original wish
- **THEN** the system retains both the original wish reference and the job target

### Requirement: Append-only event ledger
The system SHALL record every durable state-changing operation as an append-only event with a checksum chain.

#### Scenario: State-changing operation records event
- **WHEN** a root job is created or a candidate is submitted
- **THEN** the system appends an event containing the job id, event type, payload, previous checksum, and current checksum

#### Scenario: Event order is queryable
- **WHEN** events for a job are requested
- **THEN** the system returns events in creation order without mutating prior events

### Requirement: Job state machine
The system SHALL enforce the first-stage job states `draft`, `ready`, `running`, `blocked`, `reviewing`, `accepted`, `rejected`, `waiting_human`, and `abandoned`.

#### Scenario: Move ready job into running
- **WHEN** a draft job has no open required-context gaps and the user marks it ready then running
- **THEN** the system records the state transitions and reports the current state as `running`

#### Scenario: Block running when required context is missing
- **WHEN** a job has open required-context gaps
- **THEN** the system MUST reject a transition into `running`

### Requirement: Candidate isolation
The system SHALL keep submitted result appearances in candidate state until the responsible job accepts them with evidence.

#### Scenario: Submit candidate result
- **WHEN** the user submits a candidate result for a job
- **THEN** the system stores the result as a `candidate_result` appearance and moves the job to `reviewing`

#### Scenario: Candidate is not accepted automatically
- **WHEN** a candidate result has been submitted but not accepted
- **THEN** the system MUST NOT expose it as an accepted result for the job

### Requirement: Evidence-backed acceptance
The system SHALL require an evidence appearance before a job can accept a candidate result as complete within its responsibility scope.

#### Scenario: Accept candidate with evidence
- **WHEN** the user submits evidence and accepts a candidate result using that evidence
- **THEN** the system marks the job `accepted`, marks the candidate appearance `accepted`, and links the evidence to the job

#### Scenario: Reject acceptance without evidence
- **WHEN** the user attempts to accept a candidate result without evidence
- **THEN** the system MUST reject the operation and leave the job unaccepted

### Requirement: Guardkeeper hard failures
The system SHALL reject illegal operations before they are written to the event ledger.

#### Scenario: Reject event without job
- **WHEN** an operation references a missing job id
- **THEN** the system MUST reject the operation and MUST NOT append an event

#### Scenario: Reject direct result submission without job
- **WHEN** a user attempts to submit a result without a valid job
- **THEN** the system MUST reject the result and MUST NOT create a stable appearance

#### Scenario: Reject child completing parent scope
- **WHEN** a child job attempts to accept or complete a parent or root responsibility scope
- **THEN** the system MUST reject the operation and MUST NOT mark the parent or root job accepted

#### Scenario: Reject broken appearance reference
- **WHEN** an operation references an appearance with a missing record, failed checksum, or incompatible version
- **THEN** the system MUST reject the operation before state changes are recorded

### Requirement: CLI manual workflow
The system SHALL provide a command-line workflow for initializing the runtime, creating a root job, submitting candidates and evidence, accepting or rejecting candidates, and inspecting status and events.

#### Scenario: Complete manual happy path
- **WHEN** the user initializes the runtime, creates a root job, marks it ready and running, submits a candidate, submits evidence, and accepts the candidate
- **THEN** the CLI exits successfully and `status` reports the job as `accepted`

#### Scenario: Inspect audit trail
- **WHEN** the user asks for events for a job
- **THEN** the CLI displays the recorded event sequence for that job
