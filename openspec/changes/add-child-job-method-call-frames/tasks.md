## 1. Method Call Frame Runtime

- [x] 1.1 Add method call frame event constants and runtime payload validation.
- [x] 1.2 Extend method-law binding so callers can append a method call frame event for the same job.
- [x] 1.3 Project method call frames into tree summaries and parent re-evaluation output.

## 2. Child Job Method Binding

- [x] 2.1 Extend `TreeService.propose_child_job` to accept optional method binding fields and reject incomplete method bindings before creating a child job.
- [x] 2.2 Extend the `tree propose-child` CLI with method binding arguments and include binding output in JSON results.
- [x] 2.3 Ensure parent jobs do not inherit child method bindings in `tree show`.

## 3. Flow Logging

- [x] 3.1 Add machine and readable log labels for method call frame events.
- [x] 3.2 Record root sandbox method calls as call frames without adding multi-method composition.

## 4. Independent Methods

- [x] 4.1 Keep PDCA 法, 控制变量法, and 辩证法 as independent skill method files.
- [x] 4.2 Verify each new method file loads through the existing method loader.

## 5. Validation

- [x] 5.1 Add focused runtime and CLI tests for child method binding and method call frame projection.
- [x] 5.2 Run OpenSpec validation for `add-child-job-method-call-frames`.
- [x] 5.3 Run Python unit tests and compile checks.
- [x] 5.4 Run hardcoding scan after code changes.
