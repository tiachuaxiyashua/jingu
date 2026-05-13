# Frontier Refresh

Run this refresh before every orchestration review.

## Official domains

- `platform.openai.com`
- `langchain-ai.github.io`
- `microsoft.github.io/autogen`
- `docs.crewai.com`
- `modelcontextprotocol.io`

## Required searches

1. `site:platform.openai.com/docs/guides/agents OpenAI agents orchestration tools handoffs official`
2. `site:langchain-ai.github.io/langgraph human in the loop persistence official`
3. `site:microsoft.github.io/autogen stable design patterns multi-agent official`
4. `site:docs.crewai.com flows crews official`
5. `site:modelcontextprotocol.io roots specification authorization official`

## What to extract

- How agent roles communicate
- Whether shared state is graph-based, message-based, or event-based
- How loops, retries, and durable checkpoints are modeled
- How human approval / interrupts are inserted
- Whether tools and external capabilities are attached to roles, tasks, or runtime context

## Review trigger questions

- Does Cyber Editor define orchestration as runtime semantics or only as UI cards?
- Are branch / loop / subflow meanings explicit enough that two teams would build the same engine?
- Is agent-to-agent communication explicit and bounded?
- Are interrupts and resume part of the runtime, not only a UI idea?
