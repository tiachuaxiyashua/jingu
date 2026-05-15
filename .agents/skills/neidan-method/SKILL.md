---
name: neidan-method
description: Jingu Neidan Method prototype for actively transforming vague human wishes into executable capability loops by clarifying concepts, generating task-specific methods, identifying evidence and feedback channels, producing artifacts, and updating the method from feedback.
---

# Neidan Method

This is not optimized as a minimal auto-triggered Codex skill. It is a Jingu method prototype intended to be actively invoked, stress-tested, expanded, and eventually internalized as a reusable `法`.

Neidan Method turns "I want X but I do not know how" into a learning-and-execution loop. It treats the user's wish as the source, then builds the missing capability around it: concepts, standards, evidence, methods, execution, feedback, revision, and reusable learning.

Do not use this as a thinking-only checklist. The method must move toward a concrete artifact and a feedback channel.

## Core Loop

```text
original wish
  -> task ye
  -> concept breakdown
  -> operational standards
  -> evidence / examples / counterexamples
  -> capability method v0
  -> execution artifact
  -> feedback / evaluation
  -> method update or rollback
```

## Required Discipline

1. Preserve the user's original wish before rewriting it.
2. Do not shrink the final goal just because a smaller artifact is easier. Separate final target, current phase output, and validation artifact.
3. Break vague concepts until they become executable choices, observable standards, examples, counterexamples, or feedback questions.
4. Create child work only when it improves execution, validation, risk control, or value choice. Avoid decorative decomposition.
5. Prefer generated defaults for low-level execution details. Ask the human only when the answer materially changes value, direction, risk, or irreversible commitment.
6. Treat community practice, expert heuristics, tests, market data, physical feedback, user feedback, and AI review as usable evidence with different reliability levels.
7. Every generated method is provisional. It must record what feedback would confirm, revise, or retire it.

## Workflow

### 1. Establish Task Ye

Create a task contract:

```text
source_wish:
final_target:
current_phase_output:
validation_artifact:
non_goals:
known_constraints:
risk_level:
feedback_channels:
```

If the user asks for a broad end state, keep that end state visible. Do not let a prototype, sample, or outline silently become the real deliverable.

### 2. Extract Concepts

List the important concepts in the wish. For each concept, classify it:

```text
concept:
role: goal | material | quality | constraint | risk | audience | tool | domain
current_clarity: clear | vague | conflicting | missing
blocks_execution: yes | no
blocks_evaluation: yes | no
needs_external_evidence: yes | no
needs_human_choice: yes | no
```

### 3. Operationalize Concepts

For every blocking vague concept, produce at least one of:

- executable definition
- measurable proxy
- rubric
- example
- counterexample
- source-backed heuristic
- decision question
- feedback loop

Do not stop at labels like "high quality", "engaging", "safe", "professional", "novel", or "complete". Turn them into actions and checks.

### 4. Build Child Ye

Create child work units only for unresolved items that matter:

```text
child_ye:
purpose:
input_xiang:
method:
expected_output:
acceptance_check:
feeds_back_to:
```

Typical child ye:

- evidence search
- concept refinement
- example mining
- counterexample mining
- method synthesis
- risk review
- execution
- evaluation
- feedback incorporation

### 5. Synthesize Method Fa

Create a task-specific method:

```text
method_name:
applies_to:
steps:
rules:
examples:
counterexamples:
quality_checks:
feedback_to_collect:
revision_rules:
```

The method may be a temporary skill, checklist, rubric, playbook, workflow, or prompt protocol. Keep it usable by another agent without the full conversation.

### 6. Execute

Use the method to produce the best current artifact. Do not only analyze unless analysis itself is the requested artifact.

For large tasks, produce:

- final target map
- current phase deliverable
- next execution batch
- what feedback would update the method

### 7. Evaluate And Update

Evaluate with the best available feedback:

```text
human feedback
physical test
unit/integration test
market metric
expert/community heuristic
AI critique
source comparison
red-team review
```

Record:

```text
confirmed:
weakened:
changed:
new_gap:
method_update:
rollback_needed:
```

## Output Shape

Use this compact structure unless the task needs another format:

```text
Original wish:
Task ye:
Concept map:
Blocking gaps:
Child ye:
Generated method:
Artifact:
Evaluation plan:
Method update notes:
Observed failure modes:
```

## Failure Modes To Watch

- Goal collapse: replacing the user's final goal with a smaller convenient output.
- Concept ornamentation: decomposing words without improving execution.
- Proxy worship: treating a measurable proxy as the real value.
- Source flattening: treating a forum tip, expert rule, benchmark, and physical test as equally strong.
- Question flood: asking the human about low-level details that the system should propose by default.
- Self-sealing method: generating a method that cannot be corrected by feedback.
- Context bloat: importing all child work into the parent instead of passing conclusions, evidence, and open issues.

When any failure mode appears, name it and revise the method before continuing.
