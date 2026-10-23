# ADR-0017：计划结项后的显式空闲状态

> 文档 ID：`ADR-0017`
> 文档类型：`adr`
> 生命周期：`current`
> 状态：`accepted`
> 适用阶段：`global`
> 日期：2026-10-05
> 权威范围：没有获授权下一任务时的计划归档与项目空闲状态
> 取代/后继：not_applicable；补充 [ADR-0016](./ADR-0016-INDEPENDENT-DOCUMENT-SUBSYSTEMS.md) 的 Plan/Status 独立契约
> 最近核验：2026-10-05

## 背景

完成计划应迁入 History，下一排队任务只能在用户启动时进入 current。原“全树始终恰好一个 current”规则无法同时表达这两项要求，容易使已完成计划继续伪装执行中，或使未授权任务被自动启动。

## 决定

执行中仍恰好一个 current。只有已完成计划归档且没有下一任务授权时，机器状态显式记录 `project_phase=idle_after_completed_plan` 和 `current_plan_id=null`，此时必须零 current。任何状态都不允许多个；空闲标记下的非空/缺失 current_plan_id、残留 current，以及其他阶段零 current 均失败。

只有上述显式空闲且 `current_plan_id=null` 时，`active_workflow_id` 必须显式为 `null`，表示没有活动执行流程；通过 `last_completed_workflow_id` 保留最近完成 Workflow 的结果导航。其他执行状态仍须合法的活动 Workflow，字段缺失不等同于显式空闲。

空闲是项目状态，不是新的计划生命周期，不产生 CC/UE 操作授权。保留最后完成计划及其证据，排队与暂停计划保持原状态；等待用户启动下一计划或指定新任务。[Governance](../../GOVERNANCE.md#72-计划) 与检查器共同执行该规则。

## 后果

计划能够真实归档，项目能真实等待，不需新增占位计划。原执行中的计划、需求与证据检查继续有效；本规则不提前判定任何资产任务完成。

## 未采用方案

不自动晋升排队计划，不让完成计划无限保持 current，不创建虚假维护任务，也不无条件允许零 current。

## 复审条件

若以后支持用户授权的并行主计划或自动排队执行，须重新评估此规则；现阶段仍保持单主线执行与显式启动授权。
