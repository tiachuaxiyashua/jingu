## ADDED Requirements

### Requirement: Method source resolution
The sandbox AI task loop SHALL resolve a method source before sending any task request to the AI provider.

#### Scenario: Explicit method path
- **WHEN** the user starts `ai run` or `ai chat` with `--method <path>`
- **THEN** the sandbox loads that method file and uses it for the task turn.

#### Scenario: Repository method pointer
- **WHEN** no explicit method path is supplied and the repository method pointer exists
- **THEN** the sandbox resolves the method path from the pointer file and loads that method.

#### Scenario: Missing method source
- **WHEN** no explicit method path is supplied and no valid method pointer can be resolved
- **THEN** the sandbox fails before calling the AI provider instead of running as a bare model request.

### Requirement: Method context injection
The sandbox AI task loop SHALL inject the loaded method content into the AI request as explicit system context.

#### Scenario: AI request includes method context
- **WHEN** the user submits a task instruction
- **THEN** the AI provider request contains a system message with the loaded method name, source path, checksum, and full method content.

### Requirement: Observable method flow
The sandbox AI task loop SHALL record method loading and method usage events in both the live monitor stream and the persistent diagnostic log.

#### Scenario: Method flow is logged
- **WHEN** a task turn is executed
- **THEN** the flow includes events for method source resolution, method content loading, method context injection, method self-review request, method self-review response, and method update-candidate recording.

### Requirement: Method self-review evidence
The sandbox AI task loop SHALL request a method self-review after each AI candidate result and store the self-review as evidence without automatically accepting, rejecting, or editing the method.

#### Scenario: Self-review is evidence only
- **WHEN** the AI returns a task candidate response
- **THEN** the sandbox records a method self-review response and submits evidence containing the method reference, checksum, and self-review content while leaving candidate acceptance to later explicit runtime action.

### Requirement: One-click method-driven session
The one-click PowerShell launcher SHALL open both the task/chat CLI and monitor CLI so that the task CLI can use the configured method and the monitor CLI can display the complete method-driven flow.

#### Scenario: Launcher dry run shows method-driven commands
- **WHEN** the launcher is run with `-DryRun`
- **THEN** it prints the chat command, monitor command, sandbox path, log directory, and method source that will be used.
