## ADDED Requirements

### Requirement: Acceptance routing after verification
The AI sandbox SHALL run a shared AI acceptance-routing step after candidate generation, deterministic verification, and any bounded deterministic repair loop.

#### Scenario: Candidate path completes
- **WHEN** an `ai run` or `ai chat` candidate path has a latest candidate, verification report, and repair summary
- **THEN** the system MUST ask the configured AI provider for an acceptance-routing judgment before recording the final result output.

### Requirement: Routing judgment contract
The acceptance router SHALL return a structured route that chooses one of: continue without feedback, repair by executor, or feedback/decision job.

#### Scenario: Router chooses continue
- **WHEN** the router judges that no semantic repair, directional correction, or high-value decision is needed
- **THEN** the system MUST record the skip judgment as evidence and MUST NOT create a repair or feedback child job.

#### Scenario: Router chooses executor repair
- **WHEN** the router judges that the candidate has a repairable issue that does not require human value裁决
- **THEN** the system MUST create a repair child job, request a revised candidate from the configured AI provider, submit that candidate on the repair job, and verify it.

#### Scenario: Router chooses feedback decision
- **WHEN** the router judges that the candidate exposes a high-value or directional decision point
- **THEN** the system MUST create a feedback child job with required context gaps and evidence from the routing judgment.

### Requirement: Routing evidence payload
The acceptance-routing request SHALL include the original task, latest candidate, deterministic verification evidence, repair-loop summary, and any known unresolved gaps.

#### Scenario: Provider receives routing request
- **WHEN** the system calls the provider for acceptance routing
- **THEN** the provider request MUST be derived from recorded task/candidate/evidence data and MUST NOT embed domain-specific acceptance rules that were not present in the task, method, or verification evidence.

### Requirement: Acceptance repair remains bounded
The acceptance router SHALL NOT create an unbounded semantic repair loop.

#### Scenario: Semantic repair is requested
- **WHEN** the router chooses executor repair
- **THEN** the system MUST perform at most one acceptance-role repair attempt for that completed candidate path before returning the latest candidate and recording evidence.

### Requirement: Routing observability
The acceptance-routing flow SHALL be visible in JSONL logs, readable Markdown logs, and job-tree snapshots.

#### Scenario: Acceptance routing runs
- **WHEN** a routing request is prepared, a routing judgment is received, a repair job is created, a feedback job is created, or a route is skipped
- **THEN** the flow log MUST include the route action, affected job id, parent/root linkage, compact evidence summary, and no-auto-accept/no-auto-reject marker.
