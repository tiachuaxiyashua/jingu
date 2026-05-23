## 1. Review Logging

- [x] 1.1 Add flow event names, readable labels, fields, and block rendering for child package review request, response, accepted, repair requested, repair response, repair rejected, repair limit, and accepted parent re-evaluation.
- [x] 1.2 Add tree mirror actions for child package review, acceptance, repair job creation, repair package submission, and accepted parent re-evaluation.

## 2. Review Contract

- [x] 2.1 Build child package review provider messages with child contract, package, evidence, parent context, and a strict JSON review schema.
- [x] 2.2 Parse and validate review judgments with action `accept` or `repair`, structured checks, evidence, repair instruction, and parent consumption summary.

## 3. Acceptance And Repair Loop

- [x] 3.1 Accept reviewed child package candidates through `RuntimeService.accept_candidate` and record acceptance evidence.
- [x] 3.2 On repair judgment, reject the current child candidate, create a repair child job, start it, request a repaired package, and submit the repaired package back to the original child job.
- [x] 3.3 Re-run review once after repair and stop without completion if the repaired package is invalid or not accepted.
- [x] 3.4 Record parent re-evaluation after accepted child packages so accepted results become visible to the parent job.

## 4. Integration

- [x] 4.1 Integrate child package review loop into frontier dispatch after package submission and before child split proposal registration.
- [x] 4.2 Ensure child split proposal registration runs only from the latest accepted package; unresolved packages remain logged but not consumed.

## 5. Validation

- [x] 5.1 Add unit tests for direct acceptance, repair then acceptance, invalid review response, and repair limit behavior.
- [x] 5.2 Run OpenSpec validation, unit tests, compile checks, and hardcoding scan.
- [x] 5.3 Manually exercise a task and verify logs show review request, accept/repair, accepted parent re-evaluation, accepted child result, and no乱码.
