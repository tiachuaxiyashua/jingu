# Repo Local Instructions

## Truth And Docs Sources

- `truth/` is the emerging source of truth for the future refactor and new architecture direction.
- `docs/` is the legacy documentation system for the current Cyber Editor implementation. Keep it as migration evidence and current-state reference.
- When working on future product direction, object model, file protocol, AI orchestration philosophy, or broad refactor strategy, read `truth/README.md` first, then the relevant files under `truth/`.
- When working on current implementation maintenance, bug fixes, UI behavior, tests, or code-to-doc parity for the existing app, read `docs/README.md`, then the relevant legacy docs.
- If `truth/` conflicts with `docs/`, treat `truth/` as the new target and `docs/` as old state unless the user explicitly asks to preserve the old design.
- Do not create additional parallel truth roots beyond `truth/` and `docs/` without explicit user approval.
- Do not treat a UI shell, callable API, or old status label as completion. Mature completion means: document consistency, code owner, user-visible path, tests/evidence, and packaged-app proof where user-facing.
- If code conflicts with `truth/` on future refactor work, update or propose a truth change first. If current-maintenance code conflicts with `docs/`, update or propose a legacy doc change first.
- Do not delete detailed design content merely to simplify docs. First migrate still-useful detail into `truth/` or the current legacy source file, then remove only duplicated or obsolete wording.

## GitHub Synchronization

- The GitHub repository is the source-controlled handoff path for this project. All durable code, docs, tests, scripts, and configuration changes must be committed through git and pushed to the GitHub remote.
- Before starting any code or document modification, run `git status --short` and synchronize with the remote using `git fetch origin` plus the appropriate pull/rebase flow for the current branch. Do not begin from an unknown local-only state.
- Before handing work back, commit the completed change with a clear message and push it to the remote branch unless the user explicitly asks not to commit or push.
- Do not commit local runtime state, build output, test artifacts, recovered scratch material, `node_modules/`, packaged executables, `.env*`, or secrets. Keep those excluded by `.gitignore`.
- If the remote is unavailable or authentication fails, stop and report the exact blocker before making further durable changes.

## UI Validation And Screenshots

- When validation, screenshots, or Electron/desktop regression work needs to open the app UI on Windows, run it from an extra Windows virtual desktop instead of the user's primary desktop.
- Avoid any workflow that makes the primary screen flash, steals focus on the main desktop, or visibly disrupts the user's current workspace.

## Packaged Runtime Validation

- Once a packaged Cyber Editor build exists, all user-facing validation must use the packaged executable under `out/package/` instead of `electron .` as the final proof path.
- Preserve manual verification projects under `out/manual-projects/`, not under `out/package/`, so repackaging does not delete the project the user needs to reopen later.
- If the preserved verification project lives outside `out/package/`, the packaged app folder must still contain a visible launcher or pointer entry so a human opening `out/package/...` can immediately find and reopen the exact verification project.
