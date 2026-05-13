---
name: frontier-test-architecture-review
description: Review automated test architecture, oracle design, eval strategy, isolation, traceability, and Electron/UI test coverage against current official guidance from Playwright, OpenAI evals, and Electron testing docs. Use when auditing whether the test suite can actually stop regressions in UI, orchestration, runtime governance, and AI behavior.
---

# Frontier Test Architecture Review

## Mandatory Frontier Refresh

Before every review:
1. Open [references/frontier-refresh.md](./references/frontier-refresh.md).
2. Run the official searches.
3. Record `Frontier refresh` with date, sources, and changed testing guidance.

## Review Workflow

1. Refresh frontier guidance.
2. Read `docs/03-架构实现/03-数据契约状态机与安全.md`, `docs/04-测试验收/`, `docs/README.md`, relevant review docs, then `tests/` and the runtime owners under test.
3. Evaluate isolation, oracle quality, destructive-path coverage, traceability, packaged/electron realism, and AI eval coverage.
4. Score against [references/checklist.md](./references/checklist.md).
5. Output findings with doc/code/test evidence.

## Domain Rules

- Do not accept test count as proof; accept only oracle quality and path coverage.
- Do not accept AI runtime quality claims without eval-like evidence or trace assertions.
- Do not accept Electron/UI coverage that ignores resize, persistence, and packaged paths.
- Prefer user-visible assertions and trace artifacts over implementation-detail selectors.

## Load These References

- [references/frontier-refresh.md](./references/frontier-refresh.md)
- [references/source-map.md](./references/source-map.md)
- [references/checklist.md](./references/checklist.md)
