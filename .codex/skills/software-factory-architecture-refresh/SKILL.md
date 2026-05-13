---
name: software-factory-architecture-refresh
description: Refresh the Software Factory system-design architecture diagram from current docs and code, outputting a Chinese Flat Icon SVG/PNG plus a status summary. Use when the user asks to draw or update the project system architecture map, rescan docs and `src/` after changes, mark completed vs partial vs unfinished architecture areas, or keep the repo architecture diagram continuously in sync.
---

# Software Factory Architecture Refresh

Generate and refresh the repo's system-design architecture map as a stable artifact, not a one-off sketch.

This skill is specialized for `e:\chuan_project\software_factory`. It rescans the current docs and code, then regenerates:

- Chinese system-design architecture diagram
- Flat Icon SVG
- PNG export
- architecture status summary markdown

## Source Of Truth Order

Use this precedence:

1. `docs/03-架构实现/01-系统架构与分层Owner.md`
2. `docs/03-架构实现/02-AI编排运行时.md`
3. `docs/03-架构实现/03-数据契约状态机与安全.md`
4. `docs/01-需求与PRD/03-功能范围与优先级.md`
5. `docs/02-产品设计/03-关键交互裁决.md`
6. `docs/04-测试验收/01-验收门禁与测试策略.md`
8. `src/renderer/**`
9. `src/main/**`
10. `src/shared/**`

Treat:

- `docs/03-架构实现/` as the system-architecture shape truth
- `docs/01-需求与PRD/03-功能范围与优先级.md` and `docs/04-测试验收/` as the status and proof baseline
- `src/` as implementation ownership
- renderer/main/shared file owners as module granularity

If docs and code disagree, preserve diagram status from `docs/01-需求与PRD/03-功能范围与优先级.md` and note the mismatch in the summary.

## Workflow

### 1. Refresh the diagram

Run:

```powershell
python -X utf8 .codex/skills/software-factory-architecture-refresh/scripts/refresh_architecture_diagram.py
```

This writes:

- `artifacts/architecture/software-factory-architecture.svg`
- `artifacts/architecture/software-factory-architecture.png`
- `artifacts/architecture/software-factory-architecture.data.json`
- `artifacts/architecture/software-factory-architecture-status.md`

Then run the mandatory self-check:

```powershell
python -X utf8 .codex/skills/software-factory-architecture-refresh/scripts/check_architecture_diagram.py
```

Do not deliver the diagram if the self-check fails.

### 2. Follow the first-pass success path

Use this exact path before making any layout or wording changes:

1. Lock the target first:
   - the output must be a **system-design architecture diagram**
   - it must not become a docs-governance map, reading-order map, or doc-directory map
2. Establish the system shape from docs before touching code:
   - read `docs/03-架构实现/01-系统架构与分层Owner.md`
   - read `docs/03-架构实现/02-AI编排运行时.md`
   - read `docs/03-架构实现/03-数据契约状态机与安全.md`
3. Use `docs/01-需求与PRD/03-功能范围与优先级.md` only for status coloring:
   - green/amber/red comes from `已完成 / 部分完成 / 未完成`
   - do not let `docs/01-需求与PRD/03-功能范围与优先级.md` redefine the system layer shape
4. Scan implementation owners from code:
   - include important owner files from `src/renderer`
   - include important owner files from `src/main`
   - include shared contracts from `src/shared`
   - keep module granularity as fine as practical; small but real owner files should still appear
5. Build the diagram with this stable lane model:
   - left column: `Renderer`
   - middle column: `Electron / IPC / Main 平台与工程 / AI`
   - right column: `Main Runtime` plus `文档待补模块`
   - bottom row: `Shared` and `Data`
6. Add doc-defined but not fully landed modules explicitly:
   - context-pack selection UI
   - citation drill-down
   - patch/merge chain
   - invalidation propagation
   - durable run / checkpoint / resume
   - tracing / evaluation
   - local side-effect / trust governance
   - review gate / parity / recovery services
   - rules and distillation center
7. Only after the above is stable, regenerate the PNG and inspect the image.

### 3. Inspect the result

Check that:

- the title and labels stay Chinese
- the layout still shows `Renderer / IPC / Main / Shared / Data / 文档待补模块`
- every important owner file under `src/renderer`, `src/main`, and `src/shared` is still represented
- unfinished architecture blocks still correspond to real `未完成` or `部分完成` IDs
- the summary markdown still points to real code-owner paths

Use these visual acceptance checks:

- the diagram starts from `用户 -> Renderer -> IPC -> Main`
- `Shared` is shown as cross-cutting contracts, not as the main runtime lane
- `Data` is shown as project/evidence/package/provider objects, not as doc folders
- pending modules sit in a clearly separate planned area, not mixed into completed code owners
- the right-side planned modules are derived from the docs, not invented ad hoc
- no top-level container should be named around docs, tests, reviews, or governance unless the user explicitly asked for that view

### 3.5 Mandatory self-check

Self-check is required every time after regenerating the architecture diagram.

Automated checks:

- run `python -X utf8 .codex/skills/software-factory-architecture-refresh/scripts/check_architecture_diagram.py`
- fail if the diagram becomes a wide banner again; keep width/height under the configured threshold
- fail if total node count, total arrow count, or total container count drops below the current architecture baseline
- fail if any top-level container node count drops below its expected minimum
- fail if any module becomes zero-degree / unconnected
- fail if generic English container headers or type badges remain
- fail if extra-wide horizontal cross-lane arrows exceed the configured threshold

Manual visual checks:

- open the generated PNG and confirm the main reading path is top-to-bottom, not left-to-right banner style
- confirm arrows do not overlap badly enough to hide labels or module boundaries
- confirm no section looks visually collapsed, omitted, or obviously smaller than the last successful detailed version
- confirm detailed module coverage is preserved; if the user asked for fine granularity, content regression is a hard failure

If any self-check fails, edit `scripts/refresh_architecture_diagram.py`, regenerate, and rerun the self-check. Do not explain the failure away and do not stop at a partially acceptable image.

### 4. Update the architecture shape only when needed

If the repo gains a new major layer, a new service owner, or a new doc-defined pending module, update the layout/config section inside `scripts/refresh_architecture_diagram.py`, then regenerate.

Do not redraw the whole diagram ad hoc. Keep the script as the reusable source.

## Status Rules

Architecture block status is computed from related IDs in `docs/01-需求与PRD/03-功能范围与优先级.md`:

- any related `未完成` => block is `未完成`
- else any related `部分完成` => block is `部分完成`
- else => block is `已完成`

Manual status is allowed for:

- renderer shell modularization
- IPC boundary shell
- doc-defined pending modules that do not yet have a dedicated `F-*` / `INF-*` row
- entry files or cross-cutting owner files whose status must be tied to a review note

When using manual status, tie it to a real review doc or code fact.

## Success Heuristics

Use these rules to avoid the failure mode that already happened once:

1. If the user says "系统架构", default to runtime/system design, not docs structure.
2. `docs/03-架构实现/` defines the backbone layers and not-yet-fully-landed modules.
3. `docs/01-需求与PRD/03-功能范围与优先级.md` controls scope and priority; it does not replace the architectural decomposition.
4. `src/` decides module ownership and granularity; if a file is an owner, it should usually appear.
5. Tests and review records belong in summary/evidence reasoning, not as the dominant picture, unless the user explicitly asks for a test or governance architecture.

## Anti-Patterns

Do not do these:

- do not put document governance or test evidence as the primary top-level architecture lanes for a system-design request
- do not collapse the system into 5-7 oversized boxes when the user asked for detailed module coverage
- do not infer "implemented" just because a file exists
- do not hide planned modules simply because they are not yet code owners
- do not mix doc-reading guidance into the main diagram body unless it is a separate requested view

## One-Shot Checklist

Before finishing, verify all of the following:

1. The PNG is clearly a system diagram at a glance.
2. The diagram includes module-level boxes for the current code owners.
3. The unfinished area includes doc-defined pending modules from `docs/03-架构实现/`.
4. Status colors still respect `docs/01-需求与PRD/03-功能范围与优先级.md` and test proof.
5. The status summary contains real owner paths.
6. The refresh command succeeds without manual cleanup.
7. The self-check script passes.
8. The PNG has been visually inspected after the final generation, not assumed correct from code alone.

## Resources

### references/

- `style-1-flat-icon.md`: retained Flat Icon style reference distilled from the external Fireworks skill

### scripts/

- `refresh_architecture_diagram.py`: repo-specific refresh entrypoint
- `fireworks_generate_from_template.py`: vendored SVG generator retained so this skill does not depend on the external repo at runtime

## Do Not Do

- do not infer completion from code presence alone
- do not mark a block green when `docs/01-需求与PRD/03-功能范围与优先级.md` still says `部分完成` or `未完成`
- do not drift back to a docs-governance diagram when the user asked for system design architecture
- do not couple this skill to `E:\chuan_project\fireworks-tech-graph-main` after extraction
