# 动作、表情与 Morph

> 文档 ID：`TECH-UE-02`
> 文档类型：`technical`
> 生命周期：`current`
> 适用阶段：`WF-50/WF-60`
> 实现所有权：动作窗口、身体/面部组合、Root Motion、表情曲线和 Morph
> 验证所有权：`VAL-UE-01`、`VAL-UE-03`
> 输出契约：`OUT-WF50-RUNTIME-ACCEPTANCE`
> 运行环境：UE Editor Python、Animation Blueprint、AnimSequence
> 最近核验：2026-10-09（四表情与动作扩充技术交付；用户自然度待审查）

## 1. 通道模型

身体动作与面部表现可独立选择，但组合前必须分类：`none`、`curves`、`bones` 或 `hybrid`。只有 `reuse_policy=replaceable` 的身体动作才能与批准 Face Clip/Composite 重组；`paired/locked` 保留原始表演。

颈部和头部属于身体表演，不应被“纯面部”层覆盖。面部层只接管批准的 facial bone subtree/曲线；眼骨、Rig Logic 和直接 Morph 不得同时竞争同一输出。

## 2. 第一批生产输入与策略

- 每个性别 5 个动作，固定 5 秒、30 FPS、150 帧。
- `ACT_F02_CATCH_BREATH` 使用 `A_DM_F02_CATCH_BREATH_InPlaceCandidate_v001`。
- 其余动作保留源 Root Motion；短动作按 Registry 的 padding 策略补齐。
- 正式节点固定 `expression_id=happy`，表情不是第一批编辑轴。
- 每个动作使用其 `*_Happy_Composite_v001`，而不是临时预览动画。

精确路径、窗口和策略只从 `first_batch_graph_source_20260824_v1.json` 读取。

## 3. 构建与验证入口

核心实现：

- `ue_build_first_batch_idle_padding.py` / `run_first_batch_idle_padding.py`
- `ue_build_first_batch_inplace_candidates.py`

构建顺序为：导入 Body Motion → 应用窗口/InPlace/Padding → 建立表情片段 → 生成 Composite → 在同性生产 Skeleton 上验证 → 登记到图源。

## 4. 面部白块故障

已诊断的白块并非光照问题，而是表情曲线作用于错误/重复材质或 Post Process 求值路径。典型现象是中性帧正常，微笑幅度增大时额头和脸颊逐渐变白。

恢复原则：

1. 用已知正常的 `A_DM_M02_Face_SubtleSmile_Loop_v001` 和历史正确视频做对照；
2. 在角色 Blueprint 直接播放身体动作，确认材质本身正常；
3. 枚举异常 Face/Composite 的曲线，排除非几何材质参数曲线；
4. 使用已批准的直接 Morph/Composite 契约，避免 Auto Setup Post Process 与相同 CTRL 曲线重复求值；
5. 验证中性、微笑峰值和回落帧，再批量替换。

不得通过改变灯光或降低表情幅度掩盖该故障。

## 5. Morph 边界

`Full_Face_Elder` Pilot 证明同身份、同拓扑差值 Morph 可在 UE 组合 Blink/Smile/Jaw Open；它不能跨身份或跨 BodyFit复用。运行时身体 Morph 会要求服装和毛发拥有同拓扑支持，因此第一批不启用身体和年龄编辑。

## 6. Gate

每个动作/表情组合至少检查：无 T-pose、时间上有运动、头颈未冻结、眼睑/眼球/牙齿/嘴唇无明显穿模、肤色稳定、Root Motion 符合策略、五秒窗口准确。机器曲线检查与视觉检查必须同时通过。

## 7. 现成面部表演库与完整角色组合

2026-10-07新授权范围使用本机现成表演筛选4–6个有区别的面部片段，允许裁剪和调整强度、速度及衔接；不重新手工创作UE旧Happy/Sad/Angry曲线，不以相近片段凑数。本节既有第一批Happy Composite仍是历史批次契约，不作为新库默认素材或当前接受证明。

本节拥有`%OUTPUT_ROOT%/unreal_character_import/character_runtime_face_library_20261007_v1/face_library/`的现成来源盘点、源片段区间、候选取舍、派生关系/参数、通道分类、男女代表和身体组合验证。默认WF-50/OUT-WF50-RUNTIME-ACCEPTANCE、unclassified保护；当前60项男女静态/身体动作组合已技术通过；面部运行24步及可见面板技术交付已通过，用户审查仍待。来源不足4个明显不同且合适的片段时报告缺口，不靠数量目标放宽质量。

沿用本页通道边界：检查身体源是否已有面部轨道，面部只接管确认通道，不覆盖身体头颈或让不同驱动竞争。男女分别验证表情时序、眼牙嘴和肤色、关闭回中性及身体继续播放；面部选择/关闭和参数进入[Runtime3.18](./CHARACTER_RUNTIME.md#318-完整角色发色配置与现成面部库)的整套配置与重开恢复。技术交付、agent代表视觉和用户最终review分开记录，当前审查库技术交付完成，用户接受pending。

本阶段实验实现归属：`%LANCE_ROOT%/00_engine/scripts/unreal/native_face_curve_mapping_v1.py`及`tests/test_native_face_curve_mapping_v1.py`负责有证据的CC名称到UE Morph对应，不自行创作表演或把纯曲线视为完整面部姿态。`%LANCE_ROOT%/00_engine/scripts/character_creator/cc_native_face_library_v1.py`负责对隔离项目副本读取本机现成表演；其实际输出为`%OUTPUT_ROOT%/character_creator_bridge/artifacts/native_face_library_20261007_v1/`，默认WF-50/OUT-WF50-RUNTIME-ACCEPTANCE、unclassified保护。请求及源副本暂存于该脚本目录下`runtime_staging/native_face_library_20261007_v1/`，不改正式源项目。`%OUTPUT_ROOT%/unreal_character_import/character_runtime_face_library_20261007_v1/research/`盘点和对应关系研究同归本节；来源研究本身不代替筛选或身体组合验证；当前5候选与60组合结果见§7.1。

`%LANCE_ROOT%/00_engine/scripts/unreal/ue_compose_native_face_body_v1.py`归本节，属于实验组合实现：限制同一共享Skeleton与已审计面部骨范围，保留身体非面部轨道，使用源曲线采样；实际组合和有界视觉证据见§7.1与§7.4，完整角色运行验收另记。

### 7.1 当前现成候选与检查范围

旧Expression_Loop的Neutral/Happy/Sad Lo在当前CC5 MetaHuman副本中未产生有效眉嘴表演，不收入本轮库。改用本机`Expression Wrinkles/Sample Animation/Gentle_Female.iTalk`与`Dramatic_Male.iTalk`现成表演，裁剪为轻笑、认真、不满、惊讶、难过5个候选，保留源表演及裁剪/强度/过渡参数。根因证据边界见`research/legacy_italk_compatibility_diagnosis_v1.json/.md`：旧格式兼容问题尚未完全定位，不重做40角色的正式profile，也不根据文件名称接受表情。

2026-10-08最新技术检查点：`compositions/final_v3_manifest.json`的60项组合全部success，覆盖男女×5表情×静止及5身体动作，共14,568个SOURCE采样帧。面部最大平移误差约9.8564e-5cm、旋转0.112885832°、缩放8.0168e-7；非面部骨最大原比较误差约3.07858e-5。旧failed的displeased回执原样保留，新slug重试通过，不把失败转正。R03按现成候选技术筛选完成；完整角色面部选择/关闭、保存恢复和交付R04–R05已完成，实际证据归Runtime3.18。本检查点之后registry已按validated_review写入60项，用户最终接受pending。

### 7.2 原生曲线与面部骨的误差界限

组合从源动画逐帧求值，保留非面部骨及无关身体曲线，只替换审计过的面部曲线和10个面部支持骨。头、颈、root、pelvis仍属于身体。静态模式保留其明确参考姿态；不得把静态参考和动作源混为同一基线。

面部骨平移界限0.001cm、缩放绝对误差0.0001；面部旋转统一最大0.2°。UE将float32 quaternion转换成Euler通道时，近90°奇异分支存在真实表示损失；理论角损失上界约0.115349898°，0.2°给浮点转换和三角计算留统一余量，不再随单项失败逐次提高。已观察到约0.050052°和0.100910°，不能称为完全一致或仅显示误差。超过上限继续失败；非面部骨/曲线原有0.0001标准不变。

推导与原始最坏帧分别是`research/ue_quaternion_storage_bound_v2.md`及`research/ue_quaternion_storage_singularity_evidence_v1.json`。保留每份报告的实测、最坏帧和自己声明的阈值；已有0.1°成功报告仍有效，旧失败必须保留并独立重做。归一化证据绑定两份研究SHA，不用研究结论代替逐帧检查。

### 7.3 审查、入库与输出所有权

新增`%LANCE_ROOT%/00_engine/scripts/unreal/ue_capture_native_face_review_v1.py`归本节：root串行采集有界面部样本，结束恢复原动画并移除临时相机，不保存关卡或修改源资产。截图成功和leader绑定本身不能独立证明所有支持组件的表情曲线同步，须结合明确的实际观察/同步证据。

`native_face_library_contract_v1.py`及`tests/test_native_face_library_contract_v1.py`归本节，检查派生动画、来源闭包、实际检查和root审查是否足以成为可选择审查项。`tests/test_compose_native_face_body_v1.py`同归本节。运行时入口的`tests/test_cfd40_native_face_integration_v1.py`归Runtime3.18。

本节拥有本Run内`%OUTPUT_ROOT%/unreal_character_import/character_runtime_face_library_20261007_v1/compositions/`、`%OUTPUT_ROOT%/unreal_character_import/character_runtime_face_library_20261007_v1/face_previews/`及`%OUTPUT_ROOT%/unreal_character_import/character_runtime_face_library_20261007_v1/normalized_face_compositions_v1/`；均为WF-50/OUT-WF50-RUNTIME-ACCEPTANCE、unclassified保护。Run内`build_verified_face_registry.py`和`capture_final_faces.py`是本轮实验输出脚本，同归本节，不是通用生产入口。

`build_verified_face_registry.py`默认只核查；root显式`--publish`且全部所需证据通过后才写`%OUTPUT_ROOT%/unreal_character_import/character_runtime_face_library_20261007_v1/native_face_library_registry_v1.json`（validated_review）。root已显式发布60项validated_review审查库，用户接受pending；它允许后续运行检查，不等于完整运行验收完成。输入说明为`face_previews/FINAL_VISUAL_REVIEW_INPUT.md`：每性别/表情两个实际观察代表必须与其余仅全帧派生覆盖分开；用户最终接受始终另记。归一化不得把60项全写为逐资产人工观看，保存后同会话SOURCE读回也不能冒称新编辑器重开。

### 7.4 代表观察的真实边界

`face_previews/final_visual_review_v1.json`为root真实观察记录：男女各5表情，在静止和Audience两个代表组合上每项看7帧，共20项/140帧；其余40项只有逐帧机器源对照。额外放大观察男女惊讶和女性难过。看到眼口位置合理、面部首尾回中性，仍属于离散边界帧观察，不是连续视频视觉验收，也不保证已有身体动作的循环接缝平滑。

支持组件同步依据是代表图片中的可见眼口位置和5个支持组件到Body的绑定；没有数值读取这些组件的Morph内部缓冲。不得扩写为60个资产都逐一观看或支持组件逐帧数值同步。早期static capture的`CTRL_expressions_mouthJawOpen`诊断名不存在，未据其值推导下颌结论；后续animation capture已改用实际`CTRL_expressions_jawOpen`。旧回执不改写，此字段失效边界保留。

用户仍需评价自然度、强度与情绪标签。registry只应在全部证据核验后按validated_review入审查面板；运行时切换/关闭/保存恢复的后续实际验证由Runtime3.18拥有，不能用本节离散图片替代。

本轮输出实验脚本`build_face_composites.py`负责组合调度，`run_native_import.py`和`run_native_worker.py`负责隔离导入/worker派发（转移语义由Motion Transfer §8拥有）。它们不是用户接受证据。发布后的registry和normalized回执冻结，不因后续审查改写历史来源。

### 7.5 契约缓存修复与来源重绑定

面部运行验证第2步因playback字典的额外说明字段被误拒绝，属于接口比较问题，不是源动画资产失败。旧失败回执保留；改为明确比较mode/end_behavior的修复通过2项针对检查。新contract已在UE实际reload成功，24步运行重试全部通过；另有可见面板交付证据，R04–R05按技术条件完成。

契约缓存每次仍完整读取并校验文件字节SHA，只有path+sha相同才复用精简native_import解析，不凭mtime跳过实际内容校验。`offline_tests/native_face_evidence_cache_benchmark_v1.json`实测4份原生导入证据共163.813MiB：首次11.8006秒，再次0.8265秒，精简缓存26,308字节。这只衡量native_import证据检查，不代表整次UE操作或面板延迟。

本节拥有以下本Run迁移证据，沿用WF-50/OUT-WF50-RUNTIME-ACCEPTANCE、unclassified保护：`%OUTPUT_ROOT%/unreal_character_import/character_runtime_face_library_20261007_v1/registry_history/`保存旧登记表原始字节；`%OUTPUT_ROOT%/unreal_character_import/character_runtime_face_library_20261007_v1/contract_cache_registry_migration_v1.json`记录本次来源变更前后、旧档SHA和内容恒定检查。

后续用户对旧五种表情的限定确认和新五秒要求独立记录在§8。以上交付当时pending保持历史含义，不倒写旧证据，也不视为新五秒候选接受。

`rebind_verified_face_contract_v1.py`是本Run的一次性迁移输出脚本，归本节。实际迁移success：先由新contract完整validate，再保留旧登记表字节、原子替换并写回执。新旧文档唯一变化是sources.contract，60项entries及其余sources保持一致；旧registry SHA为d7512cba7323f3d90ce7db896cac20a8ec8769174155afe15691262e0b26b0e1，新registry SHA为31d28eb00ad7ce7e4e1e0a29d851422c6de6342a56b6a5a75954ab000e08c1c6，新contract SHA为b47984ec84ab987e9c42938b304f9f2cd81fc987db4c57a33dbb45d5d5634c2d。旧验证报告、资产、选择和用户pending状态均未改写。UE重载证据为`dispatch/refresh_face_contract_cache_v1_remote.json`，最终24步运行和可见面板交付的独立回执见Runtime3.18。

## 8. 五秒自然面部表演试验

2026-10-08用户已审查旧五种表情并确认整体正确，同时要求自然持续5秒；不能整体放慢眨眼/嘴部动作或仅拉大眨眼间隔。允许更长现成素材、自然延长与联网参考，先做少量试验。该要求收窄本轮时间适配边界，§7的历史速度调整许可不用于全局慢放凑五秒。

本节拥有[已完成计划](../../project_management/history/completed_plans/PLAN-2026-10-NATIVE-FACE-FIVE-SECOND.md)的N2=`%OUTPUT_ROOT%/unreal_character_import/native_face_five_second_20261008_v1/`：独立用户反馈、来源/节奏分析、候选参数、派生/组合、UE运行与代表观察、交付、回归及文档审计。沿用WF-50/OUT-WF50-RUNTIME-ACCEPTANCE、默认unclassified保护；所有权登记不等于候选已通过。实际源、命令及参数由主agent小样证据确定后补齐，不预写未运行实现。

user_feedback_20261008_v1.json绑定旧库与前序technical_delivery的SHA，记录用户对旧表情的限定确认及新要求；保留旧pending回执。新候选应独立派生，继续使用§7.2通道/误差边界，保留身体头颈和非面部轨道，检查真实5秒播放及眼口节奏、首尾和身体组合。机器长度、离散帧或源对照均不能代替连续自然度评价。旧审查库保持可用，未经证据确认不提前替换；最终用户自然度始终单独记录。

### 8.1 实验入口与隔离

本节新增拥有`00_engine/scripts/unreal/ue_native_face_five_second_v1.py`、`ue_capture_native_face_five_second_v1.py`和`ue_import_five_second_source_v1.py`（experimental）；`tests/test_native_face_five_second_v1.py`及`00_engine/scripts/character_creator/tests/test_cc_native_face_experiment_output_v1.py`（utility）验证时间、路径、成功回执与CC输出分支边界。它们不能作为正式库默认入口。

五秒组合入口隔离加载原composer，只重定向N2及`/Game/DataMake/Validation/NativeFaceFiveSecond20261008/Composites`。任务必须给出同性源/参考网格、批准面部曲线名、连续五秒源窗，固定`face_rate=1`、`face_playback=hold`、`body_mode=static`与参考姿态；拒绝额外envelope、全局变速、loop和覆盖参数。该入口只做静态身体小样；独立身体兼容探针见§8.3，未晋升新身体动作矩阵。十个面部支持骨与既有全帧源对照继承§7.2，头颈/身体不得被新MotionPlus整体带入。

隔离导入入口调用[Motion Transfer §8](../transfer/MOTION_TRANSFER.md#8-完整角色现成面部表演转移)原生导入器，仅重定向到N2和`/Game/DataMake/Validation/NativeFaceFiveSecond20261008/Sources`。继承源FBX SHA、现有同性共享Skeleton、已有目标拒绝、全新报告与Skeleton保护检查。只导动画/轨道/曲线，不导网格材质或保存源Skeleton；成功导入仍不是五秒自然度接受。

现有`cc_native_face_library_v1.py`只新增明确的`experiment_id=native_face_five_second_20261008_v1`输出选择；省略字段继续原输出根，未知ID拒绝。新CC根`%OUTPUT_ROOT%/character_creator_bridge/artifacts/native_face_five_second_20261008_v1/`由本节拥有，WF-50/OUT-WF50-RUNTIME-ACCEPTANCE、unclassified保护。来源仍限定旧隔离project copy和已安装表演目录，并逐份核对SHA；不保存/覆盖源项目。实际源/request/Bridge回执见N2的`cc_jobs/`和该CC根，精确路径以请求为准。

### 8.2 复现与观察边界

准备原Gentle的男女5.35–10.35秒候选任务可从仓库根执行：

```powershell
python 00_engine/scripts/unreal/ue_native_face_five_second_v1.py --prepare
```

该命令只准备任务，不操作UE；若目标任务已有不同内容会拒绝。root核验当前UE目标后，通过N2的`dispatch_worker.py`串行派发：组合入口用`DM_NATIVE_FACE_FIVE_SECOND_TASK`，导入入口用`DM_NATIVE_FACE_IMPORT_TASK`，采样入口用`DM_NATIVE_FACE_FIVE_SECOND_CAPTURE_TASK`指向对应任务JSON。N2的`build_samples.py imports`按成功CC导出生成独立导入任务；`initial`派发初始Gentle任务。相应工具为本Run实验编排，不自动修改旧登记库，不晋升通用生产。

新采样入口要求对应成功组合报告、source unchanged、十骨范围、五秒时长及完整逐帧源对照，按0–5秒30Hz的151个含端点样本采集。它隔离复用原capture，原全局默认上限仍50，每样本仍等待16个渲染tick；共用capture锁，结束恢复场景并移除临时相机。故它是按动画时间排序的离线采样，不是墙钟实时录屏。后续若编码原速视频，应按采样时序明确处理终点帧，不能用视频容器名或151帧存在声称用户已接受自然度。

现阶段真实边界测试回执：N2 `tests/five_second_entry_and_composer.xml`为41通过、0失败/跳过，`source_research/cc_output_branch_tests.xml`为12通过、0失败/跳过。这是各自源码检查点，不代替真实UE派生/播放、全回归或最终审计。旧库来源保护另见N2的`documentation_source_boundary_review_v1.json`；后续源码修改后需重新核对，不通过改写旧SHA解除保护。

N2内`documentation_initialize_v1.py`、`dispatch_worker.py`、`preflight_ue.py`、`build_samples.py`及`source_research/analyze_sources.py`属于本Run一次性文档、会话/派发或分析工具，均由本节拥有；研究报告和稀疏曲线摘要只能支持来源筛选，不能证明五秒情绪或眨眼时长。失败时保留原回执并使用新试验ID/slug恢复，避免覆盖来源或以旧成功报告掩盖新失败。

### 8.3 原速身体兼容小样

`00_engine/scripts/unreal/ue_native_face_five_second_body_probe_v1.py`（experimental）及`tests/test_native_face_five_second_body_probe_v1.py`（utility）归本节。其唯一目标是男女各一条既有Elevator Greeting身体动作与已通过的同一性别面部五秒小样组合；不改变原静态wrapper的输入许可，也不重制完整动作库。身体来源取前序成功组合报告中的原始body_animation及SHA，不取旧带表情的Composite。既有动作长度约7.0667秒，计划仅裁可播放范围前5秒，保留原帧率与原速。

root在确认当前会话后用`DM_NATIVE_FACE_FIVE_SECOND_BODY_PROBE_TASK`指定任务JSON派发。输入必须绑定成功的同一性别五秒静态面部报告、十骨/全帧检查和一致destination，四个源/输出报告路径必须互异；新报告和新`/Game/DataMake/Validation/NativeFaceFiveSecond20261008/BodyProbes`资产均禁止覆盖。任务不接受时间/速度覆写。

实现先复制原身体资产，再用`set_number_of_frames`限制可播放范围；不能仅因调用成功就认为动作保持。它按原始帧率逐帧检查0–5秒含末端全部局部骨与float曲线，轨道/曲线集合及帧率须一致，最大误差≤0.0001，并单独记录5秒末端曲线误差。保持原键，包括可播放范围外的曲线键；原Skeleton/身体/面部/参考网格SHA及非目标脏包检查通过后，才用原composer将验证过的五秒面部按0–5秒、rate=1、hold组合。头颈与非面部保护继续由原composer验证。

N2 `tests/five_second_body_probe.xml`记录18项离线测试通过、0失败/跳过；该早期检查点当时尚未取得真实UE回执。后续实际`body_probes/{female,male}_smile_probe_v1.json`、对应`smile_crop_v1.json`及`smile_composition_v1.json`均success，男女裁剪各151含端点样本的全部骨、float曲线与末端曲线误差均为0，来源保护通过；组合保护骨/面部曲线误差为0，面部骨旋转在既定阈值内。这只关闭两个Elevator Greeting加smile代表的机器范围，近景/原速视频与用户自然度仍单独判断；失败资产与报告保留，修复使用新probe_id。

N2 `available_native_sources_v1.json`保存首轮六份CC现成表演成功导出的真实时长及SHA：男Think约5.683秒，其余约32.517–41.033秒。它只证明整条素材长度，不能推导其中每种情绪都持续五秒；导入、窗口选择与自然度另行取证。后续第七份男性副本加载女性HD Emote见§8.4。N2下新增的root串行编排、离线分析、HTML审查与media输出均继续由本节拥有，默认unclassified保护，不凭文件生成替代用户接受。

### 8.4 FName大小写兼容与跨性别源候选

初始女性Gentle五秒v1组合因曲线存在性检查失败。N2 `source_curve_diagnosis_v1.json`实际记录旧Gentle与新女性HD Emote在六个时刻的raw/SOURCE枚举：每次两侧都是395项。旧Gentle的raw名为CamelCase、SOURCE返回小写，敏感字符串比较呈现395 missing/395 extra；对名称casefold后集合一致，没有实际缺失。新HD Emote两侧本已同名。该证据说明名称比较错误，不是动画数据丢失，不据此声称六时刻以外的数值/骨骼或自然度已通过。

本节拥有`ue_compose_native_face_body_v1.py`这次最小修复及`ue_native_face_five_second_body_probe_v1.py`相应调用：以FName不区分大小写的身份规则判断批准/排除/身体替换分类及SOURCE存在性，同时保留实际名称传给UE API和报告。真正缺失、未批准曲线、同一清单内仅大小写不同的冲突仍失败；不以零值填补，也不放宽骨骼或数值阈值。`00_engine/scripts/unreal/tests/test_native_face_curve_case_v1.py`为本节utility；N2 `tests/curve_case_compatibility.xml`实录74通过、0失败/跳过，属于修复后离线检查点。

旧女性Gentle失败v1报告及其隔离clone继续保留，重试使用新v2标识；未把旧失败改成成功。旧登记库的contract、entries和来源SHA不重绑，此修复的实际UE组合、渲染和身体探针结果仍需各自回执，不能由74项测试推定通过。

修复后再次只读核验见N2 `documentation_source_boundary_after_casefix_v2.json`：旧registry字节SHA不变、六个顶层sources SHA全部匹配，registry自身没有任何直接composer path/SHA绑定。该结果与修复前v1记录分开，不覆盖旧证据；检查不递归读取来源报告内容，也不代替新UE运行验收。

第七份CC导出`male_hd_emote_female_export01`在男性隔离副本上加载女性HD Emote并成功，独立UE导入见N2 `face_imports/male_hd_emote_female_full_v1.json`。`source_research/male_hd_emote_female_three_preview_tasks_v1.json`绑定男女导入SHA，比较27–32、10–15、18.7–23.7秒三个候选窗口：每窗395曲线、301含端点采样，最大绝对差为0，眨眼事件边界一致。这里只证明这三个窗口的导入曲线数值相同；男性源已单独求值/导出，骨骼姿态、实际嘴眼表现及用户自然度仍独立待测，不因文件标注Female而推断适配，也不因曲线相同代签视觉通过。

### 8.5 暂停采样晚一个样本的诊断与修复

N2 `capture_runtime_curve_diagnosis_v1.json`发现旧暂停采样画面/运行曲线对应前一个1/30秒样本：左眨眼按请求时间比较最大误差约0.826979，按time−1/30比较约0.000986，jawOpen和mouthCornerPullL同样更匹配前一个样本。该证据定位采样求值顺序问题，不表示五秒动画资产时序错误，也不外推其他实时播放入口存在同样故障。

`ue_capture_native_face_review_v1.py`本次修复与`00_engine/scripts/unreal/tests/test_native_face_capture_timing_v1.py`（utility）由本节拥有。原顺序先`override_animation_data`求值旧实例时间，再改asset/position；`set_position`本身不刷新姿态。新增统一`apply_animation_state`在设置实例、播放状态及位置后再次override，以零delta求值当前时间；采样和原场景恢复均用此顺序。每样本16渲染tick不能代替正确求值顺序。离线顺序回归`tests/capture_timing_fix.xml`实录30通过、0失败/跳过，不是实际画面通过。

已生成的旧五组采样及一个编码视频保留为时间不准确的诊断材料，不交付或提升为自然度证据；不删除，不倒写原success回执。修正版使用独立`_capture_v2`输出。N2的`validate_capture_timing.py`为本节本Run离线验证工具：逐151点检查记录位置与请求时间一致，并把三条运行时曲线与对应原生源的同一时刻键值比较；位置误差≤1e-5秒、曲线最大绝对误差≤0.005才允许编码。0.005为运行时曲线压缩留余量，不能接受原0.827级错时；它不证明所有曲线、骨骼或渲染像素相同。

每组通过后生成`temporal_alignment_v1.json`，保留capture/source指针、capture SHA与各曲线最坏帧；该组编码只取前150帧、30 FPS得到准确5秒，终点第151样本用于验证，不额外延长视频。最终八组修正版均已通过并编码，实际入口与验收边界见§8.6。

### 8.6 五秒候选技术交付与限制

本节记录技术交付当时的范围和pending状态；后续用户已保留四类当前选择，最新决定见§8.7，旧机器回执不倒写。

N2的`review.html`汇总八段修正后视频：男女分别带笑、不满、低落和待机；标签仍为候选描述，男性待机保留“眉头较紧”提示。每段来自原片中连续五秒，rate=1，无全局慢放、短片循环或只扩眨眼间隔。没有承诺本次已把旧五种情绪全部替换为五秒版；旧正式审查库保持不变，新库晋升和用户自然度接受pending。

各`captures/*_capture_v2/temporal_alignment_v1.json`实际检查151个时刻，运行时三曲线最大误差均小于0.001，位置最大误差约2.23e-7秒；这是限定曲线与时序一致性，不是所有支持组件/骨骼/像素逐帧一致性。`review_media_validation_v1.json`由FFmpeg实际解码确认八段视频每段150帧、5.0秒，HTML包含八个视频入口。原速离线编码保留表演时间，不声称实时墙钟采集或用户已观看。

`open_in_codex`打开请求只返回queued；浏览器file协议预览被工具安全策略拒绝，浏览器交互播放未执行验证。该边界不改写动画机器验证为失败，也不把结构/FFmpeg检查当成浏览器播放成功。应通过review.html或单个MP4让用户审查眨眼、嘴部自然度及情绪持续性，未经新确认不替换旧库。

N2的`technical_delivery_v1.json`汇总机器来源/组合/身体小样、修正预览与交付边界；`available_native_sources_v2.json`补齐七份CC导出与实际导入可用范围，旧v1保存当时六份来源；`diagnostic_supersession_v1.json`区分保留的旧错时采样/视频、旧Gentle失败/clone和修正后可交付媒体。上述是证据总入口，不赋予删除旧材料的权限；默认unclassified保护。

本轮必要回归的完整三目录运行见`tests/full_suite_v2.xml`：743通过、18项受Windows沙箱严格Path.resolve的WinError5影响失败。宿主精确重跑这18项见`tests/host_permission_failures_v1.xml`及`host_permission_failures_v1_summary.json`，全部18通过、无跳过，未改生产代码或降低断言；两次合计覆盖761项，不表述为单次全套761通过。初次默认临时目录失败和恢复边界保存在`tests/full_suite_sandbox_failure.json`。最终目录及文档审计单独登记，不从定向测试推断。

本节还拥有N2的`compose_samples.py`、`capture_samples.py`、`diagnose_source_curves.py`、`retain_failed_clone.py`、`run_body_probes.py`、`validate_capture_timing.py`、`encode_reviews.py`、`make_review_page.py`及后续同Run收尾工具：只服务本次root串行试验、媒体核验与文档证据，不是默认生产入口。离线HTML与媒体产物不扩充原正式面部库。

本限定技术计划已完成并归档，结项当时用户自然度与正式库晋升pending。N2的`build_technical_delivery_v1.py`和`documentation_close_v1.py`同属本节一次性清单/文档工具，原证据不覆盖。当前状态由WF-50 Status与PROJECT_STATE拥有，最终归档审计见documentation_final_audit_v2.json。

### 8.7 用户保留的当前四类选择

2026-10-08用户明确反馈：“感觉还可以，先保留这四个作为目前的选择即可”。当前选择为`idle`待机、`smile`带笑、`displeased`不满、`sad`低落；范围是所交付男女代表预览及后续默认选择集合，不推断全40角色或所有身体动作已覆盖。

N2的`human_face_selection_feedback_v1.json`保留原话，绑定technical_delivery、八段修正v2视频及对应composition SHA；`accepted_face_selection_v1.json`是当前选择权威，含男女八项：明确UE asset/package、当前saved资产文件SHA、原片asset/源窗、rate=1、duration=5、150帧30FPS视频及来源/组合/时序证据。带笑27–32秒、不满10–15秒、低落18.7–23.7秒；待机女性17.45–22.45秒、男性7–12秒。精确字段以JSON为准。

两文件均`selection_accepted=true`、`runtime_integration=false`，当前运行时未消费这份选择目录。旧五类runtime registry及其合同/条目保持，不把八个静态代表asset视为已完成全部身体动作接入；运行集成`pending_not_started`，本次未启动UE/CC。旧technical_delivery和人工pending历史回执不改写，也不把用户反馈当作工具已验证浏览器交互。

两文件由本节拥有，沿用WF-50/OUT-WF50-RUNTIME-ACCEPTANCE及N2现有unclassified保护，不新增保留决策或授权删除。`record_accepted_face_selection_v1.py`为本Run一次性只读核对与追加记录工具，不是新运行入口。本次代码未变，保留此前761项分两次验证的真实覆盖，不重复全套回归；必要目录/文档检查另记human_selection_documentation_audit_v1.json。

2026-10-09用户进一步授权运行接入，现由[Runtime §3.19](./CHARACTER_RUNTIME.md#319-四类五秒表情接入当前审查关卡)的新Run执行。上述两份接受文件的runtime_integration=false是记录当时事实，保持原字节；最新集成进度由新Run和WF-50拥有。

## 9 无道具动作库扩充

本轮四表情与无道具动作扩充已完成限定技术交付，最终入口、现场证据和限制见9.10；原计划已归档，未自动启动后续工作。9.1–9.9及各checkpoint保留各自历史时点，旧pending/失败不倒写；最新机器总入口是M3/runtime_delivery_v1.json，用户连续自然度接受仍pending。

本节拥有`00_engine/scripts/unreal/ue_motion_library_expansion_v1.py`（experimental）：在独立目标中导入单份完整CC动作并验证BodyOnly派生，不自动裁剪/重定时、不接入面板、不保存共享Skeleton或关卡。当前pilot结果见下述独立回执；脚本存在或原长导入成功不代表已完成五秒选择、视觉接受或正式入库。

本节拥有[已完成计划R01–R05](../../project_management/history/completed_plans/PLAN-2026-10-FACE-AND-MOTION-LIBRARY-EXPANSION.md)的M3=`%OUTPUT_ROOT%/unreal_character_import/motion_library_expansion_20261009_v1/`：空间检查/保留与清理决定、来源候选和筛选、五秒窗口、导出导入与派生、逐项适用范围、版本化库/审查及最终验证证据。沿用WF-50/OUT-WF50-RUNTIME-ACCEPTANCE与unclassified保护；转移遵循Motion Transfer来源和Skeleton规则并同步WF-40。R00–R05已完成限定技术范围；最终UI交付快照及文档审计见9.10。

M3/source_inventory/candidate_motions_v2.json记录28个候选（25 rlMotion、3 iMotion），只读来源/复用/导出草稿本身不算动作交付；prepare_bridge_reuse_v1.py为本节一次性离线工具。最新登记D盘空间131936124928字节（约122.9GiB）足以支持下一批小规模素材工作，R01按space_assessment_v1.json完成no_deletion，删除文件数0。此为早期候选检查点，最终筛选及五秒矩阵以9.8为准。

### 9.1 原生时长探针与观测边界

`cc_validate_body_reconstruction.py`新增diagnostic_mode=motion_library_duration_probe的本轮入口与`tests/test_cc_motion_duration_probe_v1.py`由本节维护其M3用途；原BodyFit主脚本所有权不迁移。任务限制最多30个SHA绑定rlMotion/iMotion及一个已验证CFD隔离副本，固定本Run输入/输出，一次载入载体后逐条清身体/脸片段、原生LoadFile、读取ticks换算秒数/fps/speed/loop并再清理，不导出、渲染或保存。此mode跳过可选whole-run PowerShell undo guard，不表示自动关闭未授权弹窗；单性别测时不证明男女兼容或视觉无道具。

准备与准确argv见M3/bridge_preparation/duration_probe_delivery_v1.json，旧prepared回执保存当时状态。实际`%OUTPUT_ROOT%/character_creator_bridge/artifacts/motion_library_expansion_20261009_v1/motion_duration004_probe01/motion_duration_probe.json`在一次载carrier后因props_empty要求可观测零道具失败，results=[]、sources_unchanged=true，无有效动作测时结果。最新probe02实现已取消此观测硬门槛：记录baseline及每clip前后inventory，API不可用标props_unobservable，不阻断测时，不推断无道具；22项focused tests通过，实际新探针结果仍待独立回执。该CC artifacts Run由本节拥有，默认unclassified；探针原失败原字节保留。

最新准备、源码SHA及准确任务见M3/bridge_preparation/probe02_imotion_delivery_v1.json。单FBX入口仅在M3显式allow_imotion=true时允许原格式iMotion，要求隔离副本、bytes/SHA前后锁；旧默认rlMotion行为保持。13项针对测试通过，001/002/003长iMotion任务已staged，尚不能由此宣称实际导出或原速五秒可用。测试和准备是离线边界，后续实际回执及男女身体适配仍分别判定。

### 9.2 完整原速导入与BodyOnly小样

M3/imports/motion_cand_004_male_v3.json实际success：4.266666889秒、60fps、257个含端点样本，108身体骨及10个去面部轨道后的参考回退验证误差0，源/共享Skeleton不变；eligible_for_native_five_seconds=false，不以补帧、循环或慢放冒充自然五秒。004 v1的RCT_VECTOR枚举错误和v2的optional mesh参考基准错误保留失败记录。

face_fallback_diagnosis_v1.json区分去掉轨道后共享Skeleton回退与mesh参考比例；v3用SOURCE、optional_skeletal_mesh=None下的shared Skeleton local reference检验缺失面部轨道回退，身体对照仍使用明确mesh。该基准修正与UE源码语义一致，没有放宽1e-4阈值。

M3/imports/motion_cand_032_female_v1.json实际success：10.333333015秒、60fps、621个含端点样本，108身体骨、10面部回退及保留曲线最大误差0，源文件和共享Skeleton保持，eligible_for_native_five_seconds=true。它只证明完整原速导入和BodyOnly数字验证，尚未裁选五秒、进行视觉自然度验收或进入面板/正式动作库。R02保持in_progress，R03以in_progress记录pilot阶段；生成wrapper稳定后再集中Catalog及必要全套检查。

来源优先`%ANIMATION_ROOT%`（`D:/BaiduNetdiskDownload/iclone动作`），不足再选其他本机素材。已有P0_Core_Everyday、P1_Extended_Realistic、P2_Locked_Props_Interactions、P3_Special_Stylized及_animation_pack_tier_manifest_v1.json只说明候选优先级，清单本身final_motion_approval=false；不能由目录名判定无道具、五秒可用或已批准。目标是20–30条有丰富类别、明确原片/源窗/哈希、原速五秒策略和男女适用范围的无道具动作，先筛选再验证，不以重复近似片段凑数。

初查D盘空闲133713874944字节（约124.5GiB），足以先做有限表情集成，后续空间按实测需求决定。用户已授权自主低风险清理；执行前仍需列明现用来源、接受证据、重建能力与精确候选路径，并记录前后空间和实际结果。未知归属和现用资产保持；不为达到删除数量而清理，不把来源优先级当保留决定。基础库完成后可选探索带道具动作，须单列依赖与验证，未做不阻塞当前计划结项。总Catalog/Inventory及文档审计在最终实现稳定后一次收尾，执行中不提前宣告通过。

### 9.3 原生长候选与五秒组合检查点

motion_duration25_probe02实际success，25源中17个原生时长≥5秒；历史同源SHA的001/002/003 iMotion另有13.9333/15.35/12.35秒证据，合计20。motion_duration_gap3_probe01实际success，034为5.15秒、035为34秒、036为15秒，补到23个长源、计划男女46变体。此为时长合格候选，不是23动作已逐项无道具视觉通过；探针记录的Shadow Catcher保持不变不证明动作手部/交互依赖不存在。短004继续排除原生五秒目标。

M3/cc_batch_exports/export_batch01已实际运行，冻结检查点时status=waiting_terminal、selected_job_count=46；root串行独占CC。001女性及032男女原长导入通过，032男女各五秒body window与四类表情共10份report在检查点均success。生成由`ue_motion_library_face_pilot_v1.py`（experimental）限定本Run，复用不修改N3生成器，禁止短片循环/补帧/整体缩放；原表情选择及旧库不覆盖。全批导出导入、逐动作五秒/面部矩阵及新面板运行仍未通过，不能由032外推。

dance_pilot_visual_v1.json仅记录root实际看过女性032 BodyOnly与smile各0/1/2/3/4/5秒两组contact及smile中段原图：所见样本身体持续变化，衣发装配保持，加入smile后身体姿态对应，未见明显断肢/脱离或手持依赖。不是连续自然度、每帧穿模、男性/全部动作/全40用户接受；human_acceptance=pending、library_published=false。后续视觉必须另有真实检查记录，本节维护者不替root签视觉结论。

本节拥有M3内run_cc_motion_exports_v1.py、run_ue_motion_matrix_v1.py、execute_032_matrix_pilot.py、prepare_import_task.py、prepare_male_dance_pilot.py、capture_full_body_review.py、make_capture_contact.py、record_dance_pilot_visual.py、diagnose_face_fallback.py及documentation_record_checkpoint_v1.py等本Run串行编排/截图/证据工具，继承M3输出所有权，不逐个晋升主目录生产脚本。动态progress的路径和读取时SHA随检查点保存，后续变化不能倒写成当时全批完成。

### 9.4 独立动作扩充审查入口（实现检查点，未发布）

本节拥有`motion_library_extension_contract_v1.py`、`motion_library_review_adapter_v1.py`、`run_cfd40_motion_extension_review_v1.py`、`ue_cfd40_motion_extension_review_v1.py`、`build_motion_extension_review_v1.py`（均experimental），以及`tests/test_motion_library_extension_v1.py`、`tests/test_motion_library_expansion_v1.py`、`tests/test_motion_library_face_pilot_v1.py`（utility）。详细调用和字段见M3/panel_extension_implementation_v1.txt；新入口只显式消费新motion catalog/face overlay，不改旧N3源码、48项registry或指针，不自动创建关卡。

新motion条目男女必须绑定同一原源SHA和各自真实export/import/body-only证据，索引从6连续添加，旧1–5保持。每个新动作男女四表情完整8项矩阵与实际男女代表visual缺一则拒绝face overlay构建；一次保存新版本，不覆盖pilot文件或伪造接受。新配置使用cfd40_motion_extension_configuration_v1，旧配置仅在衣柜/身份/色板/来源锁匹配、旧action 0–5及精确N3表情SHA下显式迁移。未出版/激活前，原四表情界面仍有效；临时新pilot与旧面板共享current_case，root须先快照并恢复基线后再回旧入口。

缓存限进程内一份、绑定准确新manifest SHA，初次完整验证与哈希已追踪依赖，后续逐项比较resolved path/size/mtime_ns/ctime_ns，变化或缺失清空并重验；不修改全局旧模块，也不把持久缓存当接受。该优化信任本地文件不受内容与时间戳协同伪造；旧五动作/N3的性能测量不能外推未来23动作UI延迟。26项新runtime离线测试是实现检查点，真实UE新worker、完整选择/暂停重播/保存恢复/身份衣发及镜头根位移仍待；旧UI成功不替代新入口通过。

### 9.5 实现检查点回归与文档核验

M3/tests/full_regression_host_v1.xml/.log/_summary.json记录本次宿主一次执行907 passed、0失败/错误/跳过、407.03秒：documentation/dataset/unreal三个完整测试目录，加本轮CC duration与iMotion两组测试。使用仓库外独立D:/UE/tmp临时目录，避免旧默认Temp权限与假仓库嵌套问题；full_regression_sources_v1.json绑定源码开始SHA，结束对比source_changes_during_run=[]。这是本轮稳定实现离线验证，不代替CC全批终态、全部动作视觉、实际扩充UI或用户接受。

该实现检查点Script Catalog登记669脚本，Output Inventory登记145范围；本次文档完整审计回执为M3/documentation_implementation_audit_v1.json。它只核验documentation_implementation_checkpoint_v1.json所记录的进行中范围，后续批量进展另行同步，R02–R05不因本检查点而全部完成。

### 9.6 单对扩充入口实际运行与许可排除检查点

M3/panel_pilot032/runtime_smoke01/summary.json实际success=true、sources_unchanged=true，13个运行事件及独立恢复报告SHA已核对。032新增动作的none保持原长BodyOnly，五秒sad的暂停/续播/末帧保持/重播、整套配置扰动恢复、身份切换和旧配置离线精确迁移通过；时序探针限已加载组件，完整请求约17–31秒，不夸称即时UI响应。原基线已重新装配恢复，current_case随后按备份原字节恢复；不能以当前仍在变化的current_case文件冒充这次恢复时间点。该smoke未保存/重载关卡、未创建新窗口，新增UI尚未向用户发布，不等于全20余动作或全40接受。

panel_pilot032/root_visual_v1.json记录root真实查看男女032带笑各0–5秒六帧联图及女性中段原图，女性BodyOnly六帧参考也已看；所见衣发跟随保持、身体样本变化正常。其余六表情组合只有数值证据，不写成全八组均视觉看过；不代表连续播放自然度/每帧穿模/所有身份服装或用户接受。pilot motion_catalog_v1.json和face_overlay_v1.json仅供显式隔离小样调用，旧N3默认四表情库与指针保持。

M3/export_exclusions_v3.json绑定014/015/016各真实失败terminal、request与fatal_dialog SHA，按原源SHA排除各自计划两性；失败原因记license_unavailable，不推断未购买或其他账户状态，不绕过、不伪写成功。旧v1/v2决策与失败保留。剩余可执行目标不能由原23源/46变体数直接说成全部完成；cc_batch_exports/batch04与UE串行矩阵仍在root执行，v2检查点读取状态分别waiting_terminal和executing。

本节新增拥有`00_engine/scripts/unreal/run_motion_extension_pilot_smoke_v1.py`（experimental）及M3内prepare_license_exclusion_v1.py、prepare_visual_task_list_v1.py、execute_available_matrix_batch_v1.py、documentation_record_runtime_checkpoint_v2.py与对应输出内测试。前三个Run工具分别准备严格失败证据排除、真实视觉待办和已有有效导出的串行矩阵调度；准备不代表执行/查看通过，不将输出内工具升为生产入口。此前907项源码回归仍是有效历史检查点，本次不重复全跑，也不声称新输出工具自动纳入该907覆盖；本次目录与文档审计另记documentation_runtime_audit_v2.json。

### 9.7 最终输入准备、动作全景与稳定代码回归

本节新增拥有`00_engine/scripts/unreal/prepare_motion_extension_inputs_v1.py`、`motion_library_panorama_v1.py`、`run_motion_extension_final_smoke_v1.py`（experimental）和`tests/test_prepare_motion_extension_inputs_v1.py`、`tests/test_motion_library_panorama_v1.py`（utility）。输入准备只消费root明确审看的具名候选及来源/视觉SHA，生成新motion/face构建输入；不自动发布registry、改默认指针或创建UI。最终smoke helper只在精确目标和已验证旧基线下串行运行，不保存关卡或开窗口；远程结果未知时停止，不抢在既有job前重复调用。最终catalog/overlay此检查点尚未建立或激活，R03/R04保持in_progress，human acceptance pending。

动作全景实现详情见M3/panorama_review_implementation_v1.txt：固定camera x=1600cm、z=100cm、FOV35，保留原动作root位移，不自动追踪或锁根。专属临时辅光强度10、无阴影；专属临时延伸地板只复用原DM_CCWH_Floor已加载mesh和实际材质，按实测bounds保持厚度、水平覆盖原中心±2000cm，顶面低0.25cm，无碰撞/投影。原灯、原地板、材质和源动作不改；非全景/关闭时隐藏，事务失败仅移除新拥有助手或恢复其旧状态，拒绝同名外来对象。保存后重载的同步检查可重建临时助手，后续Slate回调只读，不在回调中加载资产。

当前全景证据仅离线验证和008独立capture：travel_review_v2_motion_cand_008_female_bodyonly等报告/截图及root观察说明见panorama实现说明，强度10的女性六帧在4–5秒仍可看见全身；这不等于最终UI内辅光/延伸地板/切回普通视角/配置恢复的现场验证。临时延伸地板实际bounds、绑定和视觉仍须新worker读回及root现场检查。固定宽镜头只覆盖所验时窗，不保证无表情原长循环动作全程不出画，也不授权裁改或冻结root运动。

本次一次宿主回归M3/tests/full_regression_host_v2.xml/.log/_summary.json为930 passed、0失败/错误/跳过、170.85秒：三个完整目录895项＋两组CC motion测试35项。仓库外独立临时目录；full_regression_sources_v2.json和full_regression_sources_after_v2.json绑定361份源码，运行前后无变化/新增。源码pin只证明字节一致，不证明每份输出工具有专属测试。此后新增reconcile_matrix_batch06_v1.py和execute_available_matrix_quiet_v1.py未包含于930回归；reconcile已有实际UE只读核验成功回执matrix_batch06_connection_reconciliation_v1.json，记录PID、summary及三个活动flag=false；quiet已通过语法检查并用于仍在运行的batch07，批次终态以运行回执为准，不能继承930测试结果。本次文档维护不重跑完整测试，catalog映射维护也不改变该运行时源码检查点的历史事实。

本节统一拥有M3内本轮新增build_export_delivery_v1.py、capture_travel_review_v1.py/v2.py、probe_travel_lighting_v1.py、run_visual_captures_serial_v1.py、execute_available_matrix_batch36_v1.py、prepare_panel_pilot032.py、record_initial_body_visual_v1.py、record_panel_pilot_visual.py，以及上述连接核对/安静输出工具。batch06远程JSON截断只经matrix_batch06_connection_reconciliation_v1.json只读核实已有UE终态/无活动job，不重复导入；quiet工具将Python完整输出记本地日志，底层runner不改。以上均继承M3输出owner/unclassified，不晋升生产入口；动态操作/视觉数量由原回执拥有，不在多处复制。CC完整导出数量与排除闭包只引用export_delivery_v1.json，不能当作UE矩阵、最终UI或用户验收完成。


### 9.8 最终筛选、矩阵和目录构建（现场交付待验）

M3/final_accepted_candidates_v1.json（SHA 0ec028754431104ed7eec3497c9a5d5c91f1e99f72f38ce2cc8a5593c750f33d）聚合root实际查看的20个入选来源、男女代表及九份视觉依据；每条身体按六个离散时刻审看，最后034/035/036见root_body_visual_eighth_v1.json。其travel采样已按visual_serial_runs/visual_20261008T223143_be156429/summary.json成功完成并恢复。此接受仅为accepted_for_panel，不替代用户连续自然度接受，不覆盖全40身份/全部衣服或逐帧穿模。034是站立到起跑，不能称持续五秒匀速跑；009按实际摆姿、008按所选五秒前向步行理解，20个来源不等于20种完全互斥语义。goal_source_space_evidence_v1.json绑定来源优先盘点、选源SHA、空间及no_deletion闭包；未选文件不宣称全部逐项哈希或视觉验收。

UE末批ue_serial_runs/run_20261008T220450_af2fcc24/summary.json实际complete_available_work，35个新增步骤成功；前序有效结果按源锁核验复用，许可排除仍依export_exclusions_v3.json。R03的入选男女原长导入、原速五秒身体窗口与四表情矩阵技术证据已齐，final_inputs_v1/preparation_receipt_v1.json与构建输入绑定20对/160个新增组合。新动作不借短片循环、冻结或慢放达到五秒；源保护与Skeleton检查以各import/body/composition原回执为准。root_visual_four_face_pairs_v1.json仅007待机、019低落、020不满、032带笑的男女八个代表，不把数字矩阵写成160组合均已视觉看过。

final_motion_catalog_v1.json（SHA 57822926ac22bda69c8f89da2cf0559cefb725b90b73d30a6c93b23b9b94f1fd）含20个新增男女动作对，原五对通过base来源保留；final_face_overlay_v1.json（SHA d22c634e44d1cba5a41ebf820c0db05673c8fb798126831c61b94db295222ecd）文件含160个新增项。预期运行时与N3旧48项合并为208项，当前尚无最终运行读回，不将预期计数当实际加载结果。selection_review_notes_v3.json提供兼容schema的观察备注，user_review_guide_v1.md提供新入口指南；文件生成不等于UI已发布。构建时检查点尚待现场验证；后续smoke01在全景步骤实际失败，修复后的smoke02结果见9.9。最终截图审看与可见新UI仍待，R04/R05保持in_progress，计划不归档。

本节继续拥有M3内assemble_final_acceptance_v1.py、capture_panorama_final_probe_v1.py、reload_final_review_modules_v1.py、open_final_motion_review_v1.ps1等本Run离线汇总/外部串行入口及其输出，沿用现有unclassified保护。930回归后新增辅助工具不纳入既有930覆盖，实际执行结果按各回执单列；quiet的batch07及后续批次结果以终态summary为准。此次只更新已证实的R02/R03和构建事实，等待最终UI证据后统一Catalog/Inventory与文档审计，不追加完整测试。


### 9.9 全景临时对象枚举修复与最终现场smoke

final_panel_smoke01的显示、播放、暂停通过，04全景步骤失败。panorama_runtime_diagnostic_v1.json及panorama_orphan_inventory_v1.json确认普通EditorActorSubsystem.get_all_level_actors遗漏RF_Transient助手，导致读回误判及旧回滚找不到自有对象，现场出现两灯、两地板。root按四个精确路径及label/tag清理，panorama_orphan_cleanup_v1.json实际success，未保存资产或地图；原失败、诊断与panorama_failure_baseline_restored_v1.json真实基线恢复证据保留。

motion_library_panorama_v1.py最小修复通过UnrealEditorSubsystem.get_editor_world取得当前编辑器world，再用GameplayStatics.get_all_actors_of_class(world, Actor)枚举，读回与回滚共同使用，继续执行专有label/tag及碰撞防护，不扩大删除范围。14项针对性测试通过；随后因生产源码实际变化，独立宿主全回归full_regression_host_v3.xml/.log/_summary.json为932 passed、0失败/错误/跳过，三个完整目录897项加CC两组35项，pytest299.83秒（JUnit299.799秒）。371份源码pin运行前后无变化/新增，证据full_regression_sources_v3.json及full_regression_sources_after_v3.json；930结果保留为修复前历史，不将源码pin等同每份工具专属测试覆盖。

final_panel_smoke02/summary.json实际success=true、sources_unchanged=true、unknown_remote_outcome=false：七个事件覆盖新动作对显示/播放/暂停、全景辅光与延伸地板正确读回、普通视角隐藏助手、配置保存恢复及最终隐藏助手。独立恢复成功，原baseline重建且current_case备份字节恢复；新目录、N3基础库/指针及已保存地图SHA前后不变。范围为一个新增动作对的运行行为，首次show约195秒、其余操作约21秒，不承诺即时响应，不代签所有动作/身份现场逐项点击。该smoke没有保存/重载地图、没有创建窗口，human acceptance仍pending。

剩余交付是由同一已验证endpoint显示最终全景、检查五秒截图并恢复，再开启新UI取得ready/可见回执；上述动作完成前R04仍in_progress，R05最终Catalog/Inventory及文档审计继续等待。M3内diagnose/cleanup/final panorama/baseline恢复工具均继承本节既有输出owner与unclassified保护，实际执行证据单列，不因清理临时助手推断删除其他输出或修复全部场景故障。


### 9.10 最终可见界面交付与结项范围

M3/runtime_delivery_v1.json（SHA 17ce830ca59be1dd8676f71ddff7e1b694dbedcd58c1e18fa0b2a2a66f7a9e44）绑定18份交付引用，本次核对全部SHA一致。最终目录提供20个新增男女动作对并保留原5对，共25对；新增160个表情组合与N3原48项键互不重叠，worker实际合并208项。四类选择为待机、带笑、不满、低落及关闭；新动作带表情使用原速五秒body窗口，关闭表情使用保留的原长BodyOnly，不能把两种时长政策混为一谈。

final_panel_smoke02验证范围见9.9。最终五秒画面由captures/final_panorama_scene_pair_5s_v1/capture_report.json实际success及全部cleanup=true证明，两身体position=5；root_final_panorama_visual_v1.json记录root真实查看并通过，final_capture_baseline_restored_v1.json证明真实基线恢复。旧Automation截图90秒未终态，晚到PNG为站立画面，明确拒绝作为五秒证据；late_screenshot_terminal_evidence_v1.json绑定唯一完整PNG、后续UE只读检查和单次ticker/reset核对，旧失败原报告保留，由SceneCapture成功证据替代本次五秒视觉判断。该代表截图不证明连续播放自然度或所有动作全程不出镜。

旧面板22544经正常CloseMainWindow关闭并退出；此前非宿主进程查询误判不作为关闭证据。新面板21168的panel/final_panel_lifecycle.json为ready/error=null，panel/final_window_state_v1.json记录实际可见MainWindowHandle与标题，panel/final_current_case.json的初始show成功并匹配最终motion/face pins。原character_ids、choices、appearance保持，交付时action_index=0、paused=true；窗口/PID只是交付快照，不承诺永久存活。关卡仍是L_DM_CFDNativeBatch40_ModularReview_v001，已保存地图及受保护源不变。

用户指南：[动作与表情审查指南](../../../../../../00_engine/outputs/unreal_character_import/motion_library_expansion_20261009_v1/user_review_guide_v1.md)。显式重开入口为M3/open_final_motion_review_v1.ps1及final_review_operator_commands_v1.txt，消费final_motion_catalog_v1.json和final_face_overlay_v1.json；重新连接前须核对当前项目/进程/UE节点，多实例不能自动猜。打开面板本身不自动切换错误关卡。旧N3默认入口和48项证据、032 pilot文件均保留，不能用旧入口推出已加载本次扩充。

来源优先本机下载目录，最终16个选源来自该目录、4个来自已安装模板，精确来源/许可排除及SHA仍以export_delivery和goal_source_space_evidence为准；最后D盘可用125846700032字节（约117.2GiB），未删除文件，未添加依赖道具的动作。034仍仅站立到起跑，009摆姿、008前向步行等语义按实际窗口记录；内部原型来源不代表已取得发布或训练权。带道具探索deferred，不是本计划硬性门槛，也不自动继续。

932项修复后回归及371源码pin范围见9.9；之后新增M3截图/恢复/交付汇总工具按真实运行回执单列，不冒称均有专属测试。本节统一拥有本Run的show_final_panorama_v1、SceneCapture、late screenshot终态核对、baseline恢复、runtime delivery构建与文档收尾工具及产物，沿用既有OUT-WF50-RUNTIME-ACCEPTANCE/unclassified保护。Catalog与Output Inventory集中重建，最终16个独立子系统及跨层结果见M3/documentation_final_audit_v2.json，不重复全套测试。

计划技术完成并归档，PROJECT_STATE显式idle_after_completed_plan/current_plan_id=null；用户连续自然度、全40身份、所有穿搭/每帧穿模及未实测组合的人类接受仍pending，不把root抽样观察变成用户代签。runtime_delivery内documentation_closure=pending是交付当时历史字段，保持原文件，文档闭环由独立最终审计回执补齐。


## 10 完整动作循环审查

2026-10-09用户确认原代表实测五秒后，授权审查时播放完整身体动作并持续循环，现有五秒脸可以重复。限定技术交付现已完成，人工连续自然度与全部组合接受仍待用户审查。本节拥有L1=`%OUTPUT_ROOT%/unreal_character_import/full_motion_loop_review_20261009_v1/`，沿用WF-50、OUT-WF50-RUNTIME-ACCEPTANCE、VAL-UE-01/02，默认unclassified保护；不新增保留或删除决定。旧五秒资产、M3目录与交付回执保留，不改变生产五秒窗口。

### 10.1 实现、输入与播放政策

本节拥有`run_cfd40_full_motion_loop_review_v1.py`、`ue_cfd40_full_motion_loop_review_endpoint_v1.py`、`ue_cfd40_full_motion_loop_v1.py`（experimental），以及`tests/test_cfd40_full_motion_loop_v1.py`、`tests/test_full_motion_loop_controller_v1.py`（utility）。前者包装原审查控制器，中间入口校验目标并调用隔离worker，后者选择完整BodyOnly、已接受脸及参考mesh/shared Skeleton并按需生成。复用M3/final_motion_catalog_v1.json和final_face_overlay_v1.json，不改原目录/默认指针；已接受脸仍由N2/accepted_face_selection_v1.json约束。

播放政策`full_body_original_speed_face_five_second_repeat_v1`：身体按完整原时长、rate=1循环；脸在每个身体周期内按原速五秒重复，身体回起点时脸也回起点。脸不跨身体周期维持独立相位；源首尾可能不同，不承诺无缝，不把循环自动升级为生产动作接受。关闭脸时使用原长身体；身体静止且脸开启时保留五秒脸循环；二者关闭则静止。

只为当前选择的性别/动作/表情组合派生，保存于`/Game/DataMake/Validation/FullMotionLoopReview20261009/Composites/`，不预生成所有组合。缓存spec包含来源asset/SHA、接受selection、政策、fps/frame count/duration及相关实现SHA；逐次检查receipt、composition report、asset及所有来源哈希，拒绝dirty输入和不完整旧生成，避免把旧五秒证据直接当成完整片通过。`cache/`、`compositions/`、请求/读回、现场观测、配置、面板和交付报告均属于L1运行证据；其域结构与SHA绑定由实际JSON拥有。

### 10.2 入口、配置与恢复

环境为现有UE5.8编辑器、datatry_02项目及原CFD40_ModularReview关卡；先核对当前项目/PID/UE节点，禁止多实例猜测。关闭旧审查窗口后，从已核对节点显式打开：

```powershell
& "$env:LANCE_ROOT/00_engine/outputs/unreal_character_import/full_motion_loop_review_20261009_v1/open_full_motion_loop_review_v1.ps1" -NodeId <verified_current_UE_node_id>
```

`%LANCE_ROOT%`的机器映射见PATH_ALIASES；若环境变量未设置，应先按该映射设置。launcher消费M3最终motion/face目录，启动新窗口“CFD40 · 完整动作循环审查”；窗口启动不代表ready，交付以L1/delivery_v1.json及绑定面板证据为准。重启UE后不得沿用旧node。首次新组合需要生成及全帧检查，后续复用已验证cache。简短使用说明见[完整动作循环审查指南](../../../../../../00_engine/outputs/unreal_character_import/full_motion_loop_review_20261009_v1/user_review_guide_v1.md)。

新配置schema=`cfd40_full_motion_loop_configuration_v1`，附review_playback_policy；保存前核验运行读回，恢复时验证content哈希、来源闭包、level/palette及政策。新UI可显式读取兼容旧配置并按本模式恢复，不倒写旧配置。来源变化、dirty源或不完整生成时停止并保留报告，先核实失败/未知远程终态，再考虑重试；不得删掉失败记录直接生成。停止循环和恢复原审查属于root串行操作，不重启UE/CC掩盖异常。源素材和原五秒入口保持可回退。

### 10.3 已验证范围与交付

show_result_v1.json及两份composition报告证明007“四周张望”男女原长15.066666603秒，带笑组合各905个含端点帧，身体骨差及脸曲线差均0，来源保持。native_cycles_v1.json通过墙钟与native动画position观测，不手动推进时间：两性别均跨完整片尾两次且playing=true，wall约15.703/30.758秒；中间主动暂停约0.6134秒，位置7.016561秒完全保持，随后继续。报告结束恢复静止0秒。该测量证明代表完整周期重复，不能表述为所有动作都已逐条实测。

smoke_summary_v1.json八事件实际全部通过：缓存显示、两完整周期与暂停继续、控制器播放/暂停、女性身份替换、关闭脸回原15秒身体、静态五秒脸、配置恢复原角色/穿搭/发型/颜色/表情/index9。没有保存关卡或重载地图；衣服保持/配置恢复不等同本次重新验证全部穿搭几何。交付UI的ready、实际可见及保护证据统一由delivery_v1.json拥有，PID仅是交付快照，不保证窗口永久存在。

本轮三个完整目录documentation/dataset/unreal回归见regression_v1.xml：916通过，0失败/错误/跳过，JUnit448.752秒（pytest448.78秒）；没有改CC实现，未把前轮额外35项CC测试混加到本次计数。新实现针对19项通过是前置检查，不与916重复累加。最终Catalog/Output Inventory及16独立子系统/跨层审计见documentation_final_audit_v1.json，原932是上一轮不同测试范围的历史结果。

本节统一拥有L1内dispatch_review_v1.py、observe_native_cycles_v1.py、runtime_smoke_v1.py、open_full_motion_loop_review_v1.ps1及本轮后续保护/面板/交付/文档工具，它们是root串行运行辅助，不是默认生产入口。计划R01–R03完成并归档；用户自然度、原片接缝、全40身份/所有穿搭/全部动作全长可见范围仍pending，不自动开展新动作、道具、场景或生产。

### 2026-10-12 旧一次性脚本退役

旧第一批动作/粗糙表情的单次执行和审查脚本已清理，精确列表见 `%OUTPUT_ROOT%/workspace_cleanup_20261012_v1/batch06_retired_scripts.json`。本页相关早期步骤仅为历史，不再作为当前命令；当前角色使用CFD40模块化入口及四类原速表情。旧字节证据不改写为新验收，现用脚本和配置按当前Registry读取。
