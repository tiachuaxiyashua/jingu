## Context

The sandbox already writes JSONL events with UTF-8 text, but JSONL is still a machine ledger. Users need to inspect the run quickly in a normal editor and identify where method loading, AI response, evidence, or cleanup failed. The truth source also treats `镜` as a human-facing projection that must not own truth but must make state readable.

## Goals / Non-Goals

**Goals:**

- Preserve the JSONL log as the durable machine event ledger.
- Add a Markdown readable log as a human-facing projection of the same events.
- Use UTF-8 BOM for the readable log to avoid Chinese mojibake in common Windows tools.
- Improve monitor output readability without dropping any event data.
- Surface both log paths in startup events and pointer files.

**Non-Goals:**

- Do not replace JSONL or change event semantics.
- Do not add a database table for logs.
- Do not filter out user inputs, method content, AI outputs, or review content from the readable log.
- Do not store secrets or provider authorization data.

## Decisions

### Keep JSONL As Ledger, Add Markdown As Mirror

The JSONL file remains the machine-readable source for event replay and tests. The Markdown file is a `镜` projection: easier to read, derived from the same events, and not a separate source of truth.

### Use UTF-8 BOM For Human Logs

The readable log is written with `utf-8-sig` on creation. This makes Windows editors identify the file as UTF-8 while leaving the existing JSONL parser behavior unchanged.

### Render Long Values As Blocks

Fields such as `input`, `response`, `result`, `method_content`, `review`, and JSON payloads are rendered as fenced blocks. Short scalar fields stay in bullet form. Fence length is chosen dynamically so embedded Markdown fences do not break the readable log.

### Set Launcher Encoding

The PowerShell launcher sets console output and `PYTHONUTF8` for the two spawned CLIs. This reduces live-monitor mojibake without forcing provider or model defaults into code.

## Risks / Trade-offs

- Readable logs duplicate JSONL content -> Accepted because the user needs a human inspection surface; logs are ignored by git.
- Readable logs can be large when method content is logged -> Accepted for validation; later work can add redaction or folding if needed.
- Console encoding varies across hosts -> Launcher configuration improves the default path; direct shell usage may still depend on host settings.
