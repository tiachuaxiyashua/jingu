## Why

Current AI sandbox requests wait for one complete provider response, so a slow reasoning model can hit a read timeout even when it would have emitted streaming thinking or content. Current method execution also injects the whole method file as one system message, which makes Neidan Method behave like a large prompt blob instead of a set of reusable `法` fragments bound to a `业`.

## What Changes

- Add streaming OpenAI-compatible chat completion support with a configurable stream idle timeout. Timeout during streaming is based on lack of emitted provider content, not total thinking duration.
- Add a generic provider request body extension field so model-specific thinking/reasoning controls can come from local configuration instead of code.
- Parse a method source into checksumed method-law fragments without hardcoding Neidan Method section names.
- Register method-law fragments as `相` under the current job and record the binding before provider calls.
- Inject method-law fragments as separate provider messages with a manifest and fragment identifiers instead of one full method-file message.
- Log provider stream deltas, method-law manifests, fragment loading, and fragment-to-job binding in JSONL and readable Markdown logs.

## Capabilities

### New Capabilities

- `streaming-ai-provider`: Streaming provider calls, stream progress logging, and configurable idle timeout for long thinking runs.
- `law-driven-method-source`: Method source parsing into reusable method-law fragments, job binding, provider injection, and method trace evidence.

### Modified Capabilities

None. The archived OpenSpec spec set is currently empty; this change supersedes behavior introduced by active unarchived changes without editing archived capabilities.

## Impact

- Affects `jingu/ai/config.py` and `jingu/ai/client.py` provider configuration and request execution.
- Affects `jingu/sandbox/method.py`, `jingu/sandbox/runner.py`, and `jingu/sandbox/flow.py` method loading, logging, and provider message assembly.
- Affects runtime constants and service code to represent method-law fragments as appearances.
- Affects sandbox tests and OpenSpec validation.
