## Context

The current sandbox flow already persists JSONL events and a Chinese Markdown mirror. The missing part is not persistence; it is process legibility. Existing events are useful to a developer who already knows the code path, but they do not give a human a clean run narrative.

The specific failure that motivated this change: a story-generation log showed the user input already containing a completed story, because that run was actually a later rewrite/evaluation attempt. The log was technically faithful, but it was not mature enough to make that provenance obvious.

## Design

### Process Step Events

Add a generic `process_step_recorded` event. Each event records:

- `process_step`: stable step id.
- `process_phase`: broad phase such as input, runtime, method, job, provider, evidence, output, cleanup.
- `process_action`: human-readable action summary.
- `process_status`: started, completed, failed, or skipped.
- optional `turn`, `job_id`, `message_count`, and relevant paths or ids.

These events are a mirror of the run pipeline, not a new execution engine.

### Input Provenance Events

Add a generic `input_provenance_recorded` event. It records:

- `input_source`: where the runtime received the input from.
- `input_character_count`
- `input_line_count`
- `input_sha256`
- `input_has_markdown_heading`
- `input_has_fenced_block`

The provenance detector intentionally avoids domain terms like "novel", "Neidan", or "complete artifact". It records generic structural signals and leaves interpretation to the human.

### Scope

Apply this to:

- one-shot `ai run`
- interactive `ai chat` turns

Do not change runtime job semantics, feedback-job judgment semantics, or method behavior.

## Risks

- Extra log volume: mitigated by compact event payloads.
- False certainty: provenance events are structural observations, not judgments.
- Hardcoding drift: keep fields generic and avoid domain-specific detection.
