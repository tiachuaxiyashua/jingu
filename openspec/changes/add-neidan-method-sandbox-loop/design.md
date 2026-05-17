## Context

The current sandbox opens a disposable runtime, sends the user message to the configured AI provider, records the provider response as a candidate, submits weak provider-response evidence, and logs the flow. This is observable, but it does not prove that the task was advanced by any Jingu method. The user cannot inspect whether Neidan Method was loaded, injected, followed, or where it failed.

The truth source requires `法` to be a reusable capability, not a hardcoded verdict loop or hidden prompt habit. The first useful implementation should therefore treat the method as a configurable source file loaded into the sandbox task turn, not as a new engine branch named after one method.

## Goals / Non-Goals

**Goals:**

- Load a method file for each sandbox AI task turn.
- Provide a repository-level method pointer so the one-click launcher can load Neidan Method without embedding the method path in reusable runtime code.
- Inject the method content into the AI request as explicit system context.
- Log method source, checksum, full content, context injection, AI response, method self-review request/response, and method update candidates.
- Keep user-facing task CLI output focused on the AI result while the monitor and persistent log show the full flow.
- Keep all runtime state inside the disposable sandbox and all diagnostic logs outside it.

**Non-Goals:**

- Do not promote Neidan Method into a stable runtime law.
- Do not automatically edit the method file.
- Do not automatically accept/reject task candidates.
- Do not create a dedicated physical table for methods.
- Do not build a UI or long-running daemon.

## Decisions

### Resolve Method Source Through Configuration

The sandbox will accept `--method <path>`. If omitted, it resolves a repository-local method pointer file whose content is a method path. This keeps the default Neidan Method selection configurable data rather than a reusable-code branch. A missing method path is a startup error because a method-driven sandbox turn without a method would recreate the bare-model failure.

### Treat Method Content As Task Context And Evidence

Each task turn loads the method file, computes its checksum, logs the full content once for that turn, and injects the content into the AI request as a system message. The response is submitted as the candidate result. Evidence is upgraded from a fixed `provider_response_received` token to a structured record containing the method path, checksum, provider response fact, and method self-review output.

### Use Generic Method Self-Review

After the candidate response, the sandbox asks the AI for a method self-review using a generic schema: method-use summary, evidence, gaps, observed failure modes, and method update candidates. The review does not change method state or candidate status; it is logged and stored as evidence so the user can diagnose where the loop failed and manually update the method.

### Keep Existing Two-CLI Shape

The one-click PowerShell script still opens a task/chat CLI and a monitor CLI against the same sandbox and log directory. The task CLI prints the answer. The monitor CLI prints every flow event and data payload, including inputs, method content, AI outputs, self-review, and cleanup.

## Risks / Trade-offs

- Method content can make logs large -> The user explicitly needs full visibility for debugging; logs stay outside source control.
- AI self-review can be wrong -> It is recorded as weak evidence and update-candidate material, not as truth or automatic method mutation.
- Default pointer can point to a missing file -> Startup fails clearly and logs the failure, preventing silent bare-model execution.
- Prompt injection inside a method file could steer the provider -> The method source is local project data chosen by the user; future versions can add method trust levels and signed references.

## Migration Plan

1. Add repository method pointer data for the current default method.
2. Add method loading and checksum support.
3. Extend sandbox flow events and evidence payloads.
4. Extend CLI and launcher arguments.
5. Add tests and run validation, hardcoding scan, and manual launcher dry-run.
