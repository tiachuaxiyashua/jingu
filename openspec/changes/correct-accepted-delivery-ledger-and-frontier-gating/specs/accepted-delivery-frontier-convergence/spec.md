## ADDED Requirements

### Requirement: Accepted contribution delivery accounting
For a quantitative text delivery contract, the sandbox SHALL calculate accumulated delivery progress from explicitly identified delivery contributions in accepted child result packages and SHALL retain source job and result appearance references for each counted contribution.

#### Scenario: Parent integration does not reduce accepted delivery progress
- **GIVEN** an accepted child result package contains a delivery contribution with measurable text
- **WHEN** the parent integration submits a candidate whose explanatory text is shorter than that contribution
- **THEN** the accumulated delivery count remains based on the accepted contribution
- **AND** the log records the contribution provenance and current remaining quantity.

#### Scenario: Support materials are excluded
- **GIVEN** an accepted child result package contains support artifacts and a separately marked delivery contribution
- **WHEN** the quantitative delivery ledger is computed
- **THEN** only the marked delivered text is counted toward the minimum
- **AND** support material is not counted solely because it appears in the package.

### Requirement: Observable contribution contract
New child result packages created for sandbox execution SHALL include a `delivery_contributions` list, which MAY be empty for a support-only result, and the independent child-package review SHALL consider whether claimed delivery contributions are consumable parent-delivery content.

#### Scenario: Delivery-producing child is reviewed
- **WHEN** a child job claims that text advances a parent quantitative delivery target
- **THEN** its result package includes the claimed contribution text and identifier
- **AND** the independent review can repair or refuse consumption when the claimed contribution is not supported by the child contract.

### Requirement: Controlled incomplete-delivery frontier
While an accumulated quantitative delivery ledger is below its minimum, the sandbox SHALL allow no more than one newly registered critical delivery advancement or delivery-unblocking child for the same parent registration cycle, and SHALL NOT activate non-critical or duplicate proposals from that cycle.

#### Scenario: Additional split proposals are parked
- **GIVEN** the parent quantitative delivery ledger is below minimum
- **AND** split extraction proposes direct delivery work together with non-critical or overlapping work
- **WHEN** split registration is applied
- **THEN** at most one declared critical delivery proposal becomes active
- **AND** other proposals are recorded as parked with their gating reason.

#### Scenario: Completion-only proposal falls back to continuation
- **GIVEN** the parent quantitative delivery ledger is below minimum
- **AND** split extraction proposes work but all proposals are completion-dependent, non-critical, or duplicate critical work
- **WHEN** split registration is applied
- **THEN** the sandbox registers one delivery-continuation child from the ledger
- **AND** the run advances through that child instead of verifying the incomplete parent candidate as final output.

#### Scenario: Deterministic continuation already occupies the frontier
- **GIVEN** parent integration has registered a delivery-continuation child because the accepted accumulated delivery is below minimum
- **WHEN** the runtime would otherwise extract another set of follow-up splits from that same integration candidate
- **THEN** it skips the duplicate extraction ingress
- **AND** logs why the existing critical continuation remains the active frontier.

#### Scenario: Accepted child package returns before further splitting
- **GIVEN** a child job submits a structured result package and the package review accepts it within the child responsibility scope
- **WHEN** the package contains open questions or suggested follow-up jobs
- **THEN** the sandbox accepts the child package and returns it to the parent before registering any new follow-up work
- **AND** follow-up work is registered from the parent integration scope rather than as descendants of the already accepted child.

#### Scenario: Auto-continue pauses after measurable delivery progress
- **GIVEN** auto-continue is enabled for a root job with a quantitative text target
- **AND** a command accepts one or more delivery contributions while the accumulated ledger remains below the minimum
- **WHEN** runnable continuation work still exists
- **THEN** the sandbox pauses at the batch boundary, records a runtime checkpoint, and does not dispatch the next delivery continuation in the same command.

#### Scenario: Readable log compacts provider stream deltas
- **GIVEN** a provider streams reasoning or content deltas
- **WHEN** the sandbox records the run logs
- **THEN** the JSONL machine ledger retains the delta events
- **AND** the Markdown readable log avoids expanding every delta into a full human-readable section.
