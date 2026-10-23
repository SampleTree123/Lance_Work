# PLAN-2026-10 项目资产、输出与目录清理

> 文档 ID：`PLAN-2026-10-ASSET-CLEANUP`
> 文档类型：`plan`
> 生命周期：`completed`
> 计划状态：`completed`
> 影响阶段：`WF-00/WF-30/WF-40/WF-50/WF-80`
> 完成条件：经审查的清理和目录重组完成，保留输入、现用 UE/CC 入口与证据链通过复核，文档及机器目录审计通过
> 完成日期：2026-10-01
> 最近核验：2026-10-01（清理、保留物与现用入口验收通过；未开启新身份实施）

## 目标与结论

按正式索引、应用依赖、配置引用和替代验证，完成 UE、Character Creator、导出包、项目输出和入口的精确清理与整理。当前生产输入、有效人工验收和必要故障追溯得到保留；旧执行入口退役，现用审查晋升到 v003。

本轮是独立资产治理任务，没有重新执行第一批生产。第一批服务器渲染、上传和训练使用已由用户确认完成；[第一批暂停计划](../../plans/paused/PLAN-2026-08-FIRST-DATA-BATCH.md)仅等待 R08/R09 的本地服务器验收证据。

## 需求最终落实

| ID | 需求与验收条件 | 影响阶段 | 状态 | 最终证据 |
| --- | --- | --- | --- | --- |
| `R01` | 全量盘点、文档/UE 快照、当前引用与替代审查、精确路径清单及保护边界完备 | `WF-00` | `completed` | 本轮 `ue_audit/`、`cc_audit/`、`output_audit/`、`documentation_before.lock.json`、`ue_map_before.lock.json` 和两阶段 `doc_current/source_before*/` |
| `R02` | CC、导出包、重复输出和失败大媒体精确清理；规范源、人工决定、必要小报告与后续重放映射保留 | `WF-30/WF-40` | `completed` | `cleanup_summary.json` 的成功分项回执，`cc_audit/final_cc_cleanup_execution_summary.json`、`cc_audit/final_protected_inputs_verification.json`；CC 验证为静态源/哈希与引用，不含新 CC 会话或作业 |
| `R03` | 现用审查与共享导入配置整理完成，旧 v001/v002 执行资产退出入口，独立 UE 重载及剩余依赖检查通过 | `WF-50` | `completed` | `current_review_verification.json`、`post_cleanup_ue_reload_verification.json`、`post_cleanup_runtime_checks_completion.json`、`ue_saved_graph_verification.json` |
| `R04` | 第一批、Headshot、BodyFit、正式衣柜/发型和验收证据保留验证通过，媒体替代和例外保留可追溯 | `WF-80` | `completed` | `final_retained_files_verification.json`、`formal_asset_hash_verification.json`、CC 最终保护核验、`output_audit/` 的视频/像素/二进制替代报告及 `retained_legacy_support_import_sources.json` |
| `R05` | 当前入口、状态、计划、Technical 所有者与机器目录同步，独立子系统、跨层审计和必要回归通过 | `WF-00/WF-50` | `completed` | `preclosure_documentation_audit.json` 为全子系统/跨层通过，`final_regression_tests.json` 为完整必要回归通过；结项文档终验统一登记到 `final_documentation_audit.json` |

以上文件均位于 `%OUTPUT_ROOT%/asset_cleanup/cleanup_20261001_v1/`，属于 `OUT-GLOBAL-OUTPUT-INVENTORY` 的 `retained_evidence`。保留和恢复语义见[Output 所有者](../../../technical/output/INVENTORY_AND_RETENTION.md#9-2026-10-01-全面清理与目录重组)；动态数量及当前入口由[项目状态](../../status/PROJECT_STATUS.md#本轮清理与重组)维护，本关闭计划不重复统计。

## 已完成范围与保留例外

- 按互不重叠的成功回执收敛缓存、CC/导出副本、重复图像与局部 Smoke 原帧、失败中间产物、已验证检查点和退役 UE 包；失败/续跑回执不重复计入总量。
- Coverage 和 Compatibility 现用 Plan/报告迁到 `%OUTPUT_ROOT%/unreal_character_import/current_reviews_20261001_v1/`，关卡 Actor 改用 v003。原 HairFit 及有效 Scalp/Hairline 图库保持现用；清理验证不扩大人工视觉范围。
- 当前发型导出 Manifest 晋升到 `%CC_EXPORT_ROOT%/scalp_hair_batch_20260924_v1/manifests/cc_export.json`。原 staging 元数据以原字节归档，旧 Gate 工单和接受报告保持冻结，历史重放使用显式新工单映射。
- 旧 `pilot_m02_ue58_v001` 完整导出包继续保留，因为现用 M02 共享支持资产的 ImportData 仍使用其中 FBX。目录年代或独立入口退休不构成删除重新导入源的依据。
- Headshot 来源/规范原型、BodyFit、第一批冻结输入及动作桥接项目、现行正式资产和人工决定保留并核验。没有新建生产批次、启动 CC 身份构建、改变第一批生产或重渲染服务器。

## 验证边界

本地原帧由已解码核验 MP4 与保留审查图片承担视觉证据替代，不声明无损像素等价或替代正式服务器发布媒体。UE 验证覆盖现用装配、保存/重载和包依赖，不能代替新的动态或头型适配视觉 Gate。原有可选 Rig 预览/LiveLink 缺失引用已记录，没有本轮新增的保存 Game 包缺失依赖。

男性发型穿模、新的固定头皮 Headshot 方案、正式 Scalp/Hairline 隐藏策略持久化、资产 ID 改名和打包运行时仍分别未实施或待验证，不作为本清理计划缺口。

## 结项与后继

受影响 Workflow Status、机器状态、里程碑和完成计划索引已登记本轮结果。后继为[下一阶段方案定义](../../plans/active/PLAN-2026-10-NEXT-STAGE-DEFINITION.md)，只整理既有事实并接收用户新目标；候选 Headshot、男性适配及正式隐藏策略不因本计划结项而获得执行范围。
