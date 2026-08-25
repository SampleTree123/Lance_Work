# WF-08 场景、相机与 Level Sequence

> 文档角色：`workflow_runbook`
> 状态：`in_progress`
> 适用阶段：`WF-08`
> 权威范围：场景、角色、相机和序列装配的阶段契约；当前第一批受限范围
> 上级入口：[`README.md`](./README.md)
> 上游：[`WF-07-ANIMATION-AND-PROPS.md`](./WF-07-ANIMATION-AND-PROPS.md)
> 下游：[`WF-09-RENDER-DATASET-PACKAGE.md`](./WF-09-RENDER-DATASET-PACKAGE.md)
> 最近核验：2026-08-24

## 1. 目的与使用时机

在角色表演通过后，将其放入审核场景，确定地面接触、相机、灯光和 Level Sequence。本阶段是角色工厂到渲染数据管线的交接点。

## 2. 当前范围与非目标

本阶段已进入本地实现。第一批只承诺 1 个场景、1 个安全角色锚点、固定灯光、4 个静态相机候选（`near/far/high/side`）和确定性 Sequence；不做道具、移动相机、场景替换、天气或灯光编辑。冻结范围见 [第一批数据 Sprint](../planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md)。

## 3. 进入条件

- 本轮使用的 32 个 FullReference Look、10 个生产动作（每个角色使用同性 5 条）和 Happy 轻动态表情通过对应自动技术门禁；Angry/Sad 候选只保留为历史验证资产，不进入首批正式节点。
- 角色 Blueprint、表演配置、服装/毛发状态和道具依赖均可追溯。
- 目标场景是 `/Game/DataMake` 下的项目自有入口，不直接改写 Vendor 地图。

## 4. 输入与输出

第一批输入：待重冻结的 node config、32 个 Look、10 条生产动作（每个性别 5 条）、Happy 轻动态表情、场景 ID、锚点、`near/far/high/side` 相机池、30 fps 和 5 秒时长。计划输出：版本化 DataMake 关卡入口、Sequence 模板、静态相机配置、角色变换、固定灯光配置、碰撞/遮挡报告和场景 sidecar。服务器正式队列为 `32 × 5 × 4 × 1 = 640` 节点；本地已渲染 32 个历史代表案例，覆盖全部 Look、全部动作、四台相机和三种表情，但未全量渲染 Happy-only 的 640 节点。

## 5. 执行环境

使用 UE 5.8、DataMake 资产入口、Sequencer 与已验证的 UE Remote Execution 编排器。UE 必须已打开目标项目且 Remote Execution 在线；脚本不通过普通系统 Python 直接导入 `unreal`。

## 6. 执行步骤

第一批当前顺序为：选择 DataMake 场景入口 → 固定安全锚点 → 放置代表男女 Look → 10 个生产动作逐条完成地面/碰撞/可见性检查 → 固定四个镜头和焦距 → 生成确定性 Sequence 模板 → 运行 32-Look 代表矩阵 → 固化 scene/camera/anchor ID → 生成服务器队列。

### 6.1 当前场景与相机

- 关卡：`/Game/DataMake/Scenes/TokyoStylized/L_DM_TokyoStylized`。
- 审核 Sequence：`/Game/DataMake/Sequences/firstweek`。
- F02 派生试点：`/Game/DataMake/Sequences/FirstBatch/LS_DM_FirstBatch_F02_20s_Pilot_v001`。
- 当前测试角色：`CC_FB_F_ID02_O04_Blueprint_LiveLink_C_1`。
- 相机池：`near/far/high/side`；空间布局已通过只读几何审计。
- 帧率冻结为 `30 fps`，每个生产节点固定 `150` 帧（`5 s`）。

`firstweek` 是人工相机布局源，当前已经满足 `0–150 near`、`150–300 far`、`300–450 high`、`450–600 side`，不得改回四段重叠。`ue_build_first_batch_20s_sequence.py` 复制该布局并生成 20 秒动作审核序列；源 `firstweek` 不被脚本改写。第一批正式数据以“单镜头、单表情、单动作的 5 秒节点”为媒体原子，四段 20 秒序列只用于一次性审核四个机位，不作为一个训练节点。

### 6.2 JSON 动作窗口到 Sequencer 的映射

权威输入为 `00_engine/outputs/character_creator_bridge/artifacts/first_batch_action_window_selection/frozen_20260821_v4/frozen_action_windows.json`。JSON 本身不会被 Sequencer 自动执行，当前构建器为 `00_engine/scripts/unreal/ue_build_first_batch_20s_sequence.py`，外层入口为 `run_first_batch_20s_sequence.py`。它把一条动作记录翻译为：

1. 绑定角色的主 `SkeletalMeshComponent`。
2. 增加 `MovieSceneSkeletalAnimationTrack`和身体动画 Section。
3. 从 `/Game/DataMake/Sequences/FirstBatch/Templates/LS_DM_NativeSkeletalAnimationSectionTemplate_v001` 复制经过编辑器原生创建并验证可求值的 Section；禁止用 Python 空建 Section 代替该模板。
4. 在 `0–150`、`150–300`、`300–450`、`450–600` 放置四个五秒 Section，每段都重新从冻结窗口起点播放。
5. `params.animation` 在正式节点中只指向对应动作与 Happy 的派生组合 AnimSequence；现有 10 个动作 × 3 表情的 30 条组合资产保留为候选与历史证据，不代表三表情都进入正式队列。
6. 组合 AnimSequence 使用已批准 InPlace 或 BodyOnly 作为身体源；原身体动画和原三秒表情 clip 不被改写。FullReference 直接 Morph 路径固定 `disable_post_process_blueprint=true`，避免 Auto Setup Post Process 对眼区重复求值。
7. UE 5.8 使用 `first_loop_start_frame_offset`；其单位是 Sequence tick，不是显示帧，因此设置为 `round(start_seconds × tick_resolution_fps)`。例如 `1.6 s` 在当前 `24000 tick/s` 下是 `38400`。
8. 足五秒的动作已验证不会越过所选窗口；F01 的 `1.6..6.6 s` 非零偏移测试在四段相同相对帧得到相同骨骼姿态。
9. F03、F04、M02、M03 曾按 `symmetric_exact_endpoint_holds_v1` 生成精确 150 帧 IdlePadded 派生资产；F04/M03 已从生产池排除，当前有效补帧资产只有 F03 与 M02。源动作保持不变，位移/缩放误差为 0。

直接把曲线表情作为 Skeletal Animation Track 的第二行不会执行与 AnimBP `Apply Additive` 等价的组合，因此该方案已淘汰。源层仍保持身体动画和表情资产分离；Sequencer 交付层复制身体动画并嵌入已批准的表情 Morph 曲线，生成可随时重建的派生组合 AnimSequence。历史聚合报告为 12/12 动作、36/36 组合通过；当前 10 动作的 30 条三表情组合资产也通过技术门禁，但首批正式队列只引用其中 10 条 Happy 组合。表情辨识度偏轻被记录为第一批已知限制，且表情不生成编辑边。

### 6.3 InPlace 候选

原始 BodyOnly 资产保持不变。四个技术候选都可保留作证据，但第一批只批准 `ACT_F02_CATCH_BREATH` 使用 `A_DM_F02_CATCH_BREATH_InPlaceCandidate_v001`；F01、M01、M04 以及其余动作全部使用原始 BodyOnly。构建器已硬编码该例外并由审计验证，禁止按“发现 Root 位移就自动换成 InPlace”的旧规则推断。

### 6.4 五秒补齐与首帧初始化

- 补齐构建器：`ue_build_first_batch_idle_padding.py`；外层入口：`run_first_batch_idle_padding.py`。
- 补齐证据：`OUTPUT_ROOT\unreal_character_import\first_batch_day3_20260823_v1\idle_padding_build.json`。
- 补齐只复制首帧/末帧姿态，不拉伸速度、不循环短动作，也不改写源 BodyOnly。
- F02 审核序列在每个 Skeletal Animation Section 使用 `1` 帧 pre-roll；源窗口另保留 `1` 帧 Bind Pose guard。两者共同消除 MRQ 第 0 帧曾出现的 T Pose，不能删除为“多余帧”。
- 2026-08-24 的首次 32-Look 批处理出现另一类 T-pose：首例正常，替换 Look 后的后续案例整段保持 T-pose。使用全新隔离 Sequence 仍可复现，证明它与 Sequence 重用、相机、编码和动画资产损坏无关；根因是不同 Reallusion Blueprint 的默认动画模式不一致，而女性路径曾使用 `force_custom_mode=false`。
- 生产构建器现在对男女全部动画 Section 强制 `force_custom_mode=true`。`run_first_batch_render_matrix.py` 会在 MRQ 前要求四段 Section、原生 Actor binding、目标 Actor 和全部 `force_custom_mode` 同时通过，并在渲染后检查五个时间采样帧确有可见运动；不满足时拒绝继续或断点复用。该门禁解决“整段 T-pose”，与上一条解决“第 0 帧 Bind Pose”的 pre-roll/guard 不可互相替代。

### 6.5 相机光学与清晰度

当前人工布局使用 `far=35 mm`，`near/high/side=20 mm`，四台相机均关闭景深焦点求值。关闭景深可让角色与环境同时清楚，适合第一批训练数据，应保持为默认。当前相机位置已经由用户调整并通过构图审计，本轮不自动改写。

画质改进建议按以下优先级另做 A/B，而不是直接覆盖当前机位：

1. `far` 保持 `35 mm`。
2. `near` 从 `20 mm` 试到 `35 mm`，相机后移以保持现有半身构图；需要更弱透视时再试 `50 mm`。
3. `high/side` 从 `20 mm` 试到 `28–35 mm`，同步后移，减少头身和边缘透视拉伸。
4. 第一批保持关闭景深；未来若启用手动焦点，焦点距离锁定角色且光圈先用 `f/5.6–8`，不能沿用浅景深电影镜头作为数据默认值。
5. 需要逐帧锐利训练图时优先关闭或降低 Motion Blur；该项需单独 A/B 后再进入冻结 Render Profile。

## 7. 退出门禁

门禁为 [`GATE-08 SCENE_READY`](../validation/README.md)。它至少需要 `VAL-SCENE-01` 与 `VIS-SCENE-01`，覆盖地面接触、角色/场景/道具碰撞、全时段相机可见性、裁切、焦点、`30 fps`、无重叠 Camera Cut、JSON 窗口偏移以及身体/Happy 组合。结构审计位于 `OUTPUT_ROOT\unreal_character_import\first_batch_day3_20260822_v2\layout_motion_audit.json`；补齐、组合和序列报告位于 `OUTPUT_ROOT\unreal_character_import\first_batch_day3_20260823_v1\`。参数化 5 秒 Sequence 与 32-Look 本地代表矩阵已经通过机器门禁，证据为 `OUTPUT_ROOT\unreal_render\first_batch_32look_matrix_20260824_v002\matrix_report.json`。当前剩余工作是把真实 scene/camera 稳定 ID、四相机与 Happy-only 契约写入正式 640 节点源，并在服务器正式节点上继续记录服装兼容性和视觉抽检结果。

## 8. 失败与恢复

当前审核 Sequence 与原始 BodyOnly 动画必须保留。相机绑定、五秒窗口和 InPlace 处理均通过新建 DataMake 派生资产恢复，不得原地改写 Vendor 地图、Vendor 动画或原始 BodyOnly 资产。

## 9. 技术依据与下一阶段

UE 资产边界见 [`ADR-0007`](../decisions/ADR-0007-UE-VENDOR-DATAMAKE-MODULARITY.md)，当前任务见 [第一批数据 Sprint](../planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md)。本阶段实现并通过后进入 [`WF-09`](./WF-09-RENDER-DATASET-PACKAGE.md)。
