---
name: frontier-runtime-governance-review
description: Review runtime governance, side-effect approval, tool boundaries, durable recovery, audit evidence, and destructive-path handling against current official guidance from OpenAI, LangGraph, and MCP. Use when auditing approvals, local/remote capability exposure, checkpoint/rollback flows, observability, or whether the runtime is safe to extend.
---

# Frontier Runtime Governance Review

Review Cyber Editor runtime safety and governance against current official agent-runtime practice.

## Mandatory Frontier Refresh

Before every review:

1. Open [references/frontier-refresh.md](./references/frontier-refresh.md).
2. Run the listed official searches.
3. Record a `Frontier refresh` block in the review:
   - refresh date
   - sources checked
   - any changed recommendation on approvals, capability boundaries, recovery, or auditability

Do not skip refresh when reviewing:
- side-effect approvals
- local script/tool execution
- MCP capability boundaries
- checkpoint / restore / rollback
- audit evidence
- failure-path handling

## Review Workflow

1. Run frontier refresh.
2. Read repo truth in this order:
   - `docs/01-需求与PRD/`
   - `docs/01-需求与PRD/03-功能范围与优先级.md`
   - `docs/03-架构实现/01-系统架构与分层Owner.md`
   - relevant `docs/03-架构实现/`
   - relevant `docs/03-架构实现/03-数据契约状态机与安全.md`
   - `src/main/services/side-effect-governance-service.ts`
   - `src/main/services/resource-governance-service.ts`
   - `src/main/services/project-service.ts`
   - `src/main/services/evidence-store-service.ts`
   - `src/main/services/runtime-service.ts`
   - relevant tests
3. Build the real path:
   `request -> preview/approval -> execution -> persistence/audit -> recovery/rollback -> observable status`
4. Score against [references/checklist.md](./references/checklist.md).
5. Output findings with doc/code/test evidence.

## Output Contract

Output in this order:

1. Findings by severity
2. Open questions / assumptions
3. Frontier refresh
4. Overall decision
5. Immediate next actions

## Domain Rules

- Do not accept approval metadata without a real execution gate.
- Do not accept rollback claims unless destructive paths are recoverable or staged.
- Do not accept tool safety if capability boundaries depend only on UI.
- Do not accept auditability if the evidence package cannot reconstruct who approved what and what ran.
- Prefer host-enforced roots and one-time approvals over ad hoc flags.

## Load These References

- Always load [references/frontier-refresh.md](./references/frontier-refresh.md).
- Load [references/source-map.md](./references/source-map.md) when mapping repo behavior to frontier practice.
- Load [references/checklist.md](./references/checklist.md) for the actual review pass.
