# Headshot 身份原型技术流程

> 文档角色：`technical_runbook`
> 状态：`validated_pilot`
> 适用阶段：`RM-05B..RM-06,WF-01..WF-03`
> 权威范围：Headshot 输入、冻结来源、CC5 Facial Profile 派生升级、原型存储、检查与生产接入边界
> 上级入口：[`README.md`](./README.md)
> 上游：用户准备的正面图、Headshot 2.x 与 CC 项目
> 下游：[`FACE_IDENTITY_AND_AGE.md`](./FACE_IDENTITY_AND_AGE.md)、[`../validation/VALIDATION_CATALOG.md`](../validation/VALIDATION_CATALOG.md)
> 最近核验：2026-08-10

## 1. 当前结论

`RM-05B` 已于 2026-08-10 通过并关闭。后续十候选扩展已将来源增加到女性与男性各五个；10 个派生副本均从 `CC4 Extended / 160` 直接加载同性交付的 CC5 HD Facial Profile，并在重载后保持为 `CC5 MetaHuman / 379`。

10 例均通过机器结构门禁：静态 Morph、眼球结构、材质分配和来源项目未改变；Profile 重载保持；Blink、轻笑、中笑、满笑、Jaw Open 与中性恢复可驱动。10 份原始输入照片均已一一映射并按 SHA-256 锁定；原 4 例已经用户视觉接受，新增 6 例保持 `pending_user_review`。此外，本批检查报告只持久化了升级前后 Morph delta，没有持久化新增项目的精确非零 shaping Morph 总数；六个 manifest 因此记录 `nonzero_shaping_morph_count=null` 与 `measurement_status=not_recorded_in_rm05c_batch`。这表示机器候选合格，不表示已经进入生产身份池。

已确认的关键事实不变：Headshot 身份已经烘焙进项目几何，不能仅保存一组滑块权重来重建。因此每个 Headshot 原型必须以 `.ccProject` 作为身份载体，以 `.ccFacialProfile` 作为动态配置载体。

规范头型的人工选择与两性动态验收已经完成。`headshot_project_seed_then_bodyfit_v1` 最小 Pilot 也已实现并取得男女 `2/2` 机器通过：Headshot 烘焙身份项目作为起点，随后只应用同性交付的平均 BodyFit、规范头型和比例参数；保存重载、眼球结构、材质、受保护 Morph 与五姿态动态门禁均通过。用户已接受最终装配视觉结果；当前路线只关闭并暂存十原型候选池，生产迁移与更多原型扩容延期到服装和动画验证完成后的 `RM-06`。

## 2. 来源、派生和生产三层

```text
冻结来源层
  输入照片 + 原始 Headshot .ccProject + SHA-256
        |
        v
派生候选层
  CC5 Profile 身份项目 + CC5 Facial Profile + 回退 Profile
  + prototype.json + 静态/动态证据 + 全部哈希
        |
        v
生产层
  用户视觉接受 + project-seed 装配实现 + 完整角色门禁
  -> 才允许加入生产 Face registry
```

- 原始项目不可覆盖，只用于追溯和重新派生。
- 派生升级不是完整的“CC5 HD 角色转换”声明；当前只证明 Facial Profile 已升级且身份几何未漂移。
- 机器通过不等于人工接受，也不等于已接入正式生成器。

## 3. 当前十个原型

| ID | 性别 | 冻结来源 Profile | 派生 Profile | 机器门禁 | 当前状态 |
| --- | --- | --- | --- | --- | --- |
| `F_HS_001` | female | `CC4 Extended / 160` | `CC5 MetaHuman / 379` | 通过 | `candidate_cc5_hd_rm05b_visual_accepted` |
| `F_HS_002` | female | `CC4 Extended / 160` | `CC5 MetaHuman / 379` | 通过 | `candidate_cc5_hd_rm05b_visual_accepted` |
| `F_HS_003` | female | `CC4 Extended / 160` | `CC5 MetaHuman / 379` | 通过 | `candidate_cc5_hd_rm05c_machine_pass_source_mapped_visual_pending` |
| `F_HS_004` | female | `CC4 Extended / 160` | `CC5 MetaHuman / 379` | 通过 | `candidate_cc5_hd_rm05c_machine_pass_source_mapped_visual_pending` |
| `F_HS_005` | female | `CC4 Extended / 160` | `CC5 MetaHuman / 379` | 通过 | `candidate_cc5_hd_rm05c_machine_pass_source_mapped_visual_pending` |
| `M_HS_001` | male | `CC4 Extended / 160` | `CC5 MetaHuman / 379` | 通过 | `candidate_cc5_hd_rm05b_visual_accepted` |
| `M_HS_002` | male | `CC4 Extended / 160` | `CC5 MetaHuman / 379` | 通过 | `candidate_cc5_hd_rm05b_visual_accepted` |
| `M_HS_003` | male | `CC4 Extended / 160` | `CC5 MetaHuman / 379` | 通过 | `candidate_cc5_hd_rm05c_machine_pass_source_mapped_visual_pending` |
| `M_HS_004` | male | `CC4 Extended / 160` | `CC5 MetaHuman / 379` | 通过 | `candidate_cc5_hd_rm05c_machine_pass_source_mapped_visual_pending` |
| `M_HS_005` | male | `CC4 Extended / 160` | `CC5 MetaHuman / 379` | 通过 | `candidate_cc5_hd_rm05c_machine_pass_source_mapped_visual_pending` |

冻结来源：

| ID | 原始项目 | SHA-256 |
| --- | --- | --- |
| `F_HS_001` | `D:\CharacterCreator_sucai\Reallusion Custom\Project\CC Project\RL_CC3_Plus Female.ccProject` | `8821192C81CBE1C6591BB1A3F1EF3E66242C1712C80FBDCE1BE13F34EE53E70` |
| `F_HS_002` | `D:\CharacterCreator_sucai\Reallusion Custom\Project\CC Project\RL_CC3_Plus Female2.ccProject` | `5C6626CA75045940744FF8DC7C68452326E1AA286EACD6423F3D37DC2542B027` |
| `F_HS_003` | `D:\CharacterCreator_sucai\Reallusion Custom\Project\CC Project\RL_CC3_Plus Female3.ccProject` | `48611509AAD5657424EC1A58C53A36734649C5997879AC1FCA7ADCDDB2945476` |
| `F_HS_004` | `D:\CharacterCreator_sucai\Reallusion Custom\Project\CC Project\RL_CC3_Plus Female4.ccProject` | `9CDB6D784E9E2A565587871A6CC5806583652280C9D2E2B50A051278164EA0B8` |
| `F_HS_005` | `D:\CharacterCreator_sucai\Reallusion Custom\Project\CC Project\RL_CC3_Plus Female5.ccProject` | `256E28DC25EBE20E2EC2F7A6569698C7388839AF2F84AF2113EDB45F97FB79DC` |
| `M_HS_001` | `D:\CharacterCreator_sucai\Reallusion Custom\Project\CC Project\RL_CC3_Plus Male.ccProject` | `92E38678EDBF6BE37A45703A864C8A7D6B82F321AF49A26E56C88FC21EAACDBF` |
| `M_HS_002` | `D:\CharacterCreator_sucai\Reallusion Custom\Project\CC Project\RL_CC3_Plus Male2.ccProject` | `4C303599F801DF968768E177261B6C1935A1E45106BF5B2B56CC2AF3B637EF67` |
| `M_HS_003` | `D:\CharacterCreator_sucai\Reallusion Custom\Project\CC Project\RL_CC3_Plus Male3.ccProject` | `20315D2857667E6A89DC9DE7DE7803338677171F6DCDD3A443718E4EC9C30BFA` |
| `M_HS_004` | `D:\CharacterCreator_sucai\Reallusion Custom\Project\CC Project\RL_CC3_Plus Male4.ccProject` | `636F1C65EE40ADE08B69981D303198C9F1C3BDE86E25EFA214BA3DC27C3C6D0E` |
| `M_HS_005` | `D:\CharacterCreator_sucai\Reallusion Custom\Project\CC Project\RL_CC3_Plus Male5.ccProject` | `727676E40CE249E418B5E3778C4A9B3653561B0412ED5F1666548D33FA9EA29B` |

`F_HS_002` 与 `M_HS_002` 的规范包参考图分别匹配 `D:\UE\CFD-LF-229-164-N.jpg` 和 `D:\UE\CFD-WM-252-224-N.jpg`。匹配依据是痣位、眼型、脸部比例与皮肤细节；该关联已写入 manifest，并纳入 2026-08-10 的统一用户验收。

新增六例的来源映射已经由文件名和人物身份视觉核对共同确认，并由配置和哈希锁定；不得再从 `.ccProject` 猜测或覆盖：

| 原型 | 原始照片 |
| --- | --- |
| `F_HS_003` | `D:\UE\CFD-MF-318-022-N.jpg` |
| `F_HS_004` | `D:\UE\CFD-MF-320-002-N.jpg` |
| `F_HS_005` | `D:\UE\CFD-MF-324-031-N.jpg` |
| `M_HS_003` | `D:\UE\CFD-IM-719-221-N.jpg` |
| `M_HS_004` | `D:\UE\CFD-MM-313-002-N.jpg` |
| `M_HS_005` | `D:\UE\CFD-WM-229-129-N.jpg` |

映射配置为 `cc_headshot_rm05c_source_reference_mapping_v1.json`，执行器为 `cc_attach_headshot_source_references.py`，报告为 `headshot_rm05c_source_mapping_20260810_v1.json`。每张照片的规范副本位于对应原型包的 `source_reference.jpg`，复制前后 SHA-256 必须完全相同。

派生升级目标：

| 性别 | Profile | SHA-256 |
| --- | --- | --- |
| female | `D:\CharacterCreator_sucai\Reallusion Templates\Actor\Facial Profile\Custom Profile\CC5 HD\HD Neutral F.ccFacialProfile` | `87FA3627F88AE98F903A6AE0A1F92A25DEDD9A8128641F3510F51008BD1A320E` |
| male | `D:\CharacterCreator_sucai\Reallusion Templates\Actor\Facial Profile\Custom Profile\CC5 HD\HD Neutral M.ccFacialProfile` | `05E5C8991456D8CFDBE45157A467866531359EBE31F933E066B0C69D2FD96A1B` |

## 4. Headshot 原始项目生成

当前 Headshot 生成仍是人工 UI 步骤，Bridge 负责生成后的受控检查。

1. 在 CC 中打开 Headshot，选择 `Pro`。
2. 选择与输入一致的 `Female` 或 `Male` Body Type。
3. 使用正面、中性、无遮挡、均匀照明的高分辨率图片。
4. 采用 `Clean Soft` 作为首轮纹理策略，生成 4096 纹理。
5. 检查五官标记后生成；不得用头发轮廓代替头颅轮廓。
6. 保存未经 BodyFit、服装、发型、年龄或随机局部 Morph 修改的原始 `.ccProject`。
7. 立即记录输入图和项目的路径、大小、修改时间与 SHA-256。

单张正面图不能可靠决定侧面深度和后脑。缺少侧面来源时，这两项必须标记为 `provisional`，不能仅凭正面相似度晋级。

## 5. CC5 Facial Profile 派生升级

### 5.1 当前已验证方式

RLPy 当前公开 API 没有发现等价于 UI “Convert Facial Profile 并保留设置”的转换函数。Pilot 使用以下受控派生方式：

1. 加载冻结来源项目并记录来源 Profile、Morph、眼球、材质和 bounds。
2. 将来源 Facial Profile 另存为回退 sidecar。
3. 直接加载同性交付 `HD Neutral F/M.ccFacialProfile`。
4. 将派生角色保存到独立 `.ccProject`，关闭并重载。
5. 验证 `CC5 MetaHuman / 379` 持久化。
6. 比较升级前后静态 Morph、眼球结构、材质、bounds 和来源项目 SHA-256。
7. 运行 Blink、三级 Smile、Jaw Open 和中性恢复矩阵。

该方式的标识是 `derived_direct_hd_profile_load_with_source_profile_sidecar_v1`。它是已验证的派生 Pilot，不冒充 CC UI 的官方转换操作。

### 5.2 机器结果

| ID | Morph | 眼球结构 | 材质 | bounds 最大差 | Profile 重载 | 来源哈希 |
| --- | --- | --- | --- | ---: | --- | --- |
| `F_HS_001` | 不变 | 不变 | 不变 | `0.00034332275390625` | 通过 | 不变 |
| `F_HS_002` | 不变 | 不变 | 不变 | `0.000362396240234375` | 通过 | 不变 |
| `F_HS_003` | 不变 | 不变 | 不变 | `<= 0.00045013427734375` | 通过 | 不变 |
| `F_HS_004` | 不变 | 不变 | 不变 | `<= 0.00045013427734375` | 通过 | 不变 |
| `F_HS_005` | 不变 | 不变 | 不变 | `<= 0.00045013427734375` | 通过 | 不变 |
| `M_HS_001` | 不变 | 不变 | 不变 | `0.0003108978271484375` | 通过 | 不变 |
| `M_HS_002` | 不变 | 不变 | 不变 | `0.00031185150146484375` | 通过 | 不变 |
| `M_HS_003` | 不变 | 不变 | 不变 | `<= 0.00045013427734375` | 通过 | 不变 |
| `M_HS_004` | 不变 | 不变 | 不变 | `<= 0.00045013427734375` | 通过 | 不变 |
| `M_HS_005` | 不变 | 不变 | 不变 | `<= 0.00045013427734375` | 通过 | 不变 |

证据目录：

```text
D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts\headshot_profile_upgrade\female_20260808_v2
D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts\headshot_profile_upgrade\male_20260808_v1
D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts\headshot_profile_upgrade\female2_20260808_v1
D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts\headshot_profile_upgrade\male2_20260808_v1
D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts\headshot_profile_upgrade\female3_20260810_v1
D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts\headshot_profile_upgrade\female4_20260810_v1
D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts\headshot_profile_upgrade\female5_20260810_v1
D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts\headshot_profile_upgrade\male3_20260810_v1
D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts\headshot_profile_upgrade\male4_20260810_v1
D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts\headshot_profile_upgrade\male5_20260810_v1
```

## 6. 规范原型包

规范根目录：

```text
D:\UE\Lance_Work\00_engine\assets\character_creator\face_prototypes\v1
```

每个原型目录必须包含：

```text
<prototype_id>\
  identity_cc5_hd.ccProject             身份几何载体
  facial_profile_cc5_hd.ccFacialProfile 动态表情配置
  source_cc4_extended.ccFacialProfile   回退/差异审计
  source_reference.jpg                  原始参考图；人工视觉通过前必须存在
  evidence\                              统一动态与静态证据
  prototype.json                         状态、哈希、来源和装配契约
```

中央注册表：

```text
D:\UE\Lance_Work\00_engine\scripts\character_creator\cc_headshot_face_prototype_registry_v1.json
```

注册表只登记包入口和状态；精确文件哈希、来源、升级结果和装配顺序由各自 `prototype.json` 管理。当前 10 个条目均为候选，`enabled_for_production=false`，且全部包含 hash-locked `source_reference.jpg`。通用暂存规则仍允许新候选短期缺少该文件，但 manifest 必须明确写入 `pending_user_mapping`；此时验证器禁止视觉通过和生产启用。若 `nonzero_shaping_morph_count` 尚未测量，manifest 还必须写入 `measurement_status=not_recorded_in_rm05c_batch`；验证器接受其作为候选证据缺口，但将 `shaping_morph_count_verified=false` 纳入生产硬门禁。

### 6.1 为什么不使用其他载体

- **Morph 向量**：已验证的 Headshot 身份不由普通 shaping slider 向量承载，无法用它替代项目几何。
- **仅 Facial Profile**：只承载表情配置，不承载身份几何。
- **Facial Profile AvatarPreset**：实验可保存，但同样不是身份载体。
- **AvatarPresetAll**：实验写出约 `73.8 MB` 文件后一直等待，直到用户关闭“未创建 Morph Slider，角色形状不会保留”的模态警告才在约 `2 小时 46 分` 后返回成功。该结果证明文件格式可写，不证明 Headshot 身份被保存；它需要人工介入、耗时不可接受且明确警告形状不会保留，因此不得进入生产路线。

规范决定见 [`ADR-0013`](../decisions/ADR-0013-HEADSHOT-BAKED-PROTOTYPE-STORAGE.md)。

## 7. 接入角色生成的唯一计划路线

Headshot 候选不能沿用“加载 BodyFit 后再读取 face slider 向量”的旧思路。计划中的 `headshot_project_seed_then_bodyfit_v1` 顺序为：

1. 按 `prototype_id` 从中央注册表定位 `prototype.json`。
2. 加载 `identity_cc5_hd.ccProject` 并验证 SHA-256。
3. 只把同性交付 BodyFit 的 Body/Junction Morph 应用到身份项目。
4. 收敛眼球和牙齿 Actor Parts，不清零未登记面部状态。
5. 重新加载该原型的 `facial_profile_cc5_hd.ccFacialProfile`。
6. 只应用 Face policy 允许的安全局部 Morph。
7. 最后应用 BodyFit 的 Head Scale 与 Neck Height。
8. 应用皮肤、眼睛材质、眉睫、牙齿、毛发和材质质量档案。
9. 执行面部动态和完整角色门禁，随后保存正式项目。

该顺序已在 `F02_Average` 与 `M02_Average` 最小 Pilot 中实现，状态为 `implemented_pilot_machine_and_user_passed`。它只证明两个平均体型，不代表十体型扩展或生产身份池迁移；十候选视觉冻结、`RM-06` 和正式配方集成完成前，不得将这些 Headshot ID 写入现有 Face V3 配方或设置 `enabled_for_production=true`。

### 7.1 头型单轴安全区间

人工审查 `2026-08-09-headshot-skull-axis-sweep-v2` 后，以下单轴区间获准进入下一步组合 Pilot：

| 参数 | Morph ID | 区间 |
| --- | --- | --- |
| `head_width` | `2019-08-13-15-33-14_head width` | `[-0.65, +0.65]` |
| `head_depth` | `2019-08-13-16-00-36_head depth` | `[-0.60, +0.60]` |
| `skull_height` | `2019-08-13-15-25-44_skull height` | `[-0.65, +0.65]` |
| `skull_width` | `2019-08-13-15-26-49_skull width` | `[-0.65, +0.65]` |
| `skull_depth` | `2019-08-13-15-27-43_skull depth` | `[-0.60, +0.60]` |
| `skull_back_depth` | `2019-08-21-13-57-18_skull back depth` | `[-0.50, +0.50]` |
| `skull_peak` | `2019-08-21-14-02-10_skull peak` | `[-0.55, +0.55]` |

唯一机器源是 `cc_headshot_skull_safe_ranges_v1.json`。原扫描清单继续保留 `Skull Back Depth = +/-0.70` 作为不可改写的范围发现证据；生产候选必须按安全区间配置夹紧。该审查只批准单轴范围，不批准 7 维范围的任意笛卡尔积；多轴组合需要控制联合幅度并通过独立 Pilot。

头型档案预算固定为全局最多 4 个，包含 `H00` 默认头型和最多 3 个差异化变体，不是男女各 4 个。男女优先共用相同 recipe ID，但每个 recipe 必须分别在至少一个女性和一个男性 Headshot 原型上通过静态与动态门禁。生产生成只从通过验证的头型档案 ID 中选择，不再独立随机 7 个轴；若共享档案在某一性别上失败，优先调整或淘汰该档案，不在没有证据时扩张为两套性别专用池。

### 7.2 多轴候选 Pilot

第二轮组合候选由 `cc_build_headshot_skull_composition_candidates_v1.py` 生成到 `cc_headshot_skull_composition_candidates_v1.json`。它提供 `C00` 默认和 `C01..C08` 八个候选，在 `F_HS_002`、`M_HS_002` 上共享同一组数值：

- 每个候选最多启用 3 个轴；
- 所有数值必须落在 `cc_headshot_skull_safe_ranges_v1.json`；
- 以各轴获批幅度归一化后，`L1 <= 2.0` 且 `L2 <= 1.2`；
- 候选 ID 使用 `C*`，人工选择后才晋级为 `H00..H03`；
- 第一轮只生成正面、四分之三和侧面静态证据；动态门禁只对最终入选档案执行。

本轮 CC 运行已经完成并由用户批准，状态为 `runtime_complete_user_approved`：男性 `9/9`，女性主批次 `6/9`，女性恢复批次 `3/3`，合并后为 `18/18` 个有效案例和 `54/54` 张原始图。所有成功案例均将受控 Morph 精确恢复到初始值，三个批次的 Undo 守卫点击数均为 `0`。

女性主批次中的 `C01/C02/C08` 首次被拦截，不是视觉失真，而是 RLPy 在多 Morph 应用期间把已经通过负值单轴扫描的 `Skull Height/Skull Width` 临时报告为 `[0, 1]`。执行器现仅对七个已经取得正负单轴证据的头型 Morph 使用 signed-runtime override；其他未知 Morph 仍严格服从运行时 bounds。恢复批次证明这三个案例可正常应用、截图并精确复原。该修复由 `test_cc_targeted_morph_initialization.py` 覆盖。

本轮机器证据：

```text
OUTPUT_ROOT\character_creator_bridge\artifacts\headshot_skull_composition_candidates\female_20260809_v1\validation_result.json
OUTPUT_ROOT\character_creator_bridge\artifacts\headshot_skull_composition_candidates\female_recovery_20260809_v1\validation_result.json
OUTPUT_ROOT\character_creator_bridge\artifacts\headshot_skull_composition_candidates\male_20260809_v1\validation_result.json
OUTPUT_ROOT\character_creator_bridge\artifacts\headshot_skull_composition_candidates\review_20260809_v1\index.json
VISUAL_PORTAL\runs\2026-08-09-headshot-skull-composition-candidates-v1\run.json
```

`cc_make_headshot_skull_profile_review_sheets_v1.py` 会忽略失败条目，因此可同时输入女性主批次、女性恢复批次和男性批次，得到每个性别恰好 `C00..C08` 九列的评审图。`build_headshot_skull_composition_run.py` 将评审索引转换为门户 run。用户已完成选择，该 run 现为 `approved`；未入选候选仍保留为历史证据。

### 7.3 规范头型选择与动态门禁

人工选择由 `cc_headshot_skull_profile_selection_v1.json` 固化，稳定映射如下：

| 规范 ID | 来源候选 | 名称 |
| --- | --- | --- |
| `H00_BASELINE` | `C00_BASELINE` | Base |
| `H01_LONG_DEEP` | `C03_LONG_DEEP` | Long Deep |
| `H02_LOW_FLAT` | `C06_LOW_FLAT` | Low Flat |
| `H03_NARROW_SHALLOW` | `C08_NARROW_SHALLOW` | Narrow Shallow |

`cc_build_headshot_skull_profile_library_v1.py` 将选择文件和原候选清单编译为 `cc_headshot_skull_profile_library_v1.json`。该库只包含上述 4 个共享 recipe，在 `F_HS_002` 与 `M_HS_002` 上形成 8 个执行案例；每例仍重新加载只读项目，不从上一例累积状态。

动态机器门禁复用 `cc5_hd_tiered_natural_smile_v1`，检查双眼闭合、轻微/中等/大幅微笑、张嘴和动作后中性恢复。结果为 `8/8`：全部保持 `CC5 MetaHuman / 379`，姿态证据 liveness、动作后中性眼球一致性、受控头型 Morph 不变和案例结束后的精确恢复均通过，两个批次 Undo 点击均为 `0`。执行器的 `targeted_morph_dynamic_pose_review` 只允许每个 preset 一个确定候选，避免把候选扫描误用为组合随机器。

权威机器记录是 `cc_headshot_skull_profile_validation_v1.json`；精确执行清单被冻结为 `review_20260809_v1/executed_manifest.json`，避免后续状态字段更新覆盖运行输入。动态评审图由 `cc_make_headshot_skull_dynamic_review_sheets_v1.py` 生成，并登记为门户 run `2026-08-09-headshot-skull-profile-dynamic-gate-v1`。机器门禁与用户动态验收均已通过，但生产状态仍由下游 project-seed + BodyFit Pilot 控制。

### 7.4 Project-seed + BodyFit 最小 Pilot

执行清单由 `cc_build_headshot_project_seed_bodyfit_pilot_v1.py` 生成到 `cc_headshot_project_seed_bodyfit_pilot_v1.json`。案例固定为：

| 案例 | 身份种子 | 头型 | BodyFit | Head Scale | Neck Height |
| --- | --- | --- | --- | ---: | ---: |
| `F_HS_002_H00_BASELINE_F02_Average` | `F_HS_002` | `H00_BASELINE` | `F02_Average` | `+10` | `0` |
| `M_HS_002_H00_BASELINE_M02_Average` | `M_HS_002` | `H00_BASELINE` | `M02_Average` | `0` | `0` |

执行器模式是 `headshot_project_seed_bodyfit_pilot`，位于 `cc_validate_body_reconstruction.py`。每例严格执行：

1. 加载并校验 Headshot `identity_cc5_hd.ccProject` 与 `facial_profile_cc5_hd.ccFacialProfile`；
2. 捕获身份、面部状态和稳定中性眼球结构；
3. 只应用对应 BodyFit 的 Body/Junction Morph，确认 Face/Other 未被修改；
4. 应用 H00 规范头型；
5. 按 `head_scale -> neck_height` 应用比例参数，零值也必须显式执行；
6. 验证目标值、受保护 Morph 指纹、眼球结构和材质不变；
7. 保存 `.ccProject`，重新加载并比较 Morph 与中性眼球结构；
8. 执行 Blink、三级 Smile、Jaw Open 与中性恢复；
9. 输出身份三视图、BodyFit/组装全身对比、动态图、重载图、向量和结果 JSON。

完整机器权威是 `run_20260810_v4/validation_result.json`，结果 `2/2`：两例均为 `CC5 MetaHuman / 379`，BodyFit 目标、固定应用顺序、受保护 Morph、材质、眼球结构、项目重载、五姿态 liveness 和中性恢复全部通过。该运行早于显式子集汇总字段，完整性由 `requested_count=2`、两个结果和清单 `pilot_policy.case_count=2` 证明。早期 v4 全身图因角色平移而灯光未平移，不能用于曝光比较；执行器随后把 7 盏可移动灯与全身角色同步平移并在截图后恢复。修正灯光的女性逐案例结果和男性显式子集结果均通过，只作为视觉派生证据，不替代 v4 的完整机器权威。

评审图由 `cc_make_headshot_project_seed_bodyfit_pilot_sheets_v1.py` 生成，门户入口为 `2026-08-10-headshot-project-seed-bodyfit-pilot-v1`，状态为 `approved`。权威状态文件是 `cc_headshot_project_seed_bodyfit_pilot_validation_v1.json`，当前为 `machine_and_user_visual_passed_pilot_accepted`；`pilot_approved=true`，但 `production_approved=false`。

## 8. 可执行入口

原始项目检查清单：

```text
D:\UE\Lance_Work\00_engine\scripts\character_creator\cc_headshot_female_project_inspection_v1.json
D:\UE\Lance_Work\00_engine\scripts\character_creator\cc_headshot_male_project_inspection_v1.json
D:\UE\Lance_Work\00_engine\scripts\character_creator\cc_headshot_female2_project_inspection_v1.json
D:\UE\Lance_Work\00_engine\scripts\character_creator\cc_headshot_male2_project_inspection_v1.json
```

升级清单：

```text
D:\UE\Lance_Work\00_engine\scripts\character_creator\cc_headshot_female_cc5_hd_upgrade_v1.json
D:\UE\Lance_Work\00_engine\scripts\character_creator\cc_headshot_male_cc5_hd_upgrade_v1.json
D:\UE\Lance_Work\00_engine\scripts\character_creator\cc_headshot_female2_cc5_hd_upgrade_v1.json
D:\UE\Lance_Work\00_engine\scripts\character_creator\cc_headshot_male2_cc5_hd_upgrade_v1.json
```

执行示例：

```powershell
$LANCE_ROOT = 'D:\UE\Lance_Work'
$bridgeClient = "$LANCE_ROOT\00_engine\character_creator_bridge\cc_bridge_client.py"
$scriptRoot = "$LANCE_ROOT\00_engine\scripts\character_creator"
$artifactRoot = "$LANCE_ROOT\00_engine\outputs\character_creator_bridge\artifacts\headshot_profile_upgrade"

python $bridgeClient validate-bodies `
  --library-file "$scriptRoot\cc_headshot_female_cc5_hd_upgrade_v1.json" `
  --output-dir "$artifactRoot\female_<run_id>" `
  --confirm-scene-replace `
  --auto-dismiss-undo-warning `
  --job-id "headshot_profile_upgrade_female_<run_id>" `
  --timeout 1800
```

男性将清单和 ID 换为 `male`。该命令会替换 CC 当前场景，但不覆盖冻结来源，也不得自动关闭或重启 CC。

Project-seed + BodyFit Pilot：

```powershell
$pilotLibrary = "$scriptRoot\cc_headshot_project_seed_bodyfit_pilot_v1.json"
$pilotOutput = "$LANCE_ROOT\00_engine\outputs\character_creator_bridge\artifacts\headshot_project_seed_bodyfit_pilot\run_<run_id>"

python $bridgeClient validate-bodies `
  --library-file $pilotLibrary `
  --output-dir $pilotOutput `
  --confirm-scene-replace `
  --auto-dismiss-undo-warning `
  --job-id "headshot_project_seed_bodyfit_<run_id>" `
  --timeout 1800
```

单例诊断可追加 `--preset-id F_HS_002_H00_BASELINE_F02_Average` 或男性 ID。省略 `--preset-id` 才是完整 `2/2` 机器门禁；显式子集只能用于恢复、诊断或补充视觉证据。

原型注册表的离线哈希检查：

```powershell
python "$scriptRoot\cc_validate_headshot_face_prototype_registry.py" `
  --registry "$scriptRoot\cc_headshot_face_prototype_registry_v1.json" `
  --output "$LANCE_ROOT\00_engine\outputs\character_creator_bridge\artifacts\headshot_face_prototype_registry_validation_<run_id>.json"
```

### 8.4 十原型暂存与视觉页

新增六个来源项目先分别执行 `project_inspection` 和 `cc5_hd_upgrade` 配置；全部机器门禁通过后，使用一次性批次清单暂存不可变原型包：

```powershell
$scriptRoot = "$LANCE_ROOT\00_engine\scripts\character_creator"
$portalRoot = "$LANCE_ROOT\00_engine\visualization_portal"

python "$scriptRoot\cc_stage_headshot_rm05c_prototypes_v1.py" `
  --batch "$scriptRoot\cc_headshot_rm05c_source_batch_v1.json"

python "$scriptRoot\cc_attach_headshot_source_references.py" `
  --mapping "$scriptRoot\cc_headshot_rm05c_source_reference_mapping_v1.json"

python "$scriptRoot\cc_validate_headshot_face_prototype_registry.py" `
  --output "$LANCE_ROOT\00_engine\outputs\character_creator_bridge\artifacts\headshot_face_prototype_registry_validation_20260810_v4.json"

python "$scriptRoot\cc_make_headshot_identity_pool_review_sheets_v1.py"
python "$portalRoot\tools\build_headshot_identity_pool_run.py"
python "$portalRoot\tools\register_run.py" `
  "$portalRoot\runs\2026-08-10-headshot-identity-pool-10-v2\run.json" `
  --replace
```

`cc_stage_headshot_rm05c_prototypes_v1.py` 是不可变的一次性暂存器：目标 ID 已存在时必须失败，不覆盖旧包。它不会把未持久化的 shaping Morph 计数猜成 `0`；该计数保持未测量，必须在生产激活前补测。`cc_attach_headshot_source_references.py` 使用显式映射配置并校验来源哈希；它可幂等重跑，但发现目标文件或 manifest 哈希不一致时必须失败，不得静默覆盖。v2 视觉页将原照片置于生成中性正面上方，供用户先核对身份，再审查 3/4 和动态姿态。

`headshot_rm05c_prototype_staging_20260810_v1.json` 是映射前的历史暂存快照；`headshot_rm05c_source_mapping_20260810_v1.json` 才是新增六例来源关联及 manifest/registry 变更的权威记录。

权威产物：

```text
OUTPUT_ROOT\character_creator_bridge\artifacts\headshot_rm05c_prototype_staging_20260810_v1.json
OUTPUT_ROOT\character_creator_bridge\artifacts\headshot_rm05c_source_mapping_20260810_v1.json
OUTPUT_ROOT\character_creator_bridge\artifacts\headshot_face_prototype_registry_validation_20260810_v4.json
OUTPUT_ROOT\character_creator_bridge\artifacts\headshot_identity_pool_10\review_20260810_v2
VISUAL_PORTAL\runs\2026-08-10-headshot-identity-pool-10-v2\run.json
```

完整验证定义见 [`VAL-CC-03/04/05`](../validation/VALIDATION_CATALOG.md)。

## 9. 冻结状态与恢复条件

1. 原 4 个规范包的静态身份、侧面、闭眼、三级 Smile、Jaw Open 和来源图匹配已通过统一用户验收；新增 6 个包机器门禁通过且原图映射完成，但仍等待用户视觉接受或淘汰。
2. 7 个头型单轴范围已完成审查；6 个轴沿用扫描区间，`Skull Back Depth` 收紧为 `[-0.50, +0.50]`，门户 run 状态为 `approved`。
3. 当前 Bridge 在两性扫描结束后恢复 `healthy/idle`；批次未触发已知 Undo 警告，所有受控 Morph 均恢复到初始值。
4. 不再继续 AvatarPreset 身份载体实验；已有警告已经否定其生产价值。
5. 规范头型已确定为 `H00 Base`、`H01 Long Deep`、`H02 Low Flat`、`H03 Narrow Shallow`；两性动态机器门禁和用户动态验收均已通过。
6. `headshot_project_seed_then_bodyfit_v1` 男女平均体型机器 Pilot 已 `2/2` 通过，门户视觉结果也已由用户接受；`RM-05B` 因此关闭。
7. 十候选扩展已建立 10 个候选和 v2 统一视觉页；用户完成新增 6 个视觉接受/淘汰后，本池即冻结暂存。10/20 比较、重复率/覆盖/成本分析、更多原型扩容、`RM-06` 面部配方验证和生产注册全部延期到第一批数据之后。

当前 Face V3 的 20 seed、17 个生产主原型和 200 条配方保持不变。Headshot 候选不进入第一批数据；只有第一批交付完成并启动 Roadmap 的 `RM-06` 后，才恢复本页未完成的视觉决定、配方比较和生产注册。
