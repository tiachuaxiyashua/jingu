## 1. Runtime Repair Routing

- [x] 1.1 Locate deterministic child-package rejection paths and preserve existing visible block behavior behind repair-budget exhaustion.
- [x] 1.2 Implement a generic deterministic package repair loop that creates repair jobs with failure evidence and raw candidate content.
- [x] 1.3 Submit repaired packages back to the original child through deterministic guardrails and then existing independent review.

## 2. Observability

- [x] 2.1 Record structured flow events and readable Chinese log entries for deterministic repair request, response, submission, rejection, and limit paths.
- [x] 2.2 Ensure repair events include source job, target job, attempt index, failure source, and failure reason without embedding task-domain literals.

## 3. Evidence And Verification

- [x] 3.1 Add regression coverage for deterministic package failure repaired into an accepted child package.
- [x] 3.2 Add regression coverage for repeated deterministic repair failure reaching the repair limit and blocking the original child once.
- [x] 3.3 Run focused tests, full tests, compile check, OpenSpec validation, and hardcoding scan.
