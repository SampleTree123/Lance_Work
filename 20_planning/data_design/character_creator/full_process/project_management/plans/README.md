# 计划索引说明

> 文档 ID：`PLAN-README`
> 文档类型：`plan_index`
> 生命周期：`current`
> 权威范围：计划生命周期和目录导航
> 最近核验：2026-08-25

- [PLAN_INDEX.md](./PLAN_INDEX.md)：所有活动、排队、暂停和已完成计划的唯一索引。
- [`active/`](./active/README.md)：恰好一个当前主计划。
- [`queued/`](./queued/README.md)：已接受但尚未开始的计划。
- [`paused/`](./paused/README.md)：执行过但暂时让位的计划。
- 完成计划移入 [`../history/completed_plans/`](../history/completed_plans/README.md)。

Backlog 候选不是计划，不分配完成承诺。

## 生命周期契约

计划生命周期只使用：`current`、`queued`、`paused`、`completed`、`cancelled`。未完成需求状态只使用：`pending`、`in_progress`、`blocked`、`deferred`；完成需求使用 `completed`。状态改变必须同时更新 `PLAN_INDEX.md`，但当前事实和证据仍由 Status 保存，Plan 不复制运行日志。

- 全树恰好一个 `current` 主计划。
- `queued` 表示已经批准范围但尚未开始；Backlog 不属于 `queued`。
- `paused` 必须写暂停原因、恢复条件和已完成需求。
- 全部完成后将计划移入 `history/completed_plans/` 并记录最终证据；取消计划同样离开活动目录并保留取消原因。
- 每个需求必须有稳定 ID、影响阶段、状态和证据入口；不得用“差不多”“准备中”等不可审计状态。
