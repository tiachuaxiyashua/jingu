# Jingu Repository Instructions

## Source Of Truth

- `truth/` is the primary source for Jingu architecture, harness principles, object models, file protocols, evaluation notes, and migration direction.
- Do not force Jingu back into Cyber Editor's old `docs/` worldview.
- Files under `legacy-config/` are copied historical references only; they are not active instructions unless explicitly promoted.
- Do not prematurely convert brainstorms into rigid architecture. Mark assumptions, open questions, and confidence clearly.

## Work Rules

- Before durable changes, run `git status --short` and synchronize with the GitHub remote once one exists.
- Commit and push durable changes unless the user explicitly asks not to.
- Do not commit runtime state, build output, test artifacts, `node_modules/`, packaged binaries, `.env*`, or secrets.
- Preserve the distinction between truth source, temporary discussion, temporary review, and temporary test materials.

## Jingu Meaning

Jingu means the golden headband on Sun Wukong. In this project it represents the harness that binds 行者 with 律, 业, 证, 验收, 风险边界, and human value authority.
