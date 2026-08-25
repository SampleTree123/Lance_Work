# 按 Workflow 组织的实现文件索引

> 文档角色：`implementation_reference`
> 状态：`current`
> 适用阶段：`WF-00..WF-09`
> 权威范围：生产阶段到 Python、JSON、UE 资产和证据的映射
> 上级入口：[`README.md`](./README.md)
> 上游：当前代码、机器 JSON、UE 资产和输出
> 下游：Workflow 复现与故障定位
> 最近核验：2026-08-24

本文回答“某个 Workflow 实际使用什么文件”。生产顺序和命令以对应 `WF-*` 为准，测试命令以 [`VALIDATION_CATALOG.md`](../validation/VALIDATION_CATALOG.md) 为准，精确参数和 ID 以机器 JSON 为准。

```text
CC_SCRIPT_ROOT = D:\UE\Lance_Work\00_engine\scripts\character_creator
BRIDGE_ROOT    = D:\UE\Lance_Work\00_engine\character_creator_bridge
UE_SCRIPT_ROOT = D:\UE\Lance_Work\00_engine\scripts\unreal
OUTPUT_ROOT    = D:\UE\Lance_Work\00_engine\outputs
CC_ASSET_ROOT  = D:\UE\Lance_Work\00_engine\assets\character_creator
VISUAL_PORTAL  = D:\UE\Lance_Work\00_engine\visualization_portal
```

## WF-00 会话预检

| 类型 | 文件/对象 | 作用 |
| --- | --- | --- |
| Bridge 配置 | `BRIDGE_ROOT\bridge_config.json` | 协议、lease、allowlist 和执行器路径 |
| CC worker | `BRIDGE_ROOT\plugin\main.py` | CC OpenPlugin 消费者 |
| CLI | `BRIDGE_ROOT\cc_bridge_client.py` | health、ping、scene-summary 和 job 操作 |
| 协议 | `BRIDGE_ROOT\protocol_v1.md` | request/result/heartbeat 线契约 |
| Undo/致命弹窗守卫 | `BRIDGE_ROOT\cc_undo_dialog_guard.ps1` | 精确处理已知 Undo 警告；精确识别 FBX 内容授权阻塞时只点击 `OK`、写入 `fatal_dialog.json` 并让执行器失败收口，不点击 `Buy`、不绕过检查 |
| 状态 | `OUTPUT_ROOT\character_creator_bridge\state\heartbeat.json` | 当前 CC instance 与活动 job |

阶段所有者：[`WF-00`](../workflow/WF-00-SESSION-PREFLIGHT.md)。

## WF-01 角色定义与 Manifest

| 类型 | 文件 | 作用 |
| --- | --- | --- |
| 编译器 | `cc_compile_character_manifest.py` | 请求解析、组合验证和确定性 Manifest |
| BodyFit | `cc_body_preset_library_v2.json` | 十个源项目、哈希和身体指纹 |
| 比例 | `cc_head_bodyfit_scale_decisions_v1.json` | Head Scale / Neck Height |
| Face recipes | `cc_face_recipes_v3_200.json` | 当前 200 条 Face V3 配方 |
| 外观 catalog | `cc_appearance_asset_catalog_v1.json` | 稳定 asset ID 到本地路径 |
| 兼容登记 | `cc_appearance_compatibility_v1.json` | 通过/拒绝组合与证据状态 |
| 面部 Registry | `cc_facial_production_registry_v1.json` | 池、顺序、年龄、色素与 QA |
| Headshot 候选 Registry | `cc_headshot_face_prototype_registry_v1.json` | 烘焙身份项目包、状态和 manifest 哈希；当前不进入生产 Face V3 |
| Headshot 十候选扩展批次 | `cc_headshot_rm05c_source_batch_v1.json` | 新增 6 个来源、检查报告、升级报告、冻结 SHA-256 与目标原型 ID |
| Headshot 十候选来源映射 | `cc_headshot_rm05c_source_reference_mapping_v1.json` | `F_HS_003..005`、`M_HS_003..005` 到六张原照片的显式路径与 SHA-256；禁止猜测映射 |
| Headshot 头型安全区间 | `cc_headshot_skull_safe_ranges_v1.json` | 人工批准的 7 个单轴范围；规范多轴档案已选定并通过机器动态门禁 |
| Headshot 规范头型选择 | `cc_headshot_skull_profile_selection_v1.json` | 固化 `H00 Base`、`H01 Long Deep`、`H02 Low Flat`、`H03 Narrow Shallow` 的人工选择与来源候选映射 |
| Headshot 规范头型门禁 | `cc_headshot_skull_profile_validation_v1.json` | 两性 `8/8` 动态机器结论、结果哈希、用户动态验收和下游 Pilot 状态 |
| Headshot project-seed Pilot | `cc_headshot_project_seed_bodyfit_pilot_v1.json`、`cc_headshot_project_seed_bodyfit_pilot_validation_v1.json` | 固定 F02/M02 平均体型两例、装配顺序、机器结论、视觉状态和证据哈希 |
| 暂存 | `CC_SCRIPT_ROOT\runtime_staging\<run_id>\request.json/manifest.json` | Bridge allowlist 内动态输入 |

阶段所有者：[`WF-01`](../workflow/WF-01-CHARACTER-DEFINITION.md)。

## WF-02 CC 装配

| 类型 | 文件 | 作用 |
| --- | --- | --- |
| 外层入口 | `BRIDGE_ROOT\cc_bridge_client.py validate-bodies` | 提交兼容 Manifest |
| RLPy 执行器 | `cc_validate_body_reconstruction.py` | CC 内加载、装配、检查和截图；只对已有正负单轴证据的 7 个头型 Morph 处理临时 signed-bounds 误报 |
| Headshot 检查清单 | `cc_headshot_{female,male}{,2,3,4,5}_project_inspection_v1.json` | 10 个冻结来源项目的静态与基础动态检查输入 |
| Headshot 升级清单 | `cc_headshot_{female,male}{,2,3,4,5}_cc5_hd_upgrade_v1.json` | 10 个冻结来源到派生 CC5 Profile 的受控升级输入 |
| Headshot 十候选暂存器 | `cc_stage_headshot_rm05c_prototypes_v1.py` | 校验新增 6 人的 inspection/upgrade/source hash，创建不可变候选包并原子扩展中央 Registry；拒绝覆盖已有 ID |
| Headshot 来源附加器 | `cc_attach_headshot_source_references.py` | 按显式配置幂等复制 `source_reference.jpg`，校验前后哈希并原子更新 manifest/Registry；不一致时失败 |
| Headshot 头型单轴扫描 | `cc_build_headshot_skull_axis_sweep_v2.py`、`cc_headshot_skull_axis_sweep_v2.json` | 从两个规范原型生成基线与 7 个 Morph 的扩大范围扫描清单 |
| Headshot 多轴头型候选 | `cc_build_headshot_skull_composition_candidates_v1.py`、`cc_headshot_skull_composition_candidates_v1.json` | 生成 `C00..C08` 两性共享候选；每个最多 3 轴并受归一化联合幅度门禁约束 |
| Headshot 规范头型库 | `cc_build_headshot_skull_profile_library_v1.py`、`cc_headshot_skull_profile_library_v1.json` | 将人工选择编译为 4 个共享规范档案和男女 8 个确定性动态门禁案例 |
| Headshot project-seed 清单 | `cc_build_headshot_project_seed_bodyfit_pilot_v1.py`、`cc_headshot_project_seed_bodyfit_pilot_v1.json` | 编译 H00 + F02/M02 两例，锁定 Headshot 项目、Profile、BodyFit、比例与输出契约 |
| Headshot project-seed 执行器 | `cc_validate_body_reconstruction.py` / `headshot_project_seed_bodyfit_pilot` | 以烘焙身份项目为种子，应用 Body/Junction、头型和比例，保存重载并执行动态门禁 |
| Profile API 探针 | `cc_facial_profile_api_probe_v1.json` | 枚举当前 RLPy Profile/Save 能力；诊断使用 |
| 存储探针 | `cc_face_prototype_storage_probe_v1.json` | 评估 Profile/AvatarPreset 载体；`AvatarPresetAll` 当前禁止生产 |
| 目标初始化 | `cc_targeted_morph_initialization.py` | 只修改登记 Morph，保护未授权状态 |
| 材质档案 | `cc_face_material_quality_profile_v1.json` | 角膜与头部皮肤质量参数 |
| Headshot 原型根 | `CC_ASSET_ROOT\face_prototypes\v1\<prototype_id>` | 身份项目、Profile、回退、参考图、证据与 manifest |
| 产物 | `OUTPUT_ROOT\character_creator_bridge\artifacts\character_build_<run_id>\cc` | result、指纹、眼球报告和截图 |

阶段所有者：[`WF-02`](../workflow/WF-02-CC-ASSEMBLY.md)。

## WF-03 CC 验收与保存

| 类型 | 文件 | 作用 |
| --- | --- | --- |
| 汇总 | `cc_summarize_character_integration_v1.py` | 汇总每角色机器结果 |
| 联系表 | `cc_make_character_integration_contact_sheets_v1.py` | 生成静态/动态人工审核材料 |
| Headshot 包校验 | `cc_validate_headshot_face_prototype_registry.py` | 离线校验 registry、manifest 和全部资产哈希；缺少原图或 shaping 计数时禁止生产启用 |
| 特定保存基准 | `cc_character_showcase_10_20260803_v1.json` | 已含 `save_character_projects=true` 的十体型 showcase |
| 证据 | `character_build_<run_id>\summary.json`、`review\`、request/manifest 副本 | Gate 输入 |
| 可视化门户 | `VISUAL_PORTAL\index.html`、`assets\app.js`、`data\registry.json` | 按日期/任务索引结果分支并进行 A/B 审查 |
| Run 登记 | `VISUAL_PORTAL\tools\register_run.py`、`runs\<run-id>\run.json` | 校验并登记新的视觉结果，不复制原始大图 |
| Headshot 单轴审查转换 | `cc_make_headshot_skull_axis_sweep_sheets_v2.py`、`VISUAL_PORTAL\tools\build_headshot_skull_axis_run.py` | 生成总览/视角矩阵并转换为门户 schema 1 run |
| Headshot 多轴候选转换 | `cc_make_headshot_skull_profile_review_sheets_v1.py`、`VISUAL_PORTAL\tools\build_headshot_skull_composition_run.py` | 汇总候选静态证据；用户选择后将门户 run 更新为 `approved` |
| Headshot 多轴候选证据 | `OUTPUT_ROOT\character_creator_bridge\artifacts\headshot_skull_composition_candidates\review_20260809_v1`、`VISUAL_PORTAL\runs\2026-08-09-headshot-skull-composition-candidates-v1\run.json` | `18/18` 有效案例、54 张原始图、男女三视角评审图和已固化选择 |
| Headshot 动态门禁转换 | `cc_make_headshot_skull_dynamic_review_sheets_v1.py`、`VISUAL_PORTAL\tools\build_headshot_skull_dynamic_gate_run.py` | 生成男女六姿态总览、同姿态横向对比和动态门户 run；机器与用户验收已通过 |
| Headshot 动态门禁证据 | `OUTPUT_ROOT\character_creator_bridge\artifacts\headshot_skull_profile_dynamic_gate\review_20260809_v1`、`VISUAL_PORTAL\runs\2026-08-09-headshot-skull-profile-dynamic-gate-v1\run.json` | 精确执行清单、两性 `8/8` 结果、72 张原始图和动态视觉评审入口 |
| Headshot project-seed 评审转换 | `cc_make_headshot_project_seed_bodyfit_pilot_sheets_v1.py`、`VISUAL_PORTAL\tools\build_headshot_project_seed_bodyfit_pilot_run.py` | 合并完整机器运行的面部/动态/重载证据与修正灯光全身图，生成男女评审图和门户 run |
| Headshot project-seed Pilot 证据 | `OUTPUT_ROOT\character_creator_bridge\artifacts\headshot_project_seed_bodyfit_pilot\run_20260810_v4`、`review_20260810_v1`、`VISUAL_PORTAL\runs\2026-08-10-headshot-project-seed-bodyfit-pilot-v1\run.json` | 完整 `2/2` 机器权威、修正灯光视觉证据、保存项目和已批准用户验收入口 |
| Headshot 十原型评审转换 | `cc_make_headshot_identity_pool_review_sheets_v1.py`、`VISUAL_PORTAL\tools\build_headshot_identity_pool_run.py` | 生成男女各 5 人的原照片身份匹配页和 7 个视角/姿态横向联系表，并转换为门户 schema 1 run |
| Headshot 十原型证据 | `OUTPUT_ROOT\character_creator_bridge\artifacts\headshot_identity_pool_10\review_20260810_v2`、`VISUAL_PORTAL\runs\2026-08-10-headshot-identity-pool-10-v2\run.json` | 10/10 机器通过且 source 全部映射；原 4 人视觉通过，新增 6 人等待视觉验收，生产启用 0 |

普通编译器尚无通用保存开关。阶段所有者：[`WF-03`](../workflow/WF-03-CC-ACCEPTANCE.md)。

## 服装源发现与 Look 开发

本节是生产系统扩展，不是每个角色都重复执行的 Workflow。当前已完成源发现、人工精选、male/female 物理规范及全部 41 个 family JSON；Look 几何门禁、十体型和 UE 文件会在实现后追加。

| 类型 | 文件/对象 | 作用 |
| --- | --- | --- |
| 源索引器 | `cc_inventory_clothing_sources_v1.py` | 只读扫描 female/male、ZIP 内部成员和散装 CC 资产，复制受限预览并生成分类/重复报告 |
| 审查图 | `cc_make_clothing_source_inventory_review_v1.py` | 为每个源包生成卡片和分页总览；无预览包明确标记需 CC 检查 |
| Portal 转换 | `VISUAL_PORTAL\tools\build_clothing_source_inventory_run.py` | 把审查索引转换为 portal schema 1 |
| 日期重组器 | `cc_reorganize_clothing_by_date_v1.py` | 支持固定 2022 和 `newest-half-per-sex` 两种包级门禁、跨男女载荷去重及独立审查库复制；默认只 dry-run |
| 重组校验器 | `cc_validate_clothing_date_reorganization_v1.py` | 对 ZIP 和散装目录执行源/目标完整 SHA-256、路径、大小和额外文件校验 |
| 人工审查队列 | `cc_build_clothing_review_queue_v1.py` | v2 生成 56 个主队列包和 22 个日期不明包的可填写 CSV 与中文审查说明，并可发布到筛选结果根 |
| 物理目录规范器 | `cc_normalize_outfit_directories_v1.py` | 默认 dry-run；将服装族根资产归入六个主体槽位、`_Accessories-Pending` 或 `Full-body/Locked-Bundle`，执行时逐文件 SHA-256 校验并在失败时回滚 |
| Family JSON Schema | `outfit_family_v1.schema.json` | 定义 confirmed family 的资产追溯、组装模式、互斥约束和证据字段 |
| 确认/延后规则 | `cc_outfit_confirmed_rules_v1.json` | 完整划分 41 个 male/female family；当前 41 个 confirmed、0 个 deferred；家族专用配饰显式区分 required/optional，复杂服装以互斥 slot group 表达 |
| Family JSON 生成器 | `cc_build_confirmed_outfit_family_json_v1.py` | 校验 family 分区和 100% 资产覆盖，生成 `explicit_looks/slot_groups/locked_bundle` JSON；允许互斥 group 复用同一资产，并支持 group 级固定/可选家族配饰；原子写入并回读，默认不覆盖 |
| Explicit→Slot Group 迁移器 | `cc_migrate_explicit_outfits_to_slot_groups_v1.py` | 将旧规则中的 24 个 `explicit_looks` family 合并为按槽位自由选择的 `slot_groups`；迁移前拒绝槽位形状或家族配饰策略不一致。迁移当时得到 37 个 slot-group family、4 个 locked-bundle family、51 个逻辑组；后续 Cheer Leader 从 1 个错误自由组拆为 3 个匹配组，当前为 53 个逻辑组 |
| Family JSON 独立验证器 | `cc_validate_outfit_family_library_v1.py` | 重算规则与资产哈希并逐文档比较；拒绝 deferred family JSON 和未登记 JSON |
| Family JSON 测试 | `tests/test_cc_outfit_family_json_v1.py` | 覆盖漏资产拒绝、`.ccShoes` 语义槽修正、互斥 group 资产复用、group 级家族配饰、写入回读和 deferred 隔离 |
| Explicit→Slot Group 迁移测试 | `tests/test_cc_migrate_explicit_outfits_to_slot_groups_v1.py` | 覆盖 24→0 的模式迁移、资产池去重、Full-body 单选池语义及不一致槽位/配饰策略拒绝 |
| 共享鞋池规范器 | `cc_organize_shared_shoes_v1.py` | 对照 family JSON 找回遗漏鞋，按 SHA-256 合并完全相同副本，生成男女独立连续编号、初步样式目录和机器清单；默认 dry-run，执行时保留完整源备份 |
| 筛选后鞋池终结器 | `cc_finalize_curated_shoes_v1.py` | 校验用户筛选边界，将当前鞋按最终类别连续重编号，生成 schema 2 清单、旧新路径映射与删除审计；执行时先完整备份并在失败时回滚 |
| 男女共享鞋整合器 | `cc_integrate_cross_sex_shoes_v1.py` | 登记 8 双女性批准副本，允许同几何具有男女独立 ID、禁止同性别重复；生成 schema 3 清单，并恢复/验证误移的家族原配鞋 |
| 共享鞋分配草稿生成器 | `cc_build_shared_shoe_assignment_draft_v1.py` | 从 41 个 family 中排除 26 个有原配鞋的 family，为其余 15 个生成空候选池、特殊审查标记和按性别/类别汇总的可用 ID；默认拒绝覆盖用户输入 |
| 服装极端体型门禁生成器 | `cc_build_outfit_compatibility_gate_v1.py` | 从当前规则动态读取全部逻辑组，各确定性抽取一个 Look，并展开到同性瘦、胖、矮三个已验收角色；当前 v3 为 53 个 Look、159 例、795 图。构建时读取兼容别名注册表，严格校验来源/别名大小与 SHA-256；未注册的 `.ccGloves` 会被拒绝 |
| 服装动作压力门禁生成器 | `cc_build_outfit_motion_stress_gate_v1.py` | 从静态 gate 为每个 Look 选择同性重体型，登记 Walk 与 Full Body Calibration 两条诊断动作、全时长五点归一化采样和短确定性输出目录；权威 v3 额外读取冻结静态审查索引，保存实际资产应用顺序、允许替换和最终 inventory 签名。生成 53 案例、583 图计划及 27 个小分片。诊断动作不属于生产动画池 |
| 服装动作压力生成器测试 | `tests/test_cc_build_outfit_motion_stress_gate_v1.py` | 覆盖同性重体型选择、动作哈希、归一化采样、短路径和分片完整性 |
| 服装动作压力网页生成器 | `VISUAL_PORTAL\tools\build_outfit_motion_stress_run.py` | 递归合并正式分片、校验每例 1+5+5 图完整性、去重重跑结果，为每个 Look 生成固定两行动作总览；默认读取人工决定文件，使重建后保持抽查接受状态，并明确诊断动作不属于生产动画池 |
| 服装动作压力网页测试 | `VISUAL_PORTAL\tests\test_outfit_motion_stress_run.py` | 覆盖嵌套检查点发现、11 图完整案例、总览生成、等待审查状态和抽查接受决定；门户测试当前 10/10 |
| 服装门禁恢复计划生成器 | `cc_build_outfit_compatibility_resume_plan_v1.py` | 合并一个或多个已完成检查点，按完整 Look 排除已完成案例并生成资源门禁分片；不属于当前 gate 的历史案例会被忽略并写入审计，不再阻断恢复。最终权威复核计划 `cc_outfit_compatibility_resume_plan_20260816_v6.json` 合并 28 个检查点，确认 159/159 已完成、0 未完成、0 恢复分片；实际最后六组由 `r14` 的 6 个单 Look 分片执行 |
| 服装加载兼容别名 | `00_engine\assets\character_creator\outfit_compatibility_aliases\compatibility_alias_registry.json` | 仅允许 `extension_dispatch_alias_only` 且要求字节完全相同；当前登记 Redsoul 手套 1 项，`.ccGloves` 来源与 `.ccCloth` 别名大小和 SHA-256 相同，2/2 探针通过。来源资产不可修改 |
| F01 证据修复计划生成器 | `cc_build_outfit_f01_correction_plan_v1.py` | 从成功检查点定位已发布的 F01 案例，生成源配饰清除 Smoke 及重拍分片；Smoke 已通过，用户决定保留旧图，生成的四个重拍分片均标为禁止执行 |
| 服装门禁执行器 | `cc_validate_body_reconstruction.py` 的 `outfit_compatibility_gate` / `outfit_motion_stress_gate` 模式 | 静态模式每例重载来源项目、清除原服装和源配饰、保留 `GetHairs`，按槽位顺序应用资产并捕获五个全身视角；动作模式验证动作文件大小/哈希，按实际片段长度把归一化位置换算为帧并采集动作图。v3 动作模式只允许冻结静态证据登记的精确替换，并在动作前要求最终 inventory 签名完全相同；其余必选件驱逐和未知弹窗均失败。JSON 原子替换针对 Windows 短暂 `PermissionError` 做 10 次有限退避重试 |
| JSON 检查点写入重试测试 | `tests/test_cc_validate_body_reconstruction_write_json.py` | 覆盖短暂 `PermissionError` 后成功替换，以及连续 10 次失败后正确抛错；测试中禁用真实等待，不依赖 CC/RLPy |
| CC 资源释放探针 | `cc_validate_body_reconstruction.py` 的 `resource_release_probe` 模式、`cc_resource_release_probe_20260815_v1.json` | 删除当前一次性测试角色、清空 Qt 图片缓存并执行三轮 Python GC；两次实测各释放约 1.1 GiB 显存，但不能释放全部 CC 原生缓存 |
| 累计门户生成器 | `VISUAL_PORTAL\tools\build_outfit_compatibility_gate_progress_run.py` | 合并初始长批与多个重启输出，只发布三个 BodyFit 均完整的 Look，去重并生成累计联系表与 portal run；不属于当前 gate 的旧 Look 会被忽略并写入审计，产物链接使用调用时传入的实际 gate 路径；重建成功后删除不再被当前 run 引用的旧编号汇总图 |
| 机器目录 | `OUTPUT_ROOT\character_creator_bridge\artifacts\clothing_source_inventory\inventory_20260811_v1\inventory.json` | 248 个源包、真实内部资产、SHA-256、槽位、重复组和机器验证 |
| 日期重组清单 | `OUTPUT_ROOT\character_creator_bridge\artifacts\clothing_date_reorganization\reorg_20260811_v2_newest50\manifest.json` | 当前 v2：131 个逻辑包；56 主队列、53 较旧半区、22 日期不明 |
| 日期重组验证 | `...\reorg_20260811_v2_newest50\validation.json` | 131 包、1309 文件、36,213,453,075 字节完整校验，0 错误 |
| 人工精选目录规范证据 | `OUTPUT_ROOT\character_creator_bridge\artifacts\clothing_structure_normalization\run_20260812_v1` | 288 个移动文件哈希通过；后置 dry-run 为 0；规范执行时 male/female 为 41 个服装族、349 个可穿戴资产，后续用户清理见当前状态 |
| Family JSON 证据 | `OUTPUT_ROOT\character_creator_bridge\artifacts\outfit_family_rules\run_20260814_v4_all_slot_groups`；Cheer 修正 dry-run 位于 `OUTPUT_ROOT\character_creator_bridge\artifacts\outfit_family_rules\cheer_leader_rule_correction_20260815_v1` | 当前 41 个 confirmed JSON、332 个登记资产、37 个 slot-group family、4 个 locked-bundle family、53 个逻辑组、0 个 deferred；Cheer Leader 已从一个错误自由组拆为三个同编号匹配组 |
| 共享鞋池证据 | `OUTPUT_ROOT\character_creator_bridge\artifacts\shoe_library_organization\run_20260814_v1` | 从 60 个活动文件与 2 个遗漏来源恢复出 58 双唯一鞋；4 份完全重复副本合并；女性 17、男性 41；包含迁移报告和迁移前完整备份 |
| 筛选后鞋池证据 | `OUTPUT_ROOT\character_creator_bridge\artifacts\shoe_library_organization\run_20260814_v2_curated_reindex` | 用户筛选后的 52 双鞋全部连续重编号：女性 17、男性 35；记录 6 个删除项、52 条旧新路径映射、schema 2 清单和执行前完整备份 |
| 男女共享鞋整合证据 | `OUTPUT_ROOT\character_creator_bridge\artifacts\shoe_library_organization\run_20260814_v3_cross_sex` | 当前 schema 3：60 个性别资产、52 套唯一几何、8 对男女同几何；恢复 2 双误移原配鞋，51 双原配鞋哈希通过，服装族验证 41/41、0 错误 |
| 共享鞋分配草稿证据 | `OUTPUT_ROOT\character_creator_bridge\artifacts\shoe_assignment\draft_20260814_v1\shared_shoe_assignment_draft.json` | 15 个无原配鞋槽 family：女性 11、男性 4；全部用户字段保持空白，4 个集成鞋疑似项显式标记；发布副本位于 `both/shared_shoe_assignment_draft.json` |
| 服装门禁累计证据 | `VISUAL_PORTAL\runs\2026-08-15-outfit-compatibility-gate-progress-v1\run.json` | 当前 v3 为 159/159 案例、53/53 个完整 Look、795 图；机器失败和发布失败均为 0。旧 Cheer Leader `default` 与 Redsoul 失败诊断均未发布；修复后的正式结果与最终 `r14` 六组已发布；F01 旧右侧证据仍按用户决定保留。该证据不等于 `VIS-CC-05` 人工穿模批准 |
| 服装静态人工决定 | `cc_outfit_visual_review_20260816_v1.json`、`...\cumulative_review_20260815_v1\reviewed_index_20260816_v1.json` | 用户接受服装-身体和服装层级静态结果；受审索引以 SHA-256 冻结。头发-头部服装冲突延期，动作、十体型和 UE 仍未批准 |
| 服装动作压力 Smoke | `OUTPUT_ROOT\character_creator_bridge\artifacts\outfit_motion_stress_gate\pilot_20260816_v1\smoke_04` | Walk + Full Body Calibration 单例 1/1、动作图 10/10、Undo 0；验证短路径和全动画归一化采样；正式批次完成状态见下两项 |
| 服装动作压力执行状态 | `cc_outfit_motion_stress_execution_state_20260816_v1.json` | 权威 gate v3；27 个分片、53/53 Look、583/583 图、机器失败 0、inventory 匹配 53/53；状态 `complete_user_spot_check_accepted`，无续跑点。文件中的 `ready_not_started` 是该检查点当时的动画池状态，不代表当前主线；现状见 `CURRENT_STATUS.md` |
| 服装动作压力人工决定 | `cc_outfit_motion_visual_review_20260817_v1.json`、`...\cumulative_review_20260816_v1\reviewed_index_20260817_v1.json` | 用户报告抽查已发布结果且未发现问题；冻结 gate 与不可变 review-index 快照哈希，明确抽查数量未知、不声称 53 个 Look 逐项签字，并保留头发冲突、十体型和 UE 边界 |
| 服装动作压力审查门户 | `VISUAL_PORTAL\runs\2026-08-16-outfit-motion-stress-gate-v1\run.json` | 53 个分组、53 个唯一 `preset_id`、每组 11 图；机器失败 0，状态 `approved`，决定栏明确为 sampled acceptance。该状态允许开始动画池建设，不等于最终服装生产批准 |
| 审查索引 | `...\inventory_20260811_v1\review\index.json` | 248 张逐包卡片、分页总览和来源路径 |
| 门户入口 | `VISUAL_PORTAL\runs\2026-08-11-cc-clothing-source-inventory-v1\run.json` | 当前 `pending_review` 的源筛选入口 |
| 技术规范 | `full_process\cc_details\OUTFIT_PIPELINE.md` | source family、Look、替换组、十体型和 UE 边界 |

机器门禁为 `VAL-CC-06`。本节成功只证明源可读、可追溯、可分类；后续真实 Look 仍需 CC 静态/动态与十体型门禁。

## 动画源发现与生产池开发

本节记录动画资产池开发所用的一次性整理工具和已固化证据。它属于系统开发，不是 `WF-07` 每个角色重复执行的运行步骤。

| 环节 | 文件/证据 | 作用与当前结果 |
| --- | --- | --- |
| 包级整理器 | `00_engine\scripts\character_creator\cc_organize_animation_pack_tiers_v1.ps1` | 严格校验 57 个预期顶层条目、目标路径与碰撞后，用 PowerShell `Move-Item` 整理；不解压、不删除。源根已整理后再次执行会因源清单不匹配而停止 |
| 源根清单 | `D:\BaiduNetdiskDownload\iclone动作\_animation_pack_tier_manifest_v1.json` | 记录 P0 11、P1 10、P2 6、P3 30，共 57 个源包；P0-P3 只表示候选审查优先级 |
| 执行清单副本 | `OUTPUT_ROOT\character_creator_bridge\artifacts\animation_pack_organization\run_20260817_v1\result.json` | 与源根清单 SHA-256 一致。整理后独立回读核验得到目标缺失 0、旧位置残留 0、根目录额外项 0；递归资产仍为 57 个压缩包和 113 个既有 `.rlMotion`。这些核验结论不是 `result.json` 内的独立字段 |
| P0 静态清点生成器 | `00_engine\scripts\character_creator\cc_inventory_p0_animation_sources_v1.py` | 用 Python `zipfile` 和本机 UnRAR 只读列出压缩包成员，记录来源、哈希、扩展名、性别/语义/依赖文件名提示；不解压、不修改源 |
| P0 清点测试 | `00_engine\scripts\character_creator\tests\test_cc_inventory_p0_animation_sources_v1.py` | 3/3，覆盖只读 ZIP 清点、唯一 ID、生产状态恒为未批准，以及手机、场景、双人、相机等保守依赖提示 |
| P0 权威静态 inventory | `OUTPUT_ROOT\character_creator_bridge\artifacts\animation_source_inventory\p0_20260817_v3\inventory.json` | 11/11 包和压缩包可读；611 `.rlMotion` + 56 `.iMotion` = 667。性别提示为女 302、男 267、未知 98；生产批准 0 |
| P0 静态审查队列 | `OUTPUT_ROOT\character_creator_bridge\artifacts\animation_source_inventory\p0_20260817_v3\review_queue.json` | 85 个 `standalone_first`、152 个语境动作、430 个道具/场景/双人依赖延后项；只决定动态审查顺序 |
| P0 Pilot 选择规范 | `00_engine\scripts\character_creator\cc_p0_animation_pilot_20260817_v1.json` | 冻结 16 条均衡候选：F02/M02 各 8 条；成员身份只表示动态审查范围，不继承生产批准 |
| P0 白名单提取器 | `00_engine\scripts\character_creator\cc_build_p0_animation_pilot_v1.py` | 只提取选择规范引用的 ZIP 成员；校验源包大小/SHA-256、成员大小/CRC、输出 SHA-256 和重复内容，原子发布 Pilot 目录，不修改源包；发布前恢复继承 ACL，确保桌面 CC 进程可读取 Sandbox 生成的白名单文件 |
| P0 提取回归测试 | `00_engine\scripts\character_creator\tests\test_cc_build_p0_animation_pilot_v1.py` | 3/3，覆盖只提取白名单且源包不变、拒绝非首轮候选、拒绝字节重复动作 |
| P0 Pilot 清单与待审表 | `OUTPUT_ROOT\character_creator_bridge\artifacts\animation_p0_pilot\pilot_20260817_v1\pilot_manifest.json`、`dynamic_review.json` | 16 条内容哈希唯一，11 `.rlMotion` + 5 `.iMotion`；该冻结时点仍记录 `pending_cc_dynamic_review/not_approved`，后续视觉结论由独立决定文件追加，不回写历史清单 |
| P0 动态 Gate 生成器 | `00_engine\scripts\character_creator\cc_build_p0_animation_dynamic_gate_v1.py` | 从 Pilot、BodyFit v2、F02/M02 项目和 Lightroom 重算哈希，生成两 actor、16 动作、每条 5 个归一化采样点的 Gate；安全默认值为保留 Lightroom 当前相机与源项目 yaw、禁用旧自动构图、启用动作首帧 Root 对齐；支持哈希锁定恢复子集，不产生批准 |
| P0 动态 Gate 配置 | `00_engine\scripts\character_creator\cc_p0_animation_dynamic_gate_20260818_v3.json` | 当前正式全量配置：16 动作、80 图；按 actor 各加载项目一次，兼容测试 11 `.rlMotion` 和 5 `.iMotion`；`camera_mode=lightroom_current`、`align_motion_start_to_source=true` |
| P0 动态 Gate 执行器 | `cc_validate_body_reconstruction.py` 的 `animation_p0_dynamic_gate` 模式 | 复用精确 Undo 守卫和动作播放；加载 Lightroom 后不再用独立相机覆盖固定灯光关系。每条动作先把首帧 Root 对齐源项目 Root，再从平移前 `RL_BoneRoot` 样本生成位移证据；后续采样只为截图临时跟随并立即恢复，不污染 Root 分类 |
| P0 动态主批与恢复证据 | `OUTPUT_ROOT\character_creator_bridge\artifacts\animation_p0_dynamic_gate\run_20260818_v8_lit_review`、`OUTPUT_ROOT\character_creator_bridge\artifacts\animation_p0_lighting_scout\start_aligned_20260818_v1` | 正式主批 16/16、80/80 图、失败 0、Undo 0；`p0_009_city_walk_normal_m` 因动作自带非零首帧 Root 产生偏移，定向重采 1/1、5/5 图后按案例覆盖。旧 2026-08-17 批次仅保留为修复前审计 |
| P0 动态累计验证 | `OUTPUT_ROOT\character_creator_bridge\artifacts\animation_p0_dynamic_gate\cumulative_review_20260818_v2_lit\consolidated_validation.json` | 权威摘要：16/16、失败 0、80 张明亮原图；7 `moving_candidate`、9 `in_place_candidate`、16 `none_detected`、隐藏 Prop 0；用户视觉状态 `accepted`，生产批准仍为 0 |
| P0 动态门户生成器 | `VISUAL_PORTAL\tools\build_animation_p0_dynamic_gate_run.py` | 合并正式 v8 与 `p0_009` 起始 Root 对齐恢复证据，校验每条 5 图、图片尺寸和 SHA-256，从平移前样本重算 Root 分类，生成 16 张动作总览和独立 portal run |
| P0 动态审查门户 | `VISUAL_PORTAL\runs\2026-08-17-cc-animation-p0-dynamic-gate-v1\run.json` | 16 个动作、80 张 1024×1024 原图；状态 `approved`。详情视角切换会按当前动作的实际帧键重建，不再沿用首组键；门户批准只代表视觉自然度通过 |
| P0 用户视觉决定 | `00_engine\scripts\character_creator\cc_p0_animation_visual_review_20260818_v1.json` | 哈希绑定 Gate 和两个来源验证；用户完整检查 16 条并报告未发现不自然现象。没有逐条书面备注，不分配循环/复用策略，也不直接批准生产 |
| P0 动态 Gate 回归测试 | `tests/test_cc_build_p0_animation_dynamic_gate_v1.py`、`tests/test_cc_animation_p0_dynamic_gate_executor_v1.py` | 当前测试全部通过；覆盖哈希漂移、批准泄漏、恢复子集、安全相机默认值、首帧 Root 对齐、Root 优先级、截图临时偏移与面部通道分类；提取器回归另为 3/3 |
| P0 门户测试 | `VISUAL_PORTAL\tests` | 13/13；覆盖决定哈希/全量范围和切组详情视角重建。当前 run 资源曾完成 99/99 HTTP 200 校验，修复后首组 `t050_f0113` 与末组 `t050_f0100` 精准 HTTP 检查均为 200 |
| P0 候选策略 | `00_engine\scripts\character_creator\cc_p0_animation_candidate_policy_20260818_v1.json` | 为 16 条分配动作角色、性别偏好、循环/一次性意图、Root Motion 政策、面部复用政策和已知限制；策略本身不产生生产批准 |
| P0 候选注册表生成器 | `00_engine\scripts\character_creator\cc_build_p0_animation_candidate_registry_v1.py` | 哈希校验 Pilot、动态累计证据、用户视觉决定、策略文件和每个提取动作；拒绝 Root 政策冲突、面部批准泄漏与源漂移 |
| P0 候选注册表 | `OUTPUT_ROOT\character_creator_bridge\artifacts\animation_p0_candidate_registry\registry_20260818_v1\candidate_registry.json` | 16 条：3 循环候选、13 一次性、7 保留源 Root Motion、9 原地、16 `replaceable`；状态 `registered_pending_ue_runtime_validation`，生产批准 0 |
| P0 UE Pilot 规范 | `00_engine\scripts\character_creator\cc_p0_animation_ue_pilot_spec_20260818_v1.json` | 固定 `CCSHOW_F02_AVERAGE_001` 和 `CCSHOW_M02_AVERAGE_001` 两个已生成穿衣项目，禁止灰色体型模板；选择女走路、男走路、原地循环、一次性手势四类动作 |
| P0 UE Pilot 工作单生成器 | `00_engine\scripts\character_creator\cc_build_p0_animation_ue_pilot_work_order_v1.py` | 校验候选状态、穿衣槽位、Showcase 汇总、角色项目 SHA-256、四个代表角色和动作政策，再生成 CC 导出与 UE 门禁顺序 |
| P0 UE Pilot 工作单 | `OUTPUT_ROOT\character_creator_bridge\artifacts\animation_p0_ue_runtime_pilot\work_order_20260818_v1\work_order.json` | `ready_for_cc_export`；2 个穿衣角色、4 条动作，要求 Skeleton、Root、循环接缝、一次性结束、面部叠加、服装变形和头发/服装冲突验证；生产批准 0 |
| P0 注册表与 UE Pilot 测试 | `tests/test_cc_build_p0_animation_candidate_registry_v1.py`、`tests/test_cc_build_p0_animation_ue_pilot_work_order_v1.py` | 4/4 + 4/4；覆盖源漂移、视觉决定漂移、Root 冲突、未穿衣角色、项目漂移和错误循环绑定 |
| P0 CC 导出配置 | `00_engine\scripts\character_creator\cc_p0_animation_ue_export_20260818_v1.json` | 哈希锁定工作单和两个 Bridge 可读穿衣项目，定义短 staging 路径、参考角色名、四个动作名及源时间线预期 |
| P0 CC 导出执行器 | `cc_validate_body_reconstruction.py` 的 `animation_p0_ue_runtime_export` 模式 | 临时清除每个源项目的 1 Body + 1 Face 预览片段但不保存源项目；导出 2 个完整参考角色与 4 个 Motion-only ASCII FBX，移动动作保留 Root，Idle/手势原地化 |
| P0 动作骨骼名修补器 | `00_engine\scripts\character_creator\cc_patch_unreal_animation_fbx_ascii.py` | 单次扫描生成修补 47 个辅助骨骼名 token 的诊断候选；2026-08-19 UE 实测后确认该 `_UE5_Patched.fbx` 不作为本轮权威输入，实际运行时导入使用哈希锁定 `_UE5_ASCII.fbx` |
| P0 晋升重写与终检 | `cc_rebase_p0_animation_ue_export_v1.py`、`cc_finalize_p0_animation_ue_export_v1.py` | staging 晋升后重写报告绝对路径，并复核工作单、FBX/JSON、材质目录、动作补丁报告和 SHA-256，生成机器 Manifest |
| P0 UE 导入 Bundle | `D:\UE\exports\character_creator\p0_ue_runtime_pilot_20260818_v1\export_bundle_manifest.json` | F02/M02 两个穿衣参考角色、4 条动作，2 条保留 Root、2 条原地；角色与 Motion 均已通过 P0 UE 技术门禁，历史 Bundle 生产状态保持 `not_approved` |
| P0 UE 参考导入/验证器 | `00_engine\scripts\unreal\ue_import_p0_runtime_pilot.py` | 执行 Bundle 哈希预检、F02/M02 分阶段原始导入与 Auto Setup 后验收；实际检查网格、Skeleton、全部材质实例槽、HQ/LWHQ 皮肤、Morph、PhysicsAsset、蓝图、IK Rig 和 Retargeter |
| P0 UE 参考验证报告 | `OUTPUT_ROOT\unreal_character_import\p0_runtime_pilot_20260819_v1\female_reference_validation.json`、`male_reference_validation.json` | F02 为 113 资产、32 材质槽、497 Morph；M02 为 127 资产、36 材质槽、501 Morph；两者 `success=true` |
| P0 UE Motion 导入/验证 | `00_engine\scripts\unreal\ue_import_p0_runtime_motions.py`、`ue_validate_p0_runtime_motions.py` | 将四个权威 ASCII FBX 绑定 F02/M02 Skeleton 导入 DataMake；检查 60 fps、帧数、Root 位移政策、循环候选/一次性结束和资产设置，报告 `motion_runtime_validation.json` 通过 |
| P0 运行时组合构建器 | `00_engine\scripts\unreal\ue_build_p0_runtime_composition.py` | 为 F02/M02 各生成四个零骨骼面部片段、一个 Body/Face AnimBP 和一个 FullReference Wrapper；Wrapper 固定 `disable_post_process_blueprint=true`，避免 RL Post Process 与直接 Morph 重复求值眼区 |
| P0 运行时 PIE 验收 | `00_engine\scripts\unreal\run_p0_runtime_validation.py` 及 `ue_stage/ue_run/ue_cleanup_p0_runtime_validation.py` | 自动暂存四个 Actor，验证 4 身体状态 × 4 面部状态、24 张图并清理临时 Actor；准确报告位于 `OUTPUT_ROOT\unreal_character_import\p0_runtime_pilot_20260819_v1\runtime_review` |
| P0 UE 审查门户 | `VISUAL_PORTAL\runs\2026-08-19-ue-p0-runtime-pilot-v1\run.json` | 16/16 组合、24/24 图；技术视觉门禁通过。只批准 FullReference direct-Morph Pilot，不声明 eye-bone gaze，不产生生产批准 |
| P0 CC 导出回归测试 | `tests/test_cc_p0_animation_ue_export_v1.py` | 4/4；覆盖导出配置/工作单绑定、穿衣项目哈希、输出命名、Root 策略和终检契约 |
| 首批身份库生成器与注册表 | `00_engine\scripts\character_creator\cc_build_first_batch_identity_library_v1.py`、`cc_first_batch_identity_library_20260820_v1.json` | 冻结 `F_ID01..04`、`M_ID01..04` 的身份配方、BodyFit 和源资产；组装证据位于 `OUTPUT_ROOT\character_creator_bridge\artifacts\first_batch_identity_assembly\run_20260820_complete` |
| 首批 16 Look 生成器与配置 | `cc_build_first_batch_full_reference_looks_v2.py`、`cc_first_batch_full_reference_looks_20260820_v2.json` | 生成每身份两套服装的环形 16 Look；女性 O04 显式覆盖为 `YogaPants_B + CasualJacket_C + Pump Heel_B`，并哈希校验替换资产 |
| 首批 16 Look CC Bundle | `D:\UE\exports\character_creator\first_data_batch_20260820_v1` | 16 个 `.ccProject`、16 个 FBX/JSON/`.fbm` 均完整；最终合并审计 `OUTPUT_ROOT\character_creator_bridge\artifacts\first_batch_full_reference_assembly\final_audit_20260820_v1.json` 为 16/16、失败 0 |
| 首批 FullReference 回归 | `tests/test_cc_build_first_batch_full_reference_looks_v2.py`、`tests/test_cc_outfit_export_optional_textures.py` | 6/6；覆盖 O04 固定替换、16 Look 唯一输出，以及“只有 JSON 引用布料权重图时才要求额外 `textures\` 目录” |
| 首批 32 Look 扩展定义 | `cc_build_first_batch_full_reference_looks_v3.py`、`cc_first_batch_full_reference_looks_20260822_v3.json`、`cc_first_batch_look_matrix_20260822_v1.json` | 把 8 身份扩为每身份 4 套同性服装；定义保留原 16 与 missing-16 的来源区分，当前 32 个唯一 Look 已全部生产 |
| 首批 missing-16 CC 工单 | `cc_first_batch_full_reference_missing_looks_20260822_v1.json`、`run_first_batch_missing_looks_export.ps1` | 只提交缺失的 8 女 + 8 男组合；`run_20260822_missing16_v1` 为 16/16、失败 0，现有 16 个 Bundle 未覆盖；证据位于 `OUTPUT_ROOT\character_creator_bridge\artifacts\first_batch_full_reference_expansion\run_20260822_missing16_v1` |
| 首批 32 Look 合并审计 | `cc_audit_first_batch_full_reference_matrix_v1.py`、`tests/test_cc_audit_first_batch_full_reference_matrix_v1.py` | 复核新旧 32 个 Project/FBX/JSON/FBM 的路径、大小和 SHA-256；`final_audit_20260822_v1.json` 为 32/32、失败 0、partial 目录 0，并正确允许 JSON 未引用权重图时不存在额外 `textures\` 目录 |
| 首批 12 动作 Gate 生成器 | `00_engine\scripts\character_creator\cc_build_first_batch_action_gate_v2.py` | 从用户更新后的目录冻结女性 6、男性 6 个动作；生成哈希锁定注册表、Pilot/Gate 输入和短运行时镜像，不修改源目录 |
| 首批动作注册表与 Gate | `00_engine\scripts\character_creator\cc_first_batch_action_registry_20260820_v2.json`、`cc_first_batch_action_gate_20260820_v2.json` | 精确登记替换后的 12 个物理动作文件；每个性别 6 条，配置图中每个 Look 仍只见 6 条同性动作 |
| 首批动作 CC 机器证据 | `OUTPUT_ROOT\character_creator_bridge\artifacts\first_batch_action_selection\dynamic_run_20260820_v1`、`visual_review_20260820_v1` | 12/12 动作、60/60 图、机器失败 0；全部未检测到面部通道和隐藏 Prop，视觉批准待用户在门户确认 |
| 首批动作 5 秒审查媒体 | `OUTPUT_ROOT\character_creator_bridge\artifacts\first_batch_action_full_preview\review_20260820_v2_5s\action_window_manifest.json` | 12/12 视频可访问；9 条哈希一致旧采集复用、3 条替换动作重采；替换动作原始帧的窄横带比例问题已由 `cc_repair_first_batch_action_preview_aspect_v1.py` 修复并保留修复前 Manifest；4 条短源采用两端 Idle 衔接，最终窗口签字待完成 |
| 首批动作窗口选择页 | `00_engine\visualization_portal\action-window-review.html`、`assets\action-window-review.js`、`visualization_portal\serve.py` | 读取上述 Manifest；支持 HTTP Range 精确 seek、等待 seek 完成后播放固定 5 秒窗口、0.1 秒起点精度、短片 Idle 补时提示、本地持久化、12 项确认进度和带源视频 SHA-256 的决定 JSON 导出 |
| 首批动作 v3 增量替换 | `cc_build_first_batch_action_gate_v3.py`、`cc_first_batch_action_full_preview_delta_20260820_v3.json`、`cc_merge_first_batch_action_review_v3.py` | 最终替换 `F02` 为 `CatchBreath.iMotion`、`M04` 为 `LivingRoom_Swing_M.rlMotion`；仅采集这 2 条，并按动作文件、预览视频和选择 JSON 的 SHA-256 继承、锁定 v2 中已确认的 10 个五秒窗口。选择页通过 `selection=` 加载继承种子，最终仍导出完整 12 条决定 JSON |
| 首批动作 v4 许可替换与最终窗口 | `cc_prepare_first_batch_action_replacements_v4.py`、`cc_first_batch_action_registry_20260821_v4.json`、`OUTPUT_ROOT\character_creator_bridge\artifacts\first_batch_action_replacements\review_20260821_v4_5s_full` | 用 `Sexy Dance`、`Battle Dance`、`Cheer Hands & Step Dance` 替换 3 条无法导出的动作；3/3 动态门禁通过，继承 9 条旧窗口并签署 3 条新窗口，最终 12/12 冻结在 `first_batch_action_window_selection\frozen_20260821_v4\frozen_action_windows.json` |
| 首批 10 动作生产池 | `cc_first_batch_action_pool_20260824_v1.json` | 从 12 条已验证源中排除 F04 Audience 09 与 M03 Audience 12；冻结每性别 5 条、F02 Catch Breath 唯一 InPlace 例外，以及表情只渲染不编辑的契约 |
| 首批动作窗口冻结工具 | `00_engine\scripts\character_creator\cc_ingest_first_batch_action_window_selection_v1.py`、`tests\test_cc_ingest_first_batch_action_window_selection_v1.py` | 接收门户导出的决定 JSON；严格校验 12/12 确认状态、动作/视频哈希、时间边界和短片补时，生成供 CC 导出与 UE 配置继续消费的冻结清单 |
| 首批 UE 导入机器清单 | `00_engine\scripts\dataset\build_first_batch_required_exports_v1.py`、`first_batch_required_exports_20260824_v3.json` | 当前资产导入清单冻结 32 Bundle、10 个生产 Motion 和三种已验证表情候选；正式配置图只引用 Happy，仍需生成与 2026-08-24 Schema 一致的新源 Manifest；旧 v1/v2/v3 不直接充当正式节点源 |
| 首批 FullReference UE 导入器 | `00_engine\scripts\unreal\ue_import_first_batch_full_reference_looks.py` | 严格读取可参数化机器清单和报告根，执行单 Look 源哈希预检、FBX 导入、Auto Setup 后验收、同性交付 Skeleton 归一化、保存及 Mesh/Morph/HQ 材质/Rig 门禁；既可导入也可对既有资产重验 |
| 首批 FullReference 外层编排 | `00_engine\scripts\unreal\run_first_batch_full_reference_import.py`、`ue_reallusion_dialog_watcher.py`、`tests/test_run_first_batch_full_reference_import.py` | `--expanded-matrix` 使用 32-Look 清单；逐 Look 调用 UE Remote Execution，精确处理已知 FBX/Auto Setup 窗口并等待实际关闭。代码硬限制新交互导入每个 UE 会话最多 3 个 Look，并拒绝同时使用 `--continue-on-error`；守卫与 UE 必须同权限，未知窗口失败停止 |
| 首批 FullReference UE 证据 | `OUTPUT_ROOT\unreal_character_import\first_batch_full_reference_expansion_20260822_v2\aggregate_import_gate.json` 及 32 份 `*_import_validation.json` | 32/32 通过、失败 0、源预检 32/32、目标目录 32；全部 Mesh、Morph、HQ/Auto Setup 材质、Rig、Skeleton 归一化和同性交付复用契约通过 |
| 首批头部皱纹材质修复 | `00_engine\scripts\unreal\ue_patch_first_batch_head_wrinkle_textures.py` | `audit/apply/restore` 三模式；检查并修复 32 个 Look 的 `CM/WM/RM/HM/NormalMap_Blend` 共 13 个纹理槽，保留基础肤色与法线 |
| 首批头部皱纹验收状态 | `VAL-XFER-02` | 2026-08-23 已确认 32/32 Look、416/416 参数匹配且占位纹理为 0；诊断报告、A/B 帧和临时 UE 资产已在验收后清理，需要时由正式修复脚本重新生成 |
| 首批动作 UE 导出工作单 | `cc_build_first_batch_action_ue_export_v1.py`、`cc_first_batch_action_ue_export_20260820_v1.json`、`OUTPUT_ROOT\character_creator_bridge\artifacts\first_batch_action_ue_export\work_order_20260820_v1\work_order.json` | 计划导出 2 个参考角色和 12 个 Motion-only FBX；当前 staging 只写出女性参考角色，随后被 CC 内容导出授权对话框阻断，不是可导入 Bundle |
| 首批动作导出阻塞证据 | `OUTPUT_ROOT\character_creator_bridge\artifacts\first_batch_action_ue_export\staging_20260820_v1\blocked_attempt_summary.json`、`fatal_dialog.json`、`fatal_recovery_guard.jsonl` | 精确记录 CC 消息和失败作业：1 个参考 FBX、0 个 Motion FBX、`promotion_allowed=false`；必须由用户处理内容授权/打包状态，禁止绕过或将 staging 晋升 |
| 首批 Motion UE 导入与规范化 | `prepare_first_batch_motion_fbxs.py`、`run_first_batch_motion_import.py`、`ue_import_first_batch_motions.py`、`tools/fbx_motion_normalizer` | 历史 12/12 Motion FBX 已通过；当前入口读取 v3 清单，只处理生产池中的 10 条。Raw 118 轨、BodyOnly 108 轨，五秒窗口与面部支撑轨移除门禁通过 |
| Day 02 静态运行时门禁 | `ue_validate_first_batch_day2_runtime.py`、`OUTPUT_ROOT\unreal_character_import\first_batch_day2_20260822_v1\day2_runtime_gate.json` | 基线 Look 的 Happy/Angry/Sad Morph、12 个 BodyOnly 动作和 6 个规范表情 clip 均通过静态契约；与后续动态证据共同构成 Day 02 自动门禁 |
| Day 02 动态六例编排 | `run_first_batch_expression_dynamic_review.py --canonical-first-batch`、`ue_stage_first_batch_expression_review.py`、`ue_bootstrap_first_batch_expression_dynamic_review.py`、`ue_capture_first_batch_expression_dynamic_review.py`、`ue_cleanup_first_batch_expression_review.py` | 规范女/男各 Happy/Angry/Sad 共 6/6 案例、180 张图、6 个 MP4；`day2_final_gate.json` 为 `automatic_success=true`，用户决定 `day2_dynamic_visual_review_20260822_v1.json` 接受轻微但可见的差异用于第一批 |

包级分类与静态文件名提示都不能替代逐条动作的 CC 播放、时长、循环、Root Motion、面部通道、隐藏依赖和动态质量门禁。剩余扩展见 [`ROADMAP.md`](../planning/ROADMAP.md) 的 `RM-09R`，运行时组合规则见 [`WF-07`](../workflow/WF-07-ANIMATION-AND-PROPS.md)。

## WF-04 CC 导出 Bundle

| 类型 | 当前对象 | 作用 |
| --- | --- | --- |
| CC 源 | accepted `.ccProject` + character Manifest | 导出身份与来源 |
| Pilot Bundle | `D:\UE\exports\character_creator\pilot_m02_ue58_v001` | 当前已验证 M02 导出 |
| 必需文件 | 同基名 FBX/JSON 与 `.fbm\`；`textures\` 按 JSON 的布料权重与动态皱纹引用决定 | Auto Setup 输入；使用面部表情时 `Wrinkle.Textures` 不得为空 |
| 追溯 | 导出 manifest/哈希记录 | 源项目到 Bundle 映射 |

当前已有首批 FullReference 的受控自动装配/导出路径；通用 Motion/任意角色导出仍依赖 CC UI 与资产状态。阶段所有者：[`WF-04`](../workflow/WF-04-CC-EXPORT-BUNDLE.md)。

## WF-05 UE 完整参考导入

| 类型 | 当前对象 | 作用 |
| --- | --- | --- |
| UE 项目 | `D:\UE\projects\datatry_02` | UE 5.8 主项目 |
| 插件 | `Plugins\RLPlugin` / Auto Setup 2.03 | Reallusion 材质与 Rig Logic 支持 |
| Shader | `/Game/CC_Shaders` | Auto Setup 内容依赖 |
| FullReference | `/Game/Vendor/Reallusion/CC5/Characters/M02_Average/FullReference` | 完整角色基准 |
| Skeleton | `.../CC_M02_Average_Pilot_UE58_Skeleton` | 后续模块和动画统一 Skeleton |
| 首批 Look 根 | `/Game/Vendor/Reallusion/CC5/FirstDataBatch/Looks` | 32 个首批烘焙 FullReference Look，女性 16、男性 16，机器门禁 32/32 通过 |
| 首批规范 Skeleton | `.../F_ID01_O01/CC_FB_F_ID01_O01_Skeleton`、`.../M_ID01_O01/CC_FB_M_ID01_O01_Skeleton` | 女性/男性首批 Look 与后续同性 Motion 的统一 Skeleton |

既有 M02 Pilot 首次导入由 UE UI 完成；P0 F02/M02 参考角色由 `ue_import_p0_runtime_pilot.py` 执行原始导入，并由用户在 Content Browser 运行 Reallusion Auto Setup 后进行严格后验收。首批 32 Look 使用 `run_first_batch_full_reference_import.py --expanded-matrix` 外层编排、精确窗口守卫和 `ue_import_first_batch_full_reference_looks.py` 后验收。长批次会累积 UE/FBX 内存，新增导入必须按最多 3 个 Look 分批并重启 UE。阶段所有者：[`WF-05`](../workflow/WF-05-UE-IMPORT-REFERENCE.md)。

## WF-06 UE 模块运行时

| 顺序 | 文件/资产 | 作用 |
| ---: | --- | --- |
| 1 | `ue_interchange_split_pilot.py` | M02 FBX 拆分导入到 `_SplitPilot` |
| 2 | `ue_validate_split_pilot.py` | 检查拆分网格、Skeleton 和预期清单 |
| 3 | `ue_apply_split_pilot_materials.py` | 从 FullReference 恢复模块材质 |
| 4 | `ue_build_m02_modular_pilot_blueprint.py` | 创建 20 组件 v001 Blueprint |
| 5 | `ue_build_m02_face_morph_broadcaster.py` | 派生 v002 并创建 Morph 广播 |
| 验证 | `ue_validate_m02_face_morph_broadcaster.py` | `VAL-UE-01` |
| 当前入口 | `/Game/DataMake/Characters/M02_Average/BP_DM_M02_ModularPilot_v002` | M02 模块角色 |
| 证据 | `OUTPUT_ROOT\unreal_character_import\m02_face_morph_broadcaster_validation.json` | v002 验证报告 |

上述构建脚本硬编码 M02；其他体型不可复用。阶段所有者：[`WF-06`](../workflow/WF-06-UE-CHARACTER-RUNTIME.md)。

## WF-07 动画、年龄和道具

| 环节 | 文件/资产 | 作用 |
| --- | --- | --- |
| 原动作导入 | `ue_import_cc5_rlmotion_pilot.py` | 导入 CC 导出的动画 FBX |
| Body-only | `ue_build_m02_body_motion_library_v001.py` | 构建两条身体动作 |
| Face curves | `ue_build_m02_face_clip_library_v001.py` | 构建面部曲线片段 |
| 支撑骨骼审计 | `ue_audit_m02_face_support_bones_v001.py` | 判断混合面部骨骼集合 |
| Hybrid face | `ue_build_m02_face_hybrid_clip_v001.py` | 曲线 + 口腔支撑骨骼 |
| AnimBP | `ue_build_m02_layered_anim_blueprint_v003.py` | 身体/面部分层控制 |
| 首批三表情配置 | `00_engine\scripts\unreal\first_batch_expression_profile_20260820_v1.json` | 冻结 Happy、Angry、Sad 的 3 秒、60 fps 曲线、自然眨眼与禁用 head/neck/eye-gaze 的边界 |
| 首批三表情构建 | `ue_build_first_batch_expression_library.py`、`ue_build_first_batch_expression_composition.py` | 为 F02/M02 各生成三条曲线资产、两级选择 AnimBP 和 FullReference 审查 Wrapper；Body 动作与 Face additive 解耦 |
| 首批三表情运行时门禁 | `run_first_batch_expression_review.py` 及 `ue_stage/ue_run/ue_cleanup_first_batch_expression_review.py` | 6/6 组合、18/18 图、自动错误 0；报告位于 `OUTPUT_ROOT\unreal_character_import\first_batch_expressions_20260820_v1\runtime_review` |
| 首批三表情审查门户 | `VISUAL_PORTAL\runs\2026-08-20-ue-first-batch-expressions-v1\run.json` | F02/M02 × Happy/Angry/Sad；状态 `pending_review`，机器通过不代替用户对辨识度和自然度的接受 |
| 动画注册表 | `cc_unreal_animation_channel_registry_v1.json` | 通道、复用政策和资产路径 |
| 组合验证 | `run_m02_face_hybrid_pie_review_v003.py` | `VAL-UE-02` 外层入口 |
| Elder 构建 | `ue_import_m02_elder_morph_snapshots.py`、`ue_build_m02_elder_body_morph.py`、`ue_build_m02_elder_component_morphs.py` | 同身份快照 Morph |
| Elder 验证 | `run_m02_elder_morph_pie_review.py` | `VAL-UE-03` 外层入口 |
| 当前 AnimBP | `/Game/DataMake/Animations/CC5/Pilot/ABP_DM_M02_BodyFaceLayer_v003` | 生产 Pilot |

生产动画源包已完成 P0-P3 包级整理，但逐条生产动画注册表、服装正式动态、三发型和道具仍没有完整实现文件。阶段所有者：[`WF-07`](../workflow/WF-07-ANIMATION-AND-PROPS.md)；资产池开发状态见本页“动画源发现与生产池开发”。

## WF-08 场景与相机

状态 `in_progress`。

| 环节 | 文件/资产 | 当前结果 |
| --- | --- | --- |
| 人工布局源 | `/Game/DataMake/Sequences/firstweek` | 30 fps、0–600；`near/far/high/side` 四段顺序 Camera Cut，源序列由用户维护 |
| 原生 Section 模板 | `/Game/DataMake/Sequences/FirstBatch/Templates/LS_DM_NativeSkeletalAnimationSectionTemplate_v001` | 由编辑器原生创建的可求值 Skeletal Animation Section；构建器通过 `copy_sections/paste_sections` 复用，避免 Python 空建 Section 只显示静态姿态 |
| 动作/表情组合构建器 | `ue_build_first_batch_action_expression_composites.py`、`run_first_batch_action_expression_composites.py` | 按 `action_id` 读取冻结动作和三表情配置；保留身体骨骼轨道并以稀疏循环关键帧嵌入 Happy/Angry/Sad Morph 曲线；既有资产默认只审计，`--replace` 才覆盖 |
| 四短动作补齐 | `ue_build_first_batch_idle_padding.py`、`run_first_batch_idle_padding.py` | F03/F04/M02/M03 使用精确端点保持补齐到 150 帧；聚合报告 `first_batch_day3_20260823_v1\idle_padding_build.json` 为 4/4 |
| 生产组合聚合入口 | `run_first_batch_all_action_expression_composites.py` | 当前 10 动作 × Happy/Angry/Sad 为 30 条；历史 12×3 的 36 条报告保留作验证证据 |
| 20 秒/单节点构建器 | `00_engine\scripts\unreal\ue_build_first_batch_20s_sequence.py` | 读取冻结动作窗口和 UE Motion Gate，复制人工布局源，绑定角色主 SkeletalMeshComponent，并用原生模板生成四个 150 帧 Section；F02 使用嵌入 Morph 曲线的组合 AnimSequence。男女路径均强制 `force_custom_mode=true`，报告 `all_cc5_looks_force_custom_mode` |
| 外层入口 | `00_engine\scripts\unreal\run_first_batch_20s_sequence.py` | 通过 UE Remote Execution 参数化 action、源/目标 Sequence 和目标 Actor；不会原地改写 `firstweek` |
| F02 组合资产 | `/Game/DataMake/Animations/CC5/FirstDataBatch/Female/Composites/F02` | Happy/Angry/Sad 三条资产均保留 108 条身体骨骼轨道、30 fps、391 帧和规范女性 Skeleton，并分别嵌入 8/12/10 条 Morph 曲线 |
| F02 试点 | `/Game/DataMake/Sequences/FirstBatch/LS_DM_FirstBatch_F02_20s_Pilot_v001` | 只对 F02 使用已批准 InPlace；四段镜头及 `Happy/Angry/Sad/Happy` 身体/表情组合通过自动审计；一帧源保护 + 一帧 pre-roll 消除 MRQ 首帧 T Pose |
| 结构/几何审计 | `ue_audit_first_batch_day3_layout_motion.py`、`OUTPUT_ROOT\unreal_character_import\first_batch_day3_20260822_v2\layout_motion_audit.json` | `sequence_contract_passed=true`、`layout_geometry_passed=true`、`production_ready=true` |
| F02 组合证据 | `OUTPUT_ROOT\unreal_character_import\first_batch_day3_20260823_v1\f02_body_expression_composite_build.json`、`f02_body_expression_sequence_build.json`、`f02_20s_body_expression_visual_review_20260823_v1.json` | 三条组合资产与正式四段序列结构通过；用户接受表情偏轻但可用于第一批 |
| 32-Look 本地矩阵配置 | `00_engine\scripts\unreal\first_batch_local_render_matrix_20260824_v1.json` | 冻结 32 个不同 Look；轮转覆盖 10 个生产动作、`near/far/high/side` 四相机和 Happy/Angry/Sad，全部样例为 150 帧 |
| Look staging | `00_engine\scripts\unreal\ue_stage_first_batch_render_look.py` | 在 DataMake staging map 中只保留一个目标角色，按样例替换 FullReference Blueprint，并返回精确 Actor 名供 Sequence 原生绑定 |
| 防 T-pose 契约 | `ue_build_first_batch_20s_sequence.py` 的 Section 报告、`run_first_batch_render_matrix.py::pose_driver_contract` 与 `temporal_motion_contract` | MRQ 前要求四段 Section、全部 `force_custom_mode=true`、原生 Actor binding 和目标 Actor；渲染后比较五个时间采样帧确认可见运动。任一失败即拒绝案例或旧结果复用。它处理热切换 Look 后整段 T-pose，和一帧 pre-roll 处理的首帧 Bind Pose 是两个独立门禁 |

F03、F04、M02、M03 四条短动作和历史 36 条组合资产已经完成；生产池排除 F04/M03 后，有效短动作是 F03/M02，有效组合是 30 条。源身体与表情资产保持分离，组合 AnimSequence 只是 Sequencer 的可重建交付缓存。参数化 5 秒 Sequence 和 32-Look 代表矩阵已通过；真实 scene/camera/Blueprint 稳定引用现已写入正式源清单。后续继续记录服装兼容性警告。阶段所有者：[`WF-08`](../workflow/WF-08-SCENE-CAMERA-SEQUENCE.md)。

## WF-09 渲染与数据集

渲染和数据集封装为 `in_progress`。本地单节点和可续跑 32 例矩阵已有验证实现；配置图与编辑链机器门禁已迁移通过，正式媒体执行器仍待完成：

| 环节 | 文件 | 当前结果 |
| --- | --- | --- |
| 当前规范 | `20_planning\data_design\schema\CONFIG_GRAPH_SCHEMA_V1.md`、`20_planning\data_design\sampling\MULTI_ROUND_CHAIN_SAMPLING_V1.md`、`20_planning\data_design\schema\MULTI_ROUND_VIDEO_EDIT_TEXT_SCHEMA_V1.md` | 已接受：四相机、Happy-only、两个 320 节点连通域、640 节点、双策略精确 4,000 链，以及 15,000 回合双语文本层 |
| 配置图源清单生成器 | `00_engine\scripts\dataset\build_first_batch_graph_source_v1.py`、`first_batch_graph_source_20260824_v1.json` | 合并 32-Look 导出清单和本地矩阵，冻结真实 scene/camera/Blueprint/Happy composite/MRQ 引用；输出 Happy-only、1440p30、双域源清单 |
| 配置图生成器 | `00_engine\scripts\dataset\build_first_batch_config_graph_v1.py` | 当前合规实现；生成两个 320 节点连通域、640 节点、8,320 条同域原子边、4,000 条双策略链和 640 个 render job，并在写盘前重算五个事实标签 |
| 模型文本词表 | `00_engine\scripts\dataset\prompt_catalog_first_batch_v1.json` | 冻结 8 身份、8 服装、10 动作、4 相机的双语语义标签、模板和 E1 配对目标视频 grounding 策略 |
| 模型文本生成器 | `00_engine\scripts\dataset\build_first_batch_prompt_layer_v1.py` | 从冻结 edges/chains 生成 dialogue/standalone 双语 `video_in + prompt + video_out` 回合；不修改图或媒体 |
| 生成器说明 | `00_engine\scripts\dataset\README.md` | 定义源清单、配置图、模型文本层和代表链审查包的命令、输入边界、输出与硬失败条件 |
| 配置图与文本自动测试 | `00_engine\scripts\dataset\tests\test_build_first_batch_graph_source_v1.py`、`test_build_first_batch_config_graph_v1.py`、`test_build_first_batch_prompt_layer_v1.py` | 图测试覆盖 Happy-only 源压缩、双域、精确配额、原子边、五事实重算、四轴 25%、全节点引用、可重复生成和旧契约拒绝；文本 5/5 覆盖双语配对、历史回退、身份 grounding、字节级确定性和非原子拒绝 |
| 正式配置图证据 | `OUTPUT_ROOT\first_batch_dataset\graph_20260824_v1\build_report.json` | `passed`：37 assets、32 Looks、640 nodes、8,320 edges、4,000 chains、640 render jobs；每域 320 节点且只有一个连通分量 |
| 代表链审查器 | `00_engine\scripts\dataset\build_first_batch_chain_review_v1.py`、`OUTPUT_ROOT\first_batch_dataset\graph_20260824_v1\review_10` | 固定选择男女各 5 条，共 10 条语义代表链；另给出 2 条 UE 视觉渲染候选 |
| 链级本地渲染矩阵 | `00_engine\scripts\unreal\build_first_batch_chain_render_matrix_v1.py`、`first_batch_chain_render_matrix_20260824_v1.json` | 把 2 条候选的 11 次路径引用去重为 9 个唯一节点，解析回正式 Look/Action/Camera Section/Happy composite；实际渲染 9/9 通过 |
| 通用样例计数渲染 | `00_engine\scripts\unreal\run_first_batch_render_matrix.py` | 已从硬编码 32 样例改为读取 `samples` 实际长度；原 32-Look 配置保持兼容，链矩阵可先 `--limit 5` 渲染第一条链，再复用已通过媒体补齐第二条 |
| 正式模型文本证据 | `OUTPUT_ROOT\first_batch_dataset\graph_20260824_v1\text_first_batch_20260824_v1` | `prompt_report.json=passed`：4,000 dialogs、15,000 turns、四轴各 3,750、双语完整、原子性通过、内部 ID 泄漏 0；`PROMPT_REVIEW.md` 为语言抽查入口 |
| 链级媒体验收 | `00_engine\scripts\unreal\validate_first_batch_chain_visual_smoke_v1.py`、`OUTPUT_ROOT\unreal_render\first_batch_chain_visual_smoke_20260824_v1` | 两链 11 次路径引用、9 个唯一视频全部为 150 帧/1440p30/Happy；视频哈希、pose-driver、temporal-motion 为 9/9，最低动态差异 41.177483；机器与 assistant 预检通过，用户决定 `user_visual_review_20260824_v1.json=accepted` |
| MRQ Preset 构建 | `ue_build_first_batch_render_profile.py`、`run_first_batch_render_profile.py` | 默认 `/Game/DataMake/Render/Presets/MRQ_DM_FirstBatch_1440p30_PNG_v001`；2560×1440、30 fps、PNG；720p Preset 只作低显存回退 |
| 本地单节点渲染 | `ue_start_first_batch_local_sample_render.py`、`run_first_batch_local_sample_render.py` | 提交 MRQ PIE 作业、等待终态、检查 150 张 PNG/尺寸并编码 H.264；不会覆盖已有 run |
| 1440p Pilot 证据 | `OUTPUT_ROOT\unreal_render\first_batch_local_sample_20260823_014930_v001\render_report.json`、`visual_review.json` | 150/150、2560×1440、30 fps、5 秒、SHA-256 通过；首帧无 T Pose，末帧夹克穿模，状态 `passed_with_visual_warning` |
| 32 例矩阵执行器 | `00_engine\scripts\unreal\run_first_batch_render_matrix.py`、`run_first_batch_32_video_matrix.ps1` | 逐例 staging Look、构建 Sequence、执行防 T-pose 门禁、提交 MRQ、验证媒体、写状态并支持断点续跑；默认读取 `first_batch_local_render_matrix_20260824_v1.json` |
| 32 例矩阵证据 | `OUTPUT_ROOT\unreal_render\first_batch_32look_matrix_20260824_v002\matrix_report.json`、`matrix_motion_audit.json`、`matrix_state.json`、`matrix_contact_sheet.png`、`index.html` | 32/32、32 个唯一 Look、10 动作全覆盖、四相机各 8 例、三表情全覆盖；4,800 PNG + 32 MP4。每例 2560×1440、30 fps、150 帧、5 秒且 pose-driver/temporal-motion contract 通过；时间变化最小值 `28.148507 > 2.0`，OpenCV 独立媒体检查无失败 |

当前已有 32 Look/10 动作的机器清单、参数化本地矩阵，以及包含真实 scene/camera/Blueprint 引用的正式源。640 节点/8,320 原子边/4,000 链和 4,000 dialogs/15,000 turns 已生成并通过机器门禁。尚无正式 GT/sidecar、640 节点媒体、服务器队列/重试或 dataset acceptance 实现；本地 32 例代表矩阵、文本层和未完整渲染的配置图都不得单独当作正式第一批数据集交付。

## 维护分支

| 领域 | 关键文件 |
| --- | --- |
| BodyFit 库构建 | `cc_build_body_preset_library_v2.py`、BodyFit 候选 JSON |
| Face 配方生成 | `cc_generate_face_recipes_v3.py`、`cc_generate_face_recipes_v3_config.json` |
| Face seed 验证 | `cc_validate_face_seeds.py` |
| 外观目录/兼容 | `cc_build_appearance_asset_catalog.py`、`cc_build_appearance_compatibility_registry.py` |
| 面部 Registry | `cc_build_facial_production_registry.py`、对应 config |

这些文件用于修改生产系统，不是每个角色的 Workflow 步骤。使用前阅读对应 `cc_details/` 技术规范。

## 当前证据与已知不一致

| 能力 | 证据 |
| --- | --- |
| 十体型身高 | `outputs/character_creator_bridge/artifacts/bodyfit_height_matrix_current_20260803_01/bodyfit_height_matrix.json` |
| M02 模块 | `outputs/unreal_character_import/m02_body_face_demo_stage.json` |
| v003 动画矩阵 | `outputs/unreal_character_import/m02_face_hybrid_review_v003/pie_review.json` |
| Elder Morph | `outputs/unreal_character_import/m02_elder_morph_review_v001/pie_review.json` |
| F02/M02 FullReference P0 运行时 | `outputs/unreal_character_import/p0_runtime_pilot_20260819_v1/runtime_review/pie_runtime_review.json`、`visual_review_decision.json`；16/16 组合、24/24 图、错误 0 |
| 材质质量 | `outputs/character_creator_bridge/artifacts/m02_face_material_recommended_20260805_01` |
| Headshot Profile 升级 | 原 4 人位于 `headshot_profile_upgrade/*_20260808_v1/v2`；新增 6 人位于 `female3..5_20260810_v1`、`male3..5_20260810_v1` |
| Headshot 来源映射 | `outputs/character_creator_bridge/artifacts/headshot_rm05c_source_mapping_20260810_v1.json`；新增 6 例复制前后 SHA-256 一致，10 个候选均有 source |
| Headshot 原型包校验 | `outputs/character_creator_bridge/artifacts/headshot_face_prototype_registry_validation_20260810_v4.json`；10 个候选、0 个生产启用、0 错误 |
| Headshot 头型初始范围与网页审查 | `visualization_portal/runs/2026-08-09-headshot-skull-profile-review-v1/run.json`；原图仍在 `outputs/character_creator_bridge/artifacts/headshot_skull_profile_review` |
| Headshot 头型扩大单轴扫描 | `visualization_portal/runs/2026-08-09-headshot-skull-axis-sweep-v2/run.json`；状态 `approved`；批准区间为 `cc_headshot_skull_safe_ranges_v1.json`，30 个案例和 90 张原图位于 `outputs/character_creator_bridge/artifacts/headshot_skull_axis_sweep_v2` |
| Headshot project-seed + BodyFit Pilot | `visualization_portal/runs/2026-08-10-headshot-project-seed-bodyfit-pilot-v1/run.json`；完整机器结果位于 `outputs/character_creator_bridge/artifacts/headshot_project_seed_bodyfit_pilot/run_20260810_v4`；当前 `approved` |
| Headshot 10 人身份池 | `visualization_portal/runs/2026-08-10-headshot-identity-pool-10-v2/run.json`；当前 `pending_review`，10 人 source 全部映射，6 个新增候选等待用户验收；验收后冻结暂存，不立即迁移生产 |
| 服装源发现与日期重组 | 原始索引为 `outputs/character_creator_bridge/artifacts/clothing_source_inventory/inventory_20260811_v1/inventory.json`；当前 v2 清单与全量校验位于 `outputs/character_creator_bridge/artifacts/clothing_date_reorganization/reorg_20260811_v2_newest50`，56 主队列、53 较旧半区、22 日期不明、0 校验错误；v1 固定 2022 结果保留 |

`dm_asset_index.json` 已在线核对并升级为 version 4，登记模块化 v002/v003 相关入口与 F02/M02 FullReference P0 v001。仍存在的债务是旧模块验证器硬编码 v001、两个旧 UE wrapper 使用固定输出目录，以及哈希锁定候选注册表尚未通过新版本迁移吸收本次 P0 结果。完整债务见 [`CURRENT_STATUS.md`](../CURRENT_STATUS.md)。
