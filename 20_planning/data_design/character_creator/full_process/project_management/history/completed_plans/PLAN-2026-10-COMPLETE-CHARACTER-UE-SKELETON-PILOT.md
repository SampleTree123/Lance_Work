# 完整男女角色UE导入与骨架标准试点

> 文档 ID：`PLAN-2026-10-COMPLETE-CHARACTER-UE-SKELETON-PILOT`
> 文档类型：`plan`
> 生命周期：`completed`
> 计划状态：`completed`
> 影响阶段：`WF-40/WF-50`
> 完成条件：各一个现有男女完整FBX独立导入，面部/材质/Morph/骨骼完整性检查；与既有发型参考及候选标准比较，复用各一个既有发型；依据代表证据确定骨架标准范围
> 最近核验：2026-10-05（历史男女完整FBX/自身骨架、现有发型静态与图形重载通过；323回归及归档独立审计v2实际通过）

## 目标与执行边界

使用已经存在的男女完整角色FBX及其JSON/纹理闭包，各一个代表导入独立UE目录，初次保留自身Skeleton，不先强行指派旧发型骨架。保留源含有的完整Morph、面部部件/骨骼、眼睛/眉毛/睫毛/牙齿口腔与材质；源不含的内容不能凭空宣称导入。具体来源及SHA在准备阶段锁定，不重新生成或导出新内容。

比较本次男女Skeleton与上一批对应发型参考Skeleton及候选标准：名字/层级、参考姿态/单位/变换与面部骨骼支持要有机器依据；复用男女各一个既有发型进行代表装配。若需修正，仅针对独立试点资产/适配设置，不覆盖正式参考或全库。根据证据说明可否使用统一或男女分开的标准、适用范围和遗留兼容限制，不能仅凭骨骼名称一致宣布兼容。

root统一操作共享UE；子agents只承担独立源/实现检查，禁止并发改同场景。沿用成熟导入/材质/固定头型模块，集中机器完整性和必要代表视觉/表情检查，不做全库重拍、逐角色繁琐验证或全表情矩阵。不重导整库服装/80发型、不建数据生产batch，不运行新的CC生成/导出。本计划与已完成CC创建/装配分开，不重开旧计划。

## 需求落实

| 需求 ID | 要求 | 影响 Workflow | 状态 | 验收条件 | 证据入口 |
| --- | --- | --- | --- | --- | --- |
| R01 | 锁定现有男女FBX及JSON/纹理来源与SHA | WF-40/WF-50 | completed | 男女各一个输入闭包，源/规范资产不覆盖，没有新导出 | complete_character_import_manifest_v1.json / source_rig_audit_v1.json；历史固定男女FBX来源/SHA保持，无新导出
| R02 | 完整导入并保留自身Skeleton/源Morph与面部材质部件 | WF-40/WF-50 | completed | 实际保存/重载可加载，源存在的Morph/组件/骨骼/材质有对应结果，精确遗漏明确失败或限制 | FIXED_HEAD_<SEX>_FULL/import_audit.json：各六部件/2,455源Morph、118骨/源SHA完整；normal_binding_audit_v1.json通过
| R03 | 比较Skeleton并确定可采用的骨架标准范围 | WF-40/WF-50 | completed | 层级/参考姿态/单位/面部支持与上次发型参考、候选标准明确；不以名称相同代替实测 | bone_standard_comparison_v2.json：男女各六部件118骨层级/参考局部T/Q/S精确0差；采用分性别自身候选，仅当前两源
| R04 | 各复用一个现有发型与必要集中代表检查 | WF-40/WF-50 | completed | 男女代表头发装配、面部/眼口/材质及必要表情响应正常或明确限制；只按实测接受 | runtime/static_assembly_report.json与runtime/render_editor_reload.json实际success；各HAIR_HB1_02静态兼容/保存图形重载，动作与新人工视觉明确未测
| R05 | 复现/恢复、必要测试与文档收口 | WF-40/WF-50 | completed | 保存来源/目标/配置/报告与恢复入口，必要回归和独立文档审计；明确非全池/batch | Transfer12/Runtime3.12复现/只读audit/恢复与来源回执已登记；regression_tests_final_v1.txt实际323passed/55.07s；documentation_audit_final_v2.json实际16独立+cross-layer全通过、0错误/0警告

## 实现与输出所有者

[Transfer12](../../../technical/transfer/CC_TO_UE_MODULAR_OUTFIT_PILOT.md#12-完整角色ue导入与骨架标准试点2026-10-05)主拥有本次导入/源清单、Skeleton比较及新实现入口，具体脚本及复现/恢复见该节；既有模块各自所有权不变。[Runtime3.12](../../../technical/unreal/CHARACTER_RUNTIME.md#312-完整男女角色骨架与代表发型装配试点2026-10-05)拥有代表场景、现有发型消费及运行时检查，不重复拥有导入/骨架比较代码。

Run Root `%OUTPUT_ROOT%/unreal_character_import/complete_character_skeleton_pilot_20261005_v1/`，导入/比较主输出归Transfer12与OUT-WF40-TRANSFER-BUNDLE（本轮消费既有FBX，不产生新CC导出），runtime/代表检查归Runtime3.12与OUT-WF50-RUNTIME-ACCEPTANCE；默认unclassified保护。源/失败日志、实际保存导入与候选骨架证据保留，不因试点结束删除正式资产或旧发型依赖。

## 停止与后续

遇到源闭包丢失、Morph/骨骼/面部材质遗漏、导入/保存失败或骨架不兼容，停在具体阶段保留证据，修独立试点/适配逻辑；不自动全库重导或升级生产标准。完成后按实际代表范围归档；无新授权时idle/current=null，批量或后续导出另行选择。

## 结项范围

本计划按既有男女参考FBX完整导入、源Morph/部件/材质/骨架机器完整性、旧参考精确对照与各一个发型静态复用/新图形编辑器保存重载的限定范围完成。男女独立Skeleton只是后续标准候选，不宣称新身份共享、男女共用、身体/表情动作或新人工视觉接受。没有启动batch、CC导出或全库重导；无后续授权时idle_after_completed_plan/current_plan_id=null。regression_tests_final_v1.txt实际323passed/55.07s；documentation_audit_final_v2.json实际16独立+cross-layer全通过、0错误/0警告，不借用历史通过。

## 结项后的限定人工确认

2026-10-05，用户在可见的新UE关卡检查后直接表示“目前看来一切正常，接下来我们的计划是什么”。`runtime/user_visual_acceptance.json`绑定原saved map/重载/静态及男女导入审计SHA，记录当前男女参考六部件和各HAIR_HB1_02静态可见外观通过。此后续事实不改写上述机器结项时未有人审的历史，也不推进身体/表情动作、新身份共享、隐藏表面或全库接受；仍idle/current=null，无新计划启动。
