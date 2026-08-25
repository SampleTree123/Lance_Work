# WF-07 动画、表演与道具

> 文档角色：`workflow_runbook`
> 状态：`validated_pilot`
> 适用阶段：`WF-07`
> 权威范围：身体动作、面部片段、年龄 Morph 与道具契约的生产组合顺序
> 上级入口：[`README.md`](./README.md)
> 上游：[`WF-06-UE-CHARACTER-RUNTIME.md`](./WF-06-UE-CHARACTER-RUNTIME.md)
> 下游：[`WF-08-SCENE-CAMERA-SEQUENCE.md`](./WF-08-SCENE-CAMERA-SEQUENCE.md)
> 最近核验：2026-08-18

## 1. 目的与使用时机

给已经通过模块运行时验收的角色分配身体动作、面部表现和可选年龄 Morph，并保留动画通道与道具依赖。该阶段结束后角色才具备可放入场景的完整表演。

## 2. 当前范围与非目标

M02 模块角色已验证两条 Body-only 动作、五种面部状态、混合曲线/支撑骨骼片段和 Elder Morph。动画源发现工作已将 57 个源包整理为 P0 11、P1 10、P2 6、P3 30，并对 P0 的 667 条动作完成静态 inventory；从 85 条首轮提示中冻结并只提取 16 条动态 Pilot。F02/M02 上的 CC 动态机器 Gate 已完成 16/16、80/80 图，用户已完整检查并接受 16 条的视觉自然度。两个穿衣角色和四条代表动作已完成 CC 导出、UE 导入和时序/Root 验证；FullReference 直接 Morph 组合完成 4 个身体状态 × 4 个面部状态、16/16 组合和 24/24 图的 PIE 门禁。生产批准仍为 0；三发型动态矩阵、其余 P0 决定和动作道具池仍为 `planned/pending`。

## 3. 进入条件

- `GATE-06 RUNTIME_ACCEPTED` 通过。
- 动画已登记 `facial_channels` 与 `reuse_policy`。
- 目标 AnimSequence 使用 M02 Skeleton，角色 Body 传播曲线到 followers。

## 4. 输入与输出

输入为模块角色、动画注册表中的 Body motion、Face clip、可选年龄权重和道具依赖。输出为确定的表演配置、所用资产 ID、组合验证报告和截图。

## 5. 执行环境

现有资产组合使用 `UE_UI`/Blueprint。构建与矩阵验证使用 `SYSTEM_PYTHON → UE_REMOTE`。已验证 M02 通道的机器权威为 `cc_unreal_animation_channel_registry_v1.json`；P0 候选元数据权威为 `animation_p0_candidate_registry\registry_20260818_v1\candidate_registry.json`。动画源包清单不是运行时注册表，也不能向单条动作继承批准状态。

## 6. 执行步骤

1. 选择 Body motion 并读取 `facial_channels`、`reuse_policy`。
2. 只有 `replaceable` 可搭配 approved Face clip；`paired` 必须使用登记组合，`locked` 保留完整表演。
3. 身体分支保留 neck/head；面部层只接管 `cc_base_facialbone` 子树。
4. 先选择运行时契约。模块化 M02 的 Hybrid 路线由 eyeLook 曲线和 Rig Logic 驱动，不能直接叠加左右眼骨轨道；P0 FullReference 直接 Morph 路线必须把组件 `disable_post_process_blueprint=true`，且当前只允许 Neutral、Blink、Asymmetric Blink 和 Subtle Smile，不声明 eye-bone gaze。
5. 年龄只使用同一身份、同一拓扑生成的 `Full_Face_Elder`；当前权重为 0、0.5、1。
6. 当前 M02 组合矩阵的唯一外层入口：

```powershell
python "$ueScriptRoot\run_m02_face_hybrid_pie_review_v003.py"
python "$ueScriptRoot\run_m02_elder_morph_pie_review.py"
```

FullReference P0 组合的唯一外层入口为：

```powershell
python "D:\UE\Lance_Work\00_engine\scripts\unreal\run_p0_runtime_validation.py"
```

该入口会暂存四个 Actor、启动 PIE、检查 16 个组合、生成 24 张图片和联系表，并在 `finally` 中退出 PIE、删除临时 Actor。报告必须同时满足 `automatic_success=true`、`visual_review=passed`，且 Wrapper 的 `disable_post_process_blueprint=true`。

7. 动作若依赖咖啡杯、箱子等道具但登记中没有匹配 prop，则该动作不得进入可渲染池。
8. 验证 wrapper 结束后检查 Main 关卡脏包，不保存临时验证 Actor。

P0 动态 Gate 已完成；只有证据漂移、脚本回归或候选扩展时才复跑。复跑前必须由用户按离线方式启动 CC，并确认 Bridge `health` 为新鲜状态。全量复跑模板为：

```powershell
python "D:\UE\Lance_Work\00_engine\character_creator_bridge\cc_bridge_client.py" validate-bodies `
  --library-file "D:\UE\Lance_Work\00_engine\scripts\character_creator\cc_p0_animation_dynamic_gate_20260818_v3.json" `
  --output-dir "D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts\animation_p0_dynamic_gate\run_<new-id>" `
  --confirm-scene-replace --auto-dismiss-undo-warning --timeout 3600
```

该命令会替换当前 CC 场景；执行前不得存在未保存的用户工作。退出 0 只表示 16 条均生成机器证据，不能把 `visual_decision=pending` 自动改为批准。

当前权威累计证据由以下两个作业按案例去重合并：

- `animation_p0_dynamic_gate\run_20260818_v8_lit_review`：统一采用 Lightroom 当前相机和源项目 yaw，正式重采 16/16 动作、80/80 图；
- `animation_p0_lighting_scout\start_aligned_20260818_v1`：修复 `p0_009_city_walk_normal_m` 的非零首帧 Root 偏移，1/1 动作、5/5 图覆盖正式主批中的同一案例。

旧的 2026-08-17 批次保留为相机、构图与 ACL 修复历史，不参与当前累计证据。需要只重跑指定案例时，用可重复的 `--case-id` 生成新的哈希锁定恢复配置；恢复子集可以只含一个 actor，不手改原 Gate：

```powershell
python "D:\UE\Lance_Work\00_engine\scripts\character_creator\cc_build_p0_animation_dynamic_gate_v1.py" `
  --case-id p0_001_city_walk_normal_f `
  --case-id p0_002_city_walk_hurry_f `
  --library-id cc_p0_animation_dynamic_gate_retry_<new-id> `
  --output "D:\UE\Lance_Work\00_engine\scripts\character_creator\cc_p0_animation_dynamic_gate_retry_<new-id>.json"
```

当前相机规范是：先加载 Lightroom，由 Lightroom 建立可见材质与灯光；不再加载独立 `ccCam` 覆盖其相机，不强制 yaw，也不运行旧自动全身构图。每条动作加载后先把动作首帧 `RL_BoneRoot` 对齐源项目 Root；之后每个采样点先记录原始变换与骨骼样本，再临时跟随 Root 完成截图，随后立即恢复。Root 分类始终由平移前样本重算，因此首帧对齐和截图跟随都不篡改动作位移证据。

累计报告和视觉门户按以下命令重建：

```powershell
python "D:\UE\Lance_Work\00_engine\visualization_portal\tools\build_animation_p0_dynamic_gate_run.py"
python "D:\UE\Lance_Work\00_engine\visualization_portal\tools\register_run.py" `
  "D:\UE\Lance_Work\00_engine\visualization_portal\runs\2026-08-17-cc-animation-p0-dynamic-gate-v1\run.json" `
  --replace
```

权威累计 JSON 为 `OUTPUT_ROOT\character_creator_bridge\artifacts\animation_p0_dynamic_gate\cumulative_review_20260818_v2_lit\consolidated_validation.json`。用户决定由 `cc_p0_animation_visual_review_20260818_v1.json` 哈希绑定 Gate 和来源验证；构建器验证其覆盖全部 16 条后将门户置为 `approved`。该状态只关闭视觉自然度门禁，不能直接产生生产批准。

候选注册表与下一阶段工作单按以下命令重建：

```powershell
python "D:\UE\Lance_Work\00_engine\scripts\character_creator\cc_build_p0_animation_candidate_registry_v1.py"
python "D:\UE\Lance_Work\00_engine\scripts\character_creator\cc_build_p0_animation_ue_pilot_work_order_v1.py"
```

注册表输出为 `OUTPUT_ROOT\character_creator_bridge\artifacts\animation_p0_candidate_registry\registry_20260818_v1\candidate_registry.json`。不可变工作单输出为 `OUTPUT_ROOT\character_creator_bridge\artifacts\animation_p0_ue_runtime_pilot\work_order_20260818_v1\work_order.json`，其历史状态保持 `ready_for_cc_export`。该工作单强制使用 `CCSHOW_F02_AVERAGE_001` 与 `CCSHOW_M02_AVERAGE_001` 两个已经生成并穿衣的角色；不得用 F02/M02 灰色基础项目替代。

本轮 CC 导出使用：

```powershell
python "D:\UE\Lance_Work\00_engine\character_creator_bridge\cc_bridge_client.py" validate-bodies `
  --library-file "D:\UE\Lance_Work\00_engine\scripts\character_creator\cc_p0_animation_ue_export_20260818_v1.json" `
  --output-dir "D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts\p0x1" `
  --confirm-scene-replace --auto-dismiss-undo-warning --timeout 1800
```

执行器是 `cc_validate_body_reconstruction.py` 的 `animation_p0_ue_runtime_export` 模式。它加载两个哈希锁定的穿衣项目，只在当前 CC 场景中清除预览时间线，不覆盖源项目；随后导出两个完整参考 FBX/Auto Setup JSON 和四个 Motion-only ASCII FBX。`cc_patch_unreal_animation_fbx_ascii.py` 只修补 47 个辅助骨骼名 token；`cc_rebase_p0_animation_ue_export_v1.py` 在晋升后重写绝对路径；`cc_finalize_p0_animation_ue_export_v1.py` 复核哈希、文件数和工作单并生成最终 Manifest。

最终导入入口是 `D:\UE\exports\character_creator\p0_ue_runtime_pilot_20260818_v1\export_bundle_manifest.json`。参考角色必须连同同名 JSON、`.fbm` 和 `textures` 导入。2026-08-19 诊断确认四个哈希锁定的 `_UE5_ASCII.fbx` 才是本轮动作导入权威输入；`_UE5_Patched.fbx` 不再用于该 Pilot。目标根为 `/Game/Vendor/Reallusion/CC5/P0RuntimePilot`，DataMake 运行时资产根为 `/Game/DataMake/Animations/CC5/P0RuntimePilot`。构建器为 `ue_build_p0_runtime_composition.py`，运行时验收入口为 `run_p0_runtime_validation.py`；准确资产路径登记在 `D:\UE\projects\datatry_02\DataMake\dm_asset_index.json` version 4。

## 7. 退出门禁

执行 [`GATE-07 PERFORMANCE_ACCEPTED`](../validation/README.md)。当前 M02 要求适用的 `VAL-UE-02`、`VAL-UE-03` 和 `VIS-UE-02` 通过。未使用 Elder 时 `VAL-UE-03=not_required`；服装、毛发或道具只要参与，就必须等待相应计划验证实现后才能声称完整 Gate 通过。

## 8. 失败与恢复

颈头冻结、眼骨竞争、Jaw 支撑不足、曲线不传播、服装/毛发穿模或缺道具时停止组合。按 `REC-UE-01` 恢复；错误分类的动画回到领域维护流程，不在本阶段临时删除轨道。

## 9. 技术依据与下一阶段

通道分类和现有资产见 [`ANIMATION_AND_MORPH_PIPELINE.md`](../ue_details/ANIMATION_AND_MORPH_PIPELINE.md)，包级整理实现与证据见 [`IMPLEMENTATION_INDEX.md`](../reference/IMPLEMENTATION_INDEX.md) 的“动画源发现与生产池开发”，Sprint 之后的动画池扩展见 [`ROADMAP.md`](../planning/ROADMAP.md) 的 `RM-09R`。服装和变体边界见 [`MODULAR_CHARACTER_RUNTIME.md`](../ue_details/MODULAR_CHARACTER_RUNTIME.md)。当前主线在此达到已验证 Pilot 边界；第一批数据继续进入 [`WF-08`](./WF-08-SCENE-CAMERA-SEQUENCE.md)，但其 Gate 通过前仍为 `planned`。
