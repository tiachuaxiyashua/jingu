## ADDED Requirements

### Requirement: Sandbox can dispatch active child frontier
The AI sandbox SHALL dispatch active child frontier jobs after AI split proposals have been registered.

#### Scenario: Dispatch active child job
- **WHEN** split proposal registration creates active child jobs under the current root job
- **THEN** the sandbox selects active leaf child jobs and starts each selected child job through the runtime service before calling the AI provider for that child

#### Scenario: Skip when no active child frontier exists
- **WHEN** no active child leaf job exists under the current root job
- **THEN** the sandbox records that frontier dispatch was skipped and continues the normal root candidate flow

### Requirement: Child execution submits structured result package candidates
The AI sandbox SHALL require dispatched child jobs to return structured result packages and SHALL submit valid packages as child job candidates with evidence.

#### Scenario: Valid child result package
- **WHEN** a dispatched child job returns a JSON package with conclusion, artifacts, evidence summary, open questions, and suggested follow-up jobs
- **THEN** the sandbox submits the package through the tree service and records child package submission

#### Scenario: Invalid child result package
- **WHEN** a dispatched child job returns invalid JSON or an incomplete package
- **THEN** the sandbox records the child package rejection and MUST NOT mark the child or parent as complete

### Requirement: Parent re-evaluation is logged after child package submission
The AI sandbox SHALL record parent re-evaluation after each child result package submission.

#### Scenario: Parent sees candidate child package
- **WHEN** a child package has been submitted as a candidate
- **THEN** the sandbox records the parent re-evaluation output including unresolved children, open questions, and child method call frames

### Requirement: Child execution can propose next-level jobs without recursive execution
The AI sandbox SHALL allow a dispatched child job to propose next-level child jobs through the existing split proposal registration path, but SHALL NOT execute those next-level jobs in the same dispatch pass.

#### Scenario: Child proposes grandchild jobs
- **WHEN** a dispatched child result exposes further blocking work
- **THEN** the sandbox can register grandchild jobs through the code gatekeeper and leave them for a later dispatch pass
