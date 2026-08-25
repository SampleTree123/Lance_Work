# PLAN-2026-08 第一批多轮视频编辑数据

> 文档 ID：`PLAN-2026-08-FIRST-DATA-BATCH`
> 文档类型：`plan`
> 生命周期：`current`
> 计划状态：`current`
> 影响阶段：`WF-10..WF-90`
> 完成条件：第一批数据通过 `GATE-90 DATASET_RELEASED`
> 最近核验：2026-08-25

## 目标

交付一批可追溯、可独立验证的多轮视频编辑数据，先完整跑通 CC、UE、配置图、文本、服务器渲染和封装链路，不等待全部长期角色工厂能力。

## 需求与落实

| ID | 需求 | 影响阶段 | 状态 | 证据入口 |
| --- | --- | --- | --- | --- |
| `R01` | 冻结编辑轴、媒体和交付规格 | `WF-10` | `completed` | [批次状态](../../status/batches/BATCH-001-FIRST-DATA.md) |
| `R02` | 冻结完整 Look、动作、相机和表情策略 | `WF-20` | `completed` | [WF-20 状态](../../status/workflows/WF-20.md) |
| `R03` | 完成 CC Look、Bundle 和 UE FullReference | `WF-30/WF-40` | `completed` | [WF-40 状态](../../status/workflows/WF-40.md) |
| `R04` | 验证动作、表情、材质和防 T-pose | `WF-50` | `completed` | [WF-50 状态](../../status/workflows/WF-50.md) |
| `R05` | 固定场景、四相机和五秒 Sequence | `WF-60` | `completed` | [WF-60 状态](../../status/workflows/WF-60.md) |
| `R06` | 生成并验证图、链、Prompt 和 Render Jobs | `WF-70` | `completed` | [WF-70 状态](../../status/workflows/WF-70.md) |
| `R07` | 实现正式节点执行器、GT、Sidecar、Manifest 和重试 | `WF-80` | `completed` | [WF-80 状态](../../status/workflows/WF-80.md) |
| `R08` | 服务器预检、项目 Smoke 和 10 节点基准 | `WF-00/WF-80` | `pending` | [服务器执行](../../../technical/rendering_release/SERVER_EXECUTION.md) |
| `R09` | 完整渲染、QA、文本媒体解析和发布包 | `WF-80/WF-90` | `pending` | [WF-90 状态](../../status/workflows/WF-90.md) |

## 当前执行顺序

1. 完成 `R08` 的仓库/UE 项目同步、服务器预检与 10 节点性能基准。
2. 运行全部正式 Render Jobs，按 `node_id` 重试。
3. 完成 `R09` 的媒体/文本/链解析、QA、哈希和发布封装。

## 不包含

通用 UE 模块化换装、Headshot 全面替换 Face V3、年龄编辑、道具、多场景、完整表情轴和全部动画资产不作为本计划完成条件。

## 停止条件

- 配置或资产哈希与冻结输入不一致。
- 同一 `node_id` 产生冲突媒体。
- 服务器不能稳定加载项目或 10 节点基准无法给出可接受执行方案。
- 需要改变节点语义、媒体规格或链契约但没有新版本计划批准。
