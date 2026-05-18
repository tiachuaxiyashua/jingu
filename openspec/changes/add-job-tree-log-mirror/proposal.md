## Why

AI 沙盒已经记录输入、输出、候选、证据和反馈业，但可读日志仍难以看出业树如何生长、当前父子关系是什么、一次反馈判断是否真正影响了业树。愿主需要从实时监控和保存日志中直接定位“业树哪里变了、为什么变、现在有哪些节点”。

## What Changes

- Add a human-readable job-tree mirror to AI sandbox flow logs.
- Emit explicit job-tree lifecycle events when root jobs are created, jobs move through ready/running/reviewing states, candidates/evidence are attached, and child feedback jobs are created or skipped.
- Include compact tree snapshots after meaningful tree changes so monitor output and saved Markdown logs show parent/child relationships and current node states.
- Keep the runtime database and JSONL events as the source of truth; readable tree output is only a `镜` projection derived from runtime state.

## Capabilities

### New Capabilities

- `job-tree-log-mirror`: Covers readable AI sandbox logging of job-tree changes, parent-child relationships, and tree management snapshots.

### Modified Capabilities

None.

## Impact

- Affected code: `jingu/sandbox/flow.py`, `jingu/sandbox/runner.py`, and focused sandbox tests.
- Affected behavior: AI sandbox monitor and persisted Markdown logs become easier to inspect for job-tree state.
- No external dependency changes.
