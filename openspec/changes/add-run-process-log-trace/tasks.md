## 1. Flow Event Contract

- [x] 1.1 Add generic process-step and input-provenance event names, Chinese readable labels, and field labels.
- [x] 1.2 Add generic input provenance helper that records size, line count, digest, and structure flags without domain-specific detection.

## 2. Sandbox Runner Trace

- [x] 2.1 Emit process-step and input-provenance events in one-shot AI runs.
- [x] 2.2 Emit process-step and input-provenance events in interactive chat sessions and turns.

## 3. Verification

- [x] 3.1 Extend sandbox tests to assert process trace and input provenance are persisted in JSONL and readable logs.
- [x] 3.2 Run targeted tests, compile checks, OpenSpec validation, and hardcoding scan.
