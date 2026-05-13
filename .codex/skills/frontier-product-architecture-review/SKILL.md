---
name: frontier-product-architecture-review
description: Review product boundary, feature hierarchy, object model, user journeys, and progressive disclosure against current desktop-workbench guidance from VS Code UX, Fluent/WinUI, and current AI product patterns. Use when auditing whether requirements, feature trees, and page entry paths are coherent enough for implementation.
---

# Frontier Product Architecture Review

Review Cyber Editor as a product system, not as isolated pages.

## Mandatory Frontier Refresh

Before every review:
1. Open [references/frontier-refresh.md](./references/frontier-refresh.md).
2. Run the listed official searches.
3. Record `Frontier refresh` with date, sources, and any changed recommendation.

## Review Workflow

1. Refresh frontier guidance.
2. Read `docs/README.md`, `docs/01-需求与PRD/`, `docs/02-产品设计/`, `docs/03-架构实现/01-系统架构与分层Owner.md`, then relevant `src/renderer/*`.
3. Trace the main journeys:
   - create project
   - start orchestration without project
   - edit/run inside project
   - resource/template/skill management
4. Score against [references/checklist.md](./references/checklist.md).
5. Produce findings with doc/code/test evidence.

## Domain Rules

- Do not accept a feature tree if entry paths and object ownership still imply different products.
- Do not accept “supports novices and experts” unless both paths are explicit and low-conflict.
- Do not accept repeated management surfaces for the same object unless there is one primary surface and one secondary surface.

## Load These References

- [references/frontier-refresh.md](./references/frontier-refresh.md)
- [references/source-map.md](./references/source-map.md)
- [references/checklist.md](./references/checklist.md)
