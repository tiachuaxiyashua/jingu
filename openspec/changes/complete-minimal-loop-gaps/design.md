## Context

The runtime already has a minimal job tree, AI candidate generation, split proposals, child package review, parent integration, verification, repair, acceptance routing, JSONL/readable logs, and a static trace viewer. The last evaluation identified ten gaps that all point to the same issue: the loop is observable, but several control signals are still helper-only, one-pass, or weakly linked.

The truth source requires that child jobs supply material, parent jobs integrate, candidates remain isolated, evidence carries hardness, high-value decisions return to humans, and views remain read-only projections.

## Goals / Non-Goals

**Goals:**
- Make integration, integration repair, human decision, method-step, and learning-candidate paths visible as jobs or appearances.
- Keep parent/root completion authority separate from all new helper paths.
- Add bounded continuation so the minimal loop can advance more than one frontier wave.
- Strengthen runtime metadata enough for manual inspection and future migration.
- Improve the viewer from a projection into a practical trace debugger.
- Replace scattered loop constants at the runtime boundary with explicit options.

**Non-Goals:**
- Do not implement mature autonomous planning or unlimited recursive agents.
- Do not auto-approve human decisions.
- Do not promote method learning candidates into stable method files.
- Do not replace the SQLite schema with many new tables.
- Do not claim that AI self-review is hard evidence.

## Decisions

1. **First-class job visibility without new tables**

   Integration, integration repair, human decision, method-step, and learning paths will be represented as normal child jobs or candidate appearances, plus typed flow events. This follows the truth source: semantic objects can live in the existing job, appearance, and event tables until query pressure justifies separate tables.

2. **Bounded continuous advancement**

   The runner will loop frontier dispatch for a configured number of waves. Each wave can process children, review packages, integrate accepted material, and register follow-up work. The loop stops on max waves, no active frontier, or no progress. This avoids infinite autonomous behavior while making multi-step verification possible.

3. **Integration repair is a job, not hidden retry**

   Invalid parent integration output creates a child repair job under the parent and records a repair prompt/evidence. A single configured repair attempt can return a corrected integration JSON. If it remains invalid, the parent candidate is unchanged and the issue is visible.

4. **Human decision return is evidence-backed state**

   Acceptance routing can create human decision jobs. A new runtime helper can record a decision payload against that job and attach decision evidence. In this change the CLI/runtime exposes the recording path and logs it; interactive UX can grow later.

5. **Evidence hardness as metadata**

   Evidence submissions can carry `evidence_hardness` and `evidence_kind` metadata. Existing evidence defaults to weak/unspecified unless a deterministic tool, runtime check, human decision, or external source marks it stronger. The viewer displays the field when present.

6. **Lineage via appearance metadata and evidence JSON**

   Parent integration candidates will store upstream candidate, consumed child result/evidence refs, and integration job ids in appearance metadata. This is a stronger reference than log-only evidence and remains compatible with the current table model.

7. **Method learning remains candidate-only**

   Method update observations become `method_learning_candidate` appearances and evidence. They are not written into skill/method files and are not treated as stable law.

8. **Viewer controls are client-only**

   Search, event-phase filtering, job filtering, and appearance highlighting are implemented in browser JavaScript over the loaded JSONL. The viewer never mutates runtime state.

## Risks / Trade-offs

- [Risk] Continuous advancement can hide too much autonomous behavior. → Mitigation: bounded wave count, no auto-completion, and full wave logs.
- [Risk] More event types add complexity. → Mitigation: all new events map to existing process/log/viewer patterns.
- [Risk] AI-generated repair can still be invalid. → Mitigation: parse/validate before mutation; invalid repair only records evidence and job state.
- [Risk] Evidence hardness labels may be over-trusted. → Mitigation: labels are metadata, not acceptance authority; weak evidence risks remain visible.
- [Risk] Method-step extraction from markdown can be naive. → Mitigation: treat it as traceable candidate work only, not stable法 decomposition.
