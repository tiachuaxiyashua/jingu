## Why

金箍已经能让子业产出果包、独立验收、打回修复并被父业看到 accepted 结果，但父业还不会消费这些已接收子业果包生成自己的候选成果。与此同时，现有业树网页投影只能粗略看节点和事件，不能清楚看到每一步的输入、输出、执行动作、验收判断和状态变化，无法支撑用户定位流程卡点。

本变更在“完善最小可验证闭环”的前提下补齐父业整合器，并重做业树日志查看器，使用户能逐步查看业树每一步的输入、输出、动作、证据和状态变化。

## What Changes

- 新增父业整合器 provider 调用：读取已接收子业果包、父业契约、根业候选和父业重评估，生成父业整合候选。
- 父业整合候选只提交为父业候选与证据，不自动接收父业或根业。
- 当没有已接收子业果包时，明确记录父业整合跳过原因。
- 修复真实风险：未验收或未接收的子业果包不得触发父业整合；父业整合响应必须结构化并携带证据、消费摘要和未决缺口。
- 重做 `tools/job-tree-log-viewer` 为逐步 trace 视图：左侧可筛选时间线，中间业树，右侧展示当前步骤的输入、输出、动作、状态变更、证据和原始 JSON。
- viewer 只读解析日志，不调用模型、不修改运行库、不把镜像当真相源。

## Capabilities

### New Capabilities

- `parent-job-integration`: AI 沙盒可以在子业果包 accepted 后由父业整合器消费已接收子业结果，生成父业候选成果和证据，但不自动接收父业。
- `job-tree-trace-viewer`: 静态网页可以从 JSONL 日志逐步重放金箍运行过程，并清晰展示每一步输入、输出、动作、状态变化、证据和业树变化。

### Modified Capabilities

暂无。当前仓库尚未归档出稳定 `openspec/specs/` 能力目录，本次以新增能力覆盖父业整合和可观测性增强。

## Impact

- 影响 `jingu/sandbox/runner.py`、`jingu/sandbox/flow.py`、`jingu/cli.py`。
- 影响 `tools/job-tree-log-viewer/index.html`、`viewer.js`、`styles.css`、`README.md` 和 viewer 验证脚本。
- 增加单元测试、viewer 投影测试和手动日志验证。
- 不新增数据库表，不新增外部依赖，不提交运行日志或 artifacts。
