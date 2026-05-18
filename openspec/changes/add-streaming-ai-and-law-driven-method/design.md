## Context

The current sandbox uses a single blocking chat completion request. That is acceptable for short non-reasoning answers, but it is brittle for models that emit reasoning or long generation through an SSE stream. A read timeout before the final response gives the human no visibility into whether the provider was idle, thinking, or already emitting partial content.

The current method path loads `SKILL.md`, logs it, and injects the whole file into one system message. That made the first method-driven loop observable, but it does not match the truth source: `法` is a reusable capability, `相` is a stable referable object, and `业` should bind the capability it uses. The next step should convert method source into smaller method-law fragments that can be referenced, bound, logged, and inspected without creating a dedicated physical method table.

## Goals / Non-Goals

**Goals:**

- Support provider streaming while keeping provider/model truth in `.env.deepseek.local`.
- Treat stream timeout as an idle timeout: emitted reasoning or content counts as progress and keeps the request alive.
- Allow model-specific thinking/reasoning request knobs through a config JSON object, without hardcoding those knobs in runtime code.
- Parse method markdown generically into method-law fragments with ids, titles, levels, order, checksums, and content.
- Store/bind method-law fragments as appearances for each job and log the full binding trail.
- Inject a compact method manifest plus separate law-fragment messages into provider calls.
- Require method self-review to report which method-law fragments were used or failed.

**Non-Goals:**

- Do not build a full durable law scheduler or method library table.
- Do not hardcode Neidan Method section names, step names, model names, or thinking parameter names.
- Do not auto-promote candidate method updates into stable law.
- Do not auto-accept or reject task candidates.

## Decisions

### Streaming Is Configurable But Enabled By Default

DeepSeek-compatible chat calls will include `stream: true` by default, with `DEEPSEEK_STREAM=false` as an escape hatch for provider profiles that cannot stream. The stream idle timeout is configured by `DEEPSEEK_STREAM_IDLE_TIMEOUT_SECONDS` and defaults longer than the non-stream request timeout. This directly addresses reasoning models while preserving local configuration ownership.

Alternative considered: only increase `DEEPSEEK_TIMEOUT_SECONDS`. That still gives no partial output visibility and still times out long but active streams.

### Provider-Specific Thinking Controls Come From JSON Config

Runtime code will support a `DEEPSEEK_EXTRA_BODY_JSON` object merged into the request body, while protecting runtime-owned keys such as messages, model, stream, and temperature. This allows the user to configure current or future thinking/reasoning fields without writing provider-specific branches into code.

Alternative considered: add explicit `DEEPSEEK_THINKING` or `DEEPSEEK_REASONING_EFFORT` fields. That would prematurely encode one provider's vocabulary.

### Method Markdown Becomes Generic Method-Law Fragments

The parser will split markdown by headings. Each heading section becomes a method-law fragment with deterministic metadata and a checksum. The implementation will not know that a section is named "总循环" or "工作流程"; those titles remain data from the method source.

Alternative considered: create a hand-authored Neidan Method manifest. That would be cleaner long term, but it would hardcode the current method shape before the method has stabilized.

### Bind Fragments As Appearances, Not A New Table

Each fragment is stored as an `appearance` with a method-law-fragment type and metadata, and the current job receives a binding event. This follows the truth source's first-version constraint: semantic objects such as `法` can begin as appearance classes and events rather than new physical tables.

Alternative considered: add method/law tables. That is heavier than needed for the current validation loop and would make the simple sandbox harder to inspect.

## Risks / Trade-offs

- Streaming can create large logs -> log deltas are required for diagnosis; logs remain outside source control.
- SSE dialects vary across providers -> implement OpenAI-compatible parsing and keep non-stream fallback configurable.
- Splitting markdown by headings is only a structural approximation of `法` -> fragments are explicit and reviewable, and future feedback can replace the parser with a manifest format.
- AI self-review may claim fragment usage incorrectly -> the trace is evidence material, not truth or acceptance.
- Extra request JSON can be misconfigured -> protected keys are rejected before provider calls so runtime-owned fields cannot be overridden silently.

## Migration Plan

1. Add configuration fields for streaming, stream idle timeout, and extra request body JSON.
2. Add streaming response parsing and stream event callbacks.
3. Add method-law fragment parsing, logging, and job binding.
4. Replace single method-system-message injection with manifest plus fragment messages.
5. Update evidence and tests, then run OpenSpec validation, unit tests, compile checks, and hardcoding scan.
