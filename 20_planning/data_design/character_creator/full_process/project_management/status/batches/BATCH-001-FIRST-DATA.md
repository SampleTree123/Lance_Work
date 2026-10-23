# BATCH-001 第一批多轮视频编辑数据

> 文档 ID：`BATCH-001-FIRST-DATA`
> 文档类型：`batch_status`
> 生命周期：`current`
> 所属计划：[`PLAN-2026-08-FIRST-DATA-BATCH`](../../plans/paused/PLAN-2026-08-FIRST-DATA-BATCH.md)（本地证据收口暂停）
> 证据收口阶段：`WF-80/WF-90`；生产已由用户确认完成
> 最近核验：2026-10-01（批次生产完成保持；仅证据同步暂停）

## 冻结规格

机器权威字段见 [`PROJECT_STATE.json`](../PROJECT_STATE.json) 和正式 source manifest。本批使用男女两个兼容域、四个原子编辑轴、固定 Happy 表情、五秒 1440p30 媒体。

## 阶段进度

| 阶段 | 状态 |
| --- | --- |
| 批次定义 | 完成 |
| 资产矩阵 | 完成 |
| CC 角色与 Look | 完成 |
| UE 导入与表演 | 完成 |
| 场景/相机/Sequence | 完成 |
| 图/链/Prompt/Jobs | 完成 |
| 本地代表媒体 | 完成并接受 |
| 正式执行器本地 Smoke | 完成并接受（2/2 真渲染；2/2 哈希恢复） |
| 正式服务器媒体 | 用户确认已完成；服务器证据待同步 |
| GT/Sidecar 契约 | 本地正式执行器已验证；完整批次机器证据待同步，用户已确认服务器完成 |
| 最终交付包 | 用户确认已上传并用于训练；发布证据待同步 |

## 权威机器产物

第一批数据当前分为结构数据、媒体执行结果和最终交付三层。只有 `WF-90` 发布候选会把它们汇聚成一个完整数据集；当前不能把任意一个本地输出目录单独称为最终数据集。

| 层/用途 | 输出契约 | 当前版本或目标位置 | 实际内容 | 格式与实现入口 | 当前状态 |
| --- | --- | --- | --- | --- | --- |
| 图、链、作业与文本 | `OUT-WF70-JOB-GRAPH` | `%OUTPUT_ROOT%/first_batch_dataset/graph_20260824_v1/` | Source/Assets/Domains、Nodes、Edges、Chains、Render Jobs、Prompt/Turn/Dialog 和构建报告 | [配置图与编辑链](../../../technical/dataset/CONFIG_GRAPH_AND_CHAINS.md#4-输出契约)、[Prompt 层](../../../technical/dataset/PROMPT_LAYER.md#4-输出) | `authoritative`，结构已完成 |
| 身份 Grounding | `OUT-WF70-JOB-GRAPH` 的输入 | `%OUTPUT_ROOT%/character_creator_bridge/artifacts/first_batch_identity_references/full_20260824_v001/` | 8 个身份的稳定参考图、描述与捕获摘要 | [Prompt 层](../../../technical/dataset/PROMPT_LAYER.md#2-权威输入)、[WF-70 状态](../workflows/WF-70.md#当前输出与证据) | `authoritative` 输入 |
| 本地代表媒体 | `OUT-WF80-NODE-MEDIA` 的验证证据 | `%OUTPUT_ROOT%/unreal_render/first_batch_32look_matrix_20260824_v002/` 与 `%OUTPUT_ROOT%/unreal_render/first_batch_chain_visual_smoke_20260824_v1/` | 32 Look 代表矩阵与代表编辑链视频/帧 | [渲染执行](../../../technical/rendering_release/RENDER_EXECUTION.md)、[WF-80 状态](../workflows/WF-80.md#当前输出与证据) | `retained_evidence`，不是完整节点媒体 |
| 正式执行器本地 Smoke | `OUT-WF80-NODE-MEDIA` 的验证证据 | `%OUTPUT_ROOT%/unreal_render/first_batch_formal_executor_smoke_20260825_v003/` | 2 个真实节点的 Run Root、视频、Sidecar、GT、Manifest、attempt 和哈希恢复证据 | [Run Root 契约](../../../technical/rendering_release/RENDER_EXECUTION.md#4-run-root-契约) | `retained_evidence`，不是 640 节点正式结果 |
| 正式服务器节点媒体 | `OUT-WF80-NODE-MEDIA` | 服务器 Run Root 待同步 | 640 个唯一节点的视频、Sidecar/GT、状态、attempt、日志和媒体 Manifest | [服务器执行](../../../technical/rendering_release/SERVER_EXECUTION.md)、[渲染执行](../../../technical/rendering_release/RENDER_EXECUTION.md#4-run-root-契约) | `pending`（用户已确认完成，证据待同步） |
| 最终统一交付包 | `OUT-WF90-DATASET-RELEASE` | 服务器发布路径待同步 | Manifest、Graph、Text、Node Media、Metadata/GT/Sidecar、QA 和 Checksums | [数据集封装](../../../technical/rendering_release/DATASET_PACKAGE.md#1-交付结构)、[WF-90 状态](../workflows/WF-90.md#当前输出与证据) | `pending`（用户已确认上传并用于训练，证据待同步） |
| UE 导入聚合证据 | `OUT-WF40-TRANSFER-BUNDLE` 的验证证据 | `%OUTPUT_ROOT%/unreal_character_import/first_batch_full_reference_expansion_20260822_v2/aggregate_import_gate.json` | 32 Look 的导入汇总和 Gate 结论 | [资产追溯](../../../technical/transfer/ASSET_TRACEABILITY.md)、[WF-40 状态](../workflows/WF-40.md#当前输出与证据) | `retained_evidence` |

从 Master 查找本批数据的固定路径是：`Master -> Project Status -> BATCH-001 -> 本表`。从本表继续时，点击“格式与实现入口”查看文件结构与生成命令，点击对应 Workflow Status 查看该层当前是否已被接受；稳定 `OUT-*` 语义统一见 [输出契约目录](../../../technical/output/OUTPUT_CONTRACTS.md)。

## 验证摘要

| 范围 | 结果 |
| --- | --- |
| 批次规格、矩阵、CC、传输、UE 运行时、场景、图与文本 | 已通过；服装局部风险按本批决定接受 |
| 本地代表节点媒体 | 已通过 |
| 正式执行器本地 2 节点真渲染与恢复 | 已通过；不等同于完整媒体 Gate |
| 正式 640 节点媒体 | `pending`；用户确认完成，Manifest/QA/哈希待同步 |
| 当前服务器像素环境 | 旧失败快照；不代表当前服务器执行状态 |
| 10 节点基准 | 用户确认服务器正式渲染完成；基准证据待同步 |
| 数据集发布 | `pending` |

精确 `VAL-*` 结果和当前 `OUT-*` 位置由对应 [Workflow Status](../workflows/README.md) 维护；本页只汇总本批执行状态。

## 已接受限制

- 服装为烘焙 Look，不执行 UE 任意换装。
- 表情不是本批编辑轴。
- 头发/头部服装和极端动作服装冲突按既有兼容性警告处理。
- Headshot、年龄、道具、多场景和通用模块化不进入本批。

## 当前阻塞与下一步

本批次不是当前下一阶段方案定义计划的执行批次；`PROJECT_STATE.active_batch_id=null` 表示没有新的生产批次正在运行，冻结值与全部已完成生产事实仍由本页维护。所属计划已转 paused，R08/R09 的服务器验收证据同步为 `deferred`；本轮清理必须保护第一批输入和有效验证证据，不自动重建或重渲染。

用户于 2026-09-22 确认服务器正式渲染、打包上传和多轮训练使用已完成。旧的 NVIDIA 565.57.01 像素失败报告保留为历史快照，不再代表当前服务器执行状态。当前缺口是同步服务器 Manifest、Run Root/上传清单、QA、Checksums 和训练运行清单；在证据闭合前不关闭 `GATE-80/GATE-90`。
