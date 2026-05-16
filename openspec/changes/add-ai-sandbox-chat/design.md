## Context

The current kernel can create jobs, store appearances, append events, and enforce first-stage guardrails. A human still has to run many low-level commands to see value. The next smallest useful layer is an AI chat workflow that drives the kernel internally and presents a simple result to the user.

The repository instruction requires DeepSeek-backed tests and AI runtime code to load local configuration from `.env.deepseek.local`, without hardcoding keys, model names, or provider URLs.

## Goals / Non-Goals

**Goals:**

- Provide a single command that asks AI a question and prints only the final answer.
- Create all runtime state inside a sandbox that is removed automatically at the end of the run.
- Provide a separate monitor command that prints each flow transition in real time.
- Persist workflow inputs, provider request summaries, provider responses, kernel operations, final outputs, failures, and cleanup events to a log file outside the sandbox.
- Drive the existing Jingu runtime kernel during the AI workflow: root job, ready, running, candidate, evidence, accept.
- Load DeepSeek provider configuration from `.env.deepseek.local`.
- Avoid committing or persisting secrets, provider defaults, or sandbox state.

**Non-Goals:**

- No multi-turn persistent conversation history after sandbox destruction.
- No UI.
- No model selection UI.
- No multi-agent orchestration.
- No long-running daemon.

## Decisions

### Add `jingu ai run` and `jingu ai monitor`

The main user-facing command is:

```text
python -m jingu.cli ai run --message "..."
```

It prints only the final AI answer to stdout. Flow status is written to a JSONL event stream inside the active sandbox and mirrored to a persistent JSONL log outside the sandbox.

The monitor command is:

```text
python -m jingu.cli ai monitor
```

It tails the active sandbox event stream and prints status lines until the run finishes or the sandbox disappears. It also reports the persistent log path when that path is known.

### Use an ephemeral sandbox slot by default

The default sandbox path is derived from the OS temporary directory and a stable slot name. The run command creates the sandbox at start and removes it in a `finally` block. A `--sandbox` argument allows explicit paths for debugging or parallel manual validation.

This keeps the default path discoverable by the monitor without printing internal state from the run command.

### Store live monitor events inside the sandbox and diagnostic logs outside it

The monitor event file lives inside the sandbox, so cleanup removes it with the rest of the runtime state. A persistent diagnostic log lives outside the sandbox, so cleanup preserves enough evidence for bug repair and flow backtracking.

The runner writes lifecycle and I/O events:

- sandbox_created
- runtime_initialized
- root_job_created
- job_ready
- job_running
- user_input_recorded
- ai_request_started
- ai_response_received
- candidate_submitted
- evidence_submitted
- job_accepted
- result_output_recorded
- run_finished
- sandbox_destroyed

The run command never writes these events to stdout. It writes them to the live event stream and persistent log. Logs must not include secrets or authorization headers.

Default persistent logs are written under a temporary Jingu log directory. The run and monitor commands accept `--log-dir` so the user can choose a durable directory for bug reports.

### Keep provider truth in local configuration

The DeepSeek client reads `DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL`, `DEEPSEEK_MODEL`, and optional numeric settings from `.env.deepseek.local`. Missing required values fail before calling the provider.

The client uses Python standard library HTTP support to avoid adding dependencies.

## Risks / Trade-offs

- The monitor must start before or during a run to see the ephemeral event stream -> Persistent logs still preserve the full flow after cleanup.
- Default sandbox slot supports one active default run -> Use `--sandbox` for parallel runs.
- Provider failures will produce no AI answer -> The run command reports errors to stderr and still destroys the sandbox.
- AI evidence is weak in this first chat layer -> The evidence only proves the provider returned a response; stronger validation belongs to later verifier work.
- Logs may contain user prompts and AI outputs -> Keep logs outside source control, do not store secrets, and allow `--log-dir` so users can control retention.

## Migration Plan

1. Add AI configuration and DeepSeek client modules.
2. Add sandbox event stream and runner orchestration.
3. Extend CLI with `ai run` and `ai monitor`.
4. Add one-click scripts.
5. Add persistent JSONL logging for full flow and I/O.
6. Add tests for config loading, cleanup, result-only output, monitoring stream behavior, and persistent log contents.
7. Run OpenSpec validation, tests, compile check, and hardcoding scan.
