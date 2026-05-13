# System Review Checklist

Use this checklist to run a complete Cyber Editor system review.

## 1. Product boundary

- Is the product still clearly a desktop orchestration-first text/image workbench?
- Are non-goals explicit enough to prevent platform drift?
- Do requirements define target users, output boundaries, and primary usage modes?

## 2. Requirement completeness

- Do `docs/01-需求与PRD/` and `docs/02-产品设计/` constrain the product enough for a product engineer to derive the same feature tree?
- Are core and necessary non-core requirements separated clearly?
- Are output types, directories, and input/output ownership defined?

## 3. Feature hierarchy and atomic coverage

- Does `docs/01-需求与PRD/03-功能范围与优先级.md` cover the current P0/P1/P2 feature boundaries and reachable user actions?
- Are M/S/A items decomposed to atomic behaviors rather than slogans?
- Are statuses credible against runtime reality?

## 4. UI information architecture

- Are all user-reachable pages and modal/drawer paths defined?
- Is the first screen low-noise for novices while preserving deep paths for experts?
- Do page entry, exit, switch, and return paths match code?

## 5. Four-layer architecture boundary

- Are intelligent, orchestration, connection, and capability layers separated?
- Is each important object owned by one runtime layer?
- Are renderer, IPC, and main responsibilities distinct?

## 6. Orchestration semantics

- Are node types, edges, loops, parallelism, subflows, and agent communication rules explicit?
- Are stage guard, confirmation, rerun, pause/resume, and output contracts defined?
- Do orchestration docs match actual execution code and UI?

## 7. AI harness and context engineering

- Is there a real context-pack, budgeting, recovery, and long-dialogue strategy?
- Are indexing, retrieval, provenance, and compression present in code, not only docs?
- Is the harness sufficient for long projects and multi-step flows?

## 8. Model governance and AI controllability

- Is dynamic model selection implemented on the true runtime path?
- Are structure enforcement, repair, fallback, and provider diagnostics real?
- Are local and remote model behaviors governed consistently?

## 9. Data and file contracts

- Are project, flow, template, role, skill, artifact, export, and evidence schemas owned in one place?
- Are directory rules, version fields, and upgrade/repair behaviors explicit?
- Can another implementer rebuild storage layout without guessing?

## 10. Persistence and recovery

- Are save, autosave, snapshot, rollback, resume, and crash-recovery paths complete?
- Are destructive operations staged or rollback-safe?
- Is user external file modification detected and propagated?

## 11. Governance and trust

- Are import trust, side-effect approval, audit evidence, and permission boundaries executable?
- Are approvals bound to scope and expiry?
- Do tests prove blocked and unhappy paths?

## 12. Security and abuse resistance

- Are local package ingestion, script execution, path handling, and prompt-driven actions constrained?
- Are obvious abuse paths documented and defended?
- Is the product safe by default for local-only operation?

## 13. Cohesion and coupling

- Are shell files thin enough?
- Does each service have one clear responsibility?
- Is validation/persistence/recovery/error mapping centrally owned instead of duplicated?

## 14. Testing and oracle quality

- Do tests cover happy path, negative path, destructive path, and recovery path?
- Are there oracle-style assertions on persisted files, error codes, and UI feedback?
- Could major structural drift still pass current tests?

## 15. Traceability

- Can each important requirement be traced to feature, design, code, and tests?
- Are there open gaps where docs promise behavior with no implementation owner?
- Do review records and matrices reflect current truth?

## 16. Delivery readiness

- Can another team or AI reproduce the product behavior from docs?
- Is the current codebase safe to extend without major boundary rewrites?
- What are the top three blockers to reliable next-stage development?
