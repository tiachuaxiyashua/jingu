---
name: cyber-editor-anti-hardcode-gate
description: Run Cyber Editor anti-hardcode review when generic runtime, UI, orchestration, provider, template, or export code changes may have reintroduced template-specific paths, duplicated provider defaults, or business literals into code. Use before archiving a change, after refactors, or whenever the user asks to eliminate hardcoding.
---

# Cyber Editor Anti-hardcode Gate

Use this skill when the task involves:
- generic runtime services
- provider configuration
- orchestration/workbench refactors
- template import/export behavior
- hardcoding audits requested by the user

## Goal

Prevent three recurring failure modes:
1. Template truth is duplicated in generic services instead of living in template packages or runtime contracts.
2. Provider truth is duplicated across store, UI, and runtime instead of living in `src/shared/provider-registry.ts`.
3. A happy-path implementation passes software-factory tests but silently breaks other templates or future imports.

## Definition

Hardcoding means putting mutable truth directly into generic code, when that truth should instead come from configuration, template packages, registries, schemas, user input, or runtime state.

Short form:
- hardcoding = writing changeable truth into code that does not own it

Typical hardcoding in this repo:
- fixed template directories in generic services
- duplicated provider defaults across renderer/main/store
- business artifact names embedded in generic runtime paths
- product behavior that only works for one template id

Not hardcoding:
- stable internal protocol constants that are truly platform-owned
- error codes, state enums, and persistence file names that are part of the platform contract
- built-in assets that live as data packages rather than scattered branch logic

## Why hardcoding kept recurring

The recurring cause is structural:
1. More than one source of truth existed for the same concept.
   - Provider defaults lived in store, renderer, and runtime at the same time.
   - Template paths lived in template packages and also inside generic services.
2. Tests mostly proved the `software-factory` happy path.
   - A change could look green while still breaking `gstack-office-hours` or any future imported template.
3. Large files hid ownership drift.
   - `App.tsx`, `OrchestrationWorkspace.tsx`, and runtime services mixed generic logic with product-specific fallback knowledge.
4. Previous scans were string hunts, not ownership checks.
   - They found some literals, but they did not force the question: "which module is allowed to own this truth?"

## Ownership model

Before fixing a finding, decide who owns the truth:
- Template directories, stage artifacts, export roots, handoff source docs:
  - owned by template package or runtime template contract
- Provider labels, default URLs, default models, capability metadata, API-key policy:
  - owned by `src/shared/provider-registry.ts`
- Schema-specific fallback structure:
  - owned by schema/template-specific assets, not generic runtime services
- UI labels and badges:
  - rendered from shared registry/helper modules, not local switch blocks

If no owner exists, create one first. Do not add another fallback in-place.

## Workflow

1. Read only the files you are actively changing plus this report output:
   - `artifacts/hardcode-gate/latest.json`
   - `artifacts/hardcode-gate/latest.md`
2. Run the gate:
   - `npm run review:hardcode`
3. Classify each finding:
   - `high`: generic runtime/UI/service code contains template-specific or provider-specific literals. Fix before archive unless explicitly added to accepted debt.
   - `medium`: duplicate labels or copy-level drift. Fix in the same pass when low risk.
   - `accepted debt`: only allowed when the finding is already listed by the script as known debt, with a concrete migration reason.
4. Fix by ownership, not by search-and-replace:
   - Template-specific truth moves to template package, runtime template contract, or template-aware manifest.
   - Provider-specific truth moves to `src/shared/provider-registry.ts`.
   - UI labels render from a shared registry/helper, not local switch blocks.
5. Re-run:
   - `npm run review:hardcode`
   - `npx tsc --noEmit`
   - any targeted tests touched by the refactor

## Required review questions

Before closing the change, answer all of these with evidence:
1. Can a second template package pass this code path without changing generic code?
2. Can a second provider profile pass this code path without changing generic code?
3. If a literal remains, is it owned by a schema/template asset instead of a generic service?
4. Does at least one non-default template test cover the path?
5. Does the report show any new `high` finding outside accepted debt?
6. If the business changes, can this behavior be updated by editing data/asset/config instead of editing generic code?

If any answer is "no", the change is not ready to archive.

## Non-negotiable rules

- Do not accept “it only happens in software-factory” as a reason to keep a literal in generic code.
- Do not fix by adding another local fallback copy unless the fallback itself is the owned source of truth.
- Do not archive a change with new `high` findings outside accepted debt.

## Current accepted debt

Read the generated report. If a finding is marked `accepted-debt`, it still requires a migration plan; it is not a silent ignore list.
