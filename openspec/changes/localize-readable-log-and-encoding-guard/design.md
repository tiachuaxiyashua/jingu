## Context

Readable sandbox logs are the current human-facing projection of AI task flow. They are not the event ledger itself, but they must be understandable to the Chinese-speaking project owner. The existing Markdown log uses English headings such as `input` and raw event identifiers as the primary display text, which makes it look like a developer dump rather than a `镜`.

Some question marks in previously generated samples were caused by upstream console/string corruption before the logger received the text. Once text has become `????`, the logger cannot reconstruct the original Chinese. It can, however, preserve correct Unicode when received and warn when a value already looks damaged.

## Goals / Non-Goals

**Goals:**

- Make readable Markdown logs Chinese-first.
- Preserve raw identifiers in parentheses for debugging.
- Keep JSONL unchanged as machine-readable truth.
- Detect suspicious consecutive `?` runs and show a Chinese warning beside the affected field.
- Strengthen launcher encoding setup for both input and output.

**Non-Goals:**

- Do not mutate JSONL event schemas.
- Do not attempt impossible recovery of already-lost Chinese text from `????`.
- Do not add a localization framework or runtime language setting.
- Do not hide raw event data.

## Decisions

### Chinese Projection With Raw Identifiers

The readable renderer will display Chinese labels first and raw identifiers second, such as `输入内容（input）`. This keeps the log readable for the user and still searchable for developers.

### Warning Instead Of Silent Repair

If a value contains suspicious consecutive question marks, the renderer adds `编码警告` text before the field value. This distinguishes damaged input/output from normal task content and gives a concrete next action.

### Stronger PowerShell Encoding Setup

The launcher and monitor scripts set console input/output encoding plus `PYTHONUTF8` and `PYTHONIOENCODING`. This reduces the chance of corrupt input before it reaches Python while keeping provider configuration external.

## Risks / Trade-offs

- Some legitimate content may contain many question marks -> The warning is advisory and does not block execution or change JSONL.
- Chinese labels are currently owned by the readable projection code -> Acceptable for this first Chinese-only `镜`; future multi-language support can extract them to a resource file when needed.
- Old corrupted logs remain corrupted -> New runs will show the warning, but cannot repair old lost bytes.
