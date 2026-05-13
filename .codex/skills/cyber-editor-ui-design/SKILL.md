---
name: cyber-editor-ui-design
description: Use when designing, reviewing, prototyping, or refactoring Cyber Editor UI. Covers page hierarchy, visual discipline, interaction rules, and project-specific anti-patterns for welcome, workbench, orchestration, AI sidebar, resource center, rules center, and settings.
---

# Cyber Editor UI Design

Project-specific UI skill for Cyber Editor. Use this when the task changes how the product looks, feels, or is navigated.

## Source of Truth

For future refactor UI, read `truth/README.md` and the relevant `truth/` files first.

For current legacy Cyber Editor UI maintenance, read these docs depending on the page:

- `docs/README.md`
- `docs/01-需求与PRD/02-用户旅程与信息架构.md`
- `docs/02-产品设计/01-页面与交互PRD.md`
- `docs/02-产品设计/02-编排工作台PRD.md`
- `docs/02-产品设计/03-关键交互裁决.md`
- `docs/04-测试验收/02-核心旅程测试矩阵.md`

Treat `truth/` as the primary source for future-facing UI direction. Treat `docs/` as the legacy current-state source for maintaining the existing app. Use `openspec/` only as a secondary cross-check.

For page-level layout rules, read `references/core-screens.md`.

## Default Workflow

1. Identify the target page and its primary user path.
2. Reduce the screen to one primary task, one supporting layer, one tertiary layer.
3. Build or update a standalone webpage prototype first when the hierarchy is in question.
4. Get the prototype visually coherent before changing runtime UI.
5. Only then implement the product UI and run page-level regression.

## Visual Direction

- Start from a restrained neutral editor surface, not a showcase-style warm shell.
- Keep color restrained: one blue accent by default, status colors only for state.
- Use typography and spacing for hierarchy before using borders, cards, or color.
- Prefer crisp surfaces and thin borders over blur and glow.
- Chinese readability is mandatory. Default to `Microsoft YaHei UI`, `PingFang SC`, or `Noto Sans SC` class fonts for body text.
- Keep shadows minimal. If the layout fails without shadows, the composition is weak.

## Global Shell Rules

- Every full page keeps the left activity rail.
- Top icon order is fixed: welcome, workbench, orchestration, resource center, rules center.
- Bottom area is fixed: stage chip, unsaved-count chip, settings icon.
- If there is no active project, hide stage/unsaved chips and disable the workbench/orchestration rail icons.
- No-project orchestration is not a separate page. Welcome/resource entry must auto-bootstrap a draft project context, then open the same orchestration page.

## Page Rules

### Welcome

- First screen shows only high-frequency entry paths.
- Keep the slogan as one centered block, separate from operational areas.
- Do not let explanation blocks dominate the viewport.
- Recent projects and recent templates should be directly actionable.

### Main Workbench

- Must read like an editor, not like a marketing dashboard.
- First layer: current document and work surface.
- Second layer: file tree and global AI context.
- Third layer: task drawer, search, command palette, settings.
- Left side must remain a real file tree. Do not replace hierarchy with cards.

### Global AI Sidebar

- The main panel is the current conversation.
- The thin outer rail is only for session switching.
- Empty space must be compressed aggressively.

### Orchestration

- The canvas is the primary object.
- The page should inherit the workbench shell language: left rail, central work surface, right AI sidebar, thin session rail.
- Do not keep a permanent giant asset sidebar, permanent status block, or decorative hero.
- Node configuration must allow user-configurable role, skill, tool, connector, input artifacts, output artifacts, format, requirements, and flow behavior. Do not hardcode these as labels only.

### Resource Center

- It is the single home for external resources.
- First-level types are currently only external templates and external skills.
- Future resource categories stay as expansion slots and should not become extra top-level centers.
- Keep search, type switching, and primary actions inside the content toolbar, not in a decorative top banner.

### Rules Center

- It is the single home for rules, distillation, and knowledge graph.
- Keep the page structural: toolbar, scope column, list, detail.
- Remove explanatory hero blocks, left-side essay cards, and bottom action bars.

### Settings

- Keep a stable left-side primary menu and put secondary navigation inside the content area.
- Provider Profiles must support many providers.
- Each provider is its own card in a vertically scrollable list; the right pane edits the selected provider only.
- Low-frequency diagnostics, help, and dangerous actions belong in drawers or modals.

## Interaction Rules

- High-frequency actions can be visible, but names must stay unique for semantic targeting.
- Deep actions should open from the current object, not from distant global panels.
- Clicking a node should reveal the next edit step clearly; never make the user hunt for the inspector.
- Preserve current context when switching surfaces whenever possible.

## Anti-Patterns

- Large decorative hero blocks inside editor-class pages
- Blur-heavy shells
- Low-contrast text
- Giant gaps between functional panels
- Turning AI, sessions, or assets into separate pseudo-pages when docs define them as side regions
- Hardcoded IO contracts where the product requires user configuration
- Fixed inspector sidebars for low-frequency flow editing
- Rebuilding runtime UI before a prototype has resolved hierarchy disputes

## Validation

Before calling a UI task complete:

- Verify the first-screen hierarchy in a running prototype or app
- Check narrow-width behavior
- Check that the primary task is obvious within 3 seconds
- Check that low-frequency controls do not dominate the viewport
- Run page-level regression after implementation
