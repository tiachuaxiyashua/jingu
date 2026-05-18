## 1. Provider Streaming

- [x] 1.1 Add AI configuration fields for streaming, stream idle timeout, and extra request body JSON.
- [x] 1.2 Implement OpenAI-compatible SSE streaming in the chat client with progress callbacks and clear idle-timeout failures.
- [x] 1.3 Log provider stream deltas and stream completion from sandbox runs, chat turns, self-review, and feedback judgment calls.

## 2. Method-Law Fragment Runtime

- [x] 2.1 Parse method sources into generic method-law fragments without hardcoded Neidan Method section names.
- [x] 2.2 Bind method-law fragments to the current job as appearances and runtime events.
- [x] 2.3 Replace single full-file method injection with a manifest plus separate method-law fragment messages.
- [x] 2.4 Include method-law fragment trace requests in method self-review and evidence payloads.

## 3. Verification

- [x] 3.1 Update unit tests for streaming config, streaming parsing, fragment parsing, fragment binding, logs, and provider message shape.
- [x] 3.2 Run OpenSpec validation, unit tests, compile check, and hardcoding scan.
