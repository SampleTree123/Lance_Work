# Registry：机器权威反向索引

> 文档 ID：`REGISTRY-INDEX`
> 文档类型：`registry_index`
> 生命周期：`current`
> 权威范围：机器可读权威、适用范围、Technical 所有者和反向查询入口
> 最近核验：2026-10-22（仅补第七轮双画幅离线候选反查；其余既有索引未重审）

## 1. 子系统职责

Registry 子系统用于“已知对象名或文件类型，但不知道机器真值和实现归属”时反向查询。它只登记：

1. 机器权威的准确路径或定位规则；
2. 该权威当前用于哪个范围；
3. 解释、生成和维护它的唯一 Technical 所有者；
4. 主要消费 Workflow。

本页不复制 Registry 的字段和值，不保存当前验证结果，也不替代 Workflow 的执行顺序。当前接受版本和证据必须查 Status；字段/生成命令必须查 Technical；词义和路径别名必须查 [Reference](../reference/README.md)。

## 2. CC 与资产权威

| 对象 | 当前机器权威 | 当前范围 | Technical 所有者 | 主要 Workflow |
| --- | --- | --- | --- | --- |
| BodyFit | `repo://00_engine/scripts/character_creator/cc_body_preset_library_v2.json` | 10 个冻结 BodyFit | [BodyFit / Identity / Age](../technical/character_creator/BODYFIT_IDENTITY_AGE.md) | `WF-20`, `WF-30` |
| Face V3 | `repo://00_engine/scripts/character_creator/cc_face_seed_library_v1.json`、`repo://00_engine/scripts/character_creator/cc_face_recipes_v3_200.json` | 当前旧生产身份原型与配方 | [BodyFit / Identity / Age](../technical/character_creator/BODYFIT_IDENTITY_AGE.md) | `WF-20`, `WF-30` |
| Headshot 原型与头型 | `repo://00_engine/scripts/character_creator/cc_headshot_face_prototype_registry_v1.json`、`repo://00_engine/scripts/character_creator/cc_headshot_skull_profile_library_v1.json` | 已验证候选；是否进入批次由 Asset Matrix 决定 | [BodyFit / Identity / Age](../technical/character_creator/BODYFIT_IDENTITY_AGE.md) | `WF-20`, `WF-30` |
| 第一批 Identity | `repo://00_engine/scripts/character_creator/cc_first_batch_identity_library_20260820_v1.json` | `BATCH-001-FIRST-DATA` | [BodyFit / Identity / Age](../technical/character_creator/BODYFIT_IDENTITY_AGE.md) | `WF-20`, `WF-30` |
| 面部皮肤细节独立实验 | `%OUTPUT_ROOT%/unreal_character_import/skin_detail_optimization_20261012_v1/execution_record_v1.json`、`input_manifest_v2.json`、`c_final_capture_selection.json`、`c_variants_params_v2.json`、`review_gallery_input_latest.json` | 一男一女 A/B/C 独立对照、最终CC尝试/UE参数子集与媒体；原高级遮罩/SSS保留，非完整AutoSetup等价或正式40人换皮发布，接受范围由Status维护 | [CC装配§10](../technical/character_creator/ASSEMBLY_AND_ACCEPTANCE.md#10-面部皮肤细节独立对照实验2026-10-12)、[Runtime3.20](../technical/unreal/CHARACTER_RUNTIME.md#320-面部皮肤细节独立对照实验2026-10-12) | `WF-30`、`WF-40`、`WF-50`、`WF-80` |
| 外观资产 | `repo://00_engine/scripts/character_creator/cc_appearance_asset_catalog_v1.json`、`repo://00_engine/scripts/character_creator/cc_facial_hair_asset_catalog_v1.json`、`repo://00_engine/scripts/character_creator/cc_scalp_hair_asset_catalog_v1.json` | 皮肤、眼球、眉毛、睫毛、牙齿、胡须和头发候选 | [外观资产](../technical/character_creator/APPEARANCE_ASSETS.md) | `WF-20`, `WF-30` |
| Outfit Family | `%CLOTHING_ROOT%/<sex>/<family>/outfit_family.json` 与 `repo://00_engine/scripts/character_creator/outfit_family_v1.schema.json` | 人工批准的 Family 内组合 | [服装系统](../technical/character_creator/OUTFIT_SYSTEM.md) | `WF-20`, `WF-30` |
| Headshot统一创建参考 | `repo://00_engine/scripts/character_creator/cc_headshot_creation_references_v1.json` | 两入口男女starter/Average/固定头皮及引用SHA契约；native另选独立修复的native_starter_project字段，旧assembled starter保持，接受范围由Status维护，不晋升规范项目 | [BodyFit11](../technical/character_creator/BODYFIT_IDENTITY_AGE.md#11-cc角色创建统一自动化2026-10-05) | `WF-30` |
| Headshot基础装配几何policy | `repo://00_engine/scripts/character_creator/cc_base_assembly_geometry_policy_v2.json`；v1保留为既有女性证据绑定版本 | v2继承精确native-lash索引，仅注册male具名上界/evidence override；female规则不变，实际接受范围由Technical/Status维护，不泛化其他资产或角色 | [组装与验收9](../technical/character_creator/ASSEMBLY_AND_ACCEPTANCE.md#9-headshot基础外观精简装配2026-10-05) | `WF-30` |
| 第一批 32 Look | `repo://00_engine/scripts/character_creator/cc_first_batch_full_reference_looks_20260822_v3.json` | `BATCH-001-FIRST-DATA` | [组装与验收](../technical/character_creator/ASSEMBLY_AND_ACCEPTANCE.md) | `WF-20`–`WF-50` |
| 第一批动作池 | `repo://00_engine/scripts/character_creator/cc_first_batch_action_pool_20260824_v1.json` | 女性 5、男性 5 的当前生产动作 | [动作传输](../technical/transfer/MOTION_TRANSFER.md) | `WF-20`, `WF-40`, `WF-50` |

没有出现在“当前机器权威”列中的旧 Probe、旧版本 JSON 或人工截图，不能因为文件仍存在就被视为生产 Registry。是否保留由 Output/History 规则决定。

## 3. Transfer、UE 与数据集权威

| 对象 | 当前机器权威 | 当前范围 | Technical 所有者 | 主要 Workflow |
| --- | --- | --- | --- | --- |
| 第十一轮属性回换控制离线候选 | `%OUTPUT_ROOT%/dataset_return_control_20261022_v11/CURRENT_CANDIDATE.json`、`RULES.json`、`PRESERVATION.json`、`return_audit.json`、`frequency_audit.json`、`inherited_audit.json`、`selected_candidate/reference_manifest.json`及`reference_binding_check.json` | experimental；不变v10图内重采样后缀，trial2为当前选择；显式祖先属性回换降低，原频率／覆盖／父位置及参考绑定复核通过；配置／内容已由用户采用；限定复审见`review_20261022/AUDIT_REPORT.md`，媒体／渲染未接受，边界查Status | [数据集探索第十一版](../technical/dataset/DATASET_DESIGN_EXPLORATION_20261021.md) | `WF-70`（离线研究），`WF-80`仅后续接入 |
| 第十轮生成阶段分散历史基线 | `%OUTPUT_ROOT%/dataset_distributed_graph_20261022_v10/CURRENT_CANDIDATE.json`、`RULES.json`、`structural_candidate/SOURCES.json`、`structural_frequency_audit.json`／`structural_inherited_audit.json`、`aspect_work/selected_assignment/SOURCES.json`、`aspect_work/aspect_audit.json`、`aspect_work/selected_candidate/reference_manifest.json`及`aspect_work/reference_binding_check.json` | experimental；真实内容／完整history逐值频率、旧target／起点、整链画幅与未渲染参考需求独立通过；历史主选择训练4／测试3，当前已由第十一轮回换控制候选接续；原成本／L5取舍查Status，不作为正式Render Jobs | [数据集探索第十版](../technical/dataset/DATASET_DESIGN_EXPLORATION_20261021.md) | `WF-60`／`WF-70`（离线研究），`WF-80`仅后续接入 |
| 第八轮0.4历史衰减离线基线 | `%OUTPUT_ROOT%/dataset_decay04_20261022_v8/CURRENT_CANDIDATE.json`、`RULES.json`、`same_graph_check.json`、`structural_audit.json`、`aspect_audit.json`、`selected_candidate/{train,test}/render_requests.json`及`reference_binding_check.json` | experimental；同图实际重采样、整链双画幅与未渲染参考需求。仅单种子对，动作镜头支持不足仍在；采用和生产范围查Status | [数据集探索第八版](../technical/dataset/DATASET_DESIGN_EXPLORATION_20261021.md) | `WF-60`／`WF-70`（离线研究），`WF-80`仅后续接入 |
| 第七轮历史整链双画幅候选（0.2） | `%OUTPUT_ROOT%/dataset_dual_aspect_20261022_v7/CURRENT_CANDIDATE.json`、`RULES.json`、`selected_assignment/SOURCES.json`、`selected_candidate/ASSEMBLY.json`、`selected_candidate/{train,test}/render_requests.json`、`audit_agent/audit_selected.json`及`selected_candidate/reference_manifest.json`／`reference_summary.json` | experimental保留原链的画幅分配、渲染版本／局部镜头模板请求及未渲染参考需求；采用与最终媒体规格查Status，不视为正式Render Jobs或已产媒体 | [数据集探索第七版](../technical/dataset/DATASET_DESIGN_EXPLORATION_20261021.md) | `WF-60`／`WF-70`（离线研究），`WF-80`仅后续接入 |
| 第六轮紧凑离线图与链候选 | `%OUTPUT_ROOT%/dataset_compact_graph_20261022_v6/FINAL_SELECTION.json`、`CURRENT_CANDIDATE.json`、`selected_seed*/ASSEMBLY.json`及`DELIVERY_MANIFEST.json` | experimental离线候选选择、三seed各自来源和交付闭包；接受范围查Status，未晋升正式渲染图源，不能拼接备选seed | [数据集探索](../technical/dataset/DATASET_DESIGN_EXPLORATION_20261021.md) | `WF-60`/`WF-70`（离线研究） |
| 必需 CC 导出 | `repo://00_engine/scripts/dataset/first_batch_required_exports_20260824_v3.json` | 第一批 Transfer 输入闭包 | [资产追溯](../technical/transfer/ASSET_TRACEABILITY.md) | `WF-40` |
| 平均体型衣柜 | `%CC_EXPORT_ROOT%/wardrobe_average_20260906_v1/manifests/v3/wardrobe_registry.json`、`revision.json`、逐批 `ue_import.json` | 第二批本地衣柜扩展；Elise 修订规则覆盖外部旧 Family，既有 v2 成功来源按哈希继承；运行/合身接受状态另查 WF-40/WF-50 | [模块化 Transfer 第10.9节](../technical/transfer/CC_TO_UE_MODULAR_OUTFIT_PILOT.md#109-用户批准的锁定套装修订) | `WF-30`, `WF-40`, `WF-50` |
| 旧 UE 衣柜/发型索引与支持来源 | `repo://00_engine/assets/character_creator/wardrobe_registry_ue_v4_full_20260929.json` | 已保留的原女性发型库、历史审查/迁移、构建双版本索引的输入和既有支持依赖；默认新索引凭证失效时的回退。旧材质父项、实体发饰及同款缺省通道纹理有实际引用，不能因新版本完成删除 | [模块化 Transfer 第11.3节](../technical/transfer/CC_TO_UE_MODULAR_OUTFIT_PILOT.md#113-精确网格映射与正式索引直接读取2026-09-29) | `WF-40`, `WF-50` |
| 固定参考头型双版本发型 | `%OUTPUT_ROOT%/character_creator_bridge/artifacts/fixed_head_hair_20261004_v1/sources/source_manifest.json`、`%CC_EXPORT_ROOT%/fixed_head_hair_20261004_v1/manifests/batch.json`、`%OUTPUT_ROOT%/unreal_character_import/fixed_head_hair_20261004_v1/import_report.json` | 固定男女来源、导出与逐对导入终态的追溯权威；不是数据生产Batch。旧 accepted 支持库仍被引用，继续保留 | [模块化Transfer11.5](../technical/transfer/CC_TO_UE_MODULAR_OUTFIT_PILOT.md#115-固定男女参考头型的双版本发型转换2026-10-04) | `WF-30`, `WF-40`, `WF-50` |
| 原双版本索引／新材质索引的来源与回退 | `repo://00_engine/assets/character_creator/wardrobe_registry_ue_v4_fixed_head_hair_20261004_v1.json`；`%OUTPUT_ROOT%/unreal_character_import/fixed_head_hair_20261004_v1/registry_publication_report.json` | 原双版本单文件索引：作为新材质版本的不可变来源/回退，Family/共享鞋/许可保持，按性别选择几何共享Skeleton；默认新材质发布有效时优先新版本，否则经原发布凭证/import_report回退该版 | [模块化Transfer11.5](../technical/transfer/CC_TO_UE_MODULAR_OUTFIT_PILOT.md#115-固定男女参考头型的双版本发型转换2026-10-04)；[Runtime3.9](../technical/unreal/CHARACTER_RUNTIME.md#39-固定头型双版本发型的代表小样与索引消费2026-10-04) | `WF-40`, `WF-50` |
| 保留的 UE 衣柜／固定头型材质修复索引 | `repo://00_engine/assets/character_creator/wardrobe_registry_ue_v4_fixed_head_materials_20261005_v1.json`；`%OUTPUT_ROOT%/unreal_character_import/fixed_head_material_repair_20261005_v1/registry_publication_report.json`及两份`*_apply_publication.json` | 2026-10-05历史材质接受版本及新筛选版输入，源与历史回执不改；旧173套/40发型审查目录显式读取此版，当前默认筛选版见下一行 | [Runtime3.11](../technical/unreal/CHARACTER_RUNTIME.md#311-固定参考头型人物与发辫的定向材质修复2026-10-05)；[Transfer11.6](../technical/transfer/CC_TO_UE_MODULAR_OUTFIT_PILOT.md#116-固定参考人物材质修复与后续导入防复发2026-10-05) | `WF-40`、`WF-50` |
| 当前 UE 衣柜／男女最终发型筛选版 | `repo://00_engine/assets/character_creator/wardrobe_registry_ue_v4_reviewed_pool_20261007_v5.json`；`%OUTPUT_ROOT%/unreal_character_import/female_shared_shoes_hair_color_20261007_v1/hair_palette_v2_20261007/publication/publication_manifest_v5.json` | formal核验当前发布SHA链；按用户要求只删除指定性别发型，不再分组。衣服、女性共享鞋/原赤脚许可与男性鞋继承v4。v2/v3/v4为追溯来源，选择发布不等于全组合视觉接受 | [Runtime3.17.4](../technical/unreal/CHARACTER_RUNTIME.md#3174-v5直接筛选与丰富发色) | `WF-50` |
| 完整角色Skeleton候选 | `%OUTPUT_ROOT%/unreal_character_import/complete_character_skeleton_pilot_20261005_v1/standard_candidate_registry.json` | 两历史固定男女FBX完整独立Skeleton/六部件定位；候选而非新身份共享或正式共同Skeleton标准，接受范围另查Status | [Transfer12](../technical/transfer/CC_TO_UE_MODULAR_OUTFIT_PILOT.md#12-完整角色ue导入与骨架标准试点2026-10-05) | `WF-40`、`WF-50` |
| 当前发型导出 | `%CC_EXPORT_ROOT%/scalp_hair_batch_20260924_v1/manifests/cc_export.json` | 当前发型批量导入读取的导出 Manifest；代码目录旧 staging 副本已迁移，历史报告中的旧路径由迁移映射解释 | [模块化 Transfer](../technical/transfer/CC_TO_UE_MODULAR_OUTFIT_PILOT.md) | `WF-40` |
| 当前审查入口 | `%OUTPUT_ROOT%/unreal_character_import/current_reviews_20261001_v1/wardrobe_coverage/review_plan.json`、`hair_outfit_compatibility/review_plan.json` 和 `bodyfit_metadata.json` | 当前 v003 服装覆盖/头发服装审查的计划、最小身体绑定；旧全库重组源计划仅作冻结证据 | [角色运行时](../technical/unreal/CHARACTER_RUNTIME.md) | `WF-50` |
| 共享导入 Pipeline | `/Game/DataMake/Config/Import/DM_Interchange_Split_Pipeline_v1` | 当前导入共享配置，不再借用旧 F_BIKINI_LAYERED Pilot 目录 | [模块化 Transfer](../technical/transfer/CC_TO_UE_MODULAR_OUTFIT_PILOT.md) | `WF-40` |
| 本地 Look/Action/Camera 矩阵 | `repo://00_engine/scripts/unreal/first_batch_local_render_matrix_20260824_v1.json` | 第一批本地与图源矩阵 | [场景、相机与 Sequence](../technical/unreal/SCENE_CAMERA_SEQUENCE.md) | `WF-20`, `WF-60`, `WF-80` |
| 当前双人审查主图与保存点 | `repo://00_engine/scripts/unreal/scene_site_catalog_v1.py`；`%OUTPUT_ROOT%/pair_scene_review_20261019_v1/sites/*.json`与`panel_review_drafts.json` | 主图选择由原场景索引/迁移表及当前选择覆盖共同决定；保存点决定实际XYZ/朝向/排除，草稿按签名独立保留，不自动相加或迁移 | [场景§22.8](../technical/unreal/SCENE_CAMERA_SEQUENCE.md#228-已审查点位继续迭代2026-10-20) | `WF-60` |
| 当前拍摄选择与保存检查点 | `repo://00_engine/scripts/unreal/scene_review_selection_policy_v1.py`、`%OUTPUT_ROOT%/scene_review_checkpoint_20261020_v2/` | 私有面板当前动作选择与保存状态；冻结来源／资产／旧点保留，实际验证见Status | [场景Technical §22.11](../technical/unreal/SCENE_CAMERA_SEQUENCE.md#2211-当前拍摄选择与保存检查点2026-10-20) | `WF-60` |
| 夜间40人场景面板接入 | `repo://00_engine/scripts/unreal/night_character_review_v1.py`、`%OUTPUT_ROOT%/night_character_panel_20261020_v1/` | 从夜间完成交接读取每人六主体件／全部独立睫毛，沿用原面板入口和保存位置；实际运行见Status | [场景Technical §22.12](../technical/unreal/SCENE_CAMERA_SEQUENCE.md#2212-夜间完成导入的40人接入既有面板2026-10-20) | `WF-50`、`WF-60` |
| 当前发色与RedSoul选择 | `repo://00_engine/scripts/unreal/appearance_selection_policy_v1.py`、`%OUTPUT_ROOT%/appearance_choices_20261020_v1/` | 共享正式loader载入副本上的当前选择；女性鞋子反馈和用户调光状态见Status | [场景Technical §22.13](../technical/unreal/SCENE_CAMERA_SEQUENCE.md#2213-当前发色与redsoul选择及女性赤脚反馈2026-10-20) | `WF-50`、`WF-60` |
| 当前场景继续迭代追溯 | `%OUTPUT_ROOT%/scene_review_iteration_20261020_v1/baseline/manifest.json`、`camera/final_integrity.json`、`ground/runtime_validation.json` | 本轮可继续修改的基线、相机修复及三指定保存点运行证据；不是最终冻结或全场景/全动作生产接受，最新下一步从Status读取 | [场景§22.8](../technical/unreal/SCENE_CAMERA_SEQUENCE.md#228-已审查点位继续迭代2026-10-20) | `WF-60` |
| 第一批 Expression | `repo://00_engine/scripts/unreal/first_batch_expression_profile_20260820_v1.json` | 第一批表情配置来源 | [动画、表情与 Morph](../technical/unreal/ANIMATION_EXPRESSION_MORPH.md) | `WF-50`, `WF-70` |
| 第一批图源 | `repo://00_engine/scripts/dataset/first_batch_graph_source_20260824_v1.json` | 节点、边、链和 Render Job 的唯一源输入 | [配置图与链](../technical/dataset/CONFIG_GRAPH_AND_CHAINS.md) | `WF-70`, `WF-80` |
| Prompt Catalog | `repo://00_engine/scripts/dataset/prompt_catalog_first_batch_v1.json` | 第一批模板与身份描述 | [Prompt 层](../technical/dataset/PROMPT_LAYER.md) | `WF-70`, `WF-90` |
| UE 早期对象索引 | `%UE_PROJECT_ROOT%/DataMake/dm_asset_index.json` | 仅为早期声明追溯；旧 Main 关卡已退役，不是现用运行索引或第一批图源 | [角色运行时](../technical/unreal/CHARACTER_RUNTIME.md) | `WF-50`, `WF-60` |
| 覆盖层网格视觉决定与实施目标 | `%OUTPUT_ROOT%/unreal_character_import/hair_sex_fit_review_20260929_v1/coverage_visibility_acceptance_20260930_v1/manual_review.json`、`approved_coverage_slots.json` | 仅保存覆盖层规则网格的人工决定与待实施精确槽位；当前运行时尚未消费，不能替代正式资产索引 | [角色运行时 3.7.6](../technical/unreal/CHARACTER_RUNTIME.md#376-覆盖层隐藏策略的用户确认与实施边界2026-09-30) | `WF-50` |

本轮动作窗口、竖屏参数和场景点位试点的机器产物位于 `%OUTPUT_ROOT%/unreal_character_import/motion_portrait_scene_pilot_20261011_v1/`，字段与实现由[场景相机 §11](../technical/unreal/SCENE_CAMERA_SEQUENCE.md#11-动作整理竖屏与场景点位试点2026-10-11)拥有，消费WF-50/60/80；当前仍在构建，未发布新生产Registry。

## 4. 跨阶段控制目录

| 对象 | 机器/文档权威 | 查询用途 | 所有者 |
| --- | --- | --- | --- |
| 脚本生命周期与归属 | `repo://00_engine/scripts/SCRIPT_CATALOG.json` | 由脚本路径反查生命周期、哈希和 Technical 所有者 | [脚本生命周期](../technical/implementation/SCRIPT_LIFECYCLE.md) |
| 验证契约 | [Validation Catalog](../technical/validation/VALIDATION_CATALOG.md) | 由 `VAL-*` 反查触发条件、证据、实现与状态落点 | [Validation 子系统](../technical/validation/README.md) |
| 输出契约 | [Output Contracts](../technical/output/OUTPUT_CONTRACTS.md) | 由 `OUT-*` 反查生产者、存储类别和状态所有者 | [Output 子系统](../technical/output/README.md) |
| 输出保留规则 | `repo://00_engine/outputs/RETENTION_POLICY.json` | 由物理输出路径反查保留等级、所有者和输出契约 | [盘点与保留](../technical/output/INVENTORY_AND_RETENTION.md) |
| 输出当前盘点 | `repo://00_engine/outputs/OUTPUT_INVENTORY.json` | 查看已扫描路径的当前分类，不直接授权删除 | [盘点与保留](../technical/output/INVENTORY_AND_RETENTION.md) |
| 当前项目状态 | [PROJECT_STATE.json](../project_management/status/PROJECT_STATE.json) | 机器读取 active Workflow/Plan/Batch、验证和当前输出指针 | [Status 子系统](../project_management/status/README.md) |

## 5. 查询规则

### 5.1 反向查询

```text
对象名或物理文件
  -> 本索引定位机器权威
  -> Technical 确认字段、生成命令和限制
  -> Workflow 确认何时消费
  -> Workflow/Batch Status 确认当前接受版本与证据
```

### 5.2 顺向执行

```text
Master / 当前 Status
  -> Workflow
  -> Technical
  -> 机器 Registry / Manifest
  -> VAL-* / OUT-*
```

顺向工作不要从本页猜测执行步骤。

## 6. 独立维护契约

最终十色的新人工接受反查：`%OUTPUT_ROOT%/unreal_character_import/character_runtime_face_library_20261007_v1/final_hair_palette_user_acceptance_v1.json`由[Runtime3.18](../technical/unreal/CHARACTER_RUNTIME.md#318-完整角色发色配置与现成面部库)拥有，绑定既有十色参数/能力表与v5发型索引。它接受用户实际审查的发色，不替代尚未验证的完整角色保色、配置恢复或面部/身体组合结果；旧pending交付回执保持当时历史。

- 每条当前 Registry 必须有准确定位、适用范围、Technical 所有者和主要 Workflow。
- 同一对象存在多个版本时，只把当前权威放入主表；旧版本通过 History、Git 或产生它的 Technical 追溯。
- Registry 内容、动态计数和当前通过状态不得复制到本页。
- 新增机器权威时，先由 Technical 定义，再更新本页；若改变长期语义，同时提交 ADR。
- 路径不存在、所有者缺失、多个文件同时自称当前权威或 Status 指向不同版本时，停止使用并执行 `VAL-DOC-01`。

### Headshot 固定头皮实验工单

`%CC_SCRIPT_ROOT%/runtime_staging/headshot_fixed_scalp_20261002_v1/` 是本轮限定实验输入，运行报告位于 `%OUTPUT_ROOT%/character_creator_bridge/artifacts/headshot_fixed_scalp_20261002_v1/`，消费阶段 `WF-30`，所有者为 [BodyFit/Headshot](../technical/character_creator/BODYFIT_IDENTITY_AGE.md#9-固定头皮实验与照片自动生成)。候选项目和照片接口成功不改变正式 Identity/Hair Registry。


CFD原生双人小样机器入口：`%OUTPUT_ROOT%/unreal_character_import/cfd_native_pair_20261006_v1/complete_character_import_manifest_v1.json`、`standard_candidate_registry.json`及`ue_target.json`归[Transfer13](../technical/transfer/CC_TO_UE_MODULAR_OUTFIT_PILOT.md#13-cfd原生男女双人完整转移试点2026-10-06)，`runtime/stage_report.json`与`panel_lifecycle.json`归[Runtime3.14](../technical/unreal/CHARACTER_RUNTIME.md#314-cfd原生男女双人测试入口2026-10-06)。仅新两人独立候选/当前精确编辑器与review_ready入口，当前双人最终用户审查已在runtime/user_final_validation_v1.json直接确认；仍非正式共同Skeleton/全身份或批量启动授权，旧参考候选/正式衣柜Registry不改写。


CFD40独立批次反查：`%OUTPUT_ROOT%/unreal_character_import/cfd_native_batch40_20261006_v1/imported_character_registry.json`、`complete_export_handoff_v1.json`、`final_import_summary_v2.json`与`ue_target.json`由[Transfer14](../technical/transfer/CC_TO_UE_MODULAR_OUTFIT_PILOT.md#14-cfd原生40人完整转移批次2026-10-06)拥有；`review_pages_verification_v1.json`、`runtime/current_case.json`与`USER_REVIEW_QUICKSTART.md`由[Runtime3.15](../technical/unreal/CHARACTER_RUNTIME.md#315-cfd原生40人简单审查关卡2026-10-06)拥有。适用本批次完整转移、同性共享Skeleton及单关卡分页静态审查，不代替正式衣柜索引或其他身份批次；实例重启必须重新核对并绑定ue_target。当前接受范围由独立execution_record/PROJECT_STATE scope维护，本页不复制动态计数。


CFD照片形态辅助选样反查：`%OUTPUT_ROOT%/character_creator_analysis/cfd_face_diversity_20261007_v1/analysis.json`与`analysis_check.json`由[BodyFit §12](../technical/character_creator/BODYFIT_IDENTITY_AGE.md#12-cfd照片形态选样与cc多样性候选研究2026-10-07)拥有，只是离线组内照片形态及候选选择，不是正式Identity、创建请求或感知验收；CLI新候选记录analysis_source及输入fingerprint。


CFD40当前双人分离槽位审查反查：`%OUTPUT_ROOT%/unreal_character_import/cfd_native_batch40_20261006_v1/runtime/modular_review_20261007_v1/stage_result.json`、`current_case.json`、`selected_sources/`、`backend_validation/`及后续`panel_lifecycle.json`由[Runtime3.16](../technical/unreal/CHARACTER_RUNTIME.md#316-cfd40双人分离槽位审查2026-10-07)拥有。人物权威仍为Transfer14的imported_character_registry.json，原42步交付证据绑定reviewed_pool_v2发布链；后续运行消费formal当前发布并重新核验SHA，不改写来源。该入口替代本轮静态分页交付形式，原Runtime3.15输出和其人工静态接受原字节保留；具体机器/人工成熟度由Status拥有。

女性共享鞋、发型筛选与颜色实验反查：`%OUTPUT_ROOT%/unreal_character_import/female_shared_shoes_hair_color_20261007_v1/`内shoe_publication、hair_review、color_experiment、hair_palette_v2_20261007及session由[Runtime3.17](../technical/unreal/CHARACTER_RUNTIME.md#317-女性共享鞋发型分类与颜色实验2026-10-07)拥有。用户已取消分组，当前依据男女最终筛选直接使用；眼色不采用。颜色能力表不替代视觉接受，当前界面/颜色评价状态另查WF-50，不从文件存在推定。

## 完整角色配置与现成面部库反查

| 对象 | 机器权威 | 范围与所有者 | Workflow |
| --- | --- | --- | --- |
| 完整角色保存配置 | `%OUTPUT_ROOT%/unreal_character_import/character_runtime_face_library_20261007_v1/runtime_validation/complete_configuration.json` | 有界验证配置、来源和色板闭包；[Runtime3.18](../technical/unreal/CHARACTER_RUNTIME.md#318-完整角色发色配置与现成面部库)，不能替代正式生产配置 | WF-50 |
| 现成面部候选与CC检查 | 同Run的`research/`、`face_library/`及`%OUTPUT_ROOT%/character_creator_bridge/artifacts/native_face_library_20261007_v1/` | 候选来源和对应关系证据；[Animation §7](../technical/unreal/ANIMATION_EXPRESSION_MORPH.md#7-现成面部表演库与完整角色组合)，未完成选择不视为表情库 | WF-50 |
| 现成面部审查库 | `%OUTPUT_ROOT%/unreal_character_import/character_runtime_face_library_20261007_v1/native_face_library_registry_v1.json` | validated_review证据闭包；[Animation §7](../technical/unreal/ANIMATION_EXPRESSION_MORPH.md#7-现成面部表演库与完整角色组合)，用户接受和完整运行交付另查Status；来源迁移及旧字节由同Run的contract_cache_registry_migration_v1.json、registry_history/追溯 | WF-50 |
| 当前四类五秒表情选择 | `%OUTPUT_ROOT%/unreal_character_import/native_face_five_second_20261008_v1/accepted_face_selection_v1.json`；同Run的human_face_selection_feedback_v1.json | 用户保留idle/smile/displeased/sad，男女八个代表asset/源窗/1x5秒/媒体与证据SHA；selection_accepted=true、runtime_integration=false是该记录当时事实，后续运行发布见下一行；[Animation §8.7](../technical/unreal/ANIMATION_EXPRESSION_MORPH.md#87-用户保留的当前四类选择) | WF-50 |
| 当前四类五秒运行审查库 | `%OUTPUT_ROOT%/unreal_character_import/native_face_panel_integration_20261009_v1/active_face_library_v1.json`及其SHA绑定的native_face_library_registry_v2.json | 当前发布入口、四类男女/身体选择派生与证据闭包；旧五类registry保留为历史和回退，当前运行验收进度查Status；[Runtime §3.19](../technical/unreal/CHARACTER_RUNTIME.md#319-四类五秒表情接入当前审查关卡) | WF-50 |
| 032动作扩充隔离小样 | `%OUTPUT_ROOT%/unreal_character_import/motion_library_expansion_20261009_v1/panel_pilot032/motion_catalog_v1.json`及face_overlay_v1.json | 仅显式pilot入口，运行小样通过但未向用户发布，不替换默认N3四表情authority；[Animation §9.6](../technical/unreal/ANIMATION_EXPRESSION_MORPH.md#96-单对扩充入口实际运行与许可排除检查点) | WF-50 |
| 无道具动作扩充最终审查目录 | `%OUTPUT_ROOT%/unreal_character_import/motion_library_expansion_20261009_v1/final_motion_catalog_v1.json`、final_face_overlay_v1.json | runtime_delivery_v1.json绑定最终smoke/真实五秒视觉/面板ready；显式open_final_motion_review_v1.ps1入口与user_review_guide_v1.md，原N3默认与032 pilot历史保持。[Animation §9.10](../technical/unreal/ANIMATION_EXPRESSION_MORPH.md#910-最终可见界面交付与结项范围) | WF-50 |
| 完整身体动作循环审查 | `%OUTPUT_ROOT%/unreal_character_import/full_motion_loop_review_20261009_v1/delivery_v1.json`、cache/与compositions/ | 显式open_full_motion_loop_review_v1.ps1；消费M3最终目录，按需完整身体＋五秒脸重复，新配置cfd40_full_motion_loop_configuration_v1；旧五秒输入不覆盖。[Animation §10](../technical/unreal/ANIMATION_EXPRESSION_MORPH.md#10-完整动作循环审查) | WF-50 |
| 相机动作小样时长与离线覆盖 | `%OUTPUT_ROOT%/unreal_character_import/camera_motion_pilot_20261009_v1/offline_motion_inventory_v2.json` | 暂定统一10秒，≥10秒连续窗@1倍、7–10秒匀速慢放、<7秒排除；脸保持原速5秒重复。v1为历史，清单不等于实际媒体/自然度接受。[场景相机 §7](../technical/unreal/SCENE_CAMERA_SEQUENCE.md#7-相机动作小样2026-10-09) | WF-60；关联WF-50/80 |
| 当前相机轨迹候选与StudioV2准备 | `%OUTPUT_ROOT%/unreal_character_import/camera_motion_pilot_20261009_v1/camera_motion_pilot_plan_v3.json`；sequences_v3/（当前v003）；sequences_v2/保留历史 | 相机轨迹当前v3；Studio/Maps独立v2，专属sequence绑定。部分试点准备不等于整轮媒体验收；v1/v2失败与历史证据保留。[场景相机 §7](../technical/unreal/SCENE_CAMERA_SEQUENCE.md#7-相机动作小样2026-10-09) | WF-60；关联WF-50/80 |

| 相机小样最终审查交付 | `%OUTPUT_ROOT%/unreal_character_import/camera_motion_pilot_20261009_v1/camera_pilot_delivery_manifest_v1.json`、completion_audit_v1.json、gallery/index.html | 34审查视频；plan_v3为当前主轨迹，camera_design_v1仅历史初稿。真实重跑pixel-exact失败保留，用户候选选择pending。[场景相机 §7](../technical/unreal/SCENE_CAMERA_SEQUENCE.md#7-相机动作小样2026-10-09) | WF-60；关联WF-50/80 |


## 共用镜头库补测入口（2026-10-10）

| 机器权威 | 当前范围 | Technical所有者 | 消费Workflow |
| --- | --- | --- | --- |
| `%OUTPUT_ROOT%/unreal_character_import/camera_library_expansion_20261010_v1/human_camera_feedback_v1.json` | 原34样片限定人工反馈，不修改历史媒体或倒写旧pending | [场景相机 §8](../technical/unreal/SCENE_CAMERA_SEQUENCE.md#8-共用镜头库与补测2026-10-10) | WF-60 |
| `%OUTPUT_ROOT%/unreal_character_import/camera_library_expansion_20261010_v1/composable_camera_library_v1.json`、`camera_coverage_candidates_v1.json`、`expansion_plan_v1.json` | 三轴库、有限补测候选与冻结轨迹；拒绝/未覆盖不是全局不支持 | [场景相机 §8](../technical/unreal/SCENE_CAMERA_SEQUENCE.md#8-共用镜头库与补测2026-10-10) | WF-60 |
| `%OUTPUT_ROOT%/unreal_character_import/camera_library_expansion_20261010_v1/review_delivery_manifest_v1.json` | 当前43条入口清单与原认可/旧修订/新待审标签，不代签新候选 | [场景相机 §8](../technical/unreal/SCENE_CAMERA_SEQUENCE.md#8-共用镜头库与补测2026-10-10) | WF-60 |
| 同Run composable_camera_library_v1.json、camera_coverage_candidates_v1.json | 三轴共用库与首批优先候选；未覆盖组合仍待验证，不作完整支持白名单 | [场景相机 §8](../technical/unreal/SCENE_CAMERA_SEQUENCE.md#8-共用镜头库与补测2026-10-10) | WF-60；关联WF-50/80 |
| 同Run expansion_plan_v1.json | 具体冻结轨迹、几何通过/拒绝与源pin；骨骼代理检查不等于渲染或人工接受 | [场景相机 §8](../technical/unreal/SCENE_CAMERA_SEQUENCE.md#8-共用镜头库与补测2026-10-10) | WF-60；关联WF-80 |

## 稳定跟拍试验入口（2026-10-10）

新Run `%OUTPUT_ROOT%/unreal_character_import/camera_stable_follow_20261010_v1/` 的配置/轨迹/实际交付清单由[场景相机Technical §9](../technical/unreal/SCENE_CAMERA_SEQUENCE.md#9-稳定跟拍镜头试验2026-10-10)拥有，45候选实施中，具体机器清单以实际生成后登记为准；人工接受pending。此前§8的43条清单保留前序交付，不再表示当前执行范围。动作替换语义见[ADR-0018](../project_management/decisions/ADR-0018-ACTION-DEPENDENT-STABLE-CAMERA.md)。

| 稳定跟拍机器入口 | 用途与边界 | 所有者 |
| --- | --- | --- |
| 同稳定跟拍Run expansion_plan_v1.json / stable_geometry_audit_v1.json | 45冻结轨迹、301端点帧及适用代理诊断，非人工接受 | [场景相机 §9](../technical/unreal/SCENE_CAMERA_SEQUENCE.md#9-稳定跟拍镜头试验2026-10-10) |
| 同Run review_delivery_manifest_v1.json | 15镜头×3动作、45条可播放真实媒体，全部人工pending | [场景相机 §9](../technical/unreal/SCENE_CAMERA_SEQUENCE.md#9-稳定跟拍镜头试验2026-10-10) |

## 完整角度扩充入口（2026-10-10）

`%OUTPUT_ROOT%/unreal_character_import/camera_complete_angles_20261010_v1/` 由[场景相机Technical §10](../technical/unreal/SCENE_CAMERA_SEQUENCE.md#10-完整角度与七动作扩充2026-10-10)拥有；机器真值为 `expansion_plan_v1.json`（冻结配方/轨迹）、`prepared_jobs_v1.json`（独立UE场景与Sequence）、`media_validation_*.json`（各attempt验证媒体）及 `review_delivery_manifest_v1.json`（当前可播放集合）；恢复分批由 `recovery_render_batches_20261011_v1.json` 与 `recovery_execution_20261011_v1.json`承载。未完成媒体保持pending，当前精确进度从PROJECT_STATE读取，不以目标数冒充已交付数。此前45整体认可限用户所看范围，近景诊断与生产限制保留。

## 清理后当前审查动作入口（2026-10-12）

`repo://00_engine/assets/character_creator/current_review_actions_20261012_v1.json` 与 `review_motion_sources_20261012_v1/` 为保留十项早期动作的现用读取/规范化FBX输入；由[角色运行时](../technical/unreal/CHARACTER_RUNTIME.md#2026-10-12-清理后的当前动作读取与依赖恢复)拥有，消费WF-50。旧导入报告已删除且未伪造重建；当前包/源FBX/保留复制回执的SHA重新核对只证明现用依赖，跨性别兼容仍待实际验证。恢复回执为 `%OUTPUT_ROOT%/workspace_cleanup_20261012_v1/current_actions_runtime_recovery_v1.json`。


## 横屏标准与全动作跟随反查（2026-10-15）

| 机器权威 | 用途与适用边界 | Technical所有者 | 消费Workflow |
| --- | --- | --- | --- |
| `%OUTPUT_ROOT%/camera_follow_general_compact_20261015_v2/horizontal_camera_standard_v2.json` | 上一版已接受k=.75配置，现由§20的k=.5替代；本文件、旧比较与媒体冻结保留，不再作为当前面板标准 | [场景相机 §19](../technical/unreal/SCENE_CAMERA_SEQUENCE.md#19-全动作跟随审计横屏近距标准与七档对照2026-10-15) | WF-60/WF-80 |
| 同Run `follow_correction_v2.json`、`follow_correction_evidence_v2.json` | 当前沿用全30审计及320条原ID overlay；新增240与原80已由§20的user_acceptance_v3从外部明确接受全部非面部配方范围，不改本文件旧pending | [场景相机 §19](../technical/unreal/SCENE_CAMERA_SEQUENCE.md#19-全动作跟随审计横屏近距标准与七档对照2026-10-15) | WF-60/WF-80 |
| 同Run `user_acceptance_20261015_v1.json` | 前轮8组跟随含有意竖屏裁切接受、横屏k=.75采纳；不代签本轮新增6动作及六档新距离 | [场景相机 §19](../technical/unreal/SCENE_CAMERA_SEQUENCE.md#19-全动作跟随审计横屏近距标准与七档对照2026-10-15) | WF-60 |
| 同Run `compact_review_delivery_manifest_v1.json`、`delivery_validation_v2.json` | v2冻结54条比较及13份签名证据汇总；保留当时pending，当前接受/50%标准由§20的新回执决定，不改旧媒体 | [场景相机 §19](../technical/unreal/SCENE_CAMERA_SEQUENCE.md#19-全动作跟随审计横屏近距标准与七档对照2026-10-15) | WF-60/WF-80 |


| 机器权威 | 当前用途与适用边界 | Technical所有者 | 消费Workflow |
| --- | --- | --- | --- |
| `%OUTPUT_ROOT%/camera_standard050_accepted_20261015_v3/horizontal_camera_standard_v3.json` | 当前600非面部横屏原距离k=.5及FOV补偿，runtime8消费；竖屏600/面部60保持，旧k=.75冻结 | [场景相机 §20](../technical/unreal/SCENE_CAMERA_SEQUENCE.md#20-新增跟随接受与横屏靠近50现用标准2026-10-15) | WF-60/WF-80 |
| 同Run `user_acceptance_v3.json`、`matrix_validation_v3.json`、`runtime_validation_v3.json` | 新增6动作全部240路径与原80累计320接受、1260矩阵及36实际UE时点；不等于26场景结果已交付 | [场景相机 §20](../technical/unreal/SCENE_CAMERA_SEQUENCE.md#20-新增跟随接受与横屏靠近50现用标准2026-10-15) | WF-60/WF-80 |


## 固定26主场景选点与代表媒体执行反查（2026-10-15）

| 机器入口 | 用途与边界 | Technical所有者 | 消费Workflow |
| --- | --- | --- | --- |
| `%OUTPUT_ROOT%/all_primary_scene_sites_20261015_v1/survey_inventory_v1.json`、`survey_local_geometry_v1.json`、`survey_screen_proxies_v1.json` | 直接使用现有26主目录及当前1260组合/有限代理，不重新筛主图、不执行其余51层 | [场景相机 §21](../technical/unreal/SCENE_CAMERA_SEQUENCE.md#21-全部主场景拍摄点与曝光审查2026-10-15) | WF-60/WF-80 |
| 同Run `surveys/`、`candidate_sites/`、`checkpoints/` | 每图尝试、候选与进展；疑似问题不自动成为confirmed排除，当前完成范围由Status维护 | [场景相机 §21](../technical/unreal/SCENE_CAMERA_SEQUENCE.md#21-全部主场景拍摄点与曝光审查2026-10-15) | WF-60 |
| 同Run `scene_samples_sites_v1.json`、`scene_samples_index_v1.json`、`plans/`、`scene_samples_delivery_v1.json` | 固定26图的点位revision、代表计划及逐片合格可播清单；卡片存在不等于全图通过 | [场景相机 §21](../technical/unreal/SCENE_CAMERA_SEQUENCE.md#21-全部主场景拍摄点与曝光审查2026-10-15) | WF-60/WF-80 |
| 同Run `dual_signature_bindings/`、`dual_signature_snapshots/`、`dual_signature_reports/` | 仅fresh survey的严格Grass碰撞代理/完整raw外观双证据，raw diff及草层视觉警示必须保留；旧stale不追认，不是全局runtime升级或视觉通过 | [场景相机 §21.7](../technical/unreal/SCENE_CAMERA_SEQUENCE.md#217-草层原始变化独立dual入口与待实测边界) | WF-60 |
| 同Run `ground_object_bindings/`、`ground_object_reports/`及dual中的ground_query_policy/evidence/source | fresh定向地面查询证据链；simple分支另绑定同XY实际组件诊断及冻结base，网格接地/视觉仍pending | [场景相机 §21.8](../technical/unreal/SCENE_CAMERA_SEQUENCE.md#218-定向地面查询与严格消费链) | WF-60 |
| 同Run `panel_saved_points_sync_v1.json`、`panel_saved_point_backups/`及panel Run `sites/` | `--sync-panel-sites`默认离线预览、`--apply`才写managed点并备份；不得制造真实检查/人审签名，私有面板adapter仍待实机 | [场景相机 §21.9](../technical/unreal/SCENE_CAMERA_SEQUENCE.md#219-面板离线同步与独立私有adapter待实机验收) | WF-60 |


## 固定26主场景交付末验反查（2026-10-15）

| 机器入口 | 用途与边界 | Technical所有者 | 消费Workflow |
| --- | --- | --- | --- |
| 同Run `conservative_scene_exclusion_proposal_v3.json`、`scene_exclusion_policy_application_v1.json` | 当前点绑定的保守提案与已应用策略；建议/应用均不冒称逐帧穿模或用户接受 | [场景相机 §21.18](../technical/unreal/SCENE_CAMERA_SEQUENCE.md#2118-交付末验检查点与实际面板验证) | WF-60/WF-80 |
| 同Run `panel_saved_points_sync_v1.json`、`panel_validation/panel_4c9578397c53.json` | 最新catalog同步及代表面板实机预览、EV/排除恢复、保护文件验证；早期sync_application仍为历史 | [场景相机 §21.18](../technical/unreal/SCENE_CAMERA_SEQUENCE.md#2118-交付末验检查点与实际面板验证) | WF-60/WF-80 |
| 同Run `initial_camera_rotation_all_scenes_validation_v3.json`、`current_samples_opening_frames_audit_v1.json`、`gallery_visual_status_validation_v2.json` | 新revision初始化定向测试、具名版本精确0/1审查及网页初审绑定；旧审查不覆盖新版本，人工pending | [场景相机 §21.18](../technical/unreal/SCENE_CAMERA_SEQUENCE.md#2118-交付末验检查点与实际面板验证) | WF-60/WF-80 |
| 同Run `new_final_repairs_visual_notes_v4.json`、`current_samples_opening_frames_coverage_v2.json`、`gallery_http_validation_v1.json` | 最后4条具名版本抽帧/精确首帧补查、当前52条104帧覆盖和HTTP可取用；技术ready_for_human_review，非连续全片或用户接受 | [场景相机 §21.18](../technical/unreal/SCENE_CAMERA_SEQUENCE.md#2118-交付末验检查点与实际面板验证) | WF-60/WF-80 |
| 同Run `final_delivery_checkpoint_v1.json` | 当前技术交付集中回执；候选点/代表媒体ready_for_human_review，全部人工pending，非生产或全组合视觉接受 | [场景相机 §21.18](../technical/unreal/SCENE_CAMERA_SEQUENCE.md#2118-交付末验检查点与实际面板验证) | WF-60/WF-80 |


## 2026-10-21 当前审查进度反查

`repo://00_engine/outputs/review_progress_sync_20261021_v1/checkpoint.json`为已保存现用点位及人工排除的本次统计快照，非最终批渲染矩阵；现用真值仍为`pair_scene_review_20261019_v1/sites`和关联appearances。所有者为[场景相机Technical §22.18](../technical/unreal/SCENE_CAMERA_SEQUENCE.md#2218-当前进度统计与接续边界2026-10-21)，Workflow为WF-60。该节的曝光暂停为当时边界，恢复接入后的实现与验证反查下列§22.19入口，不从目录存在推断生产完成。

| 机器权威 | 用途与边界 | Technical所有者 | 消费Workflow |
| --- | --- | --- | --- |
| `%OUTPUT_ROOT%/local_render_profile_v1/profile.json`；`repo://00_engine/scripts/unreal/mrq_streaming_warmup_v1.py` | 当前机器专用审查／MRQ纹理预算配置与共用解析；匹配机器后按消费路径选预算，兼容旧单预算profile，不是跨硬件质量预设或纹理驻留保证 | [场景相机 §22.19](../technical/unreal/SCENE_CAMERA_SEQUENCE.md#2219-恢复曝光继承与正式开拍前纹理预热2026-10-21) | WF-60／WF-80 |
| `%OUTPUT_ROOT%/render_readiness_20261021_v1/exposure_result.json`、`render_receipts/readiness_budget10240_v1.json`、`media_validation.json`、`HANDOFF.md` | 共用曝光策略验证及当前预览复制的静态MRQ小样证据和恢复交接；初轮预算失败保留，不代表40人新正式装配、动作或全场景接受 | [场景相机 §22.19](../technical/unreal/SCENE_CAMERA_SEQUENCE.md#2219-恢复曝光继承与正式开拍前纹理预热2026-10-21) | WF-60／WF-80 |

## 2026-10-22 数据集第五轮授权规则反查

| 机器权威 | 用途与边界 | Technical所有者 | 消费Workflow |
| --- | --- | --- | --- |
| `%OUTPUT_ROOT%/dataset_balanced_graph_20261022_v5/RULES.json`、同根`GOAL.md` | 本次离线训练/测试重建的稳定机器规则与授权目标；执行事实见RULES.actual_implementation及下列候选证据，非生产Registry或正式Render Job | [探索Technical第五版](../technical/dataset/DATASET_DESIGN_EXPLORATION_20261021.md) | WF-10／WF-70（设计实验） |
| `%OUTPUT_ROOT%/dataset_balanced_graph_20261022_v5/CURRENT_CANDIDATE.json`、`candidate_c_seed1/audit.json`、`sampling_stability.json`、`independent_three_seed_audit_summary.json`、`initial_camera_distribution.json` | 唯一主候选、同图三sampling seed独立证据及初始镜头分布局限；备选不合并、采用待用户审查 | [探索Technical第五版](../technical/dataset/DATASET_DESIGN_EXPLORATION_20261021.md) | WF-10／WF-70（设计实验） |
## v11本地渲染入口反查（2026-10-23）

`00_engine/outputs/dataset_render_pilot_20261023_v1/main_jobs.json`、`pilot_jobs.json`、`jobs/*/prepared.json`、`jobs/*/media_receipt.json`、`render_receipts/`及`TRANSFER_PLAN.json`由[数据集探索Technical](../technical/dataset/DATASET_DESIGN_EXPLORATION_20261021.md)拥有，范围为当前v11本地pilot与迁移准备。候选权威仍为dataset_return_control_20261022_v11/selected_candidate；这些执行输出不替换候选、不证明服务器或正式生产验收。
