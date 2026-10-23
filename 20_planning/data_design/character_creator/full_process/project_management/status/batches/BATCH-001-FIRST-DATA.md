# BATCH-001 第一批多轮视频编辑数据

> 文档 ID：`BATCH-001-FIRST-DATA`
> 文档类型：`batch_status`
> 生命周期：`current`
> 当前计划：`PLAN-2026-08-LANCE-DIALOGUE-FIRST-FINETUNE`
> 当前阶段：`WF-90`
> 最近核验：2026-08-31

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
| 正式服务器媒体 | 完成；`v004` 640/640 accepted，13 个 UE invocation 均 exit 0，累计机器 Gate 与分层视觉抽样通过 |
| GT/Sidecar 契约 | 完成；640/640 Sidecar、配置、媒体规格、SHA-256 和状态一致 |
| 最终交付包 | v002 `dataset_v1` 已发布：640 视频、4,000 完整链、1..4000 简化链和 15,000 Turn；本机 QA、用户签字、自包含全量验证及 `JDS9B74/job118880` 候选态/发布态独立复验均完成 |

## 权威机器产物

- 配置图与文本根：`%OUTPUT_ROOT%/first_batch_dataset/graph_20260824_v1/`
- 当前正式发布：`%OUTPUT_ROOT%/delivery/first_batch_candidate_20260830_v002/dataset_v1/`（Manifest `released`）
- 最终运行与 QA 紧凑证据：`%OUTPUT_ROOT%/delivery/first_batch_candidate_20260830_v002/release_evidence/`
- 清理清单：`project_management/history/reports/FIRST_BATCH_STORAGE_CLEANUP_20260830.json`

历史 Smoke、预检、Run Root 和 staging 已在证据迁移后清理。当前 released 包是唯一保留的第一批媒体集合；发布结论由 `WF-90` 汇聚。

## 验证摘要

| 范围 | 结果 |
| --- | --- |
| 批次规格、矩阵、CC、传输、UE 运行时、场景、图与文本 | 已通过；服装局部风险按本批决定接受 |
| 本地代表节点媒体 | 已通过 |
| 正式执行器本地 2 节点真渲染与恢复 | 已通过；不等同于完整媒体 Gate |
| H200/580 Tokyo 生产候选 | 已通过；人物内容、首帧相机、逐帧确定性、10/10 基准和中断恢复成立 |
| 正式 640 节点媒体 | `passed`；`v003` 禁止交付/复用，`v004` 640/640 accepted、13 个 invocation 全部 exit 0 |
| 当前服务器像素环境 | `passed_with_accepted_risk`；H200/580.126.20 正式 Tokyo MRQ 通过，565.57.01 失败；最终 profile 的 Vulkan Validation layers 尚未补测 |
| 10 节点基准 | `passed`；10/10 accepted，中断后 7 reused + 3 rendered，随后 10/10 全复用 |
| 单 UE 50 节点资源边界 | `passed`；`v003` 单 invocation 连续完成 50 个节点并 graceful exit 0，但媒体视觉 Gate 后续失效 |
| 修复后首帧回归 | `passed`；同一 UE PID 连续 6/6 accepted，覆盖 F01/F02/F05/M01/M04/M06 与 high/side/far，首帧 MAD `0.53..2.63` |
| 修复后单 UE 50 节点媒体 Gate | `passed`；`first_batch_server_production_20260829_v004` 由单个 UE 50/50 accepted、累计审计通过、graceful exit 0，并人工复核旧问题节点 `n_14d5d6460aa8d9bd` 前四帧 |
| 数据集发布 | `passed`；独立节点对候选态和发布态完成两次全包验证，`VAL-RELEASE-01/GATE-90` 已关闭 |
| 清理后自包含验证 | `passed`；无 Render Run Root 条件下 640 视频、4,000 完整/简化链和 15,000 Turn 全部通过 |

精确 `VAL-*` 结果和当前 `OUT-*` 位置由对应 [Workflow Status](../workflows/README.md) 维护；本页只汇总本批执行状态。

## 已接受限制

- 服装为烘焙 Look，不执行 UE 任意换装。
- 表情不是本批编辑轴。
- 头发/头部服装和极端动作服装冲突按既有兼容性警告处理。
- Headshot、年龄、道具、多场景和通用模块化不进入本批。

## 当前阻塞与下一步

565.57.01 路径仍有明确外部环境阻塞，证据见 [服务器 Vulkan 阻塞报告](../../history/reports/REPORT-2026-08-28-UE58-SERVER-VULKAN-BLOCKER.md)。`8GS9B74/H200/580.126.20` 的 640 节点媒体 Gate 与 `JDS9B74/job118880` 的独立发布 Gate 均通过。当前下游先对 released 链执行确定性随机 3,600/200/200 划分与零泄漏审计，再冻结 Lance `dialogue` 四卡全参数单 Epoch 配置；最终 Vulkan Validation 边界继续作为 post-release 风险保留。
