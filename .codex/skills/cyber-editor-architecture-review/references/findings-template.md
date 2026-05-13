# Findings Template

Use this template for every architecture review finding.

## [严重|高|中|低] 标题

- Why this is architectural:
  - Explain which boundary, ownership rule, or durability rule is broken.
- Evidence in docs:
  - `path:line` or section reference
- Evidence in code:
  - `path:line` or explicit absence in runtime path
- Why it matters:
  - Describe divergence risk, corruption risk, governance bypass, or future implementation drift.
- What would a correct boundary look like:
  - Name the missing owner, store, gate, or split.
- Immediate action:
  - One pragmatic first fix, not a full roadmap

## Review Closeout

- 文档可继续指导开发：是 / 否 / 有条件
- 代码可在当前边界上继续扩展：是 / 否 / 有条件
- 当前适合大规模继续开发：是 / 否 / 仅限局部
- 必须先修复的前三个架构问题：
  1.
  2.
  3.
