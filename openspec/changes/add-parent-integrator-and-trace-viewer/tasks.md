## 1. Parent Integration Runtime

- [x] 1.1 Add flow event names, labels, fields, and tree mirror actions for parent integration request, response, candidate submission, rejection, skip, and follow-up registration.
- [x] 1.2 Build parent integrator provider messages with accepted child packages, parent contract, root candidate, parent re-evaluation, and strict JSON schema.
- [x] 1.3 Parse and validate parent integration output with integrated candidate text, consumed child jobs, evidence, open gaps, and suggested follow-up jobs.
- [x] 1.4 Submit valid parent integration output as parent candidate and evidence without accepting parent or root.
- [x] 1.5 Run split proposal registration from the parent integration candidate and record skip/reject outcomes.

## 2. Risk Fixes

- [x] 2.1 Ensure parent integration only consumes accepted child packages and logs skip when only candidate or rejected child packages exist.
- [x] 2.2 Ensure invalid parent integration output is logged and does not mutate parent candidate state.
- [x] 2.3 Keep parent/root completion authority separate from integration success.

## 3. Trace Viewer

- [x] 3.1 Redesign `index.html` layout to include step timeline, job tree, current-step IO/action/evidence/status panes, selected job detail, and raw JSON.
- [x] 3.2 Extend `viewer.js` projection with step classification, input/output/evidence extraction, integration/review milestones, state transition summaries, and unknown event fallback.
- [x] 3.3 Update CSS for dense operational trace readability without nested cards or decorative layout.
- [x] 3.4 Update viewer README and validation script to cover child review and parent integration traces.

## 4. Validation

- [x] 4.1 Add unit tests for parent integration success, integration skip, invalid integration output, and parent/root not auto-accepted.
- [x] 4.2 Add viewer projection tests for step-level trace, child package review, and parent integration milestones.
- [x] 4.3 Run OpenSpec validation, Python tests, viewer validation, compile checks, and hardcoding scan.
- [x] 4.4 Manually exercise a task and verify logs plus viewer projection show clear input/output/action/evidence traces and no乱码.
