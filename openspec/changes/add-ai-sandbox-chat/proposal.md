## Why

The first runtime kernel proves the ledger and guardrails, but it is still too low-level for manual validation. Jingu needs a minimal AI-backed conversation path that demonstrates the kernel as a usable harness while keeping runtime state isolated and disposable.

## What Changes

- Add a DeepSeek-backed minimal chat runner that loads provider settings from `.env.deepseek.local`.
- Add an ephemeral sandbox runner that creates local runtime state for one run and destroys the sandbox at the end.
- Add a result-only run command so the main terminal prints only the AI answer.
- Add a separate monitor command that tails all flow status from the active sandbox in real time.
- Add one-click PowerShell scripts for running and monitoring the sandbox workflow.
- Add tests and hardcoding scan coverage for the new non-secret configuration and cleanup behavior.

## Capabilities

### New Capabilities

- `ai-sandbox-chat`: AI-backed ephemeral chat workflow with sandbox lifecycle, result-only execution, and separate real-time flow monitoring.

### Modified Capabilities

None.

## Impact

- Adds AI provider configuration loading and DeepSeek chat client code under `jingu/ai/`.
- Adds sandbox flow orchestration under `jingu/sandbox/`.
- Extends the CLI with `ai run` and `ai monitor`.
- Adds one-click scripts under `scripts/`.
- Adds tests under `tests/`.
