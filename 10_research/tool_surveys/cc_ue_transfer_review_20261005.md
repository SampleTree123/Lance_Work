# 新角色、旧服装与身体／面部动画的衔接核查

> 核查日期：2026-10-05。范围：现有项目文档、脚本、历史实测回执、本机接口声明与官方资料。
> 本文是研究结论和待实施规范草案，不是新角色已通过 UE 验收的证明，也不替代 `full_process` 的正式 Technical、Status 或 Plan。
> 本轮没有操作 CC／UE，没有新导出、导入、修改角色或改动生产脚本。

**建议先保留已有服装，建立“静态角色、身体动作、面部动作分开导入”的流程；面部先实现自然、轻微的一段表现，再依据实际依赖裁减数据。**没有证据要求全库服装重新导出，也没有证据支持新角色直接关闭全部 Morph。

这份工作延续 Claude 之前对换装、动画与渲染接口的检查。已经整合进角色创建流程的装配几何检查不重复实现；本轮补充它与 UE 的连接条件、已知失败原因和可节省的数据。

## 1. 新角色能否继续穿旧衣服

**优先尝试直接复用。是否重新导出，要由实际身体和绑定数据决定。**

旧衣柜已有用户于 2026-09-22 确认的外观、合身、材质与动画检查；不是未经检查的素材堆。但它覆盖原男女 Average 身体及当时审查组合，不自动覆盖新生成角色、任意搭配和全部新动作。人工确认与旧机器报告里仍为 pending 的字段是两类记录，不能相互改写。[已有验收范围](../../20_planning/data_design/character_creator/full_process/project_management/status/workflows/WF-50.md)

| 新角色与旧衣服的实际关系 | 应怎样处理 | 是否重新从 CC 导出 |
| --- | --- | --- |
| 身体贴合，衣服有权重的骨及祖先层级、参考／绑定变换兼容 | 复用旧 UE 衣服网格、材质和纹理，由新 Body 通过 Leader Pose 驱动 | 不需要 |
| 几何与蒙皮可用，只需建立新的资产关联 | 优先评估已有服装 FBX 分离导入到目标 Skeleton；UE 内重新关联只能先在副本验证 | 不需要重新从 CC 导出 |
| 排除错误动画、骨映射、组件变换和导入绑定后，确认身体尺寸、服装形状或蒙皮不适配 | 回 CC 对相应体型 Conform 修形；确有权重问题再修蒙皮，检查动作后导出该适配版本 | 只重做受影响衣服／体型 |

这里要分清三个概念：

- **Skeleton 资产相同**，不能单独证明衣服合身；资产不同，也不能单独证明不能跟随。
- **Leader Pose** 传递骨骼姿势，不替衣服改变尺寸或重新蒙皮。UE 5.8 本机源码按两个 SkeletalMesh 各自的骨名建立映射，没有比较它们的 `USkeleton` 对象是否相等。但未匹配的额外骨、不同层级或绑定关系仍会出问题。[本机实现](D:/UE/UE_5.8/Engine/Source/Runtime/Engine/Private/Components/SkinnedMeshComponent.cpp:3470)、[Epic 模块化角色说明](https://dev.epicgames.com/documentation/en-us/unreal-engine/working-with-modular-characters-in-unreal-engine)
- **Compatible Skeletons／动画重定向**解决动作使用问题，不负责服装修形。直接 `SetSkeleton` 也只是引用赋值，不能代替完整的关联、保存重载与变形检查。[本机 SetSkeleton](D:/UE/UE_5.8/Engine/Source/Runtime/Engine/Classes/Engine/SkeletalMesh.h:766)、[Epic Skeletons 说明](https://dev.epicgames.com/documentation/en-us/unreal-engine/skeletons-in-unreal-engine)

当前项目还有两个明确的接入限制：换装代码要求衣服与 Body 的 Skeleton 对象相等；正式运行时入口硬编码旧 `M02_Average`、`F02_Average`。因此即使新旧结构兼容，也不能声称现有入口已经支持新角色。后续应增加已验证的新 Body 配置和兼容关系，保留失败检查，不能直接删除检查放行。[换装检查](../../00_engine/scripts/unreal/ue_build_modular_outfit_runtime_v2.py:570)、[身体入口](../../00_engine/scripts/unreal/ue_formal_wardrobe_runtime_v1.py:27)

已有分离导入和按材质槽重新匹配材质的方法可以复用；材质应取自当前正式 Registry，不能照搬已经退役的旧资产路径。重新导入同一个 FBX 不会自动解决穿模。[服装转移实现](../../20_planning/data_design/character_creator/full_process/technical/transfer/CC_TO_UE_MODULAR_OUTFIT_PILOT.md)

如果新身份仍严格保持相同规范身体，衣服适配应优先按性别／体型复用，而不是每张新脸导一套衣服。这是条件性建议，须以最终 FBX 和 UE 动作下的身体保持结果确认。当前新自动化角色尚无完整 UE 转移证据。

## 2. 身体与面部动画怎样结合

### 身体：继承处理方法，换掉旧素材假设

用户将从 CC 重新选择动作，因此本轮不逐个修旧动作资产。值得保留的是：清理并检查时间轴、显式加载来源、记录真实范围与采样率、统一骨名、明确根运动、单独导入动画，以及为渲染指定播放区间。

旧代码把原身体动作变成 BodyOnly：保留身体和头颈，删除十条面部骨轨，并清空曲线／属性。这里删除的是动画轨道，不是角色骨骼。旧素材的结果可以作为实现参考；新素材应先识别曲线用途，不能把身体纠正变形、必要属性也一起清除。带有不可分离表演关系的动作应保留为成对身体＋面部片。[旧处理实现](../../00_engine/scripts/unreal/ue_import_first_batch_motions.py:353)、[动作转移文档](../../20_planning/data_design/character_creator/full_process/technical/transfer/MOTION_TRANSFER.md)

原地或有位移应按动作决定：不能为了让角色留在镜头里统一清零根骨而造成滑步，也不能让角色根运动与 Actor 位移重复叠加。动作源、根运动策略、导出／导入采样率和实际渲染 FPS 应分别记录。

### 面部：先做一段自然表现，不增加表情编辑轴

建议先选一段以中性为主、自然眨眼、轻微眉眼／嘴角变化的短片。视线变化应服从身体动作的朝向和动作目的；先不加入大幅情绪、说话口型或持续微笑。三秒的微笑／张嘴校准片适合验证变形能力，不适合作为自然循环。

素材来源按以下顺序评估：

1. **先检查已安装 MotionPlus。**本机存在 `Animation/Motion Plus/Animated/1.Acting/04_Neutral/Idle_01_N.iMotionPlus`，以及男女 Idle 片。文件名仅证明候选存在，尚未播放确认是否包含合适的面部数据，不能直接称其自然可用。
2. **现有素材不合适时，评估 Digital Soul 的意识／观察类片段。**官方定位包含细微自然面部行为；选择极少数片段即可。当前检查的素材目录未找到对应名称，未确认安装或授权，也没有购买。高级附赠片有额外表情配置要求。[官方介绍](https://www.reallusion.com/ContentStore/iClone/pack/digital-soul-100/)
3. **需要真人表现时，再考虑 MetaHuman Animator 到 CC 的转换。**官方提供 UE 表情导出 CSV、CC／iClone 导入并可排除头部旋转的流程。它是可研究的备用来源，不是本机已经跑通的新能力；其插件和角色表情配置还需核对。[官方转换流程](https://manual.reallusion.com/Metahuman-Interoperability/Content/MetaHuman-Interoperability/17-Metahuman-Interoperability/Transferring-UE-Expressions-to-CC.htm)

### 合成：保留身体头颈，只替换面部所属的轨道

当前更贴近已有渲染器的方案是**离线生成一个合成 AnimSequence**：

1. 身体和面部源动画分别导入静态角色实际使用的 Skeleton。
2. 保留身体的 root、pelvis、四肢、脊柱、head／neck；只合入批准的面部骨骼局部变换，不能把面部源里静止的全身轨道一并覆盖过去。
3. 合入对应 Morph 曲线和纠正曲线，明确眼球、下颌、牙、舌的驱动归属。
4. 对齐采样率、时长、过渡和循环端点。头颈保持身体动作的运动；眼睛不再同时由另一套 Look-at 覆盖。
5. 保存为一个可确定性播放的动画；防止 Post Process、直接 Morph 和额外表情控制器重复驱动同一通道。配对数据中固定片段、相位和强度，避免每个编辑节点重新随机面部。

**这部分需要扩展旧实现。**旧 Composite builder 只是复制 BodyOnly，再写 Happy Morph 曲线，没有合并完整面部骨轨。不能把旧成功等同于已支持新 hybrid 表情。[旧合成代码](../../00_engine/scripts/unreal/ue_build_first_batch_action_expression_composites.py:216)、[动画职责规则](../../20_planning/data_design/character_creator/full_process/technical/unreal/ANIMATION_EXPRESSION_MORPH.md)

复用的是面部表演素材，不预先承诺同一个面部 AnimSequence 可用于所有身份。第一轮建议把相同表演应用到各代表最终角色，由 CC 求值后导出；骨骼局部平移与角色的参考姿势可能有关，指定另一个 Skeleton 并不会自动完成适配。后续确认面部绑定与变形兼容后再共享动画，否则保留按角色求值或按目标参考姿势转换的步骤。

已有独立样例证明静态网格＋单独动画导入可以正确联动眼、下颌、牙和舌；它没有证明所有新身份和新身体动作均兼容。此前仅靠同名同层级骨架／Compatible Skeletons 仍出现眼球穿出，改成向静态网格实际 Skeleton 导入动画后才解决该案例。[表情导入诊断与后续限定验收](../../20_planning/data_design/character_creator/full_process/technical/character_creator/BODYFIT_IDENTITY_AGE.md)

## 3. Morph 到底留什么，哪些数据可以省

首先把“预存变形”分成不同用途。

| 数据 | 当前建议 | 原因和边界 |
| --- | --- | --- |
| CC 中塑造身份、年龄、体型的创作滑块 | 最终形状已烘焙、UE 不再改形时，不要求逐项保留为 UE 可调 Morph | 保存原 CC 项目与来源；先确认没有被后续流程使用，不是删除角色已烘焙形状 |
| 面部表情 Morph | 保留所选面部片所需的目标 | 当前面部效果不是纯骨骼；不能全关 |
| corrective／组合纠正形变 | 保留被所选动作实际驱动的依赖 | “只眨眼微笑”不等于仅有两三条曲线；要连同闭眼、嘴角组合纠正检查 |
| 下颌、眼、牙、舌等骨骼与动画轨道 | 保留需要的骨和轨道 | Morph-only 和 bone-only 都不能直接替代已验 hybrid 输出 |
| 衣服／头发的 Morph | 按部件需要决定 | 普通蒙皮跟随不必依赖 Morph；体型、表情或姿势纠正用到的不能删 |
| 每段动画携带的重复网格／贴图 | UE 中不再重复导入；轻量源导出另做小样验证 | 优先节省可确定的重复成本 |
| 每件衣服独立 PhysicsAsset | 当前纯 Leader Pose 路线不创建 | 将来需要独立布料／头发物理时另定；不能顺带删除必要骨骼 |

本地真实回执支持保留 hybrid：代表片在 UE 中有 118 条骨轨和 127 条浮点曲线，其中 50 条 `C_` 纠正曲线，部分明显非零。单独写 jawOpen Morph 曾未能完成真实张嘴；完整片包含下颌骨和牙舌配合。样例 Body 的 293 个 Morph 是 UE API 的实际读数，不是文件字符串计数，也不是新角色必须固定达到的数量。[导入和 Morph 读取实现](../../00_engine/scripts/unreal/ue_headshot_normal_probe_v1.py:184)

**不建议一开始就做“全保留／全删除”的二选一。**先保存一份完整来源，以最终采用的面部片和身体纠正建立依赖清单，再比较裁减前后眼睑闭合、嘴角、牙舌、脸型、动态法线及实际画面。没有通过的裁减不能成为默认设置。目前没有完成全关 Morph 的逐帧消融，也没有可承诺的空间节省比例。

CC 的 `Convert Skinned Expressions to Morphs` 是把骨骼／蒙皮表情转换为 Morph 的另一种表达方式；`Mouth Open as Morph` 是单独的张嘴转换选项。它们都不是“去掉不需要的预存变形”的通用优化开关。[CC5 官方定义](https://manual.reallusion.com/Character-Creator-5/Content/ENU/5.0/17-Export/FBX-Advanced-Settings-Character.htm)

本机 SDK 确有 `RemoveUnusedMorph`、`RemoveAllMeshKeepMorph` 枚举，但枚举名称不能证明“可按任意白名单裁剪且无损”。已查项目没有完成这种用法的验证；UE 通用网格导入接口的 `import_morph_targets` 则是全量形状导入开关，未发现该通用面板暴露任意 Morph 名单筛选。因此精简需要专门的导出／导入或派生资产步骤，不能声称现成一个选项已解决。[本机 RLPy](D:/CharacterCreator/Character%20Creator%205/Bin64/RLPy.py:6577)、[本机 UE 网格接口](D:/UE/UE_5.8/Engine/Plugins/Interchange/Runtime/Source/Pipelines/Public/InterchangeGenericMeshPipeline.h:218)

## 4. 可写入后续实施规范的接口草案

### 版本和共同约定

2026-10-05 读取安装文件：CC `5.02.0923.1`；UE `5.8.1`；主工程 RLPlugin 的 `VersionName=2.03`，描述文件目标 EngineVersion 为 `5.8.0`。这是文件版本核查，不等同于本轮重新完成插件加载兼容测试。实现以本机接口和成功回执为准，不能直接照抄较旧 SDK 网页签名。[本机 SDK](D:/CharacterCreator/Character%20Creator%205/Bin64/RLPy.py:6686)、[工程插件](D:/UE/projects/datatry_02/Plugins/RLPlugin/RLPlugin.uplugin)

所有类型共同记录：来源与 SHA、导出配置、CC／UE／插件版本、单位与轴、实际骨名／父子关系／绑定变换、网格和材质槽、纹理来源、实际 Morph 清单、输出文件清单。动画另加范围、FPS、根运动和曲线归属。不能只写“UE5 预设”，也不能仅靠文件存在判断转换成功。

CC 延续现有 UE5 骨结构、骨名小写／标准化、重名处理、ResetBoneScale 等经过使用的配置；静态与动作采用同一命名和轴约定。保持外部纹理与 JSON 的完整路径关系，关闭 Embed Textures。JSON 包含 FBX 不能完整携带的材质设置，不能为节省空间直接丢掉。[官方导出说明](https://manual.reallusion.com/CC-iC-Auto-Setup/All-in-One/1.2/02_for_Unreal/Exporting-Characters-from-iC-or-CC.htm)

### CC：三类导出不能共用一个未经区分的预设

| 对象 | 已有实现与建议设置 | 尚须补齐的证据 |
| --- | --- | --- |
| 静态角色／服装见证源 | `EnableExportMotion(False)`；`AutoSkinRigidMesh`；现有静态路线使用 `TPoseForCreateMorphTargetMesh`；`SetUnrealBoneStructure(UE5)`；`EnableBasicBindPose(False)`；`ExportJson` | 最终输出层级、身体完整性、绑定姿势和 Morph 清单。不能把创建 Morph 的 T-pose 标志等同于 UI 的 Use T Pose As Bind Pose |
| 新身体动作 | `EnableExportMotion(True)`；明确 `SetExportMotionRange`／`SetExportMotionFps`；旧纯身体路线用 `RemoveAllMesh`；按动作选择 `ExportRootMotion`／`ZeroMotionRoot` | 新片是否带应保留曲线／属性；实际范围与 FPS；根运动行为 |
| hybrid 面部片 | 先延续已验完整 FBX 来源；启用动作并显式范围／FPS，`AutoSkinRigidMesh + ExportRootMotion`；不套静态 T-pose 标志 | 当前 Convert 开关的真实状态未被脚本／回执锁定；需要在下一次受控导出记录。轻量 `RemoveAllMeshKeepMorph` 仍待对照 |

实际接口为 `RExportFbxSetting` 设置后传入 `RFileIO.ExportFbxFile(avatar, path, setting)`。本机支持 `GetOption*`、`GetExportMotionFps/Range`、`GetExportLevel`、`IsBakeSubdivisionEnabled` 等读回，应记录设置后读数与文件实际结果。[静态／面部导出代码](../../00_engine/scripts/character_creator/cc_headshot_route_validation_v1.py:1503)、[既有服装导出助手](../../00_engine/scripts/character_creator/cc_validate_body_reconstruction.py:25398)

必须补充的两点：

- 现有代表诊断设置过 `EnableBakeSubdivision(False)`，但仍出现 Body 56,412 顶点而非基础 14,164；当前服装／固定头发使用的通用导出助手甚至没有显式设置导出细分。这说明工作视口 SubD0、Bake 开关和最终输出等级不是同一件事。下一版规范应记录 `SetExportLevel`／读回和实际拓扑，以代表画质决定等级，不能从 API 名字推断等级。[本地细分与导出证据](../../20_planning/data_design/character_creator/full_process/technical/character_creator/BODYFIT_IDENTITY_AGE.md)
- 当前未核实 UI 中 `Convert Skinned Expressions to Morphs` 的开关实值；未在 SDK 包装器找到对应同名设置。旧规范推荐关闭不等于此刻实际关闭。下一次导出必须明确记录模式并用实际骨轨＋曲线验证，不默认继承上次 GUI 状态。

### UE：静态网格导入与动画导入分开

本机源码确认 `import_only_animations=True` 必须同时指定有效 `skeleton`；静态网格 `skeleton=None` 会新建 Skeleton。关闭 `try_auto_select_skeleton`，避免由目录内容决定绑定对象。[本机共同接口](D:/UE/UE_5.8/Engine/Plugins/Interchange/Runtime/Source/Pipelines/Public/InterchangeGenericAssetsPipelineSharedSettings.h:185)

| 设置 | 新静态角色基线 | 衣服／头发模块 | 身体／面部动画 |
| --- | --- | --- | --- |
| `import_skeletal_meshes` | true | true | false |
| `import_static_meshes` | false | false | false |
| `import_only_animations` | false | false | true |
| `import_animations` | false | false | true |
| `skeleton` | 新基线创建并记录实际结果；复用必须有兼容证据 | 显式选择已验证目标 | 必须为静态角色实际 Skeleton |
| `try_auto_select_skeleton` | false | false | false |
| `import_morph_targets` | 首个基线 true；以后按已验证裁减来源 | 按部件依赖，未证明可删时保留 | 不靠此网格开关替代动画曲线检查 |
| `combine_skeletal_meshes_behavior` | 首个诊断沿用 `DO_NOT_COMBINE`，最终角色组织方式另验 | `DO_NOT_COMBINE` | 不产生网格 |
| `use_t0_as_ref_pose` | 显式 false | 显式 false | 不用动作第零帧改造静态基线 |
| `update_skeleton_reference_pose` | 显式 false | 显式 false | 保持目标 Skeleton，复核导入前后未变 |
| `create_physics_asset` | 当前非物理路线 false | 当前 Leader Pose 路线 false | 不产生 PhysicsAsset |
| 材质／纹理 | 单独明确 Auto Setup 材质来源与映射 | 复用已接受材质，不重复生成 | 不导入 |

该表是待实现的显式参数合同，不表示现有每个导入脚本已设置全部字段。已验诊断先分离网格、以见证导入获取 Auto Setup 材质再映射；固定头发样例则有合并 Body 的实现。两者不能混写成唯一已验角色结构，后续必须检查眼、牙、舌、睫毛等部件均收到正确骨骼和 Morph 驱动。[已验隔离导入](../../00_engine/scripts/unreal/ue_headshot_normal_probe_v1.py:184)、[已有模块导入](../../00_engine/scripts/unreal/ue_modular_outfit_pilot_import_v1.py:872)

动画还需显式记录 `import_bone_tracks`、`import_custom_attribute`、`custom_bone_animation_sample_rate`、`animation_range` 与 `frame_alignment`。保留 hybrid 骨轨和必要曲线；不要将所有曲线标成材质曲线。UE5.8 的通用曲线元数据设置已在共同属性类，旧位置属于 deprecated。删除重导曲线、剔除零曲线、冗余关键帧压缩应有单独策略，不能把“零值”误当“没有复位作用”。[本机动画接口](D:/UE/UE_5.8/Engine/Plugins/Interchange/Runtime/Source/Pipelines/Public/InterchangeGenericAnimationPipeline.h:67)

自动导入使用明确的 Interchange Pipeline，`is_automated=True`、`force_show_dialog=False`、`replace_existing=False` 和 `override_pipelines`；新配置写独立目标。源 SHA＋参数＋工具版本与目标清单一致时才可跳过，不得仅凭目录里已有 SkeletalMesh 判成功。

## 5. 其他已发现的问题及处理建议

| 已有经验／问题 | 对下一步的影响 |
| --- | --- |
| 固定头发双样例导入器关闭 Morph，且已有网格时直接返回 | 不能直接作为完整新角色入口；把开关改 true 后重跑也不会自动修复已有网格。需要独立导入目标和实际 Morph 读回。[代码](../../00_engine/scripts/unreal/ue_import_fixed_head_hair_v1.py:127) |
| 合并网格＋动画导入曾污染参考姿势，引起眼口异常及身体位移 | 延续静态基线＋动画单独导入；导入后检查实际 Skeleton、身体和眼口，不用同名骨骼代替验证 |
| 原始 FBX 曾出现异常 Shape 法线 | 保留异常源证据；沿用已验法线／切线重算策略并检查动态画面。不能以“文件无 NaN”或“重算法线”单独宣布外观正确 |
| 材质、透明眼部件、隐藏头皮槽、贴图未充分加载曾影响画面 | 使用完整 Auto Setup 材质来源和精确槽映射；复用已接受的发型隐藏槽规则。服装对应的身体隐藏面／Mask 尚未验证，应另行建立，不能在通用裸身源永久删掉换装后会露出的身体网格 |
| 保存动作引用仍可能没有实际播放实例；后台节流也曾使画面不更新 | 检查真实时间推进、身体骨运动、衣服跟随及保存重载，不能只核对动画路径。[运行时经验](../../20_planning/data_design/character_creator/full_process/technical/unreal/CHARACTER_RUNTIME.md) |
| 旧渲染入口只取角色 Blueprint，未传新模块组合；执行器写死 Happy，配置生成器写死旧数量 | 复用逐任务建 Sequence、固定 Actor 标识和确定性播放；接入新角色时传入明确装配结果与合成动画，解除历史批次假设。此次不扩成渲染重构。[旧任务入口](../../00_engine/scripts/unreal/run_first_batch_render_matrix.py:165)、[执行器](../../00_engine/scripts/unreal/run_first_batch_render_jobs.py:447) |

## 6. 后续最小验证与本轮结论边界

角色创建流程交付最终候选后，建议按以下顺序接续：

1. 男女各一名最终新角色，分别建立带必要表情数据的静态 UE 基线，核对身体、骨骼、绑定、实际细分和材料；先不批量。
2. 复用旧衣柜中代表性的贴身上衣／裤子、分层外套、鞋及整套绑定服装。先查骨映射，再在一段代表身体动作中检查肩腰领口、手臂、裆部和脚部；据此分别判定直接复用、仅 UE 重导或 CC 修形。
3. 用一段新身体动作加一段自然面部片，检查头颈归属、眨眼闭合、牙舌、视线、循环和衣服同步。大幅张嘴校准仍可保留作诊断，不进入默认自然片。
4. 保存重载并通过实际渲染入口输出短片。确认屏幕预览与最终动画调用一致，之后再扩展其余体型和动作。
5. 在完整基线的派生副本上做减量对照，记录导出／导入耗时、FBX／UE 资产大小、Morph 数及可见差异；达标后才固定精简预设。

目前可直接建议的节省顺序是：**避免重复导入网格与贴图 → 固定合适的真实导出细分 → 按用途裁减部件数据 → 最后裁减面部 Morph 依赖。**本轮没有删除原始导出、旧服装或任何动画资产。

本次核查没有把新角色标为已兼容，也没有改写其他会话的完成状态。读取到的项目状态在 2026-10-05 18:14 已为创建计划结项后的空闲，下一步仍待选择；它不代表新完整角色已经导出／导入。本报告作为独立研究交付，不启动批次、导出、UE 或渲染。[当前状态入口](../../20_planning/data_design/character_creator/full_process/project_management/status/PROJECT_STATE.json)
