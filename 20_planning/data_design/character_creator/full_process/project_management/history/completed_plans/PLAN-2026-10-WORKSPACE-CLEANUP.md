# 全工作区整理与过期内容清理

> 文档 ID：`PLAN-2026-10-WORKSPACE-CLEANUP`
> 文档类型：`plan`
> 生命周期：`completed`
> 计划状态：`completed`
> 影响阶段：`WF-00/WF-40/WF-50/WF-60/WF-80`
> 最近核验：2026-10-12

## 目标与授权

用户授权清理整个 `D:/UE` 工作区，重点为 `Lance_Work/00_engine/outputs`。明确无当前用途的旧结果、缓存、脚本、关卡和资产可以自主删除，仅完全无法判定的项目保留询问。日期和历史文档引用只作线索，不作为唯一删除或永久保留依据。保护当前角色与模块化外观、动作/表情、已接受相机/媒体、场景、原始不可替代输入及另一会话皮肤实验依赖。早期男女动作跨性别验证留作后续，本轮不删除该待验证来源。

## 需求与验收

| 需求 ID | 目标 | 影响 Workflow | 验收条件 | 当前落实状态 | 证据与缺口 |
| --- | --- | --- | --- | --- | --- |
| `PLAN-2026-10-WORKSPACE-CLEANUP/R01` | 记录试拍接受和全工作区盘点 | WF-00/WF-60 | 用户范围准确落盘；整个D:/UE目录与体积盘点 | completed | user_pilot_acceptance_v1.json及全工作区/outputs盘点 |
| `PLAN-2026-10-WORKSPACE-CLEANUP/R02` | 明确保留依赖与清理范围 | WF-40/WF-50/WF-60 | 当前配置和实际引用决定保留；逐路径说明删除理由；皮肤独立实验保护 | completed | 依赖清单与实读smoke；动作轻量依赖漏判后已重建当前配置，原报告未伪造 |
| `PLAN-2026-10-WORKSPACE-CLEANUP/R03` | 整理顶层并执行清理 | WF-00/WF-40/WF-80 | 最终绝对路径核验；分批执行与字节回执；必要路径迁移同步 | completed | cleanup_summary.json：11批实际删除，空父目录与本轮测试临时文件也已清理 |
| `PLAN-2026-10-WORKSPACE-CLEANUP/R04` | 验证当前入口并更新文档 | WF-50/WF-60/WF-80 | 保留资产/媒体、入口及依赖可用；清除失效当前描述；重建Catalog/Inventory和独立审计 | completed | 现用2095文件/94源SHA、UE依赖、网页HTTP/Range与8项离线入口通过；1153唯一测试经定向复测闭环，最终文档审计另列 |

## 实施与交付

Run Root：`%OUTPUT_ROOT%/workspace_cleanup_20261012_v1/`。Technical所有者为[输出盘点与保留](../../../technical/output/INVENTORY_AND_RETENTION.md)，输出沿用OUT-GLOBAL-OUTPUT-INVENTORY，文档验证VAL-DOC-01。root串行控制共享UE，agents可并行离线盘点、依赖检查和文档同步。删除已审查文件使用同一原生PowerShell路径语义，不跨shell拼接删除；不改变另一会话工作成果。

最终交付包括删除/迁移清单、释放文件字节和磁盘净变化的区别、保留入口验证、整理后的目录说明及完全不能判定的少量项目。无授权生产扩展、皮肤修改或动作重做。

## 最终结果与证据

11批共删除101,734个文件、161,756,367,748字节（150.647GiB逻辑文件大小）；见 `%OUTPUT_ROOT%/workspace_cleanup_20261012_v1/cleanup_summary.json`。当前入口、媒体、角色与皮肤依赖已核验，旧动作轻量依赖漏判已明确恢复为assets下当前配置，旧报告没有伪造。1153唯一测试结果经过完整运行及定向复测闭环，详见 `regression_reconciled_v1.json`；不是一次全绿完整调用。最终独立文档审计见 `documentation_final_v1.json`。

## 后续范围

未纳入旧动作跨性别兼容实测、新场景扩充或正式拍摄。当前无下一授权执行任务，进入idle/current=null，等待用户讨论项目计划。旧原帧需重渲染，已退休CC中间断点/旧关卡/旧脚本不再承诺逐步恢复；现用视频及再生成配置保留。
