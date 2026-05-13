---
name: frontier-data-contracts-review
description: Review schemas, manifests, file contracts, versioning, references, and migration strategy against current official schema and API specification guidance from JSON Schema, OpenAPI, SemVer, and MCP. Use when auditing manifest shapes, runtime evidence objects, flow drafts, artifact catalogs, or whether document contracts are stable enough for implementation.
---

# Frontier Data Contracts Review

## Mandatory Frontier Refresh

Before every review:
1. Open [references/frontier-refresh.md](./references/frontier-refresh.md).
2. Run the listed official searches.
3. Record `Frontier refresh` with date, sources, and changed schema/versioning guidance.

## Review Workflow

1. Refresh frontier guidance.
2. Read contract docs under `docs/03-架构实现/03-数据契约状态机与安全.md`, `docs/03-架构实现/`, `docs/04-测试验收/`, then shared/main code that owns those objects.
3. Check schema authority, version fields, migration rules, missing-field recovery, and folder placement.
4. Score against [references/checklist.md](./references/checklist.md).
5. Output findings with doc/code/test evidence.

## Domain Rules

- Do not accept a data model if schema authority and folder authority are split.
- Do not accept versioning without upgrade and downgrade behavior.
- Do not accept references without explicit resolution rules and missing-target behavior.
- Prefer explicit schema objects and migration rules over prose-only payload descriptions.

## Load These References

- [references/frontier-refresh.md](./references/frontier-refresh.md)
- [references/source-map.md](./references/source-map.md)
- [references/checklist.md](./references/checklist.md)
