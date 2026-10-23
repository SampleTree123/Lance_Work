# UE 角色运行时

> 文档 ID：`TECH-UE-01`
> 文档类型：`technical`
> 生命周期：`current`
> 适用阶段：`WF-40/WF-50`
> 实现所有权：UE 角色资产边界、Skeleton、Blueprint 和运行时能力
> 验证所有权：`VAL-UE-01`、`VAL-UE-02`
> 输出契约：`OUT-WF50-RUNTIME-ACCEPTANCE`
> 运行环境：Unreal Engine 5.8 Editor
> 最近核验：2026-10-20（双人快速审查启动隔离及场景继续迭代入口）

## 1. 目录与所有权

2026-10-19当前接入任务：使用用户修改后CFD40_AF_001/CFD40_AM_001的新版本导入，接正式槽位并制作仅两人的场景点位审查面板。本轮是完整内容版场景点位审查面板，仅人物菜单限定为最新两人；保留换装、发型切换、标准十色、表情、动作、镜头、主场景选择和点位保存，不是仅头发审查面板。精确来源、八件网格及共享Skeleton见[当前导入交接](../../../../../../00_engine/outputs/character_refresh_20261018_v1/CURRENT_IMPORT_HANDOFF_20261019.md)，转移/睫毛适配所有权见[新版候选转移](../transfer/CFD40_REFRESH_CANDIDATE_TRANSFER_20261018.md)。六主体件之外的两片附属睫毛必须随身体姿态、Morph和显隐共同处理。当前两人完整面板接入及限定代表检查已完成，依据见§3.22；全组合、全帧面部和精细近景质量待用户。§3.21及20261018代表回执属于各自旧版本，不自动覆盖本版；现用衣柜/发型继续复用。2026-10-20独立夜间40人导入已完成，面板仍仅接两人，另38人未接入；本轮场景继续迭代见[场景Technical §22.8](./SCENE_CAMERA_SEQUENCE.md#228-已审查点位继续迭代2026-10-20)。

```text
/Game/Vendor/Reallusion/CC5/FirstDataBatch/Looks/<LOOK_ID>  # 外部导入
/Game/DataMake/Characters/...                               # 自有 Wrapper/Blueprint
/Game/DataMake/Animations/CC5/FirstDataBatch/...            # 派生动作/表情
/Game/DataMake/Sequences/FirstBatch/...                     # 生产 Sequence
```

第一批 Look、同性 Skeleton 和平均体型 BASE 是保留输入。经独立清单与依赖闭包审查后，可通过 UE API 复制和重映射被替代的导入资产；不通过磁盘移动 uasset 整理目录。DataMake 资产可以版本化重建，但不得覆盖仍被权威节点引用的版本。现用目录与执行入口见第 3.8 节。

## 2. 第一批输入与 FullReference 契约

- 32 个 Look：女性 16、男性 16；每个 Look 已烘焙身份、平均 BodyFit、服装和外观。
- 同性 Look 共享已冻结的同性 Skeleton；男女 Skeleton 不混用。
- 第一批不提供 UE 内单件服装自由替换；身份和服装编辑通过切换完整 Look 实现。
- 每个生产 Look 必须能播放同性 5 个动作和 Happy Composite。

角色资产真值由 `first_batch_required_exports_20260824_v3.json` 与 `first_batch_graph_source_20260824_v1.json` 共同冻结。

正式运行时审计入口：

| 入口 | 作用 |
| --- | --- |
| `run_first_batch_day2_final_gate.py` | 编排表情库、Composite、动态预览和角色运行时总 Gate |
| `ue_validate_first_batch_day2_runtime.py` | 在 UE 内检查 Look、Skeleton、动作、表情、材质和 T-pose |
| `ue_patch_first_batch_head_wrinkle_textures.py` | 审计/备份/修复/恢复头部动态皱纹纹理绑定；默认只审计 |

## 3. 模块化服装 Pilot

### 3.1 历史 Pilot 架构与验收范围

旧 `/Game/DataMake/Characters/M02_Average/BP_DM_M02_ModularPilot_v002` 只证明了方向。2026-08-29 的 v001 Pilot 曾通过“每个候选网格一个隐藏组件”完成男女平均体型限定范围验收；其运行 Blueprint 和 Review Level 已在 v002 验收后删除，分类基线、转移实现和验收证据继续保留供追溯。

```text
%OUTPUT_ROOT%/unreal_character_import/modular_outfit_pilot_20260829_v1/runtime/
```

v002 在保留同一个 `Body`、Skeleton、Leader Pose 和碰撞边界的前提下，已建立固定槽位候选框架：

```text
/Game/DataMake/Characters/ModularOutfitPilot/M02_Average/BP_DM_M02_Average_ModularOutfitPilot_v002
/Game/DataMake/Characters/ModularOutfitPilot/F02_Average/BP_DM_F02_Average_ModularOutfitPilot_v002
```

每个 v002 Blueprint 只固定创建 5 个语义槽和 10 个空的可复用 Bundle 槽：

| UE 组件 | 接受的服装语义 |
| --- | --- |
| `UpperInner` | `shirts` |
| `UpperOuter` | `coats` |
| `Bottom` | `pants` 或 `skirts`，同一 Variant 互斥 |
| `FullBody` | `full_body`，与上下装互斥 |
| `Footwear` | `shoes` |
| `BundlePart01..10` | 局部配件、同语义多网格和不可拆分 Bundle 的额外部件 |

这些服装组件在 Blueprint 模板中都不保存候选 Skeletal Mesh。应用 Variant 时先加载并验证完整目标的网格路径与 Skeleton，验证成功后清空全部槽位，再通过 `SetSkeletalMesh` 赋给固定槽或 Bundle 槽。未使用槽必须恢复为空网格、隐藏且无碰撞。Bundle 槽是有界的空预分配池，不对应某件具体服装，因此完整衣柜扩展不会继续增加 Actor 组件数量。

v001 优先保证确定性和验证简单性，但 40 个候选网格都成为 Blueprint 硬引用，不是完整衣柜的最终加载架构。v002 已消除该候选硬引用与组件数随衣柜增长的问题；当前候选路径仍由 Editor 侧 JSON Runtime Plan 提供。打包运行前还需要把同一契约迁移到可 Cook 的 Primary Data Asset/软引用注册表，并验证异步加载和卸载，不能把 Editor Python Plan 直接当作最终打包接口。

历史 v002 只覆盖 `M02_Average/F02_Average`、20 个冻结 Runtime Variant 和当前代表服装结构，其机器与人工动态 Gate 均已通过。它不进入第一批 32-Look 生产图，也不代表全部服装库或打包后的通用生产衣柜。

### 3.2 历史实现与退休执行入口

以下为旧 14-Case/v002 和单发型探针的实现追溯，不是现用重建流程。转移见 [模块化服装 Transfer](../transfer/CC_TO_UE_MODULAR_OUTFIT_PILOT.md)。现用执行从第 3.5–3.8 节进入；旧 P0、单发型 ScalpHairPilot、v001 和资产对照/几何探针入口已退休，禁止通过旧命令重新生成。

| 文件 | 责任 |
| --- | --- |
| `00_engine/scripts/unreal/modular_outfit_runtime_plan_v1.py` | 从 14-Case Manifest 和 12 个 Split 报告生成已验证的候选网格/Variant 分类基线 |
| `00_engine/scripts/unreal/modular_outfit_runtime_plan_v2.py` | 把 v001 分类基线编译为 5 个语义槽、10 个 Bundle 槽和逐 Variant 网格赋值计划 |
| `00_engine/scripts/unreal/run_modular_outfit_runtime_v2.py` | 编排 v002 的 `plan/build/validate/stage/cleanup/review-level` |
| `00_engine/scripts/unreal/ue_build_modular_outfit_runtime_v2.py` | 构建无候选硬引用 Blueprint、原子换装、空槽清理和有序切换检查 |
| `00_engine/scripts/unreal/ue_modular_outfit_motion_validation_v1.py` | 导入同性动作并检查 Skeleton、核心骨轨与采样姿态变化 |
| `00_engine/scripts/unreal/ue_build_modular_outfit_review_level_v2.py` | 创建 v002 独立人工视觉复核关卡 |
| `00_engine/scripts/unreal/ue_build_scalp_hair_review_level_v1.py` | 创建 hb1-01 头发视觉探针关卡；将头发作为独立 SkeletalMeshActor 挂到男女角色，不改变服装 Blueprint |
| `00_engine/scripts/unreal/ue_repair_scalp_hair_materials_v1.py` | 重新导入发型材质/纹理，并将导入材质同步到运行时发型网格 |
| `00_engine/scripts/unreal/ue_build_scalp_hair_material_instances_v1.py` | 使用 `RL_Hair_Specular` Masked 材质和透明度纹理重建运行时头发材质实例 |
| `00_engine/scripts/unreal/ue_repair_scalp_hair_review_alignment_v1.py` | 将视觉审查关卡中的头发临时放入已有 BundlePart 实例槽，保证 Body Leader Pose 在保存重载后持续有效 |
| `00_engine/scripts/unreal/ue_disable_scalp_hair_shadows_v2.py` | 在审查关卡实例中关闭发型网格阴影投射，用于脸部颗粒状阴影对照，不修改正式 Blueprint |
| `00_engine/scripts/unreal/ue_write_scalp_hair_shadow_probe_report_v1.py` | 写入头发阴影对照的可追溯报告 |
| `00_engine/scripts/unreal/ue_hide_scalp_hair_probe_v1.py` | 在审查关卡实例中整体隐藏头发网格，用于排查脸部纹理是否由头发几何或材质直接造成 |
| `00_engine/scripts/unreal/ue_write_scalp_hair_visibility_probe_report_v1.py` | 写入头发整体隐藏对照的可追溯报告 |
| `00_engine/scripts/unreal/ue_scalp_hair_batch_import_v1.py` | 将 F02 Average 的 40 个已验证发型 FBX 批量导入 UE，复用 F02 Skeleton 与 Interchange Split Pipeline，并生成批量导入报告 |

`ue_build_modular_outfit_runtime_v2.py` 与 `ue_build_modular_outfit_review_level_v2.py` 仍被当前 v003/审查导入为共享实现；仅旧独立 `main` 被禁止，不可删掉整个模块。旧 `run_modular_outfit_runtime_v2.py` 的 14-Case 重建流程不再使用，分类 JSON 与人工/机器结果作为 `retained_evidence` 保留。第一批表情合成只使用 canonical 分支，旧 P0 分支禁止执行。

### 3.3 历史机器结果（保留证据）

v002 Runtime Plan：`%OUTPUT_ROOT%/unreal_character_import/modular_outfit_pilot_20260829_v1/runtime_plan_v2.json`。

- v002 两个 Blueprint 均已编译并保存；每个 Actor 固定为 15 个空服装槽加一个 `Body`，男/女候选注册表分别含 23/17 个网格，但 Blueprint 模板候选硬引用计数均为 0。
- 男女各 10 个 Variant，分别完成 100 个有序切换；200/200 切换保持同一 Actor、Body 和 15 个槽位组件身份，错误为 0，禁用槽残留网格为 0。
- 当时最复杂 Variant 同时启用 6 个网格并使用 4 个 Bundle 槽；仍低于 10 个 Bundle 槽的上限。
- 已保存 v002 复核关卡：`/Game/DataMake/Validation/ModularOutfitPilot/L_DM_ModularOutfitPilot_Review_v002`，其中男女代表叠穿均通过脚本装配并播放既有同性验证动作。
- v001 同性动作证据仍有效：动作严格绑定基础 Skeleton，并保留 71 条核心骨轨；0.75 秒采样最大旋转变化分别为 25.051 度和 22.616 度。
- 2026-09-02 人工动态复核覆盖多层开关、Full-body、普通分件、锁定 6 组件 Bundle 和集成单网格结构；所有组件均随同一 Body 正常运动，未出现停留、脱落、漏显示或错误材质。人工证据为 `%OUTPUT_ROOT%/unreal_character_import/modular_outfit_pilot_20260829_v1/runtime/manual_visual_review_20260902_v1.json`。
- v002 对应人工复核逐组覆盖分层服装、Full-body 加局部配件、男女锁定 6 组件 Bundle、男女集成单网格，以及男性分层/女性锁定 Bundle 的完整动作循环；结果通过。证据为 `%OUTPUT_ROOT%/unreal_character_import/modular_outfit_pilot_20260829_v1/runtime_v2/manual_visual_review_20260902_v2.json`。
- 复核中发现部分贴身/分层服装存在可接受的轻微穿模。该风险归属服装适配、身体隐藏面或布料处理，不否定本轮组件拓扑、切换和 Leader Pose 架构。
- 当时已生成独立头发视觉探针关卡：`/Game/DataMake/Validation/ScalpHairPilot/L_DM_ScalpHairPilot_Review_v001`。`hb1-01` 的四个运行时网格在 F02 使用同一基础 Skeleton 的 Leader Pose，在 M02 以跨骨架 Leader Pose 进行可见性探针；用户已确认头发放置、显示和跟随正常，单个 Pilot 的导出—导入—运行时挂载链路通过。该结果不构成 40 个候选批量生产、头发正式槽位或服装兼容 Gate 的通过。证据为 `%OUTPUT_ROOT%/unreal_character_import/scalp_hair_pilot_20260923_111307_interchange/hair_visual_review_level_v001.json`。
- 头发视觉探针最初显示为块状发片，原因是服装 Interchange 管线默认关闭材质/纹理导入，且自动 FBX Phong 材质为不透明混合。现已重新导入纹理并改用项目已有的 `RL_Hair_Specular` Masked 材质实例；修复证据为 `%OUTPUT_ROOT%/unreal_character_import/scalp_hair_pilot_20260923_111307_interchange/hair_material_repair_v1.json` 和 `hair_masked_materials_v1.json`。这只关闭了导入显示问题，颜色、发丝细节和服装组合仍待人工确认。
- 首版视觉关卡的独立头发 Actor 在重载后会丢失跨 Actor Leader Pose，造成身体动作与头发错位。当时审查实例已将 `hb1-01` 四个网格放入现有 `BundlePart01..04`，重载后四个组件仍保持 `leader_is_body=true`；这只是 Review Level 实例修复，不代表正式 Blueprint 增加 Hair 槽位。证据为 `%OUTPUT_ROOT%/unreal_character_import/scalp_hair_pilot_20260923_111307_interchange/hair_visual_review_alignment_repair_v1.json`。
- 用户观察到脸部出现类似发丝的颗粒纹理。当时审查实例中已对 M02/F02 的四个头发组件关闭 `cast_shadow` 并保存重载，用于验证是否为 Masked 发片动态阴影造成的伪纹理；网格、材质、透明度和 Leader Pose 未改变。证据为 `%OUTPUT_ROOT%/unreal_character_import/scalp_hair_pilot_20260923_111307_interchange/hair_shadow_artifact_probe_v1.json`，该设置未确认为正式策略；用户随后观察整体隐藏头发后脸部纹理仍在，按要求暂时忽略。此历史脸部现象与 3.7.3–3.7.6 的覆盖层规则网格是两个问题。
- 关闭阴影后继续进行整体隐藏对照：M02/F02 的四个头发网格均设为不可见，身体、服装、灯光和相机未变，并保存重载。证据为 `%OUTPUT_ROOT%/unreal_character_import/scalp_hair_pilot_20260923_111307_interchange/hair_visibility_probe_v1.json`；用户确认前不对脸部纹理根因下最终结论。

### 3.4 Gate 边界

`VAL-UE-02` 的 `modular_outfit_runtime_v002_20260902` 作用域已于 2026-09-02 通过。v001 的两个运行 Blueprint 和 Review Level 已按引用审计结果删除；清理证据为 `%OUTPUT_ROOT%/unreal_character_import/modular_outfit_pilot_20260829_v1/runtime_v2/v001_execution_asset_cleanup_20260902.json`。v001 分类 Plan、导入/动作脚本和人工证据仍是 v002 的可追溯依赖，不属于可删除的重复运行资产。

当时结论只涉及冻结范围内的组件拓扑、同 Actor/Body Variant 切换、Leader Pose 动作同步和代表结构。以下项目没有被该结论覆盖：

- 身体隐藏面或材质 Mask；
- Chaos Cloth、服装碰撞和复杂布料；
- LOD 同步；
- 发型、兜帽和头部服装兼容；
- 头发不是 v002 的正式服装槽位；当时视觉探针使用独立 SkeletalMeshActor，尚未纳入服装 Blueprint 的换装契约；
- 在 UE 中改变 Body Morph 后的服装视觉传播；
- 所有体型和全部服装库。

任何组件、Skeleton、Leader Pose、切换逻辑或声明范围变化都会使该作用域失效并要求重验。历史通过结果不能自动晋升为通用生产换装能力。现用 v003 已包含独立 HairPart 槽，最新限定能力见第 3.6 节；本节的旧头发探针、v002 蓝图与审查关卡已退出执行入口，清理总验收另见第 3.8 节。

### 3.5 全库网格覆盖审查

在全库转移完成后、穷举兼容性或生产接入之前使用。当前用户要求是每个已导入服装网格至少出现在一个合法完整穿搭里，不保证所有组合都正常。仅使用冻结男女平均体型，不调用或重启CC。

实现文件位于 `00_engine/scripts/unreal/`：

| 文件 | 职责 |
| --- | --- |
| `build_wardrobe_coverage_review_v1.py` | 从冻结Family、资产绑定、成功转移报告生成非穷举覆盖；保留锁定整体、必选配件、鞋池和互斥组 |
| `build_wardrobe_review_plan_v1.py` | 共用规则校验及v002槽位编译；新增显式`allow_multiple=True`，默认仍保持旧两套检查边界 |
| `run_wardrobe_coverage_review_v1.py` | 单页展示、单批装配检查、保存重载、汇总与人工翻页面板；不是后台监控 |
| `ue_wardrobe_coverage_review_v1.py` | UE内按当前 Plan 复用 v003 蓝图，核对Skeleton、Leader Pose、空槽、材质存在及动作引用，仅修改自有审查Actor |
| `tests/test_build_wardrobe_coverage_review_v1.py` | 验证非穷举覆盖、孤立资产拒绝、锁定整体、共享鞋池及失效证据拒绝 |

在 `%LANCE_ROOT%` 执行。现用 Plan 已晋升到 `current_reviews_20261001_v1/wardrobe_coverage/`，保留原搭配和 15 个服装槽，只把男女 Blueprint 改为 v003。旧生成器仍是规则编译辅助，但不得从旧 Pilot 模板重新生成现用入口；新增输入应另建版本并明确使用 v003 元数据。当前命令为：

```powershell
$run = '00_engine/outputs/unreal_character_import/current_reviews_20261001_v1/wardrobe_coverage'
python 00_engine/scripts/unreal/run_wardrobe_coverage_review_v1.py --plan "$run/review_plan.json" --action audit --start 1 --count 20
python 00_engine/scripts/unreal/run_wardrobe_coverage_review_v1.py --plan "$run/review_plan.json" --action summarize
python 00_engine/scripts/unreal/run_wardrobe_coverage_review_v1.py --plan "$run/review_plan.json" --action show --page 1
python 00_engine/scripts/unreal/run_wardrobe_coverage_review_v1.py --plan "$run/review_plan.json" --action reload --page 1
python 00_engine/scripts/unreal/run_wardrobe_coverage_review_v1.py --plan "$run/review_plan.json" --action panel
```

`audit`每次只检查指定区间，1-20之后显式执行`--start 21 --count 20`，最后按剩余数量执行。每批核验后再继续。`summarize`校验Plan哈希、重复与缺失行，并从实际组件网格反算覆盖，不能把计划覆盖当成执行覆盖。

面板按Family排列，每页最多两套，共用一个关卡`/Game/DataMake/Validation/Wardrobe/Average/L_DM_WardrobeAverage_Coverage`。选页面点`Load selected`，或直接点`Previous/Next`切换；在UE观察正面、侧面、背面及动作。Actor标签带编号，面板列出源资产路径。选择搭配编号后点`Accept selected outfit`或`Record issue`记录人工意见，问题必须有备注；未加载的页面不能记为通过。关闭面板不关闭UE或操作CC。

默认正面并暂停在动作首帧；面板`Front/Side/Back`原地旋转两个审查Actor，`Animate`切换播放。每次加载新页恢复默认正面/暂停。视口位置为`(350,0,105)`、Yaw180，角色正面Yaw为-90；仅调整审查Actor，不修改服装源数据。当前Windows快捷入口为Run Root下的`open_review.cmd`，仅启动同一面板。`panel_check.png`及`stage_*.png`是界面/构图诊断截图，不是全库验收媒体；缩小或隐藏的UE视口可能延迟截图，不能以已请求截图代替文件及像素核验。

播放修复（2026-09-12）：仅写`AnimationData`不保证已有`AnimSingleNodeInstance`绑定动作或循环；新建审查Actor曾出现引用存在但实例资产为`None`。现在`set_body_playback`显式调用`play_animation(motion, True)`、复位时间/速率、同步保存数据及播放状态，并核对实际实例。另外UE的`bThrottleCPUWhenNotForeground`会在外部面板取得焦点时覆盖视口实时更新，造成播放标记为真但时间不推进。播放时临时关闭该后台节流，暂停、翻页或正常关闭面板时恢复原值；不写持久配置，不重启UE/CC。若强制结束面板，执行同一脚本`--action stop`恢复；也可在UE编辑器偏好设置中恢复后台CPU节流选项。

更新预览代码后，当前页执行有限的实际播放检查（不是后台监控），等待发生在外部Python进程，不阻塞UE游戏线程：

```powershell
python 00_engine/scripts/unreal/run_wardrobe_coverage_review_v1.py --plan "$run/review_plan.json" --action verify-playback --playing
```

此命令读取当前已加载页，播放采样3次、暂停采样2次，再恢复命令指定的播放状态（`--playing`表示最后继续播放）。逐Actor核对时间推进、Body实际骨位置变化、已装配Follower的Leader及共有骨位置一致、暂停后不再运动。失败返回非零状态。`stage/playback_page_NNN.json`保存采样和错误，`stage/playback_sample.json`只保留最新瞬时采样；前者是当前页预览回归证据，后者不能证明持续运动。它们均属于本Run Root的运行时验证证据，不是训练视频。`assembly/checks_*.json`此前只检查装配/引用，不应解释为全库动作测试通过；实际穿模及材质外观仍需人工审查。

输出归属`OUT-WF50-RUNTIME-ACCEPTANCE`。现用 Run Root 是 `%OUTPUT_ROOT%/unreal_character_import/current_reviews_20261001_v1/wardrobe_coverage/`（上述 `$run`）；历史根 `%OUTPUT_ROOT%/unreal_character_import/wardrobe_average_20260906_v1/coverage_review_20260912_v1/` 保留原始人工/机器证据，两者均不是训练数据包：

| 文件/目录 | 内容、用途与下游 |
| --- | --- |
| `review_plan.json` | 输入哈希、合法穿搭、v002赋值、页序与逐网格见证，供UE执行 |
| `coverage_index.json` | 源资产名称/路径、搭配编号和页面，供定位问题资产 |
| `assembly/checks_*.json` | 实际组件、网格、材质、动作引用及错误，供汇总 |
| `assembly_summary.json` | 实际检查覆盖与失败/缺失清单，供Status引用，视觉状态独立 |
| `stage/page_*.json`、`stage/reload_*.json` | 展示与保存重载核对，不代表人工接受 |
| `current_page.json` | 最后实际加载的页码与关卡，供面板恢复位置 |
| `manual_review.json` | 操作者按编号记录接受/问题、备注、时间、Plan哈希；未记录前不存在 |

上述工单与证据保留，不随普通临时截图清理。验证是`VAL-UE-02`新增子范围：规划覆盖、机器绑定、人工视觉分别统计。材质非空不证明Shader正确；内层被外套遮住时不代表其表面已看清，需要时另补局部检查，不能擅改Family规则。Boots03鞋舌父材质及此前网格着色observations继续有效。全组合、全动作压力、头发兼容和生产发布不由本轮机器通过推定。

恢复：UE未发现时确认项目已启动；有未保存的其他关卡时先保存再切换。Plan输入变化使用新Run Root重建，旧人工决定不可复用。审查只重用自有关卡，不改 Vendor 材质/网格或 v003 Blueprint 默认值。旧 Pilot 关卡不再是恢复入口。机器检查为瞬时绑定检查，代表页面保存重载与人工动态检查另有证据。

### 3.6 正式索引直接读取与 v003 换装（2026-09-29）

本地第二批平均体型的 UE 单文件衣柜索引是 `00_engine/assets/character_creator/wardrobe_registry_ue_v4_full_20260929.json`。其 Family 资产直接给出 `slot`、`ue_case_root` 和精确 `ue_mesh_paths`；共享鞋给出 `ue_asset_paths`，发型给出网格路径及 `sex=male/female/both`。`formal_wardrobe_registry_v1.py` 每次选择都直接核验并读取该索引，按合法 Family 组装、鞋池和发型禁用规则产出组件赋值。它不以旧源 Registry、迁移计划或审查 Plan 作运行时选择。映射生成和 506 网格闭包见[转移第 11.3 节](../transfer/CC_TO_UE_MODULAR_OUTFIT_PILOT.md#113-精确网格映射与正式索引直接读取2026-09-29)。

当前实现文件位于 `00_engine/scripts/unreal/`：

| 文件 | 当前职责 |
| --- | --- |
| `formal_wardrobe_registry_v1.py` | 纯 Python 正式索引校验、合法搭配解析、精确组件赋值和发型性别/禁用判定 |
| `build_reviewed_wardrobe_pool_registry_v1.py` | 发布2026-10-06用户确认筛选版，重建精确差量、校验历史witness及许可，生成不可变发布证明和旧源保护证据；不修改UE资产 |
| `build_reviewed_wardrobe_pool_registry_v2.py` | 在冻结v1链上仅退出male.lift_haul，保留女性共享同名鞋与其余许可，发布不可变v2及人工反馈、合法映射和旧源保护；不修改UE资产 |
| `run_formal_wardrobe_registry_v1.py` | `inspect`、173 套旧审查装配对等校验，以及 UE 的 `build/stage/verify/cleanup` 命令入口 |
| `ue_formal_wardrobe_runtime_v1.py` | UE 中构建与应用 v003 平均体型蓝图；每次调用重读正式索引、预加载完整选择、清空并重用槽位 |
| `ue_build_modular_outfit_runtime_v2.py` | v003 复用其 Body/Leader Pose、Blueprint 组件构建和服装切换核心；添加组件后先编译 Blueprint 再寻找新组件 Getter |

两套已保存蓝图为 `/Game/DataMake/Characters/CharacterFactoryRuntime/M02_Average/BP_DM_M02_Average_CharacterFactory_v003` 与 `/Game/DataMake/Characters/CharacterFactoryRuntime/F02_Average/BP_DM_F02_Average_CharacterFactory_v003`。每个蓝图有 5 个语义服装槽、10 个 `BundlePart`、17 个 `HairPart`，共 32 个空复用槽，Body 使用既有 M02/F02 Average 网格；组件跟随 Body Leader Pose，候选服装/发型无 Blueprint 硬引用。发型仍来自 F02 导出和 F02 Skeleton；男性角色上的跨骨架使用目前仅验证运行时加载、跟随绑定及代表组合，不替代逐发型视觉适配。

从 `%LANCE_ROOT%` 运行；`build` 与 `stage` 需要已打开并完成 Python Remote Execution 初始化的完整 UE Editor，`verify` 默认启动全新 `UnrealEditor-Cmd.exe`，`cleanup` 清理脚本自身创建的展示 Actor。`stage` 会重用当前关卡中的同名 Actor，切换时清空未选服装和全部旧头发；它是编辑器验证入口，不负责保存关卡，也不是打包游戏的读取接口。

```powershell
python 00_engine/scripts/unreal/run_formal_wardrobe_registry_v1.py --phase inspect --family-id female.pretty_dresses
python 00_engine/scripts/unreal/run_formal_wardrobe_registry_v1.py --phase parity
python 00_engine/scripts/unreal/run_formal_wardrobe_registry_v1.py --phase build --transport remote
python 00_engine/scripts/unreal/run_formal_wardrobe_registry_v1.py --phase stage --transport remote --bodyfit-id F02_Average --family-id female.pretty_dresses --group-id pants --asset-id female.pretty_dresses.asset.5b02ba4e3a1b --asset-id female.pretty_dresses.asset.6377ee58f8bf --asset-id female.pretty_dresses.asset.190b0f408611 --hair-id HAIR_HB1_01
python 00_engine/scripts/unreal/run_formal_wardrobe_registry_v1.py --phase verify --bodyfit-id F02_Average --family-id female.pretty_dresses --group-id pants --asset-id female.pretty_dresses.asset.5b02ba4e3a1b --asset-id female.pretty_dresses.asset.6377ee58f8bf --asset-id female.pretty_dresses.asset.190b0f408611 --hair-id HAIR_HB1_01
python 00_engine/scripts/unreal/run_formal_wardrobe_registry_v1.py --phase cleanup --transport remote
```

证据根为 `%OUTPUT_ROOT%/unreal_character_import/formal_registry_runtime_v1/`，由本节作为 `OUT-WF50-RUNTIME-ACCEPTANCE` 的运行时验证输出负责：`reviewed_173_parity.json` 保存全部旧装配的路径/槽位逐项对等结果；`*_build_*.json` 保存新蓝图结构；`*_stage_*.json` 保存同 Actor 切换；`*_verify_*.json` 与 `*_verify_cmd.log` 保存独立进程重载与实际组件应用。2026-09-29 已通过 173/173 旧搭配对等、男女 v003 蓝图各 32 个空槽及新进程重载；实际 UE 切换样本包含女装允许发型→`WarriorCloak` 禁发型→Elise 锁定 Bundle/共享鞋/允许发型，以及男性 `dash` 发型与 `redsoul` 禁发型。成功证据为 `F02_Average_verify_2026-09-29T083054.196069_0000.json`、`M02_Average_verify_2026-09-29T083218.492785_0000.json` 等同根报告。所有展示 Actor 已清理，未保存临时关卡。

这是编辑器运行时与固定平均体型样本的机器验证；具体身份的头型/发型视觉适配、全部动作下的穿模、打包后数据加载、后续胡须接口均未因此通过。第一批 FullReference 保持不变。2026-10-01 现用 Coverage 与 Compatibility 两关卡中的旧角色已迁到 v003，保存重载通过；旧 v002 角色和历史审查关卡不再作为执行入口。

### 3.7 平均体型发型六视审查与发片材质修复（2026-09-29）

本轮按用户限定只检查发型本身：40 个保留发型按正式索引的 `male/female/both` 分类，在 F02/M02 平均体型上形成 51 个发型×性别 Case（女 30、男 21），每个 Case 拍摄正面、前左、左侧、背面、右侧、前右六视。保存的审查关卡为 `/Game/DataMake/Validation/ScalpHairFit/L_DM_ScalpHairFit_Review_v001`。从 `%LANCE_ROOT%` 运行：

```powershell
python 00_engine/scripts/unreal/build_hair_sex_fit_review_v1.py
python 00_engine/scripts/unreal/run_hair_sex_fit_review_v1.py --action build
python 00_engine/scripts/unreal/run_hair_sex_fit_review_v1.py --action show --index 1
python 00_engine/scripts/unreal/run_hair_sex_fit_review_v1.py --action view --view back
python 00_engine/scripts/unreal/run_hair_sex_fit_review_v1.py --action capture --start 1 --count 15 --timeout-seconds 900
python 00_engine/scripts/unreal/run_hair_sex_fit_review_v1.py --action normalize
python 00_engine/scripts/unreal/build_hair_sex_fit_gallery_v1.py
```

`build`、`show`、`view`、`capture` 需要已运行且 Remote Execution 可用的完整 UE Editor。照片证据根为 `%OUTPUT_ROOT%/unreal_character_import/hair_sex_fit_review_20260929_v1/`，归 `OUT-WF50-RUNTIME-ACCEPTANCE`：`review_plan.json` 冻结 Case、蓝图和视角，`gallery.html` 按性别逐项展示六视并链接 CC 原六视图；若本地 HTML 在应用内预览为空白，使用 `gallery_markdown.md` 进入每款发型独立的六视 Markdown 页面。`captures/` 保存 306 张现行照片，`captures_legacy_phong/` 保留修复前对照，`assistant_visual_screen.json` 记录助手观察而非用户验收。仅索引中的材质元数据变化时可刷新 Plan 的源 Registry 哈希；Case 内容或顺序变化必须另建版本。

首次全库拍摄发现 40 款发型的 271 个材质槽仍使用 FBX Legacy Phong。修复计划 `masked_repair_plan.json` 对其中 220 个具有发丝/头皮用途的槽建立 `RL_Hair_Specular` Masked 实例并写回原 Skeletal Mesh；51 个发饰、实体辫子或其他槽保持原状，旧材质资产未删除。运行入口 `build_hair_masked_repair_plan_v1.py`、`run_hair_masked_repair_v1.py`、`ue_repair_hair_masked_materials_v1.py`。40 款逐项报告、全新 UE 进程重新加载报告 `masked_repair_fresh_load_verification.json` 均通过：220/220 修复槽、51/51 未变槽、无未保存内容包。正式单文件索引的 `hair_assets[].meshes[].materials` 已同步实际材质路径；生成脚本以修复计划的网格/槽位逐项校验，未列出的槽保留原材质。

修复后 51 个 Case 的 306 张照片完整，但**视觉验收尚未关闭**：助手观察到部分 HB1 中性发型在 M02 头顶或后脑露出大片头皮，`HB1-11/13` 的剃发区在男女头型上呈局部棕色斑块，`HB1-18` 左右辫子颜色不一致，部分 HB2 实体辫子或花饰颜色与 CC 原图不符。具体编号和照片见 `assistant_visual_screen.json`。灰色身体和高对比审查灯光造成颗粒与银白高光，不能凭此确认最终颜色。当前没有自动剔除发型、修改 `male/female/both` 分类，也没有开展逐身份头型或服装交叉审查；后续需先处理可复现的材质/适配问题并由用户作视觉决定。

2026-09-30 用户指出照片在普通查看器中全部为黑色。解码核查确认现行 306 张 PNG 的 RGB 画面存在，但 Alpha 全为 0；此前只核验文件头与尺寸的 `gallery_validation.json` 未覆盖可见性。`run_hair_sex_fit_review_v1.py --action normalize` 已把整批照片无损转为 8-bit RGB PNG，逐张比较确认颜色像素不变，原始文件保留在同根 `captures_raw_zero_alpha/`；修复清单与前后哈希见 `capture_visibility_normalization.json`。此命令不需要 UE；后续 `capture` 完成后自动执行同一处理，宿主 Python 需要 Pillow。页面生成器现解码检查尺寸、非零透明度和非黑 RGB，并按文件哈希刷新图片引用，306 张全部通过。照片可读性恢复只关闭输出故障，用户发型视觉验收仍待完成。

2026-09-30 用户查看照片后报告：女性暂未发现明显穿模，男性存在穿模，部分发型仍粗糙并显露发片。用户原话、截图与助手定位保存在同根 `manual_review_20260930.json` 和 `user_evidence/HB1_09_hair_card_artifact_20260930.png`；该截图对应女性 Case 004、`HAIR_HB1_09` 左侧图。这属于问题反馈，尚未给出逐款最终验收或排除名单。

实现复核确认当前网格全部导出自 F02，审查脚本对男性也要求 F02 Skeleton 并直接使用 M02 Body Leader Pose；这能证明组件挂载，不能证明参考头型与骨骼变形适配。男性失败可能来自 F02 烘焙形状或跨 Skeleton 变形，需用同性导出对照隔离。材质修复只从同一模板复制并覆写 `Base Color Map` 与 `Opacity Map`，没有按各发型的 CC JSON 迁移 `RLHair` 粗糙度、主/次高光、透光和染色参数；现有重载验证只证明材质父类、两张贴图和保存状态。HB1-09 JSON 的 Root/ID/Flow 贴图路径为空，不能把这些贴图缺失直接认定为根因。还须区分透明度阈值/贴图过滤与单次 SceneCapture 的时域采样问题。

用户于 2026-09-30 指定先解决发片粗糙与发丝显示，男性穿模后续处理。本轮不启动 CC 或男性重导出，不修改发型性别许可。

#### 3.7.1 发丝渲染修复 V2：全库材质验证（2026-09-30）

实际材质审计 `rendering_repair_v2/initial_material_audit.json` 确认旧实例除底色、透明贴图外仍继承 M02 另一款发型的 Root/ID/Flow/Depth/Blend/ORM 贴图；透明贴图为 `sRGB=true / TC_DEFAULT`，而父材质的透明采样器要求线性灰度。旧 SceneCapture 没有连续帧历史。早期审计读到的 `r.PostProcessAAQuality=0` 不代表关闭抗锯齿：本地 UE 5.8 源码不再定义该变量，查询返回值不能用于判定；当前完整编辑器实测 `r.AntiAliasingMethod=4`（TSR）、`r.TemporalAA.Quality=2`。这些问题和边界须通过对照图核验，不能只凭材质父类正确宣布发丝显示已修复。

| 脚本 | 职责 |
| --- | --- |
| `ue_audit_hair_rendering_v2.py` | 读取实际材质参数、贴图、透明压缩与开关；默认保留初始审计，`DM_HAIR_AUDIT_V2=True` 验证已应用的 V2 报告和网格槽 |
| `build_hair_rendering_repair_plan_v2.py` | 从每款 CC JSON 和本地 RLPlugin 参数映射生成 40 款、220 槽修复计划；不继承另一发型的贴图 |
| `ue_repair_hair_rendering_v2.py` | 创建独立 `_StrandsV2` 材质实例，使用自身底色/透明贴图与父材质默认辅助贴图，保存并回读验证参数 |
| `run_hair_rendering_repair_v2.py` | 顺序逐款修复或用独立命令行 UE 执行剩余项；按完整成功报告续跑，`--verify` 从磁盘重新加载并审计 |
| `launch_local_unreal_editor_v1.py` | 以项目内可写日志/ShaderWorkingDir 启动 UE，或执行 `sdk-check`；不修改系统级环境变量 |

V2 透明贴图设为 `sRGB=false / TC_GRAYSCALE`，保留原纹理资产；透明幂与倍数恢复为 1、最小透明补偿为 0、Mask Clip 为 0.15。源 Root/ID/Flow 路径均为空，故停用 Flow/ORM 与再次染色，避免使用无关贴图或在导出底色上重复染色；粗糙度、散射及高光强度按来源参数设置。修复时保存了旧实例和旧照片；本轮按独立清单清理被替代资产与重复媒体，恢复映射和必要证据保留。UE 5.8 的材质参数 setter 即使写入成功也返回 false，脚本以 getter 回读判定，不把这个返回值当成失败。

40 款、220 个发片/头皮槽均已应用 V2，逐款证据为 `reports/HAIR_*.json`。独立命令行 UE 的 `fresh_load_material_audit.json` 与 `fresh_verify_20260930_165136/verification_result.json` 已确认全部槽从磁盘重新加载、实际底色/透明绑定、灰度压缩及源参数一致，51 个发饰或其他材质槽保持原始绑定。正式索引同步全部 220 个 V2 路径，`registry_full_sync.json` 确认除材质路径外其他字段不变；`registry_pilot_sync.json` 仅为前期单例证据。`build_full_ue_wardrobe_registry_v1.py` 按完整成功逐款报告叠加 V2，不把部分报告当作完成。

`ue_hair_sex_fit_review_v1.py` 拍摄显式启用 AntiAliasing/TemporalAA/PostProcessing，每个视角至少预热 32 帧和 1 秒，并保持时域状态。隐藏或 unattended 编辑器中 `capture_every_frame=true` 没有可靠执行，曾得到纯灰底色图片；失败整批保留在 V2 的 `captures/`，不得晋升。现改为 `capture_every_frame=false`，每个预热帧显式调用 `capture_scene()`；同时拒绝重叠拍摄，正常结束或取消后恢复后台节流。抗锯齿读取当前 TAA/TSR，必要时临时切为 TSR 并恢复，不再使用不存在的旧变量。`run_hair_sex_fit_review_v1.py` 自动规范化 RGB 并解码检查全部期望照片，透明、损坏、尺寸异常和纯色图片均判失败；纯灰底色回归测试已补齐。

`--capture-root` / `DM_HSF_CAPTURE_ROOT` 只能指向当前 Run Root 内的独立目录。`pilot_explicit_background_capture_clean/` 的 HB1-09 六视已确认正确女性角色与有效画面；早期发生重叠拍摄的 `pilot_explicit_background_capture/` 不作性别适配证据。全库新图输出到 `captures_explicit/`，验证成功、人工抽查构图后才能保留旧现行图并晋升；图片完整和材质机器检查均不等于用户最终视觉通过。有效决定和分步报告保留；被替代实例、重复大图及零透明度原图按本轮替代映射收敛，保留故障代表样本。

本轮 306 张显式逐帧新图已完成，`captures_explicit_validation.json` 验证全部可读、尺寸和非纯色；晋升到现行 `captures/` 前逐图保留旧照片为 `captures_masked_v1_before_strands_v2/`。`capture_promotion.json` 记录新旧哈希与实际 TSR 观测，`gallery_validation.json` 为 306/306，`assistant_visual_screen_v2.json` 只记录抽查结论和剩余宽高光、边缘颗粒、实体辫子疑点，不是视觉通过。整批任务启动时旧变量请求仍被记录为 `aa_quality=6`，该请求实际无效；当前脚本已移除，报告以实际 `r.AntiAliasingMethod=4` 为准。

从 `%LANCE_ROOT%` 执行：

```powershell
python 00_engine/scripts/unreal/build_hair_rendering_repair_plan_v2.py
python 00_engine/scripts/unreal/run_hair_rendering_repair_v2.py --hair-id HAIR_HB1_09
python 00_engine/scripts/unreal/run_hair_rendering_repair_v2.py --remaining --transport cmd
python 00_engine/scripts/unreal/run_hair_rendering_repair_v2.py --verify
python 00_engine/scripts/unreal/run_hair_sex_fit_review_v1.py --action capture --start 1 --count 51 --capture-root 00_engine/outputs/unreal_character_import/hair_sex_fit_review_20260929_v1/rendering_repair_v2/captures_explicit --timeout-seconds 1800
```

`cmd` 修复使用 NullRHI，不进行渲染；通过启动 INI 覆写关闭本进程的异步蒙皮/纹理编译，并使用独立 MCP 端口 28110，避免和完整编辑器冲突。不要在 commandlet 中反射设置 `EditorExperimentalSettings`：本轮试验触发过 FoliageEdit 崩溃，改为启动 INI 后剩余修复退出码 0，证据为 `cmd_repair_20260930_161851/editor_cmd.log`。完整拍摄仍须实际运行带 GPU 的 UE。以上材料、照片、日志及审计属于本节已有 `OUT-WF50-RUNTIME-ACCEPTANCE` 作用域，均位于 `hair_sex_fit_review_20260929_v1/rendering_repair_v2/`；未经保留决策不清理。

#### 3.7.2 dotnet 启动异常：已知原因与待核实复发

2026-09-30 启动日志捕获 `AutomationTool` 的 `UnauthorizedAccessException`：它无法删除用户 Roaming 下旧 `Log.txt/Log.json`，随后也无法写入 LocalAppData 下 `ErrorLog.txt`。这是本次已定位的一次 `dotnet.exe` 未处理异常来源；不能把所有同代码弹窗都直接归为这个原因，也没有证据要求重装 .NET。

启动入口将 `uebp_LogFolder`、`uebp_FinalLogFolder`、`uebp_EngineSavedFolder` 设置为本次运行目录下的 `uat_logs/uat_saved`，仅传给 UE 及其子进程；`-ShaderWorkingDir` 指向项目内临时目录，解决另一次 ShaderCompileWorker 写入失败。每次运行创建独立目录，以免相互删除日志：

```powershell
python 00_engine/scripts/unreal/launch_local_unreal_editor_v1.py --mode sdk-check
python 00_engine/scripts/unreal/launch_local_unreal_editor_v1.py --mode editor
python 00_engine/scripts/unreal/launch_local_unreal_editor_v1.py --mode editor --hair-review
```

`sdk-check_20260930_151225/launch_report.json` 为退出码 0；完整启动 `editor_20260930_151643/editor.log` 中 SDK 检测与设备检测均为 0，`uat_logs/Log.txt` 记录 `BUILD SUCCESSFUL / ExitCode=0`，UE Remote Execution 与上述单例拍摄均正常。用户随后仍报告同样弹窗；Windows 可读应用日志未找到对应新 dotnet 崩溃记录，正在确认是新弹窗还是上一轮未关闭窗口。因此当前状态是**启动检查通过、用户报告的复发尚未对齐**，不是故障已彻底关闭。手动快捷方式和其他脚本不会自动继承此入口的环境，不能外推为系统范围修复。

后台审查使用 `--hair-review`：隐藏窗口、打开审查关卡、`-unattended`，仅本进程关闭 PathTracing，实际 SceneCapture 仍使用 GPU。该配置跳过自动保存恢复模态窗口；启动前保留 `package_restore_info_before_launch.json`，不恢复或删除自动保存包，也不修改生产项目的路径追踪设置。2026-09-30 当前后台编辑器记录在 `editor_20260930_163316/`，Remote Execution 和显式逐帧拍摄实际可用；此前系统启动检查结果仍保留独立证据，不冒充该次启动的检测日志。受限执行账号启动时也曾卡在账户权限初始化，改用已授权本地用户上下文后完成启动与新进程核验。

当前发丝材质的全库扩展与磁盘重载已通过，新照片继续验证；用户最终视觉验收和新弹窗来源仍未关闭。男性头型适配保持后置，届时再用 F02/M02 同性导出对照决定是否增加 BodyFit 网格变体。

#### 3.7.3 发际线黑色网格：头皮层透明材质诊断（2026-09-30）

用户在 V2 新照片中报告额头、太阳穴和耳前出现规则黑色网格。第二、三张附件经 RGB 像素哈希精确匹配为女性 Case 006 / HB1-13 正面、Case 015 / HB2-05 前左；第一张为 Case 004 / HB1-09 正面裁剪。诊断根为 V2 下 `scalp_grid_diagnostic_20260930_v1/`，属于已有 `OUT-WF50-RUNTIME-ACCEPTANCE`，用户证据、来源映射和结论在 `diagnosis.json`。

`ue_probe_scalp_grid_v1.py` 使用当前关卡、相机和角色，对三款拍摄 baseline、隐藏头皮槽、只保留头皮槽、关闭头发阴影和头皮全不透明五种临时对照。最终有效证据是 `verified_controls/` 的 15 张照片及 `probe_progress.json`：隐藏头皮采用 `/Engine/Transient` 中常量零 Opacity Mask 材质，不依赖发丝材质内部的透明参数；只保留头皮时，其他发型槽使用同一不可见材质。所有变化只作用于临时组件覆盖，不保存源网格、材质或正式索引；结束后清除探针角色并恢复后台节流。重跑必须选择新版本目录，不能覆写现有照片。

三款均观察到：隐藏头皮槽后规则黑网格消失，只保留头皮时仍可单独复现；关闭头发阴影后网格仍在；强制头皮全不透明后点阵消失但留下黑色硬边覆盖层，不是可接受修复。`shader_opacity_graph.json` 进一步确认 `RL_Hair_Specular` 的 Opacity Mask 直接连接 `DitherTemporalAA`。源 `Scalp8` 底色和透明贴图没有规则黑网格，其透明图发际线为渐变；CC JSON 将该层标为普通 `Tra`，没有发丝 Custom Shader。当前修复把 Scalp 与 Hair 一起套用 Hair Shading Model，导致头皮渐变透明层在此审查渲染中显露抖动点阵；已定位的直接问题是头皮透明层，不需要以男性头型重导出解释这三张女性图片。

前期根目录及 `corrected_controls/` 的参数式隐藏试验当时保留为诊断历史，不用于“隐藏头皮后消失”的判断；本轮以代表样本和精确清理映射解释旧媒体保留范围。`Opacity Strength=0` 会绕过透明贴图，不能当作隐藏。新的常量零材质对照解决了这一不确定性。全库修复计划含 38 款的 69 个 Scalp 槽，这只是共同实现的潜在影响范围，不代表已经人工确认 38 款全都出现网格。

用户随后要求先审查“隐藏头皮覆盖层”的全库候选，决定是否沿用该策略，执行见 3.7.4。若隐藏后出现发根缺口或剃发区域丢失，再对相关款单独修正 Scalp 材质和透明过渡。正式 V2 绑定和现行照片保持现状；当时视觉确认待完成，最新规则网格子范围已由 3.7.6 收口，男性穿模继续后置。

#### 3.7.4 隐藏头皮覆盖层的全库候选审查（2026-09-30）

候选根为审查 Run Root 下 `scalp_hidden_review_20260930_v1/`，沿用原 `review_plan.json` 的 Case 编号、性别许可、标准角色、相机与六个方向，不覆盖现行 `captures/` 或原页面。`scalp_hidden_manifest.json` 记录来源计划/索引哈希、原版图片哈希和候选状态；隐藏槽审计与图片校验是机器证据，当时采用策略仍须用户视觉确认，最新确认与未实施边界见 3.7.6。

`ue_hair_sex_fit_review_v1.py` 的隐藏模式只在临时角色的组件上覆盖名称以 `Scalp` 开头且与 V2 计划准确匹配的材质槽，使用常量零 Opacity Mask；不能隐藏包含发丝和头皮的整个混合网格，也不能用 `Opacity Strength=0` 代替。逐案例核验其他材质槽和源网格绑定未变，结束后销毁临时角色并恢复节流/抗锯齿配置，不保存 UE 网格、材质或正式索引。瞬态 Actor 不一定出现在 EditorActorSubsystem 的枚举中，因此拍摄直接持有 Actor，清理使用编辑器 World 的 GameplayStatics 枚举。前期 `pilot/` 拍摄因瞬态枚举失败，没有有效图片；`pilot_verified/` 为前期机器试验，清理残留并重新拍摄的有效单款预检为 `pilot_clean/`，当时均留作诊断，不进入全库图库；后续物理保留以清理映射和代表样本为准。

`run_hair_sex_fit_review_v1.py` 要求隐藏模式明确指定独立图片与进度目录；已存在的候选图片不覆盖，续跑只选择未拍摄范围。`scalp_hiding_audit_*.json` 逐项记录隐藏与保留的槽，`capture_progress_*.json` 记录进度，`captures_visibility_normalization.json`、`captures_validation.json` 检查 RGB 可读性和全部预期图片。`build_hair_sex_fit_gallery_v1.py` 可生成独立 HTML 与 Markdown 图库，每个方向附原版对照；没有 Scalp 槽的款式在页面明确标为保持原样。

```powershell
python 00_engine/scripts/unreal/run_hair_sex_fit_review_v1.py --action capture --start 1 --count 51 --hide-scalp --capture-root 00_engine/outputs/unreal_character_import/hair_sex_fit_review_20260929_v1/scalp_hidden_review_20260930_v1/captures --progress-root 00_engine/outputs/unreal_character_import/hair_sex_fit_review_20260929_v1/scalp_hidden_review_20260930_v1 --timeout-seconds 1800
python 00_engine/scripts/unreal/build_hair_sex_fit_gallery_v1.py --output-root 00_engine/outputs/unreal_character_import/hair_sex_fit_review_20260929_v1/scalp_hidden_review_20260930_v1 --scalp-hidden
```

这些候选图片、Manifest、逐槽核验、哈希核验和预检证据归本节已有 `OUT-WF50-RUNTIME-ACCEPTANCE` 作用域；不自动晋升为正式资产设置或原图库。当前有效对照与决定保留，重复/失败大媒体和透明原图按本轮替代映射收敛，保留必要故障代表样本。人工需检查规则网格是否消失、发际线/发根是否露出缺口、剃发区域是否丢失；其他发丝边缘颗粒与男性穿模分别记录，不混同为头皮隐藏失败。

#### 3.7.5 Hairline 发际线覆盖层漏识别（2026-09-30）

用户认为隐藏后总体明显改善，但指出 Case 003 / HB1-05 前后接近。逐槽检查确认 HB1-05、HB1-20 没有 `Scalp` 命名槽，却分别包含 `Hairline_Transparency_Pbr` 和 `Hairline1_Transparency_Pbr`，位于各自目录的 `messy_high` 网格槽 1。原全库隐藏规则只匹配 `Scalp` 前缀，因此其男女 Case 003/011/033/041 没有任何实际槽覆盖。此前“没有头皮覆盖层”的页面文字不准确，已更正为“没有 Scalp 命名槽，但 Hairline 发际线层仍保留”；原 306 张候选照片未替换。

`ue_probe_scalp_grid_v1.py` 新增受限诊断参数：`DM_SGP_ROOT` 指定审查 Run Root 内独立证据目录，`DM_SGP_CASES` 为 `(index, view)` 列表，`DM_SGP_MODES` 选择既有控制，`DM_SGP_INCLUDE_HAIRLINE=True` 临时把 `Hairline` 前缀槽纳入隔离范围。默认诊断仍只处理 Scalp，参数不改变正式网格或索引。该轮选择 `[(3,'front'), (3,'left'), (11,'front_left'), (33,'front'), (33,'left'), (41,'front_left')]`，控制为 `baseline`、`scalp_hidden`、`hair_cards_hidden`；此扩展模式中后二者分别表示隐藏 Hairline、只保留 Hairline。

证据在 V2 下 `hairline_grid_diagnostic_20260930_v1/`：`verified_controls/` 的 18 张照片及其同目录 `probe_progress.json`、`image_validation.json` 均通过。观察确认隐藏 Hairline 后所测发际线的规则网格消失，单独保留该层可复现；其他发丝与发髻保留。`diagnosis.json` 记录两个实际槽和来源、原版与 Scalp 候选的全部 612 张照片哈希未变、正式索引未变及 431 个源网格/材质包自快照后的哈希未变。新增对照只作用于临时组件，结束清理并恢复普通审查角色。

源 HB1-05 的 Hairline 透明贴图包含细短毛发，所以它不能简单等同于实体头皮盖片；隐藏也会移除这些细节。后续候选需采用已核验的网格/槽位清单覆盖 Scalp 与这两个 Hairline 槽，并由用户检查发际线外观；其他主发丝颗粒、宽高光和男性穿模仍单独处理。`comparison.html`、`comparison.md` 展示原版、隐藏 Hairline、只保留该层三组图，原候选页面的四个 Case 增加补充入口。该轮当时的用户评价为整体改善但有遗漏；补充对照后的规则网格视觉确认见 3.7.6，不外推为全部发型或正式资产实施通过。该目录归本节已有 `OUT-WF50-RUNTIME-ACCEPTANCE`，有效诊断、决定和当前对照保留；被替代的旧大图按本轮清理映射收敛。

#### 3.7.6 覆盖层隐藏策略的用户确认与实施边界（2026-09-30）

用户在查看全库 Scalp 候选及 HB1-05/HB1-20 的 Hairline 补充对照后明确确认：“的确，现在已经完全合理了，发型没有再出现这种网格线。” 本次将 **规则黑色网格的视觉复核** 记为通过，确认隐藏已核验覆盖层的策略。该结论不关闭男性穿模、逐身份头型适配、全部发型外观、动态播放或打包运行时 Gate。

人工决定与准确实施目标保存在当前发型审查 Run Root 下 `coverage_visibility_acceptance_20260930_v1/`：`manual_review.json` 绑定用户原话、证据哈希及范围，`approved_coverage_slots.json` 汇总逐槽核验的 Scalp 和 Hairline 清单。目标必须按 `hair_id + mesh + slot_index + slot_name` 精确匹配，实施前核对当前正式索引哈希及原材质；只隐藏匹配槽，不隐藏含有主发丝的整个网格，不用 `Opacity Strength=0` 代替常量零透明材质。BabyHair、主发丝、发髻、辫子和发饰不因名称相似而扩入清单。

这份清单是**已确认视觉策略的待实施目标**，当前 v003 读取器、正式网格和材质尚未消费它。现行全库候选仍为 Scalp-only 的六视图；两个 Hairline 款式的男女四个 Case 通过 3.7.5 的补充对照查看，尚未拍摄一套整库 Scalp+Hairline 联合六视图。后续如实施正式策略，应单独执行组件或材质持久化、保存重载和代表视觉检查，再更新实现状态；本轮只同步文档，没有修改 UE 资产或重拍图片。

隐藏 Hairline 会同时移除该层细短毛发，这一取舍已包含在所审查对照中。用户的确认来源是直接陈述，不能伪造为逐图按钮日志。上述人工决定、槽位清单和当前候选/补充证据归本节已有 `OUT-WF50-RUNTIME-ACCEPTANCE`，保留为 `retained_evidence`；恢复时先读本节与最新 WF-50 状态，不能继续执行 3.7.3–3.7.5 中已经被本次确认取代的“等待用户确认”。

### 3.8 现用入口与 2026-10-01 清理边界

现用 UE 资产由正式 `wardrobe_registry_ue_v4_full_20260929.json` 和 v003 读取器驱动。保留两个 Average BASE 的 Body、规范 Skeleton、必需物理/面部支持；`/Game/Vendor/Reallusion/CC5/Characters/M02_Average/` 剩余部分仍被当前发型共享纹理、材质模板、动画/面部 Rig 支持消费，不能整树删除。`CC_Shaders` 与有效 `CC_Rigs` 核心保留，损坏演示网格/Picker 只有经过逐包闭包审查才能退休；缺失 Rig 预览引用不等于 Rig 图可删。

| 现用功能 | UE 关卡 | 现用 Plan / Run Root |
| --- | --- | --- |
| 全库服装覆盖 | `/Game/DataMake/Validation/Wardrobe/Average/L_DM_WardrobeAverage_Coverage` | `%OUTPUT_ROOT%/unreal_character_import/current_reviews_20261001_v1/wardrobe_coverage/` |
| 发型×服装审查 | `/Game/DataMake/Validation/ScalpHairCompatibility/L_DM_ScalpHairCompatibility_Review_v001` | `%OUTPUT_ROOT%/unreal_character_import/current_reviews_20261001_v1/hair_outfit_compatibility/` |
| 发型六视与覆盖层对照 | `/Game/DataMake/Validation/ScalpHairFit/L_DM_ScalpHairFit_Review_v001` | `%OUTPUT_ROOT%/unreal_character_import/hair_sex_fit_review_20260929_v1/` |

Coverage 按第 3.5 节启动，也可双击该根的 `open_review.cmd`。Compatibility 使用当前脚本默认 Plan，其 `bodyfit_metadata.json` 只保留 `bodyfits` 和消费者实际读取的 Body、Blueprint、15 个服装槽定义；没有旧 Pilot candidate/variant。启动或查看：

```powershell
python 00_engine/scripts/unreal/run_hair_outfit_compatibility_review_v1.py --action panel
python 00_engine/scripts/unreal/run_hair_outfit_compatibility_review_v1.py --action show --case-index 1
python 00_engine/scripts/unreal/run_hair_outfit_compatibility_review_v1.py --action view --view side
```

也可双击 Compatibility 根的 `open_panel.cmd`；HairFit 继续用第 3.7 节入口。各面板需要正常启动、Remote Execution 可用的 UE Editor，不启动 CC。

2026-10-01 验证证明：两现用关卡各自的旧角色已替换为 v003，原 transform、服装赋值、Body、动画和附加头发保持，保存重载通过；Coverage 对既有 173 套搭配全部实际装配，并验证第 1 页重载；Compatibility 第 1 项及正/侧/背三个方向通过。证据在 `%OUTPUT_ROOT%/asset_cleanup/cleanup_20261001_v1/current_review_verification.json` 与 `ue_audit/review_actor_migration_result.json`。这是入口迁移和 API 装配验证，不是新增逐款人工视觉或完整动态发型验收。

旧 14-Case、P0、ScalpHairPilot、v001/v002 独立执行入口和早期对照关卡已退休，原证据和冻结计划不改写。旧启动 Main 已退役，现用启动地图为 HairFit。按 `ue_cleanup_review.json` 的精确名单共清理 2,396 个 UE 包、4,594,625,010 字节；新进程确认名单中的包在 registry 和文件系统均不存在，正式 777 个网格/材质/纹理包的字节哈希完全不变，173 套搭配重新装配、第 1 页保存重载及 Compatibility 第 1 项三视复验通过。保存依赖图没有新增缺失的 Game 引用，保留 Rig 的只读补验成功且没有保存或新增脏包；历史 Rig 预览缺失引用仍由诊断报告说明。总验收证据见 cleanup 根的 `ue_cleanup_receipt.json`、`formal_asset_hash_verification.json`、`ue_saved_graph_verification.json` 和 `post_cleanup_runtime_checks_completion.json`。这次收口不包含新增发型视觉或动态适配验收。

执行曾出现两个真实边界：旧 World 的 `delete_asset=True`、registry 条目消失但 `.umap` 留存；后续 UE API 实际删除部分 uasset 后，将保留的 M02 材质模板网格在内存中标脏。两者均停止并保留失败/部分回执，保留包没有保存，UE 会话已退出。UE 5.8 对象删除计数与后续 package 清理是不同步骤，返回 True 不能代表物理删除成功。

最终恢复采用已审核的完整确切名单：先验证保存后的新鲜依赖图对删除集合没有外部消费者、正式保留闭包没有交集，关闭所有 UE 进程，再用原生 PowerShell 的字面路径逐文件清理名单中的剩余包。每条路径、文件大小/哈希与伴随文件均已核对，没有按 unused/Pilot 名称扩张范围；API 完成的 10 个包与离线清理的 14 个 World、2,372 个其余资产分别记录，失败/部分回执保留。删除后已在全新 UE 进程重扫 registry，完成正式包哈希、173 套装配和现用关卡重载验证。这是本轮已获明确授权的精确恢复，不是日常直接删除 uasset 的通用方法。执行清单、逐项结果和恢复边界由 [全面清理 Output 所有者](../output/INVENTORY_AND_RETENTION.md#9-2026-10-01-全面清理与目录重组)维护。

重新导入来源也属于保留边界：`retained_legacy_support_import_sources.json` 实测 183 个仍使用的 M02 共享支持资产，其 ImportData 指向 `%CC_EXPORT_ROOT%/pilot_m02_ue58_v001/CC_M02_Average_Pilot_UE58.Fbx`，来源文件均存在。因此该旧 M02 完整导出包的 271 个文件、501,042,951 字节继续保留；独立 Pilot 入口退休不代表这些来源可删。其他已替代的旧导出 821 个文件、3,517,715,394 字节已按 `cc_retired_export_cleanup_receipt.json` 清理。本次不修改保留资产的 ImportData，也不把男性头型适配、正式运行时 Scalp/Hairline 隐藏设置或 Headshot 固定头型能力写成已实现。

### 3.9 固定头型双版本发型的代表小样与索引消费（2026-10-04）

本节拥有 `ue_review_fixed_head_hair_pilot_v1.py`、`ue_audit_fixed_head_hair_v1.py` 和正式索引消费者对双版本发型的支持；导出/导入及索引生成归 [Transfer 11.5](../transfer/CC_TO_UE_MODULAR_OUTFIT_PILOT.md#115-固定男女参考头型的双版本发型转换2026-10-04)。HB3-17 的男女代表小样已通过；全量导入、新索引发布和一次实际加载审计也已通过，终态证据由导入/发布报告及项目状态定位。既有 v003 Body/服装资产不会由此被自动改为新规范人物。

小样脚本读取新批次 `import_report.json`，要求同一代表发型男女两条记录已成功，并在 `/Game/DataMake/CharacterFactory/FixedHeadHair_20261004_v1/Review/L_FixedHeadHair_Pilot` 使用对应固定头型基础网格和骨架挂载。默认 `DM_FIXED_HAIR_PILOT_ID=HAIR_HB3_17`，可设置 `DM_FIXED_HAIR_PILOT_CAPTURE=False` 只保存可检查关卡；代表结果写 `%OUTPUT_ROOT%/unreal_character_import/fixed_head_hair_20261004_v1/pilot_review.json`，六张实际 GPU 图片写 `%OUTPUT_ROOT%/unreal_character_import/fixed_head_hair_20261004_v1/pilot_captures/`。二者由本节拥有，归 `OUT-WF50-RUNTIME-ACCEPTANCE`，作为 retained pilot 证据保留：仅 HB3-17 男女正/侧/背六视，不是全库照片。真实图片路径以该 `pilot_review.json` 为准；本节输出所有权与保留策略使用上述实际 `pilot_captures` 前缀。该小样对两个几何分支执行，不改变原 `sex` 使用许可；全库是否完成仍查导入报告。2026-10-05 的 `pilot_review.json` 已登记六张正/侧/背图实际视觉查看通过：两性均在预期头皮位置，发丝和透明边缘可见，未见规则黑网格。快速 SceneCapture、诊断基础人物材质接缝不作为正式数据集画质/肤色验收，也不扩大为全库或动态穿模。

`formal_wardrobe_registry_v1.hair_fit` 将几何适配与使用许可分开：旧条目只有 `meshes` 时继续原行为；新条目 `fit_variants` 必须同时含 `female/male`，每组提供共享 `skeleton_path` 及准确 `meshes`。`resolve_selection` 先判断 `sex` 和 Family/资产 `deny_all`，允许后按 `character_sex` 选择路径，并输出 `hair_fit_sex/hair_skeleton_path`。`ue_formal_wardrobe_runtime_v1.py` 据此核对对应共享 Skeleton，不再把新男性版本强制当作旧 F02 网格。

命令入口支持显式新索引。正式默认读取器现根据哈希绑定 publication 和完整 import_report 选择该新索引；旧索引保留作构建来源、历史审查与支持依赖追溯，证据不匹配时回退旧版本。真实 Python/CLI 默认读取与原使用许可、Family、共享鞋保持相同的检查在本批次 `consumer_completion_check.json`。显式入口：

```powershell
python 00_engine/scripts/unreal/run_formal_wardrobe_registry_v1.py --registry 00_engine/assets/character_creator/wardrobe_registry_ue_v4_fixed_head_hair_20261004_v1.json --phase inspect
```

全量导入成功且新索引发布后，执行一次只读 `ue_audit_fixed_head_hair_v1.py`：

```powershell
python 00_engine/scripts/unreal/run_fixed_head_hair_v1.py --action audit
```

该检查通过正式读取器解析所有 40 款男女版本，再实际加载 80 组发型的网格、共享骨架及材质/纹理；检查新版本仅有男女两个 Skeleton、精确预期网格集合和无 `_Staging` 资产/物理包残留，检查批准覆盖槽都引用持久化的零 Mask。结果为 `%OUTPUT_ROOT%/unreal_character_import/fixed_head_hair_20261004_v1/final_runtime_audit.json`，由本节直接生成并拥有，归 `OUT-WF50-RUNTIME-ACCEPTANCE`；它是 retained 结构加载/支持闭包终验报告，不是全部发型的视觉或动作验收，不产生新输出类别。这是全库轻量加载/闭包证明，不渲染全部款式或测试动作；运行前置未满足不能提前写通过。 图形设备故障后可在 NullRHI 编辑器执行此结构审计，具体恢复归 Transfer 11.5；`review` 拍摄必须使用正常图形编辑器，不能以无 GPU 运行替代已有小样视觉证据。调度脚本 `run_fixed_head_hair_v1.py` 的实现所有权仍归 Transfer。

2026-10-05 已实际执行上述一次结构审计，`final_runtime_audit.json` 为 `success=true`，与发布 Registry SHA 一致，全部目标适配版本的网格、两个共享 Skeleton、零 Mask 及必要支持可加载，staging 包/物理残留为零。精确计数及所有引用保存在该报告；这是 NullRHI 结构加载结果，不替代 GPU 代表图片或全库视觉检查。

`stage/verify` 使用同一 `--registry` 选项传到 UE。旧 v003 Body 路径不因索引切换自动替换成新固定头型人物；精确固定源挂载由本次独立小样证明，后续 Headshot 角色装配必须使用相应参考形状。除实际异常外不增加逐款视觉、全动作或严格旧 Average 位姿门禁。覆盖层只处理批准的 Scalp/Hairline 精确槽，发丝及实体发辫/装饰仍保留；不得用隐藏整个发型替代渲染修复。


### 3.10 固定头型发型的双角色人工审查（2026-10-05）

本节拥有 `00_engine/scripts/unreal/ue_fixed_head_hair_manual_review_v1.py`、`00_engine/scripts/unreal/run_fixed_head_hair_manual_review_v1.py` 和一键入口 `00_engine/scripts/unreal/open_fixed_head_hair_manual_review_v1.ps1`。这些入口建立独立双角色关卡及人工切换入口，使用已经发布的固定头型双版本索引；不重新导出/导入、不拍摄图片、不操作 CC，不关闭或重启用户现有 UE 会话。CLI 已完成 `--help` 与语法检查；实际 UE 代表加载和启动交付也已通过，证据为本节新 Run Root 的 `worker_smoke_check.json`、`cli_smoke_check.json`、`entry_context.json` 与 `machine_handoff.json`。R01 界面交付 completed；R02 用户逐款静态贴合审查已通过；R03 两项原因核查及建议已交付，正式修复未实施。

目标关卡为 `/Game/DataMake/Validation/FixedHeadHair/L_DM_FixedHeadHair_ManualReview_v001`，对应固定女性/男性基础网格各一人，同时显示同一保留发型的 female/male 几何适配版本；逐款切换供用户观察，审查模式不会改写正式 `male/female/both` 使用许可。输入来源是已发布 `wardrobe_registry_ue_v4_fixed_head_hair_20261004_v1.json` 及其固定参考资产，原转移证据与接受策略保持不变。

Run Root `%OUTPUT_ROOT%/unreal_character_import/fixed_head_hair_manual_review_20261005_v1/` 由本节拥有，归 `OUT-WF50-RUNTIME-ACCEPTANCE`；保存界面配置、切换/代表加载报告及后续人工结论的追溯信息，不生成 `captures`。界面机器交付属于 `VAL-UE-02` 的独立入口子范围；用户已直接确认全部发型在两个固定参考人物上的静态贴合及无明显穿模；材质外观存在本轮报告异常，单独核查，不凭 API 成功关闭人工 Gate。只做代表加载核对，不新增全动作或任意身份检查。发生实际错误时保存失败报告并恢复当前界面，不触发原导出/导入批处理。

2026-10-05 已实际交付：原 UE PID36348 持续运行，原关卡保持未修改，新独立关卡保存。HB1-01 男女各四个发型部件与对应 Skeleton/LeaderPose 一致，两基础人物比例为 1；正面男女同屏、女性侧面放大、男性背面放大的实际控制均完成刷新。面板一键启动成功并自动加载第 1 款 `HAIR_HB1_01 / Curly long ponytail`，正面男女同屏；`panel_state.json` 是当下可续看选择。该交付阶段没有自动拍图，后续用户完成实际审查并直接在对话给出结论。人工汇总为 `human_review_summary.json`；没有自动补造面板 `manual_review.json` 的逐项按钮日志。机器视角与引用检查本身不等于人工接受。

使用已经打开且 Remote Python 可用的 `datatry_02` 图形编辑器。一键启动（从任意 PowerShell 位置）：

```powershell
& 'D:\UE\Lance_Work\00_engine\scripts\unreal\open_fixed_head_hair_manual_review_v1.ps1'
```

该入口先显示指定款式，再打开中文面板；可用 `-HairIndex 1` 指定起始项。面板等待 UE 视口刷新结束才显示“已加载”，避免后台操作完成但画面未刷新；下拉框直接切换、上一款/下一款逐项选择；正面、侧面、背面、斜侧面与男女同屏/女性放大/男性放大控制编辑器视角。正常关闭面板只恢复审查期间的后台 CPU 设置，不退出 UE。CLI 准确参数为 `--action panel|show|view|status|restore`、`--hair-index 1..40`、`--view front|side|back|threequarter`、`--sex both|female|male`；从 `%LANCE_ROOT%` 可直接调用：

```powershell
python 00_engine/scripts/unreal/run_fixed_head_hair_manual_review_v1.py --action panel
python 00_engine/scripts/unreal/run_fixed_head_hair_manual_review_v1.py --action show --hair-index 1 --view front --sex both
```

用户可选填备注并点击“女性/男性正常”或“有问题”，将人工决定写入本 Run Root 的 `manual_review.json`，绑定当前 Registry SHA；也可直接在对话中给结论，后续由维护者记录来源，不要求逐项点击记录按钮。`panel_state.json` 只表示选择和镜头状态，不能代替人工决定；错误写 `panel_error.json` 或 `restore_error.json`，不因此重跑原转换。

本次界面交付的文档/回归证据为同 Run Root 的 `documentation_audit_final.json` 和 `regression_tests.json`：16 个独立检查及跨层检查实际通过、零错误警告，完整要求回归通过。这两份证据归本节的独立审查交付范围；不扩大为用户逐款视觉通过，也不改写原转移批次的终验报告。

2026-10-05 用户已确认全部 40 款男女两版发型在对应固定参考人物上正确贴合、未见穿模。这一 `VAL-UE-02` 静态几何子范围由直接文字报告关闭；不改发型使用许可，不扩大动态、其他身份、服装组合或生产画质。`human_review_summary.json` 记录 Registry SHA、范围、用户文字、五张用户附件原路径与两项未关闭材质问题，由本节拥有且归现有 `OUT-WF50-RUNTIME-ACCEPTANCE`。面板点击记录与对话人工汇总是不同证据来源，不相互伪造。

#### 本轮两项材质异常的原因核查

只读报告为同 Run Root 的 `ue_material_readback.json`、`hair_braid_material_diagnosis.json` 与 `body_seam_diagnosis.json`，按既有运行输出归本节及 `OUT-WF50-RUNTIME-ACCEPTANCE`。审查使用当前材质/纹理属性、源 CC JSON、旧新纹理 SHA 与源 FBX 交界数据；未切换场景、修改资产或执行材质因果 A/B。Run Root 中 `ue_read_material_diagnosis.py` 和 `body_seam_source_probe.py` 是该轮 retained 只读诊断执行记录，不是新生产或批处理入口。

**发辫偏深：** 源 CC JSON 明确为 `RLHair` 的 12 个 `Hair_Pbr/Hair_N_Pbr` 等实体辫槽，被旧修复按非 Transparency 名称误归“实体辫子/发饰保留”分支。当前辫子继续引用 Generic Legacy Phong / DefaultLit，SpecularColor 与 Specular map 权重为零；相邻主体使用 `MSM_HAIR` 的 StrandsV2，反光响应不一致。结构范围为 HB1-18、HB2-02、HB2-05、HB2-06、HB2-12 五款，12 源槽 / 24 双性绑定；真实 39 发饰槽不属于修复目标。用户报告三款旧新 Diffuse 字节一致，排除本次导出换色；源实体辫原色可略暗，不能承诺改 Shader 后完全同色。建议以源 `Custom Shader=RLHair` 判定语义，为对应辫槽建立独立 Hair 实例并绑定该槽自己的颜色、透明度、粗糙度/高光参数，保持已烘焙颜色策略，先对一代表款做 A/B，再处理明确范围；不隐藏辫子、不改饰品、不重导网格。

**身体接缝（后续复核更正）：** 两性Head Normal属性为`sRGB=false/TC_NORMALMAP`，Body/Arm/Leg六Normal却以`sRGB=true/TC_DEFAULT/WORLD`导入，这是已确认的纹理分类缺陷；修复试验复制出的女性`T_Skin_Head_Normal`即使属性看似正确，GPU实际采样曾为`[1,1,0]`，造成半黑错误；这是试验资源复制异常。`texture_gpu_original_head_normal.json`实际读取原CombinedBase男女Head Normal均近`[0,0,1]`正常，不能把试验异常归到原Head Normal或照片源。16张源Diffuse/Normal与旧验收导出字节一致，源几何共享控制点且两侧法线差为零，不需要修改头型/身体几何。

原`body_seam_diagnosis.json`所写源头/体约25/43 RGB显著色差是采样脚本错误：Head/Body/Arm/Leg的UDIM整数偏移UV被clamp到边界，而应先UV modulo1后采样各材质自己的PNG。后续`%OUTPUT_ROOT%/unreal_character_import/fixed_head_material_repair_20261005_v1/skin_source_seam_corrected_diagnosis.json`明确supersedes该源色差结论；正确wrap后四类皮肤交界均差约1–1.7 RGB/255，无显著源肤色色差。旧报告原样保留用于追溯，不能继续作为改肤色或生成Delta必要性的依据。当前修复采用物理源独立导入16张PNG并统一简单DefaultLit材质，不修改源肤色色调、不使用颜色Delta；实施状态见3.11。

R03 原因核查与处理建议已交付；正式修复、代表因果对照与材质视觉接受未实施。原 Registry、正式网格/材质和转换报告保持不变，用户之后启动修复时只检查代表修复效果，不重新恢复全库静态适配或80套重导。

当前计划与人工结论状态见[新人工审查计划](../../project_management/history/completed_plans/PLAN-2026-10-FIXED-HEAD-HAIR-VISUAL-REVIEW.md)和 [WF-50](../../project_management/status/workflows/WF-50.md)。

### 3.11 固定参考头型人物与发辫的定向材质修复（2026-10-05）

用户已授权实际修复前节已确认的两个问题。实现所有者为本文，影响 `WF-40/WF-50`，验证归 `VAL-UE-02` 的独立材质修复子范围；修复及发布已完成，代表机器核验和后续用户人工接受分别记录；不能以授权或目录存在代替证据。可复用导入防复发规则另由 [Transfer 11.5](../transfer/CC_TO_UE_MODULAR_OUTFIT_PILOT.md#115-固定男女参考头型的双版本发型转换2026-10-04)描述。本节拥有以下稳定实现；导入主worker的实现归Transfer11.5，调用本节源语义和Normal辅助。

| 实现 | 职责与当前边界 |
| --- | --- |
| `00_engine/scripts/unreal/hair_source_shader_v1.py` | 按源`RLHair`语义建立发丝/辫子实例、按槽读取参数；模块导入不改资产，颜色已烘焙，不再次应用染色/顶点色 |
| `00_engine/scripts/unreal/ue_repair_fixed_head_braid_materials_v1.py` | `plan/preview/restore_preview/apply/rollback`精确辫子槽修复，持久化apply与原槽journal；现五款24绑定已apply |
| `00_engine/scripts/unreal/ue_repair_fixed_head_skin_materials_v1.py` | `build/preview/apply/rollback/status`两参考Body物理源纹理独立导入与统一材质；当前保存apply已通过，2网格8skinbindings、无Delta；后续用户可观察代表效果 |
| `00_engine/scripts/unreal/ue_fixed_head_skin_texture_utils_v1.py` | 依据精确四CC皮肤槽及源JSON Diffuse/Normal声明建立物理源计划、TextureFactory新资源和统一皮肤实例；兼容函数名不是仅改Normal flags |
| `00_engine/scripts/unreal/build_fixed_head_skin_seam_control_v1.py` | 保留早期线性颜色增量控制试验；UDIM采样复核后未发现显著源色差，最终unified方案不调用此控制图，也不把试验当正式修复 |
| `00_engine/scripts/unreal/build_fixed_head_material_registry_v1.py` | 两类修复成功apply后才生成新材质引用版本并发布哈希绑定回执；两类成功apply已取得，新材质Registry已发布；严格依两份独立快照与SHA核验 |

本节复现前置为现有`datatry_02`图形UE Editor、Remote Execution可用，保持原参考几何/源纹理与转换证据。辫子worker默认仅`plan`，使用UE全局`DM_BRAID_REPAIR_MODE`指定阶段，可用`DM_BRAID_REPAIR_HAIR_IDS`限定诊断目标；`apply`精确保存网格材质槽，`rollback`从durable journal恢复原槽。使用UE Python控制台运行（以下只生成plan，不改材质绑定）：

```python
from pathlib import Path
__file__ = r'D:\UE\Lance_Work\00_engine\scripts\unreal\ue_repair_fixed_head_braid_materials_v1.py'
DM_BRAID_REPAIR_MODE = 'plan'
DM_BRAID_REPAIR_HAIR_IDS = None
exec(compile(Path(__file__).read_text(encoding='utf-8-sig'), __file__, 'exec'), globals(), globals())
```

身体worker的`DM_SKIN_REPAIR_MODE=build/preview/apply/rollback/status`提供阶段控制。最终使用`DM_SKIN_SHADER_VARIANT='unified'`，该分支强制`DM_SKIN_CORRECTION_STRENGTH=0`、不创建或采样颜色Delta图。早期`hq`、颜色控制/`build_fixed_head_skin_seam_control_v1.py`保留为失败或非采用试验的复现，不能作为默认或正式修复；无需再生成控制图。最终新父材质为`M_UnifiedSkin_PhysicalSource_v1`，Opaque/DefaultLit、Roughness0.6/Specular0.35。

两性Head/Body/Arm/Leg的Diffuse及Normal共16张原始PNG经`TextureFactory`独立导入到修复目录，不复制旧故障GPU纹理：Diffuse为`sRGB=true/TC_DEFAULT`，Normal为`sRGB=false/TC_NORMALMAP/CHARACTER_NORMAL_MAP`，绑定各自的物理源路径与SHA。源照片像素、原纹理和几何保持。仅修属性不足以处理复制纹理GPU样本白值；需要核对实际新纹理采样/代表显示。

新索引发布器为`python 00_engine/scripts/unreal/build_fixed_head_material_registry_v1.py`，仅在两份saved apply实际成功后运行；它检查exact24辫槽、两性Body、旧索引来源及哈希，保存publication独立快照。该门禁现已满足并实际运行；新publication为`registry_publication_report.json`，保存`hair_apply_publication.json`与`skin_apply_publication.json`独立成功apply快照并绑定各自SHA，避免把可变latest当长期发布真值。新默认Registry为`wardrobe_registry_ue_v4_fixed_head_materials_20261005_v1.json`，SHA为`15d83025446fc472a2275f1b39aa483f99f644aad60cd32052ee21afaedeb5a6`。旧双版Registry、原import_report及其publication保持原字节；前序默认阶段现在是回退/来源，不作为新材质权威。

运行证据根为 `%OUTPUT_ROOT%/unreal_character_import/fixed_head_material_repair_20261005_v1/`，归现有 `OUT-WF50-RUNTIME-ACCEPTANCE`，由本文产生和维护：记录精确源语义/目标绑定、前后材质/纹理设置、代表对照、保存结果与几何保护。`execution_state.json`表示当前范围与进度；发辫`hair/hair_apply_latest.json`已为success/apply，完整24绑定及源纹理SHA、材质参数/原槽journal保留。新UE材质位于`/Game/DataMake/CharacterFactory/MaterialRemediation_20261005_v1/Hair/`，使用对应源Diffuse/Opacity与`RL_Hair_Specular`。代表`hair_before.png`和`hair_after_preview.png`已实际查看：HB2-05辫子从暗黑条状改善为棕色细节，R01completed；真实饰品与Scalp/Hairline策略不改变。此处原为机器代表图检查，后续用户场景人工接受见本节补充记录。

身体最终`skin_apply.json`success/apply，男女两Body网格共8皮肤槽已保存到各自独立的物理源实例；`correction_strength=0`，父`M_UnifiedSkin_PhysicalSource_v1`没有颜色Delta节点。试验复制女性Head Normal早期GPU白值导致半黑，原CombinedBase男女Head Normal实际GPU采样正常，物理原PNG独立重导后面部恢复正常；原失败/诊断图保留且不作为成功证据。`material_repair_visual_review.json`登记主agent实际查看`body_final_front.png`和`body_final_back_rotated.png`：未见原明显颈肩/躯干/四肢材料边界及异常阴影，两性脸正常。后颈部分被发型遮挡，未做隐藏面审查；`body_final_back.png`墙后黑图是失败拍摄，不用于接受。R02completed，这是代表静态材质范围，不是新增用户确认或任意光照/动态/生产画质通过。

**图片交付的透明通道纠正：** 原`body_final_front.png`等代表文件的RGB有正常渲染内容，但RGBA包装的Alpha全为0；遵循透明通道的查看器会将其显示为空白。先前图像查看忽略Alpha，不能由该查看结果推断原文件可直接交付。这是图片包装的透明通道问题，不是原渲染RGB为空白，也不改变材质修复、正式索引或代表检查范围。原RGBA文件保留；同Run Root的`body_final_front_visible.png`、`body_final_back_rotated_visible.png`、`hair_before_visible.png`和`hair_after_preview_visible.png`是可正常查看的RGB PNG入口。`opaque_previews_manifest.json`记录各原图Alpha范围及转换前后RGB SHA，逐像素RGB一致；仅移除错误透明包装，没有重渲染或修改材质。失败拍摄`body_final_back.png`仍不作为接受证据，不能用透明通道纠正替代其拍摄失败结论。

本轮策略现在是保持源颜色、正确物理纹理与统一材质响应，不进行头身色调修正；发辫exact24绑定已成功保存。检查对应范围及保存结果，不重拍全库、不重复静态几何人审或重导80套。真实发饰、固有辫子原色、批准隐藏的Scalp/Hairline及人物/发型几何保持，不能隐藏问题部件冒作修复。

后续修复效果可在原双角色审查关卡/面板查看，入口见3.10；本轮机器交付本身不会自动产生用户视觉通过记录；用户现已通过原审查界面检查并直接确认，见同Run Root的`user_material_acceptance.json`。当前执行与需求状态由 [新材质计划](../../project_management/history/completed_plans/PLAN-2026-10-FIXED-HEAD-MATERIAL-REPAIR.md)及 [WF-50状态](../../project_management/status/workflows/WF-50.md)维护。发辫/身体saved apply、真实代表结果和新索引发布已登记。`material_apply_verification.json`是实际UE只读readback：264检查、0失败，核对8皮肤/24发辫绑定、8Normal/8Diffuse的线性语义及物理源SHA、26其他身体材质与Skeleton保持。它不声称新的全角度GPU或动态通过。

**后续导入防复发已接入并验证。** `ue_fixed_head_skin_texture_utils_v1.configure_imported_skin_normals`保留历史函数名，但实现已扩为精确四皮肤槽的Diffuse+Normal物理源导入及统一材质实例。`build_skin_source_plan`限定FixedHeadHair下Shared/CombinedBase目标，要求四不同标准皮肤槽、源JSON各通道存在、纹理路径留在对应导出包，锁定源SHA，并以网格/源/材质参数指纹生成版本化`SkinSource_v1/S_<fingerprint>`目录。每槽自己的物理源Diffuse/Normal经TextureFactory导入，不能复制可能损坏的Interchange GPU资源；复用已有版本时核对ImportData及源SHA/语义，维持幂等。父材质为直接Diffuse/Normal输入、DefaultLit、Roughness0.6/Specular0.35，无Delta/改肤色；仅替换四皮肤槽，其他身体材质与几何/Skeleton不变。主导入worker消费关系归Transfer11.6。

同根`skin_future_import_offline_check.json`覆盖男女8槽/16纹理规划与4针对性测试通过；`skin_future_import_runtime_smoke.json`为真实UE独立女性Body副本，首次4槽/8纹理成功导入，第二次全部复用/幂等，正式Body完全不改。此smoke只证明一个独立副本的API/源图/直接材质图，不能扩为全量重导或新视觉库。R03completed；R04实际readback部分已完成，本轮完整要求回归`material_repair_regression.txt`已通过307项（74.52秒），`material_repair_docs_audit.json`16独立子系统/跨层实际全通过、0错误警告。R04completed，计划迁History；归档导航的快速终验由`material_repair_docs_audit_final.json`登记，不重复UE或完整pytest，整计划已完成归档，项目显式空闲；后续用户修复后外观接受单独由`user_material_acceptance.json`记录。

`completed_import_guard_verification.json`记录实际调用主导入完成批次guard：80records保持完成，正常无重导返回，原`import_report.json`SHA前后均为`f98f91fcffb2d694121dad13b22e4cf5a123e090f3c468b36f975e9fdab30755`。防复发改代码不会因旧批次完成就覆盖历史报告或重导。

2026-10-05用户通过现有审查界面检查后直接确认：“ok，没问题，我刚才也通过审查界面进行了检查，一切正常。” `user_material_acceptance.json`（记录时间2026-10-05T12:57:13+08:00）绑定当前正式材质Registry及SHA，关闭现有男女参考人物审查场景中的修复后发型和皮肤外观人工接受范围。来源是本轮直接文字报告，不是逐款/逐角按钮记录；不新增动态、任意身份或隐藏表面通过，原材质失败、机器代表图和失败拍摄历史保留。

#### 本轮材质修复的恢复边界

旧材质/纹理输入保留。发辫worker`DM_BRAID_REPAIR_MODE='rollback'`按`hair/hair_apply_journal.json`恢复原槽；皮肤worker`DM_SKIN_REPAIR_MODE='rollback'`按`skin_mesh_backup.json`及`skin_actor_backup.json`恢复网格材质槽/审查组件覆盖。两者只恢复相应UE绑定，不自动修改publication或默认Registry选择。

若实际回退已经发布的修复，消费者必须同时显式选择旧`wardrobe_registry_ue_v4_fixed_head_hair_20261004_v1.json`并重新检查该回退范围；不能仅回滚UE槽后仍用新默认索引而声称完整回退完成。新/旧发布回执与apply快照保持追溯，恢复后应登记新结果，不改写已完成转换或修复证据。当前没有执行回滚。用户看结果继续使用3.10原双角色关卡/面板，它通过默认索引加载新材质引用；不会更换规范几何或触发批量重导。

### 3.12 完整男女角色骨架与代表发型装配试点（2026-10-05）

[已完成静态试点](../../project_management/history/completed_plans/PLAN-2026-10-COMPLETE-CHARACTER-UE-SKELETON-PILOT.md)的来源/导入/骨架比较归[Transfer12](../transfer/CC_TO_UE_MODULAR_OUTFIT_PILOT.md#12-完整角色ue导入与骨架标准试点2026-10-05)。本节唯一拥有`00_engine/scripts/unreal/ue_stage_complete_character_skeleton_pilot_v1.py`及`%OUTPUT_ROOT%/unreal_character_import/complete_character_skeleton_pilot_20261005_v1/runtime/`，归OUT-WF50-RUNTIME-ACCEPTANCE，默认unclassified保护；系统CLI归Transfer12。

`runtime/static_assembly_report.json`实际success：男女各六部件加载，以Body为LeaderPose，眼睛/牙齿/舌头/tearline/occlusion跟随；从当前已批准材质Registry消费对应性别HAIR_HB1_02（四组件），每个发型组件118共有骨参考位移差0、LeaderPose读回true。旧发型资产/许可/Skeleton没有修改；这只接受这两历史来源的静态引用装配，尚不接受动作/表情播放或新身份共享；本试点静态可见外观已获用户后续确认，见下段。

审查关卡为`/Game/DataMake/Validation/CompleteCharacterSkeleton20261005/L_DM_CompleteCharacterSkeleton_Pilot_v001`。入口`python 00_engine/scripts/unreal/run_complete_character_skeleton_pilot_v1.py --action open`要求已启动图形编辑器、无脏关卡；NullRHI只用于导入，不能作视觉查看。`runtime/render_editor_reload.json`success=true：新图形编辑器重载已保存关卡，20个skeletal actor及所有非Body LeaderPose引用读回，UE现保留此关卡供用户查看。静态机器回执与图形入口交付通过；机器重载不代替人审；随后root在用户可见UE窗口137398打开同一新关卡并确认双方显示，原自动GPU进程26728窗口隐藏，未假称该窗口已显示。用户实际查看后直接说“目前看来一切正常，接下来我们的计划是什么”，`runtime/user_visual_acceptance.json`绑定原saved map、重载/静态报告及两导入审计SHA，记录男女参考六部件+各HAIR_HB1_02静态可见外观通过。身体/表情动作、新身份共骨架及隐藏表面未验证。

当前六部件共保留每性别2,455个跨网格源Morph；独立Skeleton和HQ材质范围见Transfer12。源无独立HD眉毛，不代表最新CC装配输出。本轮不重导80发型/服装，不启动batch、CC或新导出；标准仍是男女分开的候选，common_skeleton_adopted=false，必要动态/新身份范围后续按独立授权建立。

### 3.13 完整角色服装、发型与身体动作审查界面（2026-10-05）

新Body拓扑补读由tonight_20261006_v1/runtime/read_complete_body_topology_v1.py负责，输入complete_body_topology_pins_v1.json与单女小样request，说明为complete_body_topology_readme_v1.md。真实回执runtime/complete_body_topology_readbacks/20261005T232945676254Z_8292d555/receipt.json已completed/success：女性SOURCE_MODEL转换几何14,164顶点、28,092三角面，位置与固定旧快照一致；以当前render顶点数15,602及固定UE5.8源码排除render fallback。DynamicMesh顶点/三角ID不是render或原FBX索引；6个render section有效材质槽可读，原始LODMaterialMap、源面到render面对应仍未测。未保存资产、未改场景、未建立遮挡。check_complete_body_topology_offline_v1.py的7项模拟检查不能代替该回执；男性本轮补读未执行，可逆遮挡仍未实现。原始几何及回执归runtime/complete_body_topology_readbacks/，沿用本节输出保护。

身体遮挡证据见tonight_20261006_v1/runtime/body_occlusion_evidence_memo_v1.md：旧运行时未实现皮肤表面遮挡，隐藏未用衣物组件不能算该功能。新Body六材质槽也不等于已证明可安全隐藏的六个解剖分区；当前缺少逐面覆盖及渲染section对应。R05需单独取得绑定新Body的遮挡依据、应用/换装/裸身恢复和失败回退证据；当前槽位快照不覆盖HiddenMaterials或动态材质参数，不能提前宣称可逆遮挡完成。

高跟鞋单变量方法见tonight_20261006_v1/runtime/heel_pose_only_method_v1.md：从已验证v002动作重建独立A/B，仅B的左右foot/ball四骨局部旋转变化，保持全部平移/缩放、其他骨轨与同帧场景一致；必须先取得鞋自身参考数据和完整回读。动态同动作版本尚未实现；下文静态A/B资产已补独立数值读回，场景对照仍未执行，不关闭R02/R05。新旧CC_Base_Body源多边形、UV及UVIndex原始数组哈希不同，不能按索引直接移植遮挡；这也不等于已证明UV岛语义布局不同。

只读诊断同属本节：tonight_20261006_v1/runtime/read_heel_bind_pose_v1.py读取F015鞋网格与完整女Body各自的118骨局部参考变换，不用共享Skeleton参考替代鞋自身参考；check_heel_bind_pose_payload_offline_v1.py和read_heel_bind_pose_offline_validation_v1.json记录模拟检查。真实runtime/heel_bind_pose_readbacks/20261005T232940361835Z_5e718529.json及heel_actual_reference_comparison_v1.json确认鞋相对Body的pelvis局部平移约+8.7678cm，左右foot旋转差约44.17/44.18度、ball约33.10度；这不是穿模深度、角色升高修正量或鞋姿态修复验收。material_audit/ue_query_texture_residency_sample_v1.py、parse_texture_residency_log_v1.py只查询指定已加载贴图并解析唯一标记日志；test_texture_residency_parser_v1.py及texture_residency_sample_validation_v1.json记录离线边界。后续material_audit/residency_queries/20261005T234247Z_54d0d47345fc4489a91edb3483b21040/host_capture_20261005T234305Z_657aa013/reparse_categoryless_csv_v2/parsed.json已按原始字节顺序重新解析：男性衬衫当前1024×1024、11 resident mips；女性Top1/Top2当前5376×5376、Streaming=NO、VT=NO，女性resident mip数量与Wanted仍未测。先前“女性LIST在END之后”的判断已更正：原CSV在LIST_END之前，旧parser未识别无LogCategory前缀的header；失败结果保留。仅限这3张纹理与该查询时点，高分截图在前可能已推进资源加载，不外推335项全量驻留或原始截图时点状态。输出沿用本节Run Root及OUT-WF50-RUNTIME-ACCEPTANCE保护。

**今晚新增授权（2026-10-06）**：[当前Plan](../../project_management/plans/active/PLAN-2026-10-COMPLETE-CHARACTER-WARDROBE-DIAGNOSIS.md)扩大为正式筛选发布、槽位/关卡迁移、全部保留衣物/鞋材质审查、有网络来源的改善建议；替代下文前序阶段禁止池发布的执行边界，历史证据和已接受范围不改。新证据归同父Run Root的`tonight_20261006_v1/registry_publication/`、`runtime/`、`material_audit/`、`material_methods/`，沿用OUT-WF50-RUNTIME-ACCEPTANCE/unclassified保护。本节拥有关卡迁移、全量材质画面与建议的产生/验证，正式Registry默认选择仍由其原Technical所有者维护并同步Registry入口。拟建新固定组件worker及测试须在实现后登记准确入口和实际生命周期，不能由拟定名称宣称已通过。

初次筛选v1已冻结：`00_engine/assets/character_creator/wardrobe_registry_ue_v4_reviewed_pool_20261006_v1.json`，由`build_reviewed_wardrobe_pool_registry_v1.py`产生，原发布链tonight_20261006_v1/registry_publication/保留。当前默认已晋升不可变v2：`00_engine/assets/character_creator/wardrobe_registry_ue_v4_reviewed_pool_20261006_v2.json`，实现为`00_engine/scripts/unreal/build_reviewed_wardrobe_pool_registry_v2.py`，`formal_wardrobe_registry_v1.py`逐级核验v2/v1/materials发布SHA链，缺失或漂移明确失败，无静默旧池回退。`reviewed_pool_v1_registry_path()`及显式历史读取保留历史复现；原发型sex/几何fit与reviewed_sexes两层许可保持。v2证据见tonight_20261006_v1/post_slot_user_review_20261006_v1/publication_manifest_v2.json、selection_validation_v2.json、selection_mapping_v2.json、protected_sources_v2.json；正式SHA为42bea3d643cff65734efa21b7ed9282ae654cd49365346bd327ac284277d1f24。发布规则证明和实际用户接受分开记录，不由registry.new_body_visual_acceptance=false抹掉下述人工反馈，也不将用户反馈推广为全库Gate。

旧`complete_character_review_contract_v1.py`已显式固定materials历史台账，保持173套/40发型历史界面与证据复现；新固定槽位审查另读新筛选目录，不把旧历史索引偷偷重编号。配套历史目录测试同样显式使用保留版；两套入口的范围分开。

今晚新增实现仍为`experimental`，由本节拥有：`00_engine/scripts/unreal/ue_complete_character_fixed_slot_runtime_v1.py`负责六基础部件+32衣物/配件/发型固定组件、稳定归属、预检、构建/迁移/切换和独立读回；`complete_character_slot_review_contract_v1.py`提供正式筛选目录、真实按槽合法选择、原编号快捷预设和到运行时的完整选择转换；`ue_complete_character_slot_review_v1.py`整合动作、视角、失败回退和保存重载前读回；`run_complete_character_slot_review_v1.py`提供中文面板/CLI，`open_complete_character_slot_review_v1.ps1`为可见启动器。配套测试为`test_complete_character_fixed_slot_runtime_v1.py`、`test_complete_character_slot_review_contract_v1.py`、`test_complete_character_slot_review_worker_v1.py`、`test_complete_character_slot_review_controller_v1.py`。离线通过不代表真实UE已完成：构建、迁移、动作/CopyPose/重载和用户审查必须分别留证。

真实执行检查点（2026-10-06）：首次旧build在远程观察90秒超时后继续运行，最终于2026-10-05T23:00:58Z（本地10月6日07:00:58）成功；tonight_20261006_v1/runtime/fixed_slots_build_v1.json记录两性BP各38组件、37个Follower构造分支，男女BP均保存。原超时与女性先保存/男性开始日志保留，不再记作当前等待build。新优化版本的直接节点创建、耗时/加载SHA及取消恢复边界仍是另一次实现；runtime/build_implementation_optimized_v2.py/.json及17项离线检查不能倒称本次旧build已使用优化。fresh editor_before_migration_v1.json记录原World的63个审查Actor、dirty_maps/dirty_content均空；before_migration_checks_v1.json核对原关卡、独立备份及备份回执SHA保持，source_assets_modified=false。

首次迁移失败见runtime/fixed_slots_migrate_v1_remote.json：槽位赋值随后失效，不能按新Actor存在判成功。本节拥有的实验探针runtime/probe_slot_property_reset_v1.py及slot_property_reset_probe_v1.json实际证明，变更component_tags的默认editor属性通知会重建组件（same_component=false），PropertyAccessChangeNotifyMode.NEVER保持对象身份；临时Actor已销毁、当时fixed_pair_absent=true、未保存关卡或修改源。现worker实例属性使用NEVER；材质同时经原生SetMaterial更新渲染，再精确清空/还原override数组；apply前后核对组件对象身份，失败rollback重新解析当前组件并独立读回，不复用失效引用。

迁移重试fixed_slots_migrate_retry_v2_remote.json与fixed_slots_migrate_v1.json已success：男女各38组件、component_identity_stable=true、errors=[]，56个旧人物/附件Actor仅隐藏保留。initial_slot_review_v1_remote.json实际show女89/男23、hair2、action0/paused成功。初次copy_pose_saved_reload_10_v1_remote.json曾因女性HairPart01–04在重载后回到Body Leader而失败；首次actor_tag_graph_patch_20261005T234441_57cb9eb4.json又在function_reference公开API预检安全失败，这些旧回执保持原样。后续actor_tag_graph_patch_20261005T235811_d9d59867.json已success：男女BP独立备份、37处分支由组件tag改为Actor级slot tag，其他187节点保留，两BP均patched_saved。补丁本身不代表重载通过；后续runtime/controlled_checks/20261006T000449_46c526/receipt.json完成40步，才提供实际运行验证。



机器交付时40步包括10个合法男女组装对；女性保留发型10/15/16/24/33各自show→pause→save/reload→重装前读回→pose采样；男女动作2–5均时间推进且骨位置变化，结合既有Audience检查记录限定动作覆盖，不能补称每条动作都有独立暂停稳定测试。全部预期CopyPose组件head/pelvis静态距离小于0.1cm（实际head最大约2.91e-14cm、pelvis为0）；仅是暂停同步容差，pose_acceptance、visual_fit_acceptance和human_acceptance仍pending。末尾恢复女89/男23、hair2、静态后保存重载成功。该次首次面板PID32124曾ready/error null并完成show；最新关闭状态与人工反馈见下述补记；不是鞋姿态/遮挡或人工外观接受。actor_tag_runtime_regression_v1.xml为491 passed、0失败/0错误/0跳过、97.876秒，仅该轮必要回归；目录与文档最终审计仍待root统一。

今晚阶段性执行与证据入口另由本节统一拥有，生命周期均为experimental，不因文件存在视为已执行。runtime/下backup_review_level_v1.py、preflight_before_migration_v1.py、preflight_editor_v1.py、run_fixed_slots_v1.py、run_payload_v1.py负责备份、预检和root串行派发；build_implementation_before_optimization_v1.py为旧构建实现快照。prepare_controlled_switch_cases_v1.py产生controlled_switch_cases_v1.json，run_controlled_slot_checks_v1.py已实际完成上述40步。它核验实际业务回执，步骤间比较current_case归一化选择，变化即停止且不自动恢复/继续保存；不检测原生视口拖动等全部原生操作，root须全程独占。超时保留任务终态未知且不重派；静态CopyPose同步结果与pose/visual/human pending分开。read_slot_pose_sample_v1.py产生pose_samples/具来源的身体/跟随骨位置回执，单时刻观察不作穿模或动态同步验收。patch_fixed_slot_actor_tag_graph_v1.py与probe_copy_graph_public_read_v1.py负责受限图补丁/公开读取探针，首次补丁预检失败保留，后续成功应用及重载以独立新回执登记。record_live_progress_20261006_v1.py为execution_checkpoint_v1.json的早期产生器；当前检查点按新机器回执维护，不重跑旧脚本覆盖进展；read_material_batch_v1.py和run_material_remaining_batches_v1.py调度只读材质批次。material_audit/下build_offline_audit_v1.py、build_surface_witnesses_v1.py、inspect_source_textures_v1.py产生离线清点/合法见证/源图资料；check_texture_residency_entrypoint_offline_v1.py与test_texture_residency_deferred_completion_v1.py拥有驻留入口/异步完成边界检查。新增patch/pose/controlled_switch/execution_checkpoint、ue_batches/、ue_effective_material_audit_v1.json/.md、captures/和residency_queries/均归本节及OUT-WF50-RUNTIME-ACCEPTANCE，unclassified保护；Catalog/Inventory与最终审计由root待代码稳定后统一重建，不继承前序回归作为本次改动通过。


后续准备入口仍归本节、experimental：runtime/probe_fixed_slot_template_handles_v1.py读取BP模板句柄，read_floor_contact_context_v1.py记录真实Floor和角色上下文，floor_contact_context_4057ec670c.json实测水平地板顶面Z=-2.5cm，未移动地板或角色；组件bounds/足骨不是变形后鞋底接触或穿模深度。runtime/prepare_static_heel_pose_ab_v1.py及test_static_heel_pose_ab_v1.py、static_heel_pose_ab_v1.md、static_heel_pose_ab_preparation_v1.json负责静态足姿A/B：118轨参考姿态中只改变foot_l/r和ball_l/r四骨旋转，保持其他旋转及全部T/S，不加入pelvis升高；默认preflight离线不创建资产。真实builder曾在创建/保存A/B后校验失败，runtime/static_heel_pose_ab_20261006T001912_3bab1f4b.json及对应remote失败原样保留；后续独立只读验证不能倒写旧builder成功。

本节新增experimental只读入口为runtime/read_existing_static_heel_pose_ab_v1.py，request_existing_static_heel_pose_ab_read_v1.json为请求；runtime/static_heel_pose_ab_readback_20261006T002926_1cef1d4a.json实际success/completed_read_only，核对既存A/B输入不变量及允许误差，源与A/B包SHA保持，未新建/保存资产或改场景。该回执仅证明资产数值，不证明鞋内贴合、接地、场景应用或恢复；scene_pose_and_visual_validation仍pending。runtime/body_occlusion_bounded_recommendation_v1.md拥有基于新女Body拓扑/UV的有界遮挡建议，未制作或应用mask，不以整体隐藏Leg/Body掩盖短裤或高跟鞋外露皮肤；runtime/user_review_guide_v1.md提供新面板人工检查与问题记录方法，人工反馈仍独立于机器检查。

material_audit/prepare_visual_execution_v1.py、run_visual_execution_v1.py与test_visual_execution_offline_v1.py由本节拥有，visual_execution_schedule_v1.json、visual_execution_readme_v1.md、visual_execution_validation_v1.json登记76个合法组装场景、92个采集组、822张基础机位覆盖326项；9项无合法组外套单列。原7项离线检查通过；实际采集已启动，完整完成范围及在途范围以runtime/execution_checkpoint_v1.json和各run回执为准，不能把已采集当作已看图或已接受。runner逐场景show、每批最多12视角，等待同run捕获及恢复完成，失败/超时不重派、不自动切回、不保存关卡，根会话全程独占；current_case守卫不检测两派发之间所有原生UE操作。图片采集成功仍须逐目标衣片/材质槽核实可见，visual_review保持pending/quality_verdict为空。material_audit/test_texture_residency_actual_csv_v2.py拥有真实无LogCategory CSV解析回归。上述准备、回归、floor、graph_function_evidence/、controlled_checks/、pose_samples/、panel生命周期与未来visual_execution_runs/回执均归OUT-WF50-RUNTIME-ACCEPTANCE/unclassified保护，未改变源资产保留规则。

旧审查入口新增迁移保护：当前审查World中，任一Actor的精确label、专用owner tag、对应FixedSlotRuntime生成类同时匹配，便拒绝旧show/view/playback/reload及直接stage；不以Blueprint文件或迁移回执存在判断，未迁移关卡不受影响。恢复入口保留。`test_complete_character_legacy_review_migration_guard_v1.py`与registry_publication/legacy_migration_guard_pytest_v1.xml记录17项离线检查，真实编辑器拦截仍待迁移后核验。runtime/catalog_to_fixed_slots_check_v1.json另证156旧编号预设与38性别发型选择可生成无槽位冲突的实际新计划，不代替装配/动作/重载结果。

材质完整分母为335独立衣物/鞋、1043源材质槽与2308源图，证据为tonight_20261006_v1/material_audit/coverage_manifest_v1.json、source_texture_inventory_v1.json及offline_accounting_validation_v1.json。legal_surface_witness_manifest_v1.json中326项有合法完整组合，9项streetwear外套因原YogaPants组停用而无当前合法组，仅保留独立表面诊断。ue_read_material_batch_v1.py的18批UE实读已完整覆盖335项，汇总ue_effective_material_audit_v1.json/.md核验1043槽、2308源通道逐项对应和2320张不同UE纹理，0读取错误/对应缺口；每批dirty集合稳定，但已有当前审查map dirty、content为空。LOD Bias/MaxTextureSize均0、平台与缓存导入尺寸一致，不是驻留证明。134张Normal类型/sRGB正确，13条源Normal声明实际经Bump接入且开关开启；147条源Strength百分值与UE归一化值一致，10个零值源端也为零。1043槽Roughness Map查询值为共享Gray，shader实际连通未检查；本次读资产材质，不代替场景组件OverrideMaterials。F95衣片WA165有独立Normal、其鞋WA015为默认Normal，不能把F93–95反馈统一归因缺法线。工作4方法报告material_methods/material_improvement_methods_v1.md已结合逐件可见表面给出有界建议；335项均有记录（326实图、9无合法组合未定），不是视觉全部接受。

材质画面安排为material_audit/visual_scene_schedule_v1.json及check/说明，按完整请求去重并保留item/组件归属，安排覆盖不等于画面可见。material_audit/ue_capture_material_samples_v1.py及test_capture_material_samples_v1.py由本节拥有：当前同一已装配配置最多12个视角，both只允许full、单性允许head/torso/legs/feet/full；不改衣服、源材质或光照，沿已核对视口捕获，状态守卫/恢复仍生效，用户改场景/搭配/镜头时不覆盖新状态。旧接口失败及最小化超时回执原样保留；20261005T231950_5c34ce2e三张虽捕获/恢复成功但full裁脚、feet裁鞋底，不能作完整取景证据。随后captures/20261005T233117_55157a20/capture_receipt.json三张捕获与恢复通过，root实看女性full头脚完整、feet含鞋底地面，亮皮肤/噪点仍限制评价；最新captures/20261005T234524_98f6c89d/capture_receipt.json三张亦通过，root实看双人full、男性legs、女性head取景可见，男性裤腿下摆进入legs画面（距离250cm、高度50cm、FOV45）。这是限定取景/捕获/恢复证据，非335项材质视觉完成或用户接受。定向驻留源码依据见material_methods/resident_mip_evidence_from_ue58_source_v1.md；不把尺寸元数据或Wanted比例当作实际最高驻留。

收据原子发布修复仍由本节拥有：material_audit/test_capture_receipt_atomic_retry_v1.py覆盖临时占用、持久拒绝与其它异常传播；capture_receipt_retry_validation_v1.xml为3项新测试及既有capture/runner合计21 passed。仅PermissionError时重试同一.partial→json替换，10次尝试间最多9次25ms显式等待，不重拍；225ms不是包含文件IO/系统调度的严格墙钟上限。MS019原captures/20261006T002417_eb6ac418/capture_receipt.json failed、1张完成、restoration_success=true，原失败保留。visual_execution_schedule_v2.json只更新capture脚本pin，76场景/822机位与其它字段不变；material_audit/visual_execution_schedule_v2_revision_v1.json/.md记录v1/v2 SHA、原因和19项输入实测，run_visual_execution_v1.py通过显式--schedule选择版本，不放宽其它pin校验。受控重采以独立新run收据为准。

material_audit/compile_visual_findings_v1.py为本节experimental离线汇总入口，不调用UE，默认只报告覆盖；显式--write仅在335项均有明确记录、76场采集与恢复收据以及所引图片SHA核验齐全后发布，9项无合法组合外套须单列受限/未定，不能冒称有统一光照见证。material_audit/visual_review/拥有MS001图片/材料索引、逐件观察、排队索引、9孤立外套与粉泳装有界诊断；material_audit/visual_reviews/拥有root及其它reviewer分段实际看图记录。两目录均需保留audit_item_id、scene_id、具体观察、建议、独立贴合问题、证据图片/SHA及user_acceptance=pending；同纹理不替代不同材料版本看图。material_audit/findings/material_findings_v1.json/.csv/.html已由该汇总器发布；图片SHA、场景/截图编号及场景条目归属均核验，无图豁免仅允许9孤立外套为uncertain；HTML/CSV保留每条原判定与场景，不以混合汇总掩盖受限范围；上述脚本、测试、版本证明与审查产物沿用本节OUT-WF50-RUNTIME-ACCEPTANCE/unclassified保护，最终交付需重建catalog及Output Inventory，并以runtime/tonight_final_documentation_audit_v1.json记录全量文档audit。

最终交付记录（2026-10-06）：335项均已记录：暂时保留118、建议改善111、暂不能判定106。其中326项有合法组装画面，9项外套无合法组合，明确列为未定；不是335项视觉通过。runtime/tonight_delivery_summary_v1.md为简明交付入口，runtime/user_review_guide_v1.md为人工检查步骤。runtime/final_restore_request_v1.json、final_reload_request_v1.json及对应final_restore_initial_20261006_v1_remote.json、final_reload_initial_20261006_v1_remote.json记录恢复原F89/M23 hair2静态并保存重载；replies/4133774099514c53b4e0611e46839c8c.json为独立重装前读回success。runtime/tonight_final_regression_v1.xml记录491 passed/0失败/0跳过；runtime/tonight_final_documentation_audit_v1.json记录最终16独立子系统和跨层通过、0错误/0警告；首次缺少WF-50需求显式映射的失败审计已保留并修正。新增交付/审核文件均沿用本节OUT-WF50-RUNTIME-ACCEPTANCE/unclassified保护。

粉色泳装WA031的上游身份问题见material_audit/visual_review/bikini_pink_assembly_diagnosis_v1.json/.md及bikini_pink_source_geometry_v1.json：粉罩衫与WA036泳裤的源面索引/UV及四张贴图相同、位置数组不同，CC历史加载回执、源导出和UE提取一致；其余四色coats为WarriorCloak。问题已在导出内容/资源角色标注上游，不能归作新槽位残留；原ccCloth内容与加载行为尚未最后区分。user_review_guide_v1.md要求人工检查时暂不叠加可选粉罩衫，保留异常资产；当前registry、采集pins与场景不因该备忘改动，不能把同帧两裤片材质自动分别放行。

**新版槽位人工反馈与v2池（2026-10-06）**：用户已亲自检查新版固定槽位关卡，报告除男性Lift & Haul及鞋问题外，其余服装、发型与动作基本正确合理。男性male.lift_haul已退出正式v2候选池，不删除资产；女性共享同名鞋保留。R10按用户实际观察范围completed，不推断全部组合、动作逐帧或隐藏面通过。高跟鞋仍保留待讨论，鞋脚姿/接地、新Body可逆遮挡及未覆盖动态贴合仍待；未实施材质或几何改善。

精确原话与边界由tonight_20261006_v1/post_slot_user_review_20261006_v1/human_review_feedback_v2.json保存。当前38families/309family assets/43shared shoes/32hair；新增剔除male.lift_haul的11网格及旧男性33–36，历史样例为女79/男73共152，编号不压缩；女性共享Lift & Haul鞋不因同名被删除。

本节拥有tonight_20261006_v1/post_slot_user_review_20261006_v1/current_material_scope_v1.json/.md，按v1 findings和v2 registry的SHA/精确网格集合筛选当前324项（保留117/改善101/未定106）；移除WA233–WA243原10改善/1保留，历史335份记录/采集pins不改写，没有新拍摄、重审或改善。

机器交付曾恢复F89/M23、hair2、静态双人全身并保存重载；该记录保持历史范围。最新面板runtime/panel_lifecycle.json为PID42712/stage closed/restore_success=true，用户审查已完成，不宣称面板当前ready；本轮发布不操作UE或重新打开面板。 控制器再次打开时仅复用当前目录仍合法的保存衣物选择；被剔除family选择须回到合法预设，默认静态/hair2政策保持。R06维持in_progress用于鞋及未覆盖代表动态贴合，不能把用户笼统报告换算成每件/每帧通过；R05鞋pose/新Body可逆遮挡未实现，R02/R03未定项保留。本次v2发布/控制器改动必要回归post_review_regression_v1.xml已实际515 passed、0失败/0跳过（45.03秒）；本次文档审计post_review_documentation_audit_final_v1.json实际16个独立子系统及跨层通过，0错误/0警告。 新反馈、池范围与后续检查均归本节、OUT-WF50-RUNTIME-ACCEPTANCE/unclassified保护；不实际改善材质/几何、不运行CC/重导/删除，不改另一会话状态。

#### 现有参考女性高跟鞋受控验证（2026-10-06）

本轮新增授权先使用已导入fixed-head完整参考女性验证高跟鞋，不等待新角色才能开展机制检查；用户随后开始导入并要求暂不操作UE，后续共享应用执行已停止。Run Root为`%OUTPUT_ROOT%/unreal_character_import/complete_character_wardrobe_hair_review_20261005_v1/tonight_20261006_v1/runtime/heel_validation_20261006_v1/`，本节拥有全部实验工具、执行证据和策略报告，沿用`OUT-WF50-RUNTIME-ACCEPTANCE`/`unclassified`保护；不新增删除或CC操作权限。

现有完整参考女性F015静态A/B已完成两轮、共8张正背脚部图：真实求值确认仅foot_l/r与ball_l/r四骨局部旋转变化，Body上游姿态/同轮人物变换保持，鞋跟随Body；原包哈希和场景恢复检查通过。root可见观察为B脚踝包裹及鞋跟朝向改善，接地和鞋内全部表面仍未接受。第二轮A/B共同临时抬高20cm仅用于诊断隔离，已恢复，不能作为站立高度或接地参数。 精确回执为captures/20261006T031607_7bb0910b/capture_receipt.json与captures/20261006T032028_81561ee9/capture_receipt.json，独立actual_pose_comparison_v1.json及actual_pose_clearance_comparison_v1.json均通过。这里的观察为root实际查看图片，不是用户最终鞋修复批准，不推断侧面/鞋内全表面、全部鞋款、动态或最新创建身体接受。

两轮静态回执实际绑定的是编辑器既有warm-loaded reviewed_pool_v1目录，registry SHA c7b10609fb5d2de83917e17b3cde5c8258fe8e1aa94043287dc6efaa8dd89bea；本轮为该加载态上的同鞋/四骨机制试验，不是v2运行时或热重载验收。正式机器默认v2权威SHA 42bea3d643cff65734efa21b7ed9282ae654cd49365346bd327ac284277d1f24保持，原回执不改写。所测F89/F015及男性Cyber组合不涉及新增Lift & Haul排除；current_v2_choice_compatibility_v1.json已以正式v2 SHA 42bea3d643cff65734efa21b7ed9282ae654cd49365346bd327ac284277d1f24离线解析实际选择通过，不能由此证明编辑器已读v2。下一次获准UE操作先核验catalog.source.registry SHA或显式刷新依赖，拒绝继续误用缓存v1。setup_restore_context_v1.py已新增fresh formal.current_registry_path/文件SHA与warm UI catalog的严格门；缓存v1会明确拒绝，新增代码尚未在UE执行。

第一轮执行源码SHA为0ce02f41406c314a516d59ddc50fabc1629adcd91c023563f355caffc89b9acf，由ue_capture_static_heel_ab_dispatched_v1.py及dispatched_source_binding_v1.json保留字节绑定；原receipt不回写。第二轮执行当前ue_capture_static_heel_ab_v1.py，SHA为fc3e4e0aab3485b81f9f44759d6a196f957c6979081e94010af2222739dca329，含终态dirty包检查；不能倒称第一轮已执行后来新增检查。

Audience动态A/B独立动画资产已生成并全帧数值读回：118轨、137关键帧、30fps，原108轨之外10轨以Body参考填充，两态同样填充；B仅四脚骨使用normalized(D × Q_A(t))，全部平移/缩放及其余旋转保持。源动画及保护包未改、帧末GC完成。动态场景采集与实际变形鞋顶点测量尚未执行；用户换World后fixture/preflight安全拒绝，未修改新场景。 builder证据为dynamic_heel_ab_20261006T032815_345d6fd3.json，仅completed_assets_only，不当作实际动作/接地通过。editor_context_after_operator_switch_v1.json为最后只读边界：World为/Game/DataMake/Validation/CFDNativePair20261006/PreviousSession/L_PreviousReview_20261006_v001，dirty空，live_fixture_snapshot=false，静态handle/task inactive，动态状态absent；未加载回旧审查World覆盖操作者选择。

本节拥有H目录全部以下脚本，生命周期均为`experimental`：`build_heel_findings_v1.py`、`compare_dynamic_heel_capture_v1.py`、`compare_static_heel_capture_v1.py`、`measure_posed_shoe_vertices_v1.py`、`prepare_dynamic_heel_ab_v1.py`、`probe_editor_context_after_switch_v1.py`、`probe_posed_surface_api_v1.py`、`read_scene_context_v1.py`、`setup_restore_context_v1.py`、`test_dynamic_heel_ab_v1.py`、`test_dynamic_heel_capture_v1.py`、`test_static_heel_capture_v1.py`、`ue_capture_dynamic_heel_ab_v1.py`、`ue_capture_static_heel_ab_dispatched_v1.py`、`ue_capture_static_heel_ab_v1.py`。setup_restore_context/read_scene_context读取/暂设/恢复限定fixture；静态capture/独立compare留四骨求值与源保护证据；dynamic prepare仅建独立动画、dynamic capture/compare和measure_posed_shoe_vertices为后续受控采集/实际变形几何验证；探针只读，API可见不代表顶点测量已运行。build_heel_findings_v1.py为已实际执行的纯离线hash证据汇总入口，不连接UE，产出heel_validation_findings_v1.json/.md与human_visual_observations_v1.json；current_v2_choice_compatibility_v1.json为离线合法性证据，本节拥有，不能当热重载接受。三份test仅证明相应离线边界，不代替共享UE执行。

heel_repair_options_v1.md与dynamic_test_protocol_v1.md保存复核策略；本节同时拥有root汇总heel_validation_findings_v1.json/.md和human_visual_observations_v1.json。新增证据不改写此前失败或静态准备报告。用户要求导入期间暂不操作UE，root已停止共享UE操作；这仅暂停UE执行，不将唯一current计划改为paused。现有参考身体可承担机制验证，最新男女成品另需复核，不由本轮替代。R02/R05/R06继续in_progress，高跟鞋未退出候选池，正式鞋pose/接地配置和新Body遮挡未接入。

本轮离线验证实际完成：H/heel_offline_regression_v1.xml为新增工具21 passed（0失败/错误/跳过）；H/required_regression_v1.xml为项目要求回归521 passed（0失败/错误/跳过，147.66秒），不借用此前515项结果。Catalog/Inventory已重新盘点；H/documentation_closure_v1.json记录最终16个独立子系统与跨层审计，H/verification_summary_v1.json汇总本轮范围。测试和文档通过不改变动态场景、鞋底接地及最新角色待验状态。全部新增验证输出由本节及OUT-WF50-RUNTIME-ACCEPTANCE拥有，保持unclassified保护。

本节拥有[已完成计划](../../project_management/history/completed_plans/PLAN-2026-10-COMPLETE-CHARACTER-WARDROBE-HAIR-REVIEW.md)的独立UE审查界面、既有服装/发型消费与代表BodyOnly动作适配。新Run Root为`%OUTPUT_ROOT%/unreal_character_import/complete_character_wardrobe_hair_review_20261005_v1/`，归`OUT-WF50-RUNTIME-ACCEPTANCE`，默认`unclassified`保护；不改变前序完整角色导入或旧服装/发型证据。本轮工具交付已完成，人工合身/穿模仍pending，实际范围由[WF-50状态](../../project_management/status/workflows/WF-50.md)记录，不能由脚本存在推断交付成功。

输入使用前序`complete_character_skeleton_pilot_20261005_v1/standard_candidate_registry.json`中的两个完整人物及各自Skeleton、正式服装/发型Registry和现用覆盖Look计划；Family、鞋、发型性别许可与禁用规则仍由正式索引解释。人物Body、Tongue、Eyes、Teeth、Tearline、EyeOcclusion六部件保持完整；旧审查工具中的CombinedBase人物不能覆盖新人物。服装/发型Skeleton路径与新Body不同本身不构成失败或成功：必须核对真实骨集合/父子层级、逐骨记录参考平移/旋转/缩放差异，再核验LeaderPose实际绑定。当前旧服装虽骨层级匹配，仍有参考姿势差异；允许在本次隔离审查原型中试穿，不能由共有骨对齐推出静态合身或动态无穿模。新人物服装/发型视觉仍须人工检查。

本节唯一拥有以下四个入口及配套测试；实施阶段生命周期为`experimental`，收尾时由Script Catalog登记实际哈希与本节owner。`00_engine/scripts/unreal/complete_character_review_contract_v1.py`负责离线来源、服装/发型和现用动作目录；`00_engine/scripts/unreal/run_complete_character_wardrobe_hair_review_v1.py`负责控制面板、参数、锁与回执；`00_engine/scripts/unreal/open_complete_character_wardrobe_hair_review_v1.ps1`打开用户交互面板；`00_engine/scripts/unreal/ue_complete_character_wardrobe_hair_review_v1.py`负责新关卡、六部件/服装/发型槽、逐骨检查、视角与播放。`00_engine/scripts/unreal/tests/test_complete_character_review_contract_v1.py`拥有五项离线来源/规则测试；`00_engine/scripts/unreal/tests/test_complete_character_review_controller_v1.py`拥有回执路径/失败传播、精确编辑器选择、静止打开和无控制台错误持久化等18项控制器测试，实际`controller_pytest.xml`为18 passed/0 skipped。它们不能替代UE运行验证。控制器`panel_lifecycle.json`记录窗口创建、命令/关闭恢复及错误阶段；本轮实际stage ready/PID16168/error null，`panel_state.json`绑定同PID与默认静态首显配置。复用模块保持原所有权，不通过调用旧stage/show覆盖其硬编码关卡和人物。

独立关卡为`/Game/DataMake/Validation/CompleteCharacterWardrobeHair20261005/L_DM_CompleteCharacter_WardrobeHair_Review_v001`；与前序完整角色静态关卡分离。工作目录为`%LANCE_ROOT%`，用户入口是`powershell -File 00_engine/scripts/unreal/open_complete_character_wardrobe_hair_review_v1.ps1`，只连接已有UE；可选`-NodeId`明确会话。Python控制器接受`--action panel|show|view|playback|sample|audit|reload|restore|status`；选择参数为`--female-outfit`、`--male-outfit`、`--hair-index`、`--action-index`，视图参数为`--view front|side|back|threequarter`、`--focus both|female|male`、`--framing full|head`，播放参数为`--playing`/`--no-playing`，`--node-id`用于明确已有编辑器。动作0是静态；界面默认首套服装、HB1_02、双人全身正面、暂停。确切参数以代码为准，实际面板/CLI烟雾测试由本Run Root回执登记。

动作目录必须同时匹配现用Graph、Action Pool、历史成功导入/归一化Manifest及退休回执；每性别保留5条，共10条，已退休两条不得复用。代表身体动画仅使用曲线为空的已有BodyOnly来源，建立本关卡`Animations/Female|Male/A_CCWH_<动作>_v002`独立片段，不改原动画或人物Skeleton，不添加兼容Skeleton关系或面部层。源有108骨轨，但UE5.8该数据模型的legacy `get_bone_animation_tracks`曾返回空数组；早期v1副本未正确获得骨轨，保留诊断且不用于审查。v002用`AnimationLibrary.get_bone_poses_for_frame(..., False)`逐源帧取局部姿势，再通过Controller重建轨道、帧率和时长并比较源/目标。早期Audience回执采用`1e-4 cm / 0.05 deg / 1e-5 scale`阈值；现行实现采用`1e-3 cm / 0.05 deg / 1e-5 scale`预览重建阈值，各片段以自身报告中的`preview_limits`为准，不回写旧结果。这是受限预览的数值误差上限，不能作为正式重定向、任意Skeleton兼容或视觉自然度结论。

已有输出包括`entry_context.json`原关卡/相机、`protected_sources_before.json`保护基线、`current_case.json`当前装配/请求/逐骨差异、`animations/*_v002.json`来源与目标包SHA/局部轨道误差，以及`playback_motion_samples.json`、`playback_all_actions.json`动作与暂停采样。现用十条BodyOnly隔离片段均已实际播放，七个身体骨坐标确有变化，已采样Follower头骨世界坐标与Body在三样本中精确重合；暂停样本通过。代表多件服装切至裸身和服装禁发型清空已通过，早期切换hair20因额外发饰骨被旧严格检查拒绝，其失败保留；后续`copy_pose_motion_samples.json`已实际验证hair20/HB2_11、动作3、男女各三样本共有头骨误差小于7e-14 cm。`switch_and_reload_checks.json`16项通过，覆盖多件→裸身、禁发型、hair1/20/40/0/2、视角/人物/全身头部切换及保存重载；`saved_reload_readback.json`在重新装配前读取已保存绑定。`extra_bone_hair_checks.json`随后完成全部十款额外骨发型两性动作3，共有head误差<.001cm；`copy_pose_saved_reload_readback.json`完成重装前CopyPose裸保存绑定读回。用户桌面面板已ready，最终37项基线SHA保持；342必要回归通过。失败的v1片段、`last_error.json`与探针保留。`VAL-UE-02`验证本轮实际装配/切换和逐骨跟随；`VAL-UE-01`验证代表身体动作时间变化和暂停稳定；`VAL-DOC-01`负责文档与目录。界面交付完成不等于新人物服装/发型人工外观通过，人工结果单独保持pending，用户后续检查按实际范围记录。

额外发饰骨修复已取得代表运行证据：旧审计归档为`leader_only_partial_audit.json`，仅执行560/666网格，其中118失败，涉及10款发型男女各59个网格；旧假设要求Follower全部骨名都在Body中，错误拒绝有附加发饰骨的网格。现行最小修复在审查namespace创建`Followers/ABP_CCWH_CopyPose_<Skeleton哈希>`：有额外骨的发型走Copy Pose，匹配的身体骨复制Body姿势，额外骨保留导入参考姿势；其余Follower继续LeaderPose。共同骨父层级仍须一致，无共同身体骨或非有限参考变换仍停止。不改原Skeleton、不加入物理。新的`all_mesh_binding_audit.json`完成666/666网格（346衣物+320头发）共同骨映射/层级检查；118个含额外骨头发网格请求CopyPose路径，202网格参考姿势完全一致。此报告不等于666网格全部动态/视觉通过；代表HB2_11及全部十款额外骨发型已完成限定动作3共有头骨跟随，CopyPose裸重载已验。HB2_11花饰仍沿源`flower→pivot→jewelry_barrette_04→pelvis`绑定，未改为head；即使共有head一致也不能推出花饰视觉位置正确。`HB2_11_flower_attachment_observation.json`记录弯腰动作三个样本中花饰骨标记至head距离变化：女性约16.46cm、男性约1.53cm；这是骨标记观测，不是表面穿模或视觉接受。人工审查应特别观察hair20在弯腰/转身时花饰位置，后续修正须另按用户授权处理。

旧全网格检查累计SkeletonModifier可编辑几何描述，UE内存耗尽后退出；日志`ue_memory_exhaustion_log.txt`保留，root记录峰值约67GiB虚拟内存。崩溃后`protected_sources_after_crash.json`确认37个保护文件SHA均未改变。恢复进程PID15228曾停在“恢复包”窗口；用户现已处理，UE接口恢复，root明确override并重新绑定新node，旧阻塞解除。垃圾回收实际排队到帧末执行，worker限制每批count≤40、批末请求回收，再开始下一批，不能把同一帧循环中的GC调用视为立即释放。新的666网格审计已完成且未再OOM；`audit_memory_release.json`请求卸载654个仅审计加载包且`any_unloaded=true`、无错误，排除当前引用与脏包，仅释放内存，不保存或删除源文件。旧OOM日志与失败审计不改写。最终改动后`regression_pytest.xml`为342 passed/0失败/0跳过、89.956秒。`static_pose_reset_check.json`确认十动作→静态复位前后骨一致：动作0须同时`set_animation_asset(None)`并以`get_animation_asset()`读回，防止只暂停旧实例却仍显示动作姿势；修复后全十动作播放/暂停再次通过。`preview_front.png`由root实际查看为正确全身T Pose及衣服/发型；这不构成人工fit接受。交付汇总与操作说明为`review_delivery_summary.json`及`README.md`；`documentation_audit_final.json`实际16独立子系统与跨层全通过、0错误/0警告。最终源保护只覆盖`protected_sources_before/after.json`明确37项基线，不外推全666文件。

root串行操作共享UE；切换前检查脏地图并记录原关卡与相机，有未保存用户修改则停止，禁止自动保存或丢弃。只保存新独立关卡和明确的新动作/CopyPose副本；服装/发型切换清空本关卡闲置槽，不累积旧部件。出现来源漂移、共同骨父层级不匹配、非有限参考变换、Follower失败、保存失败、静止播放或残留禁用发型时，保留失败报告并停在该项；额外骨按上述独立CopyPose路径验证，参考姿势有限但不相同则明确记录为视觉待审，不覆盖正式源资产消除差异。恢复时只加载本次已保存关卡/来源与安全检查点，正常退出恢复临时播放/编辑器设置；不重导整库、不运行CC/面部或批量渲染。本轮没有删除授权。


#### 交付后人工反馈、模块规则与诊断（2026-10-05）

人工来源为父Run Root的human_review_feedback_v1.json与review_feedback_and_resolution_notes.md：男15/女23款发型，6款重叠均原许可both；其余许可不能自动加入用户未选性别池。女Rugged & Trendy、含YogaPants15套（71–85，非streetwear全34套）、男Kilt及赛博朋克面罩3为明确候选排除；cybmask是BundlePart01，须同步locked_bundle必需清单。高跟鞋和粗糙问题先诊断，不自动删除/剔除全部鞋服。后续user_feedback_addendum_v1.json明确男01–14/23近景粗糙、女89–92较好/93–95较粗，并要求先沿coat/pants合法槽位完善再新组合测试；前序材质取证男01/05/10/14/23仅代表子集；今晚335项UE元数据已扩展覆盖这些编号，视觉逐项接受仍未取得。外形分组仍pending，HB系列不是形状组。

[当前Plan](../../project_management/plans/active/PLAN-2026-10-COMPLETE-CHARACTER-WARDROBE-DIAGNOSIS.md)按用户优先级先确定可审查的模块化方案，再完善新Body固定组件，之后测试合法组合；本节拥有diagnostics_v1/下方案与诊断，仍沿用OUT-WF50-RUNTIME-ACCEPTANCE、unclassified保护。modular_assembly_spec_v1.md明确：基础Body/眼/牙/舌/泪线/眼遮挡6部件属于身份；同Actor衣柜继承3.6的UpperInner、UpperOuter、Bottom、FullBody、Footwear五语义槽，以及BundlePart01–10、HairPart01–17。pants/skirts共享Bottom，鞋自带/共享互斥，layer或不可拆套装选择规则与物理槽分开。合法性继续由canonical family/group/semantic slots/bundle约束，coat与pants同名并不允许跨family自由混搭。

前序方案诊断检查点（今晚实施前，保留历史边界）：旧v003固定32空槽使用旧M/F_BASE；当时完整人物stage使用分立SkeletalMeshActor附件，PID5620旧面板只作定位，尚未完成新Body固定槽迁移。今晚已实施的固定组件与迁移以上方真实回执为准，稳定配件跨组合切换仍待验证。鞋pose profile及匹配新Body拓扑的可逆遮挡仍未实现：遮挡规则需随衣服应用/取消并清除上一套规则，不删共享Body，不遮露趾等可见皮肤，不以body mask代替服装形状/蒙皮/鞋姿态适配；当前独立proposal没有新增这些runtime字段。

modular_assembly_candidate_registry_v1.json是独立proposal，SHA decd52f8c8e1b9a083a067776b4d1bc48bd0c20172324141d86e18071d33c115，未覆盖正式台账。modular_assembly_contract_check_v1.json success：39families、320family assets、43shared shoes、32hair；173旧witness排除17后156合法解析，男女15/23发型许可和deny保持，容量满足5+10+17。YogaPants A–F去除后四个pants_with_*组停用，不用别family裤子补空；streetwear连体/裙组保留，男赛博朋克去cybmask后余四件仍locked_bundle。此为离线选项/容量检查，不是全组合数、156视觉通过、稳定配件实现或新32槽运行时验收；该proposal本身formal_publication=false；今晚另行发布筛选版后的默认入口见本节前文，不能把独立proposal当发布产物。

根因初查由diagnostic_findings_v1.md汇总，精确输入归source_body_and_shoe_diagnosis_v1.json。旧男女裸体BASE为56,412控制点、新身体14,164；旧普通Anita dress与1920男西装导出Body数组分别等于旧裸BASE，单位/坐标轴一致。普通旧新参考最大差主要涉及头部支持骨，不能推出腰腿普遍厘米级差异；高跟鞋则有独立穿鞋姿态，High Heel B/Pump Heel A源pelvis相对裸BASE约+8.77/+11.27cm并改变脚姿态。当前裸足Body跟随缺少鞋要求的姿态/接地配置；这证明配置差距，不证明唯一穿模原因。该前序诊断时受控测试尚未做；后续同鞋静态A/B已完成，动态场景仍待，见本节高跟鞋受控验证补记。

body_geometry_snapshot_v1.json与body_geometry_point_comparison_v1.json为真实UE只读网格和单向最近顶点检查；女性105–135cm高度区最大约4.14mm、头部约25.28mm，但含细分采样差、不对应真实表面距离/有符号穿模，分区非解剖mask。每性5个穷举样本核对KD树，SciPy/NumPy不兼容未改环境。R01仅关闭有界来源/形状初查，代表服装在新身体上的真实贴合仍待。

前序代表质量线索独立保留：material_quality_snapshot_v1.json读21衣物、36材质、96含继承默认项的UE纹理元数据；texture_source_comparison_v1.json核对4组/16材质/36真实源图，实际exports来源优先于旧缓存路径失效的source_texture_headers_v1.json。男01是2048整套共享图集、有效衣物像素受限；男23源主要1024且未导出法线，不是UE漏绑；女89源4608/5376且有法线，女93虽5376仍无源法线，不能以尺寸单独解释观感。代表源/导入尺寸一致、LODBias/MaxTextureSize为0，不能证明实时streaming无降级：actual resident mip未测。材质/有效纹素与法线粗糙度线索支持针对小样，不支持统一细分网格或全库重导。

前序诊断收尾记录（今晚授权前）：R00方案/离线合法性、R01限定初查与R04本轮诊断报告完成；当时R02/R03进行中，R05/R06尚未实施。feedback_regression_pytest_v1.xml为342 passed/0 skipped、28.64秒，仅离线必要回归，不含新槽位运行时；feedback_documentation_audit_v1.json记录该轮owner更新后结果，不继承旧交付审计。今晚R07已发布、R05/R06实施进展以上方回执及当前Plan为准，CC/重导/正式源修复与另一会话native_geometry仍不纳入。

## 4. 运行时检查

对每个生产 Look 至少检查：

1. Skeletal Mesh、Skeleton 和 Physics/Facial 支持可加载；
2. 材质槽不丢失，脸/身体接缝和肤色一致；
3. 眼睛、牙齿、睫毛、眉毛、头发、胡须可见且位置正确；
4. 动作播放时不进入 T-pose；
5. 面部曲线不与 Auto Setup Post Process 重复求值；
6. Wrapper/Sequence 引用的是当前批准 Look，而不是历史 Pilot。

## 5. 已知限制

- 烘焙服装可能在特定动作下出现局部穿模；第一批按已记录风险接受，不等同于通用兼容。
- 已审查的服装禁发型规则已由正式索引和 v003 编辑器读取器执行；新身份、未覆盖头型和动态穿模仍需另建验证范围，不能把默认 allow_all 当成视觉结论。
- 身体 Morph 在 UE 运行时变化会破坏烘焙服装适配，因此第一批不启用体型编辑。
- Headshot、年龄和可替换发型尚未进入第一批生产 Look。
- 模块化服装 Pilot 当前只覆盖男女平均体型；极端体型需要独立服装网格和完整 Gate。

## 6. 输出与恢复

构建/验证报告进入 `%OUTPUT_ROOT%/unreal_character_import/`，其中聚合 Gate 和人工决定为 `retained_evidence`，一次性舞台 Actor、临时关卡和诊断资产为 `disposable`。崩溃后先审计脏包、临时 Actor 和资产路径，再继续；不要直接保存未知自动恢复内容。

当前保留的 Day-2 运行时证据为 `%OUTPUT_ROOT%/unreal_character_import/first_batch_day2_20260822_v1/`，其策略前缀是 `unreal_character_import/first_batch_day2_20260822_v1`；被替代大媒体按精确替代清单收敛，保留报告和有效视觉替代证据。

模块化服装 Pilot 的共享分类、v001 证据和 v002 Plan 位于 `%OUTPUT_ROOT%/unreal_character_import/modular_outfit_pilot_20260829_v1/`；v002 构建、切换和复核关卡报告位于其 `runtime_v2/` 子目录。CC 侧 14-Case 证据见 [模块化服装 Transfer](../transfer/CC_TO_UE_MODULAR_OUTFIT_PILOT.md#5-历史-cc-执行证据)。该证据作为 `retained_evidence` 保留，但不能冒充第一批生产资产。


## 3.14 CFD原生男女双人测试入口（2026-10-06）

本节唯一拥有`%LANCE_ROOT%/00_engine/scripts/unreal/ue_cfd_native_pair_review_v1.py`与`run_cfd_native_pair_review_v1.py`，生产`%OUTPUT_ROOT%/unreal_character_import/cfd_native_pair_20261006_v1/runtime/`，归OUT-WF50-RUNTIME-ACCEPTANCE；来源/完整转移由Transfer13拥有。新worker/panel为validated_pilot，仅两个新CFD成品的独立关卡/限定切换/保存重载与面板交付，不是任意身份/全服装组合/全动画生产接受。

复用现有中文固定槽位界面，正式服装/发型/CopyPose源只读，新角色BP与动作副本留在`/Game/DataMake/Validation/CFDNativePair20261006/`，审查关卡`L_DM_CFDNativePair_Review_v001`。运行前按Transfer13核对ue_target当前用户Macheniek、node3FEB46014AA22FBCA2E4DDBAAF7440B4、PID12840，拒绝静默选择其他实例。

```powershell
python 00_engine/scripts/unreal/run_cfd_native_pair_review_v1.py
```

原入口交付时root在用户桌面打开控制面板PID4720，runtime/panel_lifecycle曾为ready/errornull；最新该面板closed/restore_success=true，当前实际场景以本节N简单读回为准。界面仍为“完整角色·按部件选择衣服和发型”，可选择合法服装/鞋/发型及身体动作和视角。当前action0/停止/front/hair2状态保存成功。action1停止状态、hair1及三分之四视角绑定机器通过，root实际看到两人穿衣抬手；当时仅机器交付；随后用户已直接确认本次双人验证成功，runtime/user_final_validation_v1.json为人工依据，仍不细分捏造连续播放、面部目标或全组合检查。

证据：runtime/stage_report、runner/preflight/reopened_saved_stage_remote、runtime/replies/b274602b11cf47309a7fd47d05fde97d及d980b61d249e4c31803ce27a3db1727e、panel_lifecycle。误Alt+F4关闭旧编辑器的操作历史/新桌面启动保留于execution_record.visible_editor_recovery及reopen_visible_editor；新关卡/男女Actor/dirty_maps0已在恢复编辑器实际读回，旧target另存。当前双人试点人工通过，R05 completed，runtime/user_final_validation_v1.json记录用户原话/绑定SHA；后续批量待用户明确启动，鞋脚姿/可逆遮挡等既有问题不由该入口自动修复。导入仍需交互AutoSetup+FBX窗口确认，无无人值守batch承诺，不自动进入正式人物批量。


### 最新CFD角色的简单核查与高跟鞋候选验证（2026-10-06）

本节拥有`%OUTPUT_ROOT%/unreal_character_import/cfd_native_pair_20261006_v1/runtime/heel_validation_20261006_v1/`（文中N），沿用`OUT-WF50-RUNTIME-ACCEPTANCE`/`unclassified`保护；原3.14双人worker/panel的validated_pilot范围保持，N新增工具均为experimental，不由本轮升级或泛化。

用户已在本聊天直接确认新导入两角色的服装、身体动作等表现与此前角色一致，并授权root先简单检查新关卡后继续UE工作。N/native_pair_user_acceptance_v1.json独立记录原话与观察范围，不替换另一会话runtime/user_final_validation_v1.json或其未来批量就绪结论；本轮不新增batch执行许可。

简单只读检查N/native_pair_simple_readback_v1.json通过：男女各38个固定组件，新Body/Skeleton、六基础部件、材质与跟随正常，无源资产/场景修改。面板PID4720已closed且restore_success=true，current_case action5是最后选择而非恢复后的实际场景权威；首次按旧case进行status检查失败保持，不归作资产坏。实际场景读回单独成功。 该最新简单读回sources.registry为正式v2 SHA 42bea3d643cff65734efa21b7ed9282ae654cd49365346bd327ac284277d1f24，不继承旧H warm-loaded-v1作为新角色的来源权威；源完整导入与独立接受仍归Transfer13及原3.14范围。

使用最新CFD原生女性及其真实Body参考，native_heel_reference_v1.json和static_heel_pose_ab_20261006T050542_728d5231.json完成独立参考读取及新Skeleton静态A/B构建。F015四骨姿势B叠加临时人物高度+9.695503cm后，captures/20261006T051401_0a52bfd0完成六张正/背/侧图，实际变形左右鞋整体最低点距地约0/0.03033cm。只证明此人此鞋静态候选；没有分别标定鞋跟与前掌，不是完整接地/穿模修复或全鞋参数。该高度不能代替动作支撑期接地，正式配置未接入。

Audience动态A/B在t=0/2.2667/4.5秒三个暂停时刻采集12图，captures/20261006T051915_c9628558完成并恢复，保护包与源动画未改。B左右鞋最低点距地分别约9.6898/7.7329、1.8751/0.5870、8.8551/6.9828cm，固定静态高度不能维持动作中的接地；原A动作自身pelvis/feet有约9–13cm上下运动，不能全部归咎鞋姿或强行连续脚锁。动态独立v1比较用静态0.001cm位置门限拒绝约0.05mm量级求值差，失败保持。dynamic_native_contact_comparison_v2.json已独立核验三个暂停时刻的数值诊断通过：原raw模型门限保持，运行时component位置允许0.01cm、四脚骨局部平移0.001cm、上游旋转0.05°、完整干预四元数关系0.15°。实际最大component位置差0.005421cm、局部平移差约2.7e-14cm、完整四元数关系误差0.08704°；这不是逐bit一致或接地通过，压缩/求值误差来源未独立证明。

完整fixture恢复fixture_restore_d97ef0cba7.json成功，实际原场景指纹和动画/tick等flags恢复；没有保存新鞋姿/高度到正式关卡或源资产。R02/R05/R06不关闭，鞋底整体最低点不是单独标注鞋跟/前掌接触点或鞋内穿模深度。 实际测量来自RENDER_DATA LOD0的5882个已变形顶点；SOURCE_MODEL对此跟随组件提取失败保留，不以包围盒代替接触测量。离地可能属于动作设计的抬脚/弹跳，必须先判定支撑期与离地期，不能把每个正距地数都判作错误或强制双脚锁地。连续播放、步行及全库鞋配置仍待。

N全部新增脚本生命周期为experimental，准确入口为`compare_native_dynamic_heel_capture_v1.py`、`compare_native_dynamic_heel_capture_v2.py`、`compare_native_static_heel_capture_v1.py`、`native_heel_fixture_v1.py`、`prepare_native_heel_ab_v1.py`、`read_native_heel_reference_v1.py`、`read_native_pair_smoke_v1.py`、`run_native_heel_payload_v1.py`、`test_native_dynamic_comparison_v2.py`、`test_native_dynamic_heel_adapters_v1.py`、`test_native_heel_adapters_v1.py`、`ue_capture_native_contact_v1.py`、`ue_capture_native_dynamic_heel_ab_v1.py`、`ue_capture_native_heel_ab_v1.py`。read_native_pair_smoke_v1.py读取实际组件/材质/跟随，read_native_heel_reference_v1.py读取新Body与鞋自身参考，prepare_native_heel_ab_v1.py生成独立A/B；native_heel_fixture_v1.py快照/限定临时设置/恢复，run_native_heel_payload_v1.py由root钉住编辑器串行派发。static/contact/dynamic capture与compare仅拥有限定采集/变形鞋最低点和独立比较，test仅验证对应离线边界。实际原Pose、鞋网格、骨架、材质、标准源及其他会话CC工作保持。

本节拥有N/native_heel_findings_v1.json/.md汇总、native_pair_user_acceptance_v1.json、简单检查/静态/动态数值结果与恢复证据。后续新结果以新版本登记，不倒写v1失败。先分离原Audience动作自身抬脚/弹跳与鞋姿偏置对接地的贡献，再选择平稳站立及步行动作，建立鞋姿与支撑期接地的受控小样。新CFD女角色F015静态高度只是候选，正式鞋配置/新Body遮挡仍待；保持R02/R05/R06进行中，不重导、不实际改材质或几何。 N/native_final_regression_v1.xml已实际完成16项新增native工具离线测试，0失败/错误/跳过；本轮required_regression_v1.xml实际523项通过、0失败/跳过；documentation_audit_final_v1.json记录最终16个独立子系统及跨层检查，0错误/警告。Catalog/Inventory已重建，不继承旧523项结果。N/dynamic_comparison_diagnosis_v1.md保存v1失败与v2独立诊断的精确差别，属于Runtime3.14实验输出，不是新的接地接受。


## 3.15 CFD原生40人简单审查关卡（2026-10-06）

本节生产`%OUTPUT_ROOT%/unreal_character_import/cfd_native_batch40_20261006_v1/runtime/`，归OUT-WF50-RUNTIME-ACCEPTANCE；完整转移与R00同性交享Skeleton小样由Transfer14拥有，创建BodyFit11.5。审查设计为5页每页8人，男女两排各按A/B/L/W四列各1，支持focus；布局/控制脚本/新关卡已实际机器交付，R05五页显示和代表控制检查通过，后续用户有限静态审查已通过，见§3.15.3；其他未观察范围不扩。

当前R00代表门禁已按shared_representative_acceptance_v1.json有限root_visual_smoke接受，双方设置保存/读回历史保持。CFD40创建、完整导出、完整UE导入及R05五页静态审查机器交付均已完成；整批静态可见外观已有用户有限接受；最终渲染与全动画/服装接受仍pending。最终控制器43488与79508正常退出，AutoSave已恢复原True，monitor已确认停止、automation PAUSED。GPU崩溃、包卸载和受控hold均为下述历史恢复证据，不删除资产或故障报告。Computer Use仅获准确认导入弹窗、用完停止；本轮已无活动导入。另一会话主计划、旧关卡及规范源保持；当前真值由execution_record与review_pages_verification拥有。


历史检查点（发生于双方保存与shared_representative_acceptance之前，不能作当前R00状态）：当时R00检查点仅共享probe男女导入/完整性machinepassed，身份mesh参考、canonical包SHA/shared Skeleton参考保持；身体动作/眨眼/微笑root实际可见；jaw轴修正v2已可见张嘴，但模板平移导致眼牙偏移，待新共享面部子树TranslationRetargeting=Skeleton。PythonBoneTree只读/两次apply未改，male用户已保存且10面部Skeleton模式/中性眼牙对native参考复核；female已打开并请求同样保存，回复及最终视觉待；R00保持partial而非通过。精确证据归Transfer14/probe Run，40人仍prepared/0创建，审查5页×8人布局未交付。

§3.15唯一拥有`ue_cfd_native_batch40_review_v1.py`与`run_cfd_native_batch40_review_v1.py`；5页×8人入口已完成本批次实际机器交付，仍保持experimental而非通用生产入口；当前机器接受归review_pages_verification，不从旧pair接受推导新40人视觉通过。

### 3.15.1 单关卡翻页前释放已保存角色包（代码与五页机器验证）

ue_cfd_native_batch40_review_v1.load_page先preflight(request)解析registry角色/来源及路径，不加载下一页网格；清当前槽位绑定与compatibility缓存，再对old_ids-new_ids调用Transfer14的release_saved_case_packages，finally重核共享baseline，通过后prepare才加载新页8人。保留单关卡5页×8及focus语义；重叠角色不卸载，不增加多关卡资产。release的spec/id/audited/dirty前缀边界由Transfer14拥有。15focused由实现agent通过，随后本轮documentation/dataset/unreal所需代码回归实际548全部通过（Run内release_review_required_regression_20261007.xml/.txt，0失败/错误/跳过）。随后review_pages_verification_v1.json已实际完成五页换页机器检查；代码测试和实际静态换页均不代替最终渲染或整批人工接受。

### 3.15.2 五页机器交付与用户复现入口

本节拥有Run内review_pages_verification_v1.json、runtime/current_case.json、USER_REVIEW_QUICKSTART.md及保留旧DRAFT。实际pages2/3/4/5/1各显示8人、并集40unique等于完整registry；每页上男下女、各A/B/L/W。代表page1 focus1/side/head/nohair显示1人通过；最终page1 all/front/full/hair/saveTrue成功并保存单关卡L_DM_CFDNativeBatch40_Review_v001，磁盘229,410字节、14:17:26保存，79508退出0。不由这些机器记录外推背面已专门审查、完整动作或用户视觉接受。

PowerShell入口：`& "C:\ProgramData\anaconda3\python.exe" "D:\UE\Lance_Work\00_engine\scripts\unreal\run_cfd_native_batch40_review_v1.py" --action panel`。五页8人、focus1–8、front/side/back、full/head及hair开关保持。当前绑定32420仅代表本次实例；若UE重启，先核对PID/user/project/node并更新Run内ue_target再使用面板，旧连接不能自动沿用。完整简洁说明见USER_REVIEW_QUICKSTART.md。AutoSave已恢复原True、monitor停止/automation PAUSED；human_acceptance后续已由§3.15.3有限静态回执更新，原机器pending为历史。

### 3.15.3 用户有限静态审查

用户已完成CFD40静态人工审查，未见明显问题，男性和女性身份面部差异均可见；女性主观变化较小，后续进入照片形态选样分析与CC多样性候选研究。该结论只接受实际观察的静态外观，不扩为全部动画、服装组合、隐藏面或最终渲染验收。直接结论回执为本Run runtime/user_static_review_20261007_v1.json；原machine报告里的human pending保留为当时历史。
本节拥有该用户回执，独立照片分析由BodyFit §12拥有；不借此次静态结论关闭另一会话动作/服装诊断或推断全池通过。


## 3.16 CFD40双人分离槽位审查（2026-10-07）

本节拥有`%OUTPUT_ROOT%/unreal_character_import/cfd_native_batch40_20261006_v1/runtime/modular_review_20261007_v1/`，适用WF-50、VAL-UE-01/VAL-UE-02的限定运行时绑定与切换范围，输出契约OUT-WF50-RUNTIME-ACCEPTANCE，retention=unclassified并保持保护。40人创建、完整导出/导入及同性共享Skeleton权威仍归Transfer14，旧5页×8静态入口和其有限人工反馈仍归§3.15。本节只消费已有40人成品，按用户纠正以双人分离槽位界面替代本轮静态分页交付；不是第二个current计划或新批量创建/导入任务。

### 3.16.1 身份、服装、发型和动作的组合边界

新关卡为`/Game/DataMake/Validation/CFDNativeBatch4020261006/L_DM_CFDNativeBatch40_ModularReview_v001`。复制原男女固定槽位Blueprint到独立namespace，场景始终为一女一男，每人保留38个固定组件：六基础部件、五语义服装槽、十bundle槽、十七发型槽。身份从对应性别20人中选择，六基础网格共同替换，继续使用本批对应同性共享Skeleton；Body驱动原跟随体系，额外骨发型复用CopyPose，不能混用男女性Skeleton。衣服和发型仍受canonical family/group、locked_bundle、用户性别白名单及deny约束，不允许任意跨family组合。

`character_ids`明确female/male两身份，`character_registry_sha256`绑定`imported_character_registry.json`。契约复核每身份六角色网格、导入audit路径/SHA/bytes、来源namespace和同性共享Skeleton；服装来源继续核验当前reviewed_pool_v2发布链，SHA为42bea3d643cff65734efa21b7ed9282ae654cd49365346bd327ac284277d1f24。选择角色只改变身份，保留服装、发型、动作、播放及视角选择；身份改变后先点“显示当前搭配”，再进行播放/视角等操作，队列拒绝用未加载的新身份直接发非show命令。

事务快照包含六基础部件，失败时先恢复Body再恢复其余原快照。成功命令返回且旧引用释放后，仅卸载已离开的已保存角色包，当前身份和重叠身份保留；释放及脏包保护仍调用Transfer14原有边界，不删除磁盘资产。独立Blueprint复制过程中UE曾返回同一对象两次handle：实现按真实对象path去重，再核对38个唯一固定组件；不能仅按名称丢弃不同对象。旧失败、有限恢复授权和用过的恢复回执均保留。旧规范、网格、材质、Skeleton、分页关卡和另会话CC产物不覆盖。

### 3.16.2 入口、生命周期与输出所有权

本节拥有`00_engine/scripts/unreal/cfd_native_batch40_modular_contract_v1.py`、`run_cfd_native_batch40_modular_review_v1.py`、`ue_cfd_native_batch40_modular_review_v1.py`，生命周期均为experimental；离线测试`tests/test_cfd_native_batch40_modular_review_v1.py`和`tests/test_cfd_native_batch40_modular_worker_v1.py`为utility，归本Technical owner。Run内`validate_modular_runtime_v1.py`亦为experimental，只在root已审阅schedule、stage通过并串行占有UE时使用`--execute`；默认只输出离线计划，不启动UE。候选实现和机器通过不晋升通用生产入口。

PowerShell入口（stage已完成后供root交付面板）：

```powershell
& "C:\ProgramData\anaconda3\python.exe" "D:\UE\Lance_Work\00_engine\scripts\unreal\run_cfd_native_batch40_modular_review_v1.py" --action panel
```

`--stage`只搭建独立关卡后退出；`--female-character`、`--male-character`选择已导入身份，其他继承服装preset/hair、action-index/playing、front/side/back/threequarter、both/female/male及full/head/torso/legs/feet控制。`--request-file`需要完整请求且绑定两个registry版本，`--save`只保存独立审查关卡。UE重启后必须按Transfer14重新核验/绑定ue_target的PID、project、user、node，不能沿用旧实例。

本节生产stage_result.json、entry_context.json、selected_sources、current_case.json、controller和replies、派生animations、panel_state/panel_lifecycle、backend_validation下不可变schedule/每步回执/manifest，以及后续交付说明/回归/文档审计。stage_result.json已实际success=true并保存新关卡；backend_validation/20261007T101347Z_114e8b2a/manifest.json实际completed/success=true，42/42步通过：20对覆盖40身份、六基础部件及固定组件稳定、同性十条身体动作播放/暂停、男女两实时采样、分体/整身与配件清除、发型切换/额外骨以及保存重载；重载后先inspection_before_reassembly读回通过，不靠重新组装掩盖保存缺失。 新面板PID44124已实际ready且error=null，并进入用户实际交互；当前身份/视角会随用户操作变化，不能把42步结束的AF001/AM001、F89/M23、hair2静态front/full写成永久当前状态。该组合仅为机器验证结束时已保存/重载的历史证据。用户在本聊天直接说“现在审查完毕一切正常，我们下一步还需要做什么？”；新独立human_review_acceptance_v1.json绑定本次42步manifest和delivery SHA。R11已completed，接受限定其实际审查的双人槽位界面及身份/服装/发型/身体动作表现，不捏造每组合点击记录，不扩大到全组合逐帧、高跟鞋修复或自然面部动画完成。原机器回执里的pending原字节保留为交付当时历史。 目标画面之外的早期helper截图不作为视觉通过证据。 不能用旧分页用户静态接受代签。

当前下一步：先修改女性共享鞋选择规则并离线核验男性规则未变，由root创建男女发型分类审查关卡；发色和虹膜颜色小样独立并行。收到用户视觉分类前不写发型组配置；本轮停止鞋姿优化/高跟鞋修复，面部动画、身体动作与场景扩充延后，不实际改善服装材质。

本轮机器范围只验证实际槽位、身份、来源与动画驱动；十条动作绑定/播放暂停不等于全帧服装贴合接受。女实时采样position发生loop wrap，按骨位实际变化证明推进，不把position变小误判倒放；鞋接地/新Body遮挡没有因本界面而修正。底层继承的human_review_R10 pending标签仅为工具待人审字段，本计划旧R10已完成的真实反馈不重开，新界面人工状态由R11及本scope独立维护。

root必要documentation/dataset/unreal全目录回归实际577 passed、0失败/0跳过，120.70秒，执行session27930 exit0/stdout；本轮未保存独立JUnit文件，不虚构报告路径，不继承此前548/575结果。本轮Catalog与Output Inventory已重建，独立文档子系统及跨层审计全部通过，0错误、0警告；审计回执为本节输出根documentation_audit.json。

### 3.16.3 用户有限人工接受与本次验收复核

用户在本聊天直接说“现在审查完毕一切正常，我们下一步还需要做什么？”；新独立human_review_acceptance_v1.json绑定本次42步manifest和delivery SHA。R11已completed，接受限定其实际审查的双人槽位界面及身份/服装/发型/身体动作表现，不捏造每组合点击记录，不扩大到全组合逐帧、高跟鞋修复或自然面部动画完成。原机器回执里的pending原字节保留为交付当时历史。

本节拥有human_review_acceptance_v1.json及本次human_acceptance_regression_20261007_v1.xml/.txt、human_acceptance_documentation_audit_v1.json。原42步manifest、delivery_verification和documentation_audit.json保持原字节；本次只更新文档与独立接受回执，不操作UE或修改源资产。本次人工接受后的独立复核已完成：human_acceptance_regression_20261007_v1.xml/.txt实际577 passed、0失败/错误/跳过，50.54秒；Catalog 620脚本与Output Inventory 136范围已重建，human_acceptance_documentation_audit_v1.json实际16个独立子系统及跨层通过，0错误/0警告。本次结果与此前交付577/120.70秒回执分开，不覆盖原文件。

## 3.17 女性共享鞋、发型分类与颜色实验（2026-10-07）

**前序阶段已结项：v5男女直接筛选及v3最终发色已获用户接受；新授权橙、金、银白改良见§3.17.6。**男性原36/40、女性原06/10/15仅退出对应性别，其余直接使用；不再分组，眼色不采用。旧R12–R14均完成，接受证据见§3.17.5，不将旧结果外推为新颜色通过。下文v4鞋索引/v2色板及分类、眼色待评价记录均属前序过程。

本节拥有唯一current计划R12–R14的实现、发布与证据。Run Root为`%OUTPUT_ROOT%/unreal_character_import/female_shared_shoes_hair_color_20261007_v1/`（下称N），适用WF-50与OUT-WF50-RUNTIME-ACCEPTANCE。N默认unclassified保护；shoe_publication精确子范围为retained_evidence，因为当前选择权威依赖发布SHA链。旧Runtime3.13/3.14鞋姿实验与§3.16人工接受保持历史；鞋姿优化/高跟鞋修复已被用户新策略取代，不能写成已修复或自动恢复。面部动画、身体动作/场景扩充、服装材质改善均不在本轮。

交付总入口为N/delivery_manifest_v1.json，绑定本轮发布、鞋切换、发型分页、头部遮罩/颜色保存重载及独立panel_delivery_snapshot_v1.json的SHA。交付快照记录PID28624、ready、error=null；root实际看过女性第1页原色六头与完整面板，已可交用户操作。日后panel_lifecycle/current_case随用户操作变化，不能代替该固定交付凭证，也不能将root界面检查当作用户分组或颜色自然度接受。

### 3.17.1 v4鞋策略与发布来源

精确保留范围为`%OUTPUT_ROOT%/unreal_character_import/female_shared_shoes_hair_color_20261007_v1/shoe_publication/`，本节为其生产与维护所有者。v3/v4发布SHA链在明确接受替代链前必须保留；这不授权清理源资产或同根其他实验输出。

鞋策略来源索引为`repo://00_engine/assets/character_creator/wardrobe_registry_ue_v4_reviewed_pool_20261007_v4.json`，SHA `e000b7e71768f653ffbc34f78186ef201373c3f0542f5730e0a155b8fff8262a`，凭证为N/shoe_publication/publication_manifest_v4.json；当前v5完整继承这些服装/鞋规则。`formal_wardrobe_registry_v1.py`验证当前发布链，失败明确报错，不退回被排除的旧池。v2与中间v3原文件/证据保持；v3曾强制配鞋，由v4恢复用户补充的原赤脚许可，不作为当前规则。

女性所有family自带鞋退出候选；穿鞋时，所有女性合法组统一使用F001–F005、F022–F025，不按family分池。F006–F021不可选。保留原13个可无鞋组，原4个必穿组仍必穿（pretty_dresses的pants/skirts，dress_collection的full_body/shirt_with_skirt），不新增赤脚权限。男性鞋、family/preset及头发选择规则保持；服装其他槽仍受canonical family/group、bundle约束。仅改选择，不删除网格或修改源材质、蒙皮、鞋姿。

N/shoe_publication的feedback_v4、mapping_report_v4、selection_validation_v4与protected_sources_report_v4由manifest绑定SHA；离线覆盖17女性合法组×9鞋及13个赤脚组，保留79女/73男历史见证。它证明选择和保护规则，不代表全组合UE几何/视觉通过。女性共享鞋v4发布与限定UE切换已完成，R12 completed。shoe_publication/runtime_checks_v4.json及footwear_binding_assertions_v4.json确认pretty_dresses/pants使用F025、african_casual/full_body从F001切到无鞋，实际Footwear路径/owner及空槽清除正确、男性保持；必穿组无鞋在UE执行前被拒绝。只证明这些代表绑定与清除，不是全组合几何测试。用户原已说明保留鞋池与服装兼容。

### 3.17.2 发型分类关卡与颜色小样

独立关卡为`/Game/DataMake/Validation/HairGroupColor20261007/L_DM_HairGroupColor_Review_v001`。男女分别显示原保留编号，每页6款（末页按余数）、单款放大、正/侧/背/斜前视角；每个性别使用同一已导入CFD参考身份以减少对比干扰。Body及眼牙等六部件复用既有绑定，发型按真实额外骨选择LeaderPose/CopyPose，组件override使用本关卡独立透明遮罩隐藏非头部材质，保存重载仍生效；不依赖不可持久的临时section状态，不修改源网格。用户分别给男女外形分组后才写正式配置；面板临时分类笔记不是正式分组，不按HB编号自动猜组。

`hair_review/color_capabilities.json`只含hair/eye候选数组：发色original/black/brown，虹膜original/brown/blue/green。`color_experiment/material_parameters_v1.json`是实际材质参数只读探查；完整适用边界另存color_capabilities_scope_v1.json。发色使用Base Color Tint乘色；black表示压暗，原贴图暖色可能残留，并非重新染成纯黑。保留Activate Hair Color原开关，不承诺把烘焙深发自然变浅，当前不提供金/灰色。虹膜实际调整Cornea_R/L的Iris Color，Std_Eye与皮肤等保持。

`hair_eye_color_runtime_v1.py`只生成本关卡ColorExperiments下派生MIC，继承源实例的贴图和静态开关，以组件override绑定；original清除override恢复来源。每实例所有者/输入SHA/单vector读回必须一致，异常恢复组件绑定；不调用源网格set_material，不保存源材质。参数可读写不等于自然视觉效果，用户颜色接受始终单独记录。

### 3.17.3 脚本、入口与输出归属

颜色切换补修（2026-10-07）：用户在女性第2页选择棕发/绿眼时触发错误，原因是保护检查把材质来源全部当作项目`/Game`包，遇到饰品父材质`/InterchangeAssets/Materials/FBXLegacyPhongSurfaceMaterial`即拒绝。`hair_eye_color_runtime_v1.py`现按真实`/Game`、`/Engine`、`/InterchangeAssets`内容根解析保护文件，脏包检查仍保留原mount名；未知路径及越界仍拒绝，插件饰品维持原色，不因此扩大改色目标。

N/color_experiment/plugin_material_fix_20261007_v1/manifest.json已实际success，绑定7页女23/男15全部性别发型项的棕发/绿眼成功回执及SHA，源保护保持；原失败请求女性第2页已成功恢复并保存。面板重启后PID17532、ready、error=null，root实际确认六编号9/10/11/14/15/16及棕发/绿眼选择正确。该结果补充此前只用原色覆盖所有页面的检查，不倒写旧交付凭证，也不代替用户的发型分组和颜色自然度接受。新增路径和原mount脏包回滚检查已纳入完整回归：619项通过、0失败/0跳过，181.21秒；同一补修目录regression.xml/.txt留存。Catalog和Inventory已重建，同目录documentation_audit.json独立子系统与跨层审计均通过、0错误/0警告。

本节拥有`00_engine/scripts/unreal/`下`build_reviewed_wardrobe_pool_registry_v3.py`、`build_reviewed_wardrobe_pool_registry_v4.py`、`hair_group_color_review_contract_v1.py`、`run_hair_group_color_review_v1.py`、`ue_hair_group_color_review_v1.py`和`hair_eye_color_runtime_v1.py`，生命周期experimental。v3为当前v4来源链的可复现历史发布器，不能当默认入口。`tests/test_reviewed_wardrobe_pool_registry_v3.py`、`tests/test_reviewed_wardrobe_pool_registry_v4.py`、`tests/test_hair_group_color_review_v1.py`与`tests/test_hair_eye_color_runtime_v1.py`为utility。既有`formal_wardrobe_registry_v1.py`、`complete_character_slot_review_contract_v1.py`和`run_complete_character_slot_review_v1.py`的本轮规则接入归本节，原通用槽位/历史入口仍由§3.13说明。

```powershell
python 00_engine/scripts/unreal/run_hair_group_color_review_v1.py --action catalog
python 00_engine/scripts/unreal/run_hair_group_color_review_v1.py --action show --sex female --page 1 --focus all --view front --hair-color original --eye-color original --save
python 00_engine/scripts/unreal/run_hair_group_color_review_v1.py --action panel
```

UE写操作由root串行。N/ue_target.json绑定当前节点、project/user/PID，重启后重新核验，不复用旧实例；session/identity_probe.json只记录相应会话。面板锁定选择来源SHA，来源变更需重新打开；队列串行执行，关闭面板不关闭UE或擅自切回旧关卡。

本节精确拥有N下：shoe_publication发布链；hair_review的来源、current_case、entry_context、controller/replies、颜色候选、panel_state/panel_lifecycle及分类笔记；color_experiment的只读探查、派生颜色检查与保护/恢复回执；session实例探查与日志；后续限定backend验证、人工反馈、交付说明、回归与文档审计。N内`color_experiment/probe_material_parameters_v1.py`为本轮只读实验脚本、`documentation_sync_scope_v1.py`、`documentation_bounded_update_v1.py`与`documentation_delivery_update_v1.py`为一次性文档同步工具，属于输出证据，不在代码Catalog扫描范围，不是正式生产入口。

当前发布与离线规则检查已通过。hair_review/bounded_checks_v1.json已记录12次成功调用：7页覆盖女23/男15款，末页单款背面/侧面以及男女代表发色/虹膜切换。每次绑定独立display回执；该检查证明请求与实际加载对应，不等于全部发型动态或颜色自然度接受。color_experiment/save_reload_v1.json实际读回保存关卡中7个颜色绑定，源hash不变；hair_review/head_framing_reload_v1.json确认六位置组件透明遮罩保存重开后仍生效。仅靠临时section隐藏不能持久的问题已改为独立组件材质遮罩，源网格/材质不改。hair_review/panel_lifecycle.json已记录PID28624、stage=ready、error=null，面板可供用户开始分类与试色；这不是用户已接受分组或颜色自然度。用户男女分类/颜色评价仍pending。最终交付状态由WF-50 Status与本轮实际回执拥有。男女发型分类、正式组配置和用户颜色效果接受仍pending；不得由关卡存在或参数写入提前关闭R13/R14。

前序限定机器结果支持R12完成与当时R13/R14界面/颜色实验交付；该交付当时的用户分类与颜色等待后来由下节新决定取代。最终Catalog/Inventory、全回归与文档审计由root在代码冻结后统一执行，不能继承预交付审计或旧577回归作为本轮最终结果。

### 3.17.4 v5直接筛选与丰富发色

本节记录v2色板交付时状态；后续用户接受及缩减为8色＋原色的最终配置见§3.17.5，旧v2全部证据保持原字节。

当前默认机器索引为`repo://00_engine/assets/character_creator/wardrobe_registry_ue_v4_reviewed_pool_20261007_v5.json`，SHA `3dfee9e4994d0c79ac93fc7ee934645d06c4e73ad969cd311afbed4bbee0ddd7`（准确SHA以发布manifest为准）。发布凭证是N/hair_palette_v2_20261007/publication/publication_manifest_v5.json，绑定feedback、mapping、selection及source-protection报告。男原36/40、女原06/10/15退出对应性别，保留男13/女20，共28个发型，重叠5款；女06对应发型仍保留男性许可。原编号不重新排列，女新第一页为1/2/3/5/8/9。衣服及鞋完整继承v4，禁止为用户取消分组再生成形状组配置。

本节新增拥有`00_engine/scripts/unreal/build_reviewed_wardrobe_pool_registry_v5.py`（experimental）和`tests/test_reviewed_wardrobe_pool_registry_v5.py`（utility）。精确保留范围`%OUTPUT_ROOT%/unreal_character_import/female_shared_shoes_hair_color_20261007_v1/hair_palette_v2_20261007/publication/`为retained_evidence；当前v5依赖的v4及其v3来源链同时保留。其他hair_palette_v2_20261007输出继承本节WF-50/OUT-WF50-RUNTIME-ACCEPTANCE的unclassified保护，不授权删除或清理源资产。

当前颜色能力表为original及black、brown、blue、pink、purple、red、teal、green、copper、golden_brown；eye只允许original，界面移除眼色选项及分组草稿区域。旧眼色实现和实验回执可以留作历史，但当前契约不得把旧蓝/绿眼选择带入多样性。新发色仍通过源实例派生MIC的Base Color Tint实现，部分颜色通道增强，烘焙底色、饰品原色和光照仍会影响结果；金棕不等于去色后的金发，不声称任意精确染色。

N/hair_palette_v2_20261007/runtime_checks_v2.json实际success，18次调用覆盖每个当前颜色及7页新男女名单，全部33个性别发型项实际加载，眼睛原色与源材质保护通过。root已直接观察粉、蓝变化明显正常；这只是agent代表观察，用户已认可的是此前黑棕，新色板最终视觉评价仍pending。R13按用户直接筛选已完成，R14实现和限定检查已完成但用户新增颜色反馈仍待，当前下一步只需用户查看新增发色。

本次总证据入口为N/hair_palette_v2_20261007/palette_manifest_v2.json，绑定v5来源、颜色参数、18次检查、save_reload_v2.json与panel_delivery_v2.json的SHA。保存重开后先检查、再组装：六头共37项绑定和12个原色虹膜绑定读回通过，受保护源SHA不变。交付快照PID13300、ready、error=null，女性第1页粉发/眼原色；界面已移除分组和眼色选择。six_color_visual_probe.json另外记录紫、红、青绿、绿、铜橙、金棕的横向小样，root亲自看到颜色清晰，仍不代替用户最终评价。全目录回归首次626通过、1个测试仍断言旧15/23人数而失败；仅将该测试更新为用户批准的13/20后，定向复跑1项通过，无剩余失败，未冒称修改后重新全跑。两次JUnit及regression_resolution.json均保存在本目录。最终目录/审计回执为documentation_audit.json。

### 3.17.5 用户最终发色接受与阶段结项

用户明确反馈“这些颜色都不错”，只删除绿色green和棕色brown。当前`hair_review/color_capabilities.json`只保留original、black、blue、pink、purple、red、teal、copper、golden_brown；眼色只有original。teal青绿与golden_brown金棕继续保留，v5发型索引/鞋服规则不变。用户接受仅限其实际审查效果，不扩大为任意身份、光照或全组合画质接受。

本节拥有`%OUTPUT_ROOT%/unreal_character_import/female_shared_shoes_hair_color_20261007_v1/hair_palette_v3_20261007/`：feedback_and_selection_v3.json绑定用户原话、最终选择、v5索引与能力表SHA；runtime_check_v3.json确认green/brown在进入UE前拒绝，teal/golden_brown/original三次实际切换通过，源网格/材质保持。panel_delivery.json固定记录PID31028、ready/error=null、男性第2页原色；不是可随用户后续操作变化的瞬时状态。旧v2证据不改写，退选不删除源资产。

该精确v3输出范围为retained_evidence，保存直接用户接受、最终选择/检查、交付快照、回归及归档文档证据；Runtime3.17生产与维护，沿用WF-50/OUT-WF50-RUNTIME-ACCEPTANCE。`documentation_close_v3.py`是同范围一次性归档工具，属于输出证据，不是新生产脚本。regression.xml/.txt实际627 passed、0失败/错误/跳过，172.15秒；最终目录和文档审计由root随后记录，不提前标为通过。

R12共享鞋、R13直接发型筛选、R14最终发色接受均完成。原主计划已迁入[完成历史](../../project_management/history/completed_plans/PLAN-2026-10-COMPLETE-CHARACTER-WARDROBE-DIAGNOSIS.md)，结项当时进入idle_after_completed_plan。后续用户新授权另由§3.17.6拥有，不修改旧完成计划。旧鞋修复已取消/替代，材质、遮挡及未覆盖动态项保留deferred，面部动画、动作和场景扩充未启动。

### 3.17.6 橙金银白发色改良

用户另行授权将copper铜橙调成明显橙色、golden_brown金棕调成明显金色，并增加银白。目标十项为栗色、黑、蓝、粉、紫、红、绿（沿用teal）、橙、金、银白。旧green/brown不因中文显示名重入候选；实际键、来源和参数由本轮配置/回执精确记录。v5男女发型集合、服装鞋池及眼原色边界保持。

本节是[已完成发色改良计划](../../project_management/history/completed_plans/PLAN-2026-10-HAIR-PALETTE-REFINEMENT.md)的实现所有者，拥有`%OUTPUT_ROOT%/unreal_character_import/female_shared_shoes_hair_color_20261007_v1/hair_palette_v4_20261007/`下色板来源/配置、原选择备份、调用/实际视觉记录、保存重开/来源保护、面板交付、回归/审计及documentation_close_v4.py归档工具证据。继承父Run的WF-50/OUT-WF50-RUNTIME-ACCEPTANCE归属，保留级别unclassified，不授权清理旧v2/v3证据或源资产。

实现保持原shader结构，只改独立派生MIC参数；使用新ID orange=(3,.65,.015,1)、gold=(4,5,.12,1)、silver_white=(12,24,40,1)，旧copper/golden_brown退出当前选项但旧MIC不覆盖，其余参数不变。栗色显示名对应original，绿沿用teal；当前十项与来源由palette_selection_v4.json及hair_review/color_capabilities.json说明。

probe01银白过暗而未选；probe02中root实际观察到橙色明显、金黄明确、银白明亮且保留发丝明暗，另看过男性短发银白正常。局部暖底图和光照仍影响呈现，不声称全部身份/光照严格同色。runtime_check_v4.json记录三色×男女7页共21轮，覆盖33性别发型项、99颜色发型组合。save_reload_v4.json读回37绑定及12原虹膜，源hash保持。首个save_reload调用仅在检查后调用不存在的set_game_view失败，失败回执保留，retry成功；不把失败伪写成功。

panel_delivery.json记录PID3452曾ready交付，后续panel_end_state.json为closed/editor_closed=false，不宣称面板当前仍开启。regression.xml/.txt实际627 passed、0失败/错误/跳过、109.13秒。R01–R03按原技术交付gate完成，计划已归档并进入idle；最终归档审计由root记录。用户新色接受仍pending，旧完成计划及8色接受保持原范围，不向新颜色外推。

### 3.18 完整角色发色配置与现成面部库

用户现已明确接受最终十色，后续固定使用；独立人工接受在`%OUTPUT_ROOT%/unreal_character_import/character_runtime_face_library_20261007_v1/final_hair_palette_user_acceptance_v1.json`，绑定最终能力表、v4参数与v5发型索引。旧v4交付当时pending回执原字节保持，不能倒写；该接受只涉及所审查颜色，不自动接受后续完整角色面部组合。

本节拥有[已完成计划](../../project_management/history/completed_plans/PLAN-2026-10-CHARACTER-RUNTIME-FACE-LIBRARY.md)的完整角色十色接入、整套配置/保存恢复、面部选择/关闭入口和总交付。Run Root为`%OUTPUT_ROOT%/unreal_character_import/character_runtime_face_library_20261007_v1/`，默认WF-50/OUT-WF50-RUNTIME-ACCEPTANCE、unclassified保护。`face_library/`的表演来源/筛选与组合语义归[Animation §7](./ANIMATION_EXPRESSION_MORPH.md#7-现成面部表演库与完整角色组合)，必要的`transfer/`导出导入回执归[Motion Transfer §8](../transfer/MOTION_TRANSFER.md#8-完整角色现成面部表演转移)。本节拥有`cfd_native_batch40_configuration_v1.py`及`tests/test_cfd_native_batch40_configuration_v1.py`，并扩展既有`cfd_native_batch40_modular_contract_v1.py`、`run_cfd_native_batch40_modular_review_v1.py`、`ue_cfd_native_batch40_modular_review_v1.py`；继续是有界审查实现，不晋升通用生产入口。

2026-10-08：R01–R02技术验证完成，`runtime_validation/validation_progress.json`为complete=true且20步全部success；执行定义为同目录`validate_color_configuration_v1.py`，逐步回执保留。覆盖男女十色、换发型/身份、无发后保留选色、女性合法赤脚换装、动作播放、配置保存后改动再恢复，以及保存关卡后`reload_before_reassembly.json`先读回既有绑定（inspection_before_reassembly=true）。已同步本次文档中间检查点，继续面部集成。后续面部选择、关闭和参数要纳入同一配置，不独立漂移；重开验证应先读取保存结果，不靠重新组装掩盖丢失。源网格、纹理、材质及Skeleton不覆盖，v5发型/鞋服规则与眼睛原色保持。

配置`complete_configuration.json`使用`cfd40_complete_character_configuration_v1`：content包含请求、来源、色板和关卡，并以content_sha256校验；恢复拒绝来源/色板版本变化，不静默替换。保存身份、服装、鞋/赤脚、发型、发色、所选动作、播放开关及视角；R01–R02检查点时face_id仅none占位；现已接入证据锁定的60项validated_review库，面部选择/关闭与保存恢复已通过24步实际验证。恢复动作与播放状态，不采集/恢复精确播放帧，不能宣称时间相位确定性。

R01–R05技术交付completed；现成5片段/60组合及root代表观察归Animation §7。完整角色面部选择、关闭、配置恢复与保存重开24步通过，可见面板已交付，用户最终review仍pending。UE/CC由root串行，用户已手动打开CC可使用该实例，不自行启动；不借该任务扩充场景、身体动作库或进行服装材质改善。

本阶段新增`tests/test_cfd40_native_face_integration_v1.py`归本节，覆盖审查库到完整槽位选择/关闭及配置契约。现成5候选及60组合的实际证据见Animation §7，完整运行和界面交付由下述独立回执证明。`regression_checkpoint_v1.xml/.txt`实录686 passed、378.43秒，仅是中间源码检查点，后续组合/运行改动完成后仍须root整合验证。

后续变更按受影响范围验证：686项全套回归为`regression_checkpoint_v1.xml/.txt`中的历史源码检查点；其后composer容差改动29项、driver 7项针对检查通过（root执行回执），normalizer单次缓存6项针对检查通过（本轮离线执行回执）。缓存覆盖重复读取、变化失效、旧SHA拒绝、同大小且恢复mtime篡改拒绝、单次生命周期及保留全文件SHA的精简解析。后续针对检查未保存独立JUnit路径，不编造文件名；不能说所有后续源码重新跑过686全套。后续contract缓存16项及playback比较2项针对检查也通过；最终目录和文档审计另有独立回执，面部运行24步全部通过。

面部运行第2步的playback说明字段误拒绝已修正，新契约缓存和登记表来源迁移已验证，UE实际重载成功；60个组合内容及用户接受状态保持。缓存每次仍核验全文件SHA，详情见[Animation §7.5](./ANIMATION_EXPRESSION_MORPH.md#75-契约缓存修复与来源重绑定)。旧失败回执保留，24步运行重试与可见面板交付均已通过。

本节拥有本Run的用户操作说明[REVIEW_GUIDE.md](../../../../../../00_engine/outputs/unreal_character_import/character_runtime_face_library_20261007_v1/REVIEW_GUIDE.md)：表情选择/关闭、男女放大、身体组合和整套配置保存恢复。沿用Run的WF-50/OUT-WF50-RUNTIME-ACCEPTANCE、unclassified保护；操作说明不替代运行或用户接受证据。

本轮技术交付总证据为`technical_delivery_v1.json`，绑定20步颜色配置、`runtime_validation/face_configuration_20261007T175232650907Z/validation_progress.json`的24步面部配置、60项审查库、代表观察和用户说明SHA。重开检查先读真实保存场景，再允许重新组装；恢复选定片段与播放开关，不恢复精确播放时间。当前5动作之外的新动作仍需新派生/验证。

本节拥有本Run的`technical_delivery_v1.json`、`panel_delivery_observation_v1.json`、`panel_delivery_lifecycle_v1.json`及`documentation_final_audit_v1.json`，沿用WF-50/OUT-WF50-RUNTIME-ACCEPTANCE、unclassified保护。root通过native截图实际看到ready面板、启用控件和none＋5表情下拉；交付时PID7768、窗口57345922，未点击用户验收按钮。此前后台shell启动的隐藏面板不算可见交付，已仅关闭root启动的该面板后从UE桌面进程重开；CC/UE未关闭。交付快照不保证未来窗口一直打开。

计划按技术交付条件结项并进入History，结项当时idle、用户最终接受pending。2026-10-08后续用户已确认旧五种表情整体正确；新要求为自然持续五秒，独立反馈及新试验归[Animation §8](./ANIMATION_EXPRESSION_MORPH.md#8-五秒自然面部表演试验)。旧pending回执保持原字节，不把此确认扩大为新五秒自然度或全组合接受。

#### 3.18.1 重开面板的节点与关卡恢复

`run_cfd_native_batch40_modular_review_v1.py --action panel`只打开面板，不自动打开ModularReview关卡或刷新批次`ue_target.json`。`cfd_native_pair_ue_target_v1.py`严格匹配node/user/project；节点过期时禁止按项目名fallback。应先核对用户可见UE的项目、进程、当前节点和关卡，备份旧target及面板状态后绑定精确实例，再单独打开`L_DM_CFDNativeBatch40_ModularReview_v001`并读回验证，最后重开面板。多个UE时不能自动猜选；40人排列的`L_DM_CFDNativeBatch40_Review_v001`不是双人模块化关卡，不靠反复开面板或重建场景修连接。

2026-10-09的限定恢复证据位于`%OUTPUT_ROOT%/unreal_character_import/cfd_native_batch40_20261006_v1/runtime/modular_review_20261007_v1/connection_recovery_20261009_v1/`，由本节拥有，继承父Run的WF-50/OUT-WF50-RUNTIME-ACCEPTANCE及unclassified保护。recovery_summary.json、restored_result.json和panel_ready_snapshot.json记录target PID25892/node399DA6CA408C0013F52DDCA95BF87A9A、正确关卡与面板PID38144 ready/error=null；身份LF003/WM004、服装/发型/发色及旧gentle_smile保留，以静态暂停重开。这是恢复当时快照，不是永久进程或窗口状态。仅关闭失效旧面板18824，两个UE均未关闭，四类新五秒表情未集成。

旧关卡show断言失败及随后连接reset回执保持，不倒写成功；最终结果只以独立恢复回执为准。用户指南已补上述入口边界，旧technical_delivery绑定的原指南字节保存为本恢复根REVIEW_GUIDE_before.md，review_guide_update_v1.json记录前后SHA；旧交付回执不修改。本次只修复会话连接/说明，不创建新计划或重跑此前761项代码回归，文档检查记录在同根documentation_audit_v1.json。

### 3.19 四类五秒表情接入当前审查关卡

2026-10-09用户明确要求先把已保留的四类新表情替换旧选项并接入刚才的审查关卡，再开展夜间动作扩充。此项属于唯一当前[执行计划R00](../../project_management/plans/active/PLAN-2026-10-FACE-AND-MOTION-LIBRARY-EXPANSION.md)，现已按本节末delivery_v1.json完成技术交付供用户审查；下列检查点保留阶段边界，不能将先前八段预览接受外推为全40运行视觉接受。

本节拥有N3=`%OUTPUT_ROOT%/unreal_character_import/native_face_panel_integration_20261009_v1/`的来源快照、新版运行合同/发布清单、派生组合、面板接入、实际选择/关闭/配置保存恢复与源保护验证、交付及最终文档证据。沿用WF-50/OUT-WF50-RUNTIME-ACCEPTANCE，默认unclassified保护。来源为Animation §8.7的accepted_face_selection_v1.json：男女各`idle/smile/displeased/sad`，rate=1、duration=5；原选择文件及旧五类库/回执保留，新实际运行入口以独立发布和验收证据判定，不倒写历史SHA。

当前目标是既有`L_DM_CFDNativeBatch40_ModularReview_v001`双人分离槽位审查，保留身份、鞋服、发型、发色和身体动作配置。root串行修改应用，2026-10-09核验的可见UE为PID25892/node399DA6CA408C0013F52DDCA95BF87A9A，后台PID18500保留不写；这些仅为会话快照，重启须重新核对，不能多个UE自动猜选。验收需要四类及关闭选项、原速五秒时序、眼口和代表身体组合、配置保存恢复及已覆盖动作明确；当前实测与发布证据pending，不声称全40角色或任意动作自然度通过。

执行检查点：N3/native_face_library_registry_v2.json已生成并由active_face_library_v1.json激活，48项覆盖四类×男女×各六种身体选择，全部组合数字验证通过；面部连续五秒rate=1。两条较短旧身体片段在五秒窗口中按原速重复，接缝另有矩阵记录，不能把身体重复说成面部循环。旧五类registry SHA仍为31d28eb00ad7ce7e4e1e0a29d851422c6de6342a56b6a5a75954ab000e08c1c6，原文件与旧代码备份保留。

本节拥有`00_engine/scripts/unreal/ue_native_face_panel_five_second_v1.py`（experimental）及`tests/test_native_face_panel_five_second_v1.py`、`tests/test_native_face_library_v2.py`（utility）。新wrapper仅生成/验证隔离身体窗口与已接受面部派生；既有native_face_library_contract_v1.py的v2分支和完整角色面板/配置消费变更按本节集成范围维护，通用面部契约所有者仍为Animation §7。N3内一次性准备、发布、运行、截图、测试和文档工具均属本Run证据，不晋升默认生产入口。active指针锁定新版registry SHA；registry绑定的运行源码未经协调不能修改，旧来源/回执不重绑。

root_visual_v1.json绑定男女各四类、0/2.5/5秒共24张固定镜头图及两张contact sheet；root实际审看，限定女性Audience与男性Battle Dance代表，眼睛/头发附着及面部/身体表现未见明显脱离。早期近距离跟头截图中眼发缺失同样发生于未修改原身体动画，若干刷新/LOD/距离探针未定位根因；固定camera=(300,actor.y,140)、FOV25代表图正常，不写为所有截图正常、根因已修复或全40/全部动作视觉接受。R00仍in_progress，实际面板运行、配置保存恢复与最终交付待独立smoke回执；三目录回归另记N3/tests，不由上述发布推断通过。

本轮三目录宿主回归实际覆盖809项：首次默认用户临时目录WinError5导致477通过/332 setup errors；独立临时目录重跑808通过/1失败，唯一失败因假仓库位于真实仓库被忽略的outputs下，Git枚举返回空。该项换到仓库外新临时目录精确复跑通过；新增owner映射后文档目录34项全部通过。N3/tests/regression_resolution_v1.json绑定四份JUnit，合计809项均有通过证据、无未解决失败，不宣称单次全套809通过，也未为测试改生产逻辑或旧报告。运行验收与最终目录审计仍分别判定。

运行恢复检查点：smoke01发生UE资产尚未加载完成的assert崩溃，root已核验日志；Slate回调重入导致重复加载是当前推断，不能写成已证实根因或已修复。N3/runtime_smoke/smoke01仅有启动/标签/原配置与迁移请求记录，没有完成或通过回执，保留为失败诊断。外部同步run_runtime_smoke_v2.py已准备，显式固定节点/PID、要求已显示并校验的基线，不在Slate回调加载资产，也不保存关卡；准备完成不等于运行通过。root恢复UE时N3/recovery_editor_pid.txt为14152，editor_recovery_launch.log记录启动/着色器编译，旧节点快照不可继续当当前连接。R00保持in_progress，后续成功需新的独立运行回执。

本节统一拥有N3/runtime_smoke/、dispatch/、恢复日志，以及ue_runtime_smoke_v1.py、start_runtime_smoke.py、run_runtime_smoke_v2.py等本Run一次性驱动；沿用原输出合同和unclassified保护，不逐个升级为主脚本目录的生产入口。机器目录与文档审计只证明当前记录一致，不证明本次UE运行验收完成。

崩溃原始证据为N3/editor_visible_launch.log：2928行起脚本堆栈包含SetSkeletalMeshAsset及多次SetSkeletalMesh，2944行assert检查RF_NeedLoad/RF_NeedPostLoad/RF_NeedPostLoadSubobjects，2950行critical error。它证明加载状态断言，堆栈重复本身不证明Slate重入就是根因。

后续恢复：PID14152启动后被“恢复包”窗口阻止初始化；root先备份本审查关卡唯一Auto1.umap与PackageRestoreData.json到N3/recovery_prompt_backup/（manifest绑定关卡备份SHA），保留autosave，再用官方AutoDeclinePackageRecovery启动PID24668。仅处理root本次启动且尚未进入关卡的恢复实例，不把它表述为通用绕过恢复或删除自动保存。

N3/runtime_smoke/smoke02/summary.json现success=true、error=null、sources_unchanged=true，绑定新旧registry/active指针前后SHA。限定实际验证四类表情在body1、原生组件约1.16057秒暂停保持、面板暂停/续播、五秒末帧保持、重播、none恢复原身体、整套配置扰动后恢复、显式切至LF003/WM004保留选择，最终恢复基线LF001/AM004搭配。外部同步驱动替代失败的smoke01，旧失败保留；不证明所有48组合运行、全40身份或全时序视觉自然度。没有精确播放相位序列化，也不承诺面板点击响应低于五秒；已加载组件时序探针与实际面板调用分开记录。

N3/REVIEW_GUIDE.md由本节拥有，说明四类五秒、末帧保持/重播、none和整套配置入口；不能替代实际交付。smoke02明确map_saved_or_reloaded=false、human_review=pending，故R00暂保持in_progress，等待最后保存重载及面板就绪回执。当前checkpoint文档审计见documentation_checkpoint_audit_v2.json：657脚本/145范围、16子系统及跨层0错误0警告，不等于运行已交付。

最终R00技术交付以N3/delivery_v1.json为准，status=complete_for_user_review、human_acceptance=pending。它绑定smoke02、完整保存重载回复e14c5a185a124a3aa64d4f3f9cb683cf.json（inspection_before_reassembly=true）、关卡前后SHA、指南、数字矩阵/代表审看/回归及active registry。11个引用文件当前SHA核对一致。delivered_panel_lifecycle.json固定交付快照为ready/PID22544，UE24668/node673CCAE342F919AC42C5E48CEDFAA29D与两个MainWindow均可见；LF001/AM004原衣发和银白/teal发色保留，两人smile。该快照不是永久窗口状态，保存恢复也不承诺精确播放相位。R00现completed，后续动作库由同一计划继续；未取得本次整合界面或全40自然度的用户接受，旧失败和未定位采样诊断保留。


后续同一授权计划的无道具动作扩充已技术交付，当前新入口/指南及最终回执见[Animation §9.10](./ANIMATION_EXPRESSION_MORPH.md#910-最终可见界面交付与结项范围)。该入口显式消费M3最终motion catalog与face overlay；本节N3旧默认入口、48项源锁和原交付历史不覆盖。新窗口ready不代表用户已接受所有新动作/组合。


完整身体动作循环审查的独立实现与最新边界由[Animation §10](./ANIMATION_EXPRESSION_MORPH.md#10-完整动作循环审查)拥有；本次不改变固定槽位、身份和外观配置的原所有权。

### 3.20 面部皮肤细节独立对照实验（2026-10-12）

本节拥有 `skin_detail_optimization_20261012_v1` 的独立运行状态、UE 材质变体、对照关卡/媒体、审查入口和推荐报告；适用 `WF-40/WF-50`，复用 `VAL-UE-01` / `VAL-UE-02` 与 `OUT-WF50-RUNTIME-ACCEPTANCE`。CC 选择性换皮与几何检查由 [CC装配§10](../character_creator/ASSEMBLY_AND_ACCEPTANCE.md#10-面部皮肤细节独立对照实验2026-10-12) 拥有。完整转移和相机渲染仍复用原领域入口，不重新设计骨骼、镜头或生产流水线。

Run Root 为 `%OUTPUT_ROOT%/unreal_character_import/skin_detail_optimization_20261012_v1/`；`EXECUTION_PLAN.md` 记录用户授权范围，`execution_record_v1.json` 拥有精确进度与实际证据。当前锁定角色、最终候选参数与输出分别由 input_manifest_v2.json、c_final_capture_selection.json、c_variants_params_v2.json 及媒体回执拥有；本轮技术交付与局限见同目录 RESULTS.md 及下述最终小节，用户视觉接受待确认。

男女各一名，A 原始材质，B 保留照片皮肤并优化，C 配套换皮后优化。先核对颜色/法线/粗糙度实际引用、纹理尺寸、细分对应和纹理加载，再调整毛孔、分区光泽、唇部/眼周过渡及头身颜色。所有变体使用独立材质副本，不能改共享父材质污染已接受角色。相同近景、上半身及短表情比较冻结相机、光照、曝光、动作与输出设置；若修正了共同渲染条件，A/B/C 都使用修正后的同一条件，记录原条件差异，不能将曝光差当皮肤改进。

媒体交付前需实际检查内容、尺寸/帧数、可读性和版本对应。来源与配置哈希、几何/材质检查、实际图/片、审查入口及推荐配方分开落盘；用户视觉接受保持 pending 直到明确反馈。候选没有改善时记录失败或无收益，不强行宣布换皮优于原版；不推断全 40 人或所有表情接受。原 201 条交付及唯一 current 主计划保持，CC/UE 由 root 串行核实并操作。本 Run 默认 unclassified 受保护，不授权清理或覆盖正式资产。

#### 3.20.1 独立审查页生成器

`00_engine/scripts/unreal/skin_detail_review/build_gallery.py`、同目录 `gallery.html` 与 `test_gallery.py` 由本节拥有，生命周期 experimental。生成器不启动服务器，不操作 CC/UE，不从场景准备报告推断视频已完成。复用 `encode_camera_pilot_v1.py` 的 SHA、原子 JSON 和可选完整解码检查。

输入为 Run 下显式 `review_gallery_input_v1.json`（schema=`skin_detail_review_v1`）：`characters` 固定 AF005/LM002，照片采用 Run 内相对路径及 SHA；`clips` 明示 `character_id`、`framing=head|upper`、`variant=A|B|C|B_micro`、`status`。只有 `encoded_verified` 且视频/回执 SHA 相符、回执 `decode` 为 300 帧/30 fps/10 秒/1920×1080 才公开播放地址；回执另需 `status=encoded_verified`、`video_sha256`。可选 `poster` 必须同时提供 `poster_sha256`。缺项或未核验项呈现 pending，不自动选用旧输出。页面支持男女、近景/上半身、左右 A/B/C/可选微法线诊断、同步播放/拖动、静帧保存及源照片对照。

```powershell
python 00_engine/scripts/unreal/skin_detail_review/build_gallery.py --run-root "D:/UE/Lance_Work/00_engine/outputs/unreal_character_import/skin_detail_optimization_20261012_v1" --manifest "D:/UE/Lance_Work/00_engine/outputs/unreal_character_import/skin_detail_optimization_20261012_v1/review_gallery_input_v1.json"
```

加 `--full-decode` 可对已明确声明完成的片段重新完整解码。生成 `gallery/index.html` 和 `gallery/gallery_build_receipt_v1.json`；早期页面仅 pending 骨架，不是媒体交付。五项输入边界测试及 JS 语法检查已通过，证据为 Run `gallery_tests_v2.xml`；v1 因 sandbox 临时目录不可写而 setup 失败，改用新 workspace basetemp 后通过。这属于最初 pending 骨架阶段；后续 root 已做真实双播放器检查，见下节，不能以早期语法检查替代该实际证据。

#### 3.20.2 已实现辅助入口与中期边界

本节另拥有 experimental 脚本 `skin_detail_session_v1.py`（目标会话与受控调用）、`ue_skin_detail_scene_v1.py`（独立对照场景）、`ue_skin_detail_materials_v1.py`（材质审计与隔离副本）、`ue_skin_detail_graph_audit_v1.py`（只读 RL_HQSkin 图/粗糙度路径审计）、`open_skin_detail_gallery_v1.py`（本机 Range 视频服务）。脚本均位于 `00_engine/scripts/unreal/`；图审计注入既有 Unreal API，不打开材质编辑器，前后记录父材质 SHA 及 dirty package。可用本地 UE 5.8 实现源码解释 API 行为，不能仅凭过时头文件注释判定必须打开编辑器。

最新显式页面输入为 Run `review_gallery_input_latest.json`，运行生成命令时将上一节 manifest 参数替换为该文件。`python 00_engine/scripts/unreal/open_skin_detail_gallery_v1.py --no-browser` 在本机 8893 端口提供页面及 Range 视频，不占用外部网络；省略参数可打开浏览器，`--serve` 为后台服务模式。中期检查点曾只有 A 四段、B 粗糙度四段、B_micro 近景两段完成；后续最终 C_params_v2 四段已形成完整媒体回执，版本选择以下节及最新页面 manifest 为准。root 已实测双侧 1080p 播放、时间差小于0.001秒；人工最终视觉选择 pending。

材质初读 32px 已证实为异步占位，loaded_v2 读到 Head4K、Normal2K，不能据此声称源纹理只有32px。CC 原始 2048 粗糙度存在，但原 FBX/JSON 没有导出该通道，UE 使用 Gray；B 以补回原角色粗糙度为目的，不任意改肤色或全部材质。准确诊断见 `roughness_diagnosis_v1.json`、`roughness_graph_audit_v1.json`、`roughness_switch_audit_v1.json`。微法线版是额外诊断，不代替 B 粗糙度修复的对照结论。

#### 3.20.3 最终实验结果、C 参数修正与保留边界

本轮技术结果由 Run `RESULTS.md` 解释；机器进度和最终入口由 `execution_record_v1.json` 维护。主要对照为男女各 A/B/C×head/upper 共12片，另有2片近景微法线诊断；每片1920×1080、30fps、10秒。`media_validation_baseline_loaded_v1.json`、`media_validation_b_comparison_v1.json` 与 `media_validation_c_skin_params_v2.json` 拥有实际编码/解码结果；旧 C_skin_v1 四片保留诊断，不作为最终 C 选择。

C 初版只替换标准贴图而残留原 HQ 材质参数。`c_parameter_transfer_diagnosis_v1.json` 记录差异，修正版本 `C_skin_params_v2` 在全新材质实例与关卡上复用 C 贴图，仅迁移确认对应的 Specular（女0.7、男0.6）与非Head MicroNormal Strength 0.5。实际对象/哈希为 `c_variants_params_v2.json`，场景为 `prepared_skin_params_v2.json`。本 Run 的 `ue_prepare_c_params.py` / `ue_render_c_params.py` 与编码/页面输入构建脚本属本节一次性运行驱动；创建入口拒绝覆盖，复现须新revision与独立输出，不能直接重提历史作业。

C 迁移四部位标准颜色、法线、粗糙度及可用头部AO；它不是完整 CC Auto Setup 等价重建。原高级遮罩与 SSS 配置保留，custom shader纹理槽未由SDK捕获覆盖。CC SSS半径/颜色到当前UE Burley参数缺少可靠转换，本轮没有猜测单位或修改共享profile；Cavity Strength不当作AO Strength使用。两人C头部颜色/法线/粗糙度为4K，身体并非所有通道4K。

root 实际观察最终男女head第100帧，C更有细纹、毛孔感和局部色彩变化；女性唇色/眉区改变，男性胡茬/脸色更深。B变化较小，原皮肤已带微法线；原导出缺粗糙度事实不等于已确定导出器故障，仍可能与导出设置有关。A同位置已有颈部硬阴影，不凭C暗边直接判定新增UV/材质接缝。上述是两例有限图像观察，不是所有动作逐帧或用户接受。

UE保留原网格、骨骼、Morph及眼口部件，只在实验组件覆盖独立皮肤MIC；原网格/材质由来源散列核对，正式40人不覆盖。建议优先让用户比较C，不自动批量换皮。最终配方决定、所有身份/皮肤池适用性、完整高级shader/SSS迁移和严格逐像素确定性均未晋升。本轮1151项广泛测试通过（final_tests_v3.xml，0失败/错误/跳过），最终Catalog/Inventory及文档审计由本Run独立回执收口，不在本段提前声明审计通过。

### 3.21 独立人物与头发审查关卡（2026-10-17）

面板发型下拉框和当前显示提示使用既有目录编号，格式为“01 号 · 发型名”。编号不按当前性别列表重新排序；反馈可使用“女性 02 号”或“男性 27 号”，保留编号空缺。

用户报告发片呈片状、异常阴影再次出现，要求独立人物与头发审查入口，并明确必须使用正式槽位系统。本节拥有`00_engine/scripts/unreal/ue_hair_only_review_v1.py`、`run_hair_only_review_v1.py`、`open_hair_only_review_v1.ps1`及共用覆盖修正`ue_hair_coverage_runtime_v1.py`，复用`VAL-UE-01/VAL-UE-02`与`OUT-WF50-RUNTIME-ACCEPTANCE`。Run Root为`%OUTPUT_ROOT%/hair_only_review_20261017_v1/`，关卡为`/Game/DataMake/Review/HairOnly20261017/L_HairOnlyReview`；本节拥有诊断报告、隔离对照图和装配修正读回，默认受保护。头发修复已接共用正式装配并完成本轮技术交付，待用户视觉审查；皮肤／睫毛诊断及尝试完成但未解决，已交接后续CC处理，不代表生产Gate或全40人／全发型接受。

后端使用与`ue_production_site_runtime_v1.py:preview`相同的正式装配路径：以`formal_path_overlay`解析`stage.SOURCES`，加载正式模板map并复制其中唯一`DM_CCWH_<sex>_Character`，调用`assembly.apply_actor`填充正式Blueprint的38槽。原先原生Actor临时拼装的首版已被替换，不能作为现用实现。现用版只给无服装、无身体动画、无表情和原色选择，使用头部近景相机；不遮罩身体、不强制LOD、不改正式模板组件渲染flags。未用服装槽由正式装配器清空。源槽绑定及阴影保留构成修正前基线；当前通过共用装配给组件使用下述派生覆盖MI，源网格／材质不改。

快速切换优化仅作用于本独立审查入口：会话内缓存catalog，不再逐次重载目录模块；同性别复用已有正式38槽实例，跨性别才复制模板；灯光仅缺失时初始化，切换不再逐次保存关卡，单独转视角不读取catalog。正式装配仍调用`assembly.apply_actor`，现有面板无需重启即可通过每次命令重载worker使用优化。本节拥有[轻量性能检查](../../../../../../00_engine/outputs/hair_only_review_20261017_v1/performance_quick_check.json)：success=true，UE内部catalog／换发／转视角／恢复分别为0.012／0.207／0.001／0.538秒，两次show均复用Actor，并恢复LF001/HB1_02/front。该计时不含控制器连接和视口稳定；整组桥接runner约3.82秒也不是单次点击计时，不能把0.207秒当作UI总响应。未开展重校验或新增视觉接受。

面板只提供当前40身份、该身份性别可用发型、上一款／下一款和正面／侧面／背面／斜侧面四向观察；没有服装、身体动作、表情或发色控件。运行`open_hair_only_review_v1.ps1`后选择人物／发型，点击“显示角色与发型”，再用四向按钮观察。它连接现有UE会话，不新启UE；切入独立关卡前暂停当前拍摄点播放／检查，若原地图dirty则先保存到独立Recovery副本，原地图和用户点位／外观JSON不覆盖。代表实际入口与操作见Run `README.md`。

`entry_context.json`记录原关卡与必要备份，`last_selection.json`记录最近选择，`remote/*.json`保留逐请求／回执，`latest_review_receipt.json`为可变的最新装配读回。[正式槽位冒烟](../../../../../../00_engine/outputs/hair_only_review_20261017_v1/formal_slot_smoke.json)success=true：AM001/HB3_01与LF001/HB3_14各自使用正式模板及38槽，分别核对4和6个hair材质槽源绑定与阴影保持、源资产未改；四向相机位置／旋转读回完成，结束恢复LF001/HB3_14正面。该检查只覆盖两份代表和四个相机操作，不是全40人／全发型视觉回归。此前标为front的截图实际为侧面：正式模板参考姿态面向+Y，而front相机位于+X。现仅将整个独立角色Actor的yaw设为-90，使front相机正对脸，槽位组件局部变换保持；该处是摆放朝向纠正，不把此前四向坐标读回当作四向视觉验收。稳定截图已由root确认正脸朝向正确，发际线片状边缘仍可见，根因未修复。独立观察相机随后由90cm拉远至120cm以避免裁掉头顶，构图较宽；不改变正式生产相机。旧`hair_only_formal_front.png`不作正面视觉依据，四向视觉仍未逐一接受。`panel_lifecycle.json`记录实际面板启动和连接阶段；本节拥有同Run的`documentation_validation_v1.json`。

#### 共用发片覆盖修正：技术交付，待用户视觉

[遮罩源审计](../../../../../../00_engine/outputs/hair_only_review_20261017_v1/diagnosis/hair_mask_source_audit.md)与同目录`dither_function.t3d`确认两个问题：HB1_01男女Hair_Base的`MI_Hair134_*`误绑共享`White_GaryScale`，而对应性别的真实`T_Hair134_Transparency_Pbr_Opacity`仍在；CC实际Dither输出为`alpha + (mod5 + noise)/6 - .5`，alpha=0时最高为1/3，旧clip=.15仍保留透明矩形。来源丢绑发生阶段未证实，不能直接归因目录迁移；源图不是全图非零底灰。

`ue_hair_coverage_runtime_v1.apply`仅处理HairPart中父链最终属于原CC Hair shader或现用中性发色shader允许集合的Opacity槽，跳过零遮罩和发饰等其他shader。它在`/Game/DataMake/Appearance/Materials/HairCoverageV1/`按源槽、当前颜色父材质、修正纹理及版本摘要建立可复用子MI；通用clip=.34，HB1_01的Hair134恢复各自性别真实遮罩并用.44以覆盖JPG外边最高25/255的低值。仅覆写clip和该错误遮罩，继承当前颜色及反光参数，不修改共享父shader、源纹理、源MI或网格，不关闭阴影。再次应用先剥离本helper自己的覆盖层，避免叠加父链。现用`ue_scene_site_appearance_v1.apply_actor`在发色应用之后统一调用该helper，独立审查与正式预览共用；装配缓存签名含修正版本，`ue_primary_saved_site_review_v1`命令边界重载列表包含helper。`hair_coverage`读回进入正式返回值与独立审查receipt；`source_material_bindings_unchanged`精确表示组件绑定是否仍与源槽相同，修正后可为false，而`source_assets_modified=false`表示源资产未改，两者不能混用。代码调用一致不等于正式拍摄实机复验通过。

`diagnosis/shared_repair_first.json`记录首次WF003/HB1_01组件修正读回。旧`diagnosis/visual/00`至`03`的女性图有效；更晚旧男性及皮肤图因诊断Slate回调重入、重叠Actor与内存耗尽而无效，失败保留于`visual_controls.json`，不能重新当作有效证据。恢复后诊断驱动增加busy guard防止重入，[受保护对照](../../../../../../00_engine/outputs/hair_only_review_20261017_v1/diagnosis/visual_controls_guarded.json)success=true，14张图完成且恢复WF003/HB1_01/front。root已查看新AM001/HB1_01正面与HB3_02斜侧前后图，无重叠Actor，发片效果改善；WF003两款正面也已重新拍摄。它是男女有限代表观察，不是全发型／方向视觉接受。旧驱动事故不据此推广为生产装配故障。

[可选目录绑定检查](../../../../../../00_engine/outputs/hair_only_review_20261017_v1/diagnosis/coverage_catalog_check.json)success=true：33个可选性别／发型case、117网格、199槽；130个Hair槽得到修正，59个既有零遮罩和10个发饰槽保持。报告逐槽核对继承参数不变、再次应用幂等及源资产未改。该检查为Python-only绑定范围，不渲染全目录，不证明全部款式的细发／阴影或10色跨场景观感。[十色继承检查](../../../../../../00_engine/outputs/hair_only_review_20261017_v1/diagnosis/color_coverage_check.json)success=true、count=10：仅LM002/HB1_02一代表发型逐一检查原色加九种染色，scalar／vector／switch及源材质保持，场景组件未改；不是全发型十色渲染或跨场景视觉接受。

[正式预览一致性](../../../../../../00_engine/outputs/hair_only_review_20261017_v1/diagnosis/hair_production_parity.json)success=true、differences=[]：实际游乐园既有点位以WF003/HB1_01及`MOTION_CAND_008`在0.5／1.3秒取样，与独立review的全部38槽核对网格、材质、局部变换、骨骼跟随、LOD、bounds和阴影一致；头部确实运动，点位文件SHA保持，结束恢复静态独立审查。该代表实机结果关闭“只在独立关卡有效”的疑点，不是MRQ全片、所有人物／发型或十色视觉验收。[本轮定向pytest](../../../../../../00_engine/outputs/hair_only_review_20261017_v1/diagnosis/targeted_pytest.json)实际42passed／11.63秒，覆盖primary saved-site adapter与hair-color trials两份测试，不借历史54项替代当前验证。

#### 颈胸接缝及睫毛：来源已收窄，尚未修复

[颈胸源审计](../../../../../../00_engine/outputs/hair_only_review_20261017_v1/diagnosis/skin_seam_source_audit.md)与`skin_source_boundary_probe.json`覆盖AM001、LM002、WF003：源Head↔Body/Arm交界色差小、共享控制点源法线连续；当前CFD40沿用HQ皮肤，不能套用3.11的FixedHead统一皮肤完成事实。`skin_channel_controls.json`、`skin_hq_controls.json`及[物理源法线对照](../../../../../../00_engine/outputs/hair_only_review_20261017_v1/diagnosis/skin_normal_sources_v1/probe.json)记录LM002的受控试验：低Specular=.5未修复；常量Normal明显减弱接缝但丢失细节，不作为推广方案；简单Diffuse＋Normal重新出现边界，将四个独立HQ MI的Normal替换为物理PNG重新导入资源也未修复。

[最后独立网格对照](../../../../../../00_engine/outputs/hair_only_review_20261017_v1/diagnosis/skin_imported_normals_result.json)已完成：LM002原正式mesh开启重算法线／加权法线及Mikk；隔离clone关闭重算法线和加权法线、保留导入法线并重算Mikk切线，颈胸分界仍在，原网格已恢复、未推广clone。该结果只否定此具体设置组合能解决接缝，不能排除所有切线框架，也不能由源Normal采样差异断言CC法线损坏。本轮定位为法线参与的着色贡献，具体原因和有效修复未闭环。诊断及尝试已完成、皮肤仍未解决，后续CC会话按源审计末尾交接核对同一最终mesh／UV／三角化／法线与切线约定、四部位贴图和UE构建设置，再做隔离成对验收；不要求重做照片脸、不批量覆盖40人。

睫毛源审计由[BodyFit §11的修复交接](../character_creator/BODYFIT_IDENTITY_AGE.md#原生睫毛被固定头皮目标覆盖cc修复交接2026-10-17)拥有。WF003的704原生睫毛点被固定头皮目标误覆盖，保存后相对本次照片源平均位移约5.929mm；这不是换发型直接造成。受保护对照第12／13图只将Body的`Std_Eyelash`槽临时零遮罩，穿眼线条完全消失，结束已恢复原材质；该因果对照进一步把线条绑定到睫毛分区，不是隐藏睫毛即修复。当前未实施CC候选重建、完整重导或眨眼复验，不直接在UE推中性顶点代替395项Morph及蒙皮验证。其他身份与两张未绑定身份的截图不能套用该单例数值。

3.3的历史`cast_shadow=false`仍只是诊断；3.7只处理其既有Scalp/Hairline范围。当前修正保留阴影及标准10色／反光输入，用户没有接受新柔反光策略，颜色取消与旧ID兼容证据归[场景面板§22.1](./SCENE_CAMERA_SEQUENCE.md#221-新面板实现与独立外观保存)。本轮头发修复技术交付完成，下一步由用户重点审查男女1号及其他发型边缘；皮肤／睫毛诊断与尝试已完成但未解决，后续按CC交接处理，候选未实施。R17继续in_progress等待用户视觉反馈，唯一current计划保持，人工接受及生产Gate未晋升。

### 3.22 用户修改后双人完整场景点位审查（2026-10-19，限定接入完成）

本入口只包含`CFD40_AF_001`与`CFD40_AM_001`的20261019用户修改后版本；完整来源、导入审核与八件网格由[当前导入交接](../../../../../../00_engine/outputs/character_refresh_20261018_v1/CURRENT_IMPORT_HANDOFF_20261019.md)及其`user_edited_pair_import_20261019_v1/delivery.json`拥有。R17仍在执行，本节记录新入口和有界检查点，不代替最终交付、全组合运行时或人工视觉接受。

记`S=00_engine/scripts/unreal`、`R=00_engine/outputs/pair_scene_review_20261019_v1`。以下入口和测试由本Technical拥有，执行脚本生命周期为`experimental`，并非正式生产调度器：

| 入口 | 作用与限制 |
| --- | --- |
| `S/pair_scene_review_20261019_v1.py` | 私有模块图复用完整场景点位面板；只限制新版两人人物目录，复制旧点位后使外观关联和检查结果失效；控制器与精确UE端点共用入口 |
| `S/open_pair_scene_review_20261019_v1.ps1` | 启动完整交互面板，可显式传入`-NodeId`选择已核实UE实例；不启动余38人导入 |
| `S/ue_pair_revision_runtime_20261019_v1.py` | 验证两人实际导入源/审核/UE包、同性共享Skeleton与八件网格；私有overlay替换六主体网格，保持正式38槽，另以两个独立拥有的睫毛Actor跟随Body，挂接姿态、Morph、显隐、遮挡忽略与释放清理 |
| `S/tests/test_pair_scene_review_20261019_v1.py` | 完整菜单/两人限制、copy-once点位继承与旧结果失效、首开现场同步及动态动作镜头文案等有界面板合同检查；不代替真实UI视觉接受 |
| `S/tests/test_pair_revision_runtime_20261019_v1.py` | 有界源版本拒绝、八件结构/睫毛映射、输入变化失效、None切换与拥有者清理顺序回归；离线测试不证明UE实际画面通过 |

用户要求完整内容版面板，保留换装、头发切换、标准10发色、表情、26动作、21镜头、26主场景和点位保存。当前菜单按现用库提供女20/男13发型与女12/男26服装family；这些是可选目录范围，不是所有组合已实测或接受。主场景按既有primary标记筛选，不重选、迁移或删除场景。

运行方式（从仓库根，先核实当前UE实例与用户编辑状态）：

```powershell
powershell -ExecutionPolicy Bypass -File 00_engine/scripts/unreal/open_pair_scene_review_20261019_v1.ps1
# 多UE实例时使用已核实的节点：
# ... -NodeId <actual-node-id>
```

`prepare()`只在新Run中copy-once初始化：原32点位记录各保留一份`R/inherited_sites/`来源副本，当前`R/sites/`继承坐标/朝向/曝光等场景设置与显式排除，不继承旧外观关联、检查通过或人工接受。新副本清除`appearance_config_id`、`appearance_selection`、`decisions_stamp`，置`report=null`、`human_acceptance=pending_new_character_revision`；原点位及旧外观文件保持。已有新Run点位不被后续prepare覆盖，避免覆盖用户保存。显式排除不是新角色组合安全的证明，修改/重新审查仍需按当前签名保存。

初版严格接入使用新delivery及逐人import audit、FBX/网格包/适配入口的实际绑定。UE运行时只接受新根`/Game/DataMake/Characters/Revisions/CFD40_20261019_v1`下两人八件网格；`MaterialWitnessInteractive/`仍是材质来源，不作为Body运行。派生表达/材质/睫毛载体使用独立`/Game/DataMake/Validation/PairRevision20261019_v1`，不覆盖旧正式角色源。初版worker记录当前输入签名，输入变化时暂停播放并要求重新载入；本节后续提速版已按用户要求关闭普通预览中的资源重哈希与兼容审核，改用当前审查会话缓存，旧严格签名报告不延续为新检查通过。场景/拥有者释放先清除该拥有者附属睫毛，再调用原恢复逻辑；不释放其他拥有者或公共资产。

当前技术接入检查已完成，准确范围见`R/integration_summary.json`：5代表case均读回正式38槽、新版六主体件、两片附属睫毛及非空材质槽。女性默认衣裙/Misaki及男性默认西装/casual已有限观察，男女idle近景、男性None返回睁眼也已观察。外观+临时点保存重载通过，测试文件归档`R/save_roundtrip/`而不留菜单；游乐园→中式建筑→游乐园场景往返通过。仅一个思考/front_head/landscape组合完成42/42遮挡采样、0问题，`full_matrix_checked=false`。32旧点位源hash均保持。沿用原衣发及材质接口，未扩大纹理优化；这些检查不证明所有搭配、全帧Morph/眨眼或精细皮肤质量接受。

最终回执已落盘：[panel_delivery.json](../../../../../../00_engine/outputs/pair_scene_review_20261019_v1/panel_delivery.json)记录PID53404 ready及root实际窗口确认完整换装/发型/发色/表情控件、26动作/21镜头文案，游乐园/1与模特步行/正面全身/竖屏首开同步正确；通过UI播放观察4.10/10秒进度，随后停止回0通过。[final_ready.json](../../../../../../00_engine/outputs/pair_scene_review_20261019_v1/final_ready.json)记录最终重载后的38槽与两附属睫毛接入读回。[targeted_tests.json](../../../../../../00_engine/outputs/pair_scene_review_20261019_v1/targeted_tests.json)拥有19项通过/0.82秒及最终4份Python输入pin；未执行全仓测试。该UI观察只证明所列窗口和操作，不代表全部场景/衣发/表情视觉接受。

2026-10-19接入检查点等待用户点位、穿搭与精细近景审查，再讨论渲染计划；余38当时未启动。2026-10-20独立40人导入已完成，当前双人面板的场景继续迭代由场景Technical §22.8拥有；R17仍in_progress，无生产Gate晋升；旧17/18日回执不覆盖本版。`R/documentation_integration_sync_v1.json`由本Technical拥有，仅记录7owner与入口/catalog的有界文档一致性检查，不等于全树审计。


用户随后确认新版双人完整面板正确性正常，并要求减轻强逆光头发透明感。沙丘AF001/HB1_02/青绿色同机位5图局部对照显示：实际Masked遮罩正确；Scatter从1降至0.25改善有限，Alpha Multiplier 1.3/1.5增加发丝覆盖后漏亮明显减轻。头发额头亮带及脸部白斑另有镜头光斑叠加，临时关闭只作诊断，现已恢复。该局部对照交付时UE保留1.3临时动态材质预览，正式脚本/材质/标准十色/光照曝光未改；该旧局部对照切换外观或场景会恢复正式参数；此失效规则不适用于下述已固化的双人审查统一试用路径。用户已认可逆光候选带来的改善；当时尚未决定统一应用。后续已决定在本双人审查面板为全部发型统一试用1.3（见下文），正式MRQ仍未推广，全部精细质量未接受。依据：[result.json](../../../../../../00_engine/outputs/pair_scene_review_20261019_v1/hair_backlight_comparison/result.json)、[5图说明](../../../../../../00_engine/outputs/pair_scene_review_20261019_v1/hair_backlight_comparison/README.md)。

前序切换耗时诊断已完成，当时未实施优化；现已交付下述私有面板提速实现。当前同搭配缓存未命中重绑实测6.368秒，其中骨架兼容检查累计4.542秒、已有发色应用0.209秒、38槽赋值0.038秒；子项已包含在总时长内。历史仅换发型24/32/36秒的日志对应首次创建染色与coverage派生材质；新动作清空input_stats后约1.29GiB输入重哈希是代码确认路径，未单独计时，不能据此解释最近仅换发型的等待。当前常规输入检查0.012秒、场景签名/状态0.124秒、目录0.155秒，不是本场景几十秒等待的主因。依据：[诊断说明](../../../../../../00_engine/outputs/pair_scene_review_20261019_v1/switch_performance/README.md)、[拆分计时](../../../../../../00_engine/outputs/pair_scene_review_20261019_v1/switch_performance/profile.json)、[完整重绑](../../../../../../00_engine/outputs/pair_scene_review_20261019_v1/switch_performance/full_rebind.json)、[累计明细](../../../../../../00_engine/outputs/pair_scene_review_20261019_v1/switch_performance/full_rebind.txt)，同目录保留原始UE日志excerpt。该诊断阶段未改正式代码/资产，现场选择、网格和材质读回保持；上述旧计时只代表当时本机会话，不推广到首次加载或其他场景。

#### 双人私有面板提速交付（2026-10-19）

当前`S/pair_scene_review_20261019_v1.py`已接入下列4个本Technical拥有的`experimental`实现；对应测试为`utility`，只覆盖该两人审查私有模块图，不改变正式发布/渲染流程、源资产、十色配方或生产Gate：

| 实现/测试 | 本轮职责 |
| --- | --- |
| `S/pair_review_fast_runtime_v1.py` | 关闭普通预览的全资源重哈希及重复兼容审核；缓存目录、参考骨骼/跟随方式、表情准备与外观prepare，保留显式空间检查；首次表情正确传入两人目录/新版网格overlay，跨性别切换先释放旧Body的附属睫毛 |
| `S/pair_review_material_fast_v1.py` | 复用已有中性MIC/遮罩父材质及会话MID颜色缓存；coverage后全部实际发丝binding统一Alpha Multiplier=1.3，Hair134独立clip=.47边缘保护，详见下文；不向MIC编辑API传入MID |
| `S/pair_review_face_fast_v1.py` | 按实际身体/表情clip、性别与输出根复用成功合成记录和当前会话缓存，新组合只调用既有生成路径一次；不重跑数值接受或资源SHA审核 |
| `S/pair_review_transport_fast_v1.py` | 客户端复用持久连接；失败关闭会话并原样报告，不自动重试或重放命令，下一次用户请求才新建连接 |
| `S/tests/test_pair_scene_review_20261019_v1.py` | 新增普通交互不重哈希、私有提速接入与恢复路径回归，沿用本页原面板测试所有权 |
| `S/tests/test_pair_review_material_fast_v1.py` | MID/MIC类型边界、遮罩父材质与染色复用回归 |
| `S/tests/test_pair_review_face_fast_v1.py` | 表情目录/输出根约束、已有合成与新组合缓存回归 |
| `S/tests/test_pair_review_transport_fast_v1.py` | 持久连接复用、失败不重试及后续请求恢复回归 |

普通交互现返回`asset_validation_mode=disabled_for_fast_review`及`validation_performed=false`，不能把“可预览”当成执行了完整输入审核或兼容验收。资源仍在实际加载缺失时失败；审查会话中改变源资产后应重开UE及面板以重新建立会话缓存。显式空间检查、检查/保存/开图等场景快照失效路径保留；不把普通status缓存当成整场景重新审核。

限定实机时长见[12项UE内部操作](../../../../../../00_engine/outputs/pair_scene_review_20261019_v1/switch_performance/fast_matrix.json)：颜色/发型/服装/表情/动作/相机约0.05–0.25秒，切男约0.400秒、返回女性约1.135秒，12项success；这是UE内部调用时长。[完整客户端链路](../../../../../../00_engine/outputs/pair_scene_review_20261019_v1/switch_performance/fast_transport.json)另测启动目录1.077秒、已有同外观0.202/0.216秒、暖status约0.14–0.15秒，错误报告0.144秒，错误后的下一请求重连0.421秒成功。两类计时不得混为完整按钮交互速度或持续性能保证。

[首次新发型粉色](../../../../../../00_engine/outputs/pair_scene_review_20261019_v1/switch_performance/fast_new_hair.json)HAIR_HB3_17成功、4.241秒；[旧MIC同配置参考](../../../../../../00_engine/outputs/pair_scene_review_20261019_v1/switch_performance/reference_new_hair.json)成功、56.457秒。参考截图尚待确认，不能据耗时/结构成功宣称新旧画面逐像素一致、全部发型/十色覆盖或全组合接受。五份定向测试本轮独立复跑46passed/1.00秒（另root前序46passed记录保留），未执行全库重审。`R/switch_performance/fast_documentation_check.json`由本Technical拥有，记录本次定向owner/catalog/hash/证据检查及该独立测试结果。证据与当前场景恢复/面板重开由root串行交付，R17继续in_progress，余38导入未启动；本提速不启动渲染批次。

#### 全发型统一1.3审查试用（2026-10-19）

用户已决定在当前双人完整面板为所有发型统一试用`Alpha Multiplier=1.3`，自行逐款检查。此决定只固化本私有审查路径，不表示全部发型已视觉验收，也未推广正式MRQ。`S/pair_review_material_fast_v1.py`在原色和九种染色共同的coverage修正之后，对实际发丝bindings设置1.3的会话MID；隐藏槽及饰品不参与，切换外观/场景后的重新装配也沿此路径应用，不再是早先换外观即失效的一次局部预览。

HB1_01的Hair134遮罩JPEG边缘最高25/255，乘1.3并计入抖动后的上界约0.4608；为避免旧矩形发片重现，仅`opacity_repaired`分支在私有`/Game/DataMake/Validation/PairRevision20261019_v1/Materials/Density130/`建立覆盖父材质、clip=.47。其他原clip=.34不改，不修改源材质或正式共用遮罩逻辑。对应`S/tests/test_pair_review_material_fast_v1.py`已更新边缘保护断言，root本轮实际11项通过/0.52秒；本次文档同步未重复测试或逐发型渲染。

[当前应用读回](../../../../../../00_engine/outputs/pair_scene_review_20261019_v1/hair_density130/application.json)success=true：用户新选AF001/HB1_11（5号长马尾）原色，3个实际发丝槽before均1.0、after均1.29999995，当前selection和preview保持。[本轮说明](../../../../../../00_engine/outputs/pair_scene_review_20261019_v1/hair_density130/README.md)记录边界；`R/apply_density130.py`为本Technical拥有的现场热装私有Session入口。此证据只证明当前选择实际读回及通用代码接入，不代替全部发型/颜色/场景的画面验收。root已重开面板ready（PID51188，`R/panel_lifecycle.json`更新11:59:06 UTC、error=null），用户可直接逐款审查；原R17和余38未启动边界保持。

#### 当前改用全发型1.5审查试用（2026-10-19）

用户随后要求所有发型统一1.5继续查看，本私有双人面板当前`REVIEW_ALPHA_MULTIPLIER=1.5`替代上述1.3，1.3只保留历史。Hair134专用父材质改为`Density150`、clip=.49（25/255×1.5＋1/3≈.4804，避免旧JPEG边缘复现），其他既有clip保持。[当前实机读回](../../../../../../00_engine/outputs/pair_scene_review_20261019_v1/hair_density150/application.json)成功：沙丘当前HB3_14（35号）原色3个发丝槽从1.3变为1.5，保留当前选择/预览。材质源及对应测试预期已改为1.5/.49，本轮按用户要求未重跑测试或审计。此为统一审查试用，不代表全发型视觉接受或正式MRQ推广；root串行重开面板，其他边界保持。

#### 轻微地形整体高度跟随接入（2026-10-19）

当前面板已接入整体ActorZ地面差值跟随，保持原动作起伏、人物直立及相机路径；不做IK或楼梯。AM001沙漠加油站/1的2.5→5→2.5秒三次实机调用成功，重复时刻offset一致、原预览已恢复；只是运行确认，未做视觉审查/渲染。完整公式、源码和两份证据由[场景Technical §22.7](./SCENE_CAMERA_SEQUENCE.md#227-轻微地形整体高度跟随2026-10-19运行确认完成用户视觉待审)拥有，正式render仅源码接入同helper，尚无实际渲染接受。root已重开面板ready（PID23716，error=null），当前沙漠加油站/1搭配和时刻已恢复，用户可直接自行审查轻微地形和统一1.5发型效果；原R17/余38边界保持。

#### 双人审查启动继承几何的私有快速路径（2026-10-20）

本轮仍遵循用户已授权的快速审查策略：`S/pair_review_fast_runtime_v1.py:disable_startup_asset_audits()`只在选定私有`PrivateModules`图中跳过`production_motion_contract_v1.verify_pin`及继承启动几何的`scene_site_review_geometry_v1.verify_sources`。启动几何的历史来源早于后续sequence变化，不改写其旧SHA或在每次审查重启时重新执行历史审计；实际缺失文件仍读取失败。正式发布/渲染加载器、全局共享模块及另一独立私有图的验证器保持原检查。

`S/tests/test_pair_scene_review_20261019_v1.py`新增真实私有图隔离测试，[37项相关测试回执](../../../../../../00_engine/outputs/scene_review_iteration_20261020_v1/camera/pair_review_scoped_tests.json)记录四份pair测试全部通过，并证明全局及第二私有图仍拒绝错误SHA。它只证明启动策略的隔离与缺文件行为，不代替角色资产、场景、碰撞、画面或生产Gate。本轮私有状态响应仅记录另38人未接入面板，不再误报其独立导入尚未开始；未来都市缺保存点时菜单显式提示待选。当前点位/镜头/地面继续迭代及root串行运行结果由[场景Technical §22.8](./SCENE_CAMERA_SEQUENCE.md#228-已审查点位继续迭代2026-10-20)拥有；修改后40人独立导入完成不自动把另38人加入本面板。

## 2026-10-12 清理后的当前动作读取与依赖恢复

清理候选审查漏掉 `complete_character_review_contract_v1.py` 及槽位catalog对旧 `first_batch_motions_20260822_v1`、`first_batch_cleanup_20260824_v1` 中轻量JSON的真实运行依赖，旧目录删除后不能再直接调用原读取链。这是依赖漏判，不描述为从未受影响。

修复没有伪造或恢复已删的八月导入成功报告。当前动作权威迁入 `00_engine/assets/character_creator/current_review_actions_20261012_v1.json`，派生导入FBX位于 `00_engine/assets/character_creator/review_motion_sources_20261012_v1/`。新配置基于保留的10份 `animations/ACT_*_v002.json` 复制回执核对原UE包路径、Skeleton与SHA；原始FBX按保留的导出SHA验证，再仅重建骨名称规范化的FBX。旧graph/action_pool继续限制原10动作集合。

`complete_character_review_contract_v1.current_actions(sources)`为统一实读入口；`complete_character_slot_review_contract_v1.py`委托该入口。每次catalog检查当前配置、graph/pool、复制回执、UE包及源/规范化FBX的SHA，sources暴露current_action_registry、current_action_graph/current_action_pool、action_reports与action_packages，不再要求旧normalized_manifest/cleanup_result。此项是当前数据读取恢复，不新增UE播放、重导验收或跨性别兼容结论。旧已保存配置若锁定旧sources，应重新选择并保存当前配置，不能静默假装旧SHA一致。

恢复依据为 `%OUTPUT_ROOT%/workspace_cleanup_20261012_v1/current_actions_runtime_recovery_v1.json`，6项定向测试见 `contract_recovery_tests_v1.xml`。实际离线入口验证见同Run `current_entry_offline_smoke_after_dependency_recovery_v1.json`：现用衣发鞋catalog、40身份、十发色、四表情48组合及完整面板默认request通过；实际打开文件路径记录用于后续清理保护。它不操作UE，也不是面板可见交互测试。

### 2026-10-12 旧一次性脚本退役

旧第一批动作/粗糙表情的单次执行和审查脚本已清理，精确列表见 `%OUTPUT_ROOT%/workspace_cleanup_20261012_v1/batch06_retired_scripts.json`。本页相关早期步骤仅为历史，不再作为当前命令；当前角色使用CFD40模块化入口及四类原速表情。旧字节证据不改写为新验收，现用脚本和配置按当前Registry读取。


完整回归进一步确认两份旧 `runtime_validation` 保存配置属于历史验证driver，当前UI不自动读取；`saved_configuration_scope_review_v1.json`记录这一范围。生产loader保持严格SHA拒绝，旧配置没有静默迁移或改写。模拟driver测试改为将原选择与当前catalog生成临时fixture，7项复测通过，另增旧配置拒绝测试通过。文档fixture因TEMP改到仓库内而误推断真实repo根，现仅在测试内隔离，34项文档复测通过；生产审计不变。总证据 `regression_reconciled_v1.json`按唯一testcase合并完整运行和针对复测，不能称为一次全绿完整运行。
