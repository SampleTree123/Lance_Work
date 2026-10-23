# WF-60 场景、相机与 Sequence

> 文档 ID：`WF-60`
> 文档类型：`workflow`
> 生命周期：`current`
> 前序：`WF-50`
> 后序：`WF-70`
> Exit Gate：`GATE-60 SEQUENCE_ACCEPTED`
> 最近核验：2026-08-25

## 1. 目的与使用时机

冻结角色安全锚点、场景、灯光、相机和动作窗口，并建立能够按配置生成单节点视频的 Sequence 模板。

## 2. 前后序与进入条件

- 前序：`WF-50`；后序：`WF-70`。
生产 Look 和表演组合通过 `GATE-50`，媒体规格已在批次定义中接受。

## 3. 输入

场景地图、角色 Blueprint、动作窗口、相机定义、帧率/时长和 MRQ Profile。

## 4. 正常流程

| 步骤 | 操作 | 精确实现或机器入口 | 本步输出 |
| --- | --- | --- | --- |
| 1. 冻结场景与锚点 | 选择 DataMake 场景引用、角色位置、朝向和安全活动范围 | 当前 Object Path/矩阵由 [`first_batch_local_render_matrix_20260824_v1.json`](../../../../../00_engine/scripts/unreal/first_batch_local_render_matrix_20260824_v1.json) 冻结；规则见 [场景 Technical](../technical/unreal/SCENE_CAMERA_SEQUENCE.md#3-相机与锚点) | Scene/Anchor Registry |
| 2. 冻结相机 | 建立稳定 Camera ID、构图、焦距和裁切规则 | 相机定义由同一矩阵与 [场景 Technical](../technical/unreal/SCENE_CAMERA_SEQUENCE.md#1-第一批输入与冻结配置) 共同解释 | Camera Registry |
| 3. 构建验证 Sequence | 将动作窗口、InPlace Override、角色和四相机绑定到 DataMake Sequence | 系统入口 [`run_first_batch_20s_sequence.py`](../../../../../00_engine/scripts/unreal/run_first_batch_20s_sequence.py)，UE Payload [`ue_build_first_batch_20s_sequence.py`](../../../../../00_engine/scripts/unreal/ue_build_first_batch_20s_sequence.py) | 版本化验证/自动化 Sequence |
| 4. 构建渲染 Profile | 按批次冻结时长、FPS、分辨率和MRQ设置；第一批为5秒/30FPS | [`run_first_batch_render_profile.py`](../../../../../00_engine/scripts/unreal/run_first_batch_render_profile.py) 与 [`ue_build_first_batch_render_profile.py`](../../../../../00_engine/scripts/unreal/ue_build_first_batch_render_profile.py)；参数所有者见 [渲染 Technical](../technical/rendering_release/RENDER_EXECUTION.md) | 版本化 MRQ Profile |
| 5. 审计与视觉验收 | 检查 Actor/Camera Cut/动画绑定、帧范围、时间运动、T-pose 和构图 | `ue_audit_first_batch_day3_layout_motion.py`（历史脚本已退役） 与 [视觉审查](../technical/validation/VISUAL_REVIEW.md) | `VAL-SCENE-01` 报告与视觉证据 |

第一批正式节点每次只绑定一个 `camera_id` 和150帧，不要求把四个视角并行渲染或永久拼在一个20秒Sequence中。新版本相机/时长pilot见[场景Technical §7](../technical/unreal/SCENE_CAMERA_SEQUENCE.md#7-相机动作小样2026-10-09)：只作独立试验，冻结精确窗口/轨迹和编辑对共享输入后验证，不回写第一批或自动取得生产Gate。

实验性动作替换的镜头配方/派生轨迹关系见[ADR-0018](../project_management/decisions/ADR-0018-ACTION-DEPENDENT-STABLE-CAMERA.md)：同配方可按新动作生成新平滑轨迹；外观编辑继续共享冻结轨迹，第一批生产配置不自动改变。具体实施见[Technical §9](../technical/unreal/SCENE_CAMERA_SEQUENCE.md#9-稳定跟拍镜头试验2026-10-10)。

## 5. 输出契约

| 输出 ID | 逻辑产物 | 存储类别 | 生产所有者 |
| --- | --- | --- | --- |
| `OUT-WF60-SEQUENCE-TEMPLATE` | 场景/相机 Registry、角色锚点、参数化 Sequence 和 MRQ Profile | `versioned_registry` + `ue_asset` + `run_evidence` | [场景、相机与 Sequence](../technical/unreal/SCENE_CAMERA_SEQUENCE.md) |

### 输出组成、用途与下游

| 组成 | 实际内容 | 为什么需要 | 下游消费者 |
| --- | --- | --- | --- |
| Scene/Anchor Registry | 地图、角色锚点、朝向和安全范围 | 让不同 Look 使用同一空间语义 | `WF-70` 节点定义与 `WF-80` staging |
| Camera Registry | 稳定 Camera ID、变换、镜头和构图规则 | 把相机变成可追溯编辑轴 | 图、Prompt 和渲染器 |
| Sequence/Binding 模板 | DataMake Sequence、Actor Binding、动作窗口和 Camera Cut | 避免每个节点手工重建时序绑定 | `WF-80` 节点执行器 |
| MRQ Profile | 分辨率、FPS、帧范围和渲染设置 | 确保本地与服务器像素/时序契约一致 | 本地 Smoke、服务器基准和正式渲染 |
| 布局/动态证据 | 审计报告、取景截图/视频和人工结论 | 证明 Object Path 存在之外的构图与运动正确 | `VAL-SCENE-01` 与 `GATE-60` |

当前 UE 资产和证据位置由 [WF-60 状态](../project_management/status/workflows/WF-60.md#当前输出与证据) 指定；稳定组成与保留语义见 [输出契约目录](../technical/output/OUTPUT_CONTRACTS.md#37-out-wf60-sequence-template)。

## 6. 必需验证

| 验证 ID | 角色 | 何时需要 |
| --- | --- | --- |
| `VAL-SCENE-01` | `required` | 场景、角色锚点、相机、动作窗口、Sequence 或 MRQ Profile 变化后 |

定义、证据和通过条件见 [验证目录](../technical/validation/VALIDATION_CATALOG.md)。

## 7. Exit Gate

`GATE-60 SEQUENCE_ACCEPTED` 要求全部相机取景正确、角色在有效范围、动作窗口精确、绑定稳定、时间上存在真实运动。

## 8. 技术与状态

- [场景、相机与 Sequence](../technical/unreal/SCENE_CAMERA_SEQUENCE.md)
- [渲染执行](../technical/rendering_release/RENDER_EXECUTION.md)
- [当前 WF-60 状态](../project_management/status/workflows/WF-60.md)

## 9. 失败与恢复

保留人工布局源，不原地覆盖。派生 Sequence 使用版本化 Object Path；构图或绑定失败时从布局源重建。
