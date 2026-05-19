## Context

Jingu's truth source requires `果必须携证` and states that important or disputed results need an independent verifier: a rule engine, test script, static checker, human, or independent AI session. The current AI sandbox violates this in practice: it asks the same provider for method self-review, then Codex may run shell checks outside the Jingu flow. That means the persisted job tree does not prove the candidate was verified.

The immediate failure was a text-length requirement for a generated story. Length, marker presence, and incomplete-output patterns are deterministic and should not rely on an AI judge. They are good first targets for a minimal verification job.

## Goals / Non-Goals

**Goals:**

- Create an explicit child job for deterministic candidate verification after AI candidate submission.
- Run a tool-backed verifier that reads the parent user input and candidate output.
- Extract only generic text constraints that are present in the task, such as numeric CJK length ranges and required `<<<...>>>` markers.
- Submit verifier output as evidence on the verification child job.
- Submit a compact verification summary as parent-job evidence so the parent candidate carries hard evidence.
- Record the complete verification flow in live and persisted logs.

**Non-Goals:**

- Do not implement broad literary quality judgment as deterministic code.
- Do not auto-accept or auto-reject parent candidates.
- Do not hardcode a Zhihu story schema, Neidan Method section name, or fixed output marker.
- Do not introduce new physical tables; verification jobs, evidence appearances, and events are sufficient for the current runtime stage.

## Decisions

### Verification Is A Child Job

The verifier creates a child job under the candidate-producing parent job. This matches the truth source: independent verification is work and should be visible in the job tree. The child job owns the tool evidence; the parent gets a compact evidence summary referencing the child result.

### Deterministic Text Checks Are Generic

The first verifier extracts:

- Marker pairs found in the candidate output, especially `<<<...开始>>>` / `<<<...结束>>>` style pairs.
- Explicit CJK text length ranges from the user task, such as `4500-6000中文字符`, `4500到6000汉字`, or `4500至6000字`.
- Explicit target length statements when paired with a tolerance/range in the task.
- Incomplete-output signals such as ellipsis placeholders or phrases that indicate omitted content.

The verifier does not know about Zhihu, novels, or Neidan Method. Those remain method/user-level data.

### Verification Does Not Complete The Parent

A passing verification result becomes hard evidence, but it does not accept the parent candidate. Acceptance remains a responsibility of the parent job or human/user flow. A failing result is recorded as evidence and leaves the parent in review/repair territory for the next instruction.

## Risks / Trade-offs

- The verifier may not understand every natural-language acceptance criterion -> It only claims support for extracted deterministic checks and reports unsupported checks as open gaps.
- Marker extraction could choose the wrong region if multiple marker pairs exist -> The verifier reports all detected pairs and uses the first complete pair for length checks unless the task explicitly names a marker.
- Parent evidence could overwrite previous evidence in the minimal runtime's single evidence slot -> This is already a runtime limitation; the full evidence history remains append-only in events and appearances.
- AI quality still needs separate review -> This change deliberately solves hard deterministic evidence first.

## Migration Plan

1. Add verification flow events and readable labels.
2. Add deterministic text verification module.
3. Add runtime helper in the AI sandbox to create verification child jobs, run the tool, submit child and parent evidence, and log tree updates.
4. Add unit tests and run OpenSpec validation, full tests, compile checks, and hardcoding scan.
