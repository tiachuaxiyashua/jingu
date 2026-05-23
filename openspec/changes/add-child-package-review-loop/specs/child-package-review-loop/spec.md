## ADDED Requirements

### Requirement: Sandbox reviews child result packages independently
The AI sandbox SHALL run an independent review step for submitted child result packages before making them consumable by the parent job.

#### Scenario: Review child package after submission
- **WHEN** a frontier child job submits a structured result package candidate
- **THEN** the sandbox calls an independent review provider with the child job contract, package, evidence, parent context, and requested review schema

#### Scenario: Invalid review response
- **WHEN** the review provider returns invalid JSON or misses required review fields
- **THEN** the sandbox records review rejection and MUST NOT accept the child job or parent job

### Requirement: Sandbox accepts reviewed child packages through the runtime service
The AI sandbox SHALL accept a child result package only through the runtime service when the independent review returns a valid accept judgment.

#### Scenario: Accept child package
- **WHEN** a child package review returns action `accept` with checks, evidence, and parent consumption summary
- **THEN** the sandbox accepts the child job candidate through the runtime service and records child package acceptance

#### Scenario: Parent sees accepted child package
- **WHEN** a child package has been accepted
- **THEN** the sandbox records parent re-evaluation showing accepted child results and any unresolved children or open questions

### Requirement: Sandbox creates repair jobs for reviewed child package failures
The AI sandbox SHALL create a repair child job when a child package review returns a valid repair judgment.

#### Scenario: Repair child package
- **WHEN** a child package review returns action `repair` with a repair instruction
- **THEN** the sandbox rejects the current child candidate, creates a repair job under the child job, starts the repair job, and calls the provider with the repair instruction

#### Scenario: Re-submit repaired package
- **WHEN** the repair provider returns a valid result package
- **THEN** the sandbox submits the repaired package back to the original child job and runs the child package review again

#### Scenario: Repair remains invalid
- **WHEN** the repaired package is invalid or the second review does not accept it
- **THEN** the sandbox records the failure and MUST NOT mark the child, parent, or root job complete

### Requirement: Sandbox limits child package repair recursion
The AI sandbox SHALL limit child package repair recursion to prevent unbounded provider calls.

#### Scenario: Repair limit reached
- **WHEN** a child package has already used the configured repair attempt
- **THEN** the sandbox records the repair limit outcome and leaves the child package unresolved rather than requesting another repair
