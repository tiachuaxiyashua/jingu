## ADDED Requirements

### Requirement: Guarded child job proposal
The system SHALL create child jobs through a guarded proposal path that rejects decorative or non-executable splits.

#### Scenario: Create child job from valid proposal
- **WHEN** a proposal includes parent job id, target, blocking reason, output contract, acceptance criteria, estimated effort, and depth limit
- **THEN** the system creates a child job linked to the same root job and records a split proposal event followed by a child-created event

#### Scenario: Reject vague proposal
- **WHEN** a proposal omits the blocking reason, output contract, or acceptance criteria
- **THEN** the system MUST reject the proposal and MUST NOT create a child job

#### Scenario: Reject duplicate sibling target
- **WHEN** a proposal targets the same work as an existing sibling child job
- **THEN** the system MUST reject the proposal and MUST NOT create a duplicate child job

### Requirement: Job tree projection
The system SHALL expose a query view of a root job tree without turning the view into a new source of truth.

#### Scenario: Show job tree
- **WHEN** the user asks for the tree of a root or descendant job
- **THEN** the system returns the root job, every descendant job, parent-child links, current states, targets, and required-context gaps

#### Scenario: Preserve true hierarchy
- **WHEN** a child job has its own child job
- **THEN** the tree view preserves the grandchild relation rather than flattening it into the parent context

### Requirement: Active frontier projection
The system SHALL expose active unresolved leaf jobs as the current blocking frontier.

#### Scenario: Show frontier
- **WHEN** the user asks for the frontier of a root job
- **THEN** the system returns active leaf jobs that are not accepted, rejected, or abandoned

#### Scenario: Include blocking gaps
- **WHEN** a frontier job has required-context gaps
- **THEN** the frontier entry includes those gaps

### Requirement: Structured result package
The system SHALL allow a job to submit a structured result package as a candidate result with separate evidence.

#### Scenario: Submit structured package
- **WHEN** a running job submits a package containing conclusion, artifacts, evidence summary, open questions, and suggested follow-up jobs
- **THEN** the system stores the package as a candidate result, stores evidence separately, records the package event, and leaves the job in review

#### Scenario: Reject incomplete package
- **WHEN** a package omits conclusion or evidence summary
- **THEN** the system MUST reject the package and MUST NOT create a candidate result

### Requirement: Parent re-evaluation view
The system SHALL expose a parent re-evaluation view summarizing child results, unresolved gaps, open questions, and completion readiness.

#### Scenario: Parent has unresolved children
- **WHEN** any child job is still active or blocked
- **THEN** parent re-evaluation reports the parent as not ready for completion and lists the unresolved child jobs

#### Scenario: Parent has accepted child packages
- **WHEN** child jobs have accepted results with evidence
- **THEN** parent re-evaluation includes those accepted result references and evidence references for parent consumption

### Requirement: Method validation support without method hardcoding
The system SHALL support functional validation of a user-provided method by representing the method validation as ordinary jobs, child jobs, packages, evidence, and tree views.

#### Scenario: Represent method validation tree
- **WHEN** a user creates a root job for method validation and proposes child jobs for the validation work
- **THEN** the system records a real job tree and can show frontier and parent re-evaluation without requiring engine code that knows the method's name or steps

#### Scenario: Method-specific payload stays user data
- **WHEN** a structured package contains method-specific fields
- **THEN** the system stores those fields inside the package payload and does not branch on them in engine code

### Requirement: Tree CLI workflow
The system SHALL provide CLI commands for manually driving the minimal job tree workflow.

#### Scenario: Manual tree workflow
- **WHEN** the user creates a root job, proposes a child job, marks it ready and running, submits a structured package, and asks for tree and frontier views
- **THEN** the CLI exits successfully and prints the corresponding runtime state as JSON
