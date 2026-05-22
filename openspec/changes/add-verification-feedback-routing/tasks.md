## 1. OpenSpec And Runtime Contract

- [x] 1.1 Complete the OpenSpec specs for verification-aware acceptance routing.
- [x] 1.2 Add shared routing data structures, parser, prompt builder, and log payloads.

## 2. Routing Implementation

- [x] 2.1 Wire `ai run` to call the acceptance router after deterministic verification and repair.
- [x] 2.2 Wire `ai chat` to use the same router and update chat history with routed repair output.
- [x] 2.3 Add one-shot acceptance-role executor repair when the router chooses repair.
- [x] 2.4 Create feedback child jobs when the router chooses high-value or directional feedback.

## 3. Observability And Validation

- [x] 3.1 Extend readable and JSONL logs for routing requests, judgments, repair打回, skip evidence, and feedback jobs.
- [x] 3.2 Add tests for run feedback routing, run executor repair routing, chat shared routing, and skip evidence.
- [x] 3.3 Run OpenSpec validation, unit tests, compile checks, and the hardcoding scanner.
- [x] 3.4 Harden acceptance routing against real-provider JSON shape drift and rerun real-model evidence.
