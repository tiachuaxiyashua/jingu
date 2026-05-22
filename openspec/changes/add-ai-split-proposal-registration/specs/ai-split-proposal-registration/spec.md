## ADDED Requirements

### Requirement: AI can propose child jobs without mutating the tree directly
The AI sandbox SHALL request structured child-job proposals from the model after candidate generation and SHALL treat those proposals as candidates until code gatekeeping accepts them.

#### Scenario: Request structured split proposals
- **WHEN** an AI sandbox run receives a candidate response from the provider
- **THEN** the sandbox sends a separate split proposal extraction request containing the user input, candidate response, parent job id, root method manifest, and available method catalog

#### Scenario: No proposals returned
- **WHEN** the split proposal extraction response contains an empty proposals array
- **THEN** the sandbox records that no child jobs were registered and continues the normal candidate verification flow

### Requirement: Code gatekeeper registers accepted proposals
The system SHALL register AI-proposed child jobs only by passing each proposal through the existing guarded tree service.

#### Scenario: Valid proposal is registered
- **WHEN** a split proposal has target, blocking reason, output contract, acceptance criteria, effort, depth limit, and valid optional method binding fields
- **THEN** the sandbox creates a real child job through the tree service and records the accepted registration

#### Scenario: Invalid proposal is rejected
- **WHEN** a split proposal is missing required fields, duplicates an existing sibling, exceeds guardrails, or references an unavailable method
- **THEN** the sandbox records the rejected proposal and MUST NOT create a child job for it

### Requirement: AI-selected methods come from a method catalog
The system SHALL provide a method catalog to the split proposal step and SHALL only allow AI-selected child methods that resolve from that catalog.

#### Scenario: Proposal selects catalog method
- **WHEN** a proposal selects a method path present in the method catalog
- **THEN** the child job can bind that method and open a method call frame if all binding fields are valid

#### Scenario: Proposal selects unknown method
- **WHEN** a proposal selects a method path absent from the method catalog
- **THEN** the proposal is rejected before child job creation

### Requirement: Split proposal registration is observable
The sandbox SHALL record split proposal requests, provider responses, accepted registrations, rejected registrations, and tree snapshots in both JSONL and readable logs.

#### Scenario: Readable log shows accepted and rejected proposals
- **WHEN** a sandbox run processes both accepted and rejected split proposals
- **THEN** the readable log shows the proposal payload, decision, reason, child job id for accepted proposals, and rejection reason for rejected proposals

#### Scenario: Tree snapshot includes registered child frames
- **WHEN** an accepted proposal binds a method to a child job
- **THEN** subsequent tree snapshots include the child job and its method call frame
