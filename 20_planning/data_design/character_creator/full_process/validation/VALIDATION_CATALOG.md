# 可执行验证目录

> 文档角色：`validation_catalog`
> 状态：`current`
> 适用阶段：`WF-00..WF-09`
> 权威范围：`VAL-*` 的触发条件、准确入口、输出、通过条件和证明边界
> 上级入口：[`README.md`](./README.md)
> 上游：对应 Workflow 产生的输入与 artifacts
> 下游：对应 Gate 或 [`RECOVERY_RUNBOOK.md`](./RECOVERY_RUNBOOK.md)
> 最近核验：2026-08-17

## 1. 公共环境

```powershell
$LANCE_ROOT = 'D:\UE\Lance_Work'
$ccScriptRoot = "$LANCE_ROOT\00_engine\scripts\character_creator"
$bridgeRoot = "$LANCE_ROOT\00_engine\character_creator_bridge"
$bridgeClient = "$bridgeRoot\cc_bridge_client.py"
$ueScriptRoot = "$LANCE_ROOT\00_engine\scripts\unreal"
$outputRoot = "$LANCE_ROOT\00_engine\outputs"
$ueProject = 'datatry_02'
```

执行模式：`SYSTEM_PYTHON` 不导入 `RLPy/unreal`；`BRIDGE_CLI` 由 CC worker 执行 RLPy；`UE_REMOTE` 由已打开的 UE 执行 `unreal` 脚本；`UE_UI` 是人工编辑器操作。

## VAL-CODE-01 Python 与 Bridge 回归

- 阶段/触发：`WF-00`；Python、Bridge 或机器 JSON 修改后运行，不是每个角色都运行。
- 状态/模式：`production` / `SYSTEM_PYTHON`。
- 系统问题：纯 Python 编译、汇总和 Bridge 客户端逻辑是否仍通过单元测试。
- 输入：当前工作区代码与测试 fixtures。

```powershell
python -m unittest discover -s "$ccScriptRoot\tests" -p 'test_*.py'
python -m unittest discover -s "$bridgeRoot\tests" -p 'test_*.py'
```

- 输出/通过：两个退出码均为 0，无 `FAILED` 或 `ERROR`。
- 成功证明：纯 Python 和客户端回归通过。
- 不证明：CC/RLPy、UE、视觉或本地插件在线。
- 失败去向：停止生产，修代码或配置；恢复入口 `REC-MANIFEST-01` 或对应开发任务。

## VAL-BRIDGE-01 Bridge 与 RLPy 在线

- 阶段/触发：`WF-00`；每个新 CC 会话、重启或 Bridge 异常后。
- 状态/模式：`validated_pilot` / `BRIDGE_CLI`。
- 系统问题：当前 CC worker 是否在消费队列，并能通过 RLPy 读取场景。
- 输入：已由用户离线启动的 CC 和已安装 Bridge。

```powershell
python $bridgeClient health
python $bridgeClient ping
python $bridgeClient scene-summary
```

- 输出：heartbeat、ping/result JSON 和 scene summary。
- 通过：协议匹配；heartbeat 不超过 5 秒 lease；状态为 idle 或可解释 busy；ping 与 scene summary 成功。
- 成功证明：本次 CC instance 的文件队列与 RLPy 通道可用。
- 不证明：完整角色装配、MCP、UE 或视觉正确。
- 失败去向：`REC-BRIDGE-01`。

## VAL-MANIFEST-01 角色 Manifest 完整性

- 阶段/触发：`WF-01`；每次编译角色请求后。
- 状态/模式：`production` / `SYSTEM_PYTHON`。
- 系统问题：请求是否被确定性编译，并且所有 ID、组合和审核状态有效。
- 输入：由 [`WF-01`](../workflow/WF-01-CHARACTER-DEFINITION.md) 生成的 `$manifest`。

```powershell
$compiled = Get-Content -LiteralPath $manifest -Raw | ConvertFrom-Json
$compiled | Select-Object success,status,requested_character_count,character_count
$compiled.request_results | Select-Object character_id,status
if (-not $compiled.success) { throw 'Manifest compile failed' }
if ($compiled.requested_character_count -ne $compiled.character_count) { throw 'Character count mismatch' }
if (@($compiled.request_results | Where-Object status -ne 'compiled').Count -ne 0) { throw 'Rejected request result' }
```

- 输出/通过：命令退出 0；`success=true`；请求数等于角色数；全部状态为 `compiled`。
- 成功证明：Manifest 在当前注册表下可执行且无显式拒绝。
- 不证明：资产能在 CC 中加载、角色视觉正确或项目能保存。
- 失败去向：`REC-MANIFEST-01`。

## VAL-CC-01 BodyFit 重建烟测

- 阶段/触发：`WF-02`；BodyFit 源、哈希或比例配置变化后，或诊断身体漂移时。
- 状态/模式：`validated_pilot` / `BRIDGE_CLI + CC_RLPY`。
- 系统问题：锁定 BodyFit 能否重建且 Body/Junction 指纹不漂移。
- 输入：`cc_body_preset_library_v2.json` 和目标 preset；会替换 CC 场景。

```powershell
$jobId = 'bodyfit_smoke_20260806_001'
$library = "$ccScriptRoot\cc_body_preset_library_v2.json"
$ccOut = "$outputRoot\character_creator_bridge\artifacts\$jobId"
python $bridgeClient validate-bodies `
  --library-file $library `
  --preset-id M02_Average `
  --output-dir $ccOut `
  --confirm-scene-replace `
  --auto-dismiss-undo-warning `
  --job-id $jobId `
  --no-wait
python $bridgeClient wait $jobId --timeout 3600
python $bridgeClient result $jobId
```

- 输出：批次 `validation_result.json`，preset 下 `result.json`、源/重建向量、delta、眼球报告和前后截图。
- 通过：`failure_count=0`、`error=null`、源路径/哈希/expected fingerprint 匹配且无未登记 Body/Junction 漂移。
- 成功证明：该 preset 在当前环境可重建。
- 不证明：完整角色外观或其他九个 preset 正确。
- 失败去向：`REC-CC-01`；不要直接用系统 Python 运行 RLPy 文件。

## VAL-CC-02 完整角色结构与报告

- 阶段/触发：`WF-02/03`；每个完整角色。
- 状态/模式：`validated_pilot` / `SYSTEM_PYTHON + BRIDGE_CLI + CC_RLPY`。
- 系统问题：由 Workflow 生成的完整角色是否具备完整结构、必需报告和审核素材。
- 输入：`WF-01` Manifest、`WF-02` CC artifacts、`WF-03` summary/contact sheets。
- 产生样本的准确命令：[`WF-02 第 6 节`](../workflow/WF-02-CC-ASSEMBLY.md)；汇总命令：[`WF-03 第 6 节`](../workflow/WF-03-CC-ACCEPTANCE.md)。

```powershell
$batch = Get-Content -LiteralPath "$ccOut\validation_result.json" -Raw | ConvertFrom-Json
$summaryData = Get-Content -LiteralPath $summary -Raw | ConvertFrom-Json
if ($batch.failure_count -ne 0) { throw 'CC batch has failures' }
if (-not $summaryData.success) { throw 'Character summary failed' }
```

- 输出：每角色 result、眼球/指纹报告、必需视角和姿态、summary 与 contact sheets。
- 通过：无失败；Body/Junction 隔离、Facial Profile、眼球完整性、中性恢复和必需素材无缺项。
- 成功证明：装配输出机器结构完整，具备人工审核材料。
- 不证明：视觉已接受或 `.ccProject` 已正确保存；仍必须执行 `VIS-CC-01/02/03`。
- 失败去向：`REC-CC-01`、`REC-DIALOG-01` 或回到 `WF-01`。

## VAL-CC-03 Headshot 身份原型检查

- 阶段/触发：`RM-05B..RM-06`、`WF-03`；每个新 Headshot 原始项目保存后，以及 Facial Profile、Sculpt Morph 或规范身份项目变化后。
- 状态/模式：`validated_pilot` / `BRIDGE_CLI + CC_RLPY`。
- 系统问题：项目是否可重载，Profile 升级是否持久化，静态身份、动态姿态、眼球状态和来源完整性是否保持。
- 输入：性别对应的升级清单、冻结来源 `.ccProject` 和同性交付 CC5 HD Facial Profile；会替换当前 CC 场景，但不覆盖源项目。

```powershell
$jobId = 'headshot_profile_upgrade_female_<run_id>'
$library = "$ccScriptRoot\cc_headshot_female_cc5_hd_upgrade_v1.json"
$ccOut = "$outputRoot\character_creator_bridge\artifacts\headshot_profile_upgrade\female_<run_id>"
python $bridgeClient validate-bodies `
  --library-file $library `
  --output-dir $ccOut `
  --confirm-scene-replace `
  --auto-dismiss-undo-warning `
  --job-id $jobId `
  --timeout 1800
```

- 输出：`profile_upgrade_report.json`、`facial_pose_validation.json`、派生 `.ccProject`、来源/派生 Facial Profile、静态视角、Blink、轻笑、中笑、满笑、Jaw Open 和中性恢复证据。
- 机器通过：`success=true`；来源为 `CC4 Extended / 160`；派生并重载为 `CC5 MetaHuman / 379`；Profile persisted；静态 Morph、眼球结构和材质不变；bounds 在容差内；来源项目 SHA-256 不变；动态姿态门禁通过。
- 当前基准：`female_20260808_v2`、`male_20260808_v1`、`female2_20260808_v1`、`male2_20260808_v1` 均通过，Undo 匹配数均为 0。
- 生产通过：除机器通过外，必须由 `VIS-CC-04` 接受身份/侧面/三级 Smile，并在完整角色中由 `VIS-CC-02` 覆盖 Corrective、视线、眉毛、眯眼、睁大和左右不对称动作。
- 成功证明：该具体派生项目的 CC5 Profile 可持久化且机器未发现升级导致的身份、眼球或材质漂移。
- 不证明：完整 CC5 HD 角色转换、单张正面图推断的侧面几何准确、用户已接受身份相似度、project-seed 装配已实现或候选已进入 Face V3 生产池。
- 失败去向：`REC-CC-01`、`REC-DIALOG-01`，或回到 [`HEADSHOT_PIPELINE.md`](../cc_details/HEADSHOT_PIPELINE.md) 的派生副本修正流程。

## VAL-CC-04 Headshot 原型包完整性

- 阶段/触发：`RM-05B..RM-06`、`WF-01/03`；创建、复制、整理或修改 Headshot 原型包/中央注册表后。
- 身份计数门禁：已测量的 `nonzero_shaping_morph_count` 必须为 `0`；若候选批次未持久化该计数，只允许显式使用 `null + measurement_status=not_recorded_in_rm05c_batch`，并在验证结果中得到 `shaping_morph_count_verified=false`。这种候选可保留，但不能生产启用。
- 状态/模式：`validated_pilot` / `SYSTEM_PYTHON`。
- 系统问题：中央注册表、每个 `prototype.json`、身份项目、Profile、回退 Profile、可用参考图和哈希是否一致；缺少参考图的候选是否明确保持 `pending_user_mapping`；是否错误视觉通过或启用了未验收候选。
- 输入：`cc_headshot_face_prototype_registry_v1.json` 和规范原型根；不需要打开 CC，也不修改任何资产。

```powershell
$registry = "$ccScriptRoot\cc_headshot_face_prototype_registry_v1.json"
$report = "$outputRoot\character_creator_bridge\artifacts\headshot_face_prototype_registry_validation_<run_id>.json"
python "$ccScriptRoot\cc_validate_headshot_face_prototype_registry.py" `
  --registry $registry `
  --output $report
```

- 输出：原型数量、每个 manifest/asset 的路径、大小、SHA-256、source 映射状态、视觉状态和装配实现状态。
- 通过：退出码 0、`success=true`、所有已登记文件存在且大小/哈希一致、manifest ID/性别/状态一致；缺少 `source_reference` 时必须为 `pending_user_mapping` 且不得视觉通过；未完成视觉与装配的条目不得计入生产启用。
- 当前基准：`prototype_count=10`、`production_enabled_count=0`；10 个 source 均已映射且哈希通过，原 4 个视觉通过，新增 6 个保持 `pending_user_review`，其中 shaping Morph 精确计数仍未记录。最新报告为 `headshot_face_prototype_registry_validation_20260810_v4.json`。
- 成功证明：当前规范原型包的文件完整性和状态约束一致。
- 不证明：CC 可加载项目、视觉已接受、动态表情正确或 project-seed 装配可用；这些分别由 `VAL-CC-03`、`VIS-CC-04` 和后续装配验证证明。
- 失败去向：停止使用该 registry；从冻结来源或已有升级证据重建对应原型包，不直接修改哈希掩盖差异。

## VAL-CC-05 Headshot Project-seed + BodyFit Pilot

- 阶段/触发：`RM-05B..RM-06`、`WF-02/03`；首次把 Headshot 烘焙身份接到 BodyFit、修改装配顺序、比例参数、眼球稳定逻辑、保存重载逻辑或相关执行器后。
- 状态/模式：`validated_pilot` / `BRIDGE_CLI + CC_RLPY`。
- 系统问题：能否以 Headshot `.ccProject` 为身份起点，在不破坏 Face、眼球、材质和 Facial Profile 的前提下应用规范 BodyFit、头型与比例，并保存为可重载项目。
- 输入：`cc_headshot_project_seed_bodyfit_pilot_v1.json`；完整门禁固定包含女性 `F_HS_002 + H00 + F02_Average` 和男性 `M_HS_002 + H00 + M02_Average`。会替换当前 CC 场景并把最后一个保存项目留在场景中。

```powershell
$jobId = 'headshot_project_seed_bodyfit_<run_id>'
$library = "$ccScriptRoot\cc_headshot_project_seed_bodyfit_pilot_v1.json"
$output = "$outputRoot\character_creator_bridge\artifacts\headshot_project_seed_bodyfit_pilot\run_<run_id>"

python $bridgeClient validate-bodies `
  --library-file $library `
  --output-dir $output `
  --confirm-scene-replace `
  --auto-dismiss-undo-warning `
  --job-id $jobId `
  --timeout 1800
```

- 输出：每例的身份/BodyFit/组装三视图与全身图、五姿态动态图、重载图、Morph/眼球向量、保存 `.ccProject`、`result.json`，以及完整 `validation_result.json`。
- 机器通过：`success=true`、`success_count=2`、`failure_count=0`；当前执行器还要求 `selection_mode=complete_library` 与 `library_case_count=2`。两例 BodyFit 目标与 `head_scale -> neck_height` 顺序匹配；受保护 Morph 指纹、材质和眼球结构保持；保存重载 `passed=true` 且 Morph delta 为空；`CC5 MetaHuman / 379`、五姿态 liveness 与中性眼球完整性通过。
- 当前基准：`run_20260810_v4/validation_result.json` 为完整 `2/2` 机器权威；它生成于新增 `selection_mode/library_case_count` 汇总字段之前，完整性由 `requested_count=2`、结果集合和锁定清单的 `pilot_policy.case_count=2` 共同证明。修正全身灯光的男女单例只作为视觉派生证据。状态文件是 `cc_headshot_project_seed_bodyfit_pilot_validation_v1.json`。
- 人工通过：执行 `VIS-CC-04`，接受灰色 BodyFit 与组装全身比例、头身适配、身份三视图、闭眼、三级 Smile、Jaw Open、牙齿/嘴唇、眼球/眼睑以及重载一致性。
- 成功证明：当前两个 H00 + 平均 BodyFit 案例可以按项目种子路线装配、保存和重载，且机器未发现受保护状态漂移。
- 不证明：其余三个头型、其他 8 个 BodyFit、四个原型全部组合、外观/服装/发型、生产随机化或 UE 导出已经通过。
- 失败去向：`REC-CC-01` 或 `REC-DIALOG-01`；若只需定位性别单例，可显式传一个 `--preset-id`，但显式子集不得替代完整 2/2 权威。

## VAL-CC-06 服装源包机器目录

- 阶段/触发：`WF-03`；首次盘点服装来源，或 female/male 源目录新增、删除、替换 ZIP/散装资产后。
- 状态/模式：`active_development` / `SYSTEM_PYTHON`。
- 系统问题：所有源包是否可读、来源存在、包 ID 唯一、ZIP 哈希有效、内部 CC 资产能按真实类型分类，并且预览复制没有越出 artifacts。
- 输入：`D:\BaiduNetdiskDownload\人物和服装\female` 与 `...\male`；源目录只读，不需要打开 CC。

```powershell
$inventoryRoot = "$outputRoot\character_creator_bridge\artifacts\clothing_source_inventory\inventory_20260811_v1"

python "$ccScriptRoot\cc_inventory_clothing_sources_v1.py"
python "$ccScriptRoot\cc_make_clothing_source_inventory_review_v1.py"

$inventory = Get-Content -Encoding UTF8 -Raw -LiteralPath "$inventoryRoot\inventory.json" | ConvertFrom-Json
if (-not $inventory.validation.success) { throw 'Clothing inventory validation failed' }
if ($inventory.validation.checked_archive_count -ne $inventory.validation.readable_archive_count) { throw 'Unreadable clothing archive' }
if ($inventory.validation.unique_package_id_count -ne $inventory.summary.package_count) { throw 'Duplicate package IDs' }
```

- 输出：`inventory.json`、受限预览副本、248 张逐包卡片、分页审查图和 `review/index.json`。
- 当前基准：1330 个物理文件、38.83 GiB、61/61 ZIP 可读、248 个源包、231 个服装候选、2596 个服装条目、1 组精确重复 ZIP、10 组内部资产清单重复。
- 通过：脚本退出 0；`validation.success=true`；错误数 0；全部 ZIP 可读；来源路径和 SHA-256 有效；包 ID 唯一；所有复制预览位于本轮 output 下。
- 成功证明：当前来源可以在不解压服装本体的情况下被确定性盘点、分类和追溯。
- 不证明：目录标签对应真实性别适配、服装能在 CC 加载、Look 搭配合理、无穿模、十体型兼容或 UE 可切换。
- 失败去向：停止源筛选；修复损坏/缺失来源或索引器后以新 output 目录重跑。不要删除旧源包来掩盖失败。

## VAL-CC-07 服装 Look 极端体型静态机器门禁

- 阶段/触发：`WF-03`；family JSON、鞋规则、代表 Look 抽样、BodyFit 来源、装配器或加载兼容注册表变化后，以及每个恢复分片执行时。
- 状态/模式：`machine_complete_static_visual_accepted` / `CC_BRIDGE`；重跑时要求用户按离线许可约束启动 CC，Bridge `healthy/idle`，且 RAM、commit、VRAM 均高于软边界。
- 系统问题：每个代表 Look 能否在同性瘦/胖/矮三个已验收角色上确定性重建；全部必选资产是否逐项加载且未被后续资产驱逐；来源配饰是否按本门禁策略清除；毛发是否保留；五个标准视角是否完整写入。
- 输入：当前完整 gate `cc_outfit_compatibility_gate_20260816_v3.json`；最终复核使用 `cc_outfit_compatibility_resume_plan_20260816_v6.json`，确认 159 已完成、0 未完成。最后恢复执行使用 `outfit_compatibility_chunks_20260816_r14/chunk_*.json`，每个分片只含一个完整 Look / 三个 BodyFit。

```powershell
$chunk = "$ccScriptRoot\outfit_compatibility_chunks_20260816_r14\chunk_01.json"
$run = "$outputRoot\character_creator_bridge\artifacts\outfit_compatibility_gate\run_20260816_chunks_v14\chunk_01"

python $bridgeClient health
python $bridgeClient validate-bodies `
  --library-file $chunk `
  --output-dir $run `
  --confirm-scene-replace `
  --timeout 3600
```

- 加载兼容门禁：完整 gate 构建时读取 `00_engine/assets/character_creator/outfit_compatibility_aliases/compatibility_alias_registry.json`。只允许字节完全相同的扩展名调度别名；来源/别名大小或 SHA-256 漂移、策略不匹配、未登记 `.ccGloves` 均直接失败。
- 逐 Look 通过：`validation_result.json` 中三个案例全部成功、15 张图存在且非空、必选件驱逐 0、选择重置失败 0、阻塞弹窗 0；完成后立即联合检查 RAM、commit 与 VRAM。
- 当前基准：159/159 案例、53/53 个完整 Look、795 图已发布，机器失败和发布失败均为 0；最终复核剩余 0。用户静态决定记录在 `cc_outfit_visual_review_20260816_v1.json`，受审索引冻结为 `reviewed_index_20260816_v1.json`。
- 成功证明：来源和项目可重载，代表组合能在三个极端 BodyFit 中完成静态装配、库存核对和五视角采集。
- 不证明：人工视觉无穿模、动作姿态兼容、该 family 的全部组内组合、其余七个 BodyFit、UE 运行时换装或生产批准。机器通过后仍必须进入 `VIS-CC-05`。
- 失败去向：保留失败输出，不发布不完整 Look；先区分资产加载、必选件驱逐、已知 Undo 弹窗、资源边界和视觉问题。达到任一软边界先执行资源释放探针，未全部恢复则停在 Look 边界并由用户离线重启 CC；Agent 不得自行重启。

## VAL-CC-08 服装 Look 动作压力机器门禁

- 阶段/触发：`WF-03/07`；`VAL-CC-07` 与服装静态人工审查通过后，或服装装配、BodyFit 来源、动作采样实现发生变化时。
- 状态/模式：`complete_user_spot_check_accepted` / `CC_BRIDGE`。正式批次 53/53 Look、583/583 图、机器失败 0、最终 inventory 匹配 53/53；用户于 2026-08-17 抽查门户并报告未发现问题，门户 `2026-08-16-outfit-motion-stress-gate-v1` 为 `approved`。权威执行状态为 `cc_outfit_motion_stress_execution_state_20260816_v1.json`，人工决定为 `cc_outfit_motion_visual_review_20260817_v1.json`，当前无续跑分片。
- 系统问题：每个代表 Look 能否在同性重体型上加载并完整执行两条诊断动作，按动画全长取得非重复采样图，且动作结束后可清理并恢复中性状态。
- 输入：`cc_outfit_motion_stress_gate_20260816_v3.json` 或 `outfit_motion_stress_chunks_20260816_v3/chunk_*.json`。当前范围为 53 个 Look；女性使用 `F04_Heavy`，男性使用 `M04_Heavy`。动作是同性 HD Walk 与通用 `Full Body.iMotionPlus` 校准动作，每条按 `0.0/0.2/0.4/0.6/0.8` 归一化位置采样。v3 还冻结静态审查时的资产应用顺序、已观察到的必要替换和最终 inventory；动作装配必须与该证据完全一致。

```powershell
$chunk = "$ccScriptRoot\outfit_motion_stress_chunks_20260816_v3\chunk_27.json"
$run = "$outputRoot\character_creator_bridge\artifacts\outfit_motion_stress_gate\manual_recheck_chunk_27_v1"

python $bridgeClient health
python $bridgeClient validate-bodies `
  --library-file $chunk `
  --output-dir $run `
  --confirm-scene-replace `
  --auto-dismiss-undo-warning `
  --timeout 3600
```

- 单例通过：1 张静态参考和 10 张动作图存在且非空；两条 motion 都完成 5 个采样；加载失败、未授权的必选件驱逐、未知弹窗和动作清理失败均为 0；最终 inventory 与冻结静态证据完全一致。只有冻结证据明确记录的同对象替换才允许发生。
- 当前 Smoke：Windows 长路径失败已通过短确定性案例目录修复；固定帧只覆盖动画开头的问题已改为全时长归一化采样；Walk + Full Body Calibration 单例为 1/1、动作图 10/10、Undo 0，且画面人物完整居中、姿态确有变化。
- 结果发布：`build_outfit_motion_stress_run.py` 递归合并正式分片，为每个 Look 生成 1 张静态参考、5 张 Walk 和 5 张 Full Body Calibration 的 11 图总览；真实 Smoke 已验证。构建器默认读取人工决定文件，因此重新发布不会退回等待审查。正式结果使用 `register_run.py ...\2026-08-16-outfit-motion-stress-gate-v1\run.json --replace` 注册到统一门户。
- 成功证明：当前确定性 Look 能在两种代表性关节活动负载下完成加载、采样和清理。
- 人工结论：用户采用抽查方式审查已发布证据并报告未发现问题；抽查数量未记录，因此只关闭当前动作压力等待状态，不生成 53 条逐 Look 人工决定。
- 不证明：视觉上绝对无穿模、所有生产动作、所有组内服装组合、全部十体型、头发-头部服装兼容或 UE 运行时安全。`VIS-CC-05` 的完整生产范围仍是部分完成。
- 范围边界：两条动作只是诊断负载，不得写入生产动画池。后续动画盘点、P0 动态 Gate 和 UE Pilot 已另行完成；当前可用边界以 [`CURRENT_STATUS.md`](../CURRENT_STATUS.md) 为准，剩余扩展归入 `RM-09R`。
- 失败去向：保留案例目录与失败报告；若为视觉穿模则标记 `rejected/conditional`，若为资源软边界则运行释放探针并停在完整 Look 边界，若出现未知弹窗则立即停止等待用户。

## VAL-BUNDLE-01 CC 导出 Bundle 完整性

- 阶段/触发：`WF-04`；每个导出 Bundle。
- 状态/模式：`manual_verified` / `SYSTEM_PYTHON` 外层文件检查。
- 系统问题：FBX、同名 JSON、纹理和追溯来源是否形成一个版本化整体。
- 输入：本轮 `$bundle` 和预期 `$baseName`。

```powershell
$fbx = Get-Item -LiteralPath (Join-Path $bundle "$baseName.Fbx")
$json = Get-Item -LiteralPath (Join-Path $bundle "$baseName.json")
$textures = @(Get-ChildItem -LiteralPath (Join-Path $bundle 'textures') -File)
if ($textures.Count -eq 0) { throw 'No exported textures' }
Get-FileHash -LiteralPath $fbx.FullName,$json.FullName -Algorithm SHA256
```

- 输出：文件清单、大小和哈希，随后写入导出追溯记录。
- 通过：FBX/JSON 同基名、非空、纹理存在，来源项目/Manifest/版本字段齐全。
- 成功证明：Bundle 文件结构与来源可追溯。
- 不证明：FBX 可在 UE 正确导入或材质视觉正确。
- 失败去向：`REC-XFER-01`。

## VAL-XFER-01 M02 完整参考导入

- 阶段/触发：`WF-05`；每个角色首次导入或 Bundle/插件/导入设置变化后。
- 状态/模式：`validated_pilot` / `UE_UI`；当前无通用自动验收器。
- 系统问题：同一 Bundle 是否在 UE 中形成正确完整参考角色。
- 输入：M02 基准 Bundle 或待验证新 Bundle、Auto Setup 2.03、空的新 Vendor 目标。
- 准确导入步骤：[`WF-05 第 6 节`](../workflow/WF-05-UE-IMPORT-REFERENCE.md)。
- 输出：UE Skeletal Mesh、Skeleton、材质/Rig Logic 资产、Output Log 和路径记录。
- 通过：导入无未解释错误，所需 Skeleton/Morph/材质存在，并通过 `VIS-XFER-01`。
- 成功证明：该具体 Bundle 的完整参考导入成功。
- 不证明：模块拆分、其他 BodyFit、服装/头发切换或动画正确。
- 失败去向：`REC-XFER-01` 或 `REC-UE-01`。

## VAL-UE-01 M02 v002 Morph 广播

- 阶段/触发：`WF-06`；模块 Blueprint、组件或 Morph 广播变化后。
- 状态/模式：`validated_pilot` / `UE_REMOTE`。
- 系统问题：M02 v002 是否保持 20 组件、13 个面部支持组件与非面部隔离。
- 输入：已打开 `datatry_02`，不在 PIE，Remote Execution 可用。

```powershell
python "$ueScriptRoot\ue_remote_exec.py" `
  --project $ueProject `
  --script "$ueScriptRoot\ue_validate_m02_face_morph_broadcaster.py"
```

- 输出：`$outputRoot\unreal_character_import\m02_face_morph_broadcaster_validation.json`。
- 通过：`success=true`、`errors=[]`、Blueprint 为 v002、组件数 20、面部组件数 13。
- 成功证明：登记 Morph 对支持组件广播并隔离非面部组件。
- 不证明：v002 全结构通用回归、十体型或视觉正确；旧 v001 验证器不能替代。
- 失败去向：`REC-UE-01`。

## VAL-UE-02 M02 v003 身体/面部矩阵

- 阶段/触发：`WF-07`；动画导入、分类、面部片段或 AnimBP 分层变化后。
- 状态/模式：`validated_pilot` / `SYSTEM_PYTHON → UE_REMOTE + PIE`。
- 系统问题：两条身体动作与五种面部状态能否重组，且不破坏组件和 neck/head。

```powershell
python "$ueScriptRoot\run_m02_face_hybrid_pie_review_v003.py"
```

- 输出：`m02_face_hybrid_review_v003\pie_review.json` 和 10 张截图；可选执行 `ue_make_m02_face_hybrid_review_sheet_v003.py`。
- 通过：`success=true`、`errors=[]`、矩阵 2×5、10 案例、每角色 20/19 组件、无 follower 丢 Leader，曲线/骨骼误差在容差。
- 成功证明：当前 M02 登记组合在测试矩阵内成立。
- 不证明：任意新动画、服装、毛发、道具或场景成立。
- 失败去向：`REC-UE-01`；固定输出重跑先执行 `REC-EVIDENCE-01`。

## VAL-UE-03 M02 Elder Morph 矩阵

- 阶段/触发：`WF-07`；Elder 快照、Morph 支持组件或表情共存逻辑变化后。
- 状态/模式：`validated_pilot` / `SYSTEM_PYTHON → UE_REMOTE + PIE`。
- 系统问题：同一 M02 身份的年龄 Morph 是否连续，并能与 Blink、Smile、Jaw Open 共存。

```powershell
python "$ueScriptRoot\run_m02_elder_morph_pie_review.py"
```

- 输出：`m02_elder_morph_review_v001\request.json`、`pie_review.json` 和 6 张截图。
- 通过：`success=true`、`errors=[]`、Morph 为 `Full_Face_Elder`、20 组件、6 案例、支持组件一致、曲线传播开启。
- 成功证明：该 M02 同身份、同拓扑快照年龄 Pilot 成立。
- 不证明：任意随机脸、其他 BodyFit、替换毛发/服装或身体老化成立。
- 失败去向：`REC-UE-01`；固定输出重跑先执行 `REC-EVIDENCE-01`。

## VAL-UE-04 F02/M02 FullReference P0 运行时矩阵

- 阶段/触发：`WF-07`；P0 Motion、curve-only Face clip、AnimBP、FullReference Wrapper 或 Post Process 策略变化后。
- 状态/模式：`validated_pilot` / `SYSTEM_PYTHON → UE_REMOTE + PIE`。
- 系统问题：四个身体状态与四个直接 Morph 面部状态能否在 F02/M02 FullReference 上组合，并避免 Post Process 与 Morph 重复求值造成眼区伪影。
- 前置条件：`datatry_02` 已打开、Remote Execution 在线、Main 关卡可进入 PIE；Wrapper 的唯一 SkeletalMeshComponent 必须设置 `disable_post_process_blueprint=true`。

```powershell
python "D:\UE\Lance_Work\00_engine\scripts\unreal\run_p0_runtime_validation.py"
```

- 输出：`p0_runtime_pilot_20260819_v1\runtime_review\pie_runtime_review.json`、`visual_review_decision.json`、24 张原图和 `p0_runtime_pilot_contact_sheet.png`。
- 通过：`automatic_success=true`、`visual_review=passed`、16/16 案例、24/24 图片、错误 0、四个 Body 快照均记录 Post Process 已禁用；Natural Blink 双眼曲线至少 0.90，Asymmetric Blink 左眼至少 0.90 且右眼不超过 0.06。
- 成功证明：当前 F02/M02 FullReference 的 Walk/Idle/Understood 与 Neutral/Natural Blink/Asymmetric Blink/Subtle Smile 直接 Morph 组合在该矩阵内成立。
- 不证明：eye-bone gaze、模块 follower、任意新动画、全部 P0、三发型、道具、十体型或生产批准成立。eye-bone + curve 证据仍由 `VAL-UE-02` 提供。
- 恢复：外层入口在 `finally` 中退出 PIE 并运行 cleanup；结束后仍需确认 Main 中不存在 `DM_P0_*` 临时 Actor。失败去向为 `REC-UE-01`，覆盖固定输出前先执行 `REC-EVIDENCE-01`。

## VAL-SCENE-01 场景与相机结构

- 状态：`planned`；阶段 `WF-08`。
- 计划问题：角色、道具、场景、相机和 Sequence 是否无碰撞/遮挡且全时段可渲染。
- 当前命令/输出：无。实现前不得登记通过。

## VAL-DATASET-01 数据集一致性

- 状态：`planned`；阶段 `WF-09`。
- 计划问题：媒体帧、GT、sidecar、配置、版本和哈希是否一一对应。
- 当前命令/输出：无。实现前不得登记通过。

## 2. 证据与命名

新验证使用 `%LANCE_ROOT%\00_engine\outputs\<subsystem>\<run_id>`。至少保存请求或 Manifest、终态报告、自动检查结果、视觉证据和错误日志。当前三个 UE Pilot 的固定输出目录是已披露例外，按 `REC-EVIDENCE-01` 保护旧证据。
