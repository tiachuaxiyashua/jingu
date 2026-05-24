## ADDED Requirements

### Requirement: Advancement loop controls runtime progress
The sandbox runner SHALL advance jobs through one runtime loop where every accepted child package, parent integration, verification result, repair, feedback request, and follow-up job becomes new observable job-tree state.

#### Scenario: Follow-up job registered during integration
- **WHEN** parent integration registers follow-up jobs
- **THEN** the advancement loop MUST treat those jobs as frontier work in a later loop step unless the run pauses or blocks first

#### Scenario: Runner invokes advancement
- **WHEN** the sandbox runner executes a task
- **THEN** the runner MUST delegate job progress to the advancement loop instead of relying on a fixed one-shot phase sequence to imply task completion

### Requirement: Budget exhaustion pauses, not completes
Advancement budgets SHALL limit how much work happens in one run, but reaching a budget MUST produce a paused outcome when active work remains.

#### Scenario: Wave budget exhausted with active frontier
- **WHEN** the advancement loop reaches the wave budget and active frontier jobs still exist
- **THEN** the loop outcome MUST be `paused` and the log MUST record remaining frontier job identifiers and the reason

#### Scenario: Dispatch budget exhausted with unselected frontier
- **WHEN** the dispatch limit selects only part of the active frontier
- **THEN** the loop MUST preserve the unselected jobs as remaining frontier work instead of treating the run as complete

### Requirement: Blocked jobs remain visible as blocked state
Jobs with unresolved context gaps SHALL be represented as blocked frontier state rather than generic child-result rejection.

#### Scenario: Frontier job has context gaps
- **WHEN** a frontier job cannot enter `running` because it has `required_context_gaps`
- **THEN** the loop outcome MUST expose the job as blocked with its gaps and MUST NOT present the condition as a completed result package rejection

#### Scenario: No runnable frontier exists
- **WHEN** every active frontier job is blocked by gaps or human decisions
- **THEN** the loop outcome MUST be `blocked` and the log MUST include the blocked jobs and required context gaps

### Requirement: Minimal loop is size-independent
The runtime SHALL treat large tasks as repeated executions of the same minimal loop, not as special-case pipelines.

#### Scenario: Large task creates more work than one run budget
- **WHEN** a task produces more follow-up jobs than one run can execute
- **THEN** the system MUST preserve the root job, active frontier, candidates, evidence, and pause reason so a later run can continue the same tree

#### Scenario: No active work remains
- **WHEN** no active child frontier remains and the latest parent candidate is available
- **THEN** the loop MAY report `completed` for the advancement phase without claiming the root job is accepted unless verification and acceptance rules also pass
