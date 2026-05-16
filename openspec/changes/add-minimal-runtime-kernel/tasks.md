## 1. Project Setup

- [x] 1.1 Add Python packaging and test configuration.
- [x] 1.2 Add version-control ignore rules for local Jingu runtime state and generated caches.
- [x] 1.3 Create the `jingu` package and runtime module skeleton.
- [x] 1.4 Add a repo-appropriate hardcoding scan command for the first runtime codebase.

## 2. Runtime Storage

- [x] 2.1 Implement runtime path resolution and idempotent initialization.
- [x] 2.2 Implement SQLite schema creation for jobs, appearances, and append-only events.
- [x] 2.3 Implement filesystem object-store writes with checksums.

## 3. Kernel Services

- [x] 3.1 Implement repository operations for jobs, appearances, and events.
- [x] 3.2 Implement state-machine transition validation.
- [x] 3.3 Implement guardkeeper checks for first-stage hard failures.
- [x] 3.4 Implement runtime service methods for root-job creation, readiness, running, candidate submission, evidence submission, acceptance, rejection, status, and event listing.

## 4. CLI

- [x] 4.1 Implement `jingu init`.
- [x] 4.2 Implement root-job and job-state CLI commands.
- [x] 4.3 Implement candidate, evidence, accept, reject, status, and events CLI commands.

## 5. Verification

- [x] 5.1 Add tests for runtime initialization and root-job creation.
- [x] 5.2 Add tests for append-only events and state transitions.
- [x] 5.3 Add tests for candidate isolation and evidence-backed acceptance.
- [x] 5.4 Add tests for guardkeeper hard failures.
- [x] 5.5 Run OpenSpec validation, the automated test suite, and the hardcoding scan.
