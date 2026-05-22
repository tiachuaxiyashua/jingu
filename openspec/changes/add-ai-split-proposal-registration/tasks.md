## 1. Split Proposal Extraction

- [x] 1.1 Add flow event names, readable labels, and fields for split proposal request, response, accepted registration, rejected registration, and skipped registration.
- [x] 1.2 Add method catalog discovery from local method/skill files without hardcoding specific法 names.
- [x] 1.3 Build split proposal provider messages with user input, candidate response, parent job id, root method manifest, and method catalog.

## 2. Guarded Registration

- [x] 2.1 Parse split proposal JSON and validate the top-level shape.
- [x] 2.2 Register valid proposals through `TreeService.propose_child_job`.
- [x] 2.3 Reject proposals with missing fields, duplicate sibling targets, unavailable methods, or guardrail failures without creating child jobs.

## 3. Sandbox Integration

- [x] 3.1 Run split proposal registration after candidate submission and before candidate verification in `ai run`.
- [x] 3.2 Run split proposal registration after candidate submission and before candidate verification in interactive `ai chat`.
- [x] 3.3 Ensure normal output still returns only the candidate result, not registration diagnostics.

## 4. Validation

- [x] 4.1 Add tests for accepted proposal registration, rejected proposals, and tree snapshot method call frames.
- [x] 4.2 Validate OpenSpec, run unit tests, compile checks, and hardcoding scan.
- [x] 4.3 Manually exercise a complex task with accepted child method bindings and inspect the log/tree evidence.
