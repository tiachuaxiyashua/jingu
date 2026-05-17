## Why

The current AI sandbox proves that a disposable chat session and full logging can work, but each task is still effectively a bare model request. Jingu needs a minimal method-driven task loop where a user enters a task, the session loads the Neidan Method as explicit method context, the AI uses that method to advance the task, and every method-loading, execution, output, and review signal is visible in live and persisted logs.

## What Changes

- Add a method-driven sandbox task loop that loads a method file before each AI task turn.
- Use the Neidan Method skill file as the default method source for the sandbox, while allowing an explicit `--method` path override.
- Inject the loaded method into the AI request as system context so task execution is not a naked provider call.
- Record method loading, method context injection, method-guided response receipt, method self-review, and method update-candidate events in the sandbox flow and persistent JSONL log.
- Preserve the current one-click two-window workflow: one CLI for task input and result output, one monitor CLI for full internal flow and I/O.
- Keep all sandbox runtime state disposable and all diagnostic logs outside the sandbox.
- Avoid hardcoded task verdicts, method success claims, or Neidan-specific engine branches beyond the configurable default method source.

## Capabilities

### New Capabilities

- `neidan-method-sandbox-loop`: AI sandbox task execution with explicit method loading, method-context injection, observable method use, method self-review, and logged method update candidates.

### Modified Capabilities

None.

## Impact

- Extends `jingu.sandbox` with method source loading and method-driven prompt assembly.
- Extends the AI sandbox runner and chat session with method-related flow events and persistent log fields.
- Extends the CLI and one-click script with a method-file option.
- Adds tests for method loading, AI request context injection, flow logging, and default method path behavior without provider/model hardcoding.
