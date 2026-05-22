## Context

The sandbox now produces candidate verification jobs and a bounded repair loop. That covers deterministic failures, but it still leaves a gap: a candidate can pass the hard check and still deserve a semantic repair, directional correction, or high-value escalation. Chat already has a feedback judgment hook, but `ai run` does not, and chat currently judges mostly from the raw turn rather than from the verification and repair evidence that the runtime already computed.

The truth source requires candidate isolation, evidence-carrying outcomes, high-value questions to be显影 instead of hidden, and human-facing or routed decisions when value/risk demands it. This change extends the existing routing chain instead of creating a parallel one.

## Goals / Non-Goals

**Goals:**

- Reuse one AI acceptance-routing path for both `ai run` and `ai chat`.
- Feed the router with the final candidate, verification report, repair summary, and the original task.
- Let the acceptance router push repairable semantic issues back to an execution repair job.
- Create feedback jobs for high-value or directional issues even after deterministic verification passes.
- Preserve the no-auto-accept/no-auto-reject rule.

**Non-Goals:**

- Do not replace deterministic verification with AI judgment.
- Do not promote feedback routing into a new law or global policy engine.
- Do not hardcode domain-specific rejection rules or product-specific thresholds.

## Decisions

1. Keep deterministic verification as the first gate.

   The router only runs after the verification/repair path produces a final candidate. This avoids using AI to rediscover simple mechanical failures and keeps the repair loop bounded.

2. Make the router choose a route, not a verdict.

   The router returns one of three route actions: continue without feedback, repair by executor, or feedback/decision job. This lets the acceptance role打回执行端 while preserving candidate isolation and avoiding a hidden accept/reject bit.

3. Reuse the existing feedback-job and repair-job models instead of inventing new states.

   A repair route creates an execution repair child job and submits the revised output as a new candidate. A feedback route creates a feedback child job with required context gaps. Both are visible in the job tree.

4. Pass structured evidence into the router.

   The routing prompt includes the task, final candidate, verification report, repair summary, attempt count, and final verification status. This makes the judgment explainable and keeps the logs useful for later debugging.

5. Share one routing parser across `ai run` and `ai chat`.

   The two commands should not drift into different prompt shapes or different routing semantics. A shared parser and prompt builder keeps the judgment contract stable.

6. Emit router evidence even when no feedback job is created.

   Skip decisions are still evidence. They should show why the router did not need to push the candidate back, instead of disappearing into an invisible branch.

## Risks / Trade-offs

- More provider calls may increase latency -> Keep the router bounded to one extra judgment per completed candidate path.
- The router may over-escalate high-value issues -> Preserve the skip path and record reasons so the judgment can be tuned from logs.
- The router may loop on semantic repair -> Limit acceptance-role repair to one explicit打回 per completed candidate path in this change.
- Structured prompts may become verbose -> Keep the payload compact and reuse existing evidence fields where possible.
- Chat and run may drift if one side is updated later -> Use a shared helper and test both commands against the same judgment schema.

## Migration Plan

1. Extend the sandbox runtime with a shared acceptance-routing helper.
2. Wire `ai run` to call the helper after repair completes.
3. Update `ai chat` to call the same helper with verification and repair evidence.
4. Add tests for a deterministic pass that routes to execution repair, a deterministic pass that routes to feedback, and a normal skip path.
5. Validate logs and hardcoding scan before archive.

## Open Questions

- Should later versions allow multiple acceptance-role repair cycles, or should semantic repair always remain a single打回 before human/directional feedback?
