# CFD40 新版候选：完整转移、附属睫毛与批量准备

> 文档 ID：`TECH-TRANSFER-CFD40-REFRESH-20261018`
> 文档类型：`technical`
> 生命周期：`current`
> 适用阶段：`WF-40`；附属候选审查影响 `WF-50`
> 实现所有权：本run私有 manifest compiler、完整导出准备、单人共享骨架导入、附属睫毛 adapter、离线批量准备
> 验证所有权：实现检查服务 `VAL-TRANSFER-01`；离线单测不替代真实 Gate
> 输出契约：`OUT-WF40-TRANSFER-BUNDLE` 的本run候选实现；未正式晋升
> 运行环境：系统 Python；仅 root 显式执行既有 CC Bridge/UE Editor，AutoSetup 沿现管线
> 最近核验：2026-10-19（用户修改后两人导入及完整面板接入完成，待用户视觉/点位审查）

## 1. 所有权与边界

### 2026-10-19 用户修改后重新导入补充

2026-10-20 夜间延续：用户已批准剩余角色导入，并允许UE在内存或崩溃问题后恢复。独立Run `user_edited_night_import_20261020_v1/`沿用同一版本UE根及既有共享Skeleton；本Technical拥有其`prepare_manifests.py`、`import_night.py`、`controller.py`、`aggregate_delivery.py`、`final_ue_check.py`、`publish_handoff.py`和队列/逐人回执/进度/终态证据。离线准备只复用`cc_extract_complete_fbx_source_v1`提取真实FBX，按每人真实部件保留全部睫毛，不硬编码8件。当前`editable_source`与新FBX/JSON分别绑定SHA，旧清理前准备不作为本轮证明。

`controller.py --limit N`持有独占controller.lock，逐人精确远程目标调用、保存成功后再继续；没有自动重试或启动应用功能。根会话负责实例重绑和必要恢复，独立CU协助者只确认两种导入弹窗。STOP文件仅在角色之间阻止新提交；不能将已创建STOP当作运行中的UE任务已停止。`progress.json`中ue_released保持false直到实际导入/保存/协助任务均结束，最终交接外部取证后才可置true。

内存处理只在单人完成后Python/UE GC；遇到实测构建内存提示，后续分离导入在调用期间临时把`Editor.AsyncSkinnedAssetCompilationMaxConcurrency`设1，finally恢复原值并读回。名称/语义核对本机UE源`Runtime/Engine/Private/AsyncCompilationHelpers.cpp`及`SkinnedAssetCompiler.cpp`，不写入工程配置，不改变网格/Morph质量。若UE崩溃导致finally未执行，原会话设置随进程结束，恢复实例重新核验目标。

夜间范围只含角色导入与文档，审查面板、场景、相机、光照均不在本会话范围。`final_ue_check.py`是最后一个有条件保存本轮dirty导入目录的UE调用，其他dirty包仅记录；`aggregate_delivery.py`只聚合逐人真实审计及磁盘网格存在/大小，不操作UE。最终人工画面/动作/试穿仍不由此自动接受。精确完成/失败/剩余与释放证据只读现有交接及本Run终态，不由控制器退出码单独推断。

10月20日夜间终态已交付：本Run `delivery.json`聚合白天两人和夜间逐人实际回执，`release_verification.json`、`ue_final_state.json`、`process_snapshot.json`证明任务停止与UE释放，`script_pins.json`绑定本次实现。BF001一次D3D12设备故障的失败日志保留在其`gpu_failure_attempt01/`；恢复配置只将该人最终分离网格指向`MeshesRecovery01`，不可用旧中断的`Meshes`替代。导入期间临时D3D11参数及安全重启见`recovery_record.json`/`restart_events.json`，交接前已恢复默认D3D12。所有后续装配须读取delivery的真实Object Path，不按文件夹规律猜测。相关输出仍为本Technical拥有的候选转移证据，不触发正式注册、视觉接受或清理授权。

本轮文档同步证据`documentation_pair_sync_20261019_v1.json`归本Technical拥有，仅核验当前来源、计划/状态、版本边界及相关入口链接，不等于全树审计或运行时Gate。

面板最终ready、重载读回与19项定向测试的已落盘入口为Runtime §3.22所列`panel_delivery.json`、`final_ready.json`和`targeted_tests.json`，不改变本导入证据的版本范围。

10月19日白天检查点：导入后的完整场景点位面板已接入，仅人物菜单限制新版CFD40_AF_001/CFD40_AM_001，换装、发型、十发色、表情、动作、镜头、主场景与点位保存均保留。运行时结果及后续恢复由[Runtime §3.22](../unreal/CHARACTER_RUNTIME.md#322-用户修改后双人完整场景点位审查2026-10-19限定接入完成)和`pair_scene_review_20261019_v1/integration_summary.json`拥有；本Technical仍拥有导入来源与实际部件边界。该白天检查点余38人尚未提交；10月20日夜间实际完成情况以上述独立Run终态及当前交接为准。精细近景/全帧表情/全组合接受不由导入完成自动晋升。

本轮实际来源已换成用户手动修改后的统一CC项目及新完整导出，清理前的RUN40清单/源SHA/已删除CC诊断不能继续作为当前源证据。当前交接入口为[CURRENT_IMPORT_HANDOFF_20261019.md](../../../../../../00_engine/outputs/character_refresh_20261018_v1/CURRENT_IMPORT_HANDOFF_20261019.md)，白天两人资产由同根`user_edited_pair_import_20261019_v1/delivery.json`拥有，夜间汇总由`user_edited_night_import_20261020_v1/delivery.json`拥有。历史段落的计数与强制旧coordinator仅适用于原装配版本。

本Technical拥有新Run `user_edited_pair_import_20261019_v1/`中的实验性`run_import.py`（精确UE目标派发）、`import_pair.py`（原完整导入核心组合与四Normal保存读回）、`finish_handoff.py`（仅完成证据聚合和交接记录），以及逐人manifest、source_extract、worker_status、import_audit、remote结果。输出继续归OUT-WF40-TRANSFER-BUNDLE候选证据、unclassified保护；不晋升正式生产入口。

导入复用`ue_import_complete_character_skeleton_pilot_v1.py`，以新FBX实际部件/Morph和文件SHA绑定输入；AutoSetup HQ合并材质参考与Interchange分离网格两阶段执行，后者使用既有同性共享Skeleton。新根`/Game/DataMake/Characters/Revisions/CFD40_20261019_v1`避免旧资产跳过。四块皮肤Normal沿前序设置FlipGreen=True、sRGB=False、Normalmap压缩，并保存读回；源118骨、各网格源Morph名称、父层级与共享参考姿势由原核心审计。本轮没有复做已清理的CC逐像素/原生顶点证据，不以旧回执代替新验证。

系统调用为`python -X utf8 <Run>/run_import.py CFD40_AF_001`或`CFD40_AM_001`；仅允许两人，依次串行，必要时确认AutoSetup与FBX弹窗。材质参考阶段关闭Morph/独立Skeleton是两阶段设计，最终`Meshes/`必须完整Morph且绑定共享Skeleton。`MaterialWitnessInteractive/`保留被引用材质/纹理，不能将整目录当临时垃圾删除。两个进程成功退出后运行`finish_handoff.py`验证最终回执与网格文件再记录完成。

导入阶段原交接仅包含技术检查；后续两人完整面板接入和代表运行时检查已由Runtime §3.22承接，未修改正式注册或获得全组合/人工视觉接受。夜间剩余导入需从新sources.json和导出结果生成余38人绑定、重新核实UE实例，再沿同一核心执行；不能直接恢复旧RUN40或将两人范围入口擅自作为40人调度器。具体队列、暂停边界和面板接入说明只由上述交接及delivery拥有。

本文拥有下列本run脚本的组合方式、命令、回执字段与恢复；不修改原 CFD40 身份、共享 Skeleton、生产 registry、正式固定38组件或源工程。当前接受范围以 [项目状态](../../project_management/status/PROJECT_STATUS.md) 和独立实际执行回执为准，本文的离线验证不能打开 [WF-40 Gate](../../workflow/WF-40-CC-UE-TRANSFER.md)。

Run Root 为 `%LANCE_ROOT%/00_engine/outputs/character_refresh_20261018_v1/`。以下文件名均位于该根，脚本精确仓库路径分别是：

| 仓库路径 | 职责 |
|---|---|
| `00_engine/outputs/character_refresh_20261018_v1/compile_transfer_manifest_v1.py` | 原 source40＋实际 formal catalog＋可选真实完成回执编译候选清单，保存原/当前pins |
| `00_engine/outputs/character_refresh_20261018_v1/cc_refresh_complete_export_v1.py` | 复用旧 batch40 完整导出准备/回执 inventory；仅 prepare/status |
| `00_engine/outputs/character_refresh_20261018_v1/ue_refresh_representative_import_v1.py` | 精确 UE 实例、单人候选导入、当前男女共享 Skeleton 保护、实测新增睫毛片→FBX 核验 |
| `00_engine/outputs/character_refresh_20261018_v1/ue_refresh_eyelash_followers_v1.py` | 私有 transient SkeletalMeshActor 附属睫毛；Body pose/Morph/显隐/销毁，主体38组件不变 |
| `00_engine/outputs/character_refresh_20261018_v1/refresh_batch_prepare_v1.py` | 原40人原始pins/候选seed/逐人记录与代表gate；无应用执行器或发布能力 |
| `00_engine/outputs/character_refresh_20261018_v1/ue_refresh_runtime_review_v1.py` | 实验性候选审查接线：formal catalog＋真实导入六件path overlay、generic apply_actor及私有lash adapter；仅新候选关卡，实际待root导入后验证 |
| `00_engine/outputs/character_refresh_20261018_v1/ue_refresh_eye_animation_probe_v1.py` | 候选眼部动画诊断：复制现同sex静态idle到独立验证root，保护118骨与共享Skeleton，只用动画曲线驱动眨眼/单眼端点，实际由root另择时验证 |
| `00_engine/scripts/character_creator/cc_probe_refresh_skin_material_readonly_v1.py` | 当前已加载male最终源的只读通道诊断，复用像素捕获并分别读取Normal/Bump/Roughness/Shininess/AO；不Load/Save场景/Apply，shaderImage只先列实际SDK API/docs |
| `00_engine/scripts/character_creator/cc_probe_refresh_pbr_export_ab_v1.py` | 同一实际male源与原full export route的私有A/B，仅B在真实native setting加入已测PBR format-directory flag；新目录不覆盖旧源/导出/资产 |
| `00_engine/outputs/character_refresh_20261018_v1/ue_refresh_eyelash_followers_v2.py` | 沿原adapter门的独立v2入口，精确v2 mapping/根/候选关卡，保留旧v1文件与回执 |
| `00_engine/outputs/character_refresh_20261018_v1/ue_refresh_runtime_review_v2.py` | 独立v2运行时审查入口，原pipeline组合、私有none修复/装配cache，真实v2画面待root |

对应测试所有权：`test_compile_transfer_manifest_v1.py`、`test_cc_refresh_complete_export_v1.py`、`test_ue_refresh_representative_import_v1.py`、`test_refresh_delicate_transfer_v1.py`、`test_refresh_measured_lash_contract_v1.py`、`test_refresh_fbx_quad_equivalence_v1.py`、`test_refresh_eyelash_followers_v1.py`、`test_refresh_batch_prepare_v1.py`，同样位于该 Run Root。离线肤色候选人工复核及小型审计脚本属于本run取证附件，不成为 CC 装配执行器；素材与装配执行由 [CC Assembly Technical](../character_creator/ASSEMBLY_AND_ACCEPTANCE.md) 拥有。

## 2. 输入、候选目录与保护

候选审查helper的定向测试为 `00_engine/outputs/character_refresh_20261018_v1/test_ue_refresh_runtime_review_v1.py`，同属本Technical实现所有权；离线准备与测试不能证明真实UE审查、衣发/动作或最终画面已接受。

诊断测试 `00_engine/outputs/character_refresh_20261018_v1/test_ue_refresh_eye_animation_probe_v1.py` 与 `00_engine/scripts/character_creator/tests/test_cc_probe_refresh_skin_material_readonly_v1.py` 亦归本Technical；后者只证明源pin改变会在任何场景访问前拒绝，不模拟SDK成功。

`00_engine/scripts/character_creator/tests/test_cc_probe_refresh_pbr_export_ab_v1.py`证明A不改原设置、B只改实测单bit且原native setting直传SDK，未模拟真实导出成功。

Run内`test_pbr_format_directory_flag_patch_v1.py`、`pbr_format_directory_flag_v1.patch`、`pbr_format_directory_flag_patch_spec_v1.json`及v1/v2测试回执属于本Technical的导出修复与定向测试。root已授权安装该flag，真实原route AST验证flag表达式，不加载SDK或执行导出；旧准备/结果不改写。`test_refresh_revision_v2_v1.py`及`test_refresh_runtime_revision_v2.py`分别拥有转移精确revision边界和独立运行时v2组合测试。

同Run的`test_appearance_none_reset_patch_v1.py`及`appearance_none_reset_v1.patch`、`appearance_none_reset_patch_spec_v1.json`、`APPEARANCE_NONE_RESET_PATCH.md`、`appearance_none_reset_patch_tests_v1.xml`归本Technical候选运行时诊断所有权：8项离线原apply_actor AST/有状态检查服务于两none分支6新增行的待安装小修复。root现场已见liveSmile与savedNone不符，并在明确清除后两侧为None；候选patch尚未安装，neutral画面待root，不改当前pin依赖或据此接受正式运行时。

原 source40 沿 `%OUTPUT_ROOT%/unreal_character_import/cfd_native_batch40_20261006_v1/batch_source_spec.json`，实际 formal catalog 沿 `%OUTPUT_ROOT%/production_workflow_20261017_v1/asset_inventory_formal_runtime_catalog_20261016T191604.json`。compiler 要求40个原稳定身份/性别完全一致，读取实际 current meshes，包括 BM001 的 Recovery 路径，不重选身份。

候选写根 `/Game/DataMake/Characters/Revisions/CFD40_20261018/<ID>`；完整导出短根 `D:/UE/exports/character_creator/character_refresh_20261018_v1/<ID>`。现用骨架精确为 `/Game/DataMake/Characters/Skeletons/SKEL_CFDShared_Male_v1.SKEL_CFDShared_Male_v1` 与 Female 对应对象。共享骨架允许精确只读，不放开 SaveAsset、目录保存或 rename；不复制正式骨架、不更新 refpose/T0。AutoSetup 自己的见证 Skeleton 仅在候选目录内。

完整装配回执 schema=`cfd40_character_refresh_assembly_result_v1`、status=completed，同 character_id/sex、原 source_project pin 与实际新 result_project pin；compiler results schema=`cfd40_refresh_transfer_results_v1` 仅索引已有真实回执。导出/导入 prepare 还拒绝显式 recipe_complete=false、accepted_final=false、assembly_accepted=false。PRELASH、closed partial、支持恢复探针不得转写为成品回执。

红晕为 excluded_by_user，不是待实现步骤。batch 每人保留实际原照/工程、归档几何/zero-x-y-z-identity回执、新候选seed、两套骨架与每人规划目录。旧校准只标记逐人 source equivalence 待核验；不跨人复用最终 skin/import 逆矩阵，也不自动调度40人 fresh校准。

## 3. 最小调用顺序

原人物 → 几何实际修复 → skin/eyes/Makeup 的可复用 PRELASH → 选定睫毛及支持保护/恢复 → 真正完整装配回执 → 完整 FBX bundle → 候选共享骨架导入 → 候选运行时/视觉验收。前两段实际执行不由本组wrapper替代。

batch当前机器输入与逐人选择见 [batch_preparation_v7.json](../../../../../../00_engine/outputs/character_refresh_20261018_v1/batch_preparation_v7.json)，代表配方显式沿早先 WF/LM assembly library v4→v5 pins；两位代表不会被后来的批量抽样重选，其他38按冻结选择。缺少两位真实完整代表接受回执时，下面命令只返回 gate关闭与next=null：

```powershell
python 00_engine/outputs/character_refresh_20261018_v1/refresh_batch_prepare_v1.py --action next --plan 00_engine/outputs/character_refresh_20261018_v1/batch_preparation_v7.json
python 00_engine/outputs/character_refresh_20261018_v1/refresh_batch_prepare_v1.py --action status --plan 00_engine/outputs/character_refresh_20261018_v1/batch_preparation_v7.json
```

导出 prepare 的 `$refreshCompletedPlanPath` 必须是 compiler 已绑定真实完整装配的新 manifest，不得指向 pending或PRELASH。它只生成既有 Bridge 的一次提交命令，root在共享CC空闲后才执行；后续只查 status，不能轮询重复提交：

```powershell
python 00_engine/outputs/character_refresh_20261018_v1/cc_refresh_complete_export_v1.py --action prepare --transfer-manifest $refreshCompletedPlanPath --character-id CFD40_WF_003 --job-id WF003_EXPORT_001
python 00_engine/outputs/character_refresh_20261018_v1/cc_refresh_complete_export_v1.py --action status --preparation 00_engine/outputs/character_refresh_20261018_v1/representative_exports/WF003_EXPORT_001/preparation.json
```

导出沿用 prepare_exports/make_library/bind_export_report/BridgeStepDriver；完整inventory绑定同一实际新工程、单次 UE5 motion=false/bake_subdivision=false、同基名 FBX/JSON、全部文件 SHA 和 Texture Path 闭包。full export verified 才可准备导入：

```powershell
python 00_engine/outputs/character_refresh_20261018_v1/ue_refresh_representative_import_v1.py --action prepare --transfer-manifest $refreshCompletedPlanPath --character-id CFD40_WF_003 --export-inventory $refreshVerifiedExportInventory --target-file $refreshUETargetFile --job-id WF003_REP_001
```

target JSON 精确包含 node_id/user/project/full project_file/当前 PID，uproject必须是 `D:/UE/projects/datatry_02/datatry_02.uproject`；不得只凭项目名连实例。prepare/status不连UE；显式 submit/resume 才走既有远程执行，入UE后再核对完整工程/PID、无脏包及无MRQ渲染。

## 4. 实测睫毛片合同

完整回执必须有注册实际 `eyelash_asset={asset_id,path,sha256}`，及 `eyelash_parts_evidence={capture:filepin,added_parts:list}`。每个新增 mesh 必需 name、owner、avatar_part_type字符串9、正整数 vertex_count/face_count、原有序 faces_sha256。

capture包含同 character_id/asset/list 与真实 native_snapshot filepin；读取 snapshot.other_meshes.meshes/parts/working_subdivision=0。所有非原六件须恰为清单，真实 type9对象与mesh.owner对应；mesh名可以不同于附属对象名，多个mesh也可有同一真实owner。当前注册9款均有新增件，空清单拒绝。registry素材授权与本人结构证据独立核验，不能套Delicate固定两片或靠exact6漏导。

实际 FBX 再逐件核对 mesh名、控制点及原面索引顺序SHA。原多边形可精确相等；标准导出的相邻三角对仅在完整覆盖、共享对角边反向、四个唯一原索引且按统一有向边界规则重建的整份有序quad SHA恰等于本人CC capture时等价通过。点数、索引顺序或winding仍不能改变；未知、重复、漏件、空材质、坏索引及不能精确恢复CC SHA的三角化继续拒绝，不接纳新hash常量或猜映射。原 pair.expectation 仍恰需六标准件；其后复用原 AutoSetup、DO_NOT_COMBINE、完整 Morph、118骨/层级/权重/材质与同一共享骨架检查。

详细字段、旧9款2/4件和对象/mesh拼写差异及缺证边界见 [动态合同](../../../../../../00_engine/outputs/character_refresh_20261018_v1/MEASURED_EYELASH_IMPORT_CONTRACT.md)。旧bounds/transform digest不提供拓扑，新部件实测不能从旧视觉矩阵编造。

## 5. 私有跟随与恢复

导入真成功才写 eyelash_follower_mapping_v1.json，绑定实际所有附属件/材质/骨架和Body曲线对应。root在新的 `/Game/DataMake/Validation/CFD40Refresh20261018/` 候选map中调用 adapter.bind/readback/set_visible/clear/owned，显式提供当前PID和实际主体/映射。每片独立SkeletalMeshActor，Owner/attachment/leader指向主体Body；源曲线名不同则拒绝猜remap。主体仍exact38，主体显隐/删除/身份改变或输入pins改变时同步/限定清理。

当前由appearance子任务接管adapter及其测试，已以owner路径bindings与唯一tick替代早期单owner实现，兼容原API。显式persistent=True与save_scene/restore_scene绑定实际map SHA、主体/所有附属refs和38槽；runtime helper仅在私有候选模块接入assembler/worker，收集原Body唯一动画轨和附属possessables，再复用隔离MRQ入口。detach与release_for_reload释放持久actor及原装配cache引用，避免旧World引用阻止卸载，不删除或修改native属性。以上为实现合同及`multiowner_runtime_regression_v3.xml`的77项定向离线回归（28 adapter、18 helper、31 measured contract，0 fail/error/skip）；冻结pins见`multiowner_runtime_validation_v1.json`。新关卡/序列/渲染尚需root实跑，不能当作已经生成多人画面或表情传递验收。transient预览不能替代持久map/sequence绑定，实际眨眼/视线贴合仍需画面。

import request/manifest/源码pins不可变，pending/unknown不重发。status只查磁盘；异常退出仅用 recover-exited 核对旧Editor与控制器确已退出、锁/active精确属于自己，再保留旧状态为failed并释放自有锁。真实失败后新target、新job、同manifest显式resume；不自动删资产、换源、建恢复目录或修共享骨架。完整接口/失败范围见 [单人导入](../../../../../../00_engine/outputs/character_refresh_20261018_v1/UE_REPRESENTATIVE_IMPORT.md)、[完整导出](../../../../../../00_engine/outputs/character_refresh_20261018_v1/CC_COMPLETE_EXPORT.md)、[私有运行时](../../../../../../00_engine/outputs/character_refresh_20261018_v1/EYELASH_FOLLOWER_RUNTIME.md)、[批量准备](../../../../../../00_engine/outputs/character_refresh_20261018_v1/BATCH_PREPARATION.md)。

2026-10-18真实WF003_REP_001在任何导入前因UE5.8不存在`SystemLibrary.get_project_name`失败，worker终态failed优先于controller_uncertain，dirty为空。现在从已精确验证的`Paths.get_project_file_path`完整路径stem核对名称，保留PID/完整路径门。原源码、请求与结果不改；同活Editor的新job可显式resume，须active请求SHA与真实failed worker绑定，且manifest/plan/项目/共享骨架/导出源/策略全等；当前新请求仍完整验证新代码依赖，不要求历史worker源码继续是当前版本。只有pending且确证进程已退出才用recover-exited。`project_api_fix_validation_v1.json`绑定原字节、失败证据、新002请求和3项定向检查，未声明真实新导入成功。

## 6. 输出与验证范围

本run的 `00_engine/outputs/character_refresh_20261018_v1/representative_assembly/` 保存派生的独立CC完成回执、原始链pins、源专属例外与同SHA导出暂存映射；`00_engine/outputs/character_refresh_20261018_v1/representative_import_jobs/` 保存隔离的不可变导入请求、controller/worker状态与审计索引，二者均不等于formal发布。

同root下的`representative_scene_configs/`、`representative_scene_restores/`分别保存候选场景持久绑定配置和恢复核验；`representative_sequence_followers/`保存附属睫毛与原Body动画轨收集证据；`representative_mrq/`保存隔离渲染请求/回执；`representative_runtime_requests/`、`representative_runtime_reviews/`、`representative_follower_reviews/`分别保存候选运行时请求、主体审查和附属跟随读回。这些目录归本Technical的候选运行时实验所有权，实际输出以root执行回执为准，不预建假成功。

`eye_animation_probes/`保存独立眼部动画诊断的配置/源与共享骨架保护读回，不能代替生产性能或画面接受；CC只读纹理probe的实际图/回执归Bridge artifacts `character_refresh_20261018_v1/LM002_skin_material_readonly_v1/`，本Run仅保存准备manifest与测试。

本run保存 manifest、输入pins、逐人prepare/job/worker状态、完整export inventory、import audit/follower mapping、批量plan/progress、离线JUnit及验证记录；真实二进制仍留原语义路径。原始输入、共享骨架和历史回执不覆盖。精确本轮进度由机器计划/回执与Status拥有；本组离线输出不构成新发布或额外永久保留授权，仍按现有Output/retention治理处理。

最新动态实现冻结见 [dynamic_lash_contract_validation_v1.json](../../../../../../00_engine/outputs/character_refresh_20261018_v1/dynamic_lash_contract_validation_v1.json) 与绑定的75项离线测试。检查temporary小型拓扑与metadata、实际注册素材pin及边界，不模拟真实SDK/UE成功；实际pending manifest拒绝发生于目标/目录创建之前。历史compiler/export/batch验证分别沿本run transfer_compiler_validation_v1.json、complete_export_validation_v1.json、batch_prepare_validation_v2.json，不把其旧源码pins当新动态版运行证明。

本次只维护以上Technical所有权与transfer索引，Catalog/Registry/Status/OutputInventory由root协调统一同步；未因候选准备重跑全仓测试或晋升正式Gate。

2026-10-18实际完整FBX已证明并经root条件授权的标准三角化支持：两代表各标准6+新增2、118骨、3245源Morph；新增两片UV通道有限且索引完整。`pair_actual_fbx_quad_triangulation_proof_v1.json`保存原CC SHA完全还原证明，`pair_actual_complete_fbx_offline_audit_v2.json`是当前源门实跑。`fbx_quad_equivalence_validation_v1.json`绑定53项定向检查和新源码；旧`import_wrapper_before_triangulation_v1.py.txt`保持先前导出冻结依赖的原字节。已完成export的旧preparation/status若因源码pin变化拒绝重查，不能改旧回执；直接用已核验真实inventory和新importprepare，原导出执行证据仍保留。没有以离线通过替代UE导入或画面验收。

WF003_REP_002在导入前误将字母序reference行索引到原序bone_tree，十骨模式门错误拒绝。root当前原骨序实际读回`shared_skeleton_actual_modes_0513.json`确认男女118骨及十骨均Skeleton，故只修索引顺序，未改共享包/十骨门；旧源码与002结果保留。`bone_order_fix_tests_v1.xml`用历史实录非字母序118骨验证正确模式通过/错误模式拒绝及恢复边界4项，003请求绑定修正源码；真实导入仍以worker结果为准。

WF003_REP_003和LM002_REP_003现均已真实worker completed，每人六标准件加两片实测睫毛共8件、3245个Morph；实际绑定原性别共享Skeleton，磁盘与可读reference/modes/curve flags前后不变，published=false。女性于2026-10-18 05:21:04（上海）完成；两性实际回执及follower mapping分别位于`representative_import_jobs/<job>/worker_status.json`与`representative_imports/<ID>/eyelash_follower_mapping_v1.json`。本wrapper及请求依赖冻结，不能因运行中新进展改动已pin源码；动态/画面接受仍独立维护，未发布formal或接受其余38人。当前执行状态由root的execution_record.ue_representative_current与真实worker回执维护。

女性导入UI的绑定姿态警告恰为l/r_toebasesharebone与7个ik_*，实际8件source-model skinweights均无这些骨的正权重，invalid_vertices均0；日志先报relative matrices不匹配，随后记载FbxSDKBindPose有效及recreation succeeded。`WF003_import_bindpose_readonly_audit_v1.json`绑定真实audit、权重交集和日志摘录。这支持继续既定neutral/blink/身体动作审查，不授权更新共享refpose或启用T0。当前mesh refpose记录有限值、骨名与父层级精确匹配源，但未逐值证明源transform等价；4张JSON声明眼/牙Normal真实绑定且TC_NORMALMAP/sRGB=false，不代表皮肤shader像素或颈胸画面已在UE验收。

root的女性runtime001 stage/readback已实际通过；首张高分辨截图调用超时但编辑器仍在编译749个shader（当时67%），没有重复派发或把未返回截图当完成。此为实时进展记录，最终画面及持久map/sequence/MRQ闭环另以真实回执更新。

后续root已看`neutral_front_reset_v1.png`确认双眼正常张开，`none_reset_actual_v1.json`记录liveSmile/savedNone到明确清除后两None，候选patch仍未安装。主体38槽＋两lash跨tick及smile2.3秒闭眼贴合现场通过。WF003_PERSIST_001已持久绑定且save_scene保存`representative_scene_configs/WF003_VISUAL_DIAG_001.json`，actual_reloaded=false，MRQ未测；male运行时另待root。两import completed计数2不等于整批接受，bulk=false/noformalpromotion，皮肤质量仍pending。

## 7. 实际皮肤质量缺口与只读定位

`skin_export_texture_gap_audit_v1.json/.md`绑定两代表实际JSON/纹理和CC像素证据。两人四Skin均未导出Normal，Roughness/AO路径空，Custom Shader Image路径全空，磁盘只有四张2048 Diffuse与Body/Leg Metallic；UE Head因此落入4px默认Normal/Gray。CC最终重载四皮肤Roughness/AO实图仍2048且保持，故至少这部分是导出取用缺口；legacy Bump在常规after_skin有效、保存阶段变warning，尚需独立Normal读取，不能靠Bump字段替代Normal结论。4眼/牙Normal绑定门不提供完整皮肤质量证明。

root已实际完成同图驻留对照：`neutral_front_resident.png`眉毛/雀斑恢复清楚，原`neutral_front_closeup.png`块糊。流送与缺皮肤通道为两项独立问题，前者改善不接受后者。

现export preset未写Diffuse-only筛选，但flags未包含`EExportFbxOptions_ExportPbrTextureAsImageInFormatDirectory`；[官方RFileIO Unreal示例](https://wiki.reallusion.com/IC8_Python_API%3ARLPy_RFileIO)明确列该flag。[CC5 Texture Preset手册](https://manual.reallusion.com/Character-Creator-5/Content/ENU/5.0/17-Export/FBX-Advanced-Settings-Texture-Preset.htm)说明该preset控制整套通道组合。缺flag是最小独立对照候选，未实测证明；不据示例顺带改变InverseNormalY。

`LM002_skin_material_readonly_probe_manifest_v1.json`冻结当前male最终源SHA与只读脚本。root已加入精确mode并于05:48:29在同CC实例真实完成一次，报告success=true：四皮肤Normal独立读口均sdk_empty_image，Bump均已知warning；四Roughness/AO实图均2048，Shininess也为空。SDK实值ExportPbrTextureAsImageInFormatDirectory=16777216，shader图可读方法仅发现GetShaderTextureNames且doc为空，未猜调用。实际报告/像素及分析见`LM002_skin_material_readonly_analysis_v1.json`；不加载/保存场景、不应用材质、不切细分。

`LM002_pbr_export_ab_manifest_v1.json`与staged library对应同7cc5源独立A/B，root于05:55:53真实完成：A native option4104，B16781320，异或恰16777216；option2=86075380/option3=1/Original=0/Default=0全相等、InverseNormalY未变。私有API view未修改live SDK/module或共享route，原route baseline请求记录不变，companion native_calls为实际GetOption权威。新输出为`D:/UE/exports/character_creator/character_refresh_20261018_v1/CFD40_LM_002_PBR_FLAG_A_v1/`及B目录，Bridge诊断归`headshot_character_creation_20261005_v1/CFD40_REFRESH_PBR_AB_20261018_v1/LM002/`，不冒充正式transfer inventory。

`LM002_pbr_export_ab_analysis_v1.json`绑定实际JSON/文件与逐像素证明：A37张图、四Skin无ORM与shader图；B129张图、四Skin ORM均2048且shader路径/图已输出。四ORM.R等于四源AO.R、四ORM.G等于四源Roughness.G，8项全像素误差0。Body原Roughness小部分RGB并不全灰，不能拿其R或亮度替代G比较。独立Roughness/AO字段仍空是Unreal ORM打包，不能再判为丢图。该旧源A/B基础Normal仍缺，MicroN/NBMap不能重命名替代。PBR flag已由root授权安装并通过真实分支AST检查，随后v2目录衔接见§8。新完整export/准备pins与实际质量检查另产，旧job不改写；两代表及40人整体画面gate仍关闭。

## 8. v2精确目录衔接与冻结

root已授权在同pipeline安装实证PBR flag，并为修复法线后的成品增加v2精确白名单。compiler的`revision_spec(document)`只允许v1/v2配对；旧缺字段仅解释为v1。新manifest/request/mapping显式写`revision_id`、`ue_root`、`export_root`。v2 UE根为`/Game/DataMake/Characters/Revisions/CFD40_20261018_v2`，短导出根为`D:/UE/exports/character_creator/character_refresh_20261018_v2`，原40ID和两性现共享Skeleton不变。v2必须显式配对两根，缺字段/跨版本/任意根均拒绝。

exportwrapper仍复用旧prepare_exports/make_library/BridgeStepDriver，只从版本表选择根与`CFD40_REFRESH_EXPORT_20261018_v2`状态前缀；route仅增加精确v2短根允许项及PBR flag。importer仍复用同AutoSetup/split/Morph/共享包保护，报告落`representative_imports_v2/<ID>`，候选写范围从已核验revision决定，防止覆盖原v1。原编译器/export/import源码在`*.before_revision_v2.txt`保留，旧请求/回执/UE资产不改。

`revision_v2_implementation_freeze_v1.json`绑定最终compiler/export/import/route SHA、45项原回归与7项新边界检查、male实际新receipt/manifest/prepare。root使用这些已pin依赖期间不得修改。男v1旧runtime readback曾因这次获授权源码适配拒绝，保留原错误和现场，未回滚/改旧pins，不能记为已保存。

LM002同源四法线实际恢复在06:04:58已成功，最终7521bbab…项目152891923字节由新v2 staging同SHA镜像。`representative_assembly_v2/CFD40_LM_002/completed_cc_assembly_result_v1.json`独立链接旧完整装配receipt和真实Normal restore报告；只四Normal写入/重载像素一致，全部native几何和其他8通道保护通过，旧probe的accepted_final/recipe_complete=false原值不改。原source/Delicate native704精确indices与7.37mm界限只沿已证几何不变的新派生链保留，不泛化其他人或素材。`transfer_manifest_normal_v2_LM002_v1.json`保持40ID，仅male1新成品真完成；`representative_exports/LM002_V2_EXPORT_001/preparation.json`已prepare未由本子任务提交，期望新短根/同ID，不覆盖旧FBX。actual完整新FBX及UE绑定/驻留/画面仍须验证，四Skin Normal＋ORM＋实际shader图不得再用眼牙四Normal代替。

法线SDK语义边界必须保留：本次正确`EMaterialTextureChannel_Normal`写入后，真实Normal getter仍空，而Bump getter已得到同源正确2048蓝色法线且保存重载像素完全一致。因此不能把独立Normal getter为空本身当作修复失败或一般性的槽缺失判据；此前缺图由Bump warning与真实FBX基础Normal缺失共同支持。新成品最终以语义已证Bump读回和实际FBX四Skin Normal/UE绑定为准。

male v2完整导出于06:14:34实际完成，inventory SHA42556dc4…；`LM002_v2_skin_export_quality_audit_v1.json`与`LM002_v2_actual_full_fbx_audit_v1.json`已只读核验真实bundle：八件/118骨/3245Morph、四Skin 2048基础Normal的文件SHA及RGB逐像素恰等恢复输入、四2048 ORM的AO.R/Roughness.G八项逐像素误差0，声明shader图全部实有。可进入候选导入，UE材质绑定与画面仍pending。

旧v1与新v2真实FBX的八件点数相同、原多边形索引和完整UV层全等；浮点顶点不bit-exact，不能写0。实际UnitScaleFactor=1cm，最大欧氏差Body0.000682810mm、Tongue0.000458029mm，其余含两lash约0.0000143175mm，均在既有0.002mm内，未改变阈值。证据`LM002_v1_v2_actual_fbx_geometry_uv_equivalence_v1.json`保留all_exact=false，`LM002_v1_v2_fbx_position_quantization_v1.json`给出真实单位与差值，不将此比较扩大为UE变形或画面接受。

WF同源四Normal恢复于06:19:22真实bound report成功，143007074字节74abdc6a…候选与generic engine输出仅为同字节alias；原泛化engine文件名/报告不改写，female身份/源/素材由真实bound report独立绑定。`representative_assembly_v2/CFD40_WF_003/completed_cc_assembly_result_v1.json`链接原完整recipe＋bound/engine两份实际恢复报告和same-byte staging；原exactWF/Delicate native704indices与9.32mm界限只沿已证保护的新链保留。`transfer_manifest_normal_v2_pair_v1.json`新编译40ID/2源真完成，不覆盖已提交male单人manifest；`representative_exports/WF_V2_EXPORT_001/preparation.json`已真实prepare并pin当前最终dispatcher，未由本子任务提交。root当时正在真实执行LM002_V2_REP_001，完成/新画面结论以worker为准。本文追加记录没有修改被冻结compiler/import/export/route或旧请求pins。

后续root已确认female v2 export completed（inventory SHAe622c486…），`WF003_v2_skin_export_quality_audit_v1.json`、`WF003_v2_actual_full_fbx_audit_v1.json`真实只读验证四2048基础Normal对同WF输入文件SHA/RGB全等、四ORM八个AO.R/Roughness.G分量像素误差0、shader图实有及八件/118骨/3245Morph完整。`WF003_v1_v2_actual_fbx_geometry_uv_equivalence_v1.json`证明八件点数/拓扑/完整UV层全等；厘米单位最大欧氏差0.000613046449mm在既有0.002mm内，顶点不bit-exact不写0。source可进入候选导入，尚不接受UE材质/画面。

LM002_V2_REP_001已真实worker completed，共享磁盘/可读字段不变，8张声明Normal实际绑定门通过（四Skin＋四眼牙）。新mapping在`representative_imports_v2/CFD40_LM_002/eyelash_follower_mapping_v1.json`，原v1资源保留；男女v2最终装配、主体38组件＋2睫毛附属组件行为、肤色/眉毛/颈胸近景、持久重载和MRQ结论仍需独立真实回执。不得将两位新CC源、两个v2完整导出或单个v2导入计数混写为40人接受。

root后续实际v2运行时：male材质UseORM=true，闭眼到fresh/cached None均恢复张眼，侧面已看；恰两片新lash的dirty候选材质已显式保存。LM002_V2_VISUAL_001已save并真实RELOAD，owner1/spawn0、主体38＋附属2跨tick及root看图通过，发高光噪点仍未最终接受，也没有把MRQ写成已测。female v2首次001在dirty guard前置拒绝、未导入，002当时实际running，不能预写成功。其余38的offline order f6c4d9…仍0次实际执行。本note仅追加实际进展，不改变冻结源码、原失败/完成回执、正式registry或整批gate。

appearance的独立v2 follower/runtime入口保留旧v1文件字节，精确新关卡`/Game/DataMake/Validation/CFD40Refresh20261018_v2`；新输出目录为`representative_runtime_requests_v2/`、`representative_runtime_reviews_v2/`、`representative_follower_reviews_v2/`、`representative_scene_configs_v2/`、`representative_scene_restores_v2/`、`representative_sequence_followers_v2/`、`representative_mrq_v2/`。这些目录及`representative_assembly_v2/`、`representative_imports_v2/`归本Technical候选实验输出所有权，未改变retention授权。19项离线组合回归与冻结说明见`runtime_revision_v2_validation_v1.json`、`RUNTIME_REVISION_V2.md`；前者是离线合同证据，实际男性v2单人绑定/重载/画面进展见上条，不能因初始冻结说明仍写pending而抹去实际回执；多人、Sequence及MRQ仍待root。

本次只读补充核验：`WF003_V2_REP_002/worker_status.json`于上海06:46:52真实completed，001仅为脏地图前置拒绝，不计资源导入；因此两代表v2导入现均完成，女性新画面仍需独立root接受。`representative_remaining_checks_v2.md`归本Technical输出所有权，整理现有`representative_gate`七项字段、v7当前真实pin与两代表source/geometry/seed/lash绑定通过、最短视线/身体动作/旧衣发样本，以及一次双代表多owner/Sequence/MRQ现有调用配方。它没有创建accepted Gate/运行时接受记录，没有执行应用或修改被冻结代码，也不额外要求八人/衣发/动作矩阵后才允许原代表门审查。

随后root实际查看女性v2 neutral、smile2.30闭眼、左右视线、MOTION_CAND_001/1.0旧衣发、无遮挡颈胸与下巴侧面、恢复衣发后的neutral，明确接受该代表现有七项运行时检查。`representative_runtime_reviews_v2/WF003_RUNTIME_V2_001/root_visual_observations_v1.json`记录root观察而非记录agent独立看图；同目录`candidate_runtime_acceptance_v1.json`绑定真实成功import002、27份实际文件pins、CC Eyebrow90保存重载读回及v5 recipe的redness排除。既有`runtime_fact`窄核验通过；gaze-left含眯眼、编辑层重入未证、发高光/颗粒质量边界均保留。WF003_V2_VISUAL_001已保存但actual_reloaded=false，MRQ/multiowner/bulk/userfinal均false，未创建pairgate、未发布formal，未改冻结代码或操作应用。

**阶段更正（随后由下方保存修复及新接受证据替代）**：root后续在男性无遮挡颈胸发现明显三角明暗块。本Technical owner已实际查看男女正/侧四张原PNG，确认男性锁骨/上胸及女性侧面肩顶/上臂/胸侧均存在同类分块着色；两者未见旧下巴嵌入基座仍只是窄事实。新增女性`candidate_runtime_acceptance_correction_v2.json`明确supersedes旧accepted记录用于当时gate，撤回`skin_neck_chest`一项、保留另六项及旧文件字节；当时男女该项均不通过，未建pairgate。`skin_shading_readonly_audit_v1.json`绑定真实图/两性import audit与更正：实际split显式recompute_normals/tangents均true，四Skin Normal来源/TC_NORMALMAP/sRGB已核实，但UE RenderData角法线/切线与源等价尚无实测。`SKIN_SHADING_SINGLE_VARIABLE_DIAGNOSIS.md`给root只改当前Body四Skin临时MID之Normal Map到既有Normal_Default再恢复的单变量配方；不操作应用、不写源材质/mesh/Skeleton、不改冻结代码。root的默认材质、阴影等后续独立诊断由真实新回执继续记录，不能把建议或单项缓解当根因/修复通过。

root随后实际报告基础平Normal替换使大三角消失，关闭Body cast_shadow仍明显，优先指向基础Normal与切线basis交互，未确定最终根因。`NORMAL_BASIS_READBACK_AND_FLIP_DIAGNOSIS.md`归本Technical输出，基于实际CC JSON无基础NormalY、插件仅MicroNormal flip映射、本机UE5.8源码已暴露LOD build getter/setter及PostEditChange重建，给出四Skin实际flip/scalar读回、独立纹理副本切换绿色通道的临时MID对照和独立Body副本仅禁normal重算的无导入弹窗方案。源FBX无tangent层且builder缺数据强制计算，因此false/false不是“已还原原CC tangent”的证明；副本不能直接换进mapping守护的原Body。方案未实跑，不改冻结或原资产，不撤销当前肤质阻塞。

后续root实际方向对照：false/false Body副本正面仍分块；原Body四基础Normal副本仅FlipGreen后正面大三角消失且细节保留，侧面残留并未全消除。root再以正式旧`/Identities/CFD40_LM_002` Body同相机/灯光纯灰对照，确认相同肩顶折线为既有低模表现，限定本轮皮肤门检查裂缝/接头/新增异常，不把身体细分优化扩成硬门。root授权仅male v2四Texture后导入方向修复，女性仍待独立实证。

新增本Technical实验脚本owner：`00_engine/outputs/character_refresh_20261018_v1/ue_refresh_skin_normal_direction_v1.py`与`test_skin_normal_direction_v1.py`；步骤`SKIN_NORMAL_DIRECTION_POST_IMPORT.md`，输出精确scope `skin_normal_direction_fixes/`（source-bound request、原包字节rollback、逐张progress及实际执行后completed），不改变retention。脚本独立于冻结import/rr，仅male四精确Skin Normal Texture flip=True/保存，保护原MIC/Body/shared Skeleton/导出与历史回执。001已实际离线prepare并备份四原uasset；2项窄离线测试通过，实际UE应用待root，新completed/视觉/女性或pairgate未由准备推定。

male随后已实际应用完成，`skin_normal_direction_fixes/LM002_NORMAL_DIRECTION_001/completed.json` SHA87a4478893b6be050a3087455b3cebd9ee27942877432ca0bb2d7b7fbd7d714b；root看保存后head/neckfront通过。appearance写男性`candidate_runtime_acceptance_v1.json` SHA40a20f5d7cba029b9b0a966a36d3d487c2cc5e78a6625932712fe0dab7e4afce，既有runtime_fact通过，39份真实evidence含本次completed与四保存后Texture包pins。此轮无Texture冷重载，旧scene reload另述，继承低模/实时发noise边界保留，pair/bulk/userfinal/MRQ/multiowner均false。

root随后实际确认女性WF003_V2_RELOAD_001 owner1/spawn0、四原Normal flip=False，以及女性自己的四copy/MID flipTrue与原正面图修正对照，明确授权女性同范围应用。新增本Technical实验owner脚本`ue_refresh_skin_normal_direction_female_v1.py`与`test_skin_normal_direction_female_v1.py`，精确SHA复用未变male逻辑，仅female ID/真实quality bound key/import002/女性证据适配；一项窄离线测试通过。`skin_normal_direction_fixes/WF003_NORMAL_DIRECTION_001/request.json`已实际离线prepare、四原包byte备份及所有pins核验通过，不操作UE；女性实际apply/新接受仍待root，不复用男性completed冒充通过，原female correction保留至实际重新接受。

**当前两代表门已实际核验通过，仍未发布或接受全40**：女性后导入修复已实际completed SHA2b1eb673d3c47389f4077e13f79c05aa6e6f6b613fdccd440b619451f9bb1320。root看保存后neutral/neckfront通过，0748真实routing/pose均true，诊断材质/衣发恢复；正式旧女性Body同相机/灯光纯灰和新Body肩顶同位置折线支持继承低模限制。女性`root_visual_observations_v2.json`与`candidate_runtime_acceptance_v3.json`（SHA0b1eb37ae8c3582e0e2ad52345e0b82cca547a77a50db3a96cadd0d50ef9aaea）明确supersede旧accepted与correction，原文件字节不改。七项接受限裂缝/接头/本轮新增异常与原动作衣发等既定范围，不要求消除全部原生facet。

本Technical产出`representative_gate_v2.json` SHA09d45851b8149b5cc4bbd88977c339a44233787ba5f86f1e438686f2ad675eb4，绑定v7、两完整v2 CC assembly receipts、完整导出、male001/female002实际成功import、新male接受与femalev3，以及8张真实保存后Normal Texture包pins。`representative_receipts_v2.json`为两人显式真实阶段输入；既有`refresh_batch_prepare_v1.status`最终回执`batch_progress_representative_gate_v2.json` SHAdee39f993050ec39b463d5cd8b8bb14a9bfd75157096b15a5f82941dd05048f2，gate.passed=true、两人complete_candidate_not_published/import completed、application_dispatched=false。这里仅离线核验，不启动CC/UE、不改冻结代码；允许root按现有逐人门继续候选工作，Texture修复后冷重载/MRQ/multiowner/userfinal/全40接受均false。实际旧scene reload与修复后Texture冷重载严格分开；后续新应用工作由root另行执行与记录。

新增候选拍摄集成实验owner：`ue_refresh_pair_sequence_mrq_v1.py`、`test_refresh_pair_sequence_mrq_v1.py`，步骤`PAIR_SEQUENCE_MRQ_PAYLOAD.md`。精确新输出scope `representative_pair_integration/PAIR_MRQ_001/`保存离线请求及实际执行后stage/sequence准备记录；派生UE新root `/Game/DataMake/Validation/CFD40Refresh20261018_v2/PAIR_MRQ_001`，不改现female/male地图或配置。当前实际request_v2已离线prepare且全部源/mapping/8Normal包pins checked通过；60帧/2秒，原组合动画1→3秒窗口，2 owner各38+2，只有Body动画轨，四lash按原adapter收集，MRQ沿原隔离入口。两项窄离线检查通过，未调用应用或修改被冻结依赖，实际取景/Sequence/MRQ全待root，不新增剩38人gate。旧未运行request.json/原payload字节仅保留初稿证据，当前入口只接受request_v2。

初次root实际stage因pair标签未使用原assembler要求的`DM_SiteReview_`前缀而拒绝（0809回执），已建pair图且仅一位female38槽；0811actual partial确认无bindings/LIVE/dirtycontent。独立实验owner补充`ue_refresh_pair_stage_resume_v1.py`与`test_pair_stage_resume_v1.py`：只复用这个female、合法改label、仅缺male才duplicate，不new_level/load_level/重stage；旧payload/request/失败回执字节不改。一项针对真实guard和禁止重建地图的离线检查通过，resume实际仍由root执行，以staged/后续真回执为准，未将准备记成多人或MRQ通过。

root随后真实resume与finalize成功；PAIR_MRQ_RENDER_001 completed/success、errors=[]、global_queue_unchanged/input_files_unchanged均true。`representative_pair_integration/PAIR_MRQ_001/frame_decode_v1.json`记录60张1280×720 PNG全解码，root已看0000/0039/0059确认双人动作衣发可见跟随、取景完整，脸亮/发丝dither保留，小脸画面不足独自确认新增lash最终像素。saved scene实际2owner各38+2、collection四lash actor/component possessables、新lash骨骼轨0；这些与实际渲染成功不冒称PIE内leader/最终Morph权重已直接读回。`PAIR_PIE_EVIDENCE_SCOPE.md`归本Technical输出，给出同map/Sequence一次4K及渲染期间一次不留PIE对象引用的原生只读关系/pose采样片段；不注册新callback、不改冻结脚本、不新增批量gate，本agent未执行UE。

**双owner短片集成现已限定接受**：PAIR_MRQ_DETAIL_001实际4K渲染completed/success，60帧3840×2160、无errors、queue/input files不变。root看实际0000/0037/0039及其分析裁区，确认男女开闭眼时新睫毛可见自然跟随，无明显漂浮/跨owner，动作衣发正常；root接受`representative_pair_integration/PAIR_MRQ_001/root_integration_acceptance_v1.json`（SHA79b4d3c611c22b825460e6b78b5752bf509abaf9a3c782e3425da5195cef65fb），记录时间2026-10-18 08:22:36上海。本owner只读核该真实接受文件的request/prepared/renderer/PIE pins、60个实际帧文件及root查看三帧SHA/尺寸通过；不重复整段解码或再渲染。实际PIE查询赶晚，`actual_pie_bindings_v1.json` worlds=[]明确not_captured，不当通过；未读最终求值Morph权重，也无全帧pixel-perfect断言。场景脸部亮度、发丝dither/美术光照为另行交付限制，不要求第三次render或八人矩阵。原七CHECK Gate SHA09d458…675eb4保持不变；本集成接受不是全40完成、用户最终或formal发布。

appearance已冻结剩38人的独立source-bound Normal方向实验入口，本Technical补其owner：`ue_refresh_skin_normal_direction_generic_v1.py`（SHAc7831d642e32f784ce33ada54ec7502ea8d96535fd7f7bd4e87c44d5fb2a2ce8）、`test_skin_normal_direction_generic_v1.py`，步骤`SKIN_NORMAL_DIRECTION_GENERIC.md`，验证`normal_direction_generic_validation_v1.json`/`normal_direction_generic_tests_v1.xml`（16项、3.75秒）。仅私有复用原male apply，原male/female入口不变；从真实v2 import request/audit、同export/source quality及四map来源核验动态ID精确四图，允许原Normal写入报告或新的serial completed hook.maps来源，不要求逐人重做代表A/B，也不从completed自动接受visual。输出复用`skin_normal_direction_fixes/<ID>/<attempt>/`，不覆盖原flat代表attempt；实际两个代表只读inspect通过，generic prepare/apply均0，后续真实执行另报，不计批量完成。

appearance随后新增PRELASH真实schema窄兼容实验owner：同Run `ue_refresh_skin_normal_direction_generic_v2.py`（SHA2647004ffe5d3971b6ebf2ce102b00d8e06206354959c7d1ce390042fa4f14b0）、`test_skin_normal_direction_generic_v2.py`，步骤`SKIN_NORMAL_DIRECTION_GENERIC_V2.md`；`normal_direction_generic_v2_validation_v1.json`/`normal_direction_generic_v2_tests_v1.xml`两项0.41秒。真实AM001 PRELASH无top ID时用config/closure同ID绑定，严格实际success/stage/hook complete及四源图SHA/bytes，running先拒绝；旧generic_v1与两代表入口不变。这里只登记离线实现，generic_v2 prepare/apply/SDK均0，不改变批量或视觉完成状态。

新增本Technical只读输出`V2_REVIEW_PUBLICATION_REUSE_GAPS.md`：实际正式active catalog仍指旧`/Identities`40人；旧publish_current仅为搬移发布器，当前primary/生产试片没有自动激活refresh adapter。报告给出沿现有UI、私有模块图、六件overlay、逐ID实测mapping、保存/Sequence/MRQ的最短候选接入及将来显式正式发布/整体回退步骤。九款并非固定每人两片，Dense/Dense_Extended历史各四片，其余七款两片，最终均以本次实际capture/import mapping为准；不新增八人或所有衣发矩阵门槛。

root随后授权的隔离面板薄实现归本Technical实验owner：`00_engine/outputs/character_refresh_20261018_v1/ue_refresh_candidate_panel_v1.py`（SHAfc5e37f523f051e28723997e863aa2676b57b72f7e664d61a5638a9bab835e35）和`test_refresh_candidate_panel_v1.py`，步骤`CANDIDATE_PANEL_PILOT.md`。精确输出scope `candidate_panel/`含不可变配置、复制的原本地几何/相机catalog输入、实际执行后bootstrap/请求/回复/独立点位外观草稿及短片准备记录；新增`candidate_panel_validation_v1.json`与`candidate_panel_tests_v3.xml`（四项0.37秒）。本次实际离线prepare为`candidate_panel/PANEL_PILOT_002/configuration.json`（SHA668faf1dc599fbd7a7302191521fd31ac1ef07ff67cc4a68f83fb81ce72368da）；001是早期未运行且已失效source-pin准备，保留不提交。77份实际pins和私有UI/production图装载通过，UI只列两个真实v2导入及各自Normal修复成员；未调用UE/CC、未bootstrap/打开面板/渲染，不能据此称实机可用。

新endpoint沿原panel控件/primary私有行为/production dispatcher；内部所有production assembler import统一指向同一私有v2装配实例，覆盖普通preview、set_appearance直调闭包、playback、restore。根38、两Skeleton、六标准部件不变，附属长度由实际mapping给出；revision配置pin加到既有sources指纹。只允许独立v2 Validation图，严格拒绝旧binding/dirty/MRQ后才bootstrap；render沿当前实际Body/表情、原native轨/collect/save/MRQ做2秒当前相机样本，不伪造geometry_pass，不接管正式生产renderer。原active pointer/endpoint/冻结v2 adapter不改，正式生产/Scenes激活仍待全40真实完成及明确发布；该缺口不可由本候选入口离线通过抹去。此轮仅窄文档同步，不再次运行全树catalog/audit或应用验证。

root随后实际bootstrap PANEL_PILOT_002成功；`candidate_panel/PANEL_PILOT_002/bootstrap.json` SHAff200b03c4a45d32dce55c6ed08269305b4951da80321ed31e6368a5dfd930a1实际success/create_site/exact新map。初次remote因完整461KB打印超时，root只读小回执确认，未重派bootstrap。本Technical拥有该目录新增`root_preview_switch_payload_v1.py`（root显式执行的小回包诊断payload），`female_preview_request_v1.json`、`male_set_appearance_request_v1.json`、`PREVIEW_SWITCH_PAYLOAD.md`及`preview_switch_preparation_v1.json`。两请求从实际bootstrap catalog生成原衣发/完整sources，并经原validate_selection校验，选MOTION_CAND_001/front_full/landscape/production10/1.0s，female preview后male set_appearance直调闭包；小输出保留实际Body/38槽/followers和已有bound证据字段，不增加UE查询/MRQ或新验收门。payload仅语法编译及离线输入核验，本agent没有实际执行两步；实际成功/失败由后续reply确定，冻结主入口/配置及adapter字节不改。

上述两步随后均由root实际执行成功：`replies/PANELFEMALEPREVIEW001.json`为female preview，`replies/PANELMALEAPPEARANCE001.json`为male set_appearance闭包；实际各自Body均位于v2对应ID根、root38、各2个本次Delicate附属。真实remote为`panel_female_preview_0853_remote.json`、`panel_male_switch_0855_remote.json`；root已restore并仅保存新candidate map（`panel_restore_before_import_0858_remote.json`、`panel_save_candidate_only_0859_remote.json`），未保存正常场景。它证明候选面板与production闭包装配接线的这两条实际路径，不是正常/Scenes或正式生产激活；没有新增MRQ/用户最终或全40通过。当前继续离线准备显式40真实资料的版本化正常体系入口，原active/其他会话primary源码/冻结v2均保持。

新增本Technical实验owner `00_engine/outputs/character_refresh_20261018_v1/ue_refresh_existing_system_v1.py`（SHAafb7ec336b7a19e2c7f4e2fd29b97a1ff2b9f38bcf6f24810ac3a7f68ba86d46）和`test_refresh_existing_system_v1.py`；步骤`EXISTING_SYSTEM_REVISION_INTEGRATION.md`，离线验证`existing_system_validation_v1.json`及`existing_system_tests_v3.xml`（六项0.39秒）。未来精确输出scope `system_integration/`为版本bundle、显式正常场景白名单、原生产trial plan派生pin、私有endpoint回执及followers补充准备；只在真实40输入齐后生成，不预建空发布目录。其基础40配置复用`candidate_panel/<release_id>/`，本轮没有完整40 bundle/activation/publish或CC/UE调用。

该版本化入口复用现有UI/primary私有行为/production dispatcher，同一私有assembler proxy同时覆盖正常`/Game/Scenes`精确白名单及原production trial准备/渲染调用。六标准部件＋root38及两现用Skeleton不变，附属数读取实际mapping，normal预览transient、Capture副本persistent。每map独立装配缓存，所有派生Materials/Expressions/Followers/HairCoverage及切图Recovery副本只在`/Game/DataMake/Capture/CFD40Refresh20261018_v2/<release_id>/`，禁止保存正常源图或源网格/材质/骨架。生产trial沿原prepare/相机/Body轨/renderer policy，只补既有collect/save与新supplement最终pins，不改旧base记录、不加假geometry_pass。公开prepare/启动只允许原source40恰好40ID/20+20、真实成功mapping及同人Normal completed；当前两真实代表已作为负向输入确认在任何输出前拒绝，未造其余38成功。

正式默认active pointer、canonical assembler、旧独立40入口和其他会话primary源码均不改；最终交付应明确新版版本化launcher及生产调用配方，不能称所有旧脚本已全局替换。最小未来root实际步骤是正常源场景preview/set_appearance、一次既有切图与原production试片followers准备；未要求额外MRQ或新人物/衣发/动作矩阵。旧matched入口与资产完整保留，deactivate只清本版runtime refs不保存场景/加载关卡，输入失效亦可用旧缓存精确cleanup。正常/Scenes新接线实机及全40接受仍待真实资料和root调用，隔离pilot通过不替代该事实。此轮按root仅窄Technical同步，不重跑catalog/audit。

### 本run成熟阶段执行策略与已完成抽查（2026-10-18）

用户最新提速决策以 [BATCH_VALIDATION_POLICY_V1.md](../../../../../../00_engine/outputs/character_refresh_20261018_v1/BATCH_VALIDATION_POLICY_V1.md) 与 [batch_validation_policy_v1.json](../../../../../../00_engine/outputs/character_refresh_20261018_v1/batch_validation_policy_v1.json) 为本run执行依据。后续每人继续保留本人来源/素材绑定、实际几何与原保护件、CC最终四图（中性/闭眼、正面/侧面，核对实际睫毛）、完整FBX导出、骨架/材质记录及四Normal/八ORM源像素证明。非lash原13460点0.002mm限制及逐人逐素材具名原生704例外不放宽，缺图、警告图、漏件或实际失败不作通过。

动作、旧衣服、头发与MRQ复用已接受代表的同一运行路径，按批抽查，针对真实异常深入；不逐人重复代表级矩阵，也不临时增加固定抽查数量。未抽查者明确为未单独审查，不伪造七字段runtime接受记录，且该项未重复检查不再作为逐人执行前置阻塞。本策略替代上文历史“逐人runtime门”的后续执行解释；既有代表Gate、历史回执及其消费schema不改，不能为让旧状态检查显示通过而补造接受文件。批量控制器及精确进度由本run机器计划和Status记录，本次只更新Technical解释。

不搭建临时8人关卡。全40真实资产完成后，沿原审查体系执行最终5页×8人统一审查，保留原同group_index的AM/BM/LM/WM/AF/BF/LF/WF页内顺序；当前最终审查、整批接受、用户最终接受和正式发布均未完成。两共享Skeleton、根38以及本人实际mapping的2/4片附属睫毛合同保持，不将代表Delicate两片推广所有款式。

AM001属于已有的额外批抽查：[candidate_runtime_acceptance_v1.json](../../../../../../00_engine/outputs/character_refresh_20261018_v1/representative_runtime_reviews_v2/AM001_RUNTIME_V2_001/candidate_runtime_acceptance_v1.json) SHA`2274d208607087869f3ee27ba04c3bd6477a534fde840d820e01580145f72a2b`，现有`runtime_fact`已离线消费通过，45份实际evidence pins。root-agent实际看过有效头部中性、闭眼正侧面、修正取景的中性侧面、MOTION_CAND_001/1秒+smile旧衣发及无遮挡颈胸正侧面；本人38槽、两片Straight跟随routing/pose及眉妆保存后读回均有证据。左右视线驱动明确复用代表共享路径，不冒称AM001另做左右gaze。两张无效取景图不作为眼部/侧面验收依据；两MIC仅精确本人候选包保存，自动用途标志的确切Python字段未暴露，不编造读回。该记录是root-agent-reviewed最低候选功能门，非用户人工或最终接受；旧发卡片/dither、衣服/肩部低mip最终材质画质未评，Morph getter不单独等于渲染证明。

AM001的 [runtime_scene_saved_v1.json](../../../../../../00_engine/outputs/character_refresh_20261018_v1/representative_runtime_reviews_v2/AM001_RUNTIME_V2_001/runtime_scene_saved_v1.json) 记录独立候选地图已保存；[AM001_runtime_release_001_remote.json](../../../../../../00_engine/outputs/character_refresh_20261018_v1/AM001_runtime_release_001_remote.json) 实际success，bindings/dirty_content/dirty_maps均0。未新增冷地图/Texture重载或MRQ验证，不将已保存等同已冷重载。

AF001当前 [AF001_V2_BATCH_001/worker_status.json](../../../../../../00_engine/outputs/character_refresh_20261018_v1/representative_import_jobs/AF001_V2_BATCH_001/worker_status.json) 实际completed、ue_imported=true、shared_disk_and_readable_fields_unchanged=true；其 [AF001_NORMAL_DIRECTION_001/completed.json](../../../../../../00_engine/outputs/character_refresh_20261018_v1/skin_normal_direction_fixes/CFD40_AF_001/AF001_NORMAL_DIRECTION_001/completed.json) SHA`c697b055690ca3c0c0026422d3f3ea439f5ddcf21545eb0a466297e59b184057` 为本人四图方向修正实际completed，不据此自动写本人runtime视觉接受。后续人物单独几何完成不等于CC完整装配、导出或导入成品；动态完成计数及AF002当前阶段继续只由Status/执行记录拥有。本次未改代码、registry、catalog、冻结输入或应用状态，未重跑全树审计。

最终5×8独立构建入口归本Technical实验owner：同Run `ue_refresh_final5x8_review_v1.py`、`test_refresh_final5x8_review_v1.py`，步骤 [FINAL5X8_REVIEW_STEPS.md](../../../../../../00_engine/outputs/character_refresh_20261018_v1/FINAL5X8_REVIEW_STEPS.md)，窄验证`final5x8_validation_v1.json`/`final5x8_tests_v1.xml`。旧5×8只有六标准件，旧candidate panel仅单角色选择，pair脚本仅两人，因此新入口只连接原`page_cases`/4列×2行布局与已证明的`install_assembler`、实际2/4片mapping及save/restore；不改冻结入口或原registry。输出scope `final_review_5x8/<review_id>/configuration.json`只在原40实际完整输入核验后生成，派生关卡只在`/Game/DataMake/Validation/CFD40Refresh20261018_v2/FINAL5X8/<review_id>/Page01..05/`，沿用原`representative_follower_reviews_v2/`、`representative_scene_configs_v2/`和`representative_scene_restores_v2/`实际绑定、保存、重载证据。只保存明确列出的本页派生包和该页地图；导入MIC/Normal/Body/shared变脏不自动扩权。当前四项离线检查通过：原真实source40顺序、当前真实8人准备被拒且无配置输出、原布局控制、真实Straight两片/Dense四片既有mapping；未虚构正向40人运行，实际完整40配置/最终页/应用调用均0。最终统一审查待40完成后root执行，本入口存在不构成审查、用户接受或正式发布。此项只更新owner及步骤，不重跑全仓catalog/audit。

用户随后明确正常连续自动批处理、不逐人检查、报错或一批结束统一审查，以 [BATCH_VALIDATION_POLICY_V2.md](../../../../../../00_engine/outputs/character_refresh_20261018_v1/BATCH_VALIDATION_POLICY_V2.md) 及`batch_validation_policy_v2.json`替代上述常规逐人检查节奏。保留逐人数字检查、source-bound最终四图捕获、完整导出和骨架/材质/源像素证据，但图片捕获、数值通过和视觉待批审分别记录；逐人root看图批准不再作为普通CC至export前置，未审者不伪造visual/runtime通过。原代表及AM001真实root-agent观察记录保留，最终5×8/用户接受/formal发布另列。代码实现或当前计数仍由真实执行回执和Status拥有，授权本身不等于已启动连续执行。

新增本Technical实验owner：`run_refresh_ue_continuous_v1.py`、`test_refresh_ue_continuous_v1.py`，步骤 [UE_CONTINUOUS_QUEUE_STEPS.md](../../../../../../00_engine/outputs/character_refresh_20261018_v1/UE_CONTINUOUS_QUEUE_STEPS.md)，验证`ue_continuous_validation_v1.json`及最终冻结`ue_continuous_validation_v2.json`/`ue_continuous_tests_v4.xml`；v1测试fixture缺临时request的失败XML保留，当前六项窄检查通过。`continuous_ue_existing9_v1.json`逐项只读核验真实九份已完成import/audit和Normal回执，测试使用同九份真实ready源确认全部skip，不模拟应用成功。新协调输出scope `continuous_ue_v1/<run_id>/`含不可变配置、mutable progress、独占lock/边界stop请求、逐人quality与Normal remote原回包；只消费CC控制器append-only `ready_for_ue`的本人真实CC源/manifest/inventory pins，要求`cfd40_refresh_cc_continuous_progress_v1`，无inflight时上游failed/error停，stopped_no_new_submissions在当前人结束后停，批数值登记pending只等待不当失败或新增审批。严格原import.prepare→四Normal/八ORM quality通过→原submit/status→真实audit→Normal generic v2→下一人；pending读同request不重派，派发后仍prepared或明确失败则停，不误入Normal。两已知材质弹窗仍由root操作，非免弹窗；target exact node/user/project及uproject/PID沿原入口核实，所有写入只限原v2候选/四Normal及其rollback，不改共享Skeleton或既有冻结入口。advance仅离线准备且与run同锁，stop只在边界停、不kill在跑worker；不确定socket结果只等待真实同job回执。此实现冻结时实际连续配置/运行/应用调用均0，待root启用，未因协调器存在增加导入数字或视觉接受。此次仅窄owner更新，无全仓catalog/audit。

Root随后指定真实CC progress后，`continuous_ue_v1/RUN40A/configuration.json`已离线prepare；`offline_preparation_v1.json`保存该checkpoint的progress快照与pins。实际七条CC ready行通过同源核验，九份历史import/Normal均真实skip，状态`waiting_CC_ready`、current=null、没有新import request或应用调用；仅完成配置准备，不是已启用或新增人物完成。CC progress属于append-only可增长源，其checkpoint SHA不当永久内容pin；配置中冻结的是显式路径、原source40与实现/target/已有完成输入。后续实际启用和数字由root执行回执/Status拥有，不因本离线prepare提升视觉/用户接受。

CC上游恢复后，旧`continuous_cc_v1/progress.json`保留真实failed历史，未启用的RUN40A由新`continuous_ue_v1/RUN40B/configuration.json`替代；A配置/进度原件不改。B仅将显式live上游改为`continuous_cc_recovery_v2/progress.json`，继续使用相同target与`continuous_ue_existing9_v1.json`，冻结UE代码不变。B的`offline_preparation_v1.json`记录实际七条ready pins与A相同、九份真实完成仍skip，`waiting_CC_ready/current=null`、无新request/应用；它同时pin被替代A配置与旧failed上游作为历史说明。此为新的离线准备checkpoint，非B已启动或新增人物导入通过。

本Technical补充离线批数值复核输出owner：`native704_AF003_AF004_registry_draft_v1.json`、`AF003_AF004_NUMERIC_REVIEW_V1.md`、`AF004_numeric_cc_build_failed_attempt_v1.json`及`AF003_AF004_numeric_receipts_offline_build_v1.json`。草稿保持未登记；root另行登记的`native704_AF003_AF004_registry_registered_v1.json`（SHA9271a87d5cef9de2bdeeab418fbb59e4a9784bdbd018141176b6579b31c42e3d）仅授权各本人source/asset/原704，AF003上界9.65mm、AF004上界8.45mm；原13460非lash仍0.002mm、实际两人均0.00081999355669464mm。随后复用Assembly owner的既有numeric builder，离线产出精确`batch_cases/CFD40_AF_003/numeric_cc_v2/`与AF004对应目录的技术completed CC receipt/transfer manifest，非正式生产接受。AF004首试实际Input SHA门失败且未建输出目录，失败记录保留；root确认输入静止barrier后原门单次重跑通过，无pin修改或豁免，原因仍未知、并发瞬态可疑而非已确诊dispatcher。重跑前后AF004 serial state与live progress SHA实际不变；未调用控制器、CC或UE。当前仅本人CC技术导出源就绪，新增lash UV沿既定完整FBX核验边界pending，complete_export_verified/UE_imported仍false、visual_review仍pending_batch_review。完整源哈希和产物pins以离线build记录（SHA672dc30394482b4db57070766054c78597bc7afe8c604d8e97d92657a6fbb5dc）为准，实际后续export由唯一CC owner在root调度下消费原registry/已存在manifest，不重建或覆盖回执。

## 9. 显式原生网格名与FBX名称兼容（2026-10-19）

本节拥有以下新增Run脚本，均为本Technical的候选实现，不是正式生产入口；精确仓库路径与生命周期如下。它们保留原importer、quality、Normal v2及连续UE协调器源码和全部旧配置/请求pins，不修改正在运行的CC控制器、dispatcher或人物状态。

| 仓库路径 | 生命周期 | 本Technical实现职责 |
|---|---|---|
| `00_engine/outputs/character_refresh_20261018_v1/ue_refresh_representative_import_alias_v1.py` | `experimental` | 私有加载SHA锁定的原importer，显式处理本人实测CC mesh/AvatarPart owner到FBX名字的唯一合法视图；prepare、checked_request与远程execute共用规则 |
| `00_engine/outputs/character_refresh_20261018_v1/build_skin_export_quality_alias_v1.py` | `experimental` | 原quality主体仅替换request verifier入口，继续真实四Normal/八ORM比较及同源约束 |
| `00_engine/outputs/character_refresh_20261018_v1/ue_refresh_skin_normal_direction_alias_v1.py` | `experimental` | 私有复用Normal v2，消费同一兼容import request；原四包备份、方向写入、读回和可恢复journal不变 |
| `00_engine/outputs/character_refresh_20261018_v1/run_refresh_ue_continuous_alias_v1.py` | `experimental` | 私有组合原coordinator与上述三个入口，准备、实际导入及Normal路径一致；拒用未由此入口新建的配置 |
| `00_engine/outputs/character_refresh_20261018_v1/test_source_name_alias_v1.py` | `utility` | 针对此次名称映射的三个离线回归，不调用应用或构造真实target |

真实BF002的SDK mesh名为`Lash_Low_Extend`，同一片owner为`avatar/9:Lash_Low_Extended`，实际FBX使用对象名`Lash_Low_Extended`。原精确名称门因此拒绝，并非漏件。新视图只允许已由原canonical registry/receipt/capture/snapshot核验的`CCAPP_EYELASHES_284c3a142668`、素材SHA`2b33d19afce6c84ebf87f6974033bc6c68c860fa17b60851590dc42a8ab8ad89`及这一精确owner/name对应；不提供任意名字忽略或跨素材映射。返回合同的`added_parts.name`是FBX名字，`native_mesh_name`保留SDK名字，`source_name_aliases`绑定真实capture/native snapshot与owner；原CC文件和回执不重写。

名称视图之后，原`source_expectations`仍逐件验证实际FBX。BF002这片2360点、2068个三角按原规则重组成1034个CC quad，完整消耗、winding、indices及还原拓扑SHA均与本人capture相等；不存在改顶点、重排索引或新hash常量豁免。该同源规则也已真实用于BF005。原失败证据独立保留于 [BF002_original_source_name_gate_failure_v1.json](../../../../../../00_engine/outputs/character_refresh_20261018_v1/BF002_original_source_name_gate_failure_v1.json)。

[source_name_alias_composition_validation_v1.json](../../../../../../00_engine/outputs/character_refresh_20261018_v1/source_name_alias_composition_validation_v1.json)（SHA`f2efbb1b41d4f9514e3291a67cff63c94eb6f27f646afcc17e52ec389735233d`）拥有四新入口及原实现未变的精确pins。原importer/quality/Normal v2/coordinator仍分别为`4cae1e57…`、`d0ab4a19…`、`2647004f…`、`0cff1939…`。已有 [source_name_alias_tests_v1.xml](../../../../../../00_engine/outputs/character_refresh_20261018_v1/source_name_alias_tests_v1.xml) 记录3项通过、5.29秒：真实BF002名称视图与拓扑门、错误asset/owner/碰撞及变更几何拒绝、实际私有coordinator到import/quality/Normal的入口一致且旧配置拒用。此处只登记已完成测试，未新增应用试验或重跑全仓检查。

本轮新增输出同归本Technical候选取证所有权：[BF_group_ue_offline_readiness_v1.json](../../../../../../00_engine/outputs/character_refresh_20261018_v1/BF_group_ue_offline_readiness_v1.json)、`BF001_ue_offline_readiness_v1.json`至`BF005_ue_offline_readiness_v1.json`、各本人`batch_cases/CFD40_BF_00N/actual_full_fbx_source_audit_v1.json`和`skin_export_quality_v1.json`、上述failure/validation/JUnit，以及 [RUN40C_offline_inputs_v2.json](../../../../../../00_engine/outputs/character_refresh_20261018_v1/RUN40C_offline_inputs_v2.json)。BF五人的完整导出源门、118骨、本人全部新增片、四Normal文件/像素与八ORM分量均已通过；Dense为标准6＋4片、4035源Morph，其余四人为6＋2片、3245源Morph。新增UV只证明实际FBX数组有限且索引覆盖完整，不宣称CC到FBX逐值UV相等；CC/导出state前后SHA不变，视觉仍待批审。

此离线checkpoint将旧8人与BF5合成13待导入，复用旧9份已完成import/Normal认证；实际UE完成仍9，新target为空、RUN40C配置数0、import请求数0、应用调用0。旧8人源审计/像素比较未重复，`RUN40C_offline_inputs_v1.json`与旧RUN40B配置/进度保持原字节。动态总进度由Status和执行记录拥有，不能把13个离线候选当作已导入或用户接受。

下一次实际RUN40C必须使用`run_refresh_ue_continuous_alias_v1.py`，不能继续用旧coordinator准备后只在离线审计中替名字。真实新UE target取得后，沿该入口的`--prepare RUN40C --ready-progress <当前真实CC progress> --existing <continuous_ue_existing9_v1.json> --target <真实新target.json>`创建独占配置，再用同入口`--configuration <RUN40C/configuration.json>`离线推进，root启用时才加`--run`。本checkpoint上游是`continuous_cc_user_restart_recovery_v7/progress.json`；若唯一CC owner后续迁移，须在prepare前选择真实新路径，不能编辑已准备配置。现有13份quality可原字节、独占复制到`continuous_ue_v1/RUN40C/cases/<ID>/skin_export_quality_v1.json`，协调器仍在实际提交前检查同源质量；无副本时新quality入口亦使用相同兼容request verifier。原pending同请求不重派、目标实例核验、共享Skeleton保护、四Normal rollback、边界stop/lock及root确认两材质弹窗语义不变。目录仍复用`continuous_ue_v1/<run_id>/`与现有import/Normal输出scope，不晋升formal、不新增验收矩阵或保留授权。

随后LM组仅新增LM001、LM003、LM004、LM005的离线准备，原LM002代表及旧13人不重复源审计或像素比较。新增 [LM_group_ue_offline_readiness_v1.json](../../../../../../00_engine/outputs/character_refresh_20261018_v1/LM_group_ue_offline_readiness_v1.json)（SHA`e3749370292c02be5a9e63da433f69cc9854d38767b1b56da4f3cc3fda1dd4d5`）、`LM001_ue_offline_readiness_v1.json`、`LM003_ue_offline_readiness_v1.json`、`LM004_ue_offline_readiness_v1.json`、`LM005_ue_offline_readiness_v1.json`及各本人`batch_cases/<ID>/actual_full_fbx_source_audit_v1.json`/`skin_export_quality_v1.json`继续归本Technical候选取证所有权。四人均已通过原完整源门：标准6＋本人2片、118骨、Body14164点、3245源Morph，原拓扑等价与实际FBX UV有限/完整索引、四Normal源字节像素及八ORM分量精确；LM003沿同一已冻结兼容入口处理实证Extend→Extended，未增名称例外或放宽几何门。

新独占 [RUN40C_offline_inputs_v3.json](../../../../../../00_engine/outputs/character_refresh_20261018_v1/RUN40C_offline_inputs_v3.json)（SHA`66e6d0c8eda2dac7c58159ada79a8a9b31ca4f470535bf7d60bdb2ffd01b834c`）链接原v2清单并扩为17待UE，复用旧9完成证明，原v1/v2与RUN40B均不覆盖；下一次仍必须使用上述alias coordinator，quality原字节复用规则同样适用于新增四人。此组末实际CC ready24＋两代表对应26份完整导出，实际UE仍9，新target为空、RUN40C配置/请求/应用调用均0；数字仅为本组取证checkpoint，动态进度由执行记录/Status拥有。本人serial/export state前后SHA均未变；本次未修改CC控制器或冻结源码，也未增加测试、重复旧人检查、启动应用或提升视觉/用户/formal接受。UV边界和批审策略保持原范围。

LF组随后仅检查新增LF001–005，沿上述冻结alias组合及原完整源/quality实现，未重复旧17人的审计、像素比较或测试。输出 [LF_group_ue_offline_readiness_v1.json](../../../../../../00_engine/outputs/character_refresh_20261018_v1/LF_group_ue_offline_readiness_v1.json)（SHA`bcbe1d795749cbc75e666d551e0800260949622c75cdbd30b3a63ebf4148d251`）、`LF001_ue_offline_readiness_v1.json`至`LF005_ue_offline_readiness_v1.json`，以及本人`batch_cases/CFD40_LF_00N/actual_full_fbx_source_audit_v1.json`和`skin_export_quality_v1.json`均归本Technical候选取证所有权。五人原门全部通过：118骨、Body14164点、标准6部件与本人完整新增睫毛、实际拓扑/有限UV索引完整、四Normal文件/像素与八ORM分量精确；LF002和LF005为10件/4035源Morph/4片睫毛，其余三人为8件/3245源Morph/2片。各本人serial/export state前后SHA未变；仍不宣称CC到FBX逐值UV相等或运行时视觉接受。

新独占 [RUN40C_offline_inputs_v4.json](../../../../../../00_engine/outputs/character_refresh_20261018_v1/RUN40C_offline_inputs_v4.json)（SHA`7b9d33dca51b1e5ba3df6ef09bdb8282843b02c0a4b094e34a1b0ac56eabaf87`）链接原v3、保留旧17条并新增LF5，共22待UE；旧9完成证明与全部旧清单/RUN40B保留。按root指定，其ready路径及未来命令同步为`continuous_cc_WM001_presubmit_recovery_v8/progress.json`（本次源快照29 ready＋两代表＝31份完整导出）；读取快照时该progress已为`stopped_no_new_submissions`，这是调度历史状态，不推翻已完成导出源。真正启用前仍须由root选择唯一CC owner的真实可用上游，不能绕过coordinator的上游停止门或修改已准备配置。实际UE仍9，target为空、RUN40C配置/请求/应用调用均0；下次入口仍强制`run_refresh_ue_continuous_alias_v1.py`，本人质量原字节复用和所有原保护不变。本轮未修改冻结脚本、CC控制器或应用，不增加验收门或正式发布结论；动态数字由执行记录/Status继续拥有。

WM组随后仅完成新增WM001–005的同型离线源审计和quality，旧22条及旧9完成证明直接复用。新增 [WM_group_ue_offline_readiness_v1.json](../../../../../../00_engine/outputs/character_refresh_20261018_v1/WM_group_ue_offline_readiness_v1.json)（SHA`1f693b918f32bd67a6f00b5cdf8b15145fb8b59a48ebe6cbe97cf3e0076aa8d9`）、`WM001_ue_offline_readiness_v1.json`至`WM005_ue_offline_readiness_v1.json`及本人`batch_cases/CFD40_WM_00N/actual_full_fbx_source_audit_v1.json`/`skin_export_quality_v1.json`继续归本Technical候选取证所有权。五人均通过冻结alias组合下的原门：8件、118骨、Body14164点、3245源Morph、标准6＋各本人2片实际睫毛、拓扑等价与有限/完整FBX UV索引、四Normal字节像素及八ORM分量精确；本人serial/export state前后SHA未变，不将UV有限性提升为CC到FBX逐值一致或视觉接受。

新独占 [RUN40C_offline_inputs_v5.json](../../../../../../00_engine/outputs/character_refresh_20261018_v1/RUN40C_offline_inputs_v5.json)（SHA`eb3aba1408ee0e1104ac50c6f4cba3d31d4d1dcc99cd6d563520c3a1e413fa99`）链接原v4并扩为27待UE，旧22条/所有旧版本/RUN40B不覆盖；target为空、RUN40C配置/请求/应用调用均0，实际UE仍9。本次ready34＋两代表对应36份完整导出；指定v8 progress的读取快照为`failed`，root报告停在WF001提交前junction故障、由唯一geometry owner恢复，本组没有触碰其文件或运行状态。v5显式记录`startup_requires_owner_actual_recovered_progress=true`：未来真实prepare必须使用owner届时实际恢复的可用上游及新UE target，仍经alias coordinator的原失败/停止/实例保护，不因本离线清单绕门。只检查新组、未重复旧人或测试、未改变冻结脚本/控制器/资产，不增加验收或发布范围；后续动态计数以Status/执行记录为准。
