# Jingu Repository Instructions

## Project Meaning

Jingu means the golden headband on Sun Wukong. In this project it represents the harness that binds 行者 with 律, 业, 证, 验收, 风险边界, and human value authority.

## Source Of Truth

- `truth/` is the primary source for Jingu architecture, harness principles, object models, file protocols, evaluation notes, and migration direction.
- Read `truth/README.md` first before architecture, protocol, harness-runtime, governance, evaluation, or migration work, then read the task-relevant files under `truth/`.
- Preserve the distinction between current truth source, temporary discussion, temporary review, and temporary test materials.
- Do not force Jingu back into Cyber Editor's old `docs/` worldview.
- Do not create additional parallel truth roots beyond `truth/` without explicit user approval.

## Design Discipline

- Do not prematurely convert brainstorms into rigid architecture. Mark assumptions, open questions, confidence, and unresolved risks clearly.
- Evaluate the user's ideas with intellectual honesty rather than agreement bias. Treat user claims, assistant claims, and existing truth documents as hypotheses to test; separate what is valid, what is weak, what is unproven, and what would falsify the claim.
- If implementation plans conflict with `truth/`, update or propose a truth change first; do not silently implement from conflicting assumptions.
- Do not delete detailed design content merely to simplify documents. First migrate still-useful detail into the current truth source, then remove only duplicated or obsolete wording.
- Do not treat a document shape, callable API, status label, or demo shell as completion. Mature completion means truth alignment, clear ownership, executable or reviewable path, tests or evidence, and explicit remaining risks.
- When producing artifacts that the user must judge, test, or use as evidence, output the complete artifact. Do not use excerpts, summaries, ellipses, "omitted for brevity", or partial samples in place of the actual deliverable. Never reduce artifact completeness to save tokens or effort; if the artifact is too large for one response or file, split it into explicit parts or additional files while preserving the full content.

## Anti-Hardcoding Discipline

- Do not hardcode mutable truth in generic code. Hardcoding means writing changeable project, provider, path, model, template, workflow, business, policy, or environment truth into code that does not own it.
- Keep mutable truth in the correct owner: configuration, manifests, schemas, runtime state, user input, registry modules, or truth documents. If no owner exists, create or propose the owner before adding another local literal fallback.
- Stable protocol constants, state names, table names, event types, and file names are allowed only when they are part of Jingu's owned runtime contract and are documented or covered by tests.
- Do not hardcode secrets, API keys, model names, provider URLs, absolute local paths, user-specific paths, external endpoints, test-only fixtures, or business examples into reusable runtime code.
- After every coding task, run a hardcoding scan before marking the work complete. If the repository has an established scan command, use it. If not, add or run a repo-appropriate scan and report the evidence, remaining literals, ownership rationale, and accepted risks.
- A change is not complete if the hardcoding scan finds new mutable truth in generic code without an explicit owner, migration reason, and follow-up path.

## AI Test Runtime

- DeepSeek-backed tests must load local configuration from `.env.deepseek.local` and read `DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL`, `DEEPSEEK_MODEL`, and related model settings from that file.
- Do not hardcode API keys or model names in scripts, tests, docs, command history, or committed files; keep local secret files covered by `.gitignore`.
- Use the configured DeepSeek model for AI runtime tests unless the user explicitly requests another provider or model for a specific test.

## Skill Usage

- When a task matches a local skill, first use the exact `SKILL.md` path provided by the current session. If that path is missing, do not declare the skill unavailable until checking these fallback locations in order: repository `.agents/skills/<skill-name>/SKILL.md`, legacy repository `.codex/skills/<skill-name>/SKILL.md`, user `%USERPROFILE%\.codex\skills\<skill-name>\SKILL.md`, and system `%USERPROFILE%\.codex\skills\.system\<skill-name>\SKILL.md`.
- If a referenced skill path is stale but the same skill exists in another approved local location, use the valid local path and record or repair the stale path before continuing.
- When the current local skills do not cover a problem well enough, and a specialized skill would materially improve correctness or safety, search online or the curated skill index for a suitable skill. Prefer official or trusted sources, inspect the source and purpose before installing, use the `skill-installer` workflow when applicable, and report any restart requirement.

## Parallel Sub-agent Development

- During concrete code implementation, the main coding agent may spawn enough sub-agents to develop, inspect, or verify independent work in parallel when doing so materially improves speed or quality.
- Sub-agents may use lower-cost models and lower reasoning effort when their assigned task is bounded enough for that choice. The main coding agent decides the model, effort level, role, task split, and write ownership for each sub-agent based on task risk, complexity, coupling, and verification needs.
- The main coding agent remains responsible for final integration and acceptance. Sub-agent output is never accepted blindly; the main coding agent must review changed files, check consistency with `truth/`, repo rules, OpenSpec artifacts when applicable, and run the relevant verification before reporting completion.
- Parallel delegation must not create uncontrolled edits. Each sub-agent must receive a concrete scope, clear ownership of files or questions, and the instruction not to revert or overwrite unrelated work.
- Use sub-agents for work that can proceed independently. Keep tightly coupled, high-risk, or immediately blocking decisions under the main coding agent unless explicit delegation is still the safer path.

## GitHub Synchronization

- The GitHub repository is the source-controlled handoff path for this project. Durable docs, code, tests, scripts, skills, and configuration changes must be committed through git and pushed to the GitHub remote.
- Before starting any code or document modification, run `git status --short` and synchronize with the remote using `git fetch origin` plus the appropriate pull or rebase flow for the current branch.
- Before handing work back, commit the completed change with a clear message and push it to the remote branch unless the user explicitly asks not to commit or push.
- Do not commit local runtime state, build output, test artifacts, recovered scratch material, `node_modules/`, packaged binaries, `.env*`, or secrets. Keep those excluded by `.gitignore`.
- If the remote is unavailable or authentication fails, stop and report the exact blocker before making further durable changes.
