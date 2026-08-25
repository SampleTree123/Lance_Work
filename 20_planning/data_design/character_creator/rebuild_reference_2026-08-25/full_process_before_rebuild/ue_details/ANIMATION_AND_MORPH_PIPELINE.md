# UE 身体、面部动画与 Morph 管线

> 文档角色：`technical_specification`
> 状态：`validated_pilot`
> 适用阶段：`WF-07`
> 权威范围：动画通道分类、复用政策、分层和年龄 Morph 技术契约
> 已验证对象：`M02_Average`
> 上级入口：[`README.md`](./README.md)
> 上游：动画注册表、M02 动画/Blueprint 和验证报告
> 下游：动画与道具 Workflow、未来统一角色接口
> 机器权威：`%LANCE_ROOT%\00_engine\scripts\character_creator\cc_unreal_animation_channel_registry_v1.json`
> 最近核验：2026-08-06

## 1. 目标

身体动作与面部表现可以独立选择，但只有通道被明确分类后才能重组。一个 `.rlMotion` 或 UE `AnimSequence` 不能仅凭预览判断为“纯身体”。它可能包含面部骨骼、Rig Logic 曲线或二者。

## 2. 当前运行时

```text
生产 Anim Blueprint：
/Game/DataMake/Animations/CC5/Pilot/ABP_DM_M02_BodyFaceLayer_v003

中性对照 Anim Blueprint：
/Game/DataMake/Animations/CC5/Pilot/ABP_DM_M02_BodyFaceLayer_v003_ControlNeutral

Layered Blend 根骨：cc_base_facialbone
Branch depth：1
明确排除：neck_01、neck_02、head
```

v003 保留身体动画的颈部和头部运动，只让面部层接管 `cc_base_facialbone` 子树。眼球最终姿态由 Rig Logic 曲线驱动，不直接叠加 `cc_base_l_eye` 和 `cc_base_r_eye` 轨道。

### 2.1 当前实现文件

| 环节 | 当前代码 | 运行位置 |
| --- | --- | --- |
| Body-only 动作库 | [`ue_build_m02_body_motion_library_v001.py`](../../../../../00_engine/scripts/unreal/ue_build_m02_body_motion_library_v001.py) | UE 内 |
| Face clip 库 | [`ue_build_m02_face_clip_library_v001.py`](../../../../../00_engine/scripts/unreal/ue_build_m02_face_clip_library_v001.py) | UE 内 |
| 支撑骨骼审计 | [`ue_audit_m02_face_support_bones_v001.py`](../../../../../00_engine/scripts/unreal/ue_audit_m02_face_support_bones_v001.py) | UE 内 |
| Hybrid face clip | [`ue_build_m02_face_hybrid_clip_v001.py`](../../../../../00_engine/scripts/unreal/ue_build_m02_face_hybrid_clip_v001.py) | UE 内 |
| v003 AnimBP | [`ue_build_m02_layered_anim_blueprint_v003.py`](../../../../../00_engine/scripts/unreal/ue_build_m02_layered_anim_blueprint_v003.py) | UE 内 |
| v003 矩阵外层入口 | [`run_m02_face_hybrid_pie_review_v003.py`](../../../../../00_engine/scripts/unreal/run_m02_face_hybrid_pie_review_v003.py) | 系统 Python → UE Remote Execution |
| Elder 矩阵外层入口 | [`run_m02_elder_morph_pie_review.py`](../../../../../00_engine/scripts/unreal/run_m02_elder_morph_pie_review.py) | 系统 Python → UE Remote Execution |

构建脚本用于维护现有 Pilot，不代表已经存在“输入任意动画即可生成生产资产”的通用 API。正常组合顺序见 [`WF-07`](../workflow/WF-07-ANIMATION-AND-PROPS.md)，准确验证命令见 [`VALIDATION_CATALOG.md`](../validation/VALIDATION_CATALOG.md)。

## 3. 动画分类

| 类别 | `facial_channels` | 使用规则 |
| --- | --- | --- |
| 纯身体 | `none` | `replaceable`，可以搭配已批准面部片段 |
| 曲线面部 | `curves` | 保留曲线；由 Rig Logic 驱动相关骨骼和 Morph |
| 骨骼面部 | `bones` | 必须保留需要的口腔/面部骨骼，或先生成已验证的 Body-only 派生动画 |
| 混合面部 | `hybrid` | 曲线与面部支撑骨骼作为一个片段使用 |
| 完整表演 | 视内容而定 | 登记为 `locked`，身体和面部保持配对，不再随机叠加 |

`reuse_policy`：

- `replaceable`：允许从白名单中选择别的面部片段。
- `paired`：身体与面部必须按登记 pair 一起选择。
- `locked`：保留原始完整表演，不得拆分重组。

## 4. 当前动画库

### 4.1 Body-only

| ID | UE 资产 | 状态 |
| --- | --- | --- |
| `audience_body_only_v001` | `/Game/DataMake/Animations/CC5/Pilot/A_CC_Audience_F_01_BodyOnly_v001` | `approved_pilot` |
| `walk_wander_body_only_v001` | `/Game/DataMake/Animations/CC5/Pilot/A_CC_Walk_Wander_M_BodyOnly_v001` | `approved_pilot` |

原始 Walk Wander 含面部骨骼，因此原始资产登记为 `locked/source_only`；可重组时使用 Body-only 派生版本。

### 4.2 Face-only

| ID | 通道 | 用途 |
| --- | --- | --- |
| `face_neutral_v001` | none | 中性对照 |
| `face_natural_blink_v001` | curves | 自然眨眼 |
| `face_blink_gaze_v001` | curves | 眨眼和视线 |
| `face_subtle_smile_v001` | curves | 轻微微笑 |
| `face_hybrid_support_v001` | hybrid | 曲线加颌、上颌、牙齿和舌头支撑骨骼 |

`face_jaw_open_curve_test_v001` 只有 Jaw Open 曲线，缺少完整支撑，不是生产片段。

### 4.3 FullReference P0 直接 Morph 片段

F02/M02 FullReference P0 使用另一份明确隔离的运行时契约：

| 状态 | 曲线 | 说明 |
| --- | --- | --- |
| `neutral` | 无 | 中性控制 |
| `natural_blink` | `eyeBlinkL/R` | 双眼完整闭合 |
| `asymmetric_blink` | `eyeBlinkL` | 单眼闭合，用于验证左右曲线隔离 |
| `subtle_smile` | `mouthCornerPullL/R` | 轻微微笑 |

片段位于 `/Game/DataMake/Animations/CC5/P0RuntimePilot/{F02|M02}/Face`，全部为零骨骼轨道的 curve-only additive AnimSequence。FullReference 只有一个合并 SkeletalMeshComponent；当这些 `CTRL_expressions_*` 曲线直接标为 MorphTarget 时，组件上的 Auto Setup Post Process 会和直接 Morph 重复处理眼区并产生蓝白眼罩。正式 Wrapper 因此固定 `disable_post_process_blueprint=true`。

这个契约不包含 eyeLook，也不声明眼球骨骼注视。需要 eye-bone + curve 混合时，使用已经通过 `VAL-UE-02` 的模块化 Hybrid 路线，不能把两种契约混成一个 AnimBP。

## 5. 组装流程

1. 从机器注册表选择 Body motion，并检查其 `facial_channels` 和 `reuse_policy`。
2. `replaceable` 才能从白名单选择 Face clip；`paired/locked` 保留原组合。
3. 选择运行时契约：模块 Hybrid 或 FullReference 直接 Morph，不允许混用。
4. 模块 Hybrid 将身体动画接入 v003 Body 分支、面部片段接入 `cc_base_facialbone` 分支，保留 neck/head，开启 `propagate_curves_to_followers`，并由 eyeLook 曲线与 Rig Logic 求值眼球。
5. FullReference 将身体和 curve-only 面部片段接入 P0 AnimBP，Wrapper 必须禁用 Post Process；仅使用该契约已批准的四种面部状态。
6. 用 Neutral Control 对照头颈变换和面部曲线。
7. 通过对应自动矩阵与原图视觉检查后，才把组合登记为可用。

## 6. 当前验证结果

v003 已通过 `2 body × 5 face state` 的 10 个组合。准确复跑入口只在 [`VAL-UE-02`](../validation/VALIDATION_CATALOG.md) 维护。

```text
D:\UE\Lance_Work\00_engine\outputs\unreal_character_import\m02_face_hybrid_review_v003\pie_review.json
D:\UE\Lance_Work\00_engine\outputs\unreal_character_import\m02_face_hybrid_review_v003\m02_face_hybrid_pie_contact_sheet.png
```

通过条件包括：

- 每个 Actor 20 个组件、19 个 follower。
- 无 follower 丢失 Body Leader。
- 目标曲线与源片段一致。
- 面部层不改变 `neck_01`、`neck_02`、`head` 超过容差。
- 眼球由曲线驱动且没有直接眼骨冲突。

当前 `pie_review.json` 不记录关卡保存状态。wrapper 会在 `finally` 中清理验证 Actor，但 stage 使用过非 transient actor，因此运行后必须检查 Main 关卡脏包并避免误保存测试对象。

FullReference P0 已通过 `4 body state × 4 face state` 的 16 个组合和 24 张截图；准确复跑入口由 [`VAL-UE-04`](../validation/VALIDATION_CATALOG.md) 维护：

```text
D:\UE\Lance_Work\00_engine\outputs\unreal_character_import\p0_runtime_pilot_20260819_v1\runtime_review\pie_runtime_review.json
D:\UE\Lance_Work\00_engine\outputs\unreal_character_import\p0_runtime_pilot_20260819_v1\runtime_review\p0_runtime_pilot_contact_sheet.png
```

该门禁确认 F02/M02 双眼眨眼、单眼非对称眨眼和轻微微笑均正常，蓝白眼罩、明显眼球外露和眼睑穿模均未出现。它是 P0 技术通过，不是全部动画或生产池批准。

## 7. Elder Morph Pilot

当前 UE Pilot 的 Morph 名为 `Full_Face_Elder`。它不是通用运行时年龄系统，而是由同一角色不同年龄快照生成的拓扑一致差值，并为支持组件生成对应 Morph。

准确复跑入口只在 [`VAL-UE-03`](../validation/VALIDATION_CATALOG.md) 维护。

已验证权重：

```text
young  = 0.0
middle = 0.5
older  = 1.0
```

证据：

```text
D:\UE\Lance_Work\00_engine\outputs\unreal_character_import\m02_elder_morph_review_v001\pie_review.json
```

报告通过 6 个案例：三档中性，以及 older 的 Blink、Smile、Jaw Open；`component_support_consistent=true`，曲线和权重错误为空。

### 7.1 重要边界

- 此 Morph 只对同一身份、同一拓扑、同一 Vertex ID 顺序有效。
- 当前快照中部分毛发与服装组件也含同名 Morph；这不代表任意后来替换的资产会自动支持。
- 不能把 M02 的 Elder delta 应用到另一个随机脸或另一个 BodyFit。
- 正式年龄变体应为目标身份生成配对快照，并记录源哈希和支持组件。
- 身体老化还没有进入生产流程。

## 8. 新动画接入检查

1. 导入到 `/Game/Vendor/Reallusion/CC5/Animations/...` 并保留源资产。
2. 检查 Skeleton、长度、root motion 和采样率。
3. 枚举所有骨骼轨道和曲线。
4. 判断 `none/curves/bones/hybrid`。
5. 判断 `replaceable/paired/locked`。
6. 如需可重组 Body-only，删除面部轨道后验证身体、颈部和头部动作未损失。
7. 如需 Face-only，保留必要支撑骨骼，明确排除直接眼骨轨道。
8. 更新机器注册表。
9. 运行组合矩阵并生成人工联系表。
10. 自动和人工都通过后标记 `approved_pilot` 或更高。

## 9. 停止条件

- 曲线存在但 follower 不响应。
- 面部层覆盖或冻结颈部/头部动作。
- 眼球由骨骼和 Rig Logic 同时竞争。
- Jaw Open 只有曲线而牙齿、舌头或下颌支撑不正确。
- 完整表演被错误拆成可随机组合。
- Elder Morph 用在不同拓扑或未登记组件。
- 只凭单帧看起来正常便跳过闭眼、视线、微笑和张嘴验证。

## 10. 当前同步债务

`dm_asset_index.json` 已于 2026-08-19 在线核对并升级为 version 4，同时登记模块化 M02、FullReference F02/M02、三套 AnimBP 和两份矩阵报告。仍需同步的是哈希锁定候选注册表/Bundle 的生命周期状态；不得回写历史 Manifest，应通过新版本状态迁移完成。
