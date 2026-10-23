# CC 角色组装与验收

> 文档 ID：`TECH-CC-04`
> 文档类型：`technical`
> 生命周期：`current`
> 适用阶段：`WF-30`
> 实现所有权：首批 Look 生成器、Bridge staging、RLPy 执行器、聚合审计和视觉证据；Headshot基础外观精简装配实验入口及其运行输出
> 验证所有权：`VAL-CC-01`、`VAL-CC-02`
> 输出契约：`OUT-WF30-CC-ASSETS`
> 最近核验：2026-10-18（男女PRELASH及女性选定睫毛几何/标准像素已验证；最终视觉与完整导出待验）

## 1. 能力与边界

当前实现可以按第一批机器清单分阶段构建 32 个烘焙 Look并在 CC 中保存项目；其中共享 RLPy 执行器还可由 `WF-40` 调用来产生 UE 导出 Bundle。规范 CC 项目与 CC 验收属于 `OUT-WF30-CC-ASSETS`，最终 FBX/JSON/纹理 Bundle 及其 Transfer Gate 属于 `OUT-WF40-TRANSFER-BUNDLE`。它是首批特化自动化，不是任意 BodyFit/Identity/Outfit 的通用一键产品。

## 2. 当前实现组成

| 文件 | 角色 | 运行环境 |
| --- | --- | --- |
| `cc_build_first_batch_full_reference_looks_v3.py` | 编译 32 Look、缺失工作单和状态清单 | 系统 Python |
| `cc_first_batch_full_reference_looks_20260822_v3.json` | 32 Look 权威定义 | 机器配置 |
| `cc_first_batch_full_reference_missing_looks_20260822_v1.json` | 补齐 16 Look 工作单 | 机器配置 |
| `run_first_batch_missing_looks_export.ps1` | 为 `WF-40` 分阶段提交当前批次缺失 16 Look；不是全量重建器 | PowerShell/Bridge |
| `cc_validate_body_reconstruction.py` | CC 内加载、装配、截图、保存和导出 | CC/RLPy |
| `cc_audit_first_batch_full_reference_matrix_v1.py` | 合并 CC 结果并验证 32/32 | 系统 Python |

## 3. 输入契约

- BodyFit、Identity、Appearance 和 Outfit Registry 哈希一致。
- 每个 Look ID 在完整矩阵中唯一。
- CC 源项目和资产路径位于 Bridge allowlist。
- 输出使用新 `run_id`，不覆盖已接受项目。

## 4. 执行方式

首先用生成器重新编译工作单并运行其测试：

```powershell
$CCRoot = 'D:\UE\Lance_Work\00_engine\scripts\character_creator'
python "$CCRoot\cc_build_first_batch_full_reference_looks_v3.py"
python -m pytest "$CCRoot\tests\test_cc_build_first_batch_full_reference_looks_v3.py" -q
```

需要 CC 作业时先执行 Bridge 健康检查。查看当前增量入口的参数：

```powershell
Get-Help "$CCRoot\run_first_batch_missing_looks_export.ps1" -Detailed
```

真实执行命令、唯一 Run ID、前置应用状态和 Transfer 输出见 [CC FullReference 到 UE](../transfer/CC_TO_UE_FULLREFERENCE.md#6-cc-导出执行与当前边界)。不得再次执行已完成的 missing-16 作业来“证明”通用性；新矩阵需要新计划、新 Manifest 和新的全量包装器。

## 5. 组装顺序

```text
load canonical BodyFit/source project
  -> apply identity and supported head state
  -> apply proportion/head-neck decisions
  -> apply skin/eyes/teeth/brows/lashes/hair/beard
  -> apply outfit family and footwear
  -> normalize pose/camera/light
  -> machine inspection
  -> visual acceptance
  -> save project and export bundle
```

## 6. 验收

每个生产 Look 至少需要：

- 项目可重载，Inventory、BodyFit、Identity、Outfit 和哈希一致。
- 中性正面/侧面/三分之四取景。
- 眨眼、闭眼、微笑和张嘴无眼球/牙齿/嘴唇硬错误。
- 服装在静态与代表动作中无未接受的严重穿模。
- 材质接缝、皮肤/头部颜色和头发遮挡可接受。

## 7. 输出与保留

规范 `.ccProject`、Look Manifest 和 CC 聚合验收属于 `OUT-WF30-CC-ASSETS`；动态联系表、用户决定和失败根因是其 `retained_evidence`。最终 FBX/JSON/纹理 Bundle、源到 UE 映射与导入 Gate 属于 `OUT-WF40-TRANSFER-BUNDLE`，由 [Transfer Technical](../transfer/CC_TO_UE_FULLREFERENCE.md) 解释。Bridge staging、重复截图和已合并 partial 结果可在最终审计后标为 `superseded/disposable`。

## 8. 恢复

CC 出现未知弹窗、Undo 错误或内存增长时停止当前 Look，保留作业结果，由用户重启后从未完成 ID 恢复。不得把未完成目录晋升为成功 Bundle。

## 9. Headshot基础外观精简装配（2026-10-05）

本节拥有[已完成基础装配计划](../../project_management/history/completed_plans/PLAN-2026-10-HEADSHOT-BASE-ASSEMBLY.md)的精简入口、几何保护、配置、调度及恢复。Run Root为`%OUTPUT_ROOT%/character_creator_bridge/artifacts/headshot_base_assembly_20261005_v1/`，归`OUT-WF30-CC-ASSETS`，默认unclassified保护；保留分类未审查前不得删除。第5–6节首批完整Look流程不作为本流程的逐角色验证要求。本轮只做CC基础外观，导出、UE导入、头发/服装/动作装配及渲染另立计划。

### 9.1 输入与实现入口

输入是第三步完成的CC5 Average、照片面部及固定头皮修正项目，在runtime_staging独立副本工作；不重放旧身份/BodyFit滑块或头颈配方。有效牙齿与口腔沿用输入，有实际异常才修复。代表为人工photo01女性裸subd0；准确源、副本及SHA由`representative_v3/assembly_report.json`的`config.input_lineage`保存，该阶段完成时CC为其装配后角色，当前运行对象由PROJECT_STATE决定。

| 实现 | 职责 | 当前生命周期 |
| --- | --- | --- |
| `00_engine/scripts/character_creator/cc_compile_headshot_base_assembly_v1.py` | 确定性选择皮肤、眉毛、睫毛、眼睛及颜色，编译输入/资产/SHA/geometry policy | `validated_pilot` |
| `00_engine/scripts/character_creator/cc_run_headshot_base_assembly_v1.py` | CC/RLPy精简装配、逐步几何检查、独立保存与失败恢复 | `validated_pilot` |
| `00_engine/scripts/character_creator/run_headshot_base_assembly_v1.py` | 系统Python准备、串行提交、同job续查及按角色恢复 | `experimental` |
| `00_engine/scripts/character_creator/cc_capture_assembly_geometry_v1.py` | 真实CC local顶点捕获与坐标/工作层元数据 | `validated_pilot` |
| `00_engine/scripts/character_creator/cc_assembly_geometry_invariants_v1.py` | 离线分区比较、准确索引豁免和超限判定 | `validated_pilot` |
| `00_engine/scripts/character_creator/cc_base_assembly_geometry_policy_v1.json`、`cc_base_assembly_geometry_policy_v2.json` | 本节独占证据SHA绑定的具名资产/索引/性别上界配置；v1保留，v2扩展male选择 | 实验配置，仅登记实际诊断范围 |

既有外观函数及资产池说明见[外观Technical](./APPEARANCE_ASSETS.md)，前置几何修正见[BODYFIT_IDENTITY_AGE.md](./BODYFIT_IDENTITY_AGE.md)。代表机器及人工检查证明compiler/CC runner/capture/invariants的validated_pilot范围；系统wrapper仍experimental，只有离线测试和prepare-only smoke，没有真实CC提交。用户已接受当前女性代表中性外观及闭眼、微笑、张嘴，不作为男性/整库或批量准入。

### 9.2 固定装配顺序与颜色

```text
load independent corrected input
  -> capture original local Body geometry
  -> skin -> eyebrows -> eyelashes -> eyes Material Only
  -> eyebrows-only pigmentation -> face material quality
  -> pre-save geometry gate -> independent save -> post-save geometry gate
```

每步对装配前原始几何比较，失败即停止并恢复输入。不会在CC装头发、服装、动作、年龄或胡须，不随机换牙齿。代表集中检查后批量只做必要失败检测、日志及R06回执，不逐角色重复完整截图、细分或表情矩阵。

共享颜色契约保留`color_contract_version`、`hair_color_id/hair_color_mode`、`hair_color`的root/end/highlight_a/highlight_b sRGB、`visible_gray_fraction`和两highlight strength。当前CC的`target_domains/required_domains`都只有`eyebrows`；保留相同颜色记录供后续UE头发消费，不实现本轮UE调色。代表auburn读回Root`[0.301960796,0.113725491,0.094117649]`对应`#4D1D18`，Tip`#8B4430`，不是gold；用户在最终人工确认中澄清颜色与该配方一致，之前表达有误；没有另外判定渲染异常。

### 9.3 R06几何保护及原生睫毛片规则

使用`CC_Base_Body`的local `GetVertices(False)`，按锁定Clean Soft regions比较，四区默认均0.002mm；world比对仅在捕获方明确SubD0时允许。分区/噪声下限等准确契约见当前计划。`scalp_mask_zero`是Clean Soft零mask区，包含头皮、耳、颈及原生睫毛片，不能按名字理解为纯头皮。

`eyelash_geometry_diagnosis.json`以CC5安装资源`Resource/CCHeadshot/BlendShape/G3Plus_Eyelash_for_Male.obj`的material faces核验native/reference Body拓扑一致，证明704变点全部属于`Std_Eyelash`，所有Skin顶点0mm；它们不是眼睑皮肤或头皮变形。canonical policy仅为`Lush_Extended / CCAPP_EYELASHES_284c3a142668`登记`native_lash_strip_Lush_Extended`、确切704indices和8.2mm上界（实测8.147572mm+0.05mm后向上取0.1mm）。其他顶点、分区、资产及所有皮肤仍0.002mm；没有全局放宽或眼睑皮肤豁免。

编译器显式optional `geometry_policy_path`才消费该规则；执行器验证canonical路径、policy SHA、诊断证据SHA及精确asset匹配。v3八个gate全部通过；机器终验`representative_machine_completion.json`核对13,460保护顶点max0mm、native704点约8.147572mm、8checks/0failure。该规则不证明其他睫毛资产、男性代表或任意身份外观适配。

当前统一创建入口使用独立`cc_base_assembly_geometry_policy_v2.json`（SHA`c349699878bd3d7933e039bb07d8a8c28558dc2eb4cac90c5d2982ff34042955`）；v1保持原字节与女性8.2mm规则。新Run Root `headshot_character_creation_20261005_v1/male_native_lash_diagnosis_v1.json`绑定男性失败副本和真实捕获，证明704变点仍仅`Std_Eyelash`，max13.71484956mm，其余13,460点及所有Skin严格0mm。SDK Body OBJ没有`usemtl`，材质归属由真实OBJ与安装官方male全Body逐polygon顶点拓扑完全一致后映射，不能说SDK直接给出材质标记。

v2继承同一资产、同一704indices（13411–14114），female维持具名8.2mm；仅`sex_overrides.male`选择`native_lash_strip_Lush_Extended_male`、14.0mm及该男性诊断evidence/SHA。override只能更改name/tolerance/evidence/evidence_sha256四项，不能替换索引或改其他皮肤阈值。compiler与runner共用`registered_allowance_for_sex`选择和检查；runner只接受注册v1/v2精确路径及SHA/证据绑定。其他资产、非睫毛片/四区仍0.002mm，不是全局放宽或新任意身份接受。男性PROJECT_MALE_001/attempt_002当前v2已实际完整装配/保存，8项R06通过、source_unchanged；证据见新Run Root creation_validation_summary_v1.json及该attempt装配回执。只是该male raw代表机器范围，没有新人工视觉、male照片或全池接受。

### 9.4 眼睛Material Only的幂等边界

`cc_validate_body_reconstruction.py`的`appearance_eye_material_noop_verified`以及`apply_appearance_assets(..., allow_verified_material_noop=False)`提供显式opt-in；旧默认False，只有新精简入口启用True。只有eyes/.ccEye、asset SHA核验、SDK returned=true/is_error=false、精确Material Only弹窗clicked_count=1、眼球几何/支持配置保持及两次非空材质fingerprint完全一致，才接受已应用同资产的no-op。non-eyes、无效返回、空指纹、漏点击、几何或支持改变都不豁免，不以“无变化”普遍判成功。代表v3`material_noop_verified/material_only_verified=true`，眼球几何/支持保持。

### 9.5 调度命令与请求

系统wrapper支持互斥`--request`（一个JSON对象）或`--batch`（非空对象列表、character_id唯一）。请求包含character_id、sex、整数seed、source_project、regions_path及可选facial_components/geometry_policy_path；wrapper自行分配独立output_project。显式output若提供必须位于固定Run Root且不等于源；资产、输入、region、policy/证据等SHA都受保护。

默认/`--prepare-only`只编译配置并建立独立副本，不提交CC。现有真实准备请求可这样复现：

```powershell
Set-Location 'D:\UE\Lance_Work'
$AssemblyRequest = 'D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts\headshot_base_assembly_20261005_v1\wrapper_prepare_request.json'
python 00_engine/scripts/character_creator/run_headshot_base_assembly_v1.py --request $AssemblyRequest --prepare-only
```

`--execute`才串行提交给已运行CC，不启动/重启/联网。后续获准执行的形式为`python 00_engine/scripts/character_creator/run_headshot_base_assembly_v1.py --request $AssemblyRequest --execute --wait-seconds 600`；批量将`--request`换成`--batch <JSON列表文件绝对路径>`。`--wait-seconds`默认60，可600/1800。当前代表表情已获用户接受，但本轮没有运行CC batch；prepare或命令示例不是批量执行证据。

### 9.6 恢复与保护

`controller_state.json`保存attempt/job/source/manifest/library等绑定。pending续查同job，绝不重复提交；failed旧attempt原样保留，从原始源新建attempt/output；completed先核验源、配置、保存项目SHA与机器通过回执，再跳过。请求变化使用新character_id；已完成哈希漂移直接停止，不自动重做。控制锁存在时先确认是否仍有控制器运行，不自动删除运行中锁。准备失败也留下failed attempt；CC步骤失败恢复独立输入，不覆盖原项目。

### 9.7 当前证据与未完成范围

| 证据 | 实际结论 |
| --- | --- |
| Bridge `results/base_assembly_geometry_self_check_20261005_v1.json` | 真实CC capture self_check，14,164顶点/128scalar checks，numpy可用；只打印摘要，不创建角色捕获文件 |
| `representative_v3/assembly_report.json`、`assembly_geometry_invariants.json`、`representative_machine_completion.json` | 单女性代表完整机器装配/保存、8几何gate及源/副本/结果SHA核对通过，全部Skin0mm；只写1个眉毛材质，未装scalp hair |
| `representative_v3/ASSEMBLED_female_photo01.ccProject` | 独立保存106,531,576bytes，SHA`838f5abd083b32d239ae153e63fa94aa785e7bc5e412a0b67d88cd0baec41d70` |
| `assembly_closeout_v1.json` | 结项回执绑定human v2、保存SHA、机器8gate、结项307回归、16子系统归档审计及已归档计划/idle-null；单女性代表范围，无真实batch或UE执行 |
| `representative_human_review_v2.json` | 最新直接用户陈述绑定保存SHA：neutral/blink/smile/jaw_open及auburn眉毛颜色全部accepted，仅当前女性代表配置；旧v1 partial保留历史 |
| `wrapper_prepare_check.json` | 两次同request复用同attempt/job，源SHA保持、cc_submitted=false，Bridge队列无该job；wrapper26测试实际通过3.41s，没有运行batch |
| `base_assembly_regression_v1.txt` | 完整要求442项实际通过116.50s；wrapper26为后续单独测试，不冒作已纳入此完整集合 |
| `base_assembly_documentation_audit.json` | 16独立子系统及cross-layer实际通过，0error/0warning；Catalog/Inventory已重建 |
| `future_ue_interface_review.json` | 只读后续接口规划认为不需修改本CC输出，未运行导出/UE/动画/渲染，不构成后续接受 |

R01–R06completed，计划已归档。用户直接确认当前女性代表配置的中性皮肤/眉睫/虹膜及闭眼、微笑、张嘴正常，眉毛确为auburn；不推断男性、任意身份、整个外观池、实际batch或后续UE/渲染接受。这是基础装配计划的历史结项范围；后续统一CC创建任务也已在两入口机器范围结项，当前显式idle/current=null见PROJECT_STATE/BodyFit11，不自动启动批量或UE。

历史尝试只保留失败事实与证据，不覆盖当前状态：

| 尝试 | 失败与恢复 | 保留证据 |
| --- | --- | --- |
| 初始load v1 | Bridge输入allowlist拒绝；后续runtime_staging独立副本加载成功，源SHA不变 | Bridge失败/加载报告与input lineage |
| representative_v1 | 无豁免检查拦截704native lash点，恢复输入，未跑后续eyes/pigment/save | `representative_v1/assembly_report.json`、`assembly_geometry_invariants.json`、`eyelash_geometry_diagnosis.json` |
| representative_v2 | 前三步几何passed；Eyes_01已同输入资产，旧fingerprint必须变化误报，恢复输入 | `representative_v2/assembly_report.json`、`assembly_geometry_invariants.json` |

原RUN失败报告与机器receipt不改写；人工记录与机器结果分开追溯。

结项要求回归`closure_regression_v1.txt`实际307passed（36.06s），与前阶段442及wrapper26分开追溯，不合并虚构新总数。归档导航终验`closure_documentation_audit_v1.json`实际16独立子系统及cross-layer全部通过，0error/0warning；不重复CC/完整测试，也不扩大单女性代表接受或宣称真实batch/UE通过。

## 10. 面部皮肤细节独立对照实验（2026-10-12）

本节拥有 `skin_detail_optimization_20261012_v1` 的 CC 副本、选择性换皮、几何保护与配方证据，适用 `WF-30` / `VAL-CC-01`、`VAL-CC-02` / `OUT-WF30-CC-ASSETS`。它是用户授权的小样实验，不改变 native 40 人创建默认路线，也不是第二个 current 主计划。UE 与实际对照媒体由 [Runtime3.20](../unreal/CHARACTER_RUNTIME.md#320-面部皮肤细节独立对照实验2026-10-12) 拥有。

输入为现有一男一女成品项目及各自源照片；锁定输入哈希后只操作新副本。A 保留原版，B 保留照片皮肤而在 UE 优化材质，C 使用本地合适整套皮肤并匹配照片可见肤色。族群分类仅辅助候选整理，不作为固定色值。正常眼睛、眉毛、睫毛不随机重装；若换皮实际覆盖则按配方恢复。沿用已验证的固定头皮/Average/照片面部形状，不新增捏脸、位移或动态皱纹。

CC 输出根为 `%OUTPUT_ROOT%/character_creator_bridge/artifacts/skin_detail_optimization_20261012_v1/`，统一运行方案与准确作业状态在 `%OUTPUT_ROOT%/unreal_character_import/skin_detail_optimization_20261012_v1/EXECUTION_PLAN.md` / `execution_record_v1.json`。本轮已锁定 AF005 与 LM002，输入由 UE Run 的 input_manifest_v2.json 冻结；最终 CC 捕获选择由 c_final_capture_selection.json 指向女 C_skin_v3 / 男 C_skin_v2。实际实现与失败恢复见下节；当前是独立实验技术交付，不改变正式创建入口。

实际复用 `cc_repair_headshot_support_materials_v1.py` 的 `capture_geometry` / `compare_geometry` 检查装配前后全捕获几何与可用对象变换，阈值0.002mm；不默认应用此前睫毛片豁免掩盖新变动。检查中性及代表表情、头身接缝并独立保存。CC 保持离线，不擅自重启；pending 查询同 job，失败留存后诊断。输出默认 unclassified 受保护；限定机器保护证据见下节，用户视觉接受 pending，不升级正式生产或批量能力。

### 10.1 实际实现、缺图语义故障与恢复

`00_engine/scripts/character_creator/cc_skin_detail_experiment_v1.py`（experimental）及 `tests/test_cc_skin_detail_experiment_v1.py`（utility）由本节拥有。通过现有 CC dispatcher 注入 API，A 模式捕获/保存输入，C 模式仅应用 SHA 绑定的一个 `.ccSkin` 并恢复受影响的支持材质。当前 SDK 标准纹理通道和可读 shader 参数纳入比较，custom shader texture slots 没有导出，不声称完整自定义 shader 等价。

AF005 的 A_capture_v1 因 SDK 重复枚举 mesh 失败；修正去重后 A_capture_v2 与 LM002 A_capture_v1 实测保存前后几何 delta=0。换皮会同时影响 Std_Eyelash、Std_Nails、Std_Tongue 等支持槽，不能假设 `.ccSkin` 只改四个皮肤槽。AF005 C_skin_v1 在保护检查中停止，原失败回执保留。

后续 AF005 C_skin_v2 / LM002 C_skin_v1 旧回执虽然 success，但发现 GetImage 对缺失通道返回 616px 警告 PNG，旧像素比对误将其当有效纹理写回。独立 `missing_texture_semantics_limitation_v1.json` 将这两个保存项目明确限定为非最终 CC 项目，原报告及字节不改。已确认警告图 SHA 为 `38eb6ecb3423431ffae01afeff4ad43b14260fb47874a2f10677a2ffba298385`；其存在不能证明有效材质通道。

新实现分别记录 `textures` 与 `missing_textures`，已知警告图或 SDK 空图不会作为恢复源；对原本缺失而被换皮新增的通道调用 `RemoveMaterialTexture` 并立即读回缺失状态，已有真实纹理仍精确恢复和核验。不能仅凭返回成功或像素相等忽略空槽语义。新 AF005 C_skin_v3 与 LM002 C_skin_v2 已分别实测四轮几何 max delta=0、23 个受保护槽标准通道/可读参数检查通过并独立保存；准确 SHA 与项目见 Run `execution_record_v1.json`。此为 CC 范围机器事实。最终 C 保存后未另做独立重载验证；不能宣称通过重载。UE 标准贴图与参数子集的对照迁移见 Runtime3.20，用户最终视觉接受仍 pending。

### 10.2 皮肤替换的身份外观边界

两人 CC C 副本捕获范围内几何差0mm，阈值0.002mm，且可用对象变换保持；23 个非皮肤材质槽标准 SDK 纹理及可读参数恢复并读回。这不代表 Head Diffuse 中照片烘焙的眉毛、唇色、斑点或胡茬像素保留。C 明确替换这些像素，实际女性眉区/唇色观感和男性胡茬/脸色变化必须交由用户比较。部件材质保持与面部颜色内容保持不是同一结论。

候选女性 Molly、男性 Justin 的准确资产路径/哈希在最终报告。以源照片可见肤色和候选预览选择，不将供应商族群目录名称作为身份判断或强制色值。本轮不实施“保留照片颜色、仅换法线/粗糙度”的混合配方；它只在 RESULTS.md 作为后续讨论候选。

### 10.3 用户手动纹理配方：暂缓实施（2026-10-12）

[面部纹理候选配方](./FACIAL_DETAIL_RECIPE_20261012.md)集中记录精确资产路径、男女基础层差异、红晕三选一、雀斑/痘痘二选一及50/100联动档位。用户已手动试用，自动化与UE还原尚未验证；明确暂不实施，先讨论CC与UE清晰度/材质还原差异。女性C_skin_v3项目已被用户指定为直接编辑工作文件，原报告哈希仅描述历史版本，不能据此覆盖用户修改；8893旧页面未包含这些新图层。此记录不改变另一会话当前主计划。


### 10.4 CFD40修复与新版装配执行范围（2026-10-18）

本节拥有`%OUTPUT_ROOT%/character_refresh_20261018_v1/`的执行计划、协同审计、装配及导入汇总记录，复用现有CC/Transfer/Runtime验证及输出契约。当前实现未完成，正式版本未发布；精确进度以该Run的execution_record_v1.json为准。采用[FACIAL_DETAIL_RECIPE_20261012](./FACIAL_DETAIL_RECIPE_20261012.md)新增简化节，旧全部纹理配方不执行。几何候选实现与保护证据另归BodyFit；新Makeup预设加载及图层操作须先实测，不能把旧rlHair成功证据复用为新方式通过。

本轮新增`cc_makeup_probe_v1.py`、`cc_skingen_controls_v1.py`、`cc_compile_character_refresh_v1.py`、`cc_run_character_refresh_v1.py`、`cc_refresh_material_pixels_v1.py`及对应定向tests，均experimental，由本节拥有。`cc_validate_body_reconstruction.py`受限分发makeup_probe、skingen_controls、character_refresh。实际Eyebrow层与保存重载signature已验证：女性Noble90/90、男性Knife100/100，按各自实际值保持。装配器使用真实SaveFile像素证据，首次换皮造成的睫毛/舌头支持图变化已有精确通道恢复及复查；不能按metadata指纹相等宣布保护通过。具体失败和已验证中间阶段由Run回执拥有，未表示完整选定睫毛或UE验收。

`cc_refresh_visual_probe_v1.py`及对应tests为本节拥有的experimental外观采集实现，输出同Run的CC artifacts子目录。男女修复几何已采集中性/闭眼正侧面并恢复独立源；工作SubD0，Render级别未观察，不代表最终画质或接缝接受。自动C_Blink规则不当作独立动画键，直接6通道按实际读回检查；规则内部求值不宣称已验证。首轮报告同路径覆盖问题及其修复见Run的VISUAL_PROBE.md、BLINK_CORRECTIVE_POSE_AUDIT.md和REPRESENTATIVE_VISUAL_BASELINES.md。

Run内`compile_transfer_manifest_v1.py`生成40人candidate-only清单并绑定现用共享Skeleton/正式目录，导入和发布仍pending；该脚本与完整导出、代表导入、睫毛followers及batch准备的正式Technical owner见[CFD40候选Transfer](../transfer/CFD40_REFRESH_CANDIDATE_TRANSFER_20261018.md)，Run的TRANSFER_COMPILER.md保留执行解释。新导出精确短路径根为`D:/UE/exports/character_creator/character_refresh_20261018_v1`，沿用原完整导出选项，不能使用旧FBX代替本轮未完成的导出。

本轮`cc_refresh_eyelash_probe_v1.py`与`cc_refresh_eyelash_probe_v2.py`及对应tests同归本节，生命周期experimental。v1真实Delicate加载新增两片睫毛，并使原遮眼片与泪线低层几何超出0.002mm；v2仅提供精确资产绑定的新增部件识别，不放行原支持件变化，未在CC重复提交。原高层保持不能证明低层未变。进一步诊断见Run的EYELASH_PROBE.md、DELICATE_APPLICATION_DIAGNOSIS.md，未接受新版睫毛装配。

`cc_refresh_eye_support_diagnostic_v1.py`及对应tests为本节拥有的experimental独立眼部诊断，通过`refresh_eye_support_diagnostic`分发。原始快照不主动发Morph通知，分离Apply、SetTime、渲染、Morph通知、保存及重载；scalar/vector/逆序读取交叉检查。诊断success仅指捕获完整、源恢复及哈希保持，不表示检测到的保护违规获准。保存的`DIAGNOSTIC_ONLY_expected_violation.ccProject`仅为证据，不得作为候选导出；见Run的EYE_SUPPORT_RESTORATION_DIAGNOSIS.md。

`cc_probe_eye_support_identity_v1.py`及对应tests同属本节experimental，通过`refresh_eye_support_identity`分发。先单原遮眼片182点进行同形替换验证，检查原生OBJ导出、UV/法线/面角、全部几何及保存重载，finally恢复输入。尚不应用睫毛、不执行实际支持件恢复；见Run的EYE_SUPPORT_IDENTITY_PROBE.md。前置持久诊断已经证实加载包装器后支持低层改变、渲染后高层也改变，保存重载不消失，精简数字及源报告绑定在eye_support_Delicate_persistence_compact_v1.json。

v1实际单RIAvatarPart导出返回RStatus7，在替换前停止且恢复源。`cc_probe_eye_support_identity_v2.py`及对应tests同归本节experimental，改为复用整角色`AllClothes|FullBodyPart`原生OBJ并提取唯一精确支持组，保留原v/vt/vn/usemtl与面角信息，其他保护门不变；不能将离线提取通过当作真实替换通过。见EYE_SUPPORT_IDENTITY_PROBE_V2.md。

`cc_probe_eye_support_identity_v3.py`、`cc_probe_eye_support_identity_v4.py`、`cc_eye_support_inverse_affine_v1.py`及对应tests同归本节experimental。v2失败源于错误要求原生OBJ绑定形状等于SDK活动世界坐标，已有同源主流程OBJ与SDK数据已证明两者不同；v3只取OBJ拓扑/UV/法线模板、替换输入取SDK活动世界坐标。真实v3替换仍使遮眼片低层改变约0.2566mm，原其他11套网格保持，源已恢复。v4据该源绑定实测映射做一次补偿identity验证，保留全部真实0.002mm、渲染及保存重载门；不将预测精度当作实际恢复成功。分别见EYE_SUPPORT_IDENTITY_PROBE_V3.md、EYE_SUPPORT_IDENTITY_PROBE_V4.md及绑定数据。

SkinGen失败恢复严格保留各attempt。v3红晕前缺少角色选中，修复为唯一当前avatar重选与ID读回；v4源加载误拒绝已知撤销提示，修复仅去除labels/direct_text重复正文，并保留精确完整提示及唯一按钮检查。CC是否仍运行以同实例真实Bridge响应核实；受限进程枚举缺失不构成退出或重启依据。具体回执见Run的WF003_v3_redness_selection_diagnosis.md及WF003_v4_undo_warning_diagnosis.md。

v6在换眼后首次观察到编辑器disabled，角色重选读回正确也未恢复。新v3配置将Material Only换眼移到Makeup之前，并在after_eyes建立眼球/遮眼片/泪线标准六通道像素基准；saved与reloaded必须精确保持该基准，不继承源到结果允许换眼的豁免。完整范围、限定及离线验证见WF003_v6_eye_order_diagnosis.md。新顺序的真实可用性以独立attempt回执为准，不强制启用被CC禁用的控件。

用户重启CC后，v7编辑器enabled但父标签页未显示，严格可见性检查停止。只读祖先清单核实`qtAttributeRootTab`当前页0、编辑器位于`qtAppearanceTab`；`reveal_editor`通过唯一父页绑定和`indexOf(page)`切换标签，实际成功保持角色ID且editor可见/可用/勾选。此为面板导航能力，不代表红晕或完整装配成功；见Run的inspect_editor_ancestry_v1、reveal_editor_v1回执。

用户最终移除红晕组成，v4配置明确`excluded_by_user`，不把红晕作为剩余阶段或验收条件。WF装配v9已独立保存，但SkinGen仍开启时四皮肤与原睫毛标准通道读取为已知616px警告占位图，不能判断真实纹理损坏或宣布材质有效。`cc_finalize_refresh_partial_v1.py`、`cc_recover_refresh_saved_candidate_v1.py`及对应tests由本节拥有、均experimental；前者只接受成功partial，后者精确绑定v9已保存候选与失败证据，先验证眉毛层持久性，再关闭编辑器、实际SubD0、完整原生几何与像素检查、新保存重载，不重新装素材或改旧失败回执。见redness_excluded_and_finalizer_implementation.md和WF003_v9_saved_candidate_recovery.md。尚未宣称完整配方或真实UE接受。

`cc_probe_eye_support_identity_v5.py`、`cc_eye_support_obj_semantics_v1.py`及对应tests同归本节experimental。真实v5单原EyeOcclusion同形替换已通过8项几何阶段、渲染、保存重载；最大世界误差0.000305325mm，回源0mm。UV/拓扑/材质/smoothing严格相同，法线变化须符合各自真实几何重算及原序列化精度；不扩大几何阈值。尚未证明实际Delicate后的遮眼片/泪线修复或完整装配。见Run的EYE_SUPPORT_IDENTITY_PROBE_V5.md及实际eye_occlusion_WF003_identity_v5报告。

`cc_probe_delicate_support_restore_v1.py`、`cc_support_affine_runtime_v1.py`及对应tests同归本节experimental。新mode `refresh_delicate_support_restore`复用已验证单遮眼片模型，并在本源Delicate后只读一次TearLine190实际替换响应，计算其独立恢复输入；最多两支持件各一次恢复，不循环调参。原13460 Body非睫毛点、原支持网格、UV、变换与新增两睫毛均有完整终检，finally回源；只有真实渲染/保存重载全通过才保留几何候选，仍非完整外观/UE接受。见Run的DELICATE_SUPPORT_RESTORE_PROBE.md。

`cc_probe_delicate_support_restore_v2.py`、`cc_probe_delicate_support_restore_v3.py`、`cc_support_evaluated_inverse_v1.py`及对应tests同归本节experimental。实测整角色OBJ只含原六件，因此OBJ用于原六件模板/UV核验，新增两睫毛以SDK几何/拓扑/owner保护，新增UV明确待完整FBX。v2的原低层即时恢复通过，但渲染后再次变形；v3基于该次实测的拓扑旧点求值算子逆解，单面corner按实证identity处理，现场只各恢复一次再执行全部求值/保存重载门。实际结果仍以独立run回执为准。

`cc_refresh_closed_assembly_v1.py`、`cc_verify_refresh_prelash_v1.py`及对应tests同归本节experimental。关闭编辑器的中间阶段不等于完整装配；真实四皮肤在首次保存重载出现颜色/标量通道变化，须保留逐通道差异及视觉核验，不能宣称恒等或静默增加容差。独立verify_prelash只再次Load同SHA、不Save，以首次已重载的实际产品图为基准检查严格像素稳定性、全部原生几何、来源链及眉毛已验证持久性；原生睫毛仍待实际选定资产替换，accepted_final与recipe_complete保持false。

本Run的`prelash_same_sha_implementation.md`拥有普通v5路径及实际证据解释：LM002_assembly_v1正常路径成功；WF003_verify_prelash_v2独立产品稳定验证成功。两者实际0/editor off、Body与全部12条native及owner变换保持，26材质同SHA产品重载无像素豁免。报告的success只指PRELASH阶段，完整装配/导出/UE接受仍pending。女性`visual_WF003_prelash_v1`采集与中性恢复通过，主agent限定审看neutral front/side和blink front未见明显硬颈缝或基础下巴嵌入；不替代选定睫毛后的最终视觉。

`cc_probe_delicate_support_restore_v4.py`、`cc_refresh_prelash_source_chain_v1.py`、`cc_refresh_selected_lash_pixels_v1.py`及`tests/test_cc_probe_delicate_support_restore_v4.py`、`tests/test_cc_refresh_prelash_source_chain_v1.py`、`tests/test_cc_refresh_selected_lash_pixels_v1.py`由本节拥有，均experimental。精确实现、冻结依赖/输入SHA及14项离线测试由`%OUTPUT_ROOT%/character_refresh_20261018_v1/delicate_WF003_prelash_combined_v4_manifest.json`拥有。v4从已验证PRELASH闭包加载，应用SHA绑定Delicate，复用v3实测两原支持恢复；原生睫毛及实测新增两片是授权材质变化，其余原皮肤、眼与支持严格保护，应用后新睫毛全部选定通道也须经渲染/保存重载严格相等。它不把几何v3通过提升为完整装配通过。当前串行job与终态由execution_record拥有；新增睫毛UV/完整FBX/最终视觉仍需相应实际证据。

女性combined v4已实际通过，`material_pixels_verified=true`，保存独立候选SHA `fd28fcc3c2db3897fb535495ba721a7fd9102a87f5a1fe1755b1da7b8d100522`后恢复不可变PRELASH源。其probe success仅证明本阶段几何与选定标准图像，原回执`accepted_final/recipe_complete/assembly_accepted`保持false，新增睫毛UV/完整FBX尚pending。source-bound `visual_WF003_assembled_v1`已完成中性/闭眼正侧面采集与中性恢复，主agent已实际审看四图并准许CC pilot完整导出及UE测试；该限定判断由新的独立Transfer receipt绑定，不倒改原probe或冒充用户最终/40人接受。

男性独立合并入口`cc_probe_delicate_male_prelash_v1.py`、来源链helper `cc_refresh_male_prelash_source_chain_v1.py`、求值逆解helper `cc_support_topology_runtime_inverse_v1.py`及`tests/test_cc_probe_delicate_male_prelash_v1.py`、`tests/test_cc_refresh_male_prelash_source_chain_v1.py`、`tests/test_cc_support_topology_runtime_inverse_v1.py`由本节拥有，均experimental。冻结实现/SHA、实际男性PRELASH与原几何锚点、12项离线测试由`%OUTPUT_ROOT%/character_refresh_20261018_v1/delicate_LM002_prelash_combined_v1_manifest.json`拥有；分发mode为`refresh_delicate_male_prelash`。男性从自身已验证产品来源链出发，不继承女性坐标或把女性实测结果当男性通过；原几何、皮肤/眼/支持及新增睫毛标准图像在渲染/保存重载后仍须实际验证。当前job与终态归execution_record，不由prepared manifest晋升接受。

女性四图经主agent实际审看后已允许CC pilot完整导出与UE测试，该授权只针对候选试点；不等于用户最终接受、40人接受或生产晋升。独立completed assembly receipt与export prepare由[候选Transfer Technical](../transfer/CFD40_REFRESH_CANDIDATE_TRANSFER_20261018.md)及其Run证据拥有，保留原probe的有限状态不改写。

本轮新增实验脚本所有权已补齐，Transfer对应实现与Technical已冻结；已执行Script Catalog、Output Inventory重建及文档合同检查，本scope owner/hash问题已清零。全局检查仍有其他会话的输出缺owner、旧导航锚点及output ID跨层问题，运行中新输出亦可能晚于目录快照；精确结果见本Run execution_record的documentation_catalog_check。未作无关修补、不为追刷输出持续重建、不声称全树审计通过；唯一current父计划及其他会话状态保持。

输出机器归属由`00_engine/outputs/RETENTION_POLICY.json`的`ownership_rules`登记：本Run根归本节的`OUT-WF30-CC-ASSETS`，其`representative_assembly`、`representative_exports`、`representative_import_jobs`候选证据子域归候选Transfer Technical的`OUT-WF40-TRANSFER-BUNDLE`。这次只补归属，不更改现有retention rule、默认unclassified或任何删除资格；运行中新增文件由下一次目录快照覆盖，不为追逐实时输出持续重建。

`cc_bind_refresh_geometry_commands_v1.py`及`tests/test_cc_bind_refresh_geometry_commands_v1.py`为本节拥有的experimental宿主侧薄层。它消费既有batch v7，固定剩38人的原源、各自archive、candidate命令及显式16corner fresh controller命令；不另建batch next/status。仅当既有representative_gate核实男女完整CC/export/sharedSkeleton导入/runtime接受后，显式`--execute`才可调用既有candidate→prepare→最多一步geometry advance；pending继续查询同job，不能改人重派。当前仅离线绑定38人、保留9个不同selected lash资产；0新candidate、0新geometry state、0CC/UE调用。完整selected-nine装配执行尚需独立通用runner，不得将此薄层称完整40人执行器。

该薄层产生的`%OUTPUT_ROOT%/character_refresh_20261018_v1/batch_geometry_command_bindings_v1.json`、同名manifest及`archive_calibration_final_equivalence_sample_v1.json`归本节`OUT-WF30-CC-ASSETS`，只记录固定命令、输入pin及离线决策，不产生接受回执。后续`batch_geometry/<character_id>/offline_candidate_v1`由既有BodyFit候选生成器生产，几何语义、验证及实际repair state/CC输出仍归BodyFit定义；本节只拥有其串行命令绑定，未改变几何生产所有权。既有batch plan/status/receipt/transfer outputs仍归候选Transfer Technical。本次仅补owner/输出范围，不运行全局catalog或变更retention/删除资格；4项定向离线测试与真实38人pin复核见薄层manifest，不能替代CC执行证据。


`cc_probe_registered_lash_prelash_v1.py`、`cc_refresh_registered_lash_contract_v1.py`、`cc_refresh_registered_lash_pixels_v1.py`、`cc_refresh_generic_prelash_source_chain_v1.py`及其四个同名`tests/test_*.py`由本节拥有，均experimental。它们将既有男性真实成功方法最小通用化为一个真实正常PRELASH、该人的注册九池selectedasset、历史精确object/mesh/style约束和本次实际新增拓扑；每支持件一次实际响应、一次恢复，总计最多4次ReplaceMesh。原13460/眼/原低高支持/owner最终0.002mm、原六UV/拓扑/材质、应用后实际标准六通道像素及保存重载/回源保持原门禁；无旧幅度豁免、无女性矩阵复用、无每款假拓扑表。27项离线测试与真实LM PRELASH离线prepare通过，未调CC/UE。exact mode/CLI、四件和名称别名合同及边界见本Run`REGISTERED_SELECTED_LASH_V1.md`；冻结pin归`registered_selected_lash_v1_implementation_manifest.json`。尚未将新通用入口/非Delicate新角色记为真实通过，不能将probe success当完整装配/UE接受。

该单case模块产生的本Run`*_prepared_manifest.json`、implementation manifest、说明及后续独立`registered_*`运行目录（报告、实测snapshot、OBJ、PNG对象库、rollback备份及候选项目）归本节既有`OUT-WF30-CC-ASSETS`，不改变retention或删除资格；staging library/同SHA项目镜像为允许Bridge读取的执行输入，不是接受产品。动态`selected_eyelash_parts_capture.json`保留真实SDK ordered faces，后续完整导出/Transfer receipt引用它的合同归Transfer Technical。当前仍由root串行控制共享CC/UE，既有batch next/status与representative_gate保持唯一控制入口；本次不跑全局catalog，收尾由root统一进行。


`cc_refresh_serial_stage_bindings_v1.py`及`tests/test_cc_refresh_serial_stage_bindings_v1.py`由本节拥有、均experimental，是剩38人一个case一tick的阶段串联薄层，不另建batch next/status、BodyFit算法、completed接受生成器或UE执行器。它依次复用冻结geometry thin、正常无红晕PRELASH、registered selected-lash、既有四图模块，等待本轮同格式的root真实四图/源资产具名704批准及completed CC receipt，再复用现有Transfer compiler与完整export prepare/status。`--execute`必须通过既有真实代表gate；pending持久同job、通信不确定不重派、actualfailed停止原attempt，不自动重建或跳人。12项定向离线测试通过，38人/9款order已生成但0CC/UE调用、0新geometry/serial运行state；精确SHA/命令与边界见本Run`serial_stage_bindings_v1_manifest.json`和`SERIAL_STAGE_BINDINGS_V1.md`。本入口不增runtime样本/验收条件、不伪造accepted。

该薄层的本Run`batch_serial_stage_bindings_v1.json`、`serial_stage_bindings_v1_manifest.json`、测试XML与说明归本节`OUT-WF30-CC-ASSETS`。后续`character_creator_bridge/artifacts/character_refresh_20261018_v1/batch_serial/<ID>/attempt_001`串联state及其PRELASH/lash/visual证据、对应runtime_staging输入归本节；其中引用的原BodyFit geometry状态仍由BodyFit拥有，外部completed CC receipt、transfer manifest、既有export preparation/inventory和FBX仍归Transfer Technical。本次不改变retention/删除资格，按root要求不跑全局catalog，由统一收尾整合机器目录与状态。


`cc_probe_refresh_skin_normal_restore_v1.py`及`tests/test_cc_probe_refresh_skin_normal_restore_v1.py`由本节拥有、均experimental；只绑定LM已装配源7cc5bc...及同人after_skin四张真实2048图，以已真实成功的SDK Normal四参写语义进行独立副本实验，不重装角色。Normal/Bump读口分别实录，只允许四Skin对应两读取变化；其余捕获八标准通道/眼口及睫毛、全部14164/natives/owner与保存重载/回源严格保持，不把读取空或warning替代为图，不声称FBX/视觉已通过。5项离线测试通过，0CC/UE调用；library/source/image/dependency pins与命令由本Run`LM002_skin_normal_restore_v1_manifest.json`和`SKIN_NORMAL_LOSS_AND_MINIMAL_RESTORE_V1.md`拥有，运行状态以root实际job为准。

本次`skin_normal_loss_readonly_audit_v1.json`、上述诊断/实验说明、manifest、测试XML及未来`character_refresh artifacts/LM002_skin_normal_restore_v1`全部由本节OUT-WF30-CC-ASSETS拥有；既有completed receipt/FBX/UE证据保持原Transfer owner，不覆盖或倒改。只读定位证明after_support_restore四图仍在、combined源起点已缺，尚不能归责于两者的皮肤清除调用；未采Normal与实际Normal空须区别。全局目录留root统一收尾，未变更retention/删除资格。

`cc_probe_refresh_skin_normal_restore_bound_v1.py`及`tests/test_cc_probe_refresh_skin_normal_restore_bound_v1.py`同归本节、experimental，使用私有module实例复用已真实成功的冻结LM引擎，仅替换WF精确fd28完整源和本人after_skin四图的lineage验证，不修改公共缓存或原SDK执行流程。7项定向离线测试通过；女性尚仅prepared，原报告/legacy候选保留，真实成功及回源后才加同SHA女性文件名别名。其wrapped library、`WF003_skin_normal_restore_v1_manifest.json`、`WF_SKIN_NORMAL_RESTORE_AND_BATCH_GATE_V1.md`、测试XML和后续WF003_skin_normal_restore_v1报告/图像/备份/独立候选均归本节OUT-WF30-CC-ASSETS。完整FBX/视觉仍由对应实际验证拥有。

男性Normal实验06:04:58实际成功，四Normal写/真实2048图读回/保存重载/回源已支持，reload Body world最大0.0004578878313803549mm且native local0；读取语义为Normal写入后Bump实际图、Normal getter仍空，不能混称。诊断MD追加真实终态，旧prepared manifest保留历史事实。剩38建议在关闭SkinGen/SubD0后、首次最终保存前最小接入本人四图补全，最终每次reload必须有真实图而非两次missing稳定；当前冻结serial v1尚不具备此新增实现，不因此放行批量。source skin法线可能不含后续眉毛Normal贡献，Diffuse/Makeup像素严格保护；不重装角色。未改retention或其他会话状态，全局catalog留root统一收尾。

`cc_refresh_skin_normal_closure_v1.py`及`tests/test_cc_refresh_skin_normal_closure_v1.py`同归本节、experimental。新可选入口私有复用冻结正常runner/closure及已实测Normal比较方法，在SkinGen实际关闭/SubD0/原几何检查后、原pixel_saved和首次最终SaveProject前补齐本人after_skin四真实图；健康者0写、缺者各一次Normal写，非四Skin对应通道变化仍严格失败。写后与各次最终reload须有实际图，双missing稳定不能通过；最终八标准通道同SHA产品稳定，原0.002mm及图层、像素、首次SkinGen序列化语义不变。6项定向离线测试通过，未实际CC执行；尚未修改任何冻结serial订单、dispatcher或当前v2依赖，最终mode/38新prepare版本待root确认后另行冻结。

其`skin_normal_closure_v1_implementation_manifest.json`、`SKIN_NORMAL_CLOSURE_HOOK_V1.md`、JUnit及未来本Run每case正常PRELASH内`skin_normal_closure/`八通道PNG/报告同归本节OUT-WF30-CC-ASSETS。WF独立同法Normal修复06:19:22实际成功，74abdc6a...候选及完整回源/图/几何证据由原runtime报告拥有；不能据此将新hook或38人标为实跑。原output/Transfer ownership与retention不变，全球catalog留root统一收尾。

`cc_refresh_serial_stage_bindings_v2.py`及`tests/test_cc_refresh_serial_stage_bindings_v2.py`同归本节、experimental。新入口私有复用冻结serial v1的实际控制流，只加Normal闭包mode/显式true、hook依赖及PRELASH实际文件图门；首次完成、completed step和facts恢复均重读同源capture/PNG，不能依靠complete标志或双missing稳定放行。原代表gate、同job pending、failed停止、外部source-specific批准和完整export合同不变。6项离线测试通过；root最终dispatcher SHA通知前未生成v2order或任何38运行state，不调用CC/UE。精确接线与命令由本Run`SERIAL_STAGE_BINDINGS_V2.md`和`serial_stage_bindings_v2_implementation_manifest.json`拥有。

该v2实现manifest、说明、JUnit、未来`batch_serial_stage_bindings_v2.json`与现有每case串联路径的Normal附加证据归本节OUT-WF30-CC-ASSETS；原BodyFit及Transfer/UE输出归属保持。未改旧v1、冻结实现、dispatcher、资产、retention或其他会话状态，未运行全局catalog。

root实际接入四处新mode后，按其明确给定dispatcher SHA`27b4c3a53897c7259a236729a3964b2a5f0c3d6aa1be96fdb961a2b670f84b2c`已离线生成`batch_serial_stage_bindings_v2.json`（SHA`f6c4d9c409ad0d553188d41a60c8005a7e77f01533ed59d2290591200b603d24`），38人/9款、30项实现依赖及原geometry/v7/backup pins全部checked通过；首人CFD40_AM_001只读preview通过，0运行state/0新geometry state/0CC或UE调用。新dispatcher AST语法与四处route检查通过，受影响6测试在新route下再跑通过（6.36秒），正式机器记录`serial_stage_bindings_v2_prepared_manifest.json`和`serial_stage_bindings_v2_routed_tests.xml`归本节既有OUT-WF30-CC-ASSETS；旧implementation prepared事实保留。

实际逐job仍由原BridgeStepDriver先持久化新job再提交；pending只查相同job，actualfailed保留原attempt。新提交前检查实际health/active_job_id及inbox/processing，有忙碌或队列绝不发新job。已确认的既有边界是：serial v1总catch会将尚无pending的新提交前busy/health错误标成failed，而非自动waiting；因此root开始新的execute tick前须确认idle/队列空，不宣称该冻结版本可忙时自动等候。本次仅定位并告知，不改已冻结实现/order；代表真实gate仍须由原owner核验，不从离线prepare或男方单独UE成功晋升两代表接受。

Run内`build_completed_cc_receipt_v1.py`和`00_engine/scripts/character_creator/tests/test_build_completed_cc_receipt_v1.py`由本节拥有、experimental。它仅在明确order/本人ID、已有root真实四图审批及本人源/资产具名704有限上界例外齐备时，离线构造代表同schema的completed CC receipt/results，并复用现compiler和冻结serial bind_external_completed对state deepcopy复核；不写活动state、不调health/submit/advance或应用、不自动审批/推算bound。实际Bridge jobs、本人geometry/PRELASH/眉毛/四Normal/selected lash/动态parts/四图链均核验，pending/failed一律拒绝。4项短负向测试通过；AM001当时未完成，未生成真实completed。独占新batch_cases输出，写后校验失败则保留REJECTED文件与失败报告，不覆盖旧结果。

工具说明`COMPLETED_CC_RECEIPT_BUILDER_V1.md`、implementation manifest、测试XML、pending配方/清单及builder检查报告归本节OUT-WF30-CC-ASSETS；真正completed assembly/results/compiled transfer manifest仍归既有候选Transfer Technical的OUT-WF40-TRANSFER-BUNDLE，后续完整FBX/UE接受不由构建器赋予。未修改冻结serial/compiler/route、retention或全局catalog。

Run内`build_skin_export_quality_v1.py`及`00_engine/scripts/character_creator/tests/test_build_skin_export_quality_v1.py`由本节拥有、experimental；只消费本人真实completed CC/Normal闭包或代表恢复证据、selected-lash重载像素、实际export_inventory和既有FBX source审计（或原import checked_request对已pin source_extract的审计重放），固化已有四Normal源PNG字节/RGBA全等及ORM.AO.R/Roughness.G八分量像素全等。真实PRELASH configID与hookID必须同本人，不造顶层ID；缺失/警告图/未完成均拒绝。status仅export_pixel_passed，UE绑定及视觉pending，不重parse FBX、不改冻结serial或应用。两代表真实v2bundle各重算通过，4项窄测试通过；真实AM001只验证四源图字段与generic Normal v2兼容，未生成未导出quality。精确命令/范围见本Run`SKIN_EXPORT_QUALITY_TOOL_V1.md`。

该工具manifest、JUnit、说明、代表全新tool_validation报告及后续本Run/batch_cases/<ID>/skin_export_quality_v1.json归本节既有OUT-WF30-CC-ASSETS；原completed/export/FBX/import仍归Transfer owner，不改retention或旧样本，不跑全局catalog。


### 10.4.1 本Run成熟阶段的逐人记录与批次抽查

用户明确要求成熟阶段提速。本段仅约束本轮CFD40 refresh，不改通用WF门、已有两代表回执、冻结order/source pins、正式registry或其他会话主计划。本节拥有本Run的[BATCH_VALIDATION_POLICY_V1.md](../../../../../../00_engine/outputs/character_refresh_20261018_v1/BATCH_VALIDATION_POLICY_V1.md)与[batch_validation_policy_v1.json](../../../../../../00_engine/outputs/character_refresh_20261018_v1/batch_validation_policy_v1.json)，它们是决策记录，不冒充新的可执行配置。

逐人保留本人来源/素材绑定、实际几何/保护件、CC最终四图（含闭眼睫毛、正侧面）、完整导出、骨架材质及既有四Normal/八ORM源像素记录；原非lash0.002mm与本人/源/素材具名native704上界不放宽。动作、服装、头发、MRQ不再逐人重复代表级矩阵，复用已验证路径、按批抽查，出现具体异常再深入。未单独抽查不写pass，也不设重复逐人runtime前置门；不新增抽查配额。

不创建临时8人关卡。40人完成后复用原审查体系做最终5页×8人审查；当前不是整批或用户最终接受。root-agent-reviewed批次样本与user acceptance分开，具体转移/运行时记录由[本轮Transfer Technical](../transfer/CFD40_REFRESH_CANDIDATE_TRANSFER_20261018.md)拥有，精确进度只在本Run execution_record/Status维护。红晕永久完全排除，其余授权范围继续。


### 10.4.2 本Run连续自动批处理与批终审查

用户新明确授权正常连续自动批处理，不再逐人检查，报错或一批结束统一审查。本文覆盖10.4.1中常规逐人视觉检查节奏，历史实际接受和原始证据保留。逐人root看图批准不再是正常CC至完整export前置；实际数字检查、source-bound最终四图捕获、完整export及骨架/材质/源像素证据仍必须保留。数值不通过、缺证据或实际报错不能当作pass，也不能以本授权放宽nonlash0.002mm或猜测本人native704例外。

记录须区分`automatic_numeric_checks_passed`、`four_images_captured`、`visual_review_pending_batch`。只有真实审查可写root视觉结论，用户最终接受独立；自动运行、exit0或图片文件存在均不产生视觉接受。不逐人重复动作/衣发/MRQ，不建临时8人图，40完成后沿原体系最终5页×8审查；红晕永久排除。

本Run机器政策和方法为`batch_validation_policy_v2.json`、`BATCH_VALIDATION_POLICY_V2.md`，同属本节既有OUT-WF30-CC-ASSETS Run记录；v1原文件保留。连续CC至export控制器现已冻结、准确owner及现有测试回执见下文；root实际启用CC，UE仍仅prepared，具体状态由Run回执拥有。当前数字只由execution_record/Status拥有，不重复动态计数。没有改变正式registry、冻结旧脚本或其他会话主计划。


本节连续CC实现已冻结（experimental）：`00_engine/scripts/character_creator/cc_refresh_continuous_cc_v1.py`、`00_engine/scripts/character_creator/tests/test_cc_refresh_continuous_cc_v1.py`，及本Run `00_engine/outputs/character_refresh_20261018_v1/build_numeric_cc_receipt_v2.py`。CC脚本SHA542648152f2c4a6ac731bdd26356f5732af5b58b33a6d0f9c699919a6abbe58f、numeric receipt适配SHA36e06abf86d746dc2459e1c8595f19e1e880240e3c8f9de3db50aaccb767f965。只复用原serial/builder，不改冻结旧入口、dispatcher或订单。

两阶段实际语义以本Run `CONTINUOUS_CC_V1.md` 和 `CONTINUOUS_BATCH_TWO_PHASES_V1.md` 为准：未登记本人native704上界是正常待批数值登记queue，装配和四图捕获继续下一人；不自动ceil本人max、不继承他人cap。批末root一次核本人source/asset/partition与实际数值，登记本人有限cap后，才连续完整export/UE；不用用户逐人确认。真实protectednonlash0.002mm、Normal/像素/来源/Bridge错误仍停。新的技术源receipt可保留原schema的completed/recipe_complete/assembly_accepted技术语义，但必须明示visual pending_batch_review、visual_accepted=false，不伪造root_visual_approval或用户最终接受。

本节OUT-WF30-CC-ASSETS还拥有本Run `continuous_cc_v1/progress.json`（内含`pending_native704_authorizations`和`ready_for_ue`逻辑队列，并非另造目录）、`continuous_cc_v1_prepared_manifest.json`、`continuous_native704_registration_availability_v1.json`、`continuous_cc_v1_tests.xml`、`CONTINUOUS_CC_V1.md`、`CONTINUOUS_BATCH_TWO_PHASES_V1.md`及文档观测回执`documentation_continuous_batch_activation_v1.json`。现有7项定向离线测试XML为0fail/0error，本文仅核回执，未重跑。旧policy JSON已被prepare钉hash，原JSON及被其pin的方法MD均保持字节。

root已确认旧controller退出并启动唯一连续CC；具体current和批数由Run progress/execution_record维护。UE连续协调器仍只离线prepared、尚未启用，不把准备当运行；其脚本、测试、configuration/progress和运行合同由原Transfer Technical拥有。本次仅窄owner/政策/状态同步，不运行应用或driver、不重建Catalog/OutputInventory和全仓audit；无全局通过声明。


连续CC恢复v2实验owner仍为本节：`00_engine/scripts/character_creator/cc_refresh_continuous_cc_v2.py`，SHA b8634bd12b17be7890a3faf34c2a7b325a6884421fca1ae8b025d678cb0cdc29。仅增加异常type/message/repr/traceback记录，原stage/gate/limits/调度不变；原空error未复现，不称根因已查明或该改动修复了根因。原v1、order、policy及failed历史保留，geometry_repair_audit是唯一CC owner，已恢复同原PRELASH job，无重派；具体会话和动态阶段由Run状态拥有。

本节OUT-WF30-CC-ASSETS新增精确范围为本Run `continuous_cc_recovery_v2/`（含progress、原failed与samejob/诊断副本、recovery_prepared_manifest_v2）及只读文档观测回执`documentation_continuous_recovery_RUN40B_v1.json`。原方法/JSON pins不改。UE新RUN40B引用恢复v2上游，仅离线prepared、旧A未运行被替代且保留；该实现及configuration/progress owner仍为Transfer Technical。本文仅核真实来源/结果/hash，不重复应用、测试或全仓审计。


AF005独立保存检查点续接实验owner同本节：`00_engine/scripts/character_creator/cc_resume_refresh_editing_checkpoint_v1.py`、`00_engine/scripts/character_creator/cc_resume_refresh_editing_checkpoint_v2.py`。两实际续接仍因Appearance/editor disabled失败（延长实际等待及清空重选），不称恢复成功或层已持久化。原checkpoint/failed保留，临时dispatcher均恢复。输出为本Run `AF005_editing_checkpoint_recovery_v1/`、`AF005_editing_checkpoint_recovery_v2/`及既有AF005 attempt内`01_prelash_recovery_v1/`、`01_prelash_recovery_v2/`，归本节OUT-WF30-CC-ASSETS；方法和结果由v2目录RECOVERY_RESULT.md拥有。所有controller已停止/CC空闲，后续先诊断本人检查点，不无条件重试，不变既有像素/几何门。当前剩余目标REMAINING_GOAL_V2.md和批次快照v11属于本Run计划/状态文档记录，不改变已pin策略或执行配置。


AF005正常窗口关闭及只读选择诊断实验owner同本节：`00_engine/scripts/character_creator/cc_close_refresh_profile_editor_v1.py`、`00_engine/scripts/character_creator/cc_inspect_refresh_scene_selection_v1.py`、`00_engine/scripts/character_creator/cc_inspect_refresh_scene_selection_v2.py`。真实Close一次隐藏FacialProfileEditor但独立inspect仍Appearance/editor disabled；选择v1因RLHANDLE converter不支持失败，v2保留opaque字段错误后完成实际只读inventory，Scene UI唯一actor与SDK一致，部件选择/隐藏/disabled检查未恢复editor。不能写AF005恢复或层持久性通过。dispatcher原字节恢复，未批处理/重启。

输出同本节OUT-WF30-CC-ASSETS：本Run `AF005_profile_editor_close_v1/`、`AF005_scene_selection_inspect_v1/`、`AF005_scene_selection_inspect_v2/`；原AF005 attempt内`same_scene_idle_inspect_v1/`、`current_mode_inventory_v1/`、`profile_editor_close_v1/`、`after_profile_editor_close_inspect_v1/`及相应scene-selection诊断子目录。结果边界由NEXT_RECOVERY_FINDINGS.md、SELECTION_RESULT.md及各manifest/pins拥有。本轮仅窄owner/status更新，无全局catalog或测试重跑。


最后一次只读材质映射诊断experimental owner：`00_engine/scripts/character_creator/cc_inspect_refresh_material_mapping_v1.py`，本Run `AF005_material_mapping_inspect_v1/`及AF005原attempt同名诊断输出归本节OUT-WF30-CC-ASSETS。实际26/26原scope shader映射一致、0getter错误，raw27多出旧scope排除Std_Nails不是新增损坏。editor仍disabled，未恢复；FINAL_DIAGNOSIS_BOUNDARY.md及bounded_diagnosis_summary.json限定结论。dispatcher已恢复、所有controller停止；正常重启CC仅加载原AF005检查点须先遵守此前用户不擅自重启约束，root已请求许可，答复前不执行。此为恢复待批准，不是文件已坏或保证可修；此前旧goal曾blocked等待重启许可；用户现已亲自重启并允许继续、清除旧goal，root已实际新建active goal。新会话仍须由geometry唯一owner恢复原检查点并实际验证，不称editor/队列已恢复。


AF005有界editor入口恢复实验owner：`00_engine/scripts/character_creator/cc_repair_refresh_editing_checkpoint_v3.py`、`00_engine/scripts/character_creator/cc_repair_refresh_editing_checkpoint_v4.py`。每次重载真实tab点击，disabled时同本人preset只Cancel一次，Add/Replace0；v3早期flags形状拒绝保留，v4只对齐实际列表结构。实际重载原Eyebrow100及原未解释flags相等，不以editor enabled代替持久性；新editing reload读层实际通过后才走原closure。

本Run `AF005_restarted_checkpoint_recovery_v1/`新增bounded_entry_v4失败及bounded_short_v5成功manifest/outcome/driver adoption同归本节OUT-WF30-CC-ASSETS。原attempt `bounded_normal_entry_v4/`失败保留：16条SaveFile路径260/261/269字符，成功上限259；同源同模块短输出根实际成功，捕获PNG最大214、八通道无错误，证明本次输出路径修复有效，不把失败通道当missing或支持材质损坏。短别名`%OUTPUT_ROOT%/character_creator_bridge/artifacts/character_refresh_20261018_v1/a5e5/`为junction，精确指向本人原attempt `recovered_short_v5/`，是同一输出而非第二份成品；成功report限定PRELASH，layer persistence/4Normal/8channel稳定/全几何原门通过，selected lash及最终视觉仍pending。

`continuous_cc_recovered_AF005_v4/`为本Run新的运行progress输出，仍由冻结`cc_refresh_continuous_cc_v2.py` phaseall执行，不是新controller版本；driver全门adoption后geometry唯一owner实际启动，动态会话和下一job由Run记录拥有。原failedprogress、原driver失败副本、冻结order/policy/dispatcher和全部pin不改。

另离线备选experimental owner：`00_engine/scripts/character_creator/cc_refresh_continuous_cc_v3.py`与`00_engine/scripts/character_creator/tests/test_cc_refresh_continuous_cc_v3.py`。方法/补丁/离线验证为本Run `CC_CONTINUOUS_V3_AF005_DEFER_STEPS.md`、`cc_continuous_v3_vs_v2.patch`、`cc_continuous_v3_validation_v1.json`、`cc_continuous_v3_tests_v3.xml`；已报告4项窄离线通过，不代表应用实跑。其AF005显式defer准备曾有9ready但从未run，因本人PRELASH已恢复现不消费、不改defer note或registry，不把延期当完成。本节仅补owner/实际诊断闭环，未重建Catalog/OutputInventory或全库测试。


代表门缓存v4两脚本的experimental owner同本节：`00_engine/scripts/character_creator/cc_refresh_continuous_cc_v4.py`、`00_engine/scripts/character_creator/cc_refresh_representative_gate_cache_v1.py`；对应测试`00_engine/scripts/character_creator/tests/test_cc_refresh_representative_gate_cache_v1.py`。仅进程内复用已完整通过且全部实际closure stat未变的代表门；key/closure变化重跑原全门，当前人物几何/像素/层/来源检查不缓存。root完整diff审阅由本RunREP_CACHE_V4_ROOT_REVIEW_V1.md拥有；3项离线测试与真实只读首次40.7856491s/同key复用2.3408648s passed、432文件stat未变是机制证据，不是全批应用通过或人物视觉接受。

本节OUT-WF30-CC-ASSETS拥有本Run `CC_CONTINUOUS_V4_REP_CACHE_STEPS.md`、`rep_gate_cache_validation_v1.json`、`rep_gate_cache_tests_v2.xml`、`rep_gate_cache_actual_readonly_v1.json`、`REP_CACHE_V4_ROOT_REVIEW_V1.md`及`continuous_cc_rep_cache_v4/`运行progress。root已确认旧controller正常停止、新geometry唯一会话phaseall启动，初次原代表门中；具体progress/人物/job状态由Run当前记录拥有，prepared文件不等同未launch，launch也不等同新job已提交。冻结v2/现有门/原pipeline未改，本次仅必要三条catalog/owner同步，不重建OutputInventory、全仓审计或全库测试。


本人检查点通用有界恢复实验owner同本节：`00_engine/scripts/character_creator/cc_resume_refresh_editing_checkpoint_generic_v1.py`，SHAc1d8d1672cd7ea23976b4b8b68c96ba5d80f10a9bceacb9837efde928969e8dc。按本人recipe/source、failedserial、checkpoint及原layer签名精确绑定，不继承AF005 opacity100/cap。BM001实际恢复和原driver strict adoption通过；3项定向实际证据检查含错ID/改签名拒绝，原始证据为本Run`BM001_checkpoint_recovery_v1/offline_validation_v1.json`，不替代全批或视觉接受。输出`BM001_checkpoint_recovery_v1/`及本人attempt `recovered_short_v1/`、短junction `b1r1/`和新`continuous_cc_BM001_recovery_v5/`同归本节OUT-WF30-CC-ASSETS。旧failedstate/progress保留，dispatcher原字节恢复；当前暂停恢复档案`continuous_cc_BM001_recovery_v5/pause_resume_20261018_2004/`亦属该scope，只由owner删除精确stopfile。动态会话与cap消费情况仅由Run当前记录拥有。 同一generic恢复输出`BM004_checkpoint_recovery_v1/`、本人attempt `recovered_short_v1/`及短junction `b4r1/`，和续跑`continuous_cc_BM004_recovery_v8/`亦归本节OUT-WF30-CC-ASSETS；原失败留存，实际PRELASH strict adoption不等于整人/视觉接受。


geometry私有batch代表门缓存漏口v5的experimental owner同本节：`00_engine/scripts/character_creator/cc_refresh_continuous_cc_v5.py`（SHA69310832a02ef152264e62701531eecbd403f250f5c2f2eab85407d2fa59e00c）、`00_engine/scripts/character_creator/cc_refresh_representative_gate_cache_v2.py`（SHA85eec3eabe83d5448cd0226eca4897ad62f49042350586ba1ec24dfcd79282d8）；测试`00_engine/scripts/character_creator/tests/test_cc_refresh_representative_gate_cache_v2.py`。只将geometry私有batch直接代表gate入口接入同一进程内成功缓存；本人全部原检查、显式batch语义、锁、geometry.advance及共享模块不改。root已完整审阅；随后已实际启动唯一v5会话，当前进度和PID由Run执行记录拥有。首次原gate中不代表已提交新人物job；旧冻结源码不改。

既有证据：`rep_geometry_cache_tests_v1.xml`三项窄离线0fail/0error；`rep_geometry_gate_actual_readonly_v1.json`（SHAbad5f1c9780ac010df78a514950412c138251499ccd010919dd2a270d3f6a565）实际原serial代表gate全验41.918123800s→geometry私有batch同成功缓存gate2.494869900s，434文件closure stat不变、两入口结果相同。caller plan检查另计，不缓存；这是一项gate的实测，不是整体批处理倍数，也没有实际geometry.advance/锁/app/progress/controller操作。原v4/helperv1及原geometry字节不变。

本节OUT-WF30-CC-ASSETS拥有本Run `CC_CONTINUOUS_V5_GEOMETRY_GATE_REUSE.md`、`rep_geometry_cache_validation_v1.json`、`rep_geometry_cache_tests_v1.xml`、`rep_geometry_gate_actual_readonly_v1.json`、`REP_GEOMETRY_CACHE_V5_ROOT_REVIEW_V1.md`。root新合并`native704_through_BM001_registry_registered_v1.json`（SHAb4ddcc06d4a5101bc19b4e5c42cb7addfd613bc4e8e330cd6a689336403c86ef）逐字段保留旧3人，新增BM001本人6.00有限cap；cap登记仅数值授权，不等于numeric receipt/完整export或视觉通过。当前人物与运行动态仍由Run记录拥有；本次只补这3条catalog及owner，未全库生成/测试，不改变冻结源码、pins、配置或其他会话主计划。


首次正常PRELASH有界入口及连续薄集成v6（experimental）owner同本节：`00_engine/scripts/character_creator/cc_run_character_refresh_bounded_entry_v1.py`（SHAaf5475c15eae0ee21e52d859ce2cc276dc63476642607ee8a9b4be09f1f5a297）、`00_engine/scripts/character_creator/cc_refresh_first_run_operation_v1.py`（SHA7198d6545deba1fd9b7cecb12e2354c27f8aa802694bee7ee96f43c7504fca49）、`00_engine/scripts/character_creator/cc_refresh_continuous_cc_v6.py`（SHA8243ca1204fa7f275024d24a51804b0375b341142d9761624051977ad2b429c2）；对应精确tests为`00_engine/scripts/character_creator/tests/test_cc_run_character_refresh_bounded_entry_v1.py`、`00_engine/scripts/character_creator/tests/test_cc_refresh_first_run_operation_v1.py`。

正常首次PRELASH在原runner两处插入已证有界入口：真实Appearance tab点击，必要时同本人Makeup preset精确Cancel一次；同runtime avatar最多一次重入，Add/Replace不授权。原mode/config、来源、wait、保存重载、层签名、几何、8通道像素与四Normal闭环全部保留，私有运行报告明示wrapper/source pins；旧源码不改。BM005首例`BM005_first_run_prelash_v1/actual_first_run_adoption_v1.json`实测340秒、2次入口审计、Cancel1/Add0/Replace0、原全门复核并由原driver接纳，属于首次正常执行而非failed checkpoint recovery；该回执仍仅证明PRELASH，不替代后来整人/视觉证据。不得外推全批倍数或零故障。

v6只组合冻结v5与上述入口，沿原Bridge耐久job保存intent/operation，等待同job终态后恢复精确路由并经原completed_report验证/adopt；transport/restart不得重复提交，dispatch前中断须留intent并恢复后停供检查。root已审阅，旧导出完成后的idle barrier已实际接入v6 phaseall；旧v8自然退出用于提速接入，非用户pause。具体实际launch/PID与当前人物仅由Run执行记录拥有；BM005首例不外推全批零故障。`bounded_first_run_tests_v1.xml`既有4项、`first_run_operation_tests_v2.xml`既有4项及`first_run_controller_v6_offline_validation_v1.json`真实BM005只读report gate均通过，本文仅核证据，未重跑。

OUT-WF30-CC-ASSETS新增本Run `BM005_first_run_prelash_v1/`（原state、首例manifest及adoption）、`bounded_first_run_tests_v1.xml`、`first_run_operation_tests_v2.xml`、`first_run_controller_v6_offline_validation_v1.json`；独占v6目录`continuous_cc_bounded_first_run_v6/`内含`progress.json`、`first_run_active.json`及`first_runs/<character_id>/{intent.json,operation.json,pending_serial_snapshot.json,dispatcher_original.py,dispatcher_owned.py,adoption.json}`，人物attempt内首次短输出与其精确junction仍归该人物证据。immutable intent/adoption/source pins纳入本人state.inputs，mutable operation不pin；`first_run_operation_tests_v1.xml`初次fixture缺pin失败历史保留，非v2通过证据。原failed及冻结order/policy/pins保留；本次仅5条catalog/owner窄登记，无全库生成、广泛测试或应用操作。


一次轻量真实计时对照（BM005，不作为整人提速承诺）：11项几何CC job的started/finished合计6分12秒，首任务开始至末任务结束跨度11分30秒；正常PRELASH340秒、睫毛224秒、四图60秒、完整FBX export66秒。BM004可比项为几何job合计6分02秒/跨度12分45秒、睫毛227秒/四图62秒/export63秒；其PRELASH含原失败及检查点恢复，不与首次完整流程直接比较。几何间交接空隙包含来源/订单/文件核验及调度，不能全部判为空等；numeric无独立起止计时，整段还含登记/控制器切换/其他人物导出，不据此宣称整人倍数或全批零故障。保持当前v6执行，不新增计时框架或优化实现。


自动连续v6首例已实际通过：BF001同job `cc_create_91bab98f19b0417e852a0fc0000d7def`于23:12:18→23:17:57完成（339秒），原层持久、四Normal/八通道、四阶段Body及原生支持门全部通过，Body最大0；2次入口审计/同1avatar、Cancel1/Add0/Replace0。controller自动恢复原dispatcher27b4c…并由原driver完成验证/adopt，`continuous_cc_bounded_first_run_v6/first_run_active.json`的intent已为null。实际adoption为`continuous_cc_bounded_first_run_v6/first_runs/CFD40_BF_001/adoption.json`（SHAad74847f97c8c6403a56ff1ba0df1ff8983772c94162cd1cd69f12e03eb01f25），report SHA0a94472f6308340043c9eb64df59da12cc1d485b004919e68be94f124b7cdb95。此为自动首次PRELASH机制实测，尚非BF001整人完成/视觉接受，不提前增人数，不外推全批零故障或整人倍数；未重复测试或修改代码/catalog。
