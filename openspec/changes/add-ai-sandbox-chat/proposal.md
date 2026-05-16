## Why

The first runtime kernel proves the ledger and guardrails, but it is still too low-level for manual validation. Jingu needs a minimal AI-backed conversation path that demonstrates the kernel as a usable harness while keeping runtime state isolated and disposable.

## What Changes

- Add a DeepSeek-backed interactive chat session that loads provider settings from `.env.deepseek.local`.
- Add an ephemeral sandbox session that creates local runtime state when chat starts and destroys the sandbox when the user exits.
- Add a chat CLI where the user can make task requests, continue discussion, and provide decisions or corrections.
- Add a separate monitor CLI that prints every flow event, input, output, provider interaction summary, kernel transition, error, and cleanup event in real time.
- Add one-click PowerShell launcher that opens both the chat CLI and monitor CLI with the same sandbox and log directory.
- Add tests and hardcoding scan coverage for the new non-secret configuration and cleanup behavior.

## Capabilities

### New Capabilities

- `ai-sandbox-chat`: AI-backed ephemeral interactive chat workflow with sandbox lifecycle, full diagnostic logging, and a separate real-time monitor CLI.

### Modified Capabilities

None.

## Impact

- Adds AI provider configuration loading and DeepSeek chat client code under `jingu/ai/`.
- Adds sandbox flow orchestration under `jingu/sandbox/`.
- Extends the CLI with `ai run` and `ai monitor`.
- Adds one-click scripts under `scripts/`.
- Adds tests under `tests/`.
