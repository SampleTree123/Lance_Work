# 项目当前状态

> 文档 ID：`STATUS-PROJECT`
> 文档类型：`status`
> 生命周期：`current`
> 状态来源：[`PROJECT_STATE.json`](./PROJECT_STATE.json)、当前 Registry、验证报告和用户验收
> 当前计划：`PLAN-2026-08-FIRST-DATA-BATCH`
> 最近核验：2026-08-25

## 当前结论

角色工厂已经完成第一批本地生产链路的主要准备：冻结角色/服装 Look、生产动作、表情策略、场景与四相机均已进入 UE；配置图、原子边、多轮链、Render Jobs 和双语 Prompt 已通过机器门禁；本地代表矩阵与代表编辑链已完成媒体和视觉验证。

由 `render_jobs.jsonl` 驱动的正式节点执行器已经实现并通过本地 2 节点真渲染与哈希断点恢复。当前未完成的是正式服务器生产与交付：同步冻结仓库与 UE 二进制项目，完成服务器预检和 10 节点基准，再生成完整节点媒体并封装最终数据包。

## 活动对象

| 对象 | 当前值 |
| --- | --- |
| 当前计划 | [第一批数据计划](../plans/active/PLAN-2026-08-FIRST-DATA-BATCH.md) |
| 活动批次 | [BATCH-001-FIRST-DATA](./batches/BATCH-001-FIRST-DATA.md) |
| 当前阶段 | [`WF-80`](../../workflow/WF-80-RENDER-EXECUTION.md) |
| 当前能力状态 | [Workflow Status](./workflows/README.md) |

精确数字由 [`PROJECT_STATE.json`](./PROJECT_STATE.json) 和批次状态维护，本文件不独立定义第二份机器契约。

## 已完成的当前基线

- CC 端 8 个身份和完整 32 Look 已保存、导出并完成聚合审计。
- UE 端 32/32 FullReference 已导入，同性规范 Skeleton、Morph、材质和动态皱纹修复均通过。
- 生产动作已收敛为男女各 5 个；只有指定 Catch Breath 使用 InPlace。
- 正式节点固定 Happy；Angry/Sad 保留为后续技术候选，不进入当前图。
- TokyoStylized 场景、安全锚点、`near/far/high/side` 四相机和五秒 Sequence 已验证。
- 正式图、链、Render Jobs 和 Prompt 层已确定性生成并通过测试。
- 本地 32-Look 代表矩阵和两条代表链的媒体/视觉门禁已接受。
- 正式执行器的输入锁、Lease、attempt、GT/Sidecar、媒体 Manifest、原子晋升和 `node_id` 哈希恢复已由本地男女各 1 个真实节点验证。

## 当前限制

- 正式 640 节点媒体与服务器运行尚未完成；本地 2 节点 Sidecar/Manifest 证据不能代替完整批次 Gate。
- 服装使用烘焙 FullReference Look，第一批不提供 UE 内任意单件换装。
- 通用模块化角色只完成 M02 Pilot，不是第一批生产前提。
- Headshot 原型、三发型、道具、年龄编辑和完整表情轴不进入本批正式节点。
- 极端动作服装穿模和头发/头部服装相交仍按兼容性警告处理。

## 验证概览

- `WF-10` 至 `WF-70` 的第一批必需验证均已通过或在批次范围内以已接受风险通过。
- `WF-00` 的能力基线已验证，但 CC/UE 当前会话结果属于会话级，应用重启后为 `expired`。
- `WF-80` 的代表性本地媒体和正式执行器本地 Smoke 均已通过；正式 640 节点范围仍为 `pending`。
- `VAL-SERVER-01` 与 `VAL-RELEASE-01` 均为 `pending`。
- `VAL-DOC-01` 已通过：Workflow、Validation、Output、Technical、Status、Plan、History、Decisions、Reference、Registry、Governance、Templates 与 Master 均完成独立契约检查；正式执行器实现、`R07` 状态、输出治理和服务器下一步也已闭合。证据位于 `%OUTPUT_ROOT%/documentation_audit/documentation_rebuild_20260825_v3/`。
- 逐阶段的结果、证据和失效边界见 [Workflow Status](./workflows/README.md)。

## 当前输出入口

- 批次规格和生产矩阵：Git Registry、当前计划、Batch Status 与 `PROJECT_STATE.json`。
- 图、链、Render Jobs 和 Prompt：`%OUTPUT_ROOT%/first_batch_dataset/graph_20260824_v1/`。
- 当前本地视觉证据：`%OUTPUT_ROOT%/unreal_render/first_batch_32look_matrix_20260824_v002/` 与 `first_batch_chain_visual_smoke_20260824_v1/`。
- 正式执行器本地证据：`%OUTPUT_ROOT%/unreal_render/first_batch_formal_executor_smoke_20260825_v003/`。
- 当前文档审计证据：`%OUTPUT_ROOT%/documentation_audit/documentation_rebuild_20260825_v3/`。
- 正式服务器媒体 Run Root 和统一 Delivery 尚未创建，不能把上述本地证据目录当成交付包。

## 唯一下一步

继续 `WF-80/R08`：提交并同步冻结 Git 状态与 UE 项目/二进制资产，执行服务器环境预检、两次项目 Smoke 与确定性 10 节点性能基准。

完成后更新：`WF-00/WF-80` 状态、活动批次、当前计划需求 `R08` 和服务器基准证据。
