# 面部外观与毛发资产

> 文档 ID：`TECH-CC-02`
> 文档类型：`technical`
> 生命周期：`current`
> 适用阶段：`WF-20/WF-30`
> 实现所有权：Appearance Catalog、Compatibility Registry、Pigmentation Policy 和视觉门禁
> 验证所有权：`VAL-MATRIX-01`（外观资产子项）、`VAL-CC-01`
> 输出契约：`OUT-WF20-ASSET-MATRIX`、`OUT-WF30-CC-ASSETS`
> 最近核验：2026-09-30（发型批量、兼容规则与覆盖层视觉结论对齐）

## 1. 能力与边界

外观资产包括皮肤、眼球材质、牙齿、眉毛、睫毛、头发和胡须。可以替换不等于任意组合自然；性别偏好、皮肤色素、毛发颜色、眼口几何和服装冲突必须由 Registry/Policy 控制。

## 2. 机器入口

| 文件 | 作用 | 状态 |
| --- | --- | --- |
| `cc_appearance_asset_catalog_v1.json` | 资产 ID、路径和类型 | `production` |
| `cc_appearance_compatibility_v1.json` | 性别/部件兼容结果 | `validated_pilot` |
| `cc_appearance_domain_policy_v1.json` | 皮肤与毛发色素域 | `validated_pilot` |
| `cc_facial_hair_asset_catalog_v1.json` | 胡须候选 | `validated_pilot` |
| `cc_scalp_hair_asset_catalog_v1.json` | 头发候选与性别偏好 | `validated_pilot` |
| `cc_eyelash_compatibility_batch_v1.json` | 睫毛兼容输入 | `validated_pilot` |

生成器包括 `cc_build_appearance_asset_catalog.py`、`cc_build_appearance_compatibility_registry.py` 及各部件批次/汇总工具。运行时统一由 `cc_validate_body_reconstruction.py` 执行受控配置；发型 Pilot 的清单准备由 `cc_prepare_scalp_hair_export_v1.py` 负责。首个 `hb1-01` 已完成资产加载、项目保存和自动 FBX/JSON/纹理导出验证。

## 3. 当前已验证池

当前历史证据覆盖 21 套皮肤、12 套眼球材质、13 套眉毛、9 套睫毛、2 套牙齿、5 套胡须和 58 个发型候选。数字只表示已盘点/验证边界，具体生产启用由批次矩阵决定。

眼球资产主要改变材质，但仍需检查极端视线、闭眼和眼皮遮挡。牙齿需要张嘴和微笑检查。睫毛和眉毛可以跨多种脸型，但必须保留资产应用时产生的支持状态。

## 4. 色素策略

2026-10-07当前UE成品运行时范围另见[Runtime3.17](../unreal/CHARACTER_RUNTIME.md#317-女性共享鞋发型分类与颜色实验2026-10-07)：用户取消本次发型分组，直接使用男女最终保留集合；眼色保留角色原色，不作为本轮多样性维度，发色独立扩充。旧CC外观集成Registry中的silhouette_family分层与iris_color_is_independent描述仍是该旧路线的输入/历史语义，不是当前40人成品UE运行时的选择配置，不据此重新要求分组或启用眼色随机化。

角色先根据皮肤/身份选择自然色素档案，再从档案抽取统一毛发颜色，应用到头发、眉毛和胡须。自然模式不从全局颜色池无条件采样；染发和罕见模式必须显式标记，不能伪装成自然分布。

## 5. 头发和胡须

- 发型有 `male_default`、`female_default` 和可选跨性别呈现标签。
- 第一批使用烘焙 Look，不在 UE 中任意替换头发。
- 长发、兜帽、头巾和高领服装存在相交风险；批次 Matrix 必须登记组合。
- 胡须可以作为有/无变体研究，但网格适配仍需按头面验证。

当前 60 组 Hair Builder 头发已完成男女代表脸的六视图兼容性证据，但第二批生产池尚未冻结。为处理外观相似度过高的问题，已建立逐项人工筛选清单 [cc_scalp_hair_selection_review_v1.json](../../../../../../00_engine/scripts/character_creator/cc_scalp_hair_selection_review_v1.json) 和决定文件 [cc_scalp_hair_selection_decisions_v1.json](../../../../../../00_engine/scripts/character_creator/cc_scalp_hair_selection_decisions_v1.json)。清单按头发资产顺序记录正面、四分之三、侧面、后三分之四和背面视图，并允许 `keep`、`remove`、`hold` 三种决定；用户已明确最终保留 40 组、屏蔽 20 组，决定文件已同步为 40 `keep`、20 `remove`。这确定发型资产池，不等于逐个身份的发型适配已经验收。

当前已有的六视图接触表可供预审。`hb1-01` 已完成首个 UE 视觉审查关卡搭建，但该关卡仍是人工观察证据，不能把 CC 端静态六视图证据或单个 UE 试验误写成 40 个候选的兼容性已完成。

首个发型 Pilot 使用女性中性基础项目和 `hb1-01`（`CCAPP_SCALP_HAIR_723181d44a4d`）。自动流程已成功加载头发并保存项目；首次使用较长输出路径时 FBX 返回 `status_code: 1`，改用 `D:/UE/exports/character_creator/` 下的短暂存路径后导出成功。成功证据为 `%OUTPUT_ROOT%/character_creator_bridge/artifacts/scalp_hair_shortpath_pilot_20260923_111307/validation_result.json`，产物包含 UE5 骨骼配置下的无动作 FBX、同基名 JSON 和纹理目录。该次 DRM 检查返回成功，未发生人工点击；长路径失败应按 CC 辅助纹理路径限制处理，而不是按每个发型需要手动 Pack 处理。该单款试验本身不代表批量通过；后续 2026-09-24 的全库批量验证已完成，见下段。

2026-09-24 的批量导出和 UE 导入均已完成并通过机器结构验证：40 个保留发型均有独立 `.ccProject`、FBX、JSON 和纹理目录，输出根为 `%CC_EXPORT_ROOT%/scalp_hair_batch_20260924_v1/`；批量导入脚本为 `00_engine/scripts/unreal/ue_scalp_hair_batch_import_v1.py`。UE-Cmd 报告为 40/40 成功，每项生成 8–17 个运行时发型网格，全部绑定女性 F02 Average 共享 Skeleton，材质引用均存在。此前待确认的发丝细节、颜色、位置和材质表现已通过用户观察；剩余的组合级判断已由 2026-09-26 的发型×服装视觉审查收口。2026-09-29 的 UE 单文件索引另为这 40 个保留发型标注 `male/female/both` 使用分类，详见[模块化 Transfer 第 11.2 节](../transfer/CC_TO_UE_MODULAR_OUTFIT_PILOT.md#112-保留发型的使用性别标记2026-09-29)；该字段不替代逐角色头型适配验收。

2026-09-29 在更大的全库六视检查中发现：此前单款 Pilot 的 Masked 发片材质修复未覆盖全部 40 款，批量网格虽引用存在的 FBX Phong 材质，视觉上仍会出现大片发片或不正确透明度。已对 220 个发丝/头皮槽统一修复并独立进程重载核对；余下 51 个实体辫子和发饰等槽未自动改动。标准 F02/M02 的 51 个 Case、306 张照片完成，助手记录了若干头皮覆盖和配色疑点，该轮当时用户视觉验收待完成；2026-09-30 发丝 V2 与覆盖层网格处理的后续结果见下段。运行时审查和具体问题清单见[UE 运行时 3.7 节](../unreal/CHARACTER_RUNTIME.md#37-平均体型发型六视审查与发片材质修复2026-09-29)。这项新证据收窄了前述单款 Pilot 的“材质正常”结论，不能把它外推为全库发型通过。

2026-09-26 已建立女性发型×服装穿模视觉审查入口。审查计划 `%OUTPUT_ROOT%/unreal_character_import/hair_outfit_compatibility_20260926_v1/compatibility_plan.json` 从衣柜 Registry 和已完成的 UE 模块报告解析 8 个女性连衣裙 `Full-body` 模型、`WarriorCloak_A`、`Windbreaker_A` 与 40 个发型，共 400 个逐项组合；男性 `redsoul`/`Rugged & Trendy Collection`、女性 `Rugged & Trendy Collection`、B/C 换色件及其他衣柜均明确排除。审查关卡为 `/Game/DataMake/Validation/ScalpHairCompatibility/L_DM_ScalpHairCompatibility_Review_v001`，构建入口为 `00_engine/scripts/unreal/ue_build_hair_outfit_compatibility_review_v1.py`，桌面控制入口为 `00_engine/scripts/unreal/run_hair_outfit_compatibility_review_v1.py`。该关卡只用于人工视觉决定，不修改正式服装 Blueprint；初始机器计划中的 `visual_acceptance=pending` 已由下段的人工决定记录收口，不回写原计划为按钮日志。

2026-09-26 用户完成相关 UE 视觉审批并明确给出最终范围结论，虽然没有使用控制面板上的选择按钮，结论仍以用户明确陈述作为人工审查证据保存：连衣裙 `Full-body` 的 8 个模型全部允许 40 个保留发型，共 320 个允许组合；`WarriorCloak_A/B/C` 与 `Windbreaker_A/B/C` 共 6 个潮牌外套变体全部不加载发型，共 240 个排除组合。审查证据为 `%OUTPUT_ROOT%/unreal_character_import/hair_outfit_compatibility_20260926_v1/manual_review.json`，版本化排除规则为 `00_engine/assets/character_creator/outfit_compatibility_aliases/hair_outfit_compatibility_exclusion_registry_20260926_v1.json`。这次人工视觉结论只覆盖已审查的女性 F02 Average 范围；用户随后另行确定正式索引对未明确 `deny_all` 的服装默认 `allow_all`。默认允许是组合策略，不等于未审查角色头型的视觉适配结论。

控制脚本的视角切换沿用衣柜 Review Level 的约定：固定相机位于角色前方，角色使用 `front=-90°`、`side=0°`、`back=90°` 的朝向映射。每次远程按钮调用都会强制刷新实时编辑视图并重新进入 Game View，避免 UE 窗口未获焦点时视口不更新；该刷新只作用于审查关卡实例。

自动导出的生产约束是：导出根目录必须使用较短路径，避免 CC 辅助纹理写入超过路径限制；`production_output.export_motion` 默认关闭；`export_motion=true` 仅用于隔离诊断。正式批量使用唯一的发型/性别文件名，并保留项目、FBX、JSON 和纹理目录的同基名关系。

`hb1-01` 的首个 UE 导入 Pilot 已通过：使用项目中可发现的 F02 模块化服装 Interchange 管线，并在命令行导入时临时开启 `Interchange.FeatureFlags.Import.FBX`。完整参考目录生成 10 个独立骨骼网格，其中 4 个发型网格被复制到 `Modules`；4 个运行时网格均绑定现有女性 F02 基础 Skeleton，未创建新的 Skeleton 或 Physics Asset。机器证据为 `%OUTPUT_ROOT%/unreal_character_import/scalp_hair_pilot_20260923_111307_interchange/ue_import_report.json`，实现入口为 `00_engine/scripts/unreal/ue_hair_pilot_import_v1.py`。这只证明当时单个导出到 UE 的结构映射可复用；后续批量和服装兼容结论分别查本页 2026-09-24、2026-09-26 记录。

当前已生成临时视觉审查关卡 `/Game/DataMake/Validation/ScalpHairPilot/L_DM_ScalpHairPilot_Review_v001`，由 `00_engine/scripts/unreal/ue_build_scalp_hair_review_level_v1.py` 创建。关卡在 M02/F02 平均体型角色上分别挂载 `hb1-01` 的四个运行时网格；女性使用同骨架 Leader Pose，男性记录为跨骨架视觉探针。用户已确认头发能够正确放置、显示并跟随角色，脸部颗粒纹理问题暂时忽略。该确认只关闭单个 Pilot 的视觉阻塞，不代表 40 个候选批量或服装组合兼容性通过。

首轮 UE 导入将材质导入关闭，导致运行时网格暂时使用 `WorldGridMaterial`，并且自动生成的 FBX Phong 材质为不透明混合，头发卡片因此显示成块状。已通过 `00_engine/scripts/unreal/ue_repair_scalp_hair_materials_v1.py` 开启材质/纹理导入，再由 `00_engine/scripts/unreal/ue_build_scalp_hair_material_instances_v1.py` 将透明度纹理接入项目现有的 `RL_Hair_Specular` Masked 材质。修复证据为 `%OUTPUT_ROOT%/unreal_character_import/scalp_hair_pilot_20260923_111307_interchange/hair_material_repair_v1.json` 与 `hair_masked_materials_v1.json`；用户观察确认发丝细节和位置正常，组合级穿模结论见本页 2026-09-26 的审查记录。

首版视觉关卡把头发作为独立 `SkeletalMeshActor` 挂载，保存重载后跨 Actor Leader Pose 引用会丢失，导致身体播放动作而头发停留在参考姿态。已由 `00_engine/scripts/unreal/ue_repair_scalp_hair_review_alignment_v1.py` 移入审查关卡实例已有的 `BundlePart01..04`，利用其持久化 Body Leader Pose 绑定；该修复不修改正式 Blueprint。重载验证证据为 `%OUTPUT_ROOT%/unreal_character_import/scalp_hair_pilot_20260923_111307_interchange/hair_visual_review_alignment_repair_v1.json`。

用户进一步发现脸部出现发丝状颗粒纹理。检查确认视觉审查实例中的头发组件默认开启阴影投射；已在 M02/F02 的 `BundlePart01..04` 上关闭 `cast_shadow`，保留网格、Masked 材质、透明度纹理和 Body Leader Pose 不变，并保存重载关卡。对照证据为 `%OUTPUT_ROOT%/unreal_character_import/scalp_hair_pilot_20260923_111307_interchange/hair_shadow_artifact_probe_v1.json`；后续整体隐藏头发后纹理仍未消失，用户要求暂时忽略，不作为头发缺陷继续阻塞。该设置只作用于 Review Level 实例，不代表正式头发槽位的最终渲染策略。

当时关闭头发阴影后纹理仍待确认，因此执行整体隐藏对照：已将 M02/F02 的四个头发网格设为不可见，身体、服装、灯光和相机不变，并保存重载。证据为 `%OUTPUT_ROOT%/unreal_character_import/scalp_hair_pilot_20260923_111307_interchange/hair_visibility_probe_v1.json`；该对照仍属于 Review Level 临时状态。

2026-09-30 后续全库发丝材质 V2 已完成磁盘重载与新六视图机器验证。规则黑网格定位为 Scalp/Hairline 覆盖层的抖动透明效果；用户在审查候选和 Hairline 补充对照后确认网格不再出现。此子范围的人工决定与待实施精确槽位清单见[运行时 3.7.6](../unreal/CHARACTER_RUNTIME.md#376-覆盖层隐藏策略的用户确认与实施边界2026-09-30)。正式隐藏设置尚未持久化，现有所有网格仍来自 F02 导出；男性穿模按用户要求后置，使用性别标签不代表男性头型适配通过。

### 5.1 第二批候选范围与服装兼容

第二批先为每个身份筛选约三套适配发型，并保留胡须有/无外观变体；具体数量由候选质量和视觉检查结果决定，不在候选筛选前冻结。发型/胡须不默认跨身份或跨体型互换。

发型与服装是组合级兼容关系。长发、兜帽、头巾、高领和其他头部服装可能在静态或动作中穿模；资产本身通过不代表组合可用。用户已人工筛掉明显无风险服装，只对所选女性服装做发型交叉审查；最终明确采用“除 deny_all 外默认 allow_all”的全库规则，见本页 2026-09-26 记录和正式 UE 单文件索引。已知禁用组合不得进入矩阵和图构建；未来新资产、头型或动态范围仍需单独验证，不能把默认允许解释为逐组合视觉通过。

## 6. 应用顺序

```text
Identity/BodyFit
  -> Skin
  -> Eye/Teeth
  -> Brows/Eyelashes
  -> Hair/Beard
  -> Pigmentation/material settings
  -> static and dynamic acceptance
```

不得为了替换一个部件把所有未关注 Morph 清零。应用后检查中性、眨眼、闭眼、微笑、张嘴和材质接缝。

## 7. 输出与保留

Catalog、Compatibility 和 Policy 为 `authoritative` 或 `retained_evidence`；批次截图由视觉决定引用后为 `retained_evidence`，重复轴扫描可降为 `superseded`。准确视觉入口见 [视觉审查](../validation/VISUAL_REVIEW.md)。

本能力拥有以下历史输出根及启动诊断：

```text
%OUTPUT_ROOT%/character_creator_content_acquisition/
%OUTPUT_ROOT%/character_creator_content_migration/
%OUTPUT_ROOT%/eyebrow_runner_boot.stdout.log
%OUTPUT_ROOT%/eyebrow_runner_boot.stderr.log
```

它们用于内容采购/迁移审计和早期眉毛 Runner 诊断；当前未评为 `superseded/disposable` 的项继续受保护。

## 8. 失败与恢复

资产应用失败、眼口偏移或材质异常时，从干净规范项目重新加载 Identity/BodyFit，再只重放已登记的外观步骤；不得通过清零未知 Morph、覆盖源资产或连续点击未知弹窗修补。单一资产失败时隔离该资产并保留失败组合与截图，其他已通过资产可以继续；修复后生成新 Compatibility 结果，不原地改写已接受证据。
