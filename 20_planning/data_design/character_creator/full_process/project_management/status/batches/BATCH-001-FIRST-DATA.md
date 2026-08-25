# BATCH-001 第一批多轮视频编辑数据

> 文档 ID：`BATCH-001-FIRST-DATA`
> 文档类型：`batch_status`
> 生命周期：`current`
> 当前计划：`PLAN-2026-08-FIRST-DATA-BATCH`
> 当前阶段：`WF-80`
> 最近核验：2026-08-25

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
| 正式服务器媒体 | 未开始 |
| GT/Sidecar 契约 | 本地正式执行器已验证；完整批次未完成 |
| 最终交付包 | 未完成 |

## 权威机器产物

- 配置图与文本根：`%OUTPUT_ROOT%/first_batch_dataset/graph_20260824_v1/`
- 本地代表矩阵：`%OUTPUT_ROOT%/unreal_render/first_batch_32look_matrix_20260824_v002/`
- 代表链 Smoke：`%OUTPUT_ROOT%/unreal_render/first_batch_chain_visual_smoke_20260824_v1/`
- 正式执行器本地 Smoke：`%OUTPUT_ROOT%/unreal_render/first_batch_formal_executor_smoke_20260825_v003/`
- UE 导入聚合：`%OUTPUT_ROOT%/unreal_character_import/first_batch_full_reference_expansion_20260822_v2/aggregate_import_gate.json`

这些目录目前分别承担结构输入、验证媒体和证据，不是最终交付布局。正式发布由 `WF-90` 汇聚。

## 验证摘要

| 范围 | 结果 |
| --- | --- |
| 批次规格、矩阵、CC、传输、UE 运行时、场景、图与文本 | 已通过；服装局部风险按本批决定接受 |
| 本地代表节点媒体 | 已通过 |
| 正式执行器本地 2 节点真渲染与恢复 | 已通过；不等同于完整媒体 Gate |
| 正式 640 节点媒体 | `pending` |
| 服务器环境与 10 节点基准 | `pending` |
| 数据集发布 | `pending` |

精确 `VAL-*` 结果和当前 `OUT-*` 位置由对应 [Workflow Status](../workflows/README.md) 维护；本页只汇总本批执行状态。

## 已接受限制

- 服装为烘焙 Look，不执行 UE 任意换装。
- 表情不是本批编辑轴。
- 头发/头部服装和极端动作服装冲突按既有兼容性警告处理。
- Headshot、年龄、道具、多场景和通用模块化不进入本批。

## 当前阻塞与下一步

无外部阻塞。正式节点执行器已经完成；下一步是同步冻结仓库和 UE 项目，完成服务器预检与 10 节点基准，然后批量生成媒体。
