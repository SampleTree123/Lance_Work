# ADR-0011：生产生命周期、Workflow 与 Gate 文档架构

> 文档 ID：`ADR-0011`
> 文档类型：`adr`
> 生命周期：`superseded`
> 状态：`superseded_by_ADR-0015`
> 适用阶段：`global`
> 权威范围：生命周期文档分层与 ID/命令所有权决定
> 上级入口：[`README.md`](./README.md)
> 上游：2026-08-06 文档逻辑审查
> 下游：Master、`workflow/`、`validation/` 与治理规则
> 最近核验：2026-08-06
> 取代者：[`ADR-0015`](./ADR-0015-DOCUMENTATION-OPERATING-MODEL.md)

## 背景

旧体系按 CC、Bridge、传输、UE 和验证主题铺开。它可以查到文件，却不能从零到最终数据说明当前阶段、进入原因、验证时机、输出和下一步；测试、视觉验收与恢复又混在同一篇 Runbook 中。

## 决定

1. 生产生命周期固定为 `WF-00..WF-09`，从会话预检到数据集验收。
2. Master 是唯一总入口；Workflow 是生产顺序和普通命令权威；领域文档只解释规则；Validation 分为 Gate、`VAL-*`、`VIS-*` 和 `REC-*`。
3. `RM-*` 只描述开发路线，不与 `WF-*` 混用。
4. 每份现行文档必须有标准元数据、父级入口和上下游；所有文档从 Master 可达。
5. 旧 Runbook 保留兼容页，重构前原文进入带 SHA-256 的不可变历史快照。
6. 使用只读审计器检查链接、可达性、阶段链、元数据、ID 和历史哈希。

> 历史说明：以上十段连续编号是旧体系，不是现行 Workflow。当前生命周期使用 `WF-00/10/.../90`，应从 [`full_process/README.md`](../../README.md) 进入，并以 [`ADR-0015`](./ADR-0015-DOCUMENTATION-OPERATING-MODEL.md) 为准。

## 影响

文档数量增加，但读者可沿实际生命周期逐步深入；命令与验证不再多处重复。尚未实现的场景和数据集阶段可以先定义契约，但必须标记 `planned` 且不得提供伪命令。
