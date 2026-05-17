## 1. OpenSpec And Method Configuration

- [x] 1.1 Create the OpenSpec proposal, design, specs, and tasks for the method-driven sandbox loop.
- [x] 1.2 Add repository method pointer data for the default method source.

## 2. Method Loading And Prompt Context

- [x] 2.1 Implement method source resolution from explicit path or repository pointer.
- [x] 2.2 Implement method content loading with checksum, size, and safe failure before provider calls.
- [x] 2.3 Implement generic method system-context assembly for AI requests.

## 3. Sandbox Flow And Evidence

- [x] 3.1 Add flow events for method resolution, loading, context injection, self-review, and update candidates.
- [x] 3.2 Use the method context in one-shot and interactive sandbox AI requests.
- [x] 3.3 Store method self-review and method reference data as evidence without auto-accepting or mutating methods.

## 4. CLI And Launcher

- [x] 4.1 Add method path options to `ai run` and `ai chat`.
- [x] 4.2 Update the one-click PowerShell launcher to show and pass the configured method source.

## 5. Verification

- [x] 5.1 Add tests for method resolution, context injection, flow logging, and launcher dry-run output.
- [x] 5.2 Run OpenSpec validation, automated tests, compile check, manual launcher dry-run, and hardcoding scan.
