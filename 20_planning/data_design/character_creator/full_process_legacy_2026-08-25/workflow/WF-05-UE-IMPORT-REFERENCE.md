# WF-05 UE 完整参考导入

> 文档角色：`workflow_runbook`
> 状态：`first_batch_validated`
> 适用阶段：`WF-05`
> 权威范围：在 UE 5.8 中导入并验收未经拆分的完整参考角色
> 上级入口：[`README.md`](./README.md)
> 上游：[`WF-04-CC-EXPORT-BUNDLE.md`](./WF-04-CC-EXPORT-BUNDLE.md)
> 下游：当前 Sprint 进入 [`WF-08`](./WF-08-SCENE-CAMERA-SEQUENCE.md)；模块化研究进入 [`WF-06`](./WF-06-UE-CHARACTER-RUNTIME.md)
> 最近核验：2026-08-22

## 1. 目的与使用时机

先证明 Bundle、Skeleton、Morph、材质和 Reallusion Auto Setup 产物在 UE 中完整正确，再把角色交给动画、场景或模块化流程。完整参考角色是后续排错基准，不可跳过。

首次导入新 Bundle、补充首批 Look、迁移项目或怀疑 UE 资产漂移时使用本流程。只需要重验既有资产时，运行无弹窗的 32-Look 聚合验证，不重复导入。

## 2. 当前范围与非目标

- 历史基准：`M02_Average` 与 P0 F02/M02 FullReference Pilot。
- 第一批正式范围：`F_ID01..04`、`M_ID01..04`，每个身份 4 套同性服装，共 32 个烘焙 FullReference Look。
- UE 目标根：`/Game/Vendor/Reallusion/CC5/FirstDataBatch/Looks/<LOOK_ID>`。
- 当前结果：CC 合并审计 32/32；UE 源预检 32/32、目标目录 32、导入后验收 32/32。

该门禁证明资产结构、材质、Morph、Rig 和 Skeleton 契约，不代替动作穿模、头发/头部服装冲突或最终镜头视觉验收。

## 3. 进入条件

- `GATE-04 BUNDLE_READY` 通过。
- UE 打开 `D:\UE\projects\datatry_02`，不在 PIE/Simulate，且 CC 已关闭以释放内存。
- Reallusion Auto Setup 2.03 项目插件已启用，`/Game/CC_Shaders` 存在。
- 当前 32-Look 机器清单为 `00_engine\scripts\dataset\first_batch_required_exports_20260822_v2.json`。
- CC 合并审计为 `OUTPUT_ROOT\character_creator_bridge\artifacts\first_batch_full_reference_expansion\final_audit_20260822_v1.json`，且结果为 32/32。
- 新导入目标为空；重验既有目标时不得重新触发 Auto Setup。

## 4. 输入与输出

输入是哈希锁定的 CC Project、同基名 FBX/JSON、非空 `.fbm\`，以及 JSON 实际引用时才必需的额外 `textures\`。当前生产根为：

```text
D:\UE\exports\character_creator\first_data_batch_20260820_v1
```

输出包括：

```text
/Game/Vendor/Reallusion/CC5/FirstDataBatch/Looks/<LOOK_ID>
OUTPUT_ROOT\unreal_character_import\first_batch_full_reference_expansion_20260822_v2\<LOOK_ID>_import_validation.json
OUTPUT_ROOT\unreal_character_import\first_batch_full_reference_expansion_20260822_v2\aggregate_import_gate.json
```

## 5. 执行环境

首次 Auto Setup 导入属于 `UE_UI` 流程。外部 FBX 被复制并转换为 `.uasset`，不会从导出目录移走。

`ue_reallusion_dialog_watcher.py` 只匹配已知 FBX 与 Auto Setup 窗口。窗口守卫必须与 Unreal Editor 使用相同的 Windows 权限级别；若 UE 以管理员权限启动，编排命令也必须以管理员权限运行，否则守卫能发现窗口但不能聚焦或确认。

未知窗口、恢复包、崩溃报告或选项变化必须停止并交由用户判断，不允许按坐标盲点。

## 6. 执行步骤

### 6.1 预检或重验既有 32 Look

先确认 UE 已正常进入编辑器，然后运行：

```powershell
python D:\UE\Lance_Work\00_engine\scripts\unreal\run_first_batch_full_reference_import.py --expanded-matrix --continue-on-error --delay-seconds 0
```

只有预检明确报告 `existing_destination_count=32` 时，才允许在这条无弹窗重验命令中使用 `--continue-on-error`。最终必须得到 `passed_count=32`、`failed_count=0`。

### 6.2 导入新的 Look

1. 每次只选择 1–3 个尚未存在的 `LOOK_ID`。
2. 从与 UE 相同权限级别的终端运行，例如：

```powershell
python D:\UE\Lance_Work\00_engine\scripts\unreal\run_first_batch_full_reference_import.py --expanded-matrix --look-id F_ID01_O03 --look-id F_ID01_O04 --look-id F_ID02_O01 --auto-dialogs
```

3. 新导入批次禁止使用 `--continue-on-error`。任何一项失败都必须立即停止，先判断 UE 是否仍在运行。
4. 每批最多 3 个新 Look。批次完成后正常关闭 UE，确认进程退出，再重新启动下一批。
5. 全部新增项完成后执行 6.1 的 32-Look 无弹窗聚合重验。

### 6.3 手工导入回退

自动窗口守卫不可用时，导入到对应 Vendor 目录并使用以下 FBX 选项：

| 中文 UI | 值 |
| --- | --- |
| 骨骼网格体 | 开 |
| 导入网格体 | 开 |
| 导入内容类型 | `Geometry and Skinning Weights` |
| 骨骼 | 首个同性 Look 选 `None`；后续由验收器归一化到该性别规范 Skeleton |
| 保留平滑分组 | 开 |
| 导入骨骼层级中的网格体 | 开 |
| 导入变形目标 | 开 |
| 导入动画 | 关 |

确认 Auto Setup 读取同名 JSON 和纹理。打开 Skeletal Mesh，检查比例、皮肤、眼睛、牙齿、毛发、接缝、Skeleton、Root、IK、Facial Bone，并用 Morph Target 验证左右眨眼及代表性 Smile/Jaw Open。

### 6.4 动态皱纹材质门禁

Auto Setup 的“材质存在”不等于动态皱纹正确。若 CC 导出 JSON 的 `Wrinkle.Textures` 路径为空，Auto Setup 会把 `CM1..3`、`WM1..3`、`RM1..3`、`HM1_Flow..HM3_Flow` 和 `NormalMap_Blend` 绑定到白色、灰色或默认法线占位图。此时中性脸可能正常，但 Smile、Angry 或 Sad 增强时会在额头和面颊逐渐出现白块。

首批 32 Look 使用以下可恢复修复：

```powershell
python D:\UE\Lance_Work\00_engine\scripts\unreal\ue_remote_exec.py --project datatry_02 --command "DM_MODE='audit'; exec(compile(open(r'D:\UE\Lance_Work\00_engine\scripts\unreal\ue_patch_first_batch_head_wrinkle_textures.py', encoding='utf-8').read(), r'D:\UE\Lance_Work\00_engine\scripts\unreal\ue_patch_first_batch_head_wrinkle_textures.py', 'exec'))"
python D:\UE\Lance_Work\00_engine\scripts\unreal\ue_remote_exec.py --project datatry_02 --command "DM_MODE='apply'; exec(compile(open(r'D:\UE\Lance_Work\00_engine\scripts\unreal\ue_patch_first_batch_head_wrinkle_textures.py', encoding='utf-8').read(), r'D:\UE\Lance_Work\00_engine\scripts\unreal\ue_patch_first_batch_head_wrinkle_textures.py', 'exec'))"
```

修复使用已验证 M02 的标准 CC 头部皱纹贴图，不替换各 Look 的基础肤色、Base Color 或 Normal Map。报告必须为 `look_count=32`、`placeholder_looks=0`、`success=true`。任何重新导入或重新运行 Auto Setup 都必须重跑该门禁；正式解决方案仍是让后续 CC Bundle 自带非空皱纹纹理路径。

## 7. 退出门禁

执行 [`GATE-05 UE_REFERENCE_ACCEPTED`](../validation/README.md)，并要求每个 Look 同时满足：

- 源 Bundle 哈希通过，目标只有一个主 Skeletal Mesh。
- Morph 非空，材质槽全部由 Auto Setup/HQ 材质接管。
- 计划使用面部表情时，头部 13 个动态皱纹纹理参数均非 Share 占位图，并通过至少一个 Happy、Angry、Sad 峰值帧视觉检查。
- PhysicsAsset、Skeleton、角色 Blueprint、AnimBlueprint、IK Rig/Retargeter 等必需资产存在。
- 女性全部复用 `F_ID01_O01` Skeleton，男性全部复用 `M_ID01_O01` Skeleton。
- 单项报告 `success=true`，聚合报告数量与机器清单一致。

当前权威聚合证据：

```text
D:\UE\Lance_Work\00_engine\outputs\unreal_character_import\first_batch_full_reference_expansion_20260822_v2\aggregate_import_gate.json
```

当前结果为 `success=true`、`passed_count=32`、`failed_count=0`。

## 8. 失败与恢复

2026-08-22 的一次长批次在同一 UE 进程内连续完成 9 个新增 Look 后崩溃，崩溃前 UE private commit 约为 84–90 GB。聚合记录中的 `M_ID02_O01` 首次失败是 Remote Execution 连接被重置，后续五项只是 UE 已退出后的连带失败；该 Look 在干净重启后通过，因此不是坏资产。

发生同类故障时：

1. 终止外层编排，不继续写入后续快速失败记录。
2. 检查失败 Look 目标目录是否有 partial 资产；不覆盖已通过目录。
3. 恢复包由用户决定，不自动恢复瞬态导入包。
4. 干净重启 UE，只重跑失败 Look，随后继续最多 3 项的小批次。
5. 完成后执行 32-Look 聚合重验，只有 32/32 才能关闭事件。
6. 若发生重新导入或 Auto Setup 覆盖，执行 6.4 的动态皱纹材质审计与修复，再进入表情或 MRQ 阶段。

Skeleton 误复用、Morph 缺失、灰材质、透明错误、比例异常或未知窗口同样按 `REC-XFER-01` / `REC-UE-01` 停止恢复，不得猜测选项。

## 9. 技术依据与下一阶段

当前 Sprint 的 FullReference 基线已经完成，进入 [`WF-08`](./WF-08-SCENE-CAMERA-SEQUENCE.md) 固定场景、角色锚点、相机和 Sequence。通用模块化角色研究仍由 [`WF-06`](./WF-06-UE-CHARACTER-RUNTIME.md) 管理，不作为本批数据的前置条件。

Vendor/DataMake 与追溯规则见 [`ASSET_TRACEABILITY.md`](../cc_ue_transfer/ASSET_TRACEABILITY.md) 和 [`ADR-0007`](../decisions/ADR-0007-UE-VENDOR-DATAMAKE-MODULARITY.md)。
