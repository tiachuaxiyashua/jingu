---
name: frontier-context-engineering-review
description: Review context engineering, retrieval, memory, prompt assembly, provenance, compaction, budget control, and evidence flow against current official practice from OpenAI, Anthropic, LangGraph, and MCP. Use when auditing AI harnesses, RAG/context-pack systems, long-dialogue handling, retrieval quality, or whether a document-heavy agent runtime is truly production-grade.
---

# Frontier Context Engineering Review

Review Cyber Editor context engineering against current official agent-runtime practice.

## Mandatory Frontier Refresh

Before every review:

1. Open [references/frontier-refresh.md](./references/frontier-refresh.md).
2. Run the listed web searches against official domains only.
3. Capture a `Frontier refresh` block in the review:
   - refresh date
   - sources checked
   - any changed recommendation on retrieval, memory, budget, or evidence

Do not skip refresh when reviewing:
- context pack design
- RAG / retrieval
- long dialogue compaction
- prompt assembly
- evidence / provenance
- evaluation of retrieval quality

## Review Workflow

1. Run frontier refresh.
2. Read repo truth in this order:
   - `docs/01-需求与PRD/`
   - `docs/01-需求与PRD/03-功能范围与优先级.md`
   - `docs/03-架构实现/01-系统架构与分层Owner.md`
   - `docs/03-架构实现/` relevant to AI harness
   - `docs/03-架构实现/03-数据契约状态机与安全.md` relevant to schemas/oracles
   - `src/main/services/runtime-service.ts`
   - `src/main/services/knowledge-index-service.ts`
   - `src/main/services/hybrid-retrieval-service.ts`
   - `src/main/services/provenance-service.ts`
   - `src/main/services/runtime-budget-governor.ts`
   - relevant tests
3. Build the real path:
   `user/document change -> index/update -> retrieval -> budget/packing -> prompt assembly -> run/evidence -> UI visibility`
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

- Do not accept “has RAG” unless indexed units, freshness, retrieval ranking, and provenance are all real.
- Do not accept “context compression” unless there is an explicit budget owner and evidence of what was omitted.
- Do not accept “memory” unless its scope, persistence, and invalidation are defined.
- Do not accept “sources visible” unless a user or reviewer can trace why a document entered context.
- Prefer retrieval/evidence systems that are inspectable and replayable over hidden prompt stuffing.

## Load These References

- Always load [references/frontier-refresh.md](./references/frontier-refresh.md).
- Load [references/source-map.md](./references/source-map.md) when aligning Cyber Editor to official practice.
- Load [references/checklist.md](./references/checklist.md) for the actual review pass.
