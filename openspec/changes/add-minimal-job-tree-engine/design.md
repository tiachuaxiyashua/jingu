## Context

The current runtime kernel already has the physical carriers required by the truth source: jobs, appearances, events, parent job id, root job id, and an object store. It can prove a single manual job loop, but it cannot yet expose a real job tree workflow.

The truth source says the next step is not a full scheduler or a method-specific pipeline. The next step is a minimum true tree: root, parent, child, completion ownership, structured result packages, and parent re-evaluation. It also says Neidan Method is a callable method, not the center of the job tree engine.

## Goals / Non-Goals

**Goals:**

- Preserve real parent-child job structure in runtime queries.
- Add guarded split proposals so an actor cannot create decorative child jobs without a blocking reason, independent output, acceptance criteria, and budget/depth fit.
- Add an active frontier view for the currently unresolved leaf jobs.
- Add structured result packages for child jobs so a parent can inspect conclusion, artifact references, evidence, open questions, and suggested follow-up jobs.
- Add a parent re-evaluation view showing child states, unresolved gaps, open questions, and whether the parent has enough evidence to move toward completion.
- Add CLI commands for manual functional validation.

**Non-Goals:**

- No automatic AI decomposition.
- No parallel scheduler.
- No hardcoded Neidan Method workflow.
- No method registry or stable law registry in this change.
- No UI.

## Decisions

### Keep the schema minimal

The existing `jobs`, `appearances`, and `events` tables already satisfy the truth source's first physical-carrier rule. This change will not add a new table unless the current carriers fail a concrete requirement.

Structured result packages will be stored as candidate result appearances with JSON content and a metadata marker. Evidence will remain a separate evidence appearance. This keeps candidate isolation and evidence-backed acceptance intact.

### Add a runtime tree service layer

The implementation will add a small tree-focused service over `RuntimeService` rather than bypassing the existing service. The tree layer will:

- call existing root and child job creation methods;
- validate split proposals before creating child jobs;
- call existing candidate and evidence submission methods for packages;
- query jobs and events through the repository.

This avoids a second source of truth.

### Split proposal guard fields

A split proposal must include enough data for a deterministic guard:

- parent job id;
- target;
- blocking reason;
- output contract;
- acceptance criteria;
- estimated effort;
- depth limit;
- duplicate check against existing sibling targets.

The guard does not decide whether the content is wise. It blocks clearly non-executable or decorative splits. High-value semantics remain a separate later capability.

### Frontier is a query projection

The active frontier is not a stored queue in this change. It is computed from the tree:

- a job is active when it is not accepted, rejected, or abandoned;
- a leaf active job is on the frontier;
- jobs with required context gaps expose those gaps in the frontier entry.

This preserves the truth source distinction that `业网` and `镜` are projections, not new facts.

### Neidan validation is data-driven

The engine will not contain Neidan-specific step names. A user can validate Neidan Method by creating a root job whose target and acceptance criteria describe that validation, proposing child jobs for method phases, submitting structured packages, and inspecting parent re-evaluation.

Automated tests may use neutral method-validation examples, but the engine must not depend on those names.

## Risks / Trade-offs

- Computed frontier may be too simple for future scheduling -> It is enough for manual validation and can later be replaced by a scheduler without changing stored facts.
- JSON packages can drift -> Validate a small required envelope and leave method-specific content inside a user-provided payload.
- Guard fields may be conservative -> Better to block vague splits now than to let the system become decorative task nesting.
- Parent re-evaluation is not acceptance -> It is a mirror/query view. Acceptance still uses existing candidate plus evidence guardrails.

## Migration Plan

1. Add tree projection and split proposal service methods.
2. Add structured result package submission and validation.
3. Add CLI commands for split proposal, tree view, frontier view, package submission, and parent re-evaluation.
4. Add tests for guard failures, real tree preservation, package submission, and method-validation representation.
5. Run compile checks, tests, OpenSpec validation, and hardcoding scan.

Rollback is file-level: remove the new tree service, CLI commands, tests, and OpenSpec change. No schema migration is expected.
