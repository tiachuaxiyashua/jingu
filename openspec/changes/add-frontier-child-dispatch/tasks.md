## 1. Frontier Dispatch Logging

- [x] 1.1 Add flow event names, readable labels, and fields for frontier dispatch start, skip, child start, child response, package submission, package rejection, parent re-evaluation, and dispatch finish.
- [x] 1.2 Add tree mirror actions for child dispatch and parent re-evaluation.

## 2. Child Execution

- [x] 2.1 Read child method context from the child method call frame, falling back to the root method.
- [x] 2.2 Build child execution provider messages requiring a structured result package.
- [x] 2.3 Mark selected child jobs ready/running and submit valid packages through `TreeService.submit_result_package`.
- [x] 2.4 Record invalid package responses without completing child or parent jobs.

## 3. Backflow and Next-Level Registration

- [x] 3.1 Record `TreeService.reevaluate_parent` output after each submitted child package.
- [x] 3.2 Run split proposal registration for dispatched child packages so grandchildren can be registered but not executed in the same pass.
- [x] 3.3 Integrate frontier dispatch into `ai run` and `ai chat` after root split registration.

## 4. Validation

- [x] 4.1 Add unit tests for child package submission, parent re-evaluation log, and grandchild registration.
- [x] 4.2 Run OpenSpec validation, unit tests, compile checks, and hardcoding scan.
- [x] 4.3 Manually exercise a complex task and verify increased job count, child package log, parent re-evaluation, and no乱码.
