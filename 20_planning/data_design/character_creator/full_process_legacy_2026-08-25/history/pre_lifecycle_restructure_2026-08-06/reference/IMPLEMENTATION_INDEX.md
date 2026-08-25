# 当前实现文件索引

> 文档角色：`implementation_reference`
> 上级入口：[`README.md`](./README.md)
> 最近核验：2026-08-06

本文件回答“第几步使用哪个文件”。执行细节以对应 Runbook 为准，精确参数以 JSON 为准。

```text
SCRIPT_ROOT = D:\UE\Lance_Work\00_engine\scripts\character_creator
BRIDGE_ROOT = D:\UE\Lance_Work\00_engine\character_creator_bridge
UE_SCRIPT_ROOT = D:\UE\Lance_Work\00_engine\scripts\unreal
```

## 1. CC 数据源与生成

| 步骤 | 当前文件 | 运行环境 | 作用 |
| --- | --- | --- | --- |
| BodyFit 权威 | `cc_body_preset_library_v2.json` | 数据 | 10 个源项目、哈希和 Body/Junction 指纹 |
| 比例权威 | `cc_head_bodyfit_scale_decisions_v1.json` | 数据 | Head Scale 与 Neck Height |
| 重建身体库 | `cc_build_body_preset_library_v2.py` | 系统 Python | 从配置重建/校验 BodyFit library；非日常步骤 |
| 身高矩阵请求 | `cc_bodyfit_height_matrix_v2_20260803.json` | CC/RLPy | 当前 10 体型高度验证请求 |
| Face seed 权威 | `cc_face_seed_library_v1.json` | 数据 | 20 个完整身份 seed |
| Face 政策 | `cc_face_identity_policy_v1.json` | 数据 | 审计 51 个控制（41 local、10 macro）与冻结规则 |
| Face recipe 生成 | `cc_generate_face_recipes_v3.py` + `cc_generate_face_recipes_v3_config.json` | 系统 Python | 确定性生成 V3 配方 |
| Face recipe 权威 | `cc_face_recipes_v3_200.json` | 数据 | 当前 200 条配方，实际使用筛选后的 28 个局部 Morph；文件状态仍为 quality-review-only |
| Seed 检查 | `cc_validate_face_seeds.py` | CC/RLPy | 加载 seed、Facial Profile 和动态验证 |

## 2. 外观 Registry

| 步骤 | 当前文件 | 作用 |
| --- | --- | --- |
| 资产路径目录 | `cc_appearance_asset_catalog_v1.json` | 稳定 asset ID 到本地路径 |
| 组合兼容性 | `cc_appearance_compatibility_v1.json` | 通过、拒绝和证据状态 |
| 材质质量档案 | `cc_face_material_quality_profile_v1.json` | 生产批准的皮肤/眼部参数 |
| 生产 Registry 配置 | `cc_facial_production_registry_config.json` | 构建时输入 |
| Registry 构建 | `cc_build_facial_production_registry.py` | 系统 Python 校验并汇总配置 |
| Registry 权威 | `cc_facial_production_registry_v1.json` | 当前池、顺序、年龄、色素和 QA |
| 头发目录 | `cc_scalp_hair_asset_catalog_v1.json` | 58 套发型、呈现偏好和风险 |
| 头发决定 | `cc_scalp_hair_visual_decisions_v1.json`、`cc_scalp_hair_dynamic_review_decisions_v1.json` | 静态/动态接受与拒绝 |
| 胡须目录 | `cc_facial_hair_asset_catalog_v1.json` | 5 套男性胡须 |

新增资产的生成器保留在同目录，命名为 `cc_build_*_compatibility_*`；它们用于扩池，不属于每次角色装配步骤。

## 3. 单个完整角色装配

| 顺序 | 文件/命令 | 输入 | 输出 |
| ---: | --- | --- | --- |
| 1 | 人工或结构化编辑创建 `request.json` | `character_id`、BodyFit ID、Face recipe ID、可选外观 ID | 请求文件 |
| 2 | `cc_compile_character_manifest.py` | 请求 + Body/Face/Appearance/Registry JSON | 确定性 `manifest.json` |
| 3 | `cc_bridge_client.py health` | Bridge heartbeat | 健康状态 |
| 4 | `cc_bridge_client.py validate-bodies` | manifest、输出目录、场景替换确认 | Bridge job |
| 5 | `cc_validate_body_reconstruction.py` | manifest preset | CC 内装配、QA、截图和结果；只由 RLPy 加载 |
| 6 | `cc_summarize_character_integration_v1.py` | artifact root + manifest | `summary.json` |
| 7 | `cc_make_character_integration_contact_sheets_v1.py` | summary | 人工联系表 |

准确命令见 [`../cc_details/CHARACTER_ASSEMBLY_RUNBOOK.md`](../cc_details/CHARACTER_ASSEMBLY_RUNBOOK.md)。

当前保存入口：`cc_character_showcase_10_20260803_v1.json` 已含 `save_character_projects=true`，可逐个运行 `CCSHOW_*` preset。普通 compiler 还没有通用保存开关。

## 4. Bridge

| 文件 | 作用 |
| --- | --- |
| `bridge_config.json` | 路径 allowlist、版本、轮询、heartbeat、lease 和大小上限 |
| `protocol_v1.md` | 请求/结果/heartbeat 线协议 |
| `cc_bridge_client.py` | 系统 Python CLI |
| `plugin/main.py` | CC OpenPlugin worker |
| `cc_undo_dialog_guard.ps1` | 只处理精确匹配的 Undo 警告 |

客户端命令为 `health`、`ping`、`scene-summary`、`apply-face`、`validate-bodies`、`wait`、`result`。`apply-face` 仍是旧 schema，不用于 Face V3。

## 5. CC→UE

| 步骤 | 文件或资产 | 作用 |
| --- | --- | --- |
| CC 导出 | M02 `.ccProject` + Unreal FBX preset | 生成 FBX、JSON、`.fbm` 与 textures |
| 导出基准 | `D:\UE\exports\character_creator\pilot_m02_ue58_v001` | 当前已验证 bundle |
| UE 插件 | Reallusion Auto Setup 2.03 | 创建材质、Rig Logic 和导入支持 |
| 完整参考 | `/Game/Vendor/Reallusion/CC5/Characters/M02_Average/FullReference` | 导入完整角色 |
| 拆分验证 | `ue_interchange_split_pilot.py`、`ue_validate_split_pilot.py` | 生成并验证独立网格 |
| 材质恢复 | `ue_apply_split_pilot_materials.py` | 给拆分网格分配材质 |
| v001 模块 Blueprint 基础 | `ue_build_m02_modular_pilot_blueprint.py`、`ue_validate_m02_modular_blueprint.py` | 构建和验证旧 v001；验证器仍硬编码 v001，不能充当当前 v002 直接证据 |
| v002 面部 Morph 广播 | `ue_build_m02_face_morph_broadcaster.py`、`ue_validate_m02_face_morph_broadcaster.py` | 从 v001 派生当前 v002，并验证 20 组件中的 13 个面部广播组件及非面部隔离 |

详细导出和导入选项见 [`../cc_ue_transfer/EXPORT_IMPORT_RUNBOOK.md`](../cc_ue_transfer/EXPORT_IMPORT_RUNBOOK.md)。

## 6. UE 动画

| 类型 | 当前文件 | 运行位置 | 作用 |
| --- | --- | --- | --- |
| 导入 | `ue_import_cc5_rlmotion_pilot.py` | UE 内 | 导入 CC 动画 Pilot |
| 构建 | `ue_build_m02_body_motion_library_v001.py` | UE 内 | 生成 Body-only 动作库 |
| 构建 | `ue_build_m02_face_clip_library_v001.py` | UE 内 | 生成曲线面部片段 |
| 审计 | `ue_audit_m02_face_support_bones_v001.py` | UE 内 | 审计面部支撑骨骼 |
| 构建 | `ue_build_m02_face_hybrid_clip_v001.py` | UE 内 | 构建曲线+骨骼混合片段 |
| 构建 | `ue_build_m02_layered_anim_blueprint_v003.py` | UE 内 | 构建生产 AnimBP |
| 构建 | `ue_build_m02_hybrid_neutral_control_v001.py` | UE 内 | 构建中性对照 AnimBP |
| 验证外层入口 | `run_m02_face_hybrid_pie_review_v003.py` | 系统 Python | 自动执行 stage → Simulate → PIE review → cleanup；这是复跑矩阵的入口 |
| 验证内部 | `ue_stage_m02_face_hybrid_validation_v003.py`、`ue_run_m02_face_hybrid_pie_review_v003.py`、`ue_cleanup_m02_face_hybrid_validation_v003.py` | UE 内 | 由外层 wrapper 调用，不建议分别手动执行 |
| 人工审核材料 | `ue_make_m02_face_hybrid_review_sheet_v003.py` | 系统 Python | 从 `pie_review.json` 和截图生成联系表 |

机器登记：`cc_unreal_animation_channel_registry_v1.json`。生产 AnimBP 为 v003；v002 脚本和资产只保留历史回归用途。

## 7. UE Elder Morph

| 类型 | 当前文件 | 运行位置 | 作用 |
| --- | --- | --- | --- |
| CC 输入 | `cc_elder_morph_export_pilot_m02_v1.json` | CC/RLPy | CC 青年/老年快照请求 |
| 导入 | `ue_import_m02_elder_morph_snapshots.py` | UE 内 | 导入配对快照 |
| 构建 | `ue_build_m02_elder_body_morph.py` | UE 内 | 构建 Body Morph |
| 构建 | `ue_build_m02_elder_component_morphs.py` | UE 内 | 构建支持组件 Morph |
| 构建 | `ue_build_m02_elder_morph_pilot_blueprint.py` | UE 内 | 构建 Pilot Blueprint |
| 验证外层入口 | `run_m02_elder_morph_pie_review.py` | 系统 Python | 自动布置、运行 6 案例 PIE、结束并清理 |
| 验证内部 | `ue_capture_m02_elder_morph_review.py`、`ue_run_m02_elder_morph_pie_review.py` | UE 内 | 由外层 wrapper 调用，不建议分别手动执行 |
| 人工审核材料 | `ue_make_m02_elder_morph_review_sheet.py` | 系统 Python | 从 6 张截图生成联系表 |

这条链只适用于 M02 同身份、同拓扑快照，不是任意角色通用 Morph 生成器。

## 8. 当前证据入口

| 能力 | 证据 |
| --- | --- |
| 十体型高度 | `00_engine/outputs/character_creator_bridge/artifacts/bodyfit_height_matrix_current_20260803_01/bodyfit_height_matrix.json` |
| UE 模块化角色 | `00_engine/outputs/unreal_character_import/m02_body_face_demo_stage.json` |
| v003 动画矩阵 | `00_engine/outputs/unreal_character_import/m02_face_hybrid_review_v003/pie_review.json` |
| Elder Morph | `00_engine/outputs/unreal_character_import/m02_elder_morph_review_v001/pie_review.json` |
| 材质质量 Pilot | `00_engine/outputs/character_creator_bridge/artifacts/m02_face_material_recommended_20260805_01` |

输出目录是证据，不是配置权威。需要复跑时从代码、JSON 和 Runbook 建立新 run ID。

## 9. 运行环境速查

- 可在系统 Python 运行：生成器、编译器、汇总器、联系表和 Bridge CLI。
- 只能在 CC 内运行：导入 `RLPy` 的 seed/角色/资产执行器。
- 只能在 UE 内运行：导入 `unreal` 的构建、PIE 和资产脚本。
- UE 验证 wrapper：系统 Python 运行，但通过 `ue_remote_exec.py` 把内部脚本送入已打开的 UE；这与 Unreal MCP 无关。
- PowerShell 守卫：只处理精确已知弹窗；不作为通用 GUI 自动化。

准确复跑命令、报告字段和通过条件见 [`../validation/VALIDATION_AND_RECOVERY.md`](../validation/VALIDATION_AND_RECOVERY.md)。
