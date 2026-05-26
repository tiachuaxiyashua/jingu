## Context

The sandbox currently calculates a quantitative delivery ledger from the text of the latest candidate. In the diagnostic DeepSeek run, a child result package carrying chapter content was accepted, then a parent integration candidate consisting mainly of progress analysis caused the recorded amount to fall. The same integration step parked non-critical follow-ups, but the subsequent generic split extraction path registered overlapping active jobs.

The truth source requires accepted child fruit to become parent conditions through explicit references and evidence, and permits a split only when it has a distinct consumable result without a duplicate sibling. The runtime therefore needs accounting and gating semantics, not task-domain branching.

## Goals / Non-Goals

**Goals:**

- Count quantitative delivery from explicitly marked contributions in accepted child result packages, with source appearance/job provenance and deduplication.
- Preserve current-candidate measurements as diagnostic data without allowing integration commentary to overwrite accepted delivery progress.
- Require incomplete quantitative delivery splits to declare their delivery relation and allow only one active critical-path registration for a parent at a time.
- Prevent a parent integration from sending the same incomplete-delivery condition through both deterministic continuation registration and generic extraction in the same cycle.
- Keep all decisions observable in machine and readable flow logs.
- Preserve the boundary that accepted child fruit returns to the parent before any further split registration, so a child does not recursively inherit and try to satisfy the full root quantitative contract by itself.
- Keep parent integration as a reference-and-evidence integration step, not a second writer that expands or rewrites large deliverable bodies.
- Keep one command bounded by an observable batch boundary when measurable delivery progress has been accepted and the root quantitative target is still incomplete.

**Non-Goals:**

- Decide whether any specific genre, platform strategy, chapter structure, or content direction is correct.
- Treat AI marking of a contribution as sufficient final quality proof; the existing independent child-package review and later parent verification remain required.
- Migrate historical runtime objects into newly claimed delivery progress when they did not explicitly identify delivery contributions.

## Decisions

### Add an explicit delivery contribution slot to new child result packages

New child packages include `delivery_contributions`, a list of structured contributions containing a package-local identifier, delivered text, and a declaration that the text counts toward the parent delivery target. An empty list is valid for support-only work. The child reviewer is instructed to reject or repair a package that incorrectly marks support material or omits delivered text needed by its contract.

This is preferred to inspecting artifact type labels or detecting prose in arbitrary artifact content: those are task-specific guesses and would mix evidence reports with actual deliverables.

Historical accepted packages without the new slot remain readable and integrable, but contribute zero measured delivery until a later accepted package explicitly carries a contribution.

### Build the ledger from accepted contribution references

The runner collects contributions from accepted structured child packages of the parent. Each counted item is keyed by result appearance id and contribution id, stores its source job/result reference, and has its CJK count computed by the deterministic verifier. The ledger reports both accepted accumulated quantity and the latest candidate diagnostic quantity; scheduling status uses accepted accumulated quantity when that basis is available.

This is preferred to trusting the parent integrator's stated total or counting its integrated narrative: the former is an unverified assertion and the latter caused the observed rollback.

### Gate incomplete quantitative frontiers by a declared delivery relation

When a ledger is below minimum, an AI split proposal must declare whether it directly advances the quantitative delivery, unblocks that delivery, or is non-critical. The runtime may register at most one critical proposal under that parent in the current registration pass; non-critical and additional critical proposals are parked in the log rather than activated.

When deterministic parent-integration triage has already created the single delivery-continuation job, the generic extraction pass is skipped for that integration candidate and the reason is logged. This removes the duplicated ingress that reactivated already parked work.

This is preferred to matching words such as chapter names or feedback categories, which would encode one task domain into generic runtime logic.

### Return accepted child packages to the parent before more splitting

A child package that passes review is accepted in its own responsibility scope and then returns to its parent. The runtime no longer runs generic split extraction against that child package before parent acceptance. Follow-up work exposed by the package must be consumed by the parent integration and registered from the parent scope, where completion authority and delivery accounting belong.

This prevents a delivery child from inheriting the root length target and recursively creating grandchildren to satisfy the entire root contract. It also prevents an already accepted child from continuing to own unresolved descendants, which would blur completion authority.

### Keep parent integration reference-based for large deliverables

Parent integration is instructed to produce a parent-scope manifest, consumption summary, evidence, gaps, and follow-up routing. It must not invent new deliverable content and must not copy large accepted delivery bodies back into the integration response unless the parent target itself is a small summary artifact. Quantitative progress is still calculated from accepted child `delivery_contributions`, not from the integration prose.

### Pause after measurable delivery batches

When auto-continue is enabled and a command accepts measurable delivery contributions while the root quantitative target remains incomplete, the runtime returns a paused result and records a checkpoint instead of continuing to dispatch the next runnable delivery frontier in the same command. A later resume command can continue from the checkpoint. This keeps long work as repeated verifiable batches rather than an unbounded one-shot run.

### Keep readable logs human-readable while preserving machine detail

The JSONL event ledger still records every provider stream delta. The Markdown readable log and monitor projection do not expand each stream delta into a full Markdown section; full prompts, full provider responses, result packages, evidence, and lifecycle events remain available in readable form through their higher-level events. This keeps the `镜` usable without discarding the machine audit trail.

## Risks / Trade-offs

- [Risk] An executor may mislabel support text as a delivery contribution. -> Mitigation: make contribution marking part of the child-package review contract and retain later deterministic/root verification; logs expose every counted source.
- [Risk] Historical accepted packages lack the new field and show zero attributable accumulated delivery. -> Mitigation: integrate them normally but report the missing attributable contribution rather than inventing progress.
- [Risk] A single critical frontier may defer genuinely independent work. -> Mitigation: preserve deferred proposals as visible parked evidence; once the quantitative blocker is satisfied or a later law authorizes concurrency, they can be reconsidered through a new job.
- [Risk] Skipping child-local split extraction after an accepted package can defer a useful refinement. -> Mitigation: parent integration receives open questions and suggested follow-ups, then registers them from the parent scope where their ownership is visible.
- [Risk] Reference-based integration may look less like a final artifact during intermediate batches. -> Mitigation: final completion still requires root verification; intermediate runs should expose checkpointed progress, not pretend to be the full deliverable.

## Migration Plan

1. Extend new child-package and split-proposal contracts with the structured fields while retaining read compatibility for older accepted packages.
2. Use accepted contribution accounting in split registration and parent-integration continuation routing.
3. Add visible parked/skip logging for frontier gating.
4. Validate with deterministic regression tests and a new real DeepSeek run of the original long-delivery task.

Rollback consists of reverting this change; no committed runtime-state migration is performed.

## Open Questions

- Whether future law versions should allow a configured bounded number of independent critical delivery branches remains a later evidence-driven decision; this fix uses one active branch because the current run proved uncontrolled duplication, not beneficial parallelism.
