---
name: frontier-agent-orchestration-review
description: Review agent workflow orchestration, graph semantics, multi-agent topology, subflows, handoffs, durable execution, and human-in-the-loop boundaries against current official patterns from LangGraph, AutoGen, CrewAI, OpenAI Agents, and MCP. Use when auditing flow editors, orchestration runtimes, role communication, loop/parallel semantics, or whether docs and code match modern agent-system design.
---

# Frontier Agent Orchestration Review

Review Cyber Editor orchestration design against current official agent-framework practice.

## Mandatory Frontier Refresh

Before every review:

1. Open [references/frontier-refresh.md](./references/frontier-refresh.md).
2. Run the listed web searches against the listed official domains.
3. Prefer sources updated or published most recently.
4. Record a short `Frontier refresh` block in the review output:
   - refresh date
   - sources checked
   - any change in recommended pattern vs prior assumptions

Do not skip this step when the review touches:
- multi-agent collaboration
- handoffs / delegation
- loop / branch / subflow semantics
- durable execution
- human approval / interrupts

## Review Workflow

1. Refresh frontier guidance first.
2. Read only the minimum repo truth needed, in this order:
   - `docs/01-需求与PRD/`
   - `docs/01-需求与PRD/03-功能范围与优先级.md`
   - `docs/03-架构实现/01-系统架构与分层Owner.md`
   - relevant `docs/03-架构实现/`
   - relevant `docs/03-架构实现/03-数据契约状态机与安全.md`
   - `src/renderer/components/OrchestrationWorkspace.tsx`
   - `src/shared/flow-validator.ts`
   - `src/main/services/workspace-orchestrator.ts`
   - `src/main/services/runtime-service.ts`
   - relevant tests
3. Build the real path:
   `entry -> orchestration UI -> draft/schema -> runtime owner -> persistence/evidence -> observable run result`
4. Score the system against [references/checklist.md](./references/checklist.md).
5. Produce findings with doc/code/test evidence.

## Output Contract

Output in this order:

1. Findings by severity
2. Open questions / assumptions
3. Frontier refresh
4. Overall decision
5. Immediate next actions

Every finding must cite:
- one docs reference
- one code reference or explicit missing-code fact
- one test reference or missing-test fact

## Domain Rules

- Do not accept a node canvas as a real orchestration system if loop, branch, subflow, and handoff semantics are still ambiguous.
- Do not accept “multiple agents exist” unless communication, shared state, turn-taking, and failure ownership are defined.
- Do not accept “can resume” unless checkpoints, interrupts, and retry rules are on the execution path.
- Prefer generic node semantics with explicit runtime meaning over hardcoded pattern nodes.
- Treat human approval and interrupt/resume as first-class orchestration semantics, not afterthought UI.

## Load These References

- Always load [references/frontier-refresh.md](./references/frontier-refresh.md).
- Load [references/source-map.md](./references/source-map.md) when you need to explain which external frameworks influenced the review.
- Load [references/checklist.md](./references/checklist.md) for the actual scoring pass.
