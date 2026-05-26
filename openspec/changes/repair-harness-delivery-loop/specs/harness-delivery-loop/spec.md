## ADDED Requirements

### Requirement: Quantitative text delivery ledger

The AI sandbox SHALL derive a delivery ledger from the root task and current candidate when the task contains a deterministic text-length target.

#### Scenario: Chinese magnitude range is parsed

- **GIVEN** the root task says `10万字到20万字`
- **WHEN** the sandbox verifies or advances a candidate
- **THEN** the ledger records a minimum of 100000 CJK characters and a maximum of 200000 CJK characters
- **AND** a candidate below the minimum is marked `below_minimum`

### Requirement: Critical-path follow-up routing

Parent integration SHALL NOT register every open gap as an active child when the root quantitative delivery ledger is still below its minimum.

#### Scenario: incomplete delivery parks non-critical follow-ups

- **GIVEN** a parent integration candidate remains below the root delivery minimum
- **AND** the integration reports open gaps and suggested follow-up jobs
- **WHEN** follow-up registration runs
- **THEN** the sandbox registers a delivery-continuation child job
- **AND** parks the reported gaps as visible backlog instead of active frontier jobs

### Requirement: Premature completion split rejection

The split registration path SHALL reject child proposals that require the root quantitative delivery target to already be complete while the current candidate is below its minimum.

#### Scenario: final manuscript child is proposed before minimum delivery

- **GIVEN** the root task has a quantitative text range
- **AND** the current candidate is below the minimum
- **WHEN** a split proposal requires that same full range as its own acceptance criterion
- **THEN** the proposal is rejected
- **AND** production or batch-continuation children may still be accepted.
