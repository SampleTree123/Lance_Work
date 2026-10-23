# 完整身体动作与五秒表情循环审查

> 文档 ID：`PLAN-2026-10-FULL-MOTION-LOOP-REVIEW`
> 文档类型：`plan`
> 生命周期：`completed`
> 计划状态：`completed`
> 影响阶段：`WF-50`
> 最近核验：2026-10-09（R01–R03限定技术交付完成）

## 目标与授权

用户已自行计时确认此前代表播放约五秒，要求持续循环以查看完整身体动作，允许现有五秒表情重复。仅改变审查播放方式，旧五秒资产和生产窗口保留，不重开旧动作扩充计划。

## 需求与验收

| 需求 ID | 目标 | 影响 Workflow | 验收条件 | 当前落实状态 | 证据 |
| --- | --- | --- | --- | --- | --- |
| `PLAN-2026-10-FULL-MOTION-LOOP-REVIEW/R01` | 完整身体原速循环及五秒脸重复 | `WF-50` | 完整身体原速跨片尾继续，脸五秒重复且不改源五秒资产 | `completed` | L1/show_result_v1.json及男女composition全905帧通过；native_cycles_v1.json男女均跨15.0667秒片尾两次 |
| `PLAN-2026-10-FULL-MOTION-LOOP-REVIEW/R02` | 保持审查操作与装配 | `WF-50` | 男女代表暂停/恢复，切动作状态/角色，配置保存恢复、外观保持和可见入口 | `completed` | L1/smoke_summary_v1.json八事件通过，delivery_v1.json绑定可见ready及保护；不冒称所有穿搭重验 |
| `PLAN-2026-10-FULL-MOTION-LOOP-REVIEW/R03` | 验证并记录交付边界 | `WF-50` | 必要回归、目录和文档审计通过，循环/自然度边界明确 | `completed` | L1/regression_v1.xml为916通过、无失败/错误/跳过；documentation_final_audit_v1.json独立子系统与跨层终验；指南和技术owner已同步 |

## 实现与输出

- 技术所有者：[Animation §10](../../../technical/unreal/ANIMATION_EXPRESSION_MORPH.md#10-完整动作循环审查)。
- 当前落实：[WF-50 Status](../../status/workflows/WF-50.md)。
- L1=`%OUTPUT_ROOT%/unreal_character_import/full_motion_loop_review_20261009_v1/`，沿用OUT-WF50-RUNTIME-ACCEPTANCE、VAL-UE-01/02及unclassified保护，未授权删除。

## 完成与未纳入范围

2026-10-09限定技术交付完成并归档。身体回起点时脸也重置；循环不保证无缝。此次仅男女007带笑完整周期实测与有界运行操作，不等于全40身份/全部衣服/所有动作全时长自然度通过。用户最终视觉接受pending；不自动开始新动作、道具、场景或生产任务。
