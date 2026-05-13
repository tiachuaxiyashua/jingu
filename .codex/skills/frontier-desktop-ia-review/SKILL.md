---
name: frontier-desktop-ia-review
description: Review desktop information architecture, panel hierarchy, navigation chrome, tree views, inspectors, and progressive disclosure against current official desktop guidance from VS Code UX, WinUI NavigationView, Fluent 2, and Electron constraints. Use when auditing workbench layout, panel usage, window density, or whether a page feels like a real editor instead of a demo.
---

# Frontier Desktop IA Review

## Mandatory Frontier Refresh

Before every review:
1. Open [references/frontier-refresh.md](./references/frontier-refresh.md).
2. Run the official searches.
3. Record `Frontier refresh` with date, sources, and changed UI guidance.

## Review Workflow

1. Refresh frontier guidance.
2. Read `docs/02-产品设计/`, relevant `docs/01-需求与PRD/` / `docs/01-需求与PRD/03-功能范围与优先级.md`, then renderer files for welcome/workbench/orchestration/resource/settings pages.
3. Evaluate first-screen density, panel priority, tree usage, modal/drawer usage, and adaptive resizing.
4. Score against [references/checklist.md](./references/checklist.md).
5. Output findings with doc/code/test evidence.

## Domain Rules

- Prefer persistent tree/navigation surfaces only for high-frequency objects.
- Prefer drawers/modals for low-frequency management.
- Do not let side panels dominate the main authoring surface.
- Do not treat compact-width behavior as polish; it is part of IA correctness.

## Load These References

- [references/frontier-refresh.md](./references/frontier-refresh.md)
- [references/source-map.md](./references/source-map.md)
- [references/checklist.md](./references/checklist.md)
