# 完整角色发色、配置保存与现成面部表演库

> 文档 ID：`PLAN-2026-10-CHARACTER-RUNTIME-FACE-LIBRARY`
> 文档类型：`plan`
> 生命周期：`completed`
> 计划状态：`completed`
> 影响阶段：`WF-50`
> 完成条件：固定十色进入完整男女槽位并随切换保持；整套配置保存/重开恢复通过并先同步文档；从本机现成表演筛出有依据的4–6项面部片段，男女代表与身体兼容，支持选择/关闭/保存恢复；完整角色审查入口完成技术交付，用户最终review另记pending。
> 最近核验：2026-10-08（R01–R05技术交付完成；用户最终视觉审查pending）

## 本轮工作

1. **完整角色也使用最终十色。**栗色（原色）、黑、蓝、粉、紫、红、绿（teal）、橙、金、银白已经符合用户理想，后续固定使用。换角色、发型、衣服或身体动作时保留所选颜色。
2. **整套配置能存、能恢复。**保存身份、服装、发型、发色和动作等当前组合，重开后检查实际绑定。完成这一段先同步文档，再推进后续集成。
3. **用现成表演建立小型面部库。**目标4–6种有区别的表情，可裁剪现成片段并调整强度、速度和衔接，不自创UE旧Happy/Sad/Angry曲线，不用相似片段凑数。若可用来源不足，报告实际候选和缺口。
4. **接入完整男女角色。**与代表身体动画共同检查，面部可选、可关闭，也能随整套配置保存恢复，最后交付可操作的审查入口。

## 需求与验收

| 需求 ID | 要求 | 影响 Workflow | 状态 | 验收条件 | 证据入口 |
| --- | --- | --- | --- | --- | --- |
| R01 | 固定十色进入完整男女槽位 | WF-50 | completed | 颜色来自已接受配置；代表identity/hair/outfit/action切换保留选择并实际读回；眼色保持原色、来源不覆盖 | Runtime3.18；runtime_validation/validation_progress.json，20步实际success |
| R02 | 整套配置保存、恢复及重开验证 | WF-50 | completed | 参数及资产来源可追溯，重开先检查实际场景再重组；无过期选择静默回退；完成后先同步Technical/Status/Plan | runtime_validation/complete_configuration.json、configuration_restored.json、reload_before_reassembly.json；文档检查点已同步 |
| R03 | 筛选4–6个本机现成面部表演片段 | WF-50 | completed | 来源、源区间、调整和区别有记录；不以手工旧情绪曲线代替，不凑数；数量不足如实记录，不能自报通过 | Animation §7；60组合/14,568帧通过；final_visual_review_v1.json为20代表140离散帧观察，用户评价仍待 |
| R04 | 面部与身体兼容，并纳入选择及保存恢复 | WF-50 | completed | 男女代表实际播放、关闭面部回中性及身体继续正确；头颈/眼牙/肤色无明显异常；面部选择及可调参数保存/重开恢复 | Animation §7、Runtime3.18；face_configuration_20261007T175232650907Z/validation_progress.json，24步包括关闭、配置恢复和重开前只读核验全部通过 |
| R05 | 完整角色review技术交付 | WF-50 | completed | 审查入口可用，源资产保护及必要检查通过，交付状态与用户最终审查分开；用户最终review pending，不代签 | technical_delivery_v1.json、panel_delivery_observation_v1.json；可见ready面板及none＋5项下拉已观察，未点击用户验收按钮 |

## 顺序与边界

先完成R01–R02并同步文档中间检查点；本机现成表演的只读调查可并行准备，随后完成R03–R05。UE/CC共享应用由root串行操作，子任务只做授权的离线工作。CC已由用户手动打开，可使用当前实例，不能自行启动CC。

此前发色改良计划保持完成历史，旧回执原字节保留。最终十色的新人工接受独立写入本Run，不修改旧pending字段以伪造过去的接受。男女发型名单、女性共享鞋/原赤脚许可保持；不扩展身体动作库、场景或服装材质改善。

## 所有者与证据

Run Root：`%OUTPUT_ROOT%/unreal_character_import/character_runtime_face_library_20261007_v1/`；总交付/完整角色配置由[Runtime3.18](../../../technical/unreal/CHARACTER_RUNTIME.md#318-完整角色发色配置与现成面部库)拥有，`face_library/`由[Animation §7](../../../technical/unreal/ANIMATION_EXPRESSION_MORPH.md#7-现成面部表演库与完整角色组合)拥有；若需要CC现成动作导出/UE导入，`transfer/`归[Motion Transfer §8](../../../technical/transfer/MOTION_TRANSFER.md#8-完整角色现成面部表演转移)。默认unclassified保护，依相应既有输出契约登记；R01–R05有界技术交付已完成；用户最终review仍pending。

本轮已接受输入为final_hair_palette_user_acceptance_v1.json，绑定此前最终十色能力表、v4参数及v5发型索引。R01–R02已通过20步实际验证并同步文档；恢复选定动作与播放状态，不恢复精确播放帧。现成面部片段已通过技术筛选；完整角色面部选择、关闭及保存恢复24步通过，可见面板已交付，最终用户视觉审查pending。

## 技术结项

2026-10-08 R01–R05按本计划的技术交付条件完成。5项表情来自现成表演，60组合/14,568帧源对照通过；root观察20代表/140张离散帧，不是连续视频或60项逐一人工验收。面板交付时PID7768、ready，控件及表情选项可见；此为交付快照，不保证之后窗口仍开启。用户下一步审查自然度、强度及情绪标签，未自动开启延期工作。

回归范围：686项全套为中间源码检查点；后续composer29、driver7、normalizer缓存6、contract16、playback2项针对检查通过，不宣称后续所有代码重新跑过686全套。最终文档检查见本Run的documentation_final_audit_v1.json；操作说明为REVIEW_GUIDE.md。
