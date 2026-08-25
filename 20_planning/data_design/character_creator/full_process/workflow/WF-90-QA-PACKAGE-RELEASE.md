# WF-90 QA、封装与发布

> 文档 ID：`WF-90`
> 文档类型：`workflow`
> 生命周期：`current`
> 前序：`WF-80`
> 后序：无
> Exit Gate：`GATE-90 DATASET_RELEASED`
> 最近核验：2026-08-25

## 1. 目的与使用时机

把媒体、图、链、Prompt、GT、Sidecar、哈希和验收证据汇聚成一个可交付、可验证、可恢复的数据包。

## 2. 前后序与进入条件

- 前序：`WF-80`；后序：无，发布完成后回到 `WF-10` 定义新批次。
`GATE-80` 通过，所有正式节点媒体已经完成且版本唯一。

## 3. 输入

配置图、链、Prompt、媒体清单、GT、Sidecar、软件/资产版本、运行报告和人工抽检决定。

## 4. 正常流程

| 步骤 | 操作 | 精确实现或机器入口 | 当前实现状态 | 本步输出 |
| --- | --- | --- | --- | --- |
| 1. 解析媒体引用 | 将 Nodes、Chains、Turns/Dialogs 的相对 URI 解析到 accepted Node Media | 字段和布局由 [数据集封装](../technical/rendering_release/DATASET_PACKAGE.md) 与 [Prompt Technical](../technical/dataset/PROMPT_LAYER.md) 定义 | 契约已定义，统一发布解析器 `pending` | 零悬空引用报告 |
| 2. 验证 GT/Sidecar/哈希 | 比对 Node 配置、UE 实际绑定、媒体规格、SHA-256 和 attempt 状态 | Sidecar 最低字段见 [数据集封装](../technical/rendering_release/DATASET_PACKAGE.md#2-节点-sidecar) | 正式 640 节点输入未完成，执行器 `pending` | 节点完整性报告 |
| 3. 执行 QA | 运行结构、统计、媒体和分层人工抽样检查 | 稳定 Gate 见 [Validation Catalog](../technical/validation/VALIDATION_CATALOG.md)；领域标准见 [视觉审查](../technical/validation/VISUAL_REVIEW.md) | 发布级 QA 编排器 `pending` | QA 报告与人工决定 |
| 4. 构建交付包 | 按统一布局汇聚 Manifest、Graph、Text、Media、Metadata、QA 和 Checksums | 目标结构见 [数据集封装](../technical/rendering_release/DATASET_PACKAGE.md#1-交付结构) | 发布 Builder 尚未实现 | 不可变 Release Candidate |
| 5. 冻结发布 | 分配 `release_id`，验证另一机器可复核并更新 Batch/Plan/里程碑 | 当前版本所有者为 [WF-90 状态](../project_management/status/workflows/WF-90.md) 和 [Batch Status](../project_management/status/batches/README.md) | `pending` | `OUT-WF90-DATASET-RELEASE` |

本阶段目前只有契约，没有可宣称完成的发布执行器或候选包。实现前不得把散布的本地输出目录称为正式数据集。

## 5. 输出契约

| 输出 ID | 逻辑产物 | 存储类别 | 生产所有者 |
| --- | --- | --- | --- |
| `OUT-WF90-DATASET-RELEASE` | 版本化交付包、QA 报告、发布 Manifest、Checksums 和保留/清理清单 | `delivery`，不可原地覆盖 | [数据集封装](../technical/rendering_release/DATASET_PACKAGE.md) |

### 输出组成、用途与下游

| 组成 | 实际内容 | 为什么需要 | 下游消费者 |
| --- | --- | --- | --- |
| Release Manifest | `batch_id/release_id`、输入版本、文件清单、QA 状态和追溯关系 | 提供交付包的单一顶层入口 | 用户、训练系统和独立审计 |
| Graph 与 Text | 冻结 Assets/Domains/Nodes/Edges/Chains/Render Jobs、Turns/Dialogs | 保留视频状态和编辑监督的完整语义 | 数据加载器和模型训练 |
| Node Media | 每个 `node_id` 的唯一 accepted 媒体 | 让多轮样本复用节点而不复制视频 | Turn/Dialog URI 解析 |
| Metadata/GT/Sidecar | 配置、UE 绑定、媒体规格、版本、attempt 和哈希 | 支撑可追溯性、QA 与复现 | 训练过滤、误差分析和再验证 |
| QA 与 Checksums | 机器报告、人工抽样、发布决定和全包哈希 | 证明包完整、未损坏且满足 Gate | `VAL-RELEASE-01` 与接收方 |
| 保留/清理清单 | 权威、证据、可替代和临时产物分类 | 防止发布后误删源证据或长期保留无用缓存 | Output 子系统和运维 |

当前尚无发布候选；未来准确位置由 [WF-90 状态](../project_management/status/workflows/WF-90.md#当前输出与证据) 指定。稳定组成、不可变性和保留语义见 [输出契约目录](../technical/output/OUTPUT_CONTRACTS.md#310-out-wf90-dataset-release)。

## 6. 必需验证

| 验证 ID | 角色 | 何时需要 |
| --- | --- | --- |
| `VAL-RELEASE-01` | `required` | 每个发布候选都必须独立执行，不能继承旧发布结果 |

定义、证据和通过条件见 [验证目录](../technical/validation/VALIDATION_CATALOG.md)。

## 7. Exit Gate

`GATE-90 DATASET_RELEASED` 要求媒体、链、文本和元数据零悬空引用，哈希一致，全部必需 QA 通过，人工抽检已签字，发布包可在另一台机器独立验证。

## 8. 技术与状态

- [数据集封装](../technical/rendering_release/DATASET_PACKAGE.md)
- [验证索引](../technical/validation/README.md)
- [当前 WF-90 状态](../project_management/status/workflows/WF-90.md)

## 9. 失败与恢复

发布前失败返回对应生产阶段修复并生成新版本。发布后发现错误不得覆盖既有版本，必须撤回并发布带新 ID 的修正版。
