# Core Screens

Use this file when the task needs page-level structure, not just visual tone.

## Welcome

Primary:
- Continue a recent project
- Continue a recent draft flow
- Start a new project

Supporting:
- Recent templates
- Resource center entry

Do not:
- Use a giant explanatory hero that pushes actions below the fold
- Put settings and low-frequency management in the first decision layer

## Main Workbench

Layout:
- Top toolbar
- Left activity rail
- File tree sidebar
- Center document workspace
- Right global AI sidebar
- Thin outer session rail

Primary:
- Current document title and surface

Supporting:
- File tree
- Current AI conversation

Tertiary:
- Process drawer
- Command palette
- Search
- Export

Do not:
- Replace the file tree with cards
- Turn AI into a separate full page
- Use a large empty welcome block inside the workbench

## Global AI Sidebar

Layout:
- Context summary
- Message stream
- Composer
- Outer session rail

Rules:
- The main width belongs to the current conversation
- Session switching uses the thin rail
- Deep management belongs in menus or dedicated management states

Do not:
- Spend width on decorative headers
- Duplicate workbench information already visible in the center pane

## Orchestration

Layout:
- Top flow toolbar
- Main canvas
- Canvas tool rail
- Right global AI sidebar
- Modal for node config
- Modal for role creation

Primary:
- Current flow canvas

Supporting:
- Canvas-local actions
- Current flow AI conversation

Tertiary:
- Role creation
- Node configuration
- Import/export

Rules:
- Node config must cover role, skill, connector, tool, input artifact, output artifact, format, and requirement fields
- Subflow should be entered from the node card itself
- Current canvas is current flow; no fake mode split

Do not:
- Use a permanent giant inspector sidebar
- Hardcode IO contract labels as non-editable display only
- Force users to configure roles inline inside a narrow side panel
