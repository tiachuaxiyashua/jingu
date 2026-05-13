# Orchestration Review Checklist

## 1. Runtime semantics

- Are start, end, branch, loop, parallel, subflow, interrupt, and approval semantics explicit?
- Is each node type mapped to one runtime meaning?
- Are retries, resumes, and partial reruns specified?

## 2. Multi-agent topology

- Are role definitions separate from flow topology?
- Is agent-to-agent communication modeled explicitly?
- Is shared state scoped by flow, run, node, or role?

## 3. Durable execution

- Are checkpoints persisted?
- Can a run resume without recomputing hidden state?
- Are interrupt / human approval states resumable?

## 4. Capability attachment

- Are tools/skills/connectors attached at the correct layer?
- Does the runtime prevent capability drift between role config and node execution?
- Is MCP-style capability scoping feasible from the current contracts?

## 5. Editor-to-runtime closure

- Can every visible graph construct actually execute?
- Do docs, schema, runtime owner, and tests agree on that construct?
- Are there UI constructs that still have no runtime meaning?

## 6. Review threshold

Mark `high` if any of these are true:
- branch / loop / subflow semantics are ambiguous
- multi-agent communication is implied but not modeled
- resume/interrupt is promised but not persisted
- visible editor controls have no executable owner
