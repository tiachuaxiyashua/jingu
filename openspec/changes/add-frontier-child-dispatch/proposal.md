## Why

金箍已经能把 AI 提出的分业申请登记为真实子业，但子业登记后仍停在草稿/待运行状态，无法产生结构化果包回流父业。这样业树只能“长出节点”，不能“通过前沿执行继续生长”。

本变更补齐最小前沿调度：对已登记的活跃叶子业进行一次受控执行，提交子业果包候选和证据，记录父业重评估；子业仍不能宣告父业完成，也不会被自动接收。

## What Changes

- 新增 AI 沙盒前沿子业调度步骤，在根业分业登记后挑选活跃叶子业执行。
- 子业执行时加载子业自身法调用帧中的 method；无子业 method 时继承当前根业 method。
- 子业 AI 响应必须是结构化果包 JSON，包含结论、产物、证据摘要、开放问题和建议后续业。
- 通过 `TreeService.submit_result_package` 提交果包候选和证据，不自动接收子业。
- 子业果包提交后记录父业重评估结果，显影哪些子业未解决、哪些果包已回流、哪些开放问题仍阻塞。
- 子业执行后允许再提议下一层分业申请，但仅登记为孙业，不在同一轮无限递归执行。

## Capabilities

### New Capabilities

- `frontier-child-dispatch`: AI 沙盒可以调度活跃前沿子业执行一次，提交结构化子业果包候选，并记录父业重评估。

### Modified Capabilities

暂无。当前仓库尚未归档出稳定 `openspec/specs/` 能力目录，本次以新增能力覆盖最小前沿调度与果包回流。

## Impact

- 影响 `jingu/sandbox/runner.py`、`jingu/sandbox/flow.py`。
- 复用 `TreeService.get_frontier`、`TreeService.submit_result_package`、`TreeService.reevaluate_parent`。
- 增加 AI 沙盒测试和手动验证，覆盖子业执行、果包候选、父业重评估和孙业登记。
- 不新增数据库表，不新增外部依赖。
