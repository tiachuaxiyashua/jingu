## ADDED Requirements

### Requirement: Sandbox integrates accepted child packages into parent candidates
The AI sandbox SHALL run a parent integration step when accepted child result packages are available under a parent job.

#### Scenario: Integrate accepted child packages
- **WHEN** a parent job has one or more accepted child result packages after child package review
- **THEN** the sandbox calls a parent integrator provider with the parent contract, accepted child package references, evidence summaries, root candidate, and requested integration schema

#### Scenario: Skip without accepted child packages
- **WHEN** a parent job has no accepted child result packages
- **THEN** the sandbox records that parent integration was skipped and MUST NOT submit a parent integration candidate

### Requirement: Parent integration submits candidate and evidence without accepting parent
The AI sandbox SHALL submit valid parent integration output as a parent job candidate with evidence while preserving candidate isolation.

#### Scenario: Valid parent integration output
- **WHEN** the parent integrator returns a valid JSON object with integrated candidate text, consumed child jobs, evidence, open gaps, and suggested follow-up jobs
- **THEN** the sandbox submits the integrated candidate and evidence to the parent job and records parent integration completion

#### Scenario: Parent remains unaccepted
- **WHEN** a parent integration candidate is submitted
- **THEN** the sandbox MUST NOT mark the parent job or root job accepted solely because integration succeeded

#### Scenario: Invalid parent integration output
- **WHEN** the parent integrator returns invalid JSON or misses required fields
- **THEN** the sandbox records parent integration rejection and MUST NOT submit a parent integration candidate

### Requirement: Parent integration can propose follow-up jobs through gatekeeper
The AI sandbox SHALL allow parent integration output to expose follow-up work only through the existing split proposal registration path.

#### Scenario: Follow-up work after integration
- **WHEN** the parent integration candidate exposes unresolved blocking work
- **THEN** the sandbox may run split proposal registration on the integration candidate and leave accepted or rejected proposals visible in logs
