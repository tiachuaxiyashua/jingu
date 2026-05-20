## ADDED Requirements

### Requirement: Verification result feeds repair routing
The candidate verification flow SHALL return structured routing data that allows the AI sandbox to decide whether to create a repair job, stop, or create feedback-decision evidence.

#### Scenario: Failed verification has repairable checks
- **WHEN** deterministic verification completes with failed repairable checks
- **THEN** the result MUST expose the failed check kinds, measured facts, expected constraints, and report reference needed by the repair loop.

#### Scenario: Verification is not repairable
- **WHEN** deterministic verification completes without repairable failed checks
- **THEN** the result MUST preserve unsupported gaps or non-repairable reasons so the repair loop can create feedback-decision evidence instead of guessing.

### Requirement: Verification remains non-authoritative
The verification job SHALL continue to provide evidence and SHALL NOT accept, reject, or overwrite the parent candidate.

#### Scenario: Repair candidate verification passes
- **WHEN** a repair candidate passes deterministic verification
- **THEN** the parent and repair candidates MUST remain candidate records, and acceptance or rejection MUST still require a separate responsible action.
