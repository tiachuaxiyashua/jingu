## ADDED Requirements

### Requirement: Process Step Trace
The AI sandbox SHALL emit readable process-step events that identify the runtime phase, action, status, and relevant runtime identifiers for one-shot runs and chat turns.

#### Scenario: One-shot run process is visible
- **WHEN** an AI sandbox run receives input, initializes runtime state, loads a method, creates a job, calls the AI provider, records candidate/evidence, and records output
- **THEN** the flow log contains process-step events that show those phases in chronological order.

#### Scenario: Chat turn process is visible
- **WHEN** an interactive AI sandbox chat turn processes a user input
- **THEN** the flow log contains process-step events scoped to that turn.

### Requirement: Input Provenance Trace
The AI sandbox SHALL emit input-provenance events before provider calls so a human can distinguish a fresh task instruction from a prompt that already contains a large embedded artifact.

#### Scenario: Input statistics are recorded
- **WHEN** the sandbox records user input
- **THEN** the flow log records input source, character count, line count, SHA-256 digest, and generic structure flags.

#### Scenario: Provenance remains generic
- **WHEN** input contains Markdown headings or fenced blocks
- **THEN** the provenance event records generic structure flags without domain-specific interpretation or hardcoded artifact names.

### Requirement: Existing Raw Logs Are Preserved
The process trace SHALL NOT replace full raw input, output, candidate, evidence, job-tree, or method-review events.

#### Scenario: Existing evidence remains available
- **WHEN** a sandbox run completes
- **THEN** the log still contains raw user input, provider response, candidate submission, evidence submission, result output, and sandbox cleanup events.
