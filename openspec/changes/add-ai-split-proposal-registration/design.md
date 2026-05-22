## Context

当前最小运行库已经支持真实父子业、结构化果包、子业级法绑定和法调用帧。AI 沙盒的链路仍是：根业加载一个 method、模型生成候选、方法自验、确定性校验、修复、验收路由。缺少的一环是：当模型识别到父业需要拆分时，系统不会把“分业申请”交给代码守门器登记。

真相源要求分业采用“人工智能提议，代码守门，业树引擎登记”。因此本设计让 AI 只输出候选分业 JSON，运行时解析后调用现有 `TreeService.propose_child_job()`。任何失败只记录为拒绝，不绕过守门器。

## Goals / Non-Goals

**Goals:**

- 在 AI 候选生成后，请模型显式输出结构化分业候选。
- 自动发现本地可用 method 文件，提供给模型作为可选法目录。
- 对每个候选调用现有子业守门器；通过则登记真实子业、绑定法、打开法调用帧。
- 在 JSONL 和可读日志中记录请求、响应、接受、拒绝和登记结果。

**Non-Goals:**

- 不实现完整多层自动调度，不自动执行被登记的子业。
- 不让模型直接写运行库、文件系统或事件账本。
- 不把内丹法、PDCA、控制变量法、辩证法名称写入引擎分支。
- 不把子业登记视为父业完成、候选接收或验收通过。

## Decisions

1. **用独立 provider 调用提取分业候选。**

   候选生成之后，再发一次 `split_proposal_extraction` 请求，输入包括用户原愿、候选结果、根业编号、根 method manifest 和可用 method 目录。这样不会污染候选正文，也能在日志中看到专门的分业推理输入输出。

2. **可用 method 目录来自文件系统协议，不来自硬编码法名。**

   运行时扫描工作区 `.agents/skills/*/SKILL.md` 和当前显式加载的 method 文件，提取 method 名称、路径、描述和校验码。模型只能返回目录中的 method path；否则守门器拒绝绑定。

3. **分业 JSON 使用最小结构。**

   期望 JSON：

   ```json
   {
     "proposals": [
       {
         "target": "...",
         "blocking_reason": "...",
         "output_contract": "...",
         "acceptance_criteria": "...",
         "estimated_effort": 1,
         "depth_limit": 3,
         "required_context_gaps": [],
         "method_path": "...",
         "method_binding_reason": "...",
         "method_return_point": "..."
       }
     ]
   }
   ```

   `method_path` 可省略；一旦提供，就必须同时提供绑定原因和回流点。

4. **登记使用现有 TreeService。**

   AI 沙盒不复制分业守门逻辑，只把候选交给 `TreeService.propose_child_job()`。这样重复目标、缺字段、深度预算、method 加载失败等都复用一个守门入口。

5. **失败也是证据。**

   每个候选都记录为 accepted 或 rejected。拒绝日志必须包含候选原文和错误原因，方便用户反向修正内丹法或分业提示。

## Risks / Trade-offs

- [风险] 多一次 provider 调用增加耗时。→ 这是验证业树生长所需的可观测成本；后续可通过参数关闭或按任务风险启用。
- [风险] 模型返回非法 JSON。→ 记录 `split_proposal_registration_skipped`，不影响主候选输出。
- [风险] method 目录扫描可能包含不适合作为法的技能。→ 第一版只暴露 `SKILL.md` 的名称、路径、描述，不执行技能；真正绑定仍要通过 method loader。
- [风险] AI 会提出装饰性子业。→ 现有守门器能拦截空字段、重复和预算问题；更强的“装饰性判断”后续应进入可配置分业守门法。
