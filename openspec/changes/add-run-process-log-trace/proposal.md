## Why

The AI sandbox readable log currently records low-level events, but it does not clearly show the run pipeline as a human-auditable process. A generated artifact can be pasted back into the next prompt, and the readable log will still look like a normal generation run unless the reader manually notices that the user input already contained a completed artifact.

For Jingu, this is not enough. A human should be able to inspect the saved log and answer:

- What did Jingu do before the provider call?
- What source did the user input come from?
- Did the input already contain a large artifact?
- Which runtime phase produced the candidate, evidence, self-review, and final output?

## What Changes

- Add generic process-trace flow events to AI sandbox run and chat paths.
- Add input-provenance flow events that record input source, length, line count, digest, and generic structure signals.
- Keep full user input and provider response logging unchanged.
- Keep process tracing generic; do not hardcode Neidan Method, fiction writing, or any domain-specific workflow into the logging layer.

## Capabilities

### New Capabilities

- `run-process-log-trace`: Covers readable AI sandbox logging of run phases and input provenance.

### Modified Capabilities

None.

## Impact

- Affected code: `jingu/sandbox/flow.py`, `jingu/sandbox/runner.py`, focused sandbox tests.
- Affected behavior: persisted Markdown logs and monitor output become clearer about Jingu's runtime process and whether a prompt already contained a large artifact.
- No external dependency changes.
