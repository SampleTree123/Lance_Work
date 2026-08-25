# WF-30 CC 角色组装与验收

> 文档 ID：`WF-30`
> 文档类型：`workflow`
> 生命周期：`current`
> 前序：`WF-20`
> 后序：`WF-40`
> Exit Gate：`GATE-30 CC_ASSETS_ACCEPTED`
> 最近核验：2026-08-25

## 1. 目的与使用时机

依据冻结矩阵在 CC 中构造角色和 Look，执行静态、动态、眼口、服装和材质验收，并保存规范项目。

## 2. 前后序与进入条件

- 前序：`WF-20`；后序：`WF-40`。
`GATE-20` 通过；Bridge、CC 项目和资产路径已由 `WF-00` 验证。

## 3. 输入

BodyFit、Identity、Appearance、Outfit 和动作压力测试清单，以及精确源哈希。

## 4. 正常流程

| 步骤 | 操作 | 精确实现或机器入口 | 本步输出 |
| --- | --- | --- | --- |
| 1. 编译 Look 工单 | 从冻结 BodyFit、Identity、Appearance 和 Outfit 生成首批 Look 配置 | [`cc_build_first_batch_full_reference_looks_v3.py`](../../../../../00_engine/scripts/character_creator/cc_build_first_batch_full_reference_looks_v3.py)；精确配置见 [CC 组装 Technical](../technical/character_creator/ASSEMBLY_AND_ACCEPTANCE.md#2-当前实现组成) | Look Manifest、待构建清单和输入哈希 |
| 2. 验证 Bridge | 确认当前 CC 进程、Heartbeat 和允许命令有效 | [`cc_bridge_client.py`](../../../../../00_engine/character_creator_bridge/cc_bridge_client.py)；健康检查见 [Bridge Technical](../technical/bridge/CC_BRIDGE_OPERATIONS.md#3-验证与健康检查) | 当前会话 Bridge 结果 |
| 3. 装配并保存 | 从规范源项目加载，按身份/身体、比例、外观、毛发和服装顺序执行 RLPy 作业 | CC 内执行器 [`cc_validate_body_reconstruction.py`](../../../../../00_engine/scripts/character_creator/cc_validate_body_reconstruction.py)；操作顺序见 [组装顺序](../technical/character_creator/ASSEMBLY_AND_ACCEPTANCE.md#5-组装顺序) | 规范 `.ccProject`、逐 Look 报告和截图 |
| 4. 机器与视觉验收 | 检查 Inventory、眼口动态、材质接缝、服装静态/动作兼容和可重载性 | 聚合器 [`cc_audit_first_batch_full_reference_matrix_v1.py`](../../../../../00_engine/scripts/character_creator/cc_audit_first_batch_full_reference_matrix_v1.py)；视觉标准见 [视觉审查](../technical/validation/VISUAL_REVIEW.md) | `VAL-CC-01/VAL-CC-02` 证据与失败记录 |
| 5. 冻结 CC 资产 | 恢复规范中性状态，保存最终项目、Manifest、哈希和人工决定 | 当前接受版本由 [WF-30 状态](../project_management/status/workflows/WF-30.md) 指定 | `OUT-WF30-CC-ASSETS` |

当前实现是首批特化的分阶段自动化。它能复现已冻结首批 Look，但没有“任意新矩阵一键组装”入口；新矩阵必须先新增计划、Manifest 和执行包装器。

## 5. 输出契约

| 输出 ID | 逻辑产物 | 存储类别 | 生产所有者 |
| --- | --- | --- | --- |
| `OUT-WF30-CC-ASSETS` | 被接受的 `.ccProject`、Look Manifest、机器报告、视觉决定和失败记录 | `external_binary` + `run_evidence` | [CC 组装与验收](../technical/character_creator/ASSEMBLY_AND_ACCEPTANCE.md) |

### 输出组成、用途与下游

| 组成 | 实际内容 | 为什么需要 | 下游消费者 |
| --- | --- | --- | --- |
| 规范 CC 项目 | 每个被接受 Look 的可重载 `.ccProject` | 保留 CC 端可追溯源状态并允许重导出 | `WF-40` 导出和后续 CC 修复 |
| Look Manifest | Look ID、BodyFit、Identity、Appearance、Outfit、来源和哈希 | 证明项目内容与冻结矩阵一致 | `WF-40` 工单与 `WF-70` 图源 |
| 机器验收报告 | Inventory、项目可重载、计数、路径和哈希检查 | 捕获肉眼不可见的结构错误 | `VAL-CC-01/VAL-CC-02` |
| 视觉决定 | 正面/侧面/动态关键姿态、已接受风险和人工结论 | 证明眼口、服装、毛发和材质达到当前批次标准 | `GATE-30` 与 `WF-40` |
| 失败记录 | 失败 Look、弹窗、Undo/内存问题和恢复点 | 支持按 Look 恢复而不污染已接受项目 | Bridge 恢复和后续缺陷修复 |

当前项目、配置和证据位置由 [WF-30 状态](../project_management/status/workflows/WF-30.md#当前输出与证据) 指定；稳定组成与保留语义见 [输出契约目录](../technical/output/OUTPUT_CONTRACTS.md#34-out-wf30-cc-assets)。FBX/JSON/纹理不属于本输出，而属于 `WF-40`。

## 6. 必需验证

| 验证 ID | 角色 | 何时需要 |
| --- | --- | --- |
| `VAL-BRIDGE-01` | `conditional` | 使用 Bridge 自动组装时，确认请求只执行一次并有终态 |
| `VAL-CC-01` | `required` | BodyFit、Identity、眼口和动态面部验收 |
| `VAL-CC-02` | `required` | Outfit 结构、极端体型和动作兼容验收 |

定义、证据和通过条件见 [验证目录](../technical/validation/VALIDATION_CATALOG.md)。

## 7. Exit Gate

`GATE-30 CC_ASSETS_ACCEPTED` 要求矩阵完整、保存项目可重载、动态关键姿态无未接受错误、证据和源哈希一致。

## 8. 技术与状态

- [CC 组装与验收](../technical/character_creator/ASSEMBLY_AND_ACCEPTANCE.md)
- [Bridge 操作](../technical/bridge/CC_BRIDGE_OPERATIONS.md)
- [视觉验收](../technical/validation/VISUAL_REVIEW.md)
- [当前 WF-30 状态](../project_management/status/workflows/WF-30.md)

## 9. 失败与恢复

单角色失败应隔离到独立运行，不污染已接受项目。未知 CC 弹窗、Undo 错误或资源持续增长按恢复手册停止并重启批次。
