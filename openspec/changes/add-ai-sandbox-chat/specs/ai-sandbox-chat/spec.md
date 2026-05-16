## ADDED Requirements

### Requirement: AI configuration loading
The system SHALL load DeepSeek AI runtime configuration from `.env.deepseek.local` without hardcoding API keys, provider URLs, or model names.

#### Scenario: Load valid configuration
- **WHEN** `.env.deepseek.local` contains the required DeepSeek settings
- **THEN** the system loads the API key, base URL, and model from that file

#### Scenario: Reject missing configuration
- **WHEN** a required DeepSeek setting is missing
- **THEN** the system MUST fail before making a provider request

### Requirement: Interactive AI chat command
The system SHALL provide an AI chat command where the user can conduct a multi-turn conversation for task requests and human decisions.

#### Scenario: Start interactive chat
- **WHEN** the user starts the AI chat command
- **THEN** the command creates a sandbox, initializes the Jingu workflow, and waits for user input

#### Scenario: Complete a chat turn
- **WHEN** the user enters a task request or decision
- **THEN** the command calls the configured AI provider with conversation context, drives the Jingu workflow for that turn, prints the AI reply in the chat CLI, and waits for the next input

#### Scenario: Exit interactive chat
- **WHEN** the user enters an exit command
- **THEN** the command writes session completion events, destroys the sandbox, and exits

### Requirement: Ephemeral sandbox lifecycle
The system SHALL create runtime state inside a sandbox for each AI chat session and destroy that sandbox when the chat session exits.

#### Scenario: Sandbox is removed after session exit
- **WHEN** an AI chat session exits normally
- **THEN** the sandbox directory no longer exists

#### Scenario: Sandbox is removed after failure
- **WHEN** an AI chat session fails after creating the sandbox
- **THEN** the sandbox directory no longer exists

### Requirement: Real-time flow monitor
The system SHALL provide a separate monitor command that prints AI sandbox flow events in real time without requiring the run command to print those events.

#### Scenario: Monitor active run
- **WHEN** the monitor command is watching a sandbox while an AI run is active
- **THEN** it prints lifecycle events as the run writes them

#### Scenario: Monitor exits after chat finishes
- **WHEN** the chat session writes a finished event or removes the sandbox
- **THEN** the monitor exits without leaving monitor state behind

### Requirement: Persistent diagnostic log
The system SHALL persist a JSONL diagnostic log outside the ephemeral sandbox for each AI chat session, including all user inputs, AI outputs, provider request and response summaries, kernel transitions, failures, and cleanup events.

#### Scenario: Log survives sandbox cleanup
- **WHEN** an AI chat session completes and destroys its sandbox
- **THEN** the diagnostic log file still exists outside the sandbox

#### Scenario: Log records input and output
- **WHEN** an AI chat turn receives a user message and produces an AI answer
- **THEN** the diagnostic log contains the user input event and result output event

#### Scenario: Log excludes secrets
- **WHEN** the diagnostic log records provider activity
- **THEN** the log MUST NOT contain API keys or authorization headers

### Requirement: Jingu workflow integration
Each AI chat turn SHALL drive the existing runtime kernel through root job creation, ready, running, candidate submission, evidence submission, and acceptance.

#### Scenario: Accepted job from AI response
- **WHEN** the configured AI provider returns a response
- **THEN** the sandbox workflow stores the response as a candidate result, stores provider-return evidence, accepts the candidate, and records the event flow

### Requirement: One-click scripts
The system SHALL provide a one-click script that opens the chat CLI and monitor CLI as two separate terminal windows sharing the same sandbox and log directory.

#### Scenario: Launcher opens two CLIs
- **WHEN** the user invokes the one-click script
- **THEN** the script opens one terminal for interactive AI chat and one terminal for real-time monitoring

#### Scenario: Shared session paths
- **WHEN** the one-click script starts both terminals
- **THEN** both terminals use the same sandbox path and log directory
