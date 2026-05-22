## Why

当前运行时已经能把一个 method 文件拆成法片段并绑定到当前业，但这种能力仍偏向“单业加载一个法”。用户指出的真实设计不是在同一个业里静态合并多个法，而是父业先按内丹法发现阻塞点，产生子业，子业再按自身目标绑定 PDCA、控制变量法、辩证法等法，并把果包回流父业。

如果不补“子业级法绑定与法调用帧”，系统会把多法套用伪装成一次大提示词注入，日志也无法看出哪个子业为什么调用了哪个法、产出了什么、如何回流。

## What Changes

- 新增子业提议时的可选法绑定字段：方法路径、绑定原因、调用输入、输出契约、回流点、预算、深度。
- 新增法调用帧事件：记录某个业调用某个法的输入、输出契约、验收标准、回流点、预算、深度和重复检测键。
- 允许 `tree propose-child` 在创建子业后，把指定法绑定到该子业，而不是绑定到父业或全局合并上下文。
- 新增 PDCA 法、控制变量法、辩证法三个独立法相，用于子业级调用，不创建组合 method。
- 扩展树视图、父业重评估和可读日志字段，使用户能看到子业绑定的法与法调用帧。
- 保留当前 AI 沙盒单轮根业运行能力，但明确复杂多法验证必须通过真实子业/法调用帧显影，不能靠同业静态合并法。

## Capabilities

### New Capabilities

- `child-job-method-call-frames`: 子业可以拥有自己的法绑定和法调用帧，父业通过结构化果包接收子业结果。
- `pdca-control-dialectic-methods`: PDCA 法、控制变量法、辩证法作为独立法相存在，可分别绑定到不同子业。

### Modified Capabilities

暂无。当前仓库尚未归档出稳定 `openspec/specs/` 能力目录，本次以新增能力覆盖子业法调用帧与三法法相，并在实现中保持已有业树和 method loader 行为兼容。

## Impact

- 影响 `jingu/runtime/service.py`、`jingu/runtime/tree.py`、`jingu/runtime/constants.py`、`jingu/cli.py`。
- 影响 sandbox 日志标签和可读日志字段，使法调用帧在人类日志中可见。
- 新增或调整运行时、业树和 CLI 测试。
- 新增 `.agents/skills/pdca-method/`、`.agents/skills/control-variable-method/`、`.agents/skills/dialectical-method/`。
