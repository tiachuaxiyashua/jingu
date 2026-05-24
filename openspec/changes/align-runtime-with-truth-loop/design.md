## Context

The truth source defines Jingu as a Xiang-Ye runtime: stable appearances change only through jobs; actors submit candidates; results must carry evidence; evidence and accepted results become new conditions for later jobs. The current sandbox runner has the right objects but the wrong control center: `AiSandboxRunner.run()` owns a fixed sequence of phases, and job-tree advancement is a bounded attachment inside that sequence.

This creates a structural contradiction. A minimal loop should support any-size tasks by pausing and resuming the same job tree. The current implementation can stop after a small number of waves even when runnable follow-up jobs exist, then returns a candidate as if the run lifecycle ended normally.

## Goals / Non-Goals

**Goals:**

- Make the job loop, not the fixed runner pipeline, the control center for sandbox advancement.
- Add global repository rules that prevent future code from drifting away from the truth source.
- Preserve the existing runtime laws: original wish preservation, candidate isolation, evidence-backed acceptance, and parent-scope completion ownership.
- Convert wave/frontier limits into pause budgets: reaching a budget must produce an explicit paused outcome with remaining frontier evidence.
- Keep CLI output concise while logs and viewer retain full process evidence.
- Support GitHub proxy fallback through configuration or command-level operational handling, not reusable-code hardcoding.

**Non-Goals:**

- Do not build a production-scale distributed scheduler in this change.
- Do not add new domain-specific engines for novels, word count, or web search.
- Do not remove existing log/viewer compatibility unless required by the corrected loop contract.
- Do not make AI automatically decide high-value human choices; high-value or directional choices still become feedback/human-decision jobs.

## Decisions

### Decision 1: Introduce a loop outcome instead of treating runner completion as task completion

The advancement loop will return a structured outcome:

- `completed`: no active child frontier and the latest root candidate can proceed to verification/routing.
- `paused`: budget exhausted while active or blocked jobs remain.
- `blocked`: no runnable jobs exist because context gaps or human decisions are unresolved.

Rationale: A large task is not special. It is a sequence of minimal loop turns. Budget exhaustion is not failure and not completion; it is a checkpoint.

Alternative considered: increase default wave limits. Rejected because it keeps the fixed pipeline as the control center and only hides the architectural problem.

### Decision 2: Keep existing job primitives, but make advancement re-enter after follow-up registration

Parent integration already registers follow-up jobs. The corrected loop must treat those jobs as new frontier work in the same advancement cycle until it reaches completion, blocked state, or pause budget.

Rationale: Accepted child packages and parent integration candidates are new conditions. If they create more jobs, those jobs must re-enter the same job loop.

Alternative considered: add a separate "follow-up executor" component. Rejected because it creates another orchestration path outside the job loop.

### Decision 3: Preserve context gaps as visible conditions, but stop treating them as inert strings

This change will not fully replace `required_context_gaps` with typed dependency references. It will, however, report blocked frontier state as a first-class loop outcome so the system does not silently reject the child package and continue as if nothing happened.

Rationale: typed dependency resolution is larger than this correction. The minimum truth-aligned behavior is to pause/declare blocked with evidence instead of pretending a blocked job was just a rejected package.

Alternative considered: auto-clear string gaps heuristically. Rejected because it would be self-indulgent and could incorrectly satisfy user or evidence dependencies.

### Decision 4: Make global governance rules mandatory before future runtime changes

`AGENTS.md` will require every runtime/orchestration/code change to state truth-source invariants before implementation and verify them after implementation.

Rationale: the previous drift happened because OpenSpec tasks and tests were written around symptoms. The new rule makes truth alignment part of the definition of done.

Alternative considered: rely on developer memory. Rejected because the failure was structural, not just forgetfulness.

## Risks / Trade-offs

- [Risk] The first correction may still leave `required_context_gaps` too weak for full dependency resolution. → Mitigation: blocked outcomes must expose unresolved gaps and preserve active frontier state for the next change.
- [Risk] Existing tests may expect one-shot completion. → Mitigation: update tests to assert loop outcomes and active frontier evidence, not merely event presence.
- [Risk] More loop iterations can increase provider cost. → Mitigation: budgets remain, but they pause instead of falsely ending.
- [Risk] Long tasks still need durable artifacts outside transient chat output. → Mitigation: this change preserves job/object-store evidence and makes remaining work explicit; artifact streaming can be a later job capability.

## Migration Plan

1. Add governance rules to `AGENTS.md`.
2. Add loop outcome fields and log labels without breaking existing event consumers.
3. Refactor `run_advancement_loop()` to continue while frontier changes, and to return `paused` or `blocked` instead of only "wave limit reached".
4. Update sandbox runner output selection so paused/blocked runs record the state honestly.
5. Add tests for pause/resume semantics, blocked frontier evidence, and follow-up jobs re-entering advancement.
6. Run OpenSpec validation, Python tests, compile checks, viewer validation, and hardcoding scan.

## Open Questions

- Should typed dependency references replace `required_context_gaps` in the next change, or should gaps remain text with evidence links?
- Should long-form artifact append semantics be modeled as a generic appearance-update job or as a specialized large-object writing law?
