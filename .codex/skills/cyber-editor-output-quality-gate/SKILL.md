---
name: cyber-editor-output-quality-gate
description: Review Cyber Editor generated documents and delivery artifacts with a 0-100 quality rubric, anti-false-green checks, and core-vs-assistive gating. Use when judging AI output quality, deciding whether a generated artifact is deliverable, or validating that a change did not silently degrade user-facing content.
---

# Cyber Editor Output Quality Gate

Use this skill whenever the task is not only "did a file get generated?" but "is the generated artifact actually good enough to count as success?"

## When To Use

Use this skill for:
- AI-generated requirements, clarification docs, feature trees, feature lists, solutions, test plans, delivery summaries
- regression evidence review after implementation
- real-model output sampling before archive
- user-journey validation where output quality matters more than mechanical completion

Do not use this skill only for existence checks. This skill is specifically for quality gating.

## Core Rule

Never treat a generated artifact as successful only because:
- the file exists
- the headings exist
- the export exists
- the workflow reached a completed state

The artifact must also pass a quality review.

## Quality Scale

Interpret the 0-100 score as:
- `90-100`: `excellent`，可直接交付
- `80-89`: `strong`，质量高，可作为成功输出
- `72-79`: `acceptable`，达到严格核心工件最低阈值
- `60-71`: `weak`，结构或内容明显不足，需要人工修复
- `0-59`: `critical`，不能视为成功交付

Read the score together with five dimensions:
- `completeness`: 内容是否足够完整，不是只写一句话
- `structure`: 标题、列表、整体组织是否清晰
- `specificity`: 是否包含具体对象、约束、路径、证据、术语
- `actionability`: 是否包含可执行信息，如输入输出、约束、验证、恢复、下一步
- `hygiene`: 是否存在 fallback、placeholder、过量样板或脏内容

Hard-fail regardless of score when a core artifact contains:
- deterministic fallback markers
- obvious placeholder boilerplate
- empty or nearly empty sections that only restate the heading

## Core vs Assistive

Treat artifacts in two tiers:

- `strict/core`
  - requirements
  - clarification
  - feature tree
  - feature list
  - solution docs
  - test plans
  - delivery summaries
  - Rule: `pass` only when the score is high enough and no hard-fail markers appear.

- `assistive`
  - helper diagrams
  - issue lists
  - UI preview helper artifacts
  - Rule: degraded output may be tolerated temporarily, but it must still be visible as degraded.

## Required Workflow

### 1. Identify the artifact tier
- Decide whether the artifact is `strict/core` or `assistive`.
- If unsure, bias toward `strict/core` for anything a user would directly read as the final answer.

### 2. Run the quality review script
- Single file:
  - `npm run review:output-quality -- <file>`
- Multiple files:
  - `node scripts/output-quality-review.mjs <file1> <file2> ...`
- Assistive review:
  - `node scripts/output-quality-review.mjs --assistive <file>`

### 3. Inspect the JSON output
- Read:
  - `verdict`
  - `band`
  - `score`
  - `dimensions`
  - `fallbackHits`
  - `placeholderHits`
  - `reasons`

### 4. Apply the gate
- For `strict/core` artifacts:
  - `fail` means the output is not acceptable
  - `warn` means manual inspection is required before calling it complete
  - `pass` means it can count as success
- For `assistive` artifacts:
  - `fail` blocks if the artifact is required for progression
  - `warn` is acceptable only when the degraded state is visible

### 5. Sample the actual content
- For any high-risk change or real-model run, open the artifact itself.
- Do not rely only on the numeric score.
- Confirm the document is specific, not just well-shaped.

## What To Report

Always report:
- which files were reviewed
- strict/core or assistive classification
- score, band, and dimensions for each
- the first 1-3 reasons for any warn/fail
- whether the output is acceptable, degraded, or blocked

## Repo Paths

- Quality review CLI:
  - `scripts/output-quality-review.mjs`
- Shared rubric:
  - `scripts/lib/output-quality-review.mjs`
- Runtime validator:
  - `src/shared/artifact-validators.ts`
- Fixed regression:
  - `npm run test:post-change-extreme`
- Evidence root:
  - `artifacts/post-change-extreme-validation/`
