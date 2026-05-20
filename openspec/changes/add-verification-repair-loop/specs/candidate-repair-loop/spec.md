## ADDED Requirements

### Requirement: Repair job creation from failed verification
The AI sandbox SHALL create explicit repair child jobs for failed deterministic verification results that contain repairable check failures and have remaining repair attempts.

#### Scenario: Repairable verification failure
- **WHEN** a candidate verification report has overall status `failed`, contains at least one repairable failed check, and the configured repair attempt limit has not been reached
- **THEN** the system MUST create a child repair job linked to the candidate-producing job before requesting a revised candidate.

#### Scenario: No repair for unsupported verification
- **WHEN** a candidate verification report has overall status `unsupported`
- **THEN** the system MUST NOT create a repair job from that report.

### Requirement: Repair prompt carries evidence
The repair request SHALL include the original task, previous candidate, deterministic verification report, failed check facts, and instruction to preserve the user's intent while correcting concrete failures.

#### Scenario: Provider receives repair request
- **WHEN** the system asks the configured AI provider for a repair candidate
- **THEN** the provider request MUST be derived from recorded task/candidate/evidence data and MUST NOT embed domain-specific criteria that were not present in the task or verification report.

### Requirement: Repair candidate isolation
Each repair candidate SHALL be submitted as a candidate result on the repair job and verified by a separate verification child job.

#### Scenario: Repair candidate produced
- **WHEN** the configured AI provider returns a repair candidate
- **THEN** the system MUST record it as a candidate on the repair job, run candidate verification for that repair job, and attach the verification evidence to the repair job.

### Requirement: Bounded repair loop
The repair loop SHALL stop when verification passes, when no repairable failure remains, or when the configured attempt limit is exhausted.

#### Scenario: Repair verification passes
- **WHEN** a repair candidate verification report has overall status `passed`
- **THEN** the system MUST stop repair attempts and return the repair candidate as the latest candidate output without accepting or rejecting the parent candidate.

#### Scenario: Repair attempts exhausted
- **WHEN** every configured repair attempt has been used and the latest verification report is still failed or unsupported
- **THEN** the system MUST stop provider repair calls and route the unresolved evidence to a feedback-decision job.

### Requirement: Feedback-decision job for unresolved verification
The AI sandbox SHALL create a feedback-decision child job when verification evidence cannot be resolved by the bounded repair loop.

#### Scenario: Unresolved failure remains
- **WHEN** the repair loop stops because the failure is not repairable, unsupported, or still failing after the attempt limit
- **THEN** the system MUST create a child job that records the unresolved verification report, repair attempts used, and why further autonomous repair did not continue.

### Requirement: Repair observability
The repair loop SHALL be visible in JSONL logs, readable Markdown logs, and job-tree snapshots.

#### Scenario: Repair loop runs
- **WHEN** a repair job is created, receives a provider response, submits a candidate, verifies it, or creates a feedback-decision job
- **THEN** the flow log MUST include the event, affected job id, parent/root linkage, attempt number, and compact evidence summary.
