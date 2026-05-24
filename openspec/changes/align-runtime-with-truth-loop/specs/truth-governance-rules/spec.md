## ADDED Requirements

### Requirement: Truth invariants before implementation
Before modifying durable code, tests, scripts, skills, or runtime docs, the implementation plan MUST identify the truth-source invariant protected by the change.

#### Scenario: Runtime change starts
- **WHEN** a developer begins a runtime, orchestration, AI harness, job-tree, law, evidence, verification, or sandbox change
- **THEN** the plan or OpenSpec artifact MUST state which `truth/` source section and which root law or Xiang-Ye invariant the change protects

#### Scenario: No matching truth invariant
- **WHEN** a proposed implementation cannot be traced to a current truth-source invariant
- **THEN** the developer MUST update or propose a truth-source change before implementing durable code

### Requirement: No symptom-driven component growth
New runtime components MUST NOT be added only to fix a symptom when the behavior can be expressed as a job, law, method, evidence item, appearance, or mirror projection.

#### Scenario: New component proposed
- **WHEN** implementation introduces a new service, engine, detector, router, manager, or similar runtime component
- **THEN** the design MUST explain why the behavior cannot be represented through the existing Xiang-Ye primitives

#### Scenario: Behavior can be represented as a job or law
- **WHEN** the behavior can be expressed as a job, law, method, evidence item, appearance, or mirror projection
- **THEN** the implementation MUST use that primitive instead of adding another orchestration component

### Requirement: Truth alignment definition of done
A runtime change MUST NOT be reported complete until verification evidence shows the code preserves truth-source invariants.

#### Scenario: Change completion
- **WHEN** a coding task changes runtime or orchestration behavior
- **THEN** the final verification MUST include evidence for job-only state changes, candidate isolation, evidence-backed results, responsibility-scoped completion, and hardcoding scan status

### Requirement: Proxy fallback stays operational configuration
GitHub synchronization MUST support both current and legacy local proxy ports through operational configuration or explicit fallback commands, without encoding a single mutable proxy port as reusable runtime truth.

#### Scenario: Current proxy is available
- **WHEN** `127.0.0.1:7897` can reach GitHub
- **THEN** repository synchronization MAY use that proxy without changing runtime code

#### Scenario: Legacy proxy is available
- **WHEN** `127.0.0.1:7890` can reach GitHub
- **THEN** repository synchronization MAY use that proxy without changing runtime code

#### Scenario: Proxy port changes again
- **WHEN** the local proxy port changes
- **THEN** the reusable Jingu runtime MUST NOT require code modification to synchronize or run AI tasks
