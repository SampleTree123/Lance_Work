# 当前状态索引

> 文档 ID：`STATUS-INDEX`
> 文档类型：`status_index`
> 生命周期：`current`
> 权威范围：当前项目、Workflow 和活动批次状态导航
> 最近核验：2026-08-25

- [PROJECT_STATUS.md](./PROJECT_STATUS.md)：人类可读的当前结论和唯一下一步。
- [PROJECT_STATE.json](./PROJECT_STATE.json)：受控状态字段的机器权威。
- [`workflows/`](./workflows/README.md)：十个长期阶段的能力状态。
- [`batches/`](./batches/README.md)：活动批次的冻结范围和执行状态。

状态文档覆盖更新；完整旧进度不在这里累计。完成事实进入 `history/`。

每份 Workflow Status 必须独立回答六件事：当前已具备什么能力、当前计划要求落实到哪里、适用 `VAL-*` 在哪个作用域是什么结果、当前采用哪个 `OUT-*` 版本/路径、仍有哪些风险、下一 Gate 是什么。能力曾经通过不等于当前应用会话仍有效；代表样例通过也不等于正式全批媒体完成。
