# WF-40 CC Bundle 导出与 UE 导入

> 文档 ID：`WF-40`
> 文档类型：`workflow`
> 生命周期：`current`
> 前序：`WF-30`
> 后序：`WF-50`
> Exit Gate：`GATE-40 UE_REFERENCE_ACCEPTED`
> 最近核验：2026-08-25

## 1. 目的与使用时机

把已接受 CC 项目导出为可追溯 Bundle，并在 UE 中建立通过 Auto Setup、材质、Morph、Skeleton 和运行时结构检查的 FullReference。

## 2. 前后序与进入条件

- 前序：`WF-30`；后序：`WF-50`。
`GATE-30` 通过；CC 和 UE 版本、Auto Setup、目标路径及输出空间已验证。

## 3. 输入

被接受的 CC 项目、冻结导出工单、Skeleton 策略和 Vendor/DataMake 路径规则。

## 4. 正常流程

本节说明执行顺序和代码导航；可复制命令、参数、环境与恢复方式只由相应 Technical 文档维护。

| 步骤 | 操作 | 精确实现入口 | 本步产物 |
| --- | --- | --- | --- |
| 1. 编译转移工单 | 从已接受 CC Look 与冻结矩阵生成 32-Look 配置、增量工单和路径字段 | [`cc_build_first_batch_full_reference_looks_v3.py`](../../../../../00_engine/scripts/character_creator/cc_build_first_batch_full_reference_looks_v3.py)；执行说明见 [CC 组装与验收](../technical/character_creator/ASSEMBLY_AND_ACCEPTANCE.md) | 版本化 Look/Export 配置，不是 FBX 本体 |
| 2. 从 CC 导出 | 在 CC/RLPy 中按工单保存项目并导出同基名 FBX、JSON、`.fbm` 与纹理 | 当前首批增量入口 [`run_first_batch_missing_looks_export.ps1`](../../../../../00_engine/scripts/character_creator/run_first_batch_missing_looks_export.ps1)，经 [`cc_bridge_client.py`](../../../../../00_engine/character_creator_bridge/cc_bridge_client.py) 调用 [`cc_validate_body_reconstruction.py`](../../../../../00_engine/scripts/character_creator/cc_validate_body_reconstruction.py)；边界见 [FullReference Technical](../technical/transfer/CC_TO_UE_FULLREFERENCE.md) | CC Export Bundle 与逐 Look CC 结果 |
| 3. 审计并冻结来源 | 校验 32 Look 的文件存在性、大小、哈希和目录闭包，再生成 UE 必需导出清单 | [`cc_audit_first_batch_full_reference_matrix_v1.py`](../../../../../00_engine/scripts/character_creator/cc_audit_first_batch_full_reference_matrix_v1.py)；[`build_first_batch_required_exports_v1.py`](../../../../../00_engine/scripts/dataset/build_first_batch_required_exports_v1.py) | 可追溯 Bundle Manifest/Required Exports |
| 4. 导入 UE | 在 Vendor 根逐 Look 导入 FullReference，执行 Auto Setup 并绑定冻结的同性 Skeleton | 系统入口 [`run_first_batch_full_reference_import.py`](../../../../../00_engine/scripts/unreal/run_first_batch_full_reference_import.py)；UE Payload [`ue_import_first_batch_full_reference_looks.py`](../../../../../00_engine/scripts/unreal/ue_import_first_batch_full_reference_looks.py) | UE FullReference 资产与逐 Look 导入报告 |
| 5. 聚合 Gate | 汇总 Object Path、Skeleton、Morph、材质、动态皱纹和错误分类 | 上一步系统入口的 `validate/aggregate` 模式；通过条件见 [验证目录](../technical/validation/VALIDATION_CATALOG.md) | 聚合报告与 `VAL-TRANSFER-01` 证据 |

当前代码边界必须如实理解：UE 导入侧已有可按 Look 恢复的正式入口；CC 侧已有首批工作单编译、RLPy 执行器和“已有 16 + 补齐 16”的生产入口，但尚无从空目录重建全新 32-Look Bundle 的单一通用包装脚本。不得把首批特化入口描述为通用一键流水线。

## 5. 输出契约

| 输出 ID | 逻辑产物 | 存储类别 | 生产所有者 |
| --- | --- | --- | --- |
| `OUT-WF40-TRANSFER-BUNDLE` | CC Bundle、UE FullReference、源到 Object Path 映射、导入报告和聚合 Gate | `cc_export_bundle` + `ue_asset` + `run_evidence` | [CC→UE FullReference](../technical/transfer/CC_TO_UE_FULLREFERENCE.md) |

### 输出组成、用途与下游

该逻辑输出由四个不可互相替代的组成部分构成：

| 组成部分 | 实际内容 | 为什么需要 | 下游使用者 |
| --- | --- | --- | --- |
| CC Export Bundle | 每个 Look 的 FBX、同基名 JSON、`.fbm`/纹理和来源锁 | 是 UE 导入和确定性重导入的不可变二进制来源；UE 资产不能反向替代它 | 本 Workflow 的 UE 导入步骤、故障重试与资产迁移 |
| UE FullReference | `/Game/Vendor/.../Looks/<LOOK_ID>` 下的 Skeletal Mesh、Skeleton、材质、纹理、Morph 和 Blueprint 等导入资产 | 是 UE 中真正可播放、绑定动画和参与渲染的运行时角色 | `WF-50` 运行时验收、`WF-60` Sequence、`WF-80` 渲染 |
| 来源映射 | Look ID、源文件哈希、Bundle 路径、UE Object Path 和同性 Skeleton 关系 | 保证一个 UE 资产能追溯到唯一 CC 来源，并支持按 Look 重试而不误覆盖 | 验证、Registry、故障恢复和最终发布追溯 |
| 导入报告与聚合 Gate | 每 Look 验证 JSON、32/32 汇总、失败分类和人工例外 | 证明“文件存在”之外的材质、Morph、Skeleton 和对象路径条件已通过 | `VAL-TRANSFER-01`、WF-40 Status 与进入 `WF-50` 的 Gate |

当前接受版本和三个物理位置见 [WF-40 当前状态](../project_management/status/workflows/WF-40.md#当前输出与证据)；稳定组成、存储类别和保留语义见 [输出契约目录](../technical/output/OUTPUT_CONTRACTS.md#35-out-wf40-transfer-bundle)。路径别名见 [PATH_ALIASES](../reference/PATH_ALIASES.md)。

## 6. 必需验证

| 验证 ID | 角色 | 何时需要 |
| --- | --- | --- |
| `VAL-TRANSFER-01` | `required` | Bundle、导入设置、Skeleton、材质、Morph 或目标 Object Path 变化后 |

定义、证据和通过条件见 [验证目录](../technical/validation/VALIDATION_CATALOG.md)。

## 7. Exit Gate

`GATE-40 UE_REFERENCE_ACCEPTED` 要求生产矩阵全部导入、源哈希一致、规范 Skeleton 正确、材质/Morph/皱纹通过且无静默失败。

## 8. 技术与状态

- [CC→UE FullReference](../technical/transfer/CC_TO_UE_FULLREFERENCE.md)
- [资产追溯](../technical/transfer/ASSET_TRACEABILITY.md)
- [当前 WF-40 状态](../project_management/status/workflows/WF-40.md)

## 9. 失败与恢复

交互导入按技术文档限制每个 UE 会话的新 Look 数量。UE 退出、未知窗口或哈希漂移立即停止；干净重启后从失败 Look 重试并重新运行聚合 Gate。
