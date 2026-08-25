# WF-80 本地验证与批量渲染

> 文档 ID：`WF-80`
> 文档类型：`workflow`
> 生命周期：`current`
> 前序：`WF-70`
> 后序：`WF-90`
> Exit Gate：`GATE-80 MEDIA_COMPLETE`
> 最近核验：2026-08-25

## 1. 目的与使用时机

使用已接受的 render jobs 先完成本地 Smoke 和服务器基准，再可续跑地生成全部唯一节点媒体。

## 2. 前后序与进入条件

- 前序：`WF-70`；后序：`WF-90`。
`GATE-70` 通过；目标机器环境、项目资产和输出空间已预检。

## 3. 输入

Render Jobs、UE 项目、Sequence 模板、MRQ Profile、资产哈希和服务器路径映射。

## 4. 正常流程

| 步骤 | 操作 | 精确实现或机器入口 | 当前实现状态 | 本步输出 |
| --- | --- | --- | --- | --- |
| 1. 编译本地 Smoke/矩阵 | 把代表链或冻结 Look 矩阵转换为 UE 可执行配置 | [`build_first_batch_chain_render_matrix_v1.py`](../../../../../00_engine/scripts/unreal/build_first_batch_chain_render_matrix_v1.py) 与 [`run_first_batch_render_matrix.py`](../../../../../00_engine/scripts/unreal/run_first_batch_render_matrix.py) | `production`，已完成本地证据 | 本地 Render Matrix 与计划报告 |
| 2. 审计并搭建 UE 舞台 | 检查 Look、Skeleton、Composite、相机和 Profile，再设置 staging Actor/Sequence | [`ue_audit_first_batch_render_assets.py`](../../../../../00_engine/scripts/unreal/ue_audit_first_batch_render_assets.py)、[`ue_stage_first_batch_render_look.py`](../../../../../00_engine/scripts/unreal/ue_stage_first_batch_render_look.py) | `production` | UE 依赖审计和 staging 结果 |
| 3. 渲染本地样例并验证 | 运行 150 帧 MRQ 样例/矩阵，检查媒体规格、运动、T-pose 和白块 | [`run_first_batch_local_sample_render.py`](../../../../../00_engine/scripts/unreal/run_first_batch_local_sample_render.py)、[`ue_start_first_batch_local_sample_render.py`](../../../../../00_engine/scripts/unreal/ue_start_first_batch_local_sample_render.py)、[`validate_first_batch_chain_visual_smoke_v1.py`](../../../../../00_engine/scripts/unreal/validate_first_batch_chain_visual_smoke_v1.py) | `production`，代表 Smoke 已通过 | 本地媒体与 `VAL-RENDER-01` 代表证据 |
| 4. 服务器预检与基准 | 检查服务器环境/项目并执行确定性 10 节点基准 | [`FIRST_BATCH_SERVER_PREFLIGHT.sh`](../../../../../20_planning/implementation/FIRST_BATCH_SERVER_PREFLIGHT.sh)；步骤见 [服务器执行](../technical/rendering_release/SERVER_EXECUTION.md) | 环境脚本存在；目标服务器项目 Smoke/基准 `pending` | Preflight/Benchmark Run Root |
| 5. 正式节点执行与重试 | 读取 `render_jobs.jsonl`，按 Lease/attempt 渲染、校验并原子晋升媒体 | [`run_first_batch_render_jobs.py`](../../../../../00_engine/scripts/unreal/run_first_batch_render_jobs.py)；命令、字段和恢复见 [渲染执行](../technical/rendering_release/RENDER_EXECUTION.md) | `production`；本地 2 节点真渲染与哈希恢复已通过，服务器/640 节点待执行 | 正式节点媒体、Sidecar、状态和媒体 Manifest |

第 1–3 步的本地矩阵能力不能替代第 5 步。第 5 步的实现和本地小规模 Gate 已完成；当前唯一下一工作是第 4 步的服务器同步、完整预检和确定性 10 节点基准，通过后再用同一正式执行器进入全量运行。

## 5. 输出契约

| 输出 ID | 逻辑产物 | 存储类别 | 生产所有者 |
| --- | --- | --- | --- |
| `OUT-WF80-NODE-MEDIA` | 节点媒体、GT/Sidecar、运行状态、失败与重试记录、媒体哈希和完成清单 | `render_run`，通过验证后媒体晋升为 `authoritative` | [渲染执行](../technical/rendering_release/RENDER_EXECUTION.md) |

### 输出组成、用途与下游

| 组成 | 实际内容 | 为什么需要 | 下游消费者 |
| --- | --- | --- | --- |
| Run/Attempt 元数据 | Manifest、输入锁、Lease、状态、日志、机器/版本和错误分类 | 支撑断点续跑并证明每次 attempt 使用相同节点配置 | 调度器、恢复和 QA |
| 节点媒体 | `media/nodes/<node_id>/` 下唯一 accepted 视频/帧 | 给多条链复用同一语义节点，避免重复媒体 | `WF-90`、Turn/Dialog 和训练数据 |
| GT 与 Sidecar | 节点配置、实际 UE 绑定、媒体规格、版本和哈希 | 把视频像素与确定性配置连接起来 | QA、发布和可追溯研究 |
| 重试与失败记录 | `pending/accepted/retryable_failed/permanent_failed` 及 attempt 历史 | 允许只重跑失败节点且不静默删任务 | 服务器执行和发布 Gate |
| 媒体 Manifest/完成清单 | `node_id` 到媒体 URI、字节数、SHA-256 和接受状态映射 | 让图、Prompt 和发布包解析真实媒体 | `WF-90` 零悬空审计 |
| Smoke/基准证据 | 本地代表链、服务器 10 节点和视觉抽检报告 | 在全量运行前发现系统性错误并估算资源 | `VAL-RENDER-01/VAL-SERVER-01` |

本地正式 Run Root 已创建并验证，当前只覆盖 2 个代表节点，不是 640 节点正式生产结果；准确位置和缺口见 [WF-80 状态](../project_management/status/workflows/WF-80.md#当前输出与证据)。稳定组成与晋升规则见 [输出契约目录](../technical/output/OUTPUT_CONTRACTS.md#39-out-wf80-node-media)。

## 6. 必需验证

| 验证 ID | 角色 | 何时需要 |
| --- | --- | --- |
| `VAL-RENDER-01` | `required` | 本地 Smoke、基准和正式节点媒体均使用同一媒体契约验证 |
| `VAL-SERVER-01` | `conditional` | 在服务器或新渲染机器运行正式作业前必须通过 |

定义、证据和通过条件见 [验证目录](../technical/validation/VALIDATION_CATALOG.md)。

## 7. Exit Gate

`GATE-80 MEDIA_COMPLETE` 要求所有计划节点存在唯一有效媒体，规格、时间运动、角色可见性、哈希和重试状态完整，无 T-pose、黑帧或悬空作业。

## 8. 技术与状态

- [渲染执行](../technical/rendering_release/RENDER_EXECUTION.md)
- [服务器运行](../technical/rendering_release/SERVER_EXECUTION.md)
- [当前 WF-80 状态](../project_management/status/workflows/WF-80.md)

## 9. 失败与恢复

只重渲染失败节点。不得从正式节点池静默删除失败项；无法完成时按计划允许的版本化降级生成新 Render Profile 和新节点版本。
