# ADR-0006：服装按 BodyFit 与 Look 管理

> 状态：Accepted
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
