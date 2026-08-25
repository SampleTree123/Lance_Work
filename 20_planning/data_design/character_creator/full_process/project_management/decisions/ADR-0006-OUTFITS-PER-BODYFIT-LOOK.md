# ADR-0006：服装按 BodyFit 与 Look 管理

> 文档 ID：`ADR-0006`
> 状态：`accepted`
> 文档类型：`adr`
> 生命周期：`current`
> 适用阶段：`WF-20/WF-30/WF-40/WF-50`
> 权威范围：服装按 BodyFit 与 Look 管理的决定
> 上级入口：[`README.md`](./README.md)
> 上游：服装搭配风险分析
> 下游：外观规范与 UE 模块运行时
> 最近核验：2026-08-06
> 日期：2026-07-31

## 背景

不同 BodyFit 的服装导出网格不同；Shirts、Coats 等重叠层任意组合会穿模。逐件随机无法表达层级、互斥和身体隐藏。

## 决定

服装单位是 `BodyFit × Look`。Look manifest 定义槽位、层级、互斥、Body hide mask、允许动作和验证状态。只导出实际通过的组合，UE 不进行任意单件笛卡尔随机。

## 影响

- 最多为 10 个固定 BodyFit 导出每套正式 Look。
- 可以在 UE 中使用多个 Skeletal Mesh Component 表示内外层，但只有登记组合可用。
- 采购资产先整理为 Look，再做体型和动作矩阵。
- 身体 Morph 不作为跨 BodyFit 服装适配方案。

## 复审条件

通用模块化服装在全部生产 BodyFit、动作和隐藏身体面策略上通过正式门禁，或新的服装适配技术能稳定消除逐 BodyFit 网格需求时复审。
