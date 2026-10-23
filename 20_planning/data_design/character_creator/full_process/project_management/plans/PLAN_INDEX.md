# 计划生命周期索引

> 文档 ID：`PLAN-INDEX`
> 文档类型：`plan_index`
> 生命周期：`current`
> 权威范围：当前计划、其他未完成计划和完成计划导航
> 最近核验：2026-10-14（唯一current父计划R10实现交付完成，人工审查pending）

## Current

执行状态要求一个 current；仅显式 `idle_after_completed_plan` / `current_plan_id=null` 的结项空闲状态允许并要求此表没有 current 项。不得自动晋升 queued 任务来填充此表。

| Plan | 状态 | 当前需求 | 影响阶段 |
| --- | --- | --- | --- |
| [PLAN-2026-10-CAMERA-MOTION-SCENE-ALIGNMENT](./active/PLAN-2026-10-CAMERA-MOTION-SCENE-ALIGNMENT.md) | current | R10实现/双场景试点交付completed，待用户轨迹与可用组合人工校验；R02/R05暂停 | WF-60/WF-80 |

## Queued

| Plan | 状态 | 排队内容 | 影响阶段 |
| --- | --- | --- | --- |
当前没有排队主计划；候选不自动晋升。

其他候选见 [Backlog](./queued/BACKLOG.md)。

## Paused

| Plan | 暂停原因 | 剩余需求与恢复条件 |
| --- | --- | --- |
| [PLAN-2026-08-FIRST-DATA-BATCH](./paused/PLAN-2026-08-FIRST-DATA-BATCH.md) | 当前主任务切换为资产与输出清理；第一批生产、上传和训练使用已由用户确认完成 | R01–R07 完成，R08/R09 的本地机器证据同步 `deferred`；服务器 Manifest/QA/Checksums 与训练运行清单具备审计条件后恢复证据收口 |

## Completed

| Plan | 完成日期 | 结果 |
| --- | --- | --- |
| [全工作区整理与清理](../history/completed_plans/PLAN-2026-10-WORKSPACE-CLEANUP.md) | 2026-10-12 | 全盘11批清理、现用依赖保护及漏判恢复、1153唯一测试闭环；无下一执行任务 |
| [动作整理、竖屏与场景试点](../history/completed_plans/PLAN-2026-10-MOTION-PORTRAIT-SCENE-PILOT.md) | 2026-10-12 | 201条展示结果获用户接受；旧动作跨性别兼容仍待验证，自动交互未执行 |
| [当前流程保留与清理](../history/completed_plans/PLAN-2026-10-CURRENT-PIPELINE-CLEANUP.md) | 2026-10-11 | 已审查过期输出及1417UE包清理完成，现用依赖/视频保留及重启检查通过 |
| [共用镜头库完整角度](../history/completed_plans/PLAN-2026-10-CAMERA-LIBRARY-EXPANSION.md) | 2026-10-11 | 最终147组合用户与师兄全部接受；旧14决策被新方案替代，不推断生产Gate |
| [相机动作小样](../history/completed_plans/PLAN-2026-10-CAMERA-MOTION-PILOT.md) | 2026-10-09 | 34审查视频＋实际复现、1072回归及浏览器入口完成；pixel-exact失败明确保留，待用户选择 |
| [完整身体动作循环审查](../history/completed_plans/PLAN-2026-10-FULL-MOTION-LOOP-REVIEW.md) | 2026-10-09 | R01–R03完成；男女15.0667秒两周期、操作/配置、916回归及可见UI通过，接缝/自然度待审 |
| [四类表情接入与无道具动作扩充](../history/completed_plans/PLAN-2026-10-FACE-AND-MOTION-LIBRARY-EXPANSION.md) | 2026-10-09 | R00–R05技术完成；最终界面、五秒代表视觉、932回归及文档闭环，用户自然度pending |
| [五秒自然面部表演试验](../history/completed_plans/PLAN-2026-10-NATIVE-FACE-FIVE-SECOND.md) | 2026-10-08 | 原速五秒候选、男女身体代表及八段修正视频技术完成；用户自然度pending，旧库不替换 |
| [完整角色配置与现成面部库](../history/completed_plans/PLAN-2026-10-CHARACTER-RUNTIME-FACE-LIBRARY.md) | 2026-10-08 | R01–R05技术完成，20＋24运行步骤通过，可见面板交付；用户最终视觉审查pending |
| [橙、金与银白发色改良](../history/completed_plans/PLAN-2026-10-HAIR-PALETTE-REFINEMENT.md) | 2026-10-07 | 十项色板/21轮99组合/保存保护/交付及627回归完成；用户新色接受未代签 |
| [完整角色服装诊断、共享鞋与发型发色](../history/completed_plans/PLAN-2026-10-COMPLETE-CHARACTER-WARDROBE-DIAGNOSIS.md) | 2026-10-07 | 当前授权范围完成；用户最终接受8色＋原色，分类取消、眼色不采用；鞋修复取消，延期项不自动恢复 |
| [完整角色服装/发型/身体动作审查界面](../history/completed_plans/PLAN-2026-10-COMPLETE-CHARACTER-WARDROBE-HAIR-REVIEW.md) | 2026-10-05 | R01–R04工具交付完成；666网格、十动作/额外骨动态、保存重载/UIready、37基线保护及342回归通过；合身/穿模人工待审 |
| [完整男女角色UE静态骨架试点](../history/completed_plans/PLAN-2026-10-COMPLETE-CHARACTER-UE-SKELETON-PILOT.md) | 2026-10-05 | 既有FBX各六部件/源Morph与118骨完整、旧参考精确对照、各一发型静态复用及图形编辑器重载；仅分性别候选，未测新身份共骨架/动作/新人工视觉 |
| [CC统一角色创建](../history/completed_plans/PLAN-2026-10-CC-CHARACTER-CREATION-AUTOMATION.md) | 2026-10-05 | 女性photo早版与男性raw当前v2完整机器流程/各8R06及保存通过，当前male完成跳过0新增；无新人工视觉、真实batch或UE执行 |
| [Headshot基础外观装配](../history/completed_plans/PLAN-2026-10-HEADSHOT-BASE-ASSEMBLY.md) | 2026-10-05 | R01–R06completed；单女性代表机器与中性/闭眼/微笑/张嘴人工接受，恢复wrapper测试+prepare通过，无真实batch/后续UE执行 |
| [固定头型材质定向修复](../history/completed_plans/PLAN-2026-10-FIXED-HEAD-MATERIAL-REPAIR.md) | 2026-10-05 | 发辫/身体材质保存、代表及用户参考场景外观通过；索引发布、264readback、防复发/guard及307回归/16子系统和归档终验通过 |
| [固定头型发型人工审查](../history/completed_plans/PLAN-2026-10-FIXED-HEAD-HAIR-VISUAL-REVIEW.md) | 2026-10-05 | 双角色界面、全部静态贴合用户确认与两项材质原因/建议交付；正式修复未实施 |
| [固定男女参考头型双版本发型](../history/completed_plans/PLAN-2026-10-HEADSHOT-FIXED-SCALP.md) | 2026-10-05 | R01–R05 完成；全量转移、索引加载、299 回归及终态文档审计通过；独立 25 文档状态测试通过，基础装配不自动启动 |
| [资产、输出与目录清理](../history/completed_plans/PLAN-2026-10-ASSET-CLEANUP.md) | 2026-10-01 | R01–R05 完成，保留源哈希、现用审查/重载和必要回归通过；不实施新身份或男性适配 |
| [文档体系 V2 重建](../history/completed_plans/PLAN-2026-08-DOCUMENTATION-V2.md) | 2026-08-25 | 新 Master、Workflow、Technical、状态/计划、输出治理、审计和维护 Skill |
| [首批 Motion 人工导出](../history/completed_plans/PLAN-2026-08-FIRST-BATCH-MOTION-EXPORT.md) | 2026-08-21 | 最终动作 FBX 经人工导出和机器验收进入 UE |

[PLAN-2026-10-NEXT-STAGE-DEFINITION 已完成](../history/completed_plans/PLAN-2026-10-NEXT-STAGE-DEFINITION.md)：2026-10-02 用户范围及实施验收明确。
