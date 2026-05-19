## ADDED Requirements

### Requirement: Independent verification job
The AI sandbox SHALL create an independent child verification job after submitting an AI candidate result when deterministic checks can be performed.

#### Scenario: Candidate is submitted
- **WHEN** an AI sandbox run or chat turn submits a candidate result
- **THEN** the system MUST create a child verification job linked to the candidate-producing parent job before reporting the turn as finished.

### Requirement: Deterministic text verification
The verification job SHALL run a tool-backed deterministic verifier for supported text constraints instead of relying on AI self-review.

#### Scenario: User task contains a CJK length range
- **WHEN** the user task includes a verifiable Chinese text length range and the candidate contains a text deliverable
- **THEN** the verifier MUST count actual CJK characters in the deliverable and report pass or fail against the range.

#### Scenario: Candidate contains output markers
- **WHEN** the candidate contains a complete marker-delimited region
- **THEN** the verifier MUST count the marked region and report which markers were used.

#### Scenario: Candidate has no supported deterministic checks
- **WHEN** the verifier cannot extract any supported deterministic check
- **THEN** it MUST still submit evidence that no supported hard check was available and list unsupported verification gaps.

### Requirement: Verification evidence回流
The verification result SHALL be stored as evidence on the verification child job and summarized as evidence on the parent job.

#### Scenario: Verification completes
- **WHEN** deterministic verification finishes
- **THEN** the verification child job MUST receive candidate/evidence records for the verification report, and the parent job MUST receive evidence referencing the verification child job and result.

### Requirement: Verification observability
The verification flow SHALL be visible in JSONL logs, readable Markdown logs, and job-tree snapshots.

#### Scenario: Verification job runs
- **WHEN** a verification child job is created, run, and receives evidence
- **THEN** the flow log MUST include verification job creation, tool execution, result, evidence submission, parent evidence回流, and updated job-tree snapshots.

### Requirement: Verification does not auto-accept parent candidate
The verification job SHALL NOT automatically accept or reject the parent candidate.

#### Scenario: Verification passes or fails
- **WHEN** verification returns a pass or fail result
- **THEN** the parent candidate MUST remain a candidate/review item, and acceptance or rejection MUST require a separate responsible action.
