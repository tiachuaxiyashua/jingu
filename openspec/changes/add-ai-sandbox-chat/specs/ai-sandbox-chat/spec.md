## ADDED Requirements

### Requirement: AI configuration loading
The system SHALL load DeepSeek AI runtime configuration from `.env.deepseek.local` without hardcoding API keys, provider URLs, or model names.

#### Scenario: Load valid configuration
- **WHEN** `.env.deepseek.local` contains the required DeepSeek settings
- **THEN** the system loads the API key, base URL, and model from that file

#### Scenario: Reject missing configuration
- **WHEN** a required DeepSeek setting is missing
- **THEN** the system MUST fail before making a provider request

### Requirement: Result-only AI run command
The system SHALL provide an AI run command that prints only the final AI response to standard output on success.

#### Scenario: Run minimal AI chat
- **WHEN** the user runs the AI command with a message
- **THEN** the command creates a sandbox, runs the Jingu workflow, calls the configured AI provider, accepts the result with evidence, prints only the final answer, and exits successfully

#### Scenario: Runtime status is not mixed into result output
- **WHEN** the AI run command executes successfully
- **THEN** lifecycle status messages MUST NOT be printed to standard output

### Requirement: Ephemeral sandbox lifecycle
The system SHALL create runtime state inside a sandbox for each AI run and destroy that sandbox when the run exits.

#### Scenario: Sandbox is removed after success
- **WHEN** an AI run completes successfully
- **THEN** the sandbox directory no longer exists

#### Scenario: Sandbox is removed after failure
- **WHEN** an AI run fails after creating the sandbox
- **THEN** the sandbox directory no longer exists

### Requirement: Real-time flow monitor
The system SHALL provide a separate monitor command that prints AI sandbox flow events in real time without requiring the run command to print those events.

#### Scenario: Monitor active run
- **WHEN** the monitor command is watching a sandbox while an AI run is active
- **THEN** it prints lifecycle events as the run writes them

#### Scenario: Monitor exits after run finishes
- **WHEN** the run writes a finished event or removes the sandbox
- **THEN** the monitor exits without leaving monitor state behind

### Requirement: Persistent diagnostic log
The system SHALL persist a JSONL diagnostic log outside the ephemeral sandbox for each AI run, including workflow inputs, outputs, provider request and response summaries, kernel transitions, failures, and cleanup events.

#### Scenario: Log survives sandbox cleanup
- **WHEN** an AI run completes and destroys its sandbox
- **THEN** the diagnostic log file still exists outside the sandbox

#### Scenario: Log records input and output
- **WHEN** an AI run receives a user message and produces an AI answer
- **THEN** the diagnostic log contains the user input event and result output event

#### Scenario: Log excludes secrets
- **WHEN** the diagnostic log records provider activity
- **THEN** the log MUST NOT contain API keys or authorization headers

### Requirement: Jingu workflow integration
The AI sandbox run SHALL drive the existing runtime kernel through root job creation, ready, running, candidate submission, evidence submission, and acceptance.

#### Scenario: Accepted job from AI response
- **WHEN** the configured AI provider returns a response
- **THEN** the sandbox workflow stores the response as a candidate result, stores provider-return evidence, accepts the candidate, and records the event flow

### Requirement: One-click scripts
The system SHALL provide script entry points for running the AI sandbox and monitoring the current sandbox.

#### Scenario: Run script starts AI sandbox
- **WHEN** the user invokes the run script with a message
- **THEN** the script starts the AI sandbox command and prints only the final answer

#### Scenario: Monitor script tails status
- **WHEN** the user invokes the monitor script
- **THEN** the script tails the current sandbox flow until completion
