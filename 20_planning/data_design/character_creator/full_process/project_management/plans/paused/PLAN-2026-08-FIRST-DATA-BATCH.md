# PLAN-2026-08 第一批多轮视频编辑数据

> 文档 ID：`PLAN-2026-08-FIRST-DATA-BATCH`
> 文档类型：`plan`
> 生命周期：`paused`
> 计划状态：`paused`
> 影响阶段：`WF-10..WF-90`
> 完成条件：第一批数据通过 `GATE-90 DATASET_RELEASED`
> 最近核验：2026-10-01（第一批生产已完成；仅本地验收证据同步暂缓）

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
| `R08` | 服务器预检、项目 Smoke 和 10 节点基准 | `WF-00/WF-80` | `deferred` | 用户于 2026-09-22 确认服务器正式渲染完成；服务器 Manifest、Run Root 和 QA 证据待同步，见 [WF-80 状态](../../status/workflows/WF-80.md) |
| `R09` | 完整渲染、QA、文本媒体解析和发布包 | `WF-80/WF-90` | `deferred` | 用户确认已打包上传并用于多轮训练；发布 Manifest、Checksums 和训练运行清单待同步，见 [WF-90 状态](../../status/workflows/WF-90.md) |

## 暂停原因与恢复条件

用户于 2026-09-22 已确认正式服务器渲染、打包上传和多轮训练使用完成；本计划不回退为生产未完成。尚缺的是将服务器 Run Root、Manifest、QA、Checksums 与训练运行清单同步回本地，关闭 R08/R09 的机器验收证据链。

当前主计划已经切换为[项目资产、输出与目录清理](../active/PLAN-2026-10-ASSET-CLEANUP.md)，因此本计划暂停，R08/R09 的证据同步状态为 `deferred`。原冻结输入、已接受本地执行器证据及正式生产资产继续保留；不会自动重启渲染或重建第一批。

服务器成功运行和交付证据具备可核对的路径、Manifest 与哈希，并明确恢复本地证据收口时，再将此计划恢复为 `current`；恢复前须让出当前主计划位置，继续遵守恰好一个 current 计划的规则。R01–R07 保持完成。

## 恢复后的执行顺序

1. 同步用户已确认的服务器渲染、上传和训练证据，核对 640 节点、链/文本引用、哈希和发布版本。
2. 完成 `R08/R09` 的独立 QA、Manifest 和 Checksums 审计后关闭第一批 Gate。
3. 将后续多样性工作转入独立的第二批计划；候选范围见 [Backlog](../queued/BACKLOG.md)。

## 不包含

通用 UE 模块化换装、Headshot 全面替换 Face V3、年龄编辑、道具、多场景、完整表情轴和全部动画资产不作为本计划完成条件。

## 停止条件

- 配置或资产哈希与冻结输入不一致。
- 同一 `node_id` 产生冲突媒体。
- 服务器不能稳定加载项目或 10 节点基准无法给出可接受执行方案。
- 需要改变节点语义、媒体规格或链契约但没有新版本计划批准。
