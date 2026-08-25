# WF-20 资产注册与生产矩阵冻结

> 文档 ID：`WF-20`
> 文档类型：`workflow`
> 生命周期：`current`
> 前序：`WF-10`
> 后序：`WF-30`
> Exit Gate：`GATE-20 MATRIX_FROZEN`
> 最近核验：2026-08-25

## 1. 目的与使用时机

把候选 BodyFit、身份、外观、服装、动作、表情、场景和相机收敛为可追溯、兼容且规模正确的生产矩阵。

## 2. 前后序与进入条件

- 前序：`WF-10`；后序：`WF-30`。
批次规格已经接受，所需资产类别和兼容域已知。

## 3. 输入

CC/UE 资产注册表、兼容性证据、动作窗口、服装规则、批次预算和排除清单。

## 4. 正常流程

| 步骤 | 操作 | 精确实现或机器入口 | 本步输出 |
| --- | --- | --- | --- |
| 1. 盘点候选与来源 | 对候选资产、来源路径和哈希执行结构盘点 | 对象权威从 [Registry](../registry/README.md) 反查；首批机器输入由 [资产矩阵冻结](../technical/dataset/ASSET_MATRIX_FREEZE.md#2-第一批机器输入) 列出 | 候选 ID、来源与排除清单 |
| 2. 应用兼容规则 | 应用性别、BodyFit、服装、毛发、动作、Root Motion 和道具边界 | 服装/角色规则由 [CC Technical](../technical/character_creator/README.md) 解释，动作规则由 [Motion Transfer](../technical/transfer/MOTION_TRANSFER.md) 解释 | 兼容域与允许组合 |
| 3. 编译必需导出 | 把 Look、Action、Expression 和窗口冻结为必需二进制清单 | [`build_first_batch_required_exports_v1.py`](../../../../../00_engine/scripts/dataset/build_first_batch_required_exports_v1.py) | 版本化 Required Exports Manifest |
| 4. 编译视觉/渲染矩阵 | 生成覆盖生产 Look、动作和相机的本地矩阵 | [`build_first_batch_local_render_matrix_v1.py`](../../../../../00_engine/scripts/dataset/build_first_batch_local_render_matrix_v1.py) | 版本化本地矩阵 |
| 5. 审计矩阵闭包 | 核验 Look Bundle/项目闭包、稳定 ID、计数和无隐式默认 | [`cc_audit_first_batch_full_reference_matrix_v1.py`](../../../../../00_engine/scripts/character_creator/cc_audit_first_batch_full_reference_matrix_v1.py) 与相关测试 | 完整性报告、缺失工作单和 `VAL-MATRIX-01` 证据 |

这些入口是首批专用 Builder/Registry，不是任意资产库的自动兼容求解器。候选视觉判断仍需先在其领域 Technical 中完成。

## 5. 输出契约

| 输出 ID | 逻辑产物 | 存储类别 | 生产所有者 |
| --- | --- | --- | --- |
| `OUT-WF20-ASSET-MATRIX` | 版本化生产矩阵、资产 Registry、兼容域、排除原因和完整性报告 | `versioned_registry`；外部二进制只由哈希引用 | [资产矩阵冻结](../technical/dataset/ASSET_MATRIX_FREEZE.md) |

### 输出组成、用途与下游

| 组成 | 实际内容 | 为什么需要 | 下游消费者 |
| --- | --- | --- | --- |
| 生产资产 Registry | 稳定 Identity/Look/Action/Expression/Scene/Camera ID 及来源哈希 | 避免后续按文件名猜测资产身份 | `WF-30/WF-40/WF-50` |
| 兼容域与排除项 | 性别、BodyFit、服装、动作、道具等允许组合和排除原因 | 阻止不可组合资产进入笛卡尔积 | `WF-30` 组装与 `WF-70` 图编译 |
| 必需导出 Manifest | 每个生产 ID 所需 CC/UE 二进制和 Object Path | 形成 CC/UE/服务器之间的输入锁 | `WF-40` 与服务器同步 |
| 生产/审查矩阵 | 具体 Look、动作、表达式和相机覆盖关系 | 把批次规模转为可执行工作单 | `WF-30/WF-50/WF-60` |
| 完整性报告 | 计数、缺失、哈希、重复 ID 和隐式默认检查 | 证明矩阵闭合并可进入资产构建 | `VAL-MATRIX-01` 与 `GATE-20` |

当前机器文件由 [WF-20 状态](../project_management/status/workflows/WF-20.md#当前输出与证据) 指定；稳定组成与保留语义见 [输出契约目录](../technical/output/OUTPUT_CONTRACTS.md#33-out-wf20-asset-matrix)。

## 6. 必需验证

| 验证 ID | 角色 | 何时需要 |
| --- | --- | --- |
| `VAL-MATRIX-01` | `required` | 资产池、兼容域、生产 ID 或矩阵规模发生变化后 |

定义、证据和通过条件见 [验证目录](../technical/validation/VALIDATION_CATALOG.md)。

## 7. Exit Gate

`GATE-20 MATRIX_FROZEN` 要求所有生产 ID 可解析、矩阵数量与规格一致、兼容域闭合、排除项有原因、源文件哈希已锁定。

## 8. 技术与状态

- [CC 技术索引](../technical/character_creator/README.md)
- [资产矩阵冻结](../technical/dataset/ASSET_MATRIX_FREEZE.md)
- [Registry 索引](../registry/README.md)
- [当前 WF-20 状态](../project_management/status/workflows/WF-20.md)

## 9. 失败与恢复

资产不兼容时回到候选池或调整批次规格。不得在 `WF-30` 临时替换资产而不更新矩阵。
