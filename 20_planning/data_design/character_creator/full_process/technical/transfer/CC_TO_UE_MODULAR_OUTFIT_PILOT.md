# CC 到 UE 模块化服装 Pilot

> 文档 ID：`TECH-TRANSFER-04`
> 文档类型：`technical`
> 生命周期：`current`
> 适用阶段：`WF-30/WF-40/WF-50`
> 实现所有权：模块化服装 Pilot 的 CC 工单、双形态 Bundle、UE 分离导入和可恢复执行
> 验证所有权：`VAL-TRANSFER-01`（Pilot 作用域）、`VAL-UE-02`
> 输出契约：`OUT-WF40-TRANSFER-BUNDLE`、`OUT-WF50-RUNTIME-ACCEPTANCE`
> 运行环境：CC5 离线会话、系统 Python、UE 5.8 Editor Python、Auto Setup 2.03
> 最近核验：2026-10-05（固定头型发型小样与恢复实现核对）

## 1. 能力与边界

本流程验证“无服装基础身体作为动画 Leader，服装以独立 Skeletal Mesh Component 在 UE 中切换”的实现路径。当前只覆盖 `M02_Average` 和 `F02_Average` 两个平均体型。旧 14-Case 静态转移和 v002 限定运行时 Gate 是已接受历史基线，已退出执行入口；当前全库资产由正式 UE 单文件索引和 v003 消费。它不替代第一批 32 个烘焙 FullReference Look，也不能外推到其他体型或所有发型适配。第 10–11 节已覆盖平均体型全库转移、去冗余、正式索引与现用审查；最新编辑器接入与视觉范围见运行时 3.6–3.7 和 WF-50。

CC 必须由用户按离线要求启动；Agent 不启动或重启 CC。CC 重启后必须重新通过 Bridge Heartbeat/Ping，旧 Heartbeat 不能作为当前会话证据。完成 CC Bundle 后，UE 导入、Blueprint 构建和机器验证不再依赖 CC 在线。

## 2. 历史 14-Case 冻结范围

机器输入为：

```text
00_engine/scripts/character_creator/cc_modular_outfit_pilot_source_v1.json
00_engine/scripts/character_creator/cc_modular_outfit_pilot_20260829_v1.json
00_engine/scripts/unreal/ue_modular_outfit_pilot_manifest_20260829_v1.json
```

历史 Pilot 共 14 个 Case：2 个无服装基础身体和 12 个服装 Case；覆盖普通分件、衬衫加外套、可选外套、单件 Full-body、锁定 Bundle、Family 局部配件、共享鞋、赤脚切换、裙装和集成鞋。精确 Case、模块、哈希、`cloth_options_policy` 和允许的 Runtime Variant 只从上述 Manifest 读取，不从目录名推断。

## 3. 双形态转移契约

每个服装 Case 保留两种互补表示：

| 表示 | 内容 | 用途 |
| --- | --- | --- |
| FullReference Witness | 身体、服装、材质和 JSON 完整导出 | Auto Setup 材质来源、CC 视觉基准、错误追溯 |
| Split Modules | 同一 Case 的独立 Skeletal Mesh | 绑定基础身体 Skeleton，作为 UE 服装 Follower |

基础 Case 只导入 FullReference，并提供身体 Skeletal Mesh 与规范 Skeleton。Split 导入产生的身体、眼、牙、舌等重复网格必须被分类器忽略；只有 Manifest 模块映射命中的服装网格进入 Runtime Plan。不得按 FBX 中网格顺序猜测服装槽位。

## 4. 历史实现所有权与调用次序

以下文件解释旧 Pilot 的来源，不代表可继续运行该冻结工单。当前执行入口在第 10–11 节；两个 v2 UE 模块保留共享 helpers，旧独立 main 已退休。早期 `00_engine/scripts/unreal/ue_interchange_split_pilot.py` 无当前消费者，顶层导入/保存逻辑已整体拦截，不能通过直接执行或 import 重建已退役资产。

| 顺序 | 文件 | 责任 |
| --- | --- | --- |
| 1 | `00_engine/scripts/character_creator/cc_build_modular_outfit_pilot_v1.py` | 校验 Family、鞋池和源资产，编译 14-Case CC 工单 |
| 2 | `00_engine/scripts/character_creator/run_modular_outfit_pilot_export.ps1` | 检查 CC/Bridge，会话内提交受控导出作业并拒绝覆盖 Run Root |
| 3 | `00_engine/scripts/character_creator/cc_validate_body_reconstruction.py` | 在 CC 中重载基础项目、装配模块、保存 `.ccProject` 并导出 FBX/JSON |
| 4 | `00_engine/scripts/character_creator/cc_finalize_modular_outfit_pilot_v1.py` | 把成功结果和文件哈希写回 UE Runtime Manifest |
| 5 | `00_engine/scripts/unreal/run_modular_outfit_pilot_import_v1.py` | 编排可恢复的 UE `preflight/reference/split/materials/validate` 阶段 |
| 6 | `00_engine/scripts/unreal/ue_modular_outfit_pilot_import_v1.py` | 在 UE 中导入、绑定基础 Skeleton、分类模块并写逐 Case 报告 |
| 7 | `00_engine/scripts/unreal/modular_outfit_runtime_plan_v1.py` | 从已验证导入报告编译候选网格与 Variant 分类基线 |
| 8 | `00_engine/scripts/unreal/modular_outfit_runtime_plan_v2.py` | 把分类基线编译为固定语义槽、Bundle 池和逐 Variant 网格赋值 |
| 9 | `00_engine/scripts/unreal/run_modular_outfit_runtime_v2.py` | 编排 v002 Blueprint、切换矩阵、临时 Stage 和 Review Level |
| 10 | `00_engine/scripts/unreal/ue_build_modular_outfit_runtime_v2.py` | 构建 Body Leader、空复用槽，按需加载/清空网格并验证切换 |
| 11 | `00_engine/scripts/unreal/ue_modular_outfit_motion_validation_v1.py` | 提供已验证的同性动作资产与 Skeleton/姿态变化证据 |
| 12 | `00_engine/scripts/unreal/ue_build_modular_outfit_review_level_v2.py` | 创建 v002 独立人工复核关卡，不修改生产场景 |

## 5. 历史 CC 执行证据

14-Case 工单已完成，不再按旧命令重新导出。接受的 CC 证据为 `%OUTPUT_ROOT%/character_creator_bridge/artifacts/modular_outfit_pilot/run_20260830_v3/`，冻结结果为 14/14 成功。历史工单与成功报告不改写；已替代二进制和 staging 副本的物理保留、规范来源及重放映射由本轮 `cc_audit/` 清单和回执说明。

当前新增衣柜/发型的 CC 输入必须使用其现用规范清单，并重新检查离线会话 Bridge；不能从旧 14-Case 工单、历史 Heartbeat 或已退役报告根恢复队列。平均体型 BASE 的规范项目仍保留。

## 6. 历史 UE 导入与保留 BASE

旧 12 个服装 Case、P0、单发型 ScalpHairPilot 和 v001/v002 执行资产已经有正式替代入口，旧重建命令不再提供为现用示例。历史 FullReference/Split 报告与骨骼/材质映射是追溯见证，不能用其中的旧对象路径查找当前衣柜；当前对象路径从正式 UE 索引读取。

`/Game/Vendor/Reallusion/CC5/ModularOutfitPilot/{F02_Average,M02_Average}/Cases/{F_BASE,M_BASE}/` 仍保留规范 Body、Skeleton 及被引用的支持资产。这个目录名称含 Pilot 并不表示整个树可以删除。现用 v003 与全部模块网格继续复用这些 Skeleton，不能把清理扩成重建或替换骨骼。

## 7. 历史静态通过条件与证据

`VAL-TRANSFER-01` 的 Pilot 作用域要求：

1. 14/14 FullReference Witness 可加载且 Auto Setup 材质完整；
2. 12/12 Split Case 均产生可分类服装网格；
3. 所有服装网格绑定对应基础身体 Skeleton；
4. Split 服装不创建独立 PhysicsAsset，不夹带未允许的材质、纹理、动画或 Skeleton；
5. Runtime Plan 中的每个模块都能解析为唯一 Skeletal Mesh。

当前报告根为 `%OUTPUT_ROOT%/unreal_character_import/modular_outfit_pilot_20260829_v1/`。机器结果为 14/14 FullReference、12/12 Split、112 个 Split Skeletal Mesh、0 Skeleton mismatch、0 empty mesh 和 0 Split PhysicsAsset。v002 在同一根目录下保留 `runtime_plan_v2.json`、`runtime_v2/` 机器报告和人工动态验收；它不会重新导入 CC Bundle。静态转移和 v002 限定运行时 Gate 均已关闭，精确边界见 [UE 角色运行时](../unreal/CHARACTER_RUNTIME.md#3-模块化服装-pilot)。

## 8. 输出与保留

- CC 成功 Run、最终 Runtime Manifest 和 UE 聚合报告：`retained_evidence`。
- 现用规范 `.ccProject`、FBX、JSON 和纹理 Bundle：保留当前导出来源；历史 Pilot 被替代副本按精确清单收敛，冻结工单与恢复映射继续保留。
- 失败 Run、临时 Stage Actor 和早期诊断报告默认不自动删除；必须经 Output Inventory 和替代关系审查。
- 现用 Review Level 是人工复核入口；旧关卡有现用替代且引用解除后可退休，保留其有效人工决定与装配报告。

## 9. 恢复与限制

- CC Heartbeat stale 时停止 CC 阶段并由用户重新离线启动；不由 Agent 启动或重启。
- UE 自动化账户必须把 `-ShaderWorkingDir` 和 `-ZenDataPath` 指向可写本地目录，否则 Shader 编译线程可能因默认用户目录不可写而退出；这不表示保存的 Blueprint 或关卡损坏。
- `cleanup` 只用于精确 Case 的已审查重试，不作为常规阶段，也不得删除用户生产资产。
- 当前未关闭：人工穿模、身体隐藏面、布料物理、LOD 同步、头发/兜帽兼容和 Morph 视觉传播。

## 10. 平均体型衣柜扩展

本节是 2026-09-06 开始的全服装转移实施入口，复用已验收的 v002 槽位系统，而不是重新建立一份按候选服装增加组件的 Blueprint。精确进度见 [WF-40 状态](../../project_management/status/workflows/WF-40.md)。导入成功只证明资产可用，不能代替用户的合身检查。

### 10.1 来源与去重边界

输入为 `D:\BaiduNetdiskDownload\人物和服装_newest50pct_sorted` 的 `male/female` Family JSON，以及当前共享鞋库。只使用 M02_Average、F02_Average 两个已验证基础项目。相同源文件哈希、性别、槽位与 Conform 策略的部件只导出一次；原 Family 的组合规则、鞋池和配件约束保留在 Registry，不因去重扩大兼容范围。锁定 Bundle 一起导出，不拆成可任意穿搭的单件。

2026-09-08 用户批准 Elise 仅保留 `4.ccCloth`，排除与它互斥的 `2.ccCloth`，其余必需组件不变。当前扩展库采用 `manifests/v3/`；原 `v2/` 保留作来源与已成功批次证据，不再用于创建新的全库导出任务。只有 Elise 的 Family 规则由 v3 的 `family_contracts/female.elise.json` 覆盖外部旧 JSON，外部源文件未修改或删除。迁移、精确命令与复用边界见 [第10.9节](#109-用户批准的锁定套装修订)。

仅有 `.ccGloves` 扩展名不被现有加载器接受时，在工作区创建字节相同的 `.ccCloth` 兼容别名，记录原路径及 SHA256；不改原始资产。单件导出工单只是转移单位，不代表允许角色仅穿该部件。生成衣柜 Runtime Variant 时仍须按原 Family 规则补齐其他部件。

### 10.2 程序和执行次序

1. `00_engine/scripts/character_creator/cc_build_wardrobe_library_v1.py` 验证来源、计算哈希、去重，生成完整 `wardrobe_registry.json`、`cc_export.json`、待完成的 `ue_import.json`。使用新的 `--output-dir`，不覆盖旧工单。
2. `00_engine/scripts/character_creator/cc_prepare_wardrobe_batch_v1.py` 从完整库按 `--unit-id` 提取小批工单，拒绝已存在的导出路径。需要多个导出单位时重复传入 `--unit-id`。
3. 用户离线启动 CC 后，`00_engine/character_creator_bridge/cc_bridge_client.py validate-bodies` 调用 `cc_validate_body_reconstruction.py` 装配、保存项目、导出 FBX/JSON/纹理。Agent 不启动或重启 CC；CC 导出和 UE 导入分阶段执行，不同时提交重任务。
4. 对成功结果执行 `cc_prepare_wardrobe_batch_v1.py --finalize-result <validation_result.json>`，调用既有 Finalizer 补齐真实文件哈希和场景对象映射；加入只读复用的 M_BASE/F_BASE。
5. `run_modular_outfit_pilot_import_v1.py --manifest <batch/ue_import.json> --report-root <batch_report_root>` 依次执行 `preflight`、`reference`、`split`、`materials`、`validate`。非 preflight 阶段必须显式选择服装 `--case-id`，不能选择复用基础身体；reference 增加 `--auto-dialogs`，每次最多三件并在失败时停止。
6. `00_engine/scripts/unreal/validate_wardrobe_import_batch_v1.py --manifest <batch/ue_import.json> --report-root <batch_report_root>` 核对四阶段报告身份及成功状态、Finalize 后文件哈希，复用 `modular_outfit_runtime_plan_v1.py` 的场景对象分类器。生成 `wardrobe_modules.json`，记录每个 CC 部件对应的 UE 网格和忽略的重复身体；另查空网格、骨骼和意外 PhysicsAsset。成功后才把新部件交给 v002 装配和人工静态/动作检查；未经检查的候选不标记 `runtime_approved`。

示例命令从 `%LANCE_ROOT%` 执行，路径变量指向本轮实际工单，不使用固定 14-Case 的旧 PowerShell 包装器：

```powershell
$library = 'D:\UE\exports\character_creator\wardrobe_average_20260906_v1\manifests\v2'
$batch = Join-Path $library 'batch_002'
python 00_engine/scripts/character_creator/cc_prepare_wardrobe_batch_v1.py --library-dir $library --batch-dir $batch --unit-id '<unit_id>'
$evidence = 'D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts\wardrobe_average\<new_run_id>'
$transport = Join-Path (Get-Location) '00_engine/scripts/character_creator/runtime_staging/<new_batch_id>'
New-Item -ItemType Directory -Path $transport -ErrorAction Stop | Out-Null
Copy-Item -LiteralPath "$batch/cc_export.json" -Destination "$transport/cc_export.json"
if ((Get-FileHash "$batch/cc_export.json").Hash -ne (Get-FileHash "$transport/cc_export.json").Hash) { throw 'CC manifest copy differs' }
python 00_engine/character_creator_bridge/cc_bridge_client.py validate-bodies --library-file "$transport/cc_export.json" --output-dir $evidence --confirm-scene-replace --auto-dismiss-undo-warning --job-id '<unique_job_id>' --timeout 21600
python 00_engine/scripts/character_creator/cc_prepare_wardrobe_batch_v1.py --library-dir $library --batch-dir $batch --finalize-result "$evidence/validation_result.json"
$report = 'D:\UE\Lance_Work\00_engine\outputs\unreal_character_import\wardrobe_average_20260906_v1\<batch_id>'
python 00_engine/scripts/unreal/run_modular_outfit_pilot_import_v1.py --manifest "$batch/ue_import.json" --report-root $report --phase preflight
python 00_engine/scripts/unreal/run_modular_outfit_pilot_import_v1.py --manifest "$batch/ue_import.json" --report-root $report --phase reference --case-id '<unit_id>' --auto-dialogs
# Repeat for split, materials and validate, without --auto-dialogs.
```

完整主库的 `ue_import.json` 是 pending 模板，不能直接拿它作为已完成导出的证据。UE 只消费逐批 Finalize 后的工单。导入重试先查对应阶段报告和已有 UE 资产，不盲目重新提交 reference，也不删除整个衣柜目录。

本导入器为每个 reference 启动的精确弹窗守护最多等待 3600 秒，两个已知面板处理完成后提前退出；这是为大型 FBX 的解析等待留余量，不是扩大可自动点击的弹窗范围。正在运行的旧进程不会自动采用代码修改，应继续检查它的阶段报告，不重复提交导入。

衣柜作用域每个 reference/split 完成并保存报告后，Worker 请求 Python 和 UE 对无引用对象做垃圾回收，记录 `post_import_gc_requested`；不删除资产、不重启 CC，也不承诺释放所有编辑器缓存。仍须观察系统提交余量，必要时在已保存的小批之间正常重启 UE。正在执行中的单件不会中途改变代码，下一次远程 Worker 调用才使用新版本。

窗口黑屏或长时间不刷新时，不单凭 `Responding` 判断成功或死锁。先读 `%UE_PROJECT_ROOT%/Saved/Logs/datatry_02.log` 的当前 Case、FBX Translation/网格构建阶段，间隔采样对应 UE PID 的累计 CPU 时间，并检查物理内存和提交余量、是否存在明确的阻塞弹窗。2026-09-06 的女性短裤 Split 曾在 FBX Translation 阶段耗时约 10 分钟，随后成功进入构建；构建时出现内存估计超过可用额度的警告。该实例证明界面停顿不等于停止计算，但不能据此保证每次等待都会成功。

导入未结束时不再提交第二个远程导入、不强制关闭 UE。当前阶段完成后核对成功报告及脏包，再决定下一阶段或正常重启 UE；若退出则检查进程消失和 `LogExit: Exiting`。CC 只能由用户离线启动，不能用重启 CC 作为自动恢复手段。当前 FullReference 和 Split 都会处理源 FBX 中的完整身体，因此全库扩展前须评估重复身体解析/构建开销，不能凭单件成功直接承诺批量耗时。

完整 Registry 保留编译时的 pending 初态，不靠覆盖原始编译清单来记录进度；已完成单位以逐批导出报告、`wardrobe_modules.json` 和 WF-40 当前状态为准。

### 10.3 输出位置、内容与用途

| 位置 | 内容与作用 | 保留要求 |
| --- | --- | --- |
| `%CC_EXPORT_ROOT%/wardrobe_average_20260906_v1/manifests/v3/` | 当前完整 Registry、去重映射、逐批工单；`revision.json` 记录 v2 来源哈希与复用关系，`family_contracts/` 保存批准后的 Elise 规则 | 当前权威输入，不删除；v2仍作为被引用的冻结来源保留 |
| `%CC_EXPORT_ROOT%/wardrobe_average_20260906_v1/{Male,Female}/Average/<family>/<category>/<unit>/` | `.ccProject` 与 `fbx/` 下的 FBX、JSON、贴图，支持后续重导和来源核对 | 权威二进制，不删除 |
| `%OUTPUT_ROOT%/character_creator_bridge/artifacts/wardrobe_average/<run>/` | `progress.json`、`validation_result.json`、逐单位装配与导出报告 | 保留追溯证据 |
| `%OUTPUT_ROOT%/unreal_character_import/wardrobe_average_20260906_v1/<batch>/` | 预检、Witness、Split、材质映射与静态验证报告；`wardrobe_modules.json` 是通过转移检查的实际网格映射，供后续运行时接入；失败阶段也保留 | 保留追溯证据 |
| `/Game/Vendor/Reallusion/CC5/Wardrobe/{Male,Female}/Average/<family>/<category>/<unit>/` | `FullReference` 保存材质来源，`Modules` 保存绑定同性基础 Skeleton 的分离网格 | 当前 UE 导入资产，不直接在磁盘移动 |

类别使用 `Coats/Shirts/Pants/Skirts/FullBody/Shoes/Accessories/Bundle`。这是 UE/导出目标命名，不重命名用户源目录。共享鞋放 `SharedFootwear` 家族，原配鞋仍留在原家族；跨家族复用由 Registry 映射完成。DataMake 继续负责运行时配置、Blueprint 与测试关卡，不复制全部 Vendor 资产。

`00_engine/scripts/character_creator/runtime_staging/` 是 CC 桥接输入的传输副本目录，不是长期唯一来源。桥接输入白名单不接受导出根下的工单直接作为 `--library-file`；先将权威 CC 工单复制到此目录并核对哈希，再提交。UE 和 Finalizer 使用当前版本 `manifests/v3/` 下的逐批权威工单，不放宽桥接白名单。只重试修订件时，桥接单件工单是完整批次的显式子集，其哈希与成员由 `revision.json` 固定，不要求它与三件批次整文件相同。

### 10.4 验证与尚未承诺的范围

程序回归：`00_engine/scripts/character_creator/tests/test_wardrobe_library_v1.py`、`00_engine/scripts/unreal/tests/test_ue_modular_outfit_pilot_import_v1.py`、`00_engine/scripts/unreal/tests/test_run_modular_outfit_pilot_import_v1.py`。它们覆盖去重边界、批次选择、禁止覆盖、目标路径和只读基础身体，不替代 CC/UE 现场验证。

聚合检查回归：`00_engine/scripts/unreal/tests/test_validate_wardrobe_import_batch_v1.py` 验证阶段身份、失败拒绝、服装/身体分类、基础 Skeleton 与 PhysicsAsset 边界。Witness 的辅助表情资产如出现 Auto Setup 异常会原样记录，不作为衣柜的身体或表情来源；运行时仍使用已经验收的基础身体。本门禁不宣称 Witness 内的所有辅助 Rig/表情均可用于生产。

新衣柜使用 `VAL-TRANSFER-01` 的独立作用域，必须检查实际网格分类、Skeleton、材质、空网格和意外 PhysicsAsset。`VAL-UE-02` 则另行检查实际允许组合的 v002 切换和动作。Pilot 旧结果不能自动覆盖新增服装。用户负责记录服装尺寸与头发相交的修正需求；此轮先推进服装转移，发型、胡须及其他体型随后处理。

### 10.5 完整套装检查工单

2026-09-07 的两套完整套装与 batch003 人工检查为历史限定证据，原 Plan、装配/重载报告和用户决定保留。旧 `/Game/DataMake/Validation/Wardrobe/Average/L_DM_WardrobeAverage_Review`、`L_DM_WardrobeAverage_Batch003` 已被现用 Coverage 审查替代，不再从旧 v002 模板创建或打开它们作为工作入口。

当前衣柜覆盖审查输入为 `%OUTPUT_ROOT%/unreal_character_import/current_reviews_20261001_v1/wardrobe_coverage/review_plan.json`。它使用正式新网格路径与 v003，保留原搭配、Body 和动作。已有 Plan 直接运行：

```powershell
$plan = '00_engine/outputs/unreal_character_import/current_reviews_20261001_v1/wardrobe_coverage/review_plan.json'
python 00_engine/scripts/unreal/run_wardrobe_coverage_review_v1.py --plan $plan --action show --page 1
python 00_engine/scripts/unreal/run_wardrobe_coverage_review_v1.py --plan $plan --action panel
```

`build_wardrobe_review_plan_v1.py` 和旧 `ue_build_wardrobe_review_level_v1.py` 是早期工单/关卡实现追溯，不负责现用入口的重建；前者的规则与槽位编译仍由全库生成器复用。现用命令、播放/暂停恢复、逐批装配和结果归属见 [运行时第 3.5 节](../unreal/CHARACTER_RUNTIME.md#35-全库网格覆盖审查)，最新入口验证见第 11.4 节。新输入需要新版本和重新验证，不能改写原用户确认。

### 10.6 已停止的服装几何隔离实验

目的：先测量从既有 FBX 派生仅服装几何，是否能减少重复身体/面部 Shape 的解析和构建开销，再决定是否修改逐批转移。实验不改原始 FBX、Family、已验收 UE 网格、Blueprint 或检查关卡，也不直接增加完成单位计数。

实现文件：

- `00_engine/scripts/unreal/wardrobe_fbx_geometry_probe.cpp`：使用本机 Autodesk FBX SDK 2020.2 读取 FBX，只保留精确指定 Mesh Node 对应几何及其 Shape，保留场景节点/骨骼；在导出前和重读后对比所选顶点、拓扑、蒙皮索引/权重、绑定矩阵、骨骼变换、材质名称和数量等。无匹配、同名歧义、输出已存在时拒绝。UV/法线目前只比较元素数量，Morph 只比较 Deformer 数量，因此此实验不等于完整通用保真验证。
- `00_engine/scripts/unreal/build_wardrobe_fbx_probe.ps1`：查找本机 MSVC/Windows SDK，链接 UE 附带的 FBX DLL 和 Boost JSON，编译上述 C++ 到实验输出下的 `bin/`；编译器临时环境在退出时恢复。没有另行安装依赖。
- `00_engine/scripts/unreal/validate_wardrobe_fbx_probe_v1.py`：独立核对 SDK 往返报告与原始工单哈希，仅对绑定/全局矩阵允许 `1e-10` 绝对误差；顶点、拓扑和权重不放宽。保存来源、派生文件和报告哈希；非有限数、空几何或其他差异拒绝。回归在 `00_engine/scripts/unreal/tests/test_validate_wardrobe_fbx_probe_v1.py`。
- `00_engine/scripts/unreal/ue_wardrobe_geometry_probe_v1.py`：仅用于当前 F02 Shorts，要求上述独立检查通过并再次核对三个哈希，拒绝已有测试资产；复用既有 Interchange 配置导入独立目录，对比原版 Skeleton、顶点数、LOD、材质槽、Morph 数量并排除意外 PhysicsAsset。只有这些检查全部通过才给新测试网格关联原有材质，不改原版资产。不是正式全库导入器。
- `00_engine/scripts/unreal/ue_compare_wardrobe_probe_geometry_v1.py`：只读复制原版/派生资产的 Source Model 和 Render Data 到内存，比较几何、属性、表面距离及 Source Model 各顶点蒙皮权重，写 `geometry_comparison.json`。该报告用于定位差异，不覆盖失败的导入门禁，也不自动晋升资产。
- `00_engine/scripts/unreal/ue_compare_wardrobe_corners_v1.py`：逐三角形检查位置、UV、法线/切线、顶点颜色和材质。Render Data 通过 `00_engine/scripts/unreal/wardrobe_corner_matching_v1.py` 按材质、UV、位置进行一对一匹配，允许三角形重排和保向循环移位；只针对当前单 UV 短裤实验。回归见 `00_engine/scripts/unreal/tests/test_wardrobe_corner_matching_v1.py`。输出 `corner_comparison.json` 中原编号比较与对齐比较必须区分，前者的最大差异不能当作表面损坏证据。
- `00_engine/scripts/unreal/ue_capture_wardrobe_probe_v1.py`：用于临时 Actor 与 SceneCapture 的正反面对比，原版/派生都使用原版材质；输出 `visual_probe*`，拒绝覆盖，分帧等待后拍摄，最后销毁临时 Actor。运行前记录脏包；临时 Actor 即使已销毁也可能使关卡变脏。只有确认拍摄前无脏包、期间无人编辑，才可重载原磁盘关卡丢弃临时改动；不能无条件丢弃用户未保存场景。
- `00_engine/scripts/unreal/validate_wardrobe_probe_images_v1.py --root <visual_probe目录>`：检查四张图是否有足够的非黑像素和亮度变化，写 `pixel_validation.json`；全黑或全白不能凭两图差值为零而通过。该检查只判断画面是否有内容，不自动批准服装质量，回归为 `00_engine/scripts/unreal/tests/test_validate_wardrobe_probe_images_v1.py`。

SDK 读写使用 [Autodesk FbxExporter 官方接口](https://help.autodesk.com/cloudhelp/2020/ENU/FBX-API-Reference/cpp_ref/class_fbx_exporter.html)，具体编译依赖以当前本机 `FBX.Build.cs` 和 SDK 头文件为准（2026-09-07 核对）。骨骼与穿着视觉仍须在 UE 验证，不能仅凭文件缩小或 SDK 比较通过晋升。

2026-10-01 本隔离实验未获生产晋升，旧 UE 导入/对比入口已退休；不再提供直接执行旧资产路径的命令。实验报告根为 `%OUTPUT_ROOT%/unreal_character_import/wardrobe_average_20260906_v1/optimization_20260907/`，保留数值诊断及必要样本，被替代/失败大媒体以清理映射解释。未来要继续优化应建立新隔离版本和独立 Gate。

历史实验根内：`bin/` 是可重建工具；`F_SHORTS/shorts_only.fbx` 是非权威派生；同名 `.fbx.json` 是 SDK 导出前/重读后的比较数据及体积、SDK 读取耗时；`native_validation.json` 保存矩阵容差检查和三个文件哈希；`ue_probe.json` 是引擎导入耗时和原版/派生网格的检查结果；`geometry_comparison.json` 是后续只读诊断。旧 UE 测试资产为 `/Game/DataMake/Validation/Wardrobe/OptimizationProbe20260907/F_Shorts`，未获生产晋升并已进入本轮审查清理范围。该旧入口已退休；后续尝试须以新隔离方案重新核验，不恢复本节旧执行命令。

2026-09-07 F02 Shorts 实测：145,707,008 字节原 FBX 派生为 4,060,320 字节。SDK 读取原始文件耗时 170.465 秒；精简文件 UE 导入 2.203 秒，不包含 SDK 读取/写出及材质 Witness。原始精确往返检查 `roundtrip_equal=false` 保留，78 处差异全部为矩阵舍入，最大 `1.4210854715202004e-14`；独立限定容差检查通过。

初次 UE 严格门禁失败：LOD0 渲染顶点为 33,015 对 33,017；Source Model 在 `1e-4 cm` 位置容差下仍报告 `Attribute` 差异。表面最大距离 `2.421684220813036e-05 cm`；Source Model 31,814 个顶点 ID 和蒙皮权重完全一致，无无效权重。Skeleton、材质槽、LOD 和 Morph 数量一致。后续属性定位见下方角点诊断；仍不能认定两个新增顶点只是无害接缝拆分。派生资产未获运行时批准，未关联正式材质/角色引用，完成单位计数不增加；既有完整导入路径保留。

比较性能时必须计入原始 FBX 的 SDK 读取及派生写出成本，不能只拿小 FBX 的 UE 耗时作全流程加速承诺。FullReference 材质来源策略尚未改变，男性、锁定 Bundle、带 Morph 的服装、多网格配件和全库分类覆盖也尚未由此实验关闭。

后续角点诊断：Source Model 的 60,374 个三角形 UV、颜色、材质完全一致；位置分量最大差异 `2.288818359375e-05 cm`，法线 `3.5762786865234375e-07`，切线/副切线 `0.0014218315482139587`。Render Data 按 UV 和位置匹配后 60,374 对全部对应，无缺失或额外三角形；法线分量差异最大 `0.007874071598052979`，切线/副切线 `0.016988009214401245`。这些是数值诊断结果，不是新增的通用容差通过标准。

源码依据（本机 UE 5.8）：`Engine/Source/Runtime/GeometryCore/Private/DynamicMesh/DynamicMeshOverlay.cpp` 的 `IsSameAs` 精确比较属性数组，位置 epsilon 不会自动放宽法线覆盖层比较；`Engine/Source/Runtime/RenderCore/Public/PackedNormal.h` 将法线按 127 缩放量化；`Engine/Source/Developer/MeshUtilities/Private/SkeletalMeshTools.cpp` 的 `AreSkelMeshVerticesEqual` 同时比较位置、UV、切线、法线、权重及颜色。因此微小源数值变化可导致属性精确比较失败及不同拆点/重排，当前结果与该机制一致；尚不声称已逐一追踪两个新增顶点的构建分支。正式批次仍用原始完整 FBX 路径，隔离实验未获生产批准。

当前显示边界：`visual_probe/` 首次因实例属性写入被拒绝而未完成；`visual_probe_v2/` 同帧拍摄与 `visual_probe_v3/` 分帧拍摄均近黑（RGB 仅 0..1）。v3 的命令执行完毕、临时 Actor 已移除，但 `pixel_validation.json` 为失败，不能当作视觉一致证据。原检查关卡从磁盘重载，确认无脏包后 UE 正常退出；未重启 CC。暂停继续堆叠截图尝试，原始导入路径不受此实验限制。

截图脚本随后准备了尚未现场验证的诊断选项：`DM_WARDROBE_CAPTURE_SOURCE` 可选 `SCS_FINAL_COLOR_LDR`（默认）或 `SCS_BASE_COLOR`，并开启编辑器骨骼更新。正反面机位改为模型 +X/-X 两侧，朝向中心；此前 Y 轴机位的黑图不能称为已通过的正反面证据。后续若试验须使用新输出目录，并再次核对实际构图；Base Color 即使有像素也只诊断基础颜色，不能代替最终着色一致性验证。

### 10.7 批次进度审计

`00_engine/scripts/unreal/audit_wardrobe_progress_v1.py` 从完整 CC 库读取全部单位，遍历 `batch_*` 工单。没有 Finalize 的批次只算已计划；Finalized 批次核验 CC 总报告、逐 Case 报告和 FBX/JSON/项目哈希后才算已导出。UE 只有发布 `wardrobe_modules.json`、其工单与证据哈希正确，并且重新通过四阶段验证，才算完成转移。`phase_pass_counts` 单独表示参照/分离/材质/验证进度，不把参照导入误算成成品。它不检查全量纹理字节闭包或人工合身，不代替相应 Gate。

```powershell
python 00_engine/scripts/unreal/audit_wardrobe_progress_v1.py --library-dir 'D:\UE\exports\character_creator\wardrobe_average_20260906_v1\manifests\v2' --report-root 'D:\UE\Lance_Work\00_engine\outputs\unreal_character_import\wardrobe_average_20260906_v1' --output 'D:\UE\Lance_Work\00_engine\outputs\unreal_character_import\wardrobe_average_20260906_v1\progress_audit_<new_run_id>.json'
```

输出保存各批输入/报告路径与哈希、已导出/已转移计数和等待 UE 的单位列表，属于保留追溯证据；拒绝覆盖旧审计，不回写冻结 Registry。回归：`00_engine/scripts/unreal/tests/test_audit_wardrobe_progress_v1.py`。当前最新审计由 WF-40 状态链接，不把技术示例文件名当作固定最新版本。

`00_engine/scripts/unreal/wardrobe_average_review_selection_batch003.json` 是后续人工检查选择：男 Jacket_2 搭配既有 Shirt_1/Pants_1/Shoes_1，女 Top2 搭配 Shorts1/F001。只有 batch_003 四阶段完成并发布模块映射后才可用第 10.5 节编译器生成新检查工单。原检查关卡不能覆盖；执行 `ue_build_wardrobe_review_level_v1.py` 时以模块方式载入，将其 `LEVEL_PATH` 设为独立的 `/Game/DataMake/Validation/Wardrobe/Average/L_DM_WardrobeAverage_Batch003`，并传入新工单和报告。既有禁止覆盖、来源哈希核对和重载检查仍须执行。

该检查的 `review_batch003/review_plan.json` 和 `review_level.json` 位于同一衣柜 UE 报告根，分别保存完整装配输入和保存重载结果，均保留追溯证据。新关卡是独立检查资产，不是生产关卡，也不替换原 Review。复现命令如下；现在这些输出和关卡已存在，命令用于理解实施顺序，不能直接覆盖重跑：

```powershell
$root = 'D:\UE\Lance_Work\00_engine\outputs\unreal_character_import\wardrobe_average_20260906_v1'
$registry = 'D:\UE\exports\character_creator\wardrobe_average_20260906_v1\manifests\v2\wardrobe_registry.json'
$template = '00_engine/outputs/unreal_character_import/modular_outfit_pilot_20260829_v1/runtime_plan_v2.json'
$plan = "$root/review_batch003/review_plan.json"
python 00_engine/scripts/unreal/build_wardrobe_review_plan_v1.py --registry $registry --template $template --selection 00_engine/scripts/unreal/wardrobe_average_review_selection_batch003.json --transfer-report "$root/batch_001/wardrobe_modules.json" --transfer-report "$root/batch_002/wardrobe_modules.json" --transfer-report "$root/batch_003/wardrobe_modules.json" --output $plan
if ($LASTEXITCODE -ne 0) { throw 'Review plan failed' }
$worker = (Resolve-Path '00_engine/scripts/unreal/ue_build_wardrobe_review_level_v1.py').Path
$command = "import importlib.util; spec=importlib.util.spec_from_file_location('dm_batch003_review', r'$worker'); worker=importlib.util.module_from_spec(spec); spec.loader.exec_module(worker); worker.LEVEL_PATH='/Game/DataMake/Validation/Wardrobe/Average/L_DM_WardrobeAverage_Batch003'; worker.DM_WARDROBE_REVIEW_PLAN=r'$plan'; worker.DM_WARDROBE_REVIEW_REPORT=r'$root/review_batch003/review_level.json'; worker.main()"
python 00_engine/scripts/unreal/ue_remote_exec.py --project datatry_02 --command $command
```

### 10.8 全库连续调度与延后合身检查

以下 v2 Run Root 与命令记录先前调度和恢复过程；当前修订库的执行入口见第10.9节。新版本不能沿用旧 `input_lock.json`，也不能因 CC 全部完成而自动恢复 UE。

#### 当前采用对话内逐批监督

短路径导出修正（2026-09-07）：`cc_validate_body_reconstruction.py` 的 `_outfit_gate_export_attempt_root()` 对标准 `exports/character_creator/` 布局使用该根下 `.fbx_stage/w_<随机名>/`，不再把较长的 PID/时间后缀追加到最终深层目录。FBX、JSON、`.fbm` 与辅助纹理先在同卷短目录导出，然后整体移动到原冻结 `export_root`；最终路径、文件名、CC 导出选项和检查标准不变。每 Case 的 `<basename>_export_attempt.json` 保存实际临时路径与最终路径；失败临时目录保留，不自动清理。非标准导出布局仍走原兄弟临时目录策略。新辅助目录不得通过目录链接逃出标准导出根。

可复现诊断入口 `00_engine/scripts/character_creator/cc_prepare_wardrobe_shortpath_probe_v1.py` 用 `--source <原批cc_export.json> --case-id <ID> --destination <全新短目录> --output-manifest <runtime_staging内全新JSON>` 从冻结 Case 复制隔离工单，只改最终输出根/项目路径，不改源资产、体型、Conform 或导出 basename；原工单哈希与原输出配置写入 `shortpath_probe`。然后用本节既有 `cc_bridge_client.py validate-bodies` 单次执行。该工具拒绝覆盖或与原导出目录重叠的目标；测试为 `00_engine/scripts/character_creator/tests/test_wardrobe_shortpath_probe_v1.py`，临时目录规则测试为 `00_engine/scripts/character_creator/tests/test_wardrobe_short_staging_v1.py`。

实际诊断为 `F_cfce65275ac92335b287`：原最终物理图路径233字符，旧临时后缀另增28字符，图缺失；仅把隔离输出改为 `%CC_EXPORT_ROOT%/sp1` 后，相同 Case 生成85,896字节的 `WarriorCloak_Pbr_WeightMap.jpg`，JSON相对引用保持不变。证据位于 `%OUTPUT_ROOT%/character_creator_bridge/artifacts/wardrobe_average/shortpath_probe_20260907_v1/validation_result.json` 和 `cases/<ID>/result.json`；其工单在 `runtime_staging/wardrobe_shortpath_probe_20260907_v1.json`。这证明缩短路径解决该例，不能把所有缺图或 SDK 错误都认定为同因。`sp1` 为隔离诊断导出，不计生产成功；修复后的生产 Case 仍需独立验收。`.fbx_stage/` 的失败尝试与 `sp1` 暂按诊断证据保护，问题关闭前不删除，不能混入正式 UE 导入清单。

2026-09-07 19:03 用户明确停止独立后台监控，要求助手在当前对话逐批查看结果再发起下一批。**这覆盖下节此前采用后台监控的执行选择。** `watch_wardrobe_exports_v1.py` 仅保留实现记录，不自动重启；当前 `monitor/STOP` 记录停用要求。CC 离线会话保持不变，UE 继续关闭。

使用既有调度的 `--one-cc-batch` 模式，一次执行只处理一个尚未 Finalize 且未隔离的批次；没有已分配待处理批次时，只创建一个新批次。该模式要求 `export_only`，不调用自动故障隔离。一次命令完成来源审计、导出和 Finalize 后，以 `awaiting_batch_review` 返回，必须由调用方阅读本批 Case 结果和最终工单后再次显式执行，不能在外层增加自动循环或后台监控。完整库没有剩余可执行批次时才做结束审计；有隔离项仍标 `export_incomplete`。

```powershell
python 00_engine/scripts/unreal/run_wardrobe_library_v1.py --library-dir $library --report-root $reports --run-root $run --schedule export_only --one-cc-batch --no-auto-defer-missing-weight-maps --no-auto-defer-asset-export-errors --execute
```

每批检查 `state.json`、`commands/`、该 CC 批次的 `validation_result.json` 和 manifest 根的 `batch_NNN/ue_import.json`。失败不进入下一批，先由助手诊断；只能对已检查的批次明确使用 `--defer-cc-batch` 保留失败证据，不能改成成功或修改冻结组装规则来绕过检查。单批模式仍持有全局导出锁，保留输入锁和拒绝覆盖保护。对应 `tests/test_run_wardrobe_library_v1.py` 覆盖一次仅执行一批、仅创建一批、失败不会自动隔离及拒绝导入模式。

用户自行离线重启CC后，先核对上一批是否已有成功总报告与最终工单，再检查新会话心跳、空闲队列和残留客户端进程。不能把对话中断直接当作CC导出失败，也不能沿用旧PID推断新会话健康。本次检查记录为Run Root的 `user_restart_check_20260908.json`，由助手根据只读检查填写，保存前一批结束时刻、新会话身份、重启后审计和续跑位置，属于本节保留运行证据，不是额外后台监控。尚有部分输出而缺成功报告时仍按下方恢复限制处理，不覆盖重导。

#### 仅重试失败 Case，不重复导出成功同批项

`00_engine/scripts/character_creator/cc_prepare_wardrobe_repair_v1.py` 用于根因已定位、原整批因少数失败而无法 Finalize 的修复。它不是运行器：不启动 CC、不移动文件、不循环下一批。`prepare` 只复制原工单中明确失败的 Case，保持源资产、所有 Case 参数和最终路径完全不变；原批工单、原汇总、全部原 Case 结果的 SHA-256 写入 `repair_provenance`。输出 JSON 放在桥接允许的 `runtime_staging/`，失败资产归档清单为 `preserve_failed_outputs_before_retry`，已成功项列为 `successful_case_ids_not_reexported`。

执行顺序如下，变量对应本节现有 Library、CC Artifacts 和新建修复目录：

```powershell
python 00_engine/scripts/character_creator/cc_prepare_wardrobe_repair_v1.py prepare --source $batch/cc_export.json --previous-result $oldReport/validation_result.json --output $repairManifest --export-boundary $exportRoot
# Inspect the preservation list. Resolve every source/archive under $exportRoot,
# reject existing archive destinations and reparse points, then Move-Item only
# the failed project/export roots to unique sibling archives. Do not move successes.
python 00_engine/character_creator_bridge/cc_bridge_client.py validate-bodies --library-file $repairManifest --output-dir $newReport --confirm-scene-replace --auto-dismiss-undo-warning --timeout 21600 --job-id $uniqueJob
python 00_engine/scripts/character_creator/cc_prepare_wardrobe_repair_v1.py aggregate --repair-manifest $repairManifest --retry-result $newReport/validation_result.json --output $newReport/aggregate_validation_result.json
python 00_engine/scripts/character_creator/cc_prepare_wardrobe_batch_v1.py --library-dir $library --batch-dir $batch --finalize-result $newReport/aggregate_validation_result.json
```

禁止覆盖原失败报告；新修复报告目录与 job ID 必须唯一。归档不是删除：本次使用原失败 `project_path` / `export_root` 的兄弟路径后缀 `.failed_before_shortstage_20260907`，移动前逐项核验绝对路径仍在本次导出根内。`aggregate` 核对全部原证据未变、重试 Case 与冻结参数相同、覆盖恰好是失败集合且均真实成功，复用原成功项的 `result_path`，明确标记 `evidence_kind=aggregate_of_original_successes_and_explicit_failed_case_retry`。这是可追溯的多次执行聚合，不是篡改旧失败结果；随后既有 Finalize 仍逐一检查 FBX/JSON/CC Project 哈希和冻结目标路径，下一次全库审计通过才解除该批隔离。

修复工单、原/新/聚合报告、失败项目与 FBX 归档均为本阶段 `retained_evidence`，关闭问题前不删除；成功正式资产仍使用原导出路径。实现测试 `00_engine/scripts/character_creator/tests/test_wardrobe_repair_v1.py` 覆盖只选失败件、成功件不重导、原报告不改写、路径边界、证据变更拒绝、不完整修复拒绝，以及新结果拒绝覆盖。

#### CC-only 持续监控

以下为已停用的后台方案，保留用于解释历史日志，不是当前运行方式。只有用户之后明确要求恢复才可使用 `00_engine/scripts/unreal/watch_wardrobe_exports_v1.py`。它是独立于导出调度的 Windows 后台进程，依赖当前 Python 的 `psutil`；每 60 秒读取调度状态、进程、CC 心跳、磁盘和提交内存余量。它不启动、关闭或重启 CC，不启动 UE，不删除或覆盖资产。必须先由用户离线打开 CC 并关闭 UE；电脑休眠、关机或监控进程被终止时，监控不会继续运行。

从 `%LANCE_ROOT%` 使用本节 `$library`、`$reports`、`$run` 路径：

```powershell
python 00_engine/scripts/unreal/watch_wardrobe_exports_v1.py --library-dir $library --report-root $reports --run-root $run --start-worker
```

长任务应由 `Start-Process -WindowStyle Hidden` 启动上述命令并重定向 stdout/stderr，不能依赖交互终端。`.monitor.lock` 防止同 Run Root 的第二个监控；已有导出进程只观察、不重复启动。`--start-worker` 是一次显式续跑授权，写入 `monitor/recovery.json` 后不会在监控重启时反复使用。启动前仍由调度做完整来源审计；监控的文件数量盘点只标为 `lightweight_manifest_inventory_not_hash_audit`，不能替代 Finalize 或最终哈希审计。

自动恢复边界：仅调度明确记录磁盘门槛、提交余量等待超时、CC 桥接不可用/忙碌时，监控在 CC 健康空闲、UE 关闭、磁盘至少 20 GiB、提交余量至少 6 GiB 后续跑。同一批次/步骤/故障类别最多自动恢复三次，次数持久化。未结束的 CC 客户端子进程会阻止续跑。其他崩溃、未知弹窗、部分输出、哈希不符进入 `needs_attention`，监控继续记录，但不盲目重试；这不是能够在对话结束后自行诊断任何新问题的 AI。20 分钟无调度检查点进展只给 `stalled_warning`，不强杀程序；长同步 CC 调用导致心跳暂时陈旧不单独视为崩溃。

导出调度同时支持 `--auto-defer-asset-export-errors`：只隔离已完整结束、没有 fatal dialog、同时存在成功 Case 的批次；所有失败必须恰好是 `Export first-batch FullReference character failed` 的 SDK `status_code='1'`，失败 Case 的保存项目哈希须匹配。该规则只确认可以先处理其余素材，不证明 SDK 错误根因已解决。不同错误、整批失败、未完成汇总或项目损坏仍阻塞。该开关与已有物理权重图缺失规则分别持久化；两者都保留整批原始失败证据，不把成功同批 Case 或隔离 Case 当作 Finalize 成功，不减少目标总数。

| Run Root 下的输出 | 内容与用途 | 保留要求 |
| --- | --- | --- |
| `monitor/state.json` | 最近检查时间、监控/工作进程、阶段、CC 状态、内存磁盘、轻量计数及告警 | 当前状态，可滚动更新 |
| `monitor/events.jsonl` | 每次巡检与恢复事件，用于判断是否停滞、何时续跑 | `retained_evidence`，本轮问题关闭前不删除 |
| `monitor/recovery.json` | 已消费的首次授权、各故障恢复次数、最近工作进程和日志路径 | 恢复控制文件，不可删除来绕过重试上限 |
| `monitor/worker_*_stdout.log` / `stderr.log` | 每次续跑的工作进程输出与错误 | `retained_evidence` |
| `deferred_cc_batches.json` | 原始失败批次、Case、工单/报告哈希；待修复而非已接受 | `retained_evidence`，仍是全量需求的一部分 |

在 `monitor/` 创建 `PAUSE` 文件会暂停自动续跑，创建 `STOP` 文件会停止监控；两者都不打断正在执行的导出。调度到 `export_complete` 或 `export_incomplete` 后监控结束，分别表示等待用户核验、仍有隔离项待修复；均不自动导入 UE。测试为 `00_engine/scripts/unreal/tests/test_watch_wardrobe_exports_v1.py` 和本节已有 `tests/test_run_wardrobe_library_v1.py`，覆盖恢复门槛、次数限制、未知失败拒绝、避免重复进程、导出专用命令和隔离计数。

**同类缺失的限定自动隔离**：后续 batch051 再次出现相同问题，恢复时启用 `--auto-defer-missing-weight-maps`，也持久化到 `execution_policy.json`。该规则只在 CC-only 捕获失败后运行：要求整批已结束、Case 覆盖完整，所有失败均为精确的 `ReconstructionError: Expected outfit export directory is empty: <本 Case>/fbx/textures`；FBX 非空、JSON 可解析、所有非空材质 `Texture Path` 都指向导出根内的非空文件，缺失项必须仅为 `Weight Map Path`。引用越界、材质图缺失、其他错误、部分报告、未知弹窗或通信失败均不能自动隔离，仍停止诊断。

符合条件时仍记录原失败、锁定哈希并隔离整批，绝不标成通过；随后继续其他 CC 批次。可用 `--no-auto-defer-missing-weight-maps` 显式关闭该规则。这里只自动化已经确认的诊断分类，不放松导出验收；隔离项存在时最终必须为 `export_incomplete`。`deferred_cc_batches.json` 是待修复清单，不是禁用/删除资产清单。专用测试覆盖缺失材质图、越界引用、未知错误、未完成报告、空 FBX 和非显式启用等拒绝场景。

**已诊断失败批次的隔离续跑**：`--defer-cc-batch batch_050` 仅用于操作者检查过、有完整失败汇总、尚未 Finalize 的批次，不是自动跳过未知错误。调度把批次工单、全部 Case ID、失败项、原报告路径及哈希写入 Run Root 的 `deferred_cc_batches.json`（保留诊断/恢复配置），恢复时核对哈希，不改原报告、源资产或主库。被隔离的整个批次不计入完成数；即使其中个别 Case 成功，也先保留在该批次内，不伪造聚合通过。

该模式只允许 `export_only`，继续处理其他已分配和新分配批次。剩余正常批次全部导出后，若仍有隔离项，则写 `audit_cc_incomplete_<时间戳>.json` 与 `export_incomplete`，下一步是修复隔离批次，不是 `export_complete`，也不能启动 UE。若出现其他未经诊断的错误仍报 `blocked`。修复必须保留原失败证据，重新核验并通过该批次的 `ue_import.json` Finalize 后，初始审计通过才会把它从活动隔离项移除；只删除隔离记录或改写原失败报告不构成修复。

2026-09-07 batch050 的两件 1920s 外套分别有 27 条有效材质贴图引用，但各缺一张 Auto Setup JSON `Weight Map Path` 指向的物理权重图。因此没有放松空目录检查、补造权重图或删除 JSON 引用，而是保留失败，先恢复其余导出。冻结范围仍为全库 325 单位，隔离不是从生产需求中删除服装。问题明细与当前进度由 WF-40 状态记录。

**历史执行策略（2026-09-07 下午用户更新）曾为 `export_only`**：先在已保存的 UE 退出检查点暂停导入，关闭 UE；保持用户启动的离线 CC，连续导出所有剩余小批。全部 CC 导出及来源审计通过后写 `export_complete`，停止并等待用户核验，不启动 UE。下面的交替转移步骤描述 `interleaved` 原模式，不代表当前任务还在逐批导出后立即导入。

调度策略与资产输入锁分开：`--schedule export_only` 或 `--schedule interleaved` 写入 Run Root 的 `execution_policy.json`（保留恢复配置），不改主库、Registry、`input_lock.json` 或成功报告。未传参数时恢复已保存策略，新 Run Root 才默认 `interleaved`。仅当旧调度已停止且取得唯一进程锁后，新的策略才会生效；只编辑脚本不能改变已运行 Python 的行为。

从运行中的原模式切换时，用本节后台交接命令附加 `-Schedule export_only`。辅助程序等待 UE 已保存正常退出后才交接 Python 调度进程；若退出与新 UE 启动发生竞争，新调度仍先正常关闭 UE，再开始 CC-only 阶段。已停止时可直接用下面的调度命令附加 `--schedule export_only`；用户核验之后才允许显式改回 `--schedule interleaved` 继续 UE 转移。

CC-only 同样优先跳过已经 Finalize 且初始审计通过的批次，再为剩余单位生成三件小批。最终完整审计写 `audit_cc_complete_<时间戳>.json`（保留来源证据），只有 `cc_exported_units == total_units` 才标完成，且不能冒充 UE 全库转移的 `audit_complete.json`。`state.json` 的 `schedule`、`workflow_stage`、`batch` 表示当前策略/阶段/批次；`export_complete` 的下一步固定为用户导出核验。CC-only 模式没有自动启动 UE 的路径，失败仍保存 `blocked` 并保持 CC 会话。回归测试覆盖策略持久化、导出/导入分离、CC 全量审计未通过时不能完成或导入。

退出阶段恢复（2026-09-07）：旧版 `stop_ue()` 发出正常退出后仍调用运行态的完整身份检查，可能在 Windows 退出过程中进程元数据消失时误报项目不匹配。旧日志没有保存当时的 CIM 行，不能把元数据丢失当作已经直接观测到的事实。修正后，发出退出前仍严格核对项目、编辑器、PID、创建时间和未保存包；发出成功后只等待已确认的 PID 消失，允许其元数据临时为空。任何新的 PID、创建时间变化、可读但不匹配的路径、多个 UE 或 180 秒超时仍停止，不强杀。缺失元数据的观测会写入事件日志，便于下次直接取证。

对应测试为本节的 `tests/test_run_wardrobe_library_v1.py`，覆盖退出中元数据缺失、初始身份不完整、PID 复用、其他项目、多实例、超时和退出失败。实际启动/空关卡/退出测试证据在本次 Run Root 的 `exit_fix_probe/`（保留诊断证据）；`audit_before_exit_fix_resume.json` 保存恢复前转移审计，`resume_<时间>_stdout.log`/`stderr.log` 保存独立后台恢复日志。它们均属于本节现有运行证据范围，不是新生产资产。首次恢复仍需检查 `state.json` 已推进到缺失阶段，不能仅凭启动进程就宣称恢复成功。

2026-09-07 用户接受 batch003 展示结果，并要求不再逐批等待人工确认，先把所有内容导入 UE，最后单设合身检查环节。这只调整人工检查时机，不取消 `VAL-TRANSFER-01` 的机器验证，也不把未检查的新服装标为 `VAL-UE-02 passed`。平均体型、Family 搭配规则、原始 FBX 路径和 CC 离线启动限制不变。

`00_engine/scripts/unreal/run_wardrobe_library_v1.py` 是串行调度入口，复用第 10.2 节的已有实现：

1. 先用 `audit_wardrobe_progress_v1.py` 的审计核对已完成批次及来源哈希，记录主库三个 JSON 的 `input_lock.json`；拒绝重复单位、主库变更或第二个调度进程。
2. 优先完成已导出的 pending 批次，成功阶段按精确 Case/Mode/成功报告跳过。失败报告不自动覆盖，需要诊断后再决定恢复；不会重新导入已完成参照资产。
3. 余下未分配单位按主库顺序创建小批（默认三件），调用 `cc_prepare_wardrobe_batch_v1.py`，复制工单到桥接白名单内的 `runtime_staging/<run>/<batch>/` 并校验哈希，再通过用户启动的 CC 会话导出和 Finalize。
4. 每个单位依次完成 reference、split、materials、validate，每批发布 `wardrobe_modules.json`。完成后自动进入下一批，不建立逐批穿着验收等待。
5. CC 导出前正常关闭 UE；导入时启动 UE 到 `/Engine/Maps/Entry` 空工作关卡，不改项目的默认启动地图。每四次 reference/split 重操作，或提交余量不足阈值时，确认地图和内容包均已保存后正常重启 UE。任何未保存修改都会阻止自动退出，不强杀，不启动/关闭/重启 CC。
6. 默认保留 20 GiB 磁盘空间，提交余量至少 6 GiB。空间不足立即记录断点；低提交余量最多等待 30 分钟后报阻塞。阈值是操作保护，不承诺足以避免任何一次导入的峰值；不自动删除资产腾空间。
7. 只有最终全库哈希/四阶段聚合审计覆盖全部单位，才写 `transfer_complete`。合身、材质观感、头发相交和动态穿模仍进入后续专门检查，不受这个完成标记覆盖。

先预览剩余单位，再执行（在 `%LANCE_ROOT%`）：

```powershell
$library = 'D:\UE\exports\character_creator\wardrobe_average_20260906_v1\manifests\v2'
$reports = 'D:\UE\Lance_Work\00_engine\outputs\unreal_character_import\wardrobe_average_20260906_v1'
$run = "$reports/continuous_20260907_v1"
python 00_engine/scripts/unreal/run_wardrobe_library_v1.py --library-dir $library --report-root $reports --run-root $run
# Only with CC started offline and current UE edits saved:
python 00_engine/scripts/unreal/run_wardrobe_library_v1.py --library-dir $library --report-root $reports --run-root $run --execute
```

调度日志/`state.json` 在上述 `$run`，每条命令的完整输出在 `commands/`，状态转换在 `events.jsonl`；开始审计为 `audit_start_*.json`，全量完成后才有 `audit_complete.json`。这些属于衣柜转移保留证据，不是新生产媒体输出。观察实时状态用 `Get-Content "$run/state.json" -Raw -Encoding UTF8`，其中 `running` 是某条命令正在执行，`batch_completed` 只代表该批转移成功，`blocked` 必须结合 `error` 和命令日志诊断。

`initial_cc_units`/`initial_ue_units` 是本次进程启动审计值，`completed_batches` 是该进程启动后新增完成的批次，并非整库历史列表。恢复或后台交接后进程内列表会重新开始，但初始审计重新纳入已完成映射，历史报告不会丢失。需要跨进程精确累计时使用第 10.7 节的只读审计，不把列表清空误认成进度归零。

CC 报告仍放在允许的 `%OUTPUT_ROOT%/character_creator_bridge/artifacts/wardrobe_average/<run>/<batch>/`，不能放到 UE 报告目录冒充允许输出根。实际项目/FBX/纹理与 UE 资产仍沿用第 10.3 节目录，不迁移源文件。

同一命令可在已停止后恢复，输入锁与成功报告仍须匹配；新的 `audit_start` 与命令日志不覆盖旧记录。若 CC 已产生部分文件但没有成功总报告，调度器拒绝盲目重导覆盖，需要先由操作方检查失败 Case；若 UE 导入失败，同样先检查已创建的包与脏包，不用删除整批来绕过保护。桌面应用崩溃、未知面板或失去通信不等于自动恢复成功。调用方必须观察调度进程/状态，不得把启动命令成功当作全库导入完成。

### 10.9 用户批准的锁定套装修订

**使用时机：** 已冻结 Bundle 的两个必需资产实际互相替换，且用户已明确选择其中一个。本节只变更这一组成关系，不放松加载器的“必需组件必须保留”检查；未确认的冲突不能照此擅自删件。

实现由 `00_engine/scripts/character_creator/cc_revise_wardrobe_bundle_v1.py` 负责，批准输入为 `00_engine/scripts/character_creator/wardrobe_elise_approval_20260908.json`。`prepare` 校验原单位、两个源哈希、原失败记录及全部成功 Case；仅在全新清单目录生成修订，不启动应用或导出。回归为 `00_engine/scripts/character_creator/tests/test_wardrobe_bundle_revision_v1.py`，覆盖原证据不变、只删批准项、新单位 ID、成功件不重导、输入变化/失败重试拒绝。

- 当前规则：Elise 必需组件为 `3、4、5、6、7、8、8.1、9、11`，鞋池与其他约束不变。源 `2.ccCloth` 不删除，只不进入当前装配。
- 新组成按原 `unit_key` 算法重新取 ID：`F_5398e9636fe0186d8faa`。旧失败 ID `F_80cacaff4e9288dc2a9e` 只用于历史追溯，新项目/FBX 使用新 ID，不能覆盖旧输入或冒用原哈希。
- 全库其他单位的参数、二进制路径不变；未受影响的逐批 JSON 按字节复制，**不复制或重导二进制**。`revision.json` 保存所有旧清单/Case 哈希、新主清单/修订批次/单件工单哈希，以及 `reused_finalized_manifests`。
- v3 Registry 的 Elise `manifest` 指向 `family_contracts/female.elise.json`，`original_manifest` 指回外部旧规则；新规则资产 `path` 为绝对源路径，`source_relative_path` 保留原相对名称，避免移动规则文件后误解析资源。未来装配从当前 Registry 读取规则，不直接重读外部旧 Elise JSON。重新从源库全量编译时必须重新应用这项批准修订，不能把未经修订的编译结果直接作为当前库。
- `aggregate` 核对冻结来源和新工单未变，只接受新 Elise 的真实成功结果，复用原两件 Workout 的 `result_path`。随后既有 Finalizer 检查每件项目、FBX、JSON 与对象映射。原失败总报告不改写；新汇总标记 `aggregate_of_unchanged_successes_and_user_approved_bundle_revision`。
- 旧 UE 映射仍引用 v2 的 Finalize 文件。`audit_wardrobe_progress_v1.py` 只在 v3 当前文件与声明继承的 v2 文件哈希完全相同、原文件哈希仍匹配时允许复用旧映射路径；缺显式继承或任一字节变化均拒绝，不能仅凭 Case ID 继承成功。对应测试在 `00_engine/scripts/unreal/tests/test_audit_wardrobe_progress_v1.py`。

已执行的复现命令如下；这些路径现在已有产物，禁止直接覆盖重跑。需要重新试验时换全新的修订与报告路径，保留同样的核验步骤：

```powershell
$base = 'D:/UE/exports/character_creator/wardrobe_average_20260906_v1/manifests'
$ccReports = '00_engine/outputs/character_creator_bridge/artifacts/wardrobe_average'
$ueReports = '00_engine/outputs/unreal_character_import/wardrobe_average_20260906_v1'
$retry = '00_engine/scripts/character_creator/runtime_staging/wardrobe_elise_20260908_v3/cc_export.json'
$newReport = "$ccReports/revision_20260908_v3"
python 00_engine/scripts/character_creator/cc_revise_wardrobe_bundle_v1.py prepare --source "$base/v2" --destination "$base/v3" --approval 00_engine/scripts/character_creator/wardrobe_elise_approval_20260908.json --previous-result "$ccReports/continuous_20260907_v1/batch_057/validation_result.json" --retry-output $retry
python 00_engine/character_creator_bridge/cc_bridge_client.py validate-bodies --library-file (Resolve-Path $retry).Path --output-dir "$newReport/elise" --confirm-scene-replace --auto-dismiss-undo-warning --timeout 21600 --job-id wardrobe_elise_20260908_v3
python 00_engine/scripts/character_creator/cc_revise_wardrobe_bundle_v1.py aggregate --revision "$base/v3/revision.json" --retry-result "$newReport/elise/validation_result.json" --output "$newReport/aggregate_validation_result.json"
python 00_engine/scripts/character_creator/cc_prepare_wardrobe_batch_v1.py --library-dir "$base/v3" --batch-dir "$base/v3/batch_057" --finalize-result "$newReport/aggregate_validation_result.json"
python 00_engine/scripts/unreal/audit_wardrobe_progress_v1.py --library-dir "$base/v3" --report-root $ueReports --output "$ueReports/revision_20260908_v3/audit_cc_complete.json"
```

逐条确认退出成功后才执行下一条；失败不能继续聚合或 Finalize。`v3/batch_057/ue_import.json` 为本批 UE 后续唯一输入，其他 v3 批次继续复用已成功来源。新 CC 报告根保存实际重试与聚合结果，UE 报告根 `revision_20260908_v3/` 保存全库审计与人工监督的 `state.json` 收口记录；均属于本阶段 `OUT-WF40-TRANSFER-BUNDLE` 保留证据，不是自动后台状态。修订清单、批准配置、原始/新结果与被引用 v2 文件均不得作为临时文件清理。

本次修订完成时只做CC导出收口；2026-09-09用户已批准继续UE导入，当前执行方式见第10.10节。显式使用v3、新Run Root和输入锁，沿用原UE报告根复用成功阶段；不要用旧v2连续运行命令恢复新需求。CC仍只能由用户离线启动，没有独立监控或自动循环。

### 10.10 全库导出后逐批监督 UE 导入

**触发：** v3全库CC导出已通过、用户批准导入，助手亲自检查每批后再继续。2026-09-09开始执行；精确进度以 [WF-40状态](../../project_management/status/workflows/WF-40.md#当前能力) 和本节Run Root为准。

`00_engine/scripts/unreal/run_wardrobe_library_v1.py --one-ue-batch` 只处理一个尚无 `wardrobe_modules.json` 的已导出批次，不生成新批次、不调用CC、不自动跳过失败。虽然底层持久化策略名沿用 `interleaved`，这个单批模式要求全部需求已分配且全部存在Finalize清单，并明确禁用其CC执行路径。互斥的 `--one-cc-batch` 不能同时使用。

1. 锁定v3三份主清单，重新全库审计；未完成CC导出或仍有隔离项时拒绝启动UE。
2. 验证UE进程身份；未启动时自行启动 `datatry_02` 到 `/Engine/Maps/Entry`，等待Python通信。已有脏包时停止，不丢弃用户修改。
3. 按成功报告跳过已完成步骤，仅续接 `reference/split/materials/validate` 的缺失部分，成功后生成本批映射。
4. 使用既有保存与内存门槛，在步骤之间正常重启UE；不能中断正在进行的导入，不操作CC。
5. 再次全库哈希审计，写入当前累计计数，以 `awaiting_batch_review` 退出。助手读取本批阶段报告和映射后，再显式调用一次。全部单位转移后才标 `transfer_complete`。

```powershell
$library = 'D:/UE/exports/character_creator/wardrobe_average_20260906_v1/manifests/v3'
$reports = 'D:/UE/Lance_Work/00_engine/outputs/unreal_character_import/wardrobe_average_20260906_v1'
$run = "$reports/ue_supervised_20260909_v3"
python 00_engine/scripts/unreal/run_wardrobe_library_v1.py --library-dir $library --report-root $reports --run-root $run --schedule interleaved --one-ue-batch --min-free-commit-gib 20 --min-free-lightweight-commit-gib 12 --no-auto-defer-missing-weight-maps --no-auto-defer-asset-export-errors --ue-disable-live-coding --execute
```

batch012/013使用原6GiB门槛；从batch014至044使用12GiB。044第二件外套参照构建时提交余量短暂降至0.49GiB，随后恢复且整批通过；从045起提高至16GiB。观察值、恢复时间、通过审计和修改边界在本节Run Root的 `resource_guard_change_20260909_16gib.json`。它是启动下一步骤前的余量要求，不是UE进程内存上限，也不能保证步骤中没有峰值。参数只影响资源等待和已保存边界的正常重启，可能增加重启次数，不改变导入内容或视觉验收。当前步骤不因改参数而中断或强杀。

从046起显式使用可选 `--min-free-lightweight-commit-gib 12`：仅为 `preflight/materials/validate` 指定较低余量；`reference/split` 和CC路径仍用主门槛。省略时兼容原行为，各阶段共用主门槛；该值必须大于0且不超过主门槛。磁盘、脏包、阶段成功、身份、输入哈希和已完成步骤复用的检查均保留，每4次重型操作后的重启规则不变。045实际仍为全阶段16GiB，已完成后才启动046，未热改进程；该差异在本节资源调整记录中留存。新增分阶段、默认兼容、内存不足重启和非法参数测试后，2026-09-09回归258项通过；当前运行表现按逐批证据确认，不由单元测试推断已完成导入。

2026-09-10从052起将重型门槛提高到20GiB，轻量仍为12GiB；046至051实际仍使用16/12。原因是050的Wrinkled Shirt与051的tuxedo参照构建分别观察到0.45/0.92GiB低余量，均自行恢复并通过。修改在051完成和全库审计后才应用于新调用，不热改在途进程；证据和准确命令为本节Run Root的 `resource_guard_change_20260910_20gib.json`。只调整既有CLI资源参数，不改导入选项、源文件、系统虚拟内存或代码；可能增加保存边界的正常重启，仍不保证步骤内部没有峰值。新门槛实际结果须按后续批次报告核验。

禁止在外面包自动循环或启动 `watch_wardrobe_exports_v1.py`。精确导入选项窗口的单次守护仍属于已验证导入实现，不是后台进度监督。65项启动前针对性回归涵盖现有调度、映射继承、导入入口和新增单批模式；测试为 `tests/test_run_wardrobe_library_v1.py`、`tests/test_audit_wardrobe_progress_v1.py`、`tests/test_run_modular_outfit_pilot_import_v1.py`（均位于 `00_engine/scripts/unreal/`）。

**控制器中断限制（2026-09-10）：** 不要对仍拥有 UE 子进程的调度会话发送 Ctrl+C 或终止会话，即使当前只是内存等待。batch072 在 YogaPants_A 参照导入已保存、split 尚未开始时，中断控制器也使 UE 一同退出，不能将其记作正常退出。应等待单批完成或内存等待自行超时，再按已保存包和进程身份检查正常处理 UE；在途导入不打断。本次恢复重新审计全库来源/阶段证据，并在新 UE 中核验本批已保存参照资产、前两件独立网格的 Skeleton/材质/空 PhysicsAsset 与空脏包，再从缺失 split 续跑，未重导成功件。证据为本节 Run Root 的 `recovery_batch072_20260910_1718/source_stage_audit.json`、`recovery.json`，属于同一转移输出的保留诊断证据。

恢复时曾手动用 `/Engine/Maps/Entry -nosound` 启动一次 UE；只关闭该会话的音频初始化，不改项目配置或导入参数。未确认明确内存收益，下一次调度正常重启仍使用原参数，不把此试验视为已验证优化。20/12 GiB 门槛不变，CC 始终未操作。

**Zen 启动等待窗口的限定恢复（2026-09-11）：** Python ready 超时并不证明 UE 已退出。先确认原 UE PID 仍存活，检查启动日志与 Zen 的 `/health/ready`；健康端点返回 HTTP 200 也不会自动关闭已出现的“是否等待ZenServer？”窗口。只有确认窗口属于该 UE PID、标题和“是”按钮均匹配后，才单次点击“是”，继续等待同一进程初始化；不点击“否”、不强杀、不因观察超时重复启动。按钮含义已对照本机 `Engine/Source/Developer/Zen/Private/ZenServerInterface.cpp`。随后重新验证远程通信、项目身份和空脏包，保留失败控制器日志，再显式续跑缺失阶段。batch078 Vintage 的 reference 已成功，仅补 split/materials/validate；证据为本节 Run Root 的 `recovery_batch078_zen_prompt_20260911.json`。这是助手现场核验后的恢复操作，不是通用弹窗自动确认功能，窗口句柄不能跨会话复用；CC 与 Zen 配置均未修改。

可选 `--ue-disable-live-coding` 仅在本脚本新启动 UE 时附加 `-LiveCoding=false`，后续由同一次调度发起的正常重启也沿用。它阻止该会话自动启动 C++ Live Coding 控制台，不关闭已有控制台、不触发编译、不改 Editor Preferences/项目配置/导入选项，也不会为了应用该参数立即重启现有 UE。底层语义以本机引擎 `Engine/Source/Developer/Windows/LiveCoding/Private/LiveCodingModule.cpp` 的启动参数解析为依据；它不等同于关闭 Blueprint 或材质编译。适用于纯资产导入，不用于需要热编译 C++ 的会话。默认未启用，必须在旧调用结束、已保存边界正常关闭 UE 后显式选择；实际收益与是否恢复导入应按新进程命令行、内存样本和阶段报告确认，不能由单元测试推断。

对应 `tests/test_run_wardrobe_library_v1.py` 新增可选参数默认兼容、正常重启保留参数、已有 UE 不重启、预览不启动应用与等待超时不误报 CC 正在运行的测试；启动参数写入 Run Root 的 `events.jsonl`。资源门槛、成功阶段复用、脏包保护和源哈希审计均不变。

2026-09-10 18:02 从 batch072 缺失步骤的显式续跑开始选用该参数；之前调用没有此参数。启用前的等待自行超时，再确认脏包为空并正常退出 UE；新启动进程确实没有 Live Coding 控制台，但首次资源样本仍接近门槛，不能提前声称已解决内存阻塞。准确命令、进程样本、测试结果和生效边界见本节 Run Root 的 `resource_startup_livecoding_20260910.json`，实际导入进度仍以单批审计为准。

输出仍属于 `OUT-WF40-TRANSFER-BUNDLE`：原报告根的 `batch_<编号>/` 保存阶段结果与 `wardrobe_modules.json`；新Run Root的 `state.json` 为当前调用状态，`events.jsonl`、`commands/` 保存执行记录，`input_lock.json` 锁定v3来源，`audit_start_*.json` 和 `audit_ue_batch_<编号>_*.json` 保存每批前后来源核验。上述均为保留证据，不把旧v2执行状态改写成当前进度。全部导入完成后，才进入独立的全库合身、动作和穿模检查，不由转移成功推断视觉通过。

若监督中发现不阻断构建的引擎提示，在对应批次保存 `<case_id>_import_observations.json`，记录原消息、发生阶段/资产、时间、后续实际结果和待复核范围。它属于同一输出的保留证据，不作为成功凭据或校验豁免；视觉问题仍在全库检查环节确认。

从batch083起，批末额外保留 `texture_inspection.json`，由当前UE读取分类网格的Skeleton、PhysicsAsset、材质和每项显式纹理覆盖；检查结束必须确认空脏包。Case以外的引用不能直接判为缺失，也不能整目录豁免：逐项读取实际对象，确认共享常量类型、父材质与源贴图，再保存专项证据和 `texture_inspection_verified.json`；初始检查记录保留。batch083的Boots03鞋舌材质引用共享 `Black_sRGB`，源Diffuse/Metallic仍为Case自有，但Auto Setup将鞋舌的Pbr材质选成了 `RL_GumsTongueTeeth`；这项材质语义与实际阴影仍需全库视觉审查，不由引用存在性检查宣布正确。

本次Run Root内的 `review_supervised_batch.py --batch batch_083` 是本轮证据复核辅助文件：消费同批四阶段报告、映射哈希、已留存日志和UE纹理检查，生成逐件observations及 `supervision_review.json`，一次仅处理指定批次。`audit_saved_library.py` 在全部批次完成后核对主清单的每个ID、每份映射和报告列举的已保存UE文件，生成 `final_saved_asset_audit.json`；其中按Case列出名称、槽位和独立网格路径。两者属于本轮 `OUT-WF40-TRANSFER-BUNDLE` 保留证据，不是后台监控或可脱离本轮目录使用的通用生产程序，也不能替代全库源哈希审计、真实UE阶段报告或人工合身验收。

UE 多次重启会轮换 `Saved/Logs`，因此从 batch068 起，在每件的 `validate_case` 完成后，由助手显式读取当前及备份日志，保存该件 `<case_id>_engine_log_review.json`：记录检查时间、已找到的 reference/split 完成消息、相关警告原行、错误类别及取样来源；整批检查再合并这些早期快照与最终日志。该文件属于同一转移输出的保留证据，不是独立后台监控，也不修改 UE 配置。若日志已经轮换，只能标记覆盖缺口，不能将零检索结果当作无警告。batch067 Shoes3 的 reference 引擎日志已轮换，但四阶段结构化报告、reference 命令成功记录与 split 日志仍在；其观察文件明确保留该限制，不为补日志重导成功资产。

**导入新增服装 Morph 后共享骨骼未保存的限定恢复：** 2026-09-10 batch056 的赛博朋克夹克新增 `open_01/02/03`、`wind` 四项 Morph 曲线元数据；Interchange 更新 M_BASE 共享骨骼，但 `run_import_split` 仅保存目标部件目录。下一次正常退出因此被 `Unsaved content` 拦截。该保护是正确行为，不是崩溃，也不能仅凭出现于女性导入之后就认定用了错误的性别骨骼。先用 `ue_remote_exec.py --command` 查询 `EditorLoadingAndSavingUtils.get_dirty_map_packages/get_dirty_content_packages`，不执行 Save All。

本次在保存前复制磁盘骨骼原件到 `/Game/DataMake/Diagnostics/WardrobeImportRecovery_20260910/M_BASE_DiskBefore/`，核对 SHA256。用 `Skeleton.get_reference_pose()`、`AnimationLibrary.get_curve_meta_data_*` 与 `ObjectExporterT3D` 对比：118 个骨头及参考姿势不变，归一化副本包路径后的其他导出属性不变；仅新增四项曲线且全部来自 `cs_c01_jacket.morph_targets`，既有曲线未删改。确认唯一脏包正是已比对的 M_BASE 后，才对这一资产调用 `EditorAssetLibrary.save_loaded_asset(..., only_if_is_dirty=True)`，再确认地图和内容脏包均为空，显式续跑相同批次。不得把这一结果推广为任意共享骨骼都可自动保存；未知增删骨、姿势/曲线修改或其他脏包仍先停止诊断。

证据位于本节 Run Root 的 `recovery_M_BASE_20260910/diagnosis.json`、`memory.t3d`、`disk.t3d`，JSON 包含实际比较/保存命令、前后哈希与资产路径，属于 `OUT-WF40-TRANSFER-BUNDLE` 的故障恢复证据。上述 Diagnostics 骨骼是只读对照备份，不参与运行时映射，不得当作新的生产骨骼；在恢复清理单独审查前保留。源 FBX、Family、导入设置及调度器脏包保护均未修改，本次不是通用自动保存功能的验收。

回归文件：`00_engine/scripts/unreal/tests/test_run_wardrobe_library_v1.py`，覆盖分配去重、完成阶段身份检查、UE 重启门槛和磁盘拒绝；这些测试不代替实际 CC/UE 长时间执行。当前运行与精确进度由 [WF-40 状态](../../project_management/status/workflows/WF-40.md) 记录。

**历史后台交接入口，当前禁用：** 以下仅保留9月7日早期记录的复现说明；自用户要求亲自逐批监督后，不得在本轮调用。旧入口 `00_engine/scripts/unreal/start_wardrobe_background_v1.ps1` 使用当时 `state.json` 中的 Python 调度 PID及三个根目录，验证身份，等待 `ue_normal_exit` 成功且UE退出后才停止调度Python，不停止CC/UE；等待短命令退出后从同一断点以隐藏进程重启。此机制不是本节当前执行方式。

```powershell
./00_engine/scripts/unreal/start_wardrobe_background_v1.ps1 -CoordinatorId <state_json_pid> -LibraryDir $library -ReportRoot $reports -RunRoot $run
```

交接最多等待一小时；未到安全检查点或身份变化时拒绝操作。此辅助入口限当前 `datatry_02` 桌面实例，不作为任意进程的通用终止器，也不要对已经正常后台运行的调度重复交接。记录为 `$run/background_handoff_<时间>.json`，含旧/新 PID、检查点、标准输出和错误日志路径；`transfer_complete=false` 表示交接成功绝不等同于全库完成。交接后必须检查新的 `state.json`/PID 和实际下一阶段，不能只看 Start-Process 成功。后台阻塞时不自动强杀或重导，仍按上面的技术恢复边界处理。

## 11. UE 衣柜与发型资产去冗余试点（2026-09-28）

用户已批准先做可回退试点，再讨论全库迁移。试点不重导 CC、不删除旧 UE 资产、不改正式 Registry 或现有审查关卡。目标是验证“运行时网格 + 必要材质/纹理 + 既有规范 Skeleton”的最小保存闭包，在试点当时不能把 `FullReference` 目录直接删除：原 `Modules` 仍引用其中的材质。第 11.1 节已经记录随后完成的全库重映射与经验证清理，本节旧路径和清单只用于解释迁移前证据。头发批量报告还显示 40 件共复制了 400 个 `Modules` 网格，其中 240 个为 `cc_base*` 人物部件；当前 UE Registry 草稿只索引 160 个真实发型网格。服装映射中也有被分类器忽略、但仍物理保存在 `Modules` 的重复身体网格。

试点输入固定为女性 `pretty_dresses/Pants5` 的一件服装网格与 `HB1_01` 的四个发型网格。以下三脚本均只服务这个固定试点，不是全库生产入口：

1. `00_engine/scripts/unreal/ue_audit_asset_restructure_pilot_v1.py`：只读审计 Asset Registry 依赖和真实材质覆盖，写 `ue_dependency_audit.json`。
2. `00_engine/scripts/unreal/ue_copy_asset_restructure_pilot_v1.py`：将该审计闭包复制到 `/Game/DataMake/CharacterFactory/RestructurePilot/`，逐一保存纹理、材质实例和目标网格；材质实例的显式纹理覆盖改指向新副本，网格材质槽改指向新实例，Skeleton 保持原路径；写 `ue_copy_report.json`。脚本可对自身固定试点目录续跑，但不清理或覆盖其他资产。
3. `00_engine/scripts/unreal/ue_verify_asset_restructure_pilot_v1.py`：在全新 UE 进程重新加载副本，检查资产类型、纹理覆盖、网格材质槽、Skeleton 和从新网格出发的依赖闭包，写 `ue_fresh_load_verification.json`。
4. `00_engine/scripts/unreal/ue_build_asset_restructure_compare_level_v1.py`：创建 `/Game/DataMake/Validation/AssetRestructurePilot/L_DM_AssetRestructure_Compare_v001`，同一 F02 基础角色左右两列分别装配旧网格和新网格；写 `ue_compare_level_report.json`，仅准备人工视觉核对，不自动判定像素一致。
5. `00_engine/scripts/unreal/build_asset_restructure_inventory_v1.py`：在系统 Python 下只读汇总已通过的服装/发型导入报告、草稿索引及物理 `.uasset` 大小，生成 `full_import_inventory.json`。应先于全库 UE 依赖扫描执行。
6. `00_engine/scripts/unreal/ue_audit_full_asset_restructure_dependencies_v1.py`：在 UE Asset Registry 中只读遍历全部运行时网格的同 Case 依赖闭包，生成 `full_dependency_audit.json`，将超出纹理/材质实例的特殊类型单列。它不加载所有网格、不复制资产。

本机使用 `D:/UE/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe` 对 `D:/UE/projects/datatry_02/datatry_02.uproject` 依次执行三脚本，参数为 `-run=pythonscript -script=<脚本绝对路径> -unattended -nop4 -nullrhi -nosplash -DDC-ForceMemoryCache -ddc=NoZenLocalFallback`。不带 DDC 回退参数的首次只读尝试因本机 Zen 与默认缓存均不可写而在脚本执行前失败；它没有修改资产。真实执行证据在 `%OUTPUT_ROOT%/unreal_character_import/asset_restructure_pilot_20260928_v1/`。

本次试点的结构结果：5 个网格、11 个材质实例、19 张纹理共 35 个新 `.uasset` 已保存并通过全新进程重载；两类新网格仍复用 F02 规范 Skeleton，材质实例纹理覆盖可加载，从新网格出发没有对各自旧 Case 根的依赖。对照关卡也已保存，两侧各有同一 F02 身体及五个旧/新网格。复制阶段曾因常规材质参数接口拒绝写入和初版纹理未落盘而失败；已改为只修改材质实例的显式覆盖结构、逐资产保存并增加磁盘检查，最终报告为 `success=true`。这只证明结构和加载，不证明像素一致、男女角色视觉兼容、整库闭包或空间节省。旧 `FullReference`/`Modules`、源 FBX/JSON、正式 Registry/关卡保持原样。

全库只读清单已覆盖 325 个服装 Case、40 个发型 Case、共 506 个正式索引网格，所列网格物理文件无缺失。原 `Modules` 中另有 1,950 个被分类器忽略的服装网格和 240 个未进入保留发型索引的网格；这些文件合计约 42.0 GiB，但仅是待审查的容量上限线索，不能由“未进入 Registry”直接推断无人引用或可以删除。全部运行时网格的 Case 内依赖闭包合计 1,335 个材质实例、2,890 张纹理，以及一个特殊 `SubsurfaceProfile`。唯一特殊 Case 是 `F_264b1944fafc453738a5`（女性 `pretty_dresses/Skirts`）；全库迁移器必须处理并验证这一依赖，不能直接把试点的两类资产复制逻辑盲目推广。

2026-09-28 用户在上述关卡确认新旧两侧视觉一致；试点视觉 Gate 由用户确认通过。以下第 11.1 节记录随后的全库迁移，不以本试点报告代替全库证据。

### 11.1 全库迁移与旧导入清理（2026-09-29）

全库迁移证据根为 `%OUTPUT_ROOT%/unreal_character_import/asset_restructure_full_20260929_v1/`，正式 UE 索引为 `00_engine/assets/character_creator/wardrobe_registry_ue_v4_full_20260929.json`。此次迁移未修改原 CC 项目、FBX/JSON、源 Family JSON 与历史导入/人工审查报告；2026-10-01 后续精确清理按替代映射收敛旧副本与大媒体，保留规范来源和有效决定。此次迁移仅重组 `datatry_02` 工程中的衣柜和发型 UE 导入资产。当前运行时目录为 `/Game/DataMake/CharacterFactory/Wardrobe/` 和 `/Game/DataMake/CharacterFactory/Hair/`，使用可读的性别、Family、槽位、服装名称或发型编号；`asset_id` 的哈希式命名仍保留，后续如需改名须另做 ID 映射。

操作与证据顺序：

1. `build_full_asset_restructure_plan_v1.py` 将 v3 源 Registry、`full_import_inventory.json` 和 `full_dependency_audit.json` 锁定为 `migration_plan.json`，覆盖 325 个服装 Case、40 个发型 Case、506 个运行时网格、1,335 个材质实例、2,890 张纹理和一个 `SubsurfaceProfile`，总计 4,732 个目标包，并检查目的路径重名。`ue_copy_full_asset_restructure_v1.py` 按 `run_config.json` 分批、逐 Case 保存和断点续跑；`copy_progress.json` 记录 365/365 完成。
2. `ue_rewire_full_restructure_cross_case_v1.py` 修复两个裙装材质跨 Case 引用同一皮肤配置的例外。`ue_verify_full_asset_restructure_v1.py` 在独立 UE 进程逐项加载、比对规范 Skeleton，并检查**所有旧 Case 根**的依赖；删除前后均通过，删除后报告为 365/365 Case、4,732/4,732 资产、506/506 旧网格不存在、零旧 Case 依赖。
3. `build_full_ue_wardrobe_registry_v1.py` 从原 41 个 Family 的合法 `assembly.groups` 和 331 个资产引用生成上述单文件 UE 索引，含 40 个发型、43 个共享鞋资产和用户确认的 3 个 Family 与 6 个服装资产 `deny_all` 规则。`build_migrated_review_plans_v1.py` 为 v002 模块化运行时、173 套覆盖审查和 400 项发型穿模审查生成新路径计划；历史计划与其哈希证据不改写。当时运行时、发型穿模控制脚本改读重映射计划。2026-10-01 Coverage 与 Compatibility 已再晋升至 `current_reviews_20261001_v1/`，旧 `review_plans/` 只保留迁移追溯；现用命令见第 11.4 节。
4. `ue_rewire_restructure_review_levels_v1.py` 把五个现有审查关卡的 26 个旧网格引用切到正式新路径，并把已完成视觉任务的试点关卡另外 5 个试点副本引用切到正式路径。`ue_verify_restructured_assemblies_v1.py` 在 UE 中对已审查的 173 套代表服装逐套应用固定槽位装配（男 78、女 95，零错误），并加载 40 个发型的 160 个网格；旧目录删除后复跑仍通过。
5. `ue_audit_full_restructure_referencers_v1.py` 的最终旧目录引用扫描仅剩即将共同删除的旧 Case 之间的 3 个内部引用，无外部 UE 关卡/新资产引用。`audit_full_restructure_filesystem_v1.py` 确认两个旧根下恰好是 365 个清单内 Case、30,526 个 `.uasset`、80,168,516,722 字节且无额外文件。`remove_verified_old_import_trees_v1.ps1` 先通过只读预检，随后在 UE 关闭、路径限定到工程 Content 且上述 Gate 成立时清理两棵旧树；D 盘可用空间从 167,024,951,296 增至 247,266,742,272 字节，差值 80,241,790,976 字节（包含文件系统计量差异）。试点目录另经 `ue_audit_restructure_pilot_cleanup_v1.py` 证明 35 个包无外部引用，`remove_verified_restructure_pilot_v1.ps1` 清理 27,982,356 字节。最终 `/Game/DataMake/CharacterFactory/` 只含 4,732 个 `.uasset`，物理大小 4,951,593,330 字节。

以 `UnrealEditor-Cmd.exe` 执行上述 UE 脚本时，沿用本节前述 `-DDC-ForceMemoryCache -ddc=NoZenLocalFallback` 参数。`migration_plan.json` 是旧新路径和恢复追溯依据；正式应用以新 UE 索引和新计划为准，历史导入报告中的旧路径不可作为当前资产路径。原 173 套服装及发型/服装的用户视觉结论继续有效；本轮机器验证证明复制后装配与引用可用，不宣称对 365 个 Case 逐件重新做了人工像素验收。发型性别标记是迁移后的独立索引更新，见第 11.2 节；哈希 `asset_id` 改名仍未实施。

### 11.2 保留发型的使用性别标记（2026-09-29）

正式单文件 UE 索引的每个 `hair_assets[]` 条目新增 `sex`，取值仅为 `male`、`female` 或 `both`。`build_full_ue_wardrobe_registry_v1.py` 中维护与 40 个保留 `hair_id` 一一对应的显式分类；重新生成索引前会核对 ID 集合和唯一性，避免遗漏、屏蔽发型回流或重生成时丢失标记。分类依据现有 Hair Builder 系列定位与逐款呈现倾向：HB1 保留项为 `both`，HB2 保留项为 `female`，HB3 按逐款记录分成 `male` 或 `female`。当前结果为 `both` 11、`female` 19、`male` 10，40 个条目全部有值。

`sex` 表示生成角色时允许进入的发型候选池，不表示 CC 导出身体的性别、逐个身份的头型适配结论，也不表示 40 个发型在 M02/F02 上都已完成动态视觉验收。全部发型仍来自女性 F02 导出；初始男女共同挂载视觉证据只覆盖 `hb1-01` Pilot。该标记阶段只更新索引和生成器；随后第 11.3 节的正式读取器已消费 `sex` 和服装 `deny_all`，但具体身份的头型适配仍需独立视觉检查。

标记阶段的服装条目 `ue_case_root` 已指向重组后的 `/Game/DataMake/CharacterFactory/Wardrobe/` Case 目录，331 个条目均通过物理目录存在性检查；当时尚无逐项 `ue_mesh_paths`。后续精确映射与锁定 Bundle 多部件归属由第 11.3 节补齐。

### 11.3 精确网格映射与正式索引直接读取（2026-09-29）

`build_full_ue_wardrobe_registry_v1.py` 现从已冻结的全库 `final_saved_asset_audit.json`、原资产绑定和 `migration_plan.json` 的旧新路径映射，为正式索引中全部 331 个 Family 资产补齐 `slot` 与 `ue_mesh_paths`。映射按 `(family_id, asset_id)` 找到原导入单元和模块键，再取得已验收的模块网格；锁定 Bundle 的多个资产分别持有自己的网格列表，不靠文件名猜测归属。生成时逐 Case 核对选中网格与迁移审计闭包一致、无重复、路径处于该 `ue_case_root` 下。共享鞋使用 `ue_asset_paths`，发型使用 `meshes[].path`，三者均为 UE 对象路径，不再需要源 D 盘衣服目录参与运行时选择。

当前索引的 331 个服装资产含 331 组精确映射，共 534 条服装、共享鞋和发型网格引用，去重后为 506 个 UE 网格；本地 `.uasset` 文件核对零缺失，与全库迁移后的 506 个正式可用网格一致。发型 `sex` 分类为 `male` 10、`female` 19、`both` 11。`formal_wardrobe_registry_v1.py` 是不依赖 UE 的正式读取与组装规则实现：核验 Family、组、必选/可选资产、锁定 Bundle、共享鞋互斥、槽位、发型性别及 Family/资产的 `deny_all`；输出精确 UE 网格路径和固定组件赋值。旧覆盖审查 Plan 仅供 `run_formal_wardrobe_registry_v1.py --phase parity` 做回归见证，不作为新运行时的选择来源。173 套既有已审查搭配的组件名与网格路径逐项完全一致，证据为 `%OUTPUT_ROOT%/unreal_character_import/formal_registry_runtime_v1/reviewed_173_parity.json`。

UE 中的 v003 复用组件实现、具体命令和保存重载结果由[角色运行时第 3.6 节](../unreal/CHARACTER_RUNTIME.md#36-正式索引直接读取与-v003-换装2026-09-29)负责。此处的网格闭包与旧装配相等证明索引可以作为装配来源，不等于 40 款发型在所有角色头型上的人工视觉验收；哈希式 `asset_id` 改名仍是独立后续事项。

### 11.4 现用审查晋升与旧入口退休（2026-10-01）

现用两个控制面板的 Plan/新产生报告位于 `%OUTPUT_ROOT%/unreal_character_import/current_reviews_20261001_v1/`：`wardrobe_coverage/review_plan.json` 使用男女 v003；`hair_outfit_compatibility/review_plan.json` 配合同目录 `bodyfit_metadata.json`，后者只保留消费者实际使用的 `bodyfits`、规范 Body、v003 Blueprint 与服装槽定义。历史 accepted Plan、人工决定和 batch_import_report 不改写。

Coverage 启动见第 10.5 节，也可双击该根的 `open_review.cmd`；Compatibility 双击其根的 `open_panel.cmd` 或执行：

```powershell
python 00_engine/scripts/unreal/run_hair_outfit_compatibility_review_v1.py --action panel
python 00_engine/scripts/unreal/run_hair_outfit_compatibility_review_v1.py --action show --case-index 1
python 00_engine/scripts/unreal/run_hair_outfit_compatibility_review_v1.py --action view --view back
```

2026-10-01 现用 Coverage 与 Compatibility 关卡的旧角色替换为 v003，原装配/位置/动画/附加头发保存并重载通过；Coverage 173 套实际装配与第 1 页重载通过，Compatibility 第 1 项和正/侧/背视角通过。对应 `VAL-UE-02` 的入口迁移证据为 `%OUTPUT_ROOT%/asset_cleanup/cleanup_20261001_v1/current_review_verification.json` 和 `ue_audit/review_actor_migration_result.json`。HairFit 六视及当前 Scalp/Hairline 对照仍使用原有效入口。这些结果不扩大原人工视觉范围。

旧 14-Case/P0/ScalpHairPilot 和 v001/v002 独立执行资产退出入口；`ue_build_modular_outfit_runtime_v2.py`、`ue_build_modular_outfit_review_level_v2.py` 的 shared helpers 继续服务现用 v003/审查，不能删除整份代码。BASE Skeleton/Body 和第一批 Look/动画/Sequence 保留；M02 旧树中仍被发型共享纹理、材质和 Rig/动画引用的部分保留，不能按目录年代整树删。

资产删除总验收已通过：精确名单的 2,396 个 UE 包、4,594,625,010 字节已清理，新进程核对 registry/文件系统均无残留；正式 777 个包的字节哈希完全不变，173 套装配、第 1 页保存重载及 Compatibility 第 1 项正/侧/背复验通过，保存图没有新增缺失 Game 引用，保留 Rig 只读补验也已成功。最终证据为 cleanup 根的 `ue_cleanup_receipt.json`、`formal_asset_hash_verification.json`、`ue_saved_graph_verification.json` 与 `post_cleanup_runtime_checks_completion.json`。UE API 曾遇到 World 文件残留与保留包内存标脏，均停止、未保存并退出；失败/部分回执保留。最终在 UE 全部关闭、保存图对删除集合外引用为零后，以原生 PowerShell 字面路径清理确切名单中的剩余文件；API 删除与离线清理分别记录，不能声称全部由 UE API 落盘删除。恢复从正式索引、旧新映射和回执开始，不启动旧 Pilot 重建；源码退休 guard 与 Plan 晋升不新增功能或视觉 Gate。

`retained_legacy_support_import_sources.json` 确认 183 个保留的 M02 共享支持资产，其 ImportData 仍指向 `%CC_EXPORT_ROOT%/pilot_m02_ue58_v001/CC_M02_Average_Pilot_UE58.Fbx`，实际来源均存在。旧 M02 导出包因此完整保留 271 个文件、501,042,951 字节作为重新导入源，不属于可删除垃圾；其余已替代旧导出 821 个文件、3,517,715,394 字节已清理，见 `cc_retired_export_cleanup_review.json` 的保留清单与 `cc_retired_export_cleanup_receipt.json`。目录命名和旧独立入口退休不能代替 ImportData 审计。本轮没有修改这些保留资产的来源绑定。

### 11.5 发型现用 CC 清单与共享导入 Pipeline（2026-10-01）

`ue_scalp_hair_batch_import_v1.py` 的 `MANIFEST` 现指向 `%CC_EXPORT_ROOT%/scalp_hair_batch_20260924_v1/manifests/cc_export.json`，已从 staging 原件按字节相同晋升，全部 preset ID、源项目和产出路径未变；证据为 cleanup 根 `cc_audit/hair_manifest_migration_result.json`。旧 staging 的物理保留由 CC 清理回执说明，不能再次把它当唯一当前输入。

该导入器的 `DEFAULT_PIPELINE` 现为 `/Game/DataMake/Config/Import/DM_Interchange_Split_Pipeline_v1`。Pipeline 已通过 UE API 从旧 `F_BIKINI_LAYERED/Modules` 复制到正式配置目录，F02 BASE Skeleton、分离网格、Morph、禁独立 PhysicsAsset、动画/材质/纹理开关逐项验证一致；证据为 `import_pipeline_migration.json` 与 `current_review_verification.json`。导入器每个 Case 会复制/配置自己的 Pipeline，不把共享配置位置变更解释为重新导入或新视觉通过。

本轮没有重跑已完成的发型导入，也没有改历史 `batch_import_report.json` 中的 manifest/source 路径。历史路径用于追溯，现用读者使用上述规范清单与正式 UE 索引；需要重导或增加男性网格时建立新版本和独立验证，不能直接运行旧批次重建已退役导入树。

### 11.5 固定男女参考头型的双版本发型转换（2026-10-04）

本节拥有 `cc_fixed_head_hair_batch_v1.py`、`run_fixed_head_hair_batch_v1.py`、`ue_import_fixed_head_hair_v1.py` 和 `build_fixed_head_hair_registry_v1.py` 的固定头型双版本转换。用户已接受 female01/male01 参考形状并授权夜间批处理；当前是否完成查 [项目状态](../../project_management/status/PROJECT_STATUS.md) 和本批次报告，不以代码存在代替成功。

输入女性参考为路线对照根 `female01_baked_final_capture_v1/morph_bake_checkpoint.ccProject`，男性为 `male01_average_inverse_roundtrip_v1/roundtrip_subd0.ccProject`。控制器先复制并移除附属资产，保存男女无发型 SubD0 源。来源及整理副本的 SHA、Body 低层几何摘要归 `%OUTPUT_ROOT%/character_creator_bridge/artifacts/fixed_head_hair_20261004_v1/sources/source_manifest.json`；移除前后仅比较明确的 14,164 顶点低层 Body，不把其他细分层重复网格当作多个角色。无活动场景整体替换授权之外的输入修改。

源准备与导出复用离线 Bridge 的 `validate-bodies` 和既有 `load_file_with_optional_undo_warning`。专用 `fixed_head_hair_batch` 允许 `transforms_only` 眼部快照，避免 T Pose getter 的 Undo 弹窗；不运行 Headshot/Face V3 或全面眼口验证。前两次女性准备因模式白名单及低层网格筛选失败，失败工单保留，成功源以 source_manifest 指向的 prepare_female_v3 / prepare_male_v1 为准，不原地替换失败报告。

在仓库根运行：

```powershell
python 00_engine/scripts/character_creator/run_fixed_head_hair_batch_v1.py --action pilot --hair-id HAIR_HB3_17
# 男女代表导入和挂载检查通过后继续全库；已完成工单按结果/来源哈希复用
python 00_engine/scripts/character_creator/run_fixed_head_hair_batch_v1.py --action all
```

该控制器拥有 `%CC_EXPORT_ROOT%/fixed_head_hair_20261004_v1/manifests/batch.json`：`bases` 保存男女基础导出，`cases` 为每个保留发型的男女几何版本，含 `case_id/hair_id/sex/usage_sex/source_project/hair_asset/status` 和 FBX/JSON 记录。先检查 FBX 体积、JSON 可解析、纹理文件非空以及 JSON 所有非空 `Texture Path` 引用实际存在，再登记 `exported`；`.fbm` 也属于纹理闭包，不能只数 `textures/` 子目录；这是轻量闭包检查，不逐款再跑视觉/表情。CC 完整人物 FBX 是导入中间输入，无须每款另存完整 CC 项目。

基础女性首次导出工单已产生完整 FBX/JSON/纹理，但旧导出器在发布阶段因目的父目录缺失报 `FileNotFoundError`。控制器只对这种已终态且有 `_export_attempt.json` 的情形，核对 staging/target 均在本批次允许根内、完整纹理引用闭包和 SHA，再将已完成目录发布到预期路径；不得覆盖已有且无恢复回执的目标。成功恢复见本批次 `jobs/fixed_head_hair_BASE_female/export_recovery.json`，原失败 Bridge result 保留；后续导出器预先建立目标父目录，无需再次导出该成功 Bundle。其他错误不进入这个恢复分支。

恢复入口先读取本批次 `live.json` 定位 job/result，再执行 Bridge `health` 核对当前 PID、instance、`active_job_id` 和 `inbox/processing`。存在实时工单或队列时继续监视同一执行器；只有终态失败或执行器实际结束后才决定续跑。旧对话中的 `BASE_female` 等 job ID 不作为当前任务。

UE Python 通过 `DM_FIXED_HAIR_MANIFEST` 指定上述清单，`DM_FIXED_HAIR_CONFIG` 可限定 `case_ids/max_cases` 运行小样。`ue_import_fixed_head_hair_v1.py` 仅写 `/Game/DataMake/CharacterFactory/FixedHeadHair_20261004_v1/`：`Shared/Female/CombinedBase`、`Shared/Male/CombinedBase` 用 `BY_SKELETON` 各导入一个合并裸人物网格及其原生共享 Skeleton。UE5.8 的 SkeletalMesh `skeleton` 属性只读，因此不得复制新 Skeleton 后再试图重绑已导入基础网格；发型在分离导入时就明确传入该性别共享 Skeleton，并保存新增附属骨。小样已经验证此路径，失败尝试的 `Base` 和重复 Skeleton 仅在本批次内核对无外部引用后清理。

每款精确保留的发型网格引用对应骨架，复制已接受的发丝 V2 实例；BaseColor/Opacity 优先取自本次对应性别导出的纹理，只有新 JSON 未提供该通道的有效纹理路径时才采用下述精确同款 accepted 来源回退。CC 会改变 `Hair/Scalp` 等材质数字后缀；真正需要 V2 纹理重绑定的发丝槽使用新 JSON 中该网格内部的精确材质名/导入槽名，其他已批准保留或隐藏的槽无需查询新纹理。只在旧新槽布局核对时去掉编号判断语义，不做跨网格的发丝材质模糊匹配。批准的 Scalp/Hairline 用同一 `M_Coverage_ZeroMask` 常量零 Opacity Mask 隐藏；实体发辫/装饰保留该款既有正确材质，不能套用任意发丝材质。临时完整人物导入位于本批次 `_Staging/<case>` 内；只在保留网格的 Skeleton/Physics/材质、材质父项/纹理直接引用及 Asset Registry 依赖核对通过后清理，必要支持资产保留。Asset Registry 的 `None` 返回按空列表读取，但不能以空返回代替直接材质与纹理检查。

HB1-18 的实体发饰还存在 FBX 与 JSON 分组不一的情形：分离导入 FBX 得到 `a7_3` / `a7_4` 两个网格，JSON 将它们归在 `A7_0310`，含 `Hair_Pbr` / `Hair_0_Pbr`。早期导入器在不需要新纹理的实体发饰上也强制按网格查 JSON，因此误报 `CC JSON hair mesh mapping ambiguous/missing a7_3`；失败记录保留于本批次 `runner/import_20261005_011120/HAIR_HB1_18_female_remote.json`。

这些槽属于既有不更改材质的实体发辫/装饰集合。修正后仅真正需要 V2 发丝重绑定时才查询新 JSON 的精确网格/材质；实体槽仍核对实际网格唯一匹配、对应 Skeleton、旧新槽数量与用途，然后保留同一 hair ID、对应网格/槽的 accepted 材质。HB1-18 男女条目已实际恢复成功，网格及槽名以 `import_report.json` 的对应记录为准。该恢复不表示允许对发丝槽跨款或跨网格模糊搜索，也不需要重新导出已完整的 CC Bundle；仅继续该导入 Case 的未完成步骤。

全量导入开始时 HB1-01 女性在 `hair_base/Hair9_Transparency_Pbr` 处失败：本次 CC JSON 的精确材质条目未提供 Base Color 通道，不是已引用贴图文件丢失，也不是网格/源 Bundle 不完整。导入器现只在新 JSON 缺省 Base Color 或 Opacity 的有效 `Texture Path` 时，从精确 `(hair_id, accepted mesh, slot_index, slot_name)` 对应的已接受 V2 模板取得同通道纹理；不借用别款或跨网格模糊匹配。新 JSON 提供的通道始终优先；若已有路径的文件缺失，仍明确失败，不用回退掩盖。若精确 accepted 纹理本身不能加载，也失败。

修正后 HB1-01 男女条目已实际导入成功，逐 Case 的 `accepted_texture_fallbacks` 记录 hair ID、旧精确网格/槽、通道、纹理 UE 路径及缺省原因；最终报告的 `accepted_texture_fallback_summary` 汇总这些真实来源。仅为补齐本次导出省略通道，不宣称所有新贴图都来自新 Bundle，也不要求为该缺省重新导出已完成的整库。继续原有未完成项即可。

实体发辫/装饰材质、V2 parent 与上述 fallback 纹理可能仍复用既有 accepted 支持资产。因此新版本成功不自动授权删除旧 `/Hair/` 或共享支持库；任何后续精简都必须先按真实材质父项、纹理及 Asset Registry 引用核对，不能仅按目录年代或新批次完成删除。当前旧接受库继续保留。

本轮还遇到一次图形设备故障：处理 `HAIR_HB1_05_male` 的 `space_bun_big` 包缩略图时，旧 UE 进程退出；旧日志报 `DXGI_ERROR_DRIVER_INTERNAL_ERROR` / `DXGI_ERROR_DEVICE_REMOVED`，附近含 `TexturePoolCopyOps` / `GPUSkinCache`，`RequestExit` 状态 3。这是具体 GPU/缩略图执行故障，不是 CC 导出失败，也不与早前 dotnet 弹窗混为一谈。精确旧日志 SHA、故障项、已提交检查点及恢复启动记录由本批次 `gpu_crash_recovery_20261005_v1.json` 保留。

确认旧编辑器实际退出后，使用 GUI `UnrealEditor.exe -nullrhi`、Entry 空关卡及 Python remote 恢复结构导入，沿用关闭异步 skinned/texture 编译、`-NoRestorePackages` 和隔离日志；不启动 Commandlet 的完整材质渲染，不重复导出 CC 或强杀仍在运行的编辑器。可续跑入口：

```powershell
python 00_engine/scripts/unreal/run_fixed_head_hair_v1.py --action import --all --launch --nullrhi
```

启动器在有项目编辑器时复用，并拒绝对“进程仍在但 remote 不可用”自动重复启动。新实例已实际恢复中断项并继续下一项；已成功记录经过引用核对后复用，部分资产按同一 Case 继续完成。恢复只说明本批导入用无 GPU 路径继续成功，**不说明显卡驱动根因已修好**。原 CC 进程和已完成导出未重启、未重导。NullRHI 只用于导入及结构加载审计，不能产生新的视觉通过结论；已有六张 GPU 小样图继续作为限定视觉证据，后续正式渲染仍使用正常图形编辑器。

UE 报告为 `%OUTPUT_ROOT%/unreal_character_import/fixed_head_hair_20261004_v1/import_report.json`，包含 `bases`、逐对 `records`、`success/complete`。续跑检查已有记录及网格引用，仅处理未完成项；小样的批次 `success=false/complete=false` 不代表成功样例失败，也不能用于全库发布。完成后运行：

```powershell
python 00_engine/scripts/unreal/build_fixed_head_hair_registry_v1.py
```

生成器要求全部目标对唯一且成功，输出独立 `00_engine/assets/character_creator/wardrobe_registry_ue_v4_fixed_head_hair_20261004_v1.json`。每款保留 `hair_id/display_name/sex`，改用 `fit_variants.female/male` 的 `skeleton_path/meshes`；旧单女性 `preset_id` 不再放入 UE 索引。Family、共享鞋及使用许可原样保留；来源 SHA 留外部报告，不混入纯 UE 路径描述。输出旁证为导入报告同目录 `registry_publication_report.json`。全库成功后已发布的新索引成为默认来源：正式读取器的 `current_registry_path()` 每次默认读取都会核对 publication、目标 Registry SHA 与完整导入报告 SHA/成功状态，再选择新版本；任一凭证不匹配则回退旧索引，不依赖重启长寿命 UE Python。旧文件不覆盖、不删除。当前发布时间证据见 `registry_publication_report.json`；真实默认消费者、Family/共享鞋与使用许可不变的核对见 `consumer_completion_check.json`。新索引消费见 [Runtime 3.9](../unreal/CHARACTER_RUNTIME.md#39-固定头型双版本发型的代表小样与索引消费2026-10-04)。

2026-10-05 全量导出与导入已终态成功，来源完整性、索引发布及一次全量实际加载/清理闭包通过。来源集合与精确计数以 `export_completion_check.json`、`import_report.json` 和 Runtime 的 `final_runtime_audit.json` 为准。最终 `accepted_texture_fallback_summary` 仅含 HB1-01 男女两处 Base Color 共用同一款 accepted Diffuse；没有因此重新导出整库。代表视觉证据仍限定 HB3-17 男女六视，旧支持依赖与 GPU 驱动限制继续保留。

本轮不会重新研究旧 Average 的绝对 UE 位姿残差，也不要求逐款全动作或人工审查；仅主张对所选固定参考头型的导出、绑定、代表外观与索引能力。原始规范项目和旧接受发型库保留。

### 11.6 固定参考人物材质修复与后续导入防复发（2026-10-05）

新定向修复所有者为 [Runtime3.11](../unreal/CHARACTER_RUNTIME.md#311-固定参考头型人物与发辫的定向材质修复2026-10-05)。本文件拥有的`ue_import_fixed_head_hair_v1.py`接入`hair_source_shader_v1.py`，按精确源`Custom Shader=RLHair`处理遗漏发辫而非只凭Transparency名称，烘焙颜色不重复叠染；皮肤通过`ue_fixed_head_skin_texture_utils_v1.configure_imported_skin_normals`接入实际物理源重建。该函数兼容原名，但现在包括每四标准皮肤槽自己的Diffuse+Normal，锁定源JSON与物理PNG SHA、使用TextureFactory独立导入8纹理、建立统一直接Diffuse/Normal DefaultLit父材质与实例，仅替换四皮肤槽。

该防复发路径不再仅修Normal属性；它避免复制已有故障GPU纹理资源，目标基于精确FixedHeadHair Shared/CombinedBase及源指纹，重跑核对物理源/资源语义后复用，不重建重复资产。辅助完整字段、失败门禁与恢复归Runtime3.11，主导入调用与导出Bundle来源由本节拥有。不改原PNG/肤色色调、不使用Delta，不重新导出或导入80套，不重写完成批次原import_report及旧publication。

本轮新修复根`skin_future_import_offline_check.json`已覆盖男女8槽/16源纹理规划，4针对性测试通过；`skin_future_import_runtime_smoke.json`实际使用独立女性网格副本完成4槽/8纹理导入并二次幂等复用，正式Body不改。应用后`material_apply_verification.json`通过264实际只读检查、0失败：8皮肤/24发辫、16纹理语义/源SHA、26其他材质和Skeleton保持。R03防复发已完成限定范围，非全量重导或GPU图库接受。

发辫24槽与身体两网格8皮肤槽均成功saved apply，真实代表视觉通过；新`wardrobe_registry_ue_v4_fixed_head_materials_20261005_v1.json`为默认，publication保存两份成功apply独立快照与SHA，旧双版Registry/import_report不变。新默认来源与回退归Runtime3.11及Registry索引。完成批次guard已实际验证正常无重导返回，80records与原import_report SHA保持，回执为`completed_import_guard_verification.json`；完整要求回归`material_repair_regression.txt`已307passed（74.52秒）。`material_repair_docs_audit.json`16独立子系统/跨层实际通过、0错误警告，本计划已结项归档，归档导航终验由final审计记录，Status维护当前结果，不据脚本存在推断已发布/验收；本轮没有数据生产Batch。

## 12. 完整角色UE导入与骨架标准试点（2026-10-05）

本节拥有[已完成独立试点计划](../../project_management/history/completed_plans/PLAN-2026-10-COMPLETE-CHARACTER-UE-SKELETON-PILOT.md)的来源提取、完整导入、保存与骨架比较。Run Root为`%OUTPUT_ROOT%/unreal_character_import/complete_character_skeleton_pilot_20261005_v1/`，归OUT-WF40-TRANSFER-BUNDLE；`runtime/`由[Runtime3.12](../unreal/CHARACTER_RUNTIME.md#312-完整男女角色骨架与代表发型装配试点2026-10-05)拥有，默认unclassified保护。本次消费历史既有FBX，没有运行CC或重新导出，也不是最新CC统一创建成品的转移。

### 12.1 输入与完整导入

`complete_character_import_manifest_v1.json`固定`%CC_EXPORT_ROOT%/fixed_head_hair_20261004_v1/bases/<sex>/CC_FIXED_HEAD_<SEX>.fbx`及相邻AutoSetup JSON。男女FBX SHA分别为`38c25b7466a6e544f692b2db89e2da26a09988cffb9c141fe725d54fe589596e`、`3f5e7271ade67f75677b8cdeae4257e9eb7f9bcf28b3a2f238849102428ea597`；源项目、批次及纹理来源反查`source_rig_audit_v1.json`与`fbx_source_extract_<sex>_v1.json`，源SHA不变。

首先用CCFbxFactory获得AutoSetup材质见证，再以独立Interchange拆分保留源全部Morph和骨架，不导动画/Physics，不采用见证几何。两个`FIXED_HEAD_<SEX>_FULL/import_audit.json`实际success及standard_candidate_ready=true：每性别六部件为Body、Tongue、Eyes、Teeth、Tearline、Eye Occlusion；前四各395个Morph，后两439/436，总计2,455个跨网格目标，所有源Morph名称均保留。这不是2,455个独立表情。每性别118骨骼与源集合一致，无遗漏/额外骨；源没有独立HD眉毛网格，可见眉毛属历史照片/皮肤烘焙，不能声明已带最新装配眉毛。

正式独立Skeleton为`/Game/DataMake/Validation/CompleteCharacterSkeleton20261005/FIXED_HEAD_<SEX>_FULL/Meshes/SKEL_CC5_<Sex>_Average_Complete_v1`，对应Male/Female。`standard_candidate_registry.json`记录六网格、Skeleton和Manifest SHA，`common_skeleton_adopted=false`、`visual_acceptance=pending`；`bone_standard_comparison_v2.json`绑定最新read-only import_audit SHA，男女各六部件的118骨层级、局部位移、旋转（四元数符号等价）和缩放全部精确一致/差0，仅证明这两个历史来源和对应发型参考可静态装配，不证明新身份共享或男女共同Skeleton。

### 12.2 材质及诊断边界

每性别实际有17个角色MIC绑定`/Game/CC_Shaders` HQ父材质。`actual_material_texture_inventory.json`与`normal_binding_audit_v1.json`实际核对每性别10个NormalMap绑定，sRGB=false、TC_NORMALMAP，ImportData来源为嵌入纹理的原FBX。物理PNG文件名匹配辅助报告configured=0/unmatched=10是来源表现不同，不是Normal缺失；该审计没有宣称源PNG与导入纹理像素等价。

见证AutoSetup自动产生的Rig诊断及无效AS_ExpSequence记录保留，见证几何/动画不纳入正式六部件接受。完整源Morph与骨架机器通过不等同于身体/表情动作播放通过；本轮runtime_motion_acceptance为not_tested，人类视觉与新身份共享标准未取得。

### 12.3 实现、复现与恢复

本节唯一拥有：`00_engine/scripts/character_creator/cc_extract_complete_fbx_source_v1.py`、`00_engine/scripts/unreal/ue_import_complete_character_skeleton_pilot_v1.py`、比较辅助`00_engine/scripts/unreal/compare_complete_character_bone_standard_v1.py`、系统CLI `00_engine/scripts/unreal/run_complete_character_skeleton_pilot_v1.py`及三个测试`00_engine/scripts/character_creator/tests/test_cc_extract_complete_fbx_source_v1.py`、`00_engine/scripts/unreal/tests/test_ue_import_complete_character_skeleton_pilot_v1.py`、`00_engine/scripts/unreal/tests/test_compare_complete_character_bone_standard_v1.py`。Stage worker由Runtime3.12独占，不重复归属。

从%LANCE_ROOT%执行：

```powershell
python 00_engine/scripts/unreal/run_complete_character_skeleton_pilot_v1.py --action status
python 00_engine/scripts/unreal/run_complete_character_skeleton_pilot_v1.py --action audit
python 00_engine/scripts/unreal/run_complete_character_skeleton_pilot_v1.py --action import --launch --nullrhi
python 00_engine/scripts/unreal/run_complete_character_skeleton_pilot_v1.py --action stage
python 00_engine/scripts/unreal/run_complete_character_skeleton_pilot_v1.py --action open
```

`status`只读候选索引；`audit`仅读取已存在正式试点网格/材质/骨架、写审计回执，不导入/替换/重命名/保存UE资产；`import`会写独立试点资产，`stage`会写试点关卡，`open`要求图形编辑器且无脏关卡，不可用NullRHI视觉查看。共享UE仅由root串行操作；导入遇到已有试点网格时恢复到实际审计，不覆盖正式库或强制重新替换。保存失败/源SHA、Morph或骨骼缺失会记录具体case失败；先核对回执/脏包，再针对失败阶段恢复，不因进程返回即宣布Gate通过。`regression_tests_final_v1.txt`实际323 passed（55.07秒），覆盖必需documentation/dataset/unreal及源extractor针对测试；`documentation_audit_final_v2.json`实际16独立子系统及cross-layer全通过、0错误/0警告；首次v1导航失败证据保留。

最新图形编辑器只读`import_audit.json`（audit_only=true）与bound_normal_texture_audit实际通过，每性别10精确CC JSON Normal Map绑定/TC_NORMALMAP/sRGB=false/嵌入FBX来源；初始成功导入审计以`import_audit_initial_complete.json`保留。v1骨骼对照冻结保留，当前v2绑定最新审计SHA。当前界限是男女独立候选+这两个历史来源的静态完整转移；新身份共骨架、身体动作/表情播放与新人工视觉是后续范围，不阻塞本静态试点结项。


## 13. CFD原生男女双人完整转移试点（2026-10-06）

本节拥有`%LANCE_ROOT%/00_engine/scripts/unreal/run_cfd_native_pair_transfer_v1.py`、`cfd_native_pair_ue_target_v1.py`及`tests/test_cfd_native_pair_transfer_v1.py`，以及`%OUTPUT_ROOT%/unreal_character_import/cfd_native_pair_20261006_v1/`的双人来源/导出/导入汇总，归OUT-WF40-TRANSFER-BUNDLE。CC创建归BodyFit11.5/既有CC Run Root；审查worker/panel和runtime子目录归Runtime3.14。新入口为validated_pilot，仅本次双人实际导入/保存/重载及限定绑定范围，不晋升全池生产。默认输出unclassified保护。

### 13.1 来源、导出及入口

execution_record_v1.json/.md是独立授权范围记录，不是第二current主计划；另一会话服装诊断保持。只从CFD-Combined/{female,male}/cfd选图，排除cfd-india/cfd-mr。未来A/B/L/W等量（40人各10），本轮男女各1先均匀抽族群再组内照片；sampling_manifest固定男W/CFD-WM-230、女A/CFD-AF-200及seed/候选/SHA。两人native几何均通过，男真实最终保存08_normalize_geometry、女10_post_bake_roundtrip，实际项目SHA已核对；没有重复新两人CC人工表情接受。

两人各一次完整export成功，报告为既有CC Run Root `CFD_NATIVE_PAIR_EXPORT_20261006_v1/{sex}/route_validation_report.json`。实际设置motion=false、bake_subdivision=false、UE5骨结构/UnrealPreset、Original纹理；pair_source_spec与complete_character_import_manifest_v1锁定照片/CC项目/FBX/JSON/source_extract哈希，每人6parts/118bones/2,455跨网格Morph通道。此数量不是2,455个唯一跨部件表情，也不代替源变形有效或完整表情视觉。

导出准备作用域`%OUTPUT_ROOT%/character_creator_bridge/artifacts/cfd_native_pair_export_preparation_20261006_v1/`归本节，保留一次性patch/候选/tests/manifest。representative_single_export补丁在两人创建完成后应用，源SHA7195cab6565f35e441d6bff2363765bf16c0825c7b9ddd0423eb84063568b202；post_application_validation_v1记录文本与候选一致、9passed及1preapply-only immutable guard deselected，旧准备历史不改写。

```powershell
python 00_engine/scripts/unreal/run_cfd_native_pair_transfer_v1.py --action status
python 00_engine/scripts/unreal/run_cfd_native_pair_transfer_v1.py --action prepare --spec 00_engine/outputs/unreal_character_import/cfd_native_pair_20261006_v1/pair_source_spec.json
```

prepare只准备来源；import/audit/stage/open是明确动作，不因status调用而执行。当前ue_target锁定Macheniek/node3FEB46014AA22FBCA2E4DDBAAF7440B4/PID12840；旧15228 target另存ue_target_before_reopen.json，实例变化必须重新显式核对，拒绝launch/其他实例回退。不要重复import当作审计；已保存资产先调用只读audit，再按失败阶段恢复。

### 13.2 材质见证恢复与当前通过范围

| 证据 | 实际范围 |
| --- | --- |
| CFD_NATIVE_<SEX>_001/import_audit.json | 两人success、source_unchanged、all_source_morph_names_preserved及standard_candidate_ready均true；候选标记不等于正式共同Skeleton/全动作通过 |
| runtime/stage_report.json | 独立新关卡和男女完整Actor保存success，正式衣服/发型源只读复用 |
| runner/preflight/reopened_saved_stage_remote.json | 新可见编辑器实读新level、男女Actor、dirty_maps=[] |
| runtime/replies/b274602b11cf47309a7fd47d05fde97d.json / d980b61d249e4c31803ce27a3db1727e.json | action1停止状态+hair1三分之四和action0/front/hair2保存恢复，bindings true；不是所有动作连续播放/逐帧视觉验收 |
| runtime/panel_lifecycle.json | 用户桌面面板PID4720 ready/errornull，当前双人最终用户验证已通过；独立回执runtime/user_final_validation_v1.json |
| required_regression_summary_v2.json | 可配置witness/target修复后523 passed/110.93秒；修复前v1的521历史单独保留 |

新FBX最初remote unattended=True与witness AssetImportTask automated=True分别取消AutoSetup modal；只改remote后第二次仍失败。MaterialWitness、MaterialWitnessAutoSetup及女性两份failed_initial_material_type/failed_second_task_automated审计保留。母导入器新增WITNESS_SUBDIR/WITNESS_AUTOMATED默认MaterialWitness/True不变，本scope仅witness使用MaterialWitnessInteractive/False及remote import unattended=False，split策略不改。root确认HQ AutoSetup和FBX两窗口，ControlRig off；后处理删除两文件夹提示选择否，未删除来源。后续batch弹窗自动确认尚未实现/接受，因此不能称无人值守完整导入已冻结。

root查看消息日志时Alt+F4误到主窗口导致旧UE15228退出，属于操作失误而非诊断为引擎崩溃；两人/新关卡此前已保存，原关卡SHA按root证据保持。已告知用户并桌面恢复12840，launch_report/旧target/实际新level读回保留。双人试点已获用户直接人工验证通过；未启动正式batch，不覆盖规范参考/正式库，不重导衣柜或发型池，亦未以旧CC/UE人工接受替代新两人结果。


本范围目录及脚本Catalog已最后重建，`documentation_audit_final_v1.json`实际16独立子系统和跨层全部通过、0错误/0警告；沿用修复后523回归，不重复矩阵。独立执行终态completed_user_accepted_bounded_pair，R01–R05完成，用户明确后续需要时才通知开始批量；另一会话唯一current仍保留，无新主计划/正式batch。


用户2026-10-06直接确认本次验证成功，`runtime/user_final_validation_v1.json`绑定源/导入/保存关卡SHA，作为当前人工终态，原stage/report的pending保留历史。流程可用于后续另获授权的批量创建，production_batch_authorized=false、batch_execution_started=false；等待用户明确启动通知。本scope已完成，不改变另一会话current计划。交互AutoSetup/FBX确认仍是后续自动化限制，不是已通过的人工验收阻塞；不从本次声明扩大为全池/全动画或无人值守生产认证。

此次纯文档人工验收同步由root执行必要离线回归：acceptance_documentation_regression_v1.txt实际523 passed/45.60秒、exit0，未重跑CC/UE；目录及Catalog已重建，user_acceptance_documentation_audit_v1.json实际16独立子系统/跨层全部通过、0错误/0警告。


## 14. CFD原生40人完整转移批次（2026-10-06）

本CFD40独立scope已完成创建、完整导出、完整UE导入与静态审查机器交付。40人导入/来源完整性见final_import_summary_v2.json；review_pages_verification_v1.json确认单关卡5页×8覆盖40unique，代表focus/side/head/nohair控制及最终第1页full/front/hair保存通过。AutoSave原值True已恢复，monitor停止、automation PAUSED。人工视觉验收pending，不推断全动画/服装或最终渲染接受；若UE重启需重新绑定当前实例。旧故障及恢复pending段落保持历史，当前以execution_record/final_delivery_checkpoint_v1为准。 本节拥有完整导出handoff、导入summary v1/v2和final_delivery_checkpoint；Runtime3.15拥有review与最终用户说明。以下pending/实例/runner记录均按时间保留为历史，不覆盖终态。

本节拥有`%OUTPUT_ROOT%/unreal_character_import/cfd_native_batch40_20261006_v1/`的批次授权/来源/创建引用/完整导出/共享Skeleton导入汇总，归OUT-WF40-TRANSFER-BUNDLE，默认unclassified保护；创建代码BodyFit11.5，runtime子目录/简单关卡Runtime3.15。新脚本所有权/精确入口待实现方给出，当前不将准备代码当真实通过。

用户授权40人且批准改为男女各一套共享Skeleton的顺序。R01抽样/40请求prepare完成，随后R00先将既有CFD_NATIVE_MALE_001/FEMALE_001完整FBX以独立新副本绑定对应规范同性交享Skeleton，检查代表中性、一个身体动作及闭眼/微笑/张嘴。R00通过后执行R02 native CC40创建/修正/保存，R03完整Bundle导出，R04对应共享Skeleton完整导入/部件Morph/材质读回，R05简单审查5页×8人、男女两排各A/B/L/W并支持focus。共享Skeleton不是全男女混成一个，也不复制40套独立Skeleton作最终方案。

只读对照已由root报告118骨名/层级一致、身体<0.001mm、面部骨最大男3.31mm/女5.09mm，精确源/运行回执待owner登记。不可要求面部骨位完全相同，亦不可仅名字一致外推变形正确；共享资产/mesh-specific参考与表情实际检查是R00的证据。

R01抽样/准备和R00有限root_visual_smoke已通过，范围仍以shared_representative_acceptance_v1.json为准，不等于用户整批或最终画质接受。AF002恢复、AF003新照片一次通过属于历史route SHA9e88be…fb156；BF001随后原09及v2/v3恢复三次pre-click失败，详细证据归%OUTPUT_ROOT%/unreal_character_import/cfd_native_batch40_20261006_v1/BF001_qt_lifetime_diagnosis_v1.json。当前SHA9b1dbb…c905f的owner-retention修正有13项针对测试，并由bake_control_lifetime_probe_v2.json证明实际CC中返回前后控件有效；不将引用相关证据升级为已确定Qt底层析构机制。

历史CC尾段检查点：BF001 v4限定恢复已成功晋升：%OUTPUT_ROOT%/character_creator_bridge/artifacts/headshot_character_creation_20261005_v1/CFD40_BF_001/attempt_001/creation_result.json为completed，最终项目SHA cb3b24ec…bd4484；09实际trigger、局部几何完全保持，10保存重载和11捕获完成，final_geometry_review/native_appearance_review均passed。native_appearance_review按既定结构/材质摘要边界passed，但before/after各保留272项SDK观察错误（SwigPyObject缺isNull）；不升级为完整纹理像素、视觉或UE接受。 主批次已恢复（session79490/PID4044为该恢复时记录），BF002启动以日志为准；40人成品导出导入及整批/人工验收仍待。root串行操作CC/UE；唯一监视子agent每30分钟只读检查，正常不重复通知，不保证零延迟或全部UI无人值守。仅在40人创建和完整FBX导出全部结束、必要检查通过、保存妥当且无待补导后，root才正常关闭CC，再启动UE导入；不能提前关闭仍需导出的CC。另一会话唯一current服装诊断保持，精确进度由独立PROJECT_STATE/execution_record拥有。

当前CC创建/完整导出已完成且正常关闭CC；D3D11实例32420已继续完成实际角色导入，成功进度以动态registry为准。旧73969在下一角色前受控hold（非角色失败），保存包卸载后唯一43488逐项执行registry.pending，不重导已审计角色；内存下降不等于删除资产或所有Package对象消失，最终渲染/整批视觉仍pending。 root唯一操作，其他agents离线、nightmonitor30分钟只读。用户最新明确允许Computer Use仅处理导入弹窗，用完即停止；root继续后台API优先，仅遇AutoSetup/FBX导入确认窗口时使用CUA，不恢复此前无条件电脑操作授权。 失败报告保留，UI取消不能忽略为成功；须材质见证/绑定及完整audit通过才commit registry，规范源保持，本授权不扩视频发布或另一会话修复。


### 14.1 共享Skeleton代表门禁机器检查点

本节还拥有`%OUTPUT_ROOT%/unreal_character_import/cfd_native_shared_skeleton_probe_20261006_v1/`的独立代表共享骨架来源/导入/完整性/门禁证据，以及`%LANCE_ROOT%/00_engine/scripts/unreal/run_cfd_native_shared_skeleton_probe_v1.py`。新probe runner仍experimental，18针对测试仅离线实现范围；Run内ue_shared_probe_review_v1.py为代表恢复/检查工具，不注册为新通用生产入口。

existing_reference_comparison_v1.json绑定男女及规范来源SHA，all/head/body分别比较；不把脸骨差异当失败或抹平身份。male_shared_integrity.json/female_shared_integrity.json通过，身份mesh参考、canonical包及shared参考保持。两代表6部件118骨/2455跨网格Morph保留；root五项有限smoke通过见batch40/shared_representative_acceptance_v1.json。v1轴错误横扭失败保留，v2 jaw localZ−10°/eyes localZ+8°及10面部子树Skeleton平移模式已完成，未穷尽全部表情。

R00探针时批次ue_target绑定Macheniek/PID8604/node739AEB3D45E38A18AFA6428A0E1E3C0E，runner/skeleton_api_probe_remote.json为真实只读SDK探针；不据API成功推断动态正确。该探针及当时恢复计数为历史；当前实例须重新核对，实时计数以独立executionrecord及真实CC结果为准。


### 14.2 R00面部平移重定向待办

face_template_translation_difference_v1与shared_face_axis_evidence_v2说明模板平移/局部轴；shared_face_retargeting_inspection记录两次apply尝试，但PythonBoneTree只读，未成功改变/保存模式。ue_probe_shared_face_retargeting_v1现inspect-only，不因历史action字段为apply误写修复成功。CU菜单下一次输入反复dismiss，属于工具限制，不是审批或Skeleton不兼容/角色路线失败。

用户已分别保存新男女probe Skeleton facialbone子树递归Skeleton平移模式，root最新shared_face_retargeting_inspection.json确认两性面部10骨Skeleton/其他骨未改。native_reference_vs_template_clip_v2.json的中性眼牙锚点近数值零，peak下颌/牙/舌运动为动画预期；tongue02/03中性全局仍约0.64–1.66mm旋转相关差异，不声称完整零差。root亲自复查五项代表smoke通过，用户回复仅证明设置保存，不升级为用户完整动态验收。preview_mesh_and_parts_readback.json读到tongue预览资产，但双方六部件真实存在。optional copy_source可把此次新probe设置复制到batch共享Skeleton，仍保护canonical包SHA及118参考；批次shared_skeleton_config.json/shared_skeleton_baseline.json及runner/batch40_setup_shared_remote.json现已证实男女两套实际复制/setup通过（PID8604），该setup时尚无成品导入，属于历史；当前真实导入以batch registry为准。
本批次转移实现由§14唯一拥有：`cfd_native_batch40_contract_v1.py`、`run_cfd_native_batch40_transfer_v1.py`及`tests/test_cfd_native_batch40_v1.py`。两套共享Skeleton setup实际通过，40人成品实际导入已执行并继续，当前入口仍experimental、非整批接受；`run_cfd_native_shared_skeleton_probe_v1.py`为限定R00代表smoke的validated_pilot。

CFD40_AF_001独立恢复由Run内`recover_af001_late_bake_v1.py`执行，真实3针对测试通过；CC修正语义归BodyFit11.5，本节拥有失败保留、标准state/result晋升与批次resume收据。

来源追溯由本节拥有：原route_readiness_pin_migration_v1历史保留；%OUTPUT_ROOT%/unreal_character_import/cfd_native_batch40_20261006_v1/implementation_freeze/保存历次原字节源码，后续route_invoke_readiness_pin_migration_v2、route_retained_control_pin_migration_v3、route_owner_retention_pin_migration_v4各summary.json记录对应来源迁移。v2保留完成项旧SHA，v3/v4只迁移未来执行来源，已完成项不重建；BF001三次失败和旧步骤保持，项目及旧步骤输出未改。精确SHA/记录数量由这些机器回执拥有，不另抄长表；不得把元数据重绑定写成角色资产变化。BF001新尾段已在原最终几何/native appearance/保存重载检查通过后晋升标准state/result；此限定成功不代表后续角色或整批已通过。

### 14.3 GPU故障后的有界split恢复与材质见证恢复（2026-10-07）

当前进度只看Run内imported_character_registry.json和execution_record；40完整导出已有终态核验。D3D11实例32420已继续完成实际角色导入，成功进度以动态registry为准。旧73969在下一角色前受控hold（非角色失败），保存包卸载后唯一43488逐项执行registry.pending，不重导已审计角色；内存下降不等于删除资产或所有Package对象消失，最终渲染/整批视觉仍pending。 临时D3D11/Entry或此前noRT均为进程级，项目ini未改，不能作为最终渲染接受；R05仍pending。

BM001在eye_occlusion保存缩略图时GPU DRIVER_INTERNAL_ERROR/DEVICE_REMOVED，原25256退出、99288断连；gpu_crash_20261007_0943/editor_at_crash.log及故障checkpoint保留。只给该中断case配置独立SPLIT_SUBDIR=MeshesRecovery20261007，旧5件不删除或重写。run_cfd_native_batch40_transfer_v1.split_subdir默认Meshes；split_recovery_config.json仅允许BM001、schema1、与原manifest case排序JSON SHA一致的input_fingerprint及安全单目录名。已audited完成项不得更改split目录，来源/配置漂移拒绝。worker统一用新split_root导入/审计，恢复时只save_directory(split_root)，避免递归重存旧兄弟包。SPLIT_SUBDIR和WITNESS_SUBDIR均限制安全单目录且不能相同；非恢复case保留原目录策略。

恢复配置为imports/CFD40_BM_001/split_recovery_config.json，成功证据为该case/import_audit.json和BM001_recovery_stage_documentation_sync_20261007_v1.json；exec90210退出0，六部件/2455跨网格Morph及男性shared Skeleton unchanged通过，85009恢复run_all。实现agent已运行18项针对测试（root交接回执），本轮不重跑测试矩阵。该成功限机器导入，完整动态/视觉另验。

BF003的AutoSetup材质见证曾取消，failed_7ea60e29b5f1.json记录Std_Tongue_Pbr无唯一精确材质；取消后不能继续算成功或忽略缺材质。恢复交互后，该case/import_audit.json success及完整Morph/材质绑定审计通过才进入registry；runner/target_20261007_111435_2bb1fc38/BF003_material_recovery_remote.json保留执行证据。所有failed_*.json保留。当前仅root操作UE弹窗，其他agents离线且不并发；pair_transfer_prep交接未接管已撤销；用户最新明确允许Computer Use仅处理导入弹窗，用完即停止；root继续后台API优先，仅遇AutoSetup/FBX导入确认窗口时使用CUA，不恢复此前无条件电脑操作授权。不保证任意弹窗全无人值守。

#### 第二次GPU故障后尚未验证的D3D11恢复检查点

LM002材质见证在root确认FBX前取消，取消来源未定，随后缺Std_Tongue_Pbr，六网格未saved；gpu_crash_20261007_1155/LM002_failed_audit.json保留。20560在11:55:58 autosave eye_occlusion缩略图时再次DRIVER_INTERNAL_ERROR/DEVICE_REMOVED，editor_at_crash.log保留；noRT不足，未恢复autosave。32420暂用进程级-d3d11和EngineEntry，原项目SM5支持保持。12:15只读16个编译worker CPU递增、SM5日志推进，但remote discover未ready、ue_target未改、未启动新import controller。

editor_import的成功边界在_import_character及postimport baseline返回后，对非audit操作执行gc.collect与UE collect_garbage，沿用已有wardrobe策略；5focused通过，但GC真实运行效果及D3D11恢复尚未验证。535 required全套和Catalog613属于该补丁前历史，不能改称补丁后通过；最终Catalog/Inventory/audit后续统一。

#### 材质见证fail-fast（实现阶段，尚未UE实跑）

母worker ue_import_complete_character_skeleton_pilot_v1.main在import_split前从见证SkeletalMesh建立精确slot_material_map，逐项检查原expected_meshes.expected_materials名单。取消或缺少唯一精确材质立即抛错并沿用失败report保留，不生成新的split网格；没有放宽匹配或跳过后续逐槽绑定/Normal/Morph等audit。16项离线测试由metadata agent通过并由root读取接受，32420仍在编译，实际UE执行尚未验证。CUA仅按用户新明确授权处理导入弹窗，用完停止。

#### D3D11后台就绪与临时会话设置（12:24–12:28）

32420/userMacheniek/projectdatatry_02/node0D66157C4923BAF2BAC16EA9B96129CC实际remote identity通过，ue_target已绑定。Run内configure_recovery_session.py用native load_class(/Script/UnrealEd.EditorLoadingSavingSettings)和get/set_editor_property(bAutoSaveEnable)临时True→False，未save_config；recovery_session_settings_32420.json记录原值，任务结束必须恢复True。此API成功不等于D3D11导入成功。LM002单人session1408仍运行于FactoryCCFbxFactory阶段，无新完成audit；GC实际效果未验。CUA因工具physical Escape停止，root未再调用、用户恢复或手工确认答复pending，不能推定同意。

#### LM002 D3D11首个实际角色成功与恢复授权

LM002 import_audit.json实际success，六部件/2455跨网格Morph、男性shared reference unchanged，session1408退出0；成功边界GC实际返回（root观察约7.23GB RAM）。只证明此角色D3D11导入及GC调用可执行，不证明长期整批稳定、最终渲染或全部材质视觉。唯一all runner73969跳过22已审计项，继续LM003，无重复提交。用户最新明确“恢复，仅确认导入弹窗”，root实际确认AutoSetup/FBX，删除目录提示选No；CUA用完停止。前述授权pending/1408运行/未验证均为历史检查点，autoSave原值True仍须在任务结束恢复。

#### 已保存角色包的有界内存释放与退出恢复

editor_import最前检查operator_import_hold.active，true时在下一角色导入前受控停止，不当角色失败。27audit至LF002后，root在约15.55GB UE RAM/4.7GB系统free时hold73969；Run内unload_saved_case_probe.py及unload_saved_prior_cases.py与unload_saved*.json记录LF002和LM002–005/LF001实际unload True/空error，随后约10.21GB RAM。remaining_loaded仍可91/94，只描述对象残留与内存下降，不是资产删除或完整对象清空。原saved资产保留。hold=false后唯一43488逐项执行动态registry.pending13，跳过前27；不能再同时启动旧all runner。

run_cfd_native_batch40_transfer_v1.release_saved_case_packages只接受冻结spec中唯一id，须state audited且audit success/standard_candidate_ready；仅ObjectIterator中已加载Package、精确UE_ROOT/id/前缀，绝不额外load资产或扩大到shared/canonical。与dirty_content_packages交集非空即拒绝，记录每case timestamp receipt。unload返回False或非空error即失败；成功后清引用、Python/UE GC，记录remaining对象但不要求归零。editor_import在成功保存/审计及shared baseline后调用，finally再次核对shared baseline；11focused由metadata agent实际通过/root接受，不升级为长期内存稳定性。新patch后Catalog与审计留final刷新。

退出任务必须用32420会话原设置证据recovery_session_settings_32420.json恢复bAutoSaveEnable=True（未save_config，不改项目ini），并保存恢复回执；当前pending，不因角色成功自动视为已恢复。CUA只导入弹窗、用完停止。

### 14.4 完整机器交付与恢复退出（2026-10-07）

final_import_summary_v2.json/.md继承v1的40audit/SHA/文件存在/源绑定检查，加入5页机器显示与恢复退出；v1原SHA不改。每人六部件118骨2455跨网格Morph，240parts、两shared Skeleton，总98,200跨网格通道不是独立表情数。43488最后WF005完成退出0，79508最终第1页保存退出0。recovery_session_settings_32420.json于14:17:50读回AutoSave=True（原值、无save_config），故无待恢复设置；run内restore_recovery_session.py/回执保存。monitor停止并由root工具确认automation PAUSED。当前实例若重启必须经target身份校验重新绑定ue_target，不能沿用旧PID/node。旧GPU日志、BM001原5件、failed_*材质报告及历次checkpoint全部保留，不执行清理。人工接受/全动画/正式渲染仍未声明。

CFD40收尾回执documentation_final_closure_v1.json与documentation_audit_final_delivery_v1.json由本节拥有，只记录既有交付/目录/文档检查，不新增测试矩阵或人工接受声明。
