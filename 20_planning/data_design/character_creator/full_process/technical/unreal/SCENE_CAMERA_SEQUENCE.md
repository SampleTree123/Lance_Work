# 场景、相机与 Sequence

> 文档 ID：`TECH-UE-03`
> 文档类型：`technical`
> 生命周期：`current`
> 适用阶段：`WF-60/WF-80`
> 实现所有权：场景引用、Actor 锚点、四相机、五秒 Sequence 和渲染舞台
> 验证所有权：`VAL-SCENE-01`
> 输出契约：`OUT-WF60-SEQUENCE-TEMPLATE`
> 运行环境：UE 5.8 Editor、Sequencer、Movie Render Queue
> 最近核验：2026-08-25

## 1. 第一批输入与冻结配置

| 对象 | 冻结值 |
| --- | --- |
| 场景 | `tokyo_stylized_v1` |
| DataMake 关卡 | `/Game/DataMake/Scenes/TokyoStylized/L_DM_TokyoStylized` |
| Actor 锚点 | `first_batch_actor_anchor_v1` |
| 相机 | `near`、`far`、`high`、`side` |
| 时长 | 5 秒 |
| 帧率/帧数 | 30 FPS / 150 帧 |
| 分辨率 | 2560 × 1440 |
| 自动化 Sequence | `/Game/DataMake/Sequences/FirstBatch/Automation/LS_DM_FirstBatch_RenderWorkspace_v001` |

精确对象路径和绑定由 `first_batch_graph_source_20260824_v1.json` 与 `first_batch_local_render_matrix_20260824_v1.json` 决定。

## 2. 组织原则

外部场景源不修改；`/Game/DataMake/Scenes` 保存可控引用/副本和自有布置。测试 Actor、Camera 和 Sequence 不写入源 Vendor 地图。自动化使用专用 staging map/Sequence，避免污染人工验收关卡。

## 3. 相机与锚点

- 四相机描述同一语义状态的四个视角，因此 `camera_id` 是节点编辑轴。
- 角色根位置从统一锚点推导，不能为每个 Look 手工漂移。
- 构图必须覆盖完整身体、留出固定边距，主体中心不能随 Look 明显偏移。
- Root Motion 动作可在批准范围内移动；只有指定 Catch Breath 使用 InPlace。
- 相机不实时追踪角色，除非未来另建版本并重新冻结节点语义。

## 4. Sequence 构建

实现入口：

- `ue_build_first_batch_20s_sequence.py` / `run_first_batch_20s_sequence.py`：四相机人工/矩阵验证序列；
- `ue_build_first_batch_render_profile.py` / `run_first_batch_render_profile.py`：MRQ Profile；
- `ue_stage_first_batch_render_look.py`：切换 Look 和舞台 Actor；
- `run_first_batch_render_matrix.py`：当前 32-Look 本地矩阵编排；
- `run_first_batch_local_sample_render.py`：单样例 MRQ 调用。
- `ue_audit_first_batch_day3_layout_motion.py`：只读核验关卡 Actor、四段 Camera Cut、动作窗口、InPlace Override 和帧范围。

正式节点渲染不要求在一个 20 秒 Sequence 中连续拍四相机。每个节点只绑定一个 `camera_id` 和 150 帧窗口，渲染器按 Render Job 设置对应相机。

## 5. Gate

1. Map、Sequence、Actor、Camera Cut 和动画绑定无悬空；
2. 帧率、播放范围和 MRQ 输出一致；
3. 首中末帧主体存在、居中、无遮挡且不是 T-pose；
4. 四相机确实产生不同视角；
5. 动作没有离开安全区域或被裁切；
6. 输出路径只写当前 Run Root，不覆盖权威媒体；
7. 临时 Actor/Sequence 在完成后清理或标记为 staging。

视觉验收方法见 [视觉审查](../validation/VISUAL_REVIEW.md)。

当前保留的 Day-3 场景/相机证据为 `%OUTPUT_ROOT%/unreal_character_import/first_batch_day3_20260823_v1/`，其策略前缀是 `unreal_character_import/first_batch_day3_20260823_v1`。

## 6. 失败与恢复

Actor、Camera Cut、动画绑定或对象路径失效时，只重建 DataMake staging 资产，不修改 Vendor 场景。构图或安全区域不合格时升级锚点/相机 Registry 和图源版本后重建受影响节点；不得只对个别 Look 手工偏移而继续复用同一 `camera_id`。UE 崩溃后先审计脏包和自动恢复内容，再从已接受 Sequence 版本恢复。
