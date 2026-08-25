# PLAN-2026-08 首批动作选择与导出

> 文档 ID：`PLAN-2026-08-FIRST-BATCH-MOTION-EXPORT`
> 文档类型：`completed_plan`
> 生命周期：`completed`
> 影响阶段：`WF-20/WF-40/WF-50`
> 完成日期：2026-08-24
> 最近核验：2026-08-25

## 结果

从 P0 候选中完成人工五秒窗口选择、替换不可用动作、CC FBX 导出、UE 同性 Skeleton 导入和 Runtime 验证。最终生产池为女性 5 个、男性 5 个；`ACT_F02_CATCH_BREATH` 使用批准 InPlace，其余动作保留源 Root Motion。权威清单已迁移到 `cc_first_batch_action_pool_20260824_v1.json` 和 `first_batch_graph_source_20260824_v1.json`。

## 最终需求状态

| 需求 | 结果 |
| --- | --- |
| 人工选择五秒窗口并锁定动作 ID | `completed` |
| 替换许可/导出失败动作 | `completed` |
| 导出并规范化男女动作 FBX | `completed` |
| 导入同性 UE Skeleton 并排除 T-pose | `completed` |
| 登记唯一 InPlace 例外 | `completed` |

## 接受证据

- 生产动作池：`00_engine/scripts/character_creator/cc_first_batch_action_pool_20260824_v1.json`。
- 动作导入证据：`%OUTPUT_ROOT%/unreal_character_import/first_batch_motions_20260822_v1/`。
- 当前下游图源：`00_engine/scripts/dataset/first_batch_graph_source_20260824_v1.json`。

## 未纳入范围

该计划没有承诺全 P0 动作库、道具动作、完整面部表演或通用动作导出器；这些能力仍需独立计划和验证。
