## Why

The method-driven sandbox now records the right information, but the persisted log is only machine-oriented JSONL and can display Chinese incorrectly in common Windows viewers. A validation loop that depends on human diagnosis needs a readable, UTF-8-safe log projection alongside the event ledger.

## What Changes

- Add a human-readable Markdown diagnostic log for every AI sandbox run.
- Write the readable log with a UTF-8 BOM so Windows editors reliably recognize Chinese text.
- Keep the existing JSONL log as the machine-readable event ledger.
- Add a latest-readable-log pointer next to the existing latest JSONL pointer.
- Include the readable log path in sandbox lifecycle events and launcher output.
- Format monitor output with multiline blocks for large values instead of one long inline record.
- Configure the PowerShell launcher process output to UTF-8.

## Capabilities

### New Capabilities

- `ai-sandbox-readable-logs`: Human-readable, UTF-8-safe sandbox diagnostics with readable live monitor projection.

### Modified Capabilities

None.

## Impact

- Extends `jingu.sandbox.flow` with readable log path generation and Markdown rendering.
- Extends sandbox runners to create and point to both machine and human logs.
- Extends CLI monitor formatting.
- Updates PowerShell launcher encoding setup.
- Adds tests for readable log creation, Chinese preservation, pointer writing, and monitor formatting.
