## 1. Proposal And Scope

- [x] 1.1 Create the OpenSpec proposal, design, specs, and tasks for AI sandbox chat.

## 2. AI Configuration And Client

- [x] 2.1 Implement local `.env.deepseek.local` configuration loading without hardcoded provider truth.
- [x] 2.2 Implement a standard-library DeepSeek chat client.

## 3. Sandbox Flow

- [x] 3.1 Implement ephemeral sandbox path resolution and cleanup.
- [x] 3.2 Implement JSONL flow event writing and tailing.
- [x] 3.3 Replace one-shot runner with an interactive multi-turn AI chat session that drives the existing runtime kernel per turn.
- [x] 3.4 Persist full diagnostic JSONL logs outside the sandbox, including inputs and outputs without secrets.

## 4. CLI And Scripts

- [x] 4.1 Extend the CLI with `ai chat` interactive conversation.
- [x] 4.2 Extend the CLI with `ai monitor` real-time status output.
- [x] 4.3 Replace one-shot scripts with a one-click PowerShell launcher that opens chat and monitor CLIs.
- [x] 4.4 Add log directory options to run and monitor commands and scripts.

## 5. Verification

- [x] 5.1 Add tests for configuration loading, sandbox cleanup, interactive chat output, flow events, and persistent diagnostic logs.
- [x] 5.2 Run OpenSpec validation, automated tests, compile check, hardcoding scan, and manual launcher sanity check.
