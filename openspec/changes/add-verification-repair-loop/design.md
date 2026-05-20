## Context

The current AI sandbox creates root jobs, records provider candidates and evidence, optionally asks for feedback-job judgment, and runs deterministic candidate verification jobs. Recent story-generation runs proved that verification can detect length failures, but repair still happened outside Jingu: an operator inspected logs and manually launched follow-up runs. That violates the intended job-tree direction because the repair work is not represented as a child job with its own candidate, evidence, verification, and escalation point.

The truth source requires candidate isolation, append-only events, evidence-carrying outcomes, high-value human裁决 only when needed, and avoiding heavy process for simple work. Therefore this change must be bounded, generic, and visible rather than becoming a story-specific agent loop.

## Goals / Non-Goals

**Goals:**

- Represent verification-driven repair as explicit child jobs in the existing runtime tree.
- Use deterministic verification evidence to decide whether a repair attempt is mechanically warranted.
- Record each repair prompt, provider output, candidate submission, verification result, and final routing decision in structured and readable logs.
- Create a feedback-decision child job when repair cannot proceed or remains failing within the configured attempt limit.
- Keep parent acceptance/rejection outside this loop.

**Non-Goals:**

- Do not implement full long-term law promotion, memory, or method-library mutation.
- Do not hardcode novel, Zhihu, 内丹法, or any domain-specific output criteria into the runtime.
- Do not claim semantic quality validation beyond available deterministic checks and recorded AI evidence.
- Do not convert every unsupported verification result into a repair attempt.

## Decisions

1. Add a bounded repair loop after deterministic verification.

   The loop only runs when the verification report has failed checks that are classified as repairable by their check kind. Unsupported results are logged and routed to feedback-decision when appropriate, because retrying without a concrete failing signal encourages hallucinated progress.

2. Model each repair attempt as a normal child job.

   A repair job receives a target derived from the parent task and verification evidence, a candidate result from the provider, and a verification child job of its own. This keeps the job tree truthful: the parent does not invisibly mutate its candidate, and the monitor can show exactly where the revised output came from.

3. Build repair prompts from runtime facts, not domain templates.

   The repair prompt includes the original task, the previous candidate, the verification report, and a request to preserve intent while fixing concrete failed checks. It does not mention a specific genre, product, or acceptance verdict unless those came from the user task or verifier evidence.

4. Return the latest candidate while keeping acceptance separate.

   `ai run` and `ai chat` should print the most useful candidate available, including a successful repair candidate, but the runtime still records it as a candidate. Verification pass is evidence, not acceptance.

5. Make attempt count configurable.

   CLI flags set the maximum repair attempts. Defaults remain small to prevent runaway loops and cost surprises. A zero value disables repair while preserving verification behavior.

6. Use feedback-decision jobs for unresolved failures.

   If repair attempts are exhausted, unsupported, or not safely repairable, Jingu creates a feedback-decision child job carrying the unresolved verification evidence. This is not a hardcoded accept/reject or forced human prompt; it records the need for high-value/directional decision or further method improvement.

## Risks / Trade-offs

- Repair prompts may produce a worse candidate -> Every repair candidate is isolated and re-verified; previous candidates remain logged.
- Deterministic repairability classification may be incomplete -> Unknown check kinds route to feedback-decision instead of silent retry.
- More provider calls may increase latency and cost -> Attempt count is configurable and defaults to a low bound.
- A passed deterministic check may still be low quality -> The log states only what was verified and keeps unsupported quality gaps visible.
- Feedback-decision jobs may become noisy -> They are created only after a failed/unsupported verification route that cannot be automatically repaired within bounds.
