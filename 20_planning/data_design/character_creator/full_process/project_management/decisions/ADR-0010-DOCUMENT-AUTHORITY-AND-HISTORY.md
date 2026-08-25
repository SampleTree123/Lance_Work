# ADR-0010：单一当前入口与不可变历史

> 文档 ID：`ADR-0010`
> 状态：`superseded_by_ADR-0015`
> 文档类型：`adr`
> 生命周期：`superseded`
> 适用阶段：`global`
> 权威范围：单一入口与不可变历史决定
> 上级入口：[`README.md`](./README.md)
> 上游：第一次文档重组
> 下游：文档治理与历史目录
> 最近核验：2026-08-06
> 日期：2026-08-06
> 取代者：[`ADR-0015`](./ADR-0015-DOCUMENTATION-OPERATING-MODEL.md)

## 背景

旧文档同时混合当前流程、实现细节、计划和历史，导致相同事实多处维护，恢复对话时难以判断权威版本。

## 决定

`full_process/CHARACTER_FACTORY_MASTER_SPEC.md` 是人类可读总入口；技术细节按 CC、Bridge、传输、UE、验证拆分；当前状态、Roadmap、Backlog、ADR 和 Milestone 分责。旧文档按原字节和哈希归档，旧路径只保留兼容跳转。

> 历史说明：以上是 2026-08-06 的旧决定，不是现行操作指引。当前唯一入口是 [`full_process/README.md`](../../README.md)，治理模型与目录职责以 [`ADR-0015`](./ADR-0015-DOCUMENTATION-OPERATING-MODEL.md) 为准。

## 影响

- 当前事实只维护一处，子文档可独立扩展。
- 机器 JSON 继续承载精确参数，artifacts 继续承载原始证据。
- 文档与代码冲突时停止并登记同步债务。
- 新能力进入既有目录，不因未来 UE 工作增加而重构顶层体系。
