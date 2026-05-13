---
name: frontier-defensive-programming-review
description: Review defensive programming, failure containment, rollback, damage control, runtime invariants, and boundary hardening against current official security and durability guidance from Electron, OpenAI, LangGraph, and MCP. Use when auditing risky code paths, recovery logic, approval gates, corruption handling, or whether code is robust enough for extension.
---

# Frontier Defensive Programming Review

## Mandatory Frontier Refresh

Before every review:
1. Open [references/frontier-refresh.md](./references/frontier-refresh.md).
2. Run the listed official searches.
3. Record `Frontier refresh` with date, sources, and changed guidance.

## Review Workflow

1. Refresh frontier guidance.
2. Read relevant requirement/contract docs, then risky service code and tests.
3. Inspect replay risk, rollback integrity, corruption handling, bounded retries, and invariant tests.
4. Score against [references/checklist.md](./references/checklist.md).
5. Output findings with doc/code/test evidence.

## Domain Rules

- Do not accept a fix that handles only the happy path.
- Do not accept destructive write paths without staging or recovery.
- Do not accept security/governance flags unless enforced on the runtime path.
- Prefer structured actionable errors over opaque exceptions.

## Load These References

- [references/frontier-refresh.md](./references/frontier-refresh.md)
- [references/source-map.md](./references/source-map.md)
- [references/checklist.md](./references/checklist.md)
