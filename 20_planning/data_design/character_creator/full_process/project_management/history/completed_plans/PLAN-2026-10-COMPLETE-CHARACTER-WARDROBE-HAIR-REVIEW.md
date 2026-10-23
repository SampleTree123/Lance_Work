# 完整男女角色服装、发型与身体动作审查界面

> 文档 ID：`PLAN-2026-10-COMPLETE-CHARACTER-WARDROBE-HAIR-REVIEW`
> 文档类型：`plan`
> 生命周期：`completed`
> 计划状态：`completed`
> 影响阶段：`WF-50`
> 完成条件：独立审查关卡及服装/发型/身体动作面板可操作，切换、跟随、静态复位、保存重载、源保护与必要检查通过；人工合身/穿模接受独立记录
> 最近核验：2026-10-05（R01–R04限定工具交付范围completed；342回归通过，人工视觉pending）

## 目标与执行边界

使用两个已导入完整男女角色及各自Skeleton、正式Registry、173套覆盖Look（女95/男78）、40款双版本发型，交付独立审查关卡和界面；保留Family/鞋规则、发型性别许可与禁用规则。用户追加授权旧BodyOnly动作，本轮只建立现用每性5条的独立v002预览片段，不复用两条退休动作、不改原动画或Skeleton、不加入面部或头发物理。

## 需求与落实

| 需求 ID | 要求 | 影响 Workflow | 状态 | 验收条件 | 证据入口 |
| --- | --- | --- | --- | --- | --- |
| R01 | 来源锁与原场景/源保护 | WF-50 | completed | 原地图、角色、Skeleton、旧动作和代表资源保持，保护范围明确 | entry_context.json、protected_sources_before.json、protected_sources_after.json：37项基线SHA未变；不是666网格全部哈希证明 |
| R02 | 独立关卡、完整人物与服装/发型跟随 | WF-50 | completed | 共同骨映射/层级检查，LeaderPose或额外骨CopyPose实际跟随；独立范围保存 | all_mesh_binding_audit.json：666网格（346衣物/320发型）；extra_bone_hair_checks.json：10款额外骨发型男女动作3；copy_pose_saved_reload_readback.json重装前读回 |
| R03 | 服装/发型/动作、视角和播放暂停界面 | WF-50 | completed | 代表切换无残留、禁发型生效、静态/动作可切、面板实际ready | switch_and_reload_checks.json：16项；playback_all_actions.json；static_pose_reset_check.json；panel_lifecycle.json与panel_state.json：PID16168、ready、首显1/1服装+hair2+action0/paused |
| R04 | 保存重载、运行采样、保护和文档后交付 | WF-50 | completed | 未重装先读保存绑定；动作真实变化/暂停/静态复位通过；基线保护、必要回归及独立审计齐备 | saved_reload_readback.json、copy_pose_saved_reload_readback.json；protected_sources_after.json；regression_pytest.xml：342 passed/0 skipped、89.956秒；documentation_audit_final.json：16独立子系统/跨层全通过，0错误/0警告 |

## 交付与证据所有者

关卡：`/Game/DataMake/Validation/CompleteCharacterWardrobeHair20261005/L_DM_CompleteCharacter_WardrobeHair_Review_v001`。用户面板入口及实现/恢复归[Runtime3.13](../../../technical/unreal/CHARACTER_RUNTIME.md#313-完整角色服装发型与身体动作审查界面2026-10-05)。Run Root为`%OUTPUT_ROOT%/unreal_character_import/complete_character_wardrobe_hair_review_20261005_v1/`，沿用`OUT-WF50-RUNTIME-ACCEPTANCE`，默认`unclassified`保护；交付摘要/操作说明为`review_delivery_summary.json`和`README.md`。正式源与旧验收不改写。

## 失败历史与范围限制

旧v1空骨轨副本保留不用；v002逐源帧局部骨姿势重建，数值误差按自身报告限定，仅预览，不是正式重定向/任意Skeleton兼容接受。旧严格全骨子集规则拒绝额外发饰骨，560/666、118失败记录保留于leader_only_partial_audit.json；后续新666检查通过。额外骨走独立CopyPose，共有身体骨跟随，额外骨保留参考姿势，不改原Skeleton、不加入头发物理。

旧全库检查曾因可编辑几何描述累积导致UE内存退出；用户处理恢复包窗口后恢复。修复为每批≤40、帧末排队GC，全检查完成无再次OOM；audit_memory_release.json仅请求卸载654个审计包释放内存，不保存/删除源。日志和失败回执保留。

旧服装与新Body参考姿势仍有差异；HB2_11花饰的源pelvis绑定问题未修正。共有头骨对齐、666结构检查及root所见preview_front.png不能代替人工合身、动态穿模或所有发饰的视觉接受。人工状态保持pending，不作为本轮工具交付的前置条件。静态动作0曾留旧实例，已清空动画资产并经十动作→静态前后骨一致检查通过，失败拍摄保留。

不包含CC/新导出/整库重导、面部、生产渲染、数据Batch、新身份共同Skeleton或全动作压力测试。计划归档后项目显式idle/current=null；等待用户使用界面审查及新的明确授权，不自动展开下一项。
