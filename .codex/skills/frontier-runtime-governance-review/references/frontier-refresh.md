# Frontier Refresh

Run this refresh before every runtime-governance review.

## Official domains

- `platform.openai.com`
- `langchain-ai.github.io`
- `modelcontextprotocol.io`

## Required searches

1. `site:platform.openai.com/docs/guides/agents official agents tools approvals safety`
2. `site:platform.openai.com/docs/guides/evals official evals safety regressions`
3. `site:langchain-ai.github.io/langgraph persistence human in the loop official`
4. `site:modelcontextprotocol.io authorization roots specification official`

## What to extract

- How capability boundaries are host-controlled
- How human approval is inserted before side effects
- How recovery/checkpoint semantics are modeled
- What audit evidence is needed for replay and review
- How safety regressions should be evaluated

## Review trigger questions

- Is approval bound to the exact preview / request being executed?
- Can destructive operations fail without corrupting current state?
- Are capability roots and trust boundaries explicit?
- Can the audit trail prove what happened?
