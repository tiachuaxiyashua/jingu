## ADDED Requirements

### Requirement: Chat uses shared acceptance routing
The AI chat session SHALL use the same verification-aware acceptance-routing helper as `ai run`.

#### Scenario: Chat turn completes candidate verification
- **WHEN** a chat turn has produced a latest candidate, verification report, and repair summary
- **THEN** the chat session MUST route that evidence through the shared acceptance router instead of judging only the raw assistant response.

### Requirement: Chat history follows routed candidate
The AI chat session SHALL keep conversation history aligned with the latest candidate returned by repair routing.

#### Scenario: Acceptance router repairs a chat candidate
- **WHEN** the acceptance router creates an executor repair and receives a revised candidate
- **THEN** the chat session MUST store the revised candidate as the latest assistant turn for future context.
