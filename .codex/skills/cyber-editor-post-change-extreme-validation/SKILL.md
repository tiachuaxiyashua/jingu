---
name: cyber-editor-post-change-extreme-validation
description: Run Cyber Editor post-change regression and extreme validation after implementation, before archiving a change, or whenever orchestration runtime, AI integration, knowledge indexing, rerun/recovery, or document-generation behavior may have changed. Use to summarize what is testable, run the required commands, inspect the evidence pack under `artifacts/post-change-extreme-validation/`, review output quality, and iterate until actual results match expected behavior.
---

# Cyber Editor Post Change Extreme Validation

Use this skill as the fixed regression workflow after any non-trivial change. The goal is not only “tests pass”, but “the product remains usable under extreme paths and we have evidence for it”.

## Workflow

### 1. Summarize what changed and what must be testable
- Read the active change, changed modules, and any updated docs.
- State which user-visible paths are now expected to work.
- Separate:
  - baseline paths: lint, unit, build, core e2e
  - high-risk paths: orchestration runtime, approval, loop/parallel/subflow, rerun, snapshot restore, knowledge index refresh, real-model delivery

### 2. Run the baseline commands
- Run `npm run lint`
- Run `npm run test:unit`
- Run `npm run build`
- Run targeted Playwright specs when the changed scope is narrower than a full suite.

### 3. Run the extreme validation pack
- Run `npm run test:post-change-extreme`
- This calls `scripts/run-post-change-extreme-validation.mjs`
- Treat this run as mandatory when the change touches:
  - orchestration runtime semantics
  - AI integration or provider routing
  - runtime governance or approvals
  - document generation / rerun / export
  - knowledge index refresh or note-reference logic

### 4. Inspect the evidence pack
- Open the newest folder under `artifacts/post-change-extreme-validation/`
- Read `summary.json`
- For every failed or suspicious scenario, inspect that scenario folder:
  - `report.md`
  - `result.json`
  - generated runtime/workspace outputs
- For `real-qwen-closed-loop-delivery`, also inspect `doc-quality-review.json`
- When output quality matters, also use the repo-local skill `cyber-editor-output-quality-gate` or run `npm run review:output-quality -- <file>` on the core artifacts directly
- Read output quality as:
  - `score`
  - `band`
  - `dimensions`
  - `verdict`
  not just a single pass/fail bit

### 5. Judge failures correctly
- Distinguish product defects from fixture defects.
- Before changing product code, verify the exact runtime input that reached the failing call.
- If a validator fails, inspect the concrete artifact on disk first.
- If a scenario fixture is invalid, fix the fixture and rerun. Do not misreport it as a product regression.

### 6. Close the loop
- Iterate until expected behavior, test results, and evidence are aligned.
- Then backwrite:
  - change tasks
  - feature status docs
  - trace/evidence matrices
- Do not mark a runtime-heavy change complete if the evidence pack is missing or partially red.
- Do not archive a change if strict/core artifacts are mechanically present but quality-gate review returns `fail`.

## Output Requirements
- Always report:
  - what can now be tested
  - which commands were run
  - where the newest evidence pack lives
  - which scenarios passed
  - any remaining partial/unfinished areas
- If the suite is not fully green, list the failing scenarios and whether each is:
  - product bug
  - fixture bug
  - environment issue

## Repo Paths
- Script: `scripts/run-post-change-extreme-validation.mjs`
- Wrapper command: `npm run test:post-change-extreme`
- Evidence root: `artifacts/post-change-extreme-validation/`
- Related docs:
  - `docs/12-自动化测试总册.md`
  - `docs/14-代码测试运行证据矩阵.md`
  - `docs/15-MSA-trace-matrix.md`
