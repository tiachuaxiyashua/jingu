## ADDED Requirements

### Requirement: Child jobs can bind their own method
The system SHALL allow a valid child job proposal to bind a method to the created child job without binding that method to the parent job.

#### Scenario: Create child job with method binding
- **WHEN** a child proposal includes a parent job id, executable split fields, a method path, a binding reason, and a return point
- **THEN** the system creates the child job, binds the method-law fragments to the child job, and leaves the parent job unbound to that child method

#### Scenario: Create child job without method binding
- **WHEN** a child proposal omits method binding fields
- **THEN** the system creates the child job without method-law fragment bindings and without a method call frame

#### Scenario: Reject incomplete method binding
- **WHEN** a child proposal includes a method path but omits the binding reason or return point
- **THEN** the system MUST reject the proposal and MUST NOT create the child job

### Requirement: Method calls are recorded as call frames
The system SHALL record each method binding that represents a method call as an append-only method call frame event.

#### Scenario: Open method call frame
- **WHEN** a job binds a method as an executable method call
- **THEN** the system records a method call frame containing method identity, job id, input, output contract, acceptance criteria, return point, budget, depth, and repeat detection key

#### Scenario: Preserve method call frame in event ledger
- **WHEN** a method call frame is recorded
- **THEN** it appears in the job event ledger after method-law fragment binding and before candidate submission for that job

### Requirement: Tree views expose method call frames
The system SHALL project method call frames into job tree and parent re-evaluation views without duplicating them as job table state.

#### Scenario: Show tree with child method call frame
- **WHEN** the user asks for a tree containing a child job with a method call frame
- **THEN** the child job summary includes the method call frame data and the parent summary does not inherit that child method

#### Scenario: Parent re-evaluation shows child method evidence
- **WHEN** the user asks for parent re-evaluation after child jobs have method call frames
- **THEN** the re-evaluation output includes each child's method call frame references alongside unresolved child and accepted result data

### Requirement: Method loader does not compose multiple laws into one job
The system SHALL NOT provide a static includes-style method composition path that merges multiple independent methods into the same job context.

#### Scenario: Independent methods remain independent
- **WHEN** a task needs 内丹法, PDCA 法, 控制变量法, and 辩证法
- **THEN** the expected runtime representation is separate jobs or call frames, not a single composed method source
