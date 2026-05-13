# Frontier Refresh

Run this refresh before every context-engineering review.

## Official domains

- `platform.openai.com`
- `docs.anthropic.com`
- `langchain-ai.github.io`
- `modelcontextprotocol.io`

## Required searches

1. `site:platform.openai.com/docs/guides/agents OpenAI context tools memory retrieval official`
2. `site:platform.openai.com/docs/guides/evals OpenAI evals retrieval official`
3. `site:docs.anthropic.com prompt caching official docs`
4. `site:langchain-ai.github.io/langgraph persistence memory official`
5. `site:modelcontextprotocol.io roots resources specification official`

## What to extract

- Recommended context sources and packing rules
- Retrieval quality expectations and evidence requirements
- Prompt caching / reuse implications
- Budget and truncation controls
- Provenance / citation / trace expectations
- Host-controlled resource scoping

## Review trigger questions

- Can the runtime explain why each context item is present?
- Can it survive large projects without dumping raw files into prompts?
- Are freshness and invalidation real or only implied?
- Is the evidence package enough for replay and audit?
