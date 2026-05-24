## ADDED Requirements

### Requirement: Split decisions are enforced as a law
The runtime SHALL enforce child-job split decisions through an explicit split decision law in the existing job-tree proposal path, rather than through a new standalone component.

#### Scenario: Valid split law creates child work
- **WHEN** a child-job proposal states that the child blocks parent execution, parent acceptance, requires distinct capability, or carries high-value/risk grounds
- **AND** the proposal states that the child can produce an independent parent-consumable result package
- **THEN** the existing tree service can register the child job when other depth, duplicate, and method-binding checks pass.

#### Scenario: Decorative split is rejected
- **WHEN** a child-job proposal has no execution, acceptance, capability, or high-value/risk ground
- **THEN** the runtime rejects the proposal before creating a child job.

#### Scenario: Non-consumable split is rejected
- **WHEN** a child-job proposal cannot produce an independent result package consumable by the parent
- **THEN** the runtime rejects the proposal before creating a child job.

### Requirement: AI split proposals expose the law judgment
The AI split proposal contract SHALL require a `split_law` object with the five law judgments and a reason.

#### Scenario: Missing split law is rejected
- **WHEN** an AI split proposal omits `split_law`
- **THEN** proposal normalization rejects the proposal and logs the rejection reason.

#### Scenario: Accepted split records the law
- **WHEN** an AI split proposal passes the law and other guard checks
- **THEN** JSONL and readable logs include the split-law object for user inspection.
