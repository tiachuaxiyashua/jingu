## ADDED Requirements

### Requirement: Streaming provider requests
The AI client SHALL support OpenAI-compatible streaming chat completion requests while preserving local configuration ownership for provider URL, model, credentials, and provider-specific options.

#### Scenario: Streaming request emits progress
- **WHEN** streaming is enabled and the provider emits reasoning or content deltas
- **THEN** the client MUST accumulate the final answer, expose emitted deltas to the sandbox logger, and avoid treating an active stream as timed out.

#### Scenario: Streaming request can be disabled
- **WHEN** local configuration disables streaming
- **THEN** the client MUST use the existing non-streaming completion request path.

### Requirement: Stream idle timeout
The AI client SHALL use a stream idle timeout for streaming responses and SHALL treat provider-emitted reasoning or content deltas as progress.

#### Scenario: Stream stays active
- **WHEN** provider deltas continue to arrive before the stream idle timeout expires
- **THEN** the request MUST continue until the provider finishes or an actual transport error occurs.

#### Scenario: Stream is idle
- **WHEN** no reasoning or content delta arrives within the configured stream idle timeout
- **THEN** the client MUST fail with a clear timeout error.

### Requirement: Provider-specific request body extension
The AI client SHALL allow local configuration to provide a JSON object of extra provider request body fields without allowing it to override runtime-owned keys.

#### Scenario: Extra body is valid
- **WHEN** local configuration contains a valid extra request body object
- **THEN** the client MUST merge it into the provider request body before sending the request.

#### Scenario: Extra body overrides protected keys
- **WHEN** local configuration tries to override messages, model, stream, or temperature
- **THEN** configuration loading MUST fail before any provider request.

### Requirement: Stream observability
The sandbox SHALL record streaming provider deltas and stream completion in both machine JSONL and readable Markdown logs.

#### Scenario: Provider emits stream deltas
- **WHEN** the provider emits reasoning or content deltas during a sandbox run or chat turn
- **THEN** the flow log MUST include the call kind, job id, turn when available, delta kind, delta index, and delta text.
