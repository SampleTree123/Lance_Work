# Character Creator `full_process` 文档地图

> 文档角色：`documentation_navigation`
> 唯一权威入口：[`CHARACTER_FACTORY_MASTER_SPEC.md`](./CHARACTER_FACTORY_MASTER_SPEC.md)
> 最近核验：2026-08-06

本目录覆盖 Character Creator 5 成人角色工厂、离线自动化 Bridge、CC 到 Unreal Engine 5.8 传输，以及 UE 内模块化角色和动画 Pilot。它不接管脚本、输出、CC 素材库或 UE 工程；这些外部目录由 [`reference/EXTERNAL_DIRECTORIES.md`](./reference/EXTERNAL_DIRECTORIES.md) 解释并索引。

## 建议阅读路线

| 目标 | 阅读顺序 |
| --- | --- |
| 第一次了解项目 | Master → [`CURRENT_STATUS.md`](./CURRENT_STATUS.md) → [`planning/ROADMAP.md`](./planning/ROADMAP.md) |
| 生成一个现有规则内的 CC 角色 | Master 第 9 节 → [`cc_details/CHARACTER_ASSEMBLY_RUNBOOK.md`](./cc_details/CHARACTER_ASSEMBLY_RUNBOOK.md) → [`validation/VALIDATION_AND_RECOVERY.md`](./validation/VALIDATION_AND_RECOVERY.md) |
| 修改体型、人脸或外观池 | 对应 `cc_details` 技术文档 → ADR → 机器配置 |
| 诊断 CC 通信 | [`bridge_details/BRIDGE_OPERATIONS.md`](./bridge_details/BRIDGE_OPERATIONS.md) |
| 把角色送入 UE | [`cc_ue_transfer/EXPORT_IMPORT_RUNBOOK.md`](./cc_ue_transfer/EXPORT_IMPORT_RUNBOOK.md) → `ue_details` |
| 继续后续阶段 | [`planning/ROADMAP.md`](./planning/ROADMAP.md) → 对应子目录能力矩阵 |
| 查找决定原因或历史结果 | [`decisions/README.md`](./decisions/README.md) → [`history/MILESTONE_LOG.md`](./history/MILESTONE_LOG.md) |

## 目录职责

| 目录 | 当前职责 | 未来扩展位置 |
| --- | --- | --- |
| `cc_details/` | BodyFit、面部、外观和完整 CC 装配 | Headshot、儿童体型、服装、CC 动画、道具准备 |
| `bridge_details/` | 安装、健康检查、队列、命令和恢复 | 完整角色命令、批任务、取消与监控 |
| `cc_ue_transfer/` | CC 导出、UE 导入、资产追溯 | 批量导出、LOD、贴图优化、版本迁移 |
| `ue_details/` | 模块化角色、动画、Morph | 服装切换、毛发物理、道具、场景、MRQ 渲染 |
| `validation/` | 共用质量门禁和故障恢复 | 大规模回归、性能和渲染验收 |
| `planning/` | 当前路线图和未承诺候选 | 新阶段按依赖追加 |
| `decisions/` | 已接受技术决策及理由 | 新增或取代 ADR |
| `reference/` | 路径、代码、配置、术语索引 | 新外部系统和机器配置 |
| `history/` | 里程碑与不可变旧文档 | 按日期追加快照，不定义当前行为 |

逐目录、逐文件的完整索引见 [`CHARACTER_FACTORY_MASTER_SPEC.md` 第 3.3 节](./CHARACTER_FACTORY_MASTER_SPEC.md#33-按目录划分的完整文档索引)；本页只保留快速导航，不重复完整清单。

## 快速状态

- 当前成人身体池为 10 个 hash 锁定 BodyFit。
- Face V3 有 20 个 seed、17 个生产主原型和 200 条确定性配方。
- 面部外观池已登记 21 皮肤、12 眼球材质、13 眉毛、9 睫毛、2 牙齿、5 男性胡须和 58 发型。
- M02 已完成 CC→UE、模块化拆分、身体/面部动画、Elder Morph 与混合面部动画 Pilot。
- 当前下一阶段为离线 Headshot 4 人 smoke；完整十体型 UE 导出、服装、三发型和端到端渲染仍未完成。

精确版本、已知不一致和在线状态见 [`CURRENT_STATUS.md`](./CURRENT_STATUS.md)。
