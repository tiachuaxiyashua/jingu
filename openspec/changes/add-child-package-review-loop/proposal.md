## Why

金箍已经能调度前沿子业并提交结构化果包，但果包提交后仍停留在候选态，缺少独立验收、打回修复、再提交和父业消费已接收果包的闭环。这样业树虽然能生长和回流证据，却不能证明“子业供料已被验收并可被父业使用”。

本变更补齐最小子业果包验收闭环：独立验收位审查子业果包，代码守门器根据结构化验收结果接收或拒收子业；拒收时生成修复业并让执行端重提果包；接收后父业重评估能显影已接收果包可被消费。

## What Changes

- 新增子业果包验收 provider 调用，独立于子业执行调用。
- 验收响应必须是结构化 JSON，包含接收/打回动作、可量化检查、证据、修复指令和父业消费摘要。
- 验收通过时，通过运行时服务接收子业候选果包，并记录接收证据。
- 验收打回时，创建修复子业，向执行端发送修复请求，提交修复后的果包，再重新验收一次。
- 父业重评估日志显影已接收子业果包、未解决子业、开放问题和可消费摘要。
- 不自动接收父业或根业，不把子业验收结果冒充全局完成。

## Capabilities

### New Capabilities

- `child-package-review-loop`: AI 沙盒可以对前沿子业果包进行独立验收，接收合格果包或打回生成修复业，并记录父业消费已接收果包的状态。

### Modified Capabilities

暂无。当前仓库尚未归档出稳定 `openspec/specs/` 能力目录，本次以新增能力覆盖最小子业果包验收闭环。

## Impact

- 影响 `jingu/sandbox/runner.py`、`jingu/sandbox/flow.py`。
- 复用 `RuntimeService.accept_candidate`、`RuntimeService.reject_candidate`、`RuntimeService.create_child_job`、`TreeService.submit_result_package`、`TreeService.reevaluate_parent`。
- 增加 AI 沙盒测试和手动验证，覆盖子业果包接收、打回修复、父业重评估消费显影和日志可读性。
- 不新增数据库表，不新增外部依赖。
