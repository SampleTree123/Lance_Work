# 场景、相机与 Sequence

2026-10-14：早期场景清理完成。田园、哥特城堡及对应旧关卡已删除，释放约3.6 GiB；东京和两张仍被模板引用的工作关卡统一迁入Content/Scenes/TokyoStylizedEnvironment。旧DataMake/Scenes和旧东京目录已移除。当前25个场景包、12138个包内资产文件（含77张关卡），东京已从新路径正常打开；相机拍摄继续暂停。


> 文档 ID：`TECH-UE-03`
> 文档类型：`technical`
> 生命周期：`current`
> 适用阶段：`WF-60/WF-80`
> 实现所有权：场景引用、Actor锚点、按批次冻结的相机/Sequence/渲染舞台，以及版本化相机动作小样
> 验证所有权：`VAL-SCENE-01`
> 输出契约：`OUT-WF60-SEQUENCE-TEMPLATE`
> 运行环境：UE 5.8 Editor、Sequencer、Movie Render Queue
> 最近核验：2026-10-20（禁用发型控件324case／实际Tk三状态通过；女性鞋子反馈待明确）

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
- 第一批相机不实时追踪角色。新的动态相机小样必须另建版本并锁定轨迹/输入，不回写第一批节点语义。

### 3.1 第二批场景候选

第二批场景数量暂不冻结。场景确定后，由用户为每个场景选择可用拍摄点位和相机变换；每个点位必须登记稳定 `camera_id`、锚点、安全范围和构图规则，再进入 `WF-60` 的 Sequence/矩阵。不能先按固定相机数量生成笛卡尔积，也不能把单个场景的点位假设复制到其他场景。

## 4. Sequence 构建

实现入口：

- `ue_build_first_batch_20s_sequence.py` / `run_first_batch_20s_sequence.py`：四相机人工/矩阵验证序列；
- `ue_build_first_batch_render_profile.py` / `run_first_batch_render_profile.py`：MRQ Profile；
- `ue_stage_first_batch_render_look.py`：切换 Look 和舞台 Actor；
- `run_first_batch_render_matrix.py`：当前 32-Look 本地矩阵编排；
- `run_first_batch_local_sample_render.py`：单样例 MRQ 调用。

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


## 7 相机动作小样（2026-10-09）

本节拥有`%OUTPUT_ROOT%/unreal_character_import/camera_motion_pilot_20261009_v1/`及下列实现。主阶段WF-60，关联WF-50/80，输出契约OUT-WF60-SEQUENCE-TEMPLATE，默认unclassified保护。当前为实验性相机pilot，不是已接受的正式生产媒体。本次完成范围由[归档计划](../../project_management/history/completed_plans/PLAN-2026-10-CAMERA-MOTION-PILOT.md)保存。

### 7.1 当前实现与版本

当前相机运动计划为camera_motion_pilot_plan_v3.json；StudioV2、MapsV2、SequencesV2是目录版本，实际资产leaf为v003。逐场景回执位于sequences_v3/，聚合为prepared_jobs_v2.json（generation=3）。旧轨迹、旧v002场景和失败样片保留，不作当前入口。

本轮暂定统一10秒：≥10秒素材取连续10秒@1倍，默认前10秒；7秒至不足10秒可整段匀速慢放，body_rate=source_duration/10；<7秒排除，禁止身体循环或冻结补时。表情保持1倍、每5秒重复，不随身体慢放。相机按最终10秒身体时间轴规划；同一编辑对共享轨迹、镜头、源窗、时间轴及随机输入，不按编辑后的衣发包围盒分别重新求解。此为用户后续授权，替代本pilot启动时“不慢放”限制；第一批5秒/150帧与旧完整动作循环原速规则保持。

### 7.1.1 相机候选、动作兼容与真实位移

9个静态候选是正面全身、上半身、头部近景、远景、俯视、仰视、侧面、斜侧和背面；5类动态为推进/拉远、跟随、环绕、摇摄和变焦。这是本次供审查的候选范围，不是已规定今后每个动作必须生成14个镜头，也不是最终生产相机数量。完整画面检查后才能筛出适用组合。

动作兼容目前按实际需求分为小范围活动、姿态/高度变化、朝向变化、大幅肢体活动及明显位移，并允许重叠。motion_samples_v1.json中前10秒采样显示以下差异（数值为root在水平面相对首帧的最大距离，男女范围，属于采样几何而非视觉接受）：

| 代表动作 | 本轮观察到的范围 | 相机需要处理的重点 |
| --- | --- | --- |
| 002 调整站姿 | 约25–26cm | 小范围活动、头部/上半身构图稳定 |
| 003 弯腰伸展 | 约33–34cm | 躯干高度变化；仅根据水平位移不能判断头部是否出框 |
| 029 甩头转身 | 约16–17cm | 朝向变化，固定正面会随人物转身成为侧/背面 |
| 030 舒展舞步 | 约97–99cm | 四肢展开及局部移动，不能直接按窄幅站姿近景处理 |
| 008 向前行走 | 约582–594cm | 明显前进，固定镜头需要覆盖路径，跟随镜头需保持合理方向 |
| 035 边走边思考 | 约213–218cm | 位移与上半身手势并存 |

这些动作没有统一转换为原地动作。Actor位置保持原点并不代表人物不移动：本轮动画自身的骨骼位移让身体走出数米。判断时同时读取身体/root/骨盆位置与方向，不能只看Actor transform，也不能把“调整站姿”等名称直接当作完全原地。固定镜头与跟随镜头会呈现不同的空间关系；当前脚本只预先规划相机，不消除素材位移。

同一种镜头类型可以按不同源动作预先计算不同的安全距离、目标和路径；计算完即锁定该shot的具体轨迹。一个编辑对必须复用相同的冻结镜头及时间轴，不能因换人、换衣或换发色临时重新求解。动作兼容分类用于安排试验与判定适用范围，不声称所有静态/动态镜头适合所有动作；当前配对实测范围是发色编辑，其他编辑类型仍须另验。

所有下列实现登记experimental，测试登记utility：

| 职责 | 本节拥有的实现 |
| --- | --- |
| 动作采样与规划 | ue_camera_motion_samples_v1.py、camera_motion_planner_v1.py、ue_camera_body_retime_v1.py |
| 舞台/Sequence准备 | ue_camera_pilot_stage_v1.py、ue_camera_pilot_prepare_v1.py、ue_camera_prepare_studio_v2.py、ue_camera_sequence_builder_v1.py、ue_camera_studio_lighting_v2.py |
| 渲染与媒体 | ue_camera_pilot_render_v1.py、encode_camera_pilot_v1.py、build_camera_pilot_gallery_v1.py |
| 审查网页与重新打开 | camera_pilot_gallery_v2.html（网页模板）、open_camera_pilot_gallery_v1.py（本机服务启动/复用）；生成入口为build_camera_pilot_gallery_v1.py |
| 来源/现场/配对核验 | audit_camera_pilot_sources_v1.py、ue_camera_scene_audit_v1.py、audit_camera_pair_repeatability_v1.py |
| 测试 | tests/test_camera_motion_planner_v1.py、tests/test_camera_follow_heading_v2.py、tests/test_camera_body_retime_v1.py、tests/test_camera_sequence_builder_v1.py、tests/test_camera_studio_lighting_v2.py、tests/test_camera_pilot_render_v1.py、tests/test_camera_scene_audit_v1.py、tests/test_encode_camera_pilot_v1.py |

Run内dispatch、诊断、历史probe辅助脚本归本scope，不是默认生产入口。

### 7.2 关键实现规范

每个新场景必须复制后显式LoadLevel并核对当前world，再修改自有Actor；为新world重建专属Sequence并回读绑定。Body使用原生动画section模板，五face保留独立动画轨道。相机位置/旋转/FOV各301个线性键，输出30fps的[0,300)共300帧；frame300仅为插值端点。旋转通道按roll/pitch/yaw并解缠，动画组合最终以1倍播放。

对选中角色所有有网格、非Body且parent=Body的骨骼组件开启use_attach_parent_bound。Hair仍要求parent与leader精确指向同一个Body；Tongue/Eyes/Teeth/Tearline/EyeOcclusion实际Leader必须为None，并具有既有DM_CCWH_SLOT_COPY_<Component> Actor标签，保证ConstructionScript重载时走clear-Leader分支。共享蓝图未修改。设置属性可能重建组件，实施每次按名称重新获取并在保存重载后核验，不能使用TRASH旧引用。

StudioV2 helper仅允许当前MapsV2且MRQ空闲，替换自有Key/Fill/Back为四盏白色DirectionalLight：1.8/1.2/0.6/0.6 lux，仅主灯投影。当前manual exposure bias为+0.2（旧probe为-0.8）。自有地板使用绝对世界XY厘米坐标，100cm一格，FloorXY相加取Abs再Fmod2，线性灰0.18/0.24、roughness1；负坐标不会产生负alpha。只创建StudioV2新材质，已存在且spec一致/非dirty时复用，不改旧材质；调用者保存地图。

revised现场审计读取原30/1/3清单及其哈希，并核验prepared_jobs_v2精确pin当前相机plan v3和完整34 ID范围。逐图只加载不保存，记录身份网格、可见衣发、骨骼及材质父链包SHA（/Game、/Engine、/InterchangeAssets），检查actor/Body坐标与每个binding都属于当前world。递归纹理闭包不在本审计范围。任何dirty map拒绝而不丢弃，dirty content变化停止；结束恢复进入时pilot地图，并比对原审查图恢复基准前后SHA。

### 7.3 当前证据与待验范围

本轮探索性相机小样已完成工程交付，等待用户选择镜头及评价动作节奏。34份v003场景/专属Sequence通过现场绑定与来源核验；35个渲染任务全部成功（34审查＋1复现），35段视频均完整解码为300帧、30fps、1280×720、10秒。旧源文件及用户全局MRQ队列保持，原审查地图事故按恢复证据单列，不宣称从未改动。

34条审查视频包含9个静态类型、5类动态轨迹和6个基础代表动作，另有男女慢放及360°环绕补充。root16条、planner18条各观察20张代表帧，报告绑定最终媒体；这不是人工逐帧审查，也不代表全40身份/衣发/环境均通过。首版浏览器入口实测34条、静态17/动态17筛选、搜索、并排播放/暂停、清空对照及循环切换；男女慢放样例关闭循环均准确结束在10秒，重新开启循环只影响浏览器播放，不改变文件内部动作或片长。当前改版入口及其后续验证见§7.4.1。

R04的研究验证已经执行并交付明确的负面结果：配对结构只差四块Hair材质，其他项含眼睛一致；同配置05/34的300帧重渲染均不逐像素相同。pair_repeatability_audit_v1.json保留audit_complete=true、success=false；MAE约0.013514（0–255尺度）、PSNR约65.0577dB、变化像素约4.01%，其中约97.1%只差1色阶。这些是描述，不是容差门槛。最差帧的强差异集中在脸发区域，地面也有低幅差异，根因未确证；严格确定性生产未获通过。本计划完成的是第一轮配置/轨迹与真实重跑研究验证，不把失败性质改写为达成。

完整回归1072项通过。最终证据链由completion_audit_v1.json、browser_review_v1.json及documentation_final_delivery_v1.json衔接；用户镜头选择、慢放自然度、全身份/穿搭适用性和正式生产接受均未代签。

本Run最新证据分层如下：

| 范围 | 证据 | 当前结论 |
| --- | --- | --- |
| 时长政策/来源候选 | offline_motion_inventory_v2.json、camera_motion_pilot_plan_v3.json | 当前版本；几何候选不代替视觉 |
| 34场景准备/来源/绑定 | prepared_jobs_v2.json、scene_binding_audit_v2.json、source_protection_audit_v5.json | 限定静态核验通过 |
| 三代表实际动作/组件 | studio_three_pose_probe_v3.json | 960采样；非Body Bounds与Body中心差0、五face Leader=None；root末帧观察恢复；不推广全矩阵 |
| 配对/严格复现 | pair_repeatability_audit_v1.json、repeat_difference_localization_v1.json | 配对结构通过；300帧逐像素复现未达成，audit_complete不等于success |
| 完整渲染/媒体 | render_receipts/matrix_v1.json、media_validation_matrix_v1.json | 35 jobs成功，35视频解码规格通过；34条视频提供审查 |
| 抽帧观察 | probes/matrix_static_live_v1/root_visual_review_v1.json、probes/matrix_visual_live_v1/dynamic_sampled_visual_final_v1.json | 16＋18条，每条20张代表帧；不代表人工逐帧审查或用户最终接受 |
| 回归 | full_regression_v3.xml | 1072 passed；前两次沙箱权限失败保留，不以失败环境结果代替最终通过 |
| 首次入口与交付（历史） | browser_review_v1.json、completion_audit_v1.json、documentation_final_delivery_v1.json | 原交付证据保留；探索验证完成，pixel-exact失败和用户选择待定明确保留 |
| 当前入口修复/改版 | gallery_review_redesign_v2.json、gallery/browser_redesign_observations_v2.json、documentation_gallery_redesign_v2.json | HTTP恢复及新版交互实测；34条原视频SHA不变，不重新接受镜头或生产 |

### 7.4 渲染及失败终态规则

使用独立MoviePipelineQueue/PIE executor，记录用户全局队列快照但不修改该队列。新attempt写全新renders/<attempt_id>/；render_receipts/<attempt_id>.json持久化终态。1280×720、30fps/300 PNG，spatial_samples仅允许1或4（默认1保留probe，矩阵4），temporal固定1，warmup16/8，关闭motion blur。回调只记录终态，不切换场景或启动下一队列。响应截断/结果未知时先查原executor状态，不重提相同任务。

渲染终态success不能代替媒体解码、完整角色可见性或用户视觉接受。完整矩阵媒体和抽帧核验现已具备；有限慢放自然度与最终相机偏好仍由用户判断。严格重复性未通过时不得晋升确定性生产Gate；本研究性pilot已按“执行探索验证并报告结果”范围结项；不把失败比较改为通过，也不接受确定性生产。本轮Catalog/Inventory、媒体与文档审计按交付时快照固定；后续正式生产限制需另行获授权处理。

### 7.4.1 审查入口及原始草案边界

当前入口为本Run gallery/index.html，本地浏览器地址为http://127.0.0.1:8876/gallery/index.html。该地址需要本机服务运行：2026-10-09用户报告打不开时，8876端口没有服务监听，34条视频仍存在；已通过open_camera_pilot_gallery_v1.py重新启动，并实测再次启动复用同一服务。服务只监听127.0.0.1，不向外网开放，不操作UE。

后续重新打开时，双击本Run的gallery/打开相机审查.cmd。它调用上述experimental启动器，检查本机审查入口，必要时重新启动服务，再用默认浏览器打开。不要把交付时的服务PID当作永久有效状态。CUA内置浏览器拒绝file://协议，本轮不声称直接打开HTML或离线fallback已验证；实际交付入口为HTTP与可重新启动的CMD。

camera_pilot_delivery_manifest_v1.json拥有实际34条审查清单；camera_motion_pilot_plan_v3.json拥有30主镜头轨迹，补充由retime_pilot_plan_v1.json及extra_orbit_pilot_plan_v1.json登记。网页模板camera_pilot_gallery_v2.html由build_camera_pilot_gallery_v1.py读取生成，媒体路径来自交付清单；本轮界面后续修复不重开已归档相机计划，不重新渲染视频或取得正式生产接受。

新版按7个动作分组，默认显示“向前行走”的女性固定远景11与女性前方跟拍13。操作顺序为：

1. 左侧选择一个动作，页面载入该动作的推荐对照。
2. 点击“两边一起从头播放”，比较相机取景与移动；“两边暂停”停止，“继续播放”保留当前进度。默认循环用于重复观看，关闭后每条视频在10秒结束。
3. 在下方当前动作的样片卡片点“放到左边”或“放到右边”更换对照；“恢复推荐对照”同时还原推荐两条及男女都显示的筛选。每条保留固定样片编号，可据编号向用户会话汇报偏好；网页不会自动记录最终选择。

gallery_review_redesign_v2.json记录实际浏览器验证：7组共34条全部可达，上述播放/暂停/继续、关闭循环到10秒、左右替换、性别筛选、推荐恢复及说明展开均通过；34条视频SHA与原媒体验证逐条一致。最终页面恢复11/13且循环开启，截图为gallery/review_redesign_default_v2.jpg。CMD以--no-browser实测服务复用，浏览器内可见页面另由CUA验证；本轮未通过shell自动化测试操作系统默认浏览器启动。此次仅做入口修复、定向实测及文档审计；1072项完整回归是原相机交付历史，不作为本次改版重新跑过的结论。

camera_design_v1.md是早期设计草案，其中10–15秒候选和初始动作讨论保留历史，不是当前时长或最终矩阵；不修改该已固定草案来假装它从开始就正确。当前规则以本节、plan_v3及delivery_manifest为准。浏览器“双条同时播放”用于视觉对比，不是逐帧同步测量；精确对齐使用渲染帧与实际配对审计。

### 7.5 保留的失败与恢复历史

- 首条first_media_validation_v1.json仅证明静态正面300帧/30fps/10秒。随后动态probe暴露局部RectLight照明不足、跟随方向和速度问题，采用新版照明及轨迹v3；旧样片/计划保留。
- SaveMap(newpath)生成副本却未切换world，首轮误保存原CFD40审查地图。stage_recovery_v1.json记录从操作前完整快照恢复9个Actor、背景与原位置，恢复文件并非此前磁盘字节副本。两份事故/操作前副本与SHA保留；显式LoadLevel后的原图哈希未变不代表此前从未修改。
- hair_dynamic_offline_observation_v1.json记录旧/新照明均缺发；hair_bounds_diagnosis_v1.json记录320采样A/B父Bounds修复。v002三镜头又暴露衣鞋和五face Bounds停起点，studio_three_pose_probe_v2.json是失败证据。v003扩大父Bounds与Actor面部路由修复，获得当前三代表有限证明；不改写旧失败。
- 旧Sequence跨复制world绑定不可靠，故新版每个map重建专属Sequence。续跑旧回执str(Guid)包含内存地址，改为稳定GUID to_string，仅兼容唯一已知旧生成器SHA；15份旧资产/回执保持不改写，准备随后继续。对象未变的只读兼容不等于可以忽略任意输入变化。


## 8 共用镜头库与补测（2026-10-10）

本节拥有 `%OUTPUT_ROOT%/unreal_character_import/camera_library_expansion_20261010_v1/`，主阶段WF-60，关联WF-50/80；沿用OUT-WF60-SEQUENCE-TEMPLATE与VAL-SCENE-01，默认unclassified保护。当前为实验性扩充，[当前计划](../../project_management/history/completed_plans/PLAN-2026-10-CAMERA-LIBRARY-EXPANSION.md)拥有验收目标，不改变第一批冻结生产入口与Gate。

### 8.1 共用库与接受范围

库按观察朝向、拍摄景别、相机运动分别配置，再针对源动作十秒轨迹确定具体参数。固定正面全身与前方跟拍可以拥有相同朝向/景别；人物实际位移决定两者是否产生有意义差异。小幅原地动作下相近效果可标记低优先级，不等同技术不支持。近景不能通过无声扩大为全身来假装构图通过。

组合状态分开保存：原样片已认可、当前样片不采用、需修改重测、尚未覆盖候选。未覆盖不是排除；动作名称不是兼容性依据。先检查完整十秒的目标可见、关键部位裁切、运动连续性，再进行人工画面与差异判断。俯视跟拍、上半身跟拍等复合候选可以存在，不受首轮展示镜头名称限制。

原34样片的新反馈单独记录，不修改原完成清单/媒体或当时pending历史。认可只限被审查组合；32/33慢放自然不外推所有慢放动作。180°环绕原样片认可与常规库是否默认纳入分开。正式确定性生产仍受§7记录的pixel-exact失败限制。

### 8.2 本轮实施与证据边界

保留原34媒体和原关卡；新Run使用版本化场景、专属Sequence与独立渲染队列。时间规则沿用§7.1，相机轨迹必须按最终10秒身体动画预规划并冻结；同一编辑对复用轨迹，不根据衣发重新拟合。共享UE修改由root串行负责。

推进/拉远按起止构图定义可观察幅度：例如全身至上半身、上半身至全身，或大幅动作的宽全身至紧全身；具体方案必须接受源动作全段范围约束并通过新样片审查。旧幅度过小的回执保留，不用新结果覆盖。

本轮已完成14份独立场景/Sequence准备及14条10秒渲染媒体；实际新候选偏好仍待用户审查。候选生成或脚本成功不能代替真实渲染、完整媒体检查与用户偏好。未覆盖组合应有待验证/延期理由，不以自动几何检查代签人工接受。

### 8.3 实现所有权与机器入口

| 职责 | 当前实现 | 生命周期 |
| --- | --- | --- |
| 原反馈、三轴库和优先候选生成 | build_camera_library_expansion_v1.py | experimental |
| 三轴配置到301端点轨迹与骨骼代理投影检查 | camera_composable_planner_v1.py | experimental |
| 规划器针对测试 | tests/test_camera_composable_planner_v1.py | utility |
| 独立场景复制、专属Sequence准备与来源保护 | ue_camera_library_prepare_v1.py | experimental |
| 场景准备针对测试 | tests/test_camera_library_prepare_v1.py | utility |
| 独立MRQ渲染与回执 | ue_camera_library_render_v1.py | experimental |
| 原认可、新候选与幅度对照审查页生成 | build_camera_library_gallery_v1.py | experimental |
| 本地8877审查入口启动与恢复 | open_camera_library_gallery_v1.py | experimental |

本Run配置所有权：human_camera_feedback_v1.json记录原34样片的25认可/5排除/4重测及源清单SHA；composable_camera_library_v1.json拥有朝向、景别、运动轴；camera_coverage_candidates_v1.json列首批16个优先补测候选，覆盖七动作，不是完整支持白名单。expansion_plan_v1.json由规划器产生实际轨迹与几何结果；被拒绝项保留在rejected，不通过删去失败项伪装全部适配。

从 `%LANCE_ROOT%` 执行：

```powershell
python 00_engine/scripts/unreal/build_camera_library_expansion_v1.py --manifest 00_engine/outputs/unreal_character_import/camera_motion_pilot_20261009_v1/camera_pilot_delivery_manifest_v1.json --output 00_engine/outputs/unreal_character_import/camera_library_expansion_20261010_v1
python 00_engine/scripts/unreal/camera_composable_planner_v1.py --prior 00_engine/outputs/unreal_character_import/camera_motion_pilot_20261009_v1 --output 00_engine/outputs/unreal_character_import/camera_library_expansion_20261010_v1
```

以上只完成离线配置/规划，不启动UE或证明媒体效果。对照使用source_shot_id相同的源角色、动作和外观；原网页中不同性别的两条不能作为严格受控相机对。几何检查使用骨骼代理，不等同全网格可见、衣发裁切或用户视觉通过。

### 8.4 实际执行、恢复与审查入口

2026-10-10重启后 storage_recovery_probe_v1.json 只证明本Run小文件flush及读回成功，不代表D盘完整硬件健康。recovery_source_audit_v1.json 的534项中533项匹配，唯一旧CFD40原审查地图与历史post_recovery pin漂移；原因未确证，报告success=false保持，不覆盖地图、不推断损坏或归因于本轮。execution_scope_preflight_v1.json另行验证本轮14个补测实际依赖的v003源场景、Sequence、组合动画与来源回执全部匹配，允许限定新Run执行；没有把广域恢复失败改写通过。

首批16候选中14条进入实际渲染，cam_38_expand_03、cam_50_expand_15在完整301端点骨骼代理检查中因构图范围不满足要求拒绝，保留在expansion_plan_v1.json.rejected；这是当前参数的失败，不是该镜头对所有动作不适用。expansion_geometry_audit_v1.json记录规划验证。cam_46_expand_11的实际语义为全身到全身拉远，不能标为上半身到全身。新候选尚未覆盖完整三轴组合空间。

prepared_jobs_v1.json绑定14份独立场景/专属Sequence与计划SHA。ue_camera_library_render_v1.start(unreal, attempt_id, shot_ids)调用既有隔离MRQ执行器，启动前复核计划和Sequence回执SHA；不会替换用户全局队列。representative_v1先渲染36/44/46，remaining_v1补充其余11条；media_validation_representative_v1.json与media_validation_remaining_v1.json分别记录完整解码及300帧/30fps/1280×720/10秒结果。post_render_restore_v1.json确认恢复入场ScalpHairFit世界、渲染已停止、全局队列为0。

build_camera_library_gallery_v1.py复用旧camera_pilot_gallery_v2.html两画面对照界面，保留25条原认可样片、4条旧幅度待修改对照，5条原排除不显示；新增14条标为待用户审查。review_delivery_manifest_v1.json拥有43条入口清单，旧媒体只复制小型审查衍生文件，不改原媒体。open_camera_library_gallery_v1.py复用本地启动器并固定新Run与8877端口；入口为 http://127.0.0.1:8877/gallery/index.html。8876仍属原审查Run，不能把旧入口当成本轮交付。

本轮全套回归的有效证据为full_regression_v2.xml：使用D盘可写basetemp，1081项通过。早期默认TEMP运行因fixture权限产生390项错误、691项通过，原full_regression_v1.xml保留；未将环境错误删除或宣称第一次即全通过。旧pixel-exact失败未修复，新候选用户接受pending；以上工程交付不等同正式确定性生产Gate。

入口实际核验见browser_verification_v1.json与gallery/review_page_verified_v1.png：左右10秒循环播放、动作切换及CMD --no-browser复用本地服务通过。新入口的推荐对照并不自动写入用户选择；新样片人工接受保持pending。

technical_delivery_v1.json绑定本轮最终媒体、界面及验证证据，并明确prototype_only、technical_delivery_success=true与human_acceptance=pending。visual_contact_review_v1.json对11条实际MP4各采样20帧，visual_representative_review_v1.json对另3条已验证渲染PNG各采样20帧并补看44末帧；14条采样中未发现明确切头、缺件或空白。44手顶部余量较小仍需用户审美判断。采样不是全帧视觉认证；渲染后本轮实际来源pin再次通过。当前计划保留current，等待新增组合与改进幅度的用户审查。

本轮文档维护证据为documentation_audit_v1.json，重建SCRIPT_CATALOG.json与OUTPUT_INVENTORY.json后核验16个独立子系统和跨层契约；完整测试复用已冻结源码对应的full_regression_v2.xml，不重复运行。gallery/review_page_full_v1.png为包含完整视频区域的交付截图。

## 9 稳定跟拍镜头试验（2026-10-10）

本节拥有 `%OUTPUT_ROOT%/unreal_character_import/camera_stable_follow_20261010_v1/`，主阶段WF-60、关联WF-50/80，沿用OUT-WF60-SEQUENCE-TEMPLATE及VAL-SCENE-01，unclassified保护。本轮是实验样片，不更改第一批生产设置。需求由唯一当前计划R06–R09定义。

### 9.1 镜头配方与跟随原则

15种配方：正面/侧面/背侧全身、上半身、面部近景、俯视/仰视全身共7种稳定跟拍；全身360°与120°环绕2种；正面/侧面/正后方推进与拉远6种。各在伸展、跳舞、持续行走上验证，共45候选。前七种不再单列固定/原地转向分支，小范围动作可自然近似固定，大位移则平稳跟随。

相机基于最终10秒动作整体位移提前规划，不逐帧追随头胸上下起伏；需允许小范围画面内活动并避免突然追赶。初始朝向定义正侧背，人物转身不强迫相机持续找正面。环绕中心平稳随整体位移移动，10秒完成指定角度。推拉0–7秒全身↔上半身平滑完成，7–10秒停止改变距离但继续跟随；拉远仅反转距离曲线，不倒放人物跟随路线。

近景和上半身配舞蹈允许部分时刻脸/上身不完全入画或露出更多身体，但仍要合理跟随，不能全程丢失目标或悄悄改成全身。记录限制供用户选择，不把旧严格全身代理阈值机械用于这些候选并提前拒绝。真实衣发遮挡与构图需以渲染观察为准。

### 9.2 动作替换语义与保护边界

[ADR-0018](../../project_management/decisions/ADR-0018-ACTION-DEPENDENT-STABLE-CAMERA.md)明确同配方可对不同动作生成不同平滑轨迹。§7/§8既有同轨迹规则对外观编辑继续有效，本轮动作替换例外不改写旧实验证据。源动作/角色/衣发、旧审查地图、旧媒体及全局MRQ队列保护；仅独立Run和版本化UE资产，root独占UE修改。

### 9.3 执行状态与证据

2026-10-10已获用户直接授权；离线实现和45候选冻结完成。`expansion_plan_v1.json` SHA为`3f29eb0f2e07d735bae70e4ab43a5f519124f258ecb24d38590527a7ef39c2b3`，`stable_geometry_audit_v1.json`独立重算45×301=13545端点帧，矩阵无缺失/重复，初始朝向、120°/360°环绕、18条推拉7秒完成及最后3秒保持、来源pin检查通过。42条通过其适用严格代理取景检查，64/65/95三条保留诊断例外；推拉严格景别检查只约束端点及7–10秒保持段，不能写成45条全程严格入画。骨骼代理不等同真实衣发遮挡或人工观感。实际媒体、网页、回归及人工接受尚待本Run证据，不引用旧1081回归作为新代码通过。旧14候选人工pending及pixel-exact失败保留，不晋升生产Gate。

### 9.4 实现所有权

`ue_stable_camera_review_v1.py`（experimental）拥有本轮prepare/render/encode适配，复用既有安全helper，不改写旧脚本；UE新资产根为 `/Game/DataMake/Validation/CameraStableFollow20261010`。准备前检查唯一编辑器、dirty资产和渲染状态，仅在清洁现场执行。

`camera_stable_follow_planner_v1.py`（experimental）拥有15配方、三动作整体位移预规划和本Run `expansion_plan_v1.json`；`tests/test_camera_stable_follow_planner_v1.py`（utility）为对应针对测试。45条各301端点帧，其中300帧用于10秒媒体，第301点用于终点验证。`stable_geometry_audit_v1.json`保存独立离线复核。

网页由 `build_stable_camera_gallery_v1.py`（experimental）、`stable_camera_gallery_v1.html`（experimental）与 `open_stable_camera_gallery_v1.py`（experimental）拥有；针对测试为 `tests/test_stable_camera_gallery_v1.py`（utility）。本机服务端口8878，15镜头×3动作对照，提供循环、联播、暂停定位与独立全屏。只有验证过SHA、时长和shot身份的真实媒体开放播放；实际浏览器证据仍由交付检查补齐。

### 9.5 实际准备与代表媒体检查

`prepared_jobs_v1.json`记录45份独立场景/Sequence全部准备成功及来源保持；`full_regression_v1.xml`对应冻结源码，documentation/dataset/unreal完整回归1091通过、0失败/错误/跳过、135.247秒。Script Catalog已按当前源码重建。

`media_validation_representative_v1.json`记录首批6代表样片渲染与完整解码通过，root实际查看各20代表帧，未见阻止继续补测的问题；65伸展面部近景偏宽、露出较多上身，低头时头接近画面下缘，按用户要求作为诊断样片保留，不冒称理想近景。其余39条随后全部完成，media_validation_remaining_v1.json与代表6条报告共同覆盖45条完整解码。代表帧检查不等于人工逐帧接受。

### 9.6 全矩阵媒体与待审限制

45条实际媒体全部完成，每条10秒、30fps、300帧；`review_delivery_manifest_v1.json`列45条可播放候选，human_acceptance=pending。`visual_bend_review_v1.json`、`visual_dance_review_v1.json`、`visual_walk_review_v1.json`记录每条20帧实际观察及最终媒体绑定，不是全帧人工认证。

64/65伸展近景在深弯腰时靠近下缘，65偏宽、露出较多上身；79/80舞蹈近景和85–87局部景别会裁到抬起的手臂，80转身会看到后脑；95行走面部近景在约7.33秒存在右边缘头/头发裁切。上述问题按用户允许的诊断试验范围保留，等待其决定限制、修改或排除，不能写成全身/全部上身/脸永远完整入画。其余采样未发现整体丢失、空帧或缺件，不外推全帧无问题。

`post_render_restore_v1.json`与`post_render_source_audit_v1.json`确认渲染结束后恢复干净入场世界并复核本轮来源。审查入口为 http://127.0.0.1:8878/gallery/index.html，45候选是当前唯一用户审查主线；旧14新增样片的未人工接受状态只保留历史边界，不要求用户先返回旧页面完成审查。浏览器最终功能由browser_verification_v1.json记录，技术交付由technical_delivery_v1.json绑定15份证据；截图为gallery/review_page_verified_v1.png。

### 9.7 网页交付与最终验证边界

`browser_verification_v1.json`实际验证45可播放、15配方、三动作并排10秒1280×720、配方切换、共同播放/暂停及循环；新加载的近景视频定位到末尾均到9.933234秒，无媒体错误。原标准HTTP服务缺少Range响应导致未缓存媒体无法可靠定位，已仅在 `open_stable_camera_gallery_v1.py` 实现本机8878单段Range，不改旧启动器；新 `tests/test_stable_camera_range_server_v1.py`（utility）验证实际HTTP prefix/mid/open-end/suffix请求206、越界416和完整GET200。

回归范围分开：完整1091项在独立启动器修正前通过；修正后的定向6项由 `range_regression_v1.xml` 证明。最初沙箱loopback权限失败不能算代码通过，最终以正常权限实际HTTP通过为准；未声称最后修改后又跑全部1091项。旧pixel-exact和历史CFD40地图漂移问题未在本轮解决。

`technical_delivery_v1.json`记录technical_delivery_success=true、45视频/900实际采样帧、human_acceptance=pending。最终文档证据为 `documentation_audit_v1.json`，Catalog/Inventory按冻结源码及产物重建后执行独立子系统和跨层检查。计划保持current等待用户筛选新45镜头效果；不代签视觉接受，不启动生产。

## 10 完整角度与七动作扩充（2026-10-10）

本节拥有 `%OUTPUT_ROOT%/unreal_character_import/camera_complete_angles_20261010_v1/`，主阶段WF-60、关联WF-50/80，沿用OUT-WF60-SEQUENCE-TEMPLATE和VAL-SCENE-01；unclassified保护。本轮为实验审查，不改变第一批生产配置或确定性Gate。

### 10.1 范围与规则

21配方包括全身与上半身各正面/前侧/侧面/后侧面/背面5方向、正面面部近景1、俯视/仰视全身2、120°/360°全身环绕2、正面/侧面/背面推拉6。各覆盖向前行走、舒展舞步、调整站姿、弯腰伸展、甩头转身、边走边思考、好奇探看7动作，目标147候选。

稳定跟随规则及ADR-0018保持：整体位移平滑跟随，不追随局部细小起伏，不因人物转身追逐正面；相机配方相同但可随动作派生不同轨迹。媒体10秒，推拉0–7秒结束距离变化、7–10秒保持景别同时继续位移跟随。全身/上半身新增角度不是新增朝向追踪策略。面部只保留正面；激烈动作近景诊断仍须明确记录，不宣称始终完整入画。

### 10.2 接受与保护边界

用户整体认可前序45稳定跟拍的效果，授权角度与动作扩充；认可限所看范围，不是所有近景无裁切、全部组合适用或正式生产接受。旧媒体、旧回执、人类审查当时pending记录保持；新增反馈独立保存。旧pixel-exact失败、历史地图pin漂移未由本轮解决。

只在独立新Run与版本化UE资产执行，保护来源角色/衣发/动作/原审查地图/全局MRQ队列。root独占UE操作，离线规划、网页和文档可分工。准备前检查D盘可用空间并按实际磁盘预算分批渲染，不删除未经审查的受保护输出。

### 10.3 实施过程与冻结验证

本轮已授权并完成冻结规划，当前按批次执行媒体补测；实际完成数量以各media_validation及状态文档为准。当前计划R10–R13拥有验收，本轮代码使用自身1101项回归，不用前序1091+6代替新验证；最终文档审计待媒体与网页冻结。

147候选离线计划已冻结，`expansion_plan_v1.json` SHA为`bbf4483cfbab6ca2203688eb77e795ded93ed611cbc0a5e9d5ac53b2ba88037a`；`complete_angles_geometry_audit_v1.json`独立复核147×301=44247端点帧通过。134条通过适用严格代理检查，13条保留诊断例外；不等同147条全程严格入画或真实媒体通过。随后UE准备完成，网页为21×7，仅验证通过的媒体开放播放；当前恢复进度见§10.5和状态文档。

冻结源码的完整documentation/dataset/unreal回归由本Run `full_regression_v1.xml`记录：1101通过、0失败/错误/跳过，263.920秒（JUnit记录）。Catalog重建724项；此回归只证明代码测试，不替代实际场景/媒体验证。最终Inventory/文档审计待媒体和网页完成。

### 10.4 实现所有权

`camera_complete_angles_planner_v1.py`（experimental）拥有21配方×7动作完整矩阵与本Run冻结轨迹；`tests/test_camera_complete_angles_planner_v1.py`（utility）为其针对测试。继承稳定跟随规则，新增角度不修改人物转身时的朝向追逐策略。

`ue_complete_angles_review_v1.py`（experimental）拥有本Run准备/渲染/编码适配，使用独立UE资产根 `/Game/DataMake/Validation/CameraCompleteAngles20261010`，不改旧适配器。现场预检确认唯一预期UE5.8.1节点、干净ScalpHairFit世界、无MRQ；本轮开工磁盘约105GB可用，仅是当时快照而非后续空间保证。

`build_complete_camera_gallery_v1.py`、`complete_camera_gallery_v1.html`、`open_complete_camera_gallery_v1.py`（experimental）拥有新147网页；`tests/test_complete_camera_gallery_v1.py`（utility）拥有对应测试。新本机8879端口，七动作网格及单动作大画面筛选；复用既有stable RangeHandler但不改旧代码，未验证的媒体不开放播放。6项针对测试已通过，实际147媒体与浏览器验收仍待本Run证据。


### 10.5 关闭应用后的恢复（2026-10-11，过程检查点）

21×7计划及147份独立场景/Sequence已完成，首批42条与第二批新attempt的42条均通过完整编码验证，当前84条可播放。用户关闭UE和Codex后于2026-10-11授权继续；恢复来源1194项核验通过，第二批原失败回执（15条成功回调、1条失败）保留。余下63条按舞步、边走边思考、好奇探看分别拆为21条独立批次，舞步正在渲染；最终交付目标仍为147候选。

`prepared_jobs_v1.json`已实际success，147份准备完成；`media_validation_batch_01_v1.json`记录42条完整编码成功。`render_receipts/batch_02_v1.json`保持failed原记录，不将其中成功回调自动视为已验证视频，也不覆写失败attempt。新执行从已冻结计划继续，不重新修改相机朝向规则。

恢复首轮受限读取PermissionError已保存在 `recovery_source_audit_20261011_v1.json.initial_sandbox_read_error`，不作为源资产漂移证据；最终报告success=true，1194项来源及准备资产检查通过。`media_validation_batch_02_retry_20261011_v1.json`记录新attempt的42条完整编码成功，原failed回执保持。`recovery_render_batches_20261011_v1.json`将原未启动的最后63条拆为dance/thinking/curious各21条，便于独立完成与中断恢复；原 `render_batches_v1.json`不修改，总数147不变，执行记录由 `recovery_execution_20261011_v1.json`承载。当前最终媒体、网页、Inventory和文档审计尚待；没有新代码修改，冻结代码1101回归仍按原范围有效。


### 10.6 完整媒体与审查交付（2026-10-11）

21配方×首七动作的147条真实样片已完成，全部10秒、30fps、1280×720，五个成功批次均通过完整编码验证。五份实际采样观察报告覆盖147条并绑定最终媒体；这不是连续运动或人工逐帧接受。浏览器已实际验证147条入口、七动作联播/暂停/循环、单动作筛选、全屏及进度定位。用户尚未筛选本轮组合，计划保持唯一current。

`technical_delivery_20261011_v1.json`绑定21×7完整矩阵、五份成功渲染及媒体报告、五份实际采样视觉报告、浏览器与来源恢复证据。`review_delivery_manifest_v1.json`列147可播放候选；真实媒体均300帧，未用失败attempt的局部输出冒充完成。`visual_stand_bend_review_v1.json`、`visual_walk_turn_retry_20261011_v1.json`、`visual_dance_review_20261011_v1.json`、`visual_thinking_review_20261011_v1.json`、`visual_curious_review_20261011_v1.json`拥有逐项实际观察及媒体绑定；近景裁切、自遮挡和景别浮动作为候选限制保留，所有组合待用户判断。

`post_render_source_audit_20261011_v1.json`1194项通过；`post_render_restore_20261011_v1.json`记录恢复清洁ScalpHairFit世界、无活动渲染且全局队列0。`browser_verification_20261011_v1.json`记录实际七画面联播/暂停/循环、单动作筛选、全屏和定位到末尾，截图为 `gallery/review_page_verified_20261011_v1.jpg`。入口 http://127.0.0.1:8879/gallery/index.html；关闭服务后使用gallery中的本地CMD启动器恢复。首次受限环境网络探测失败不是本地服务实际不可用，正常权限启动入口已验证。

源码未改变，完整1101回归沿用冻结源码的 `full_regression_v1.xml`，不重复声称新跑。最终Catalog/Inventory重建及独立文档检查由 `documentation_audit_20261011_v1.json`记录；技术交付完成与人工接受pending分开，唯一当前计划保持，旧失败及生产限制不变。

### 10.7 人工接受（2026-10-11）

用户与师兄确认最终147条镜头/动作搭配全部合理并保留。新增 `cleanup_current_pipeline_20261011_v1/user_camera_acceptance_v1.json` 绑定原expansion_plan与review_delivery_manifest SHA；原pending交付回执不改写。此接受覆盖本轮21×7的实际样片，不扩展到新身份/动作或严格确定性生产。旧14补测的后续选型由最终矩阵替代，不额外取得旧样片接受。相机计划归档，当前获授权任务转为清理；面部细节另会话优化，本方案保留为对照基准。

### 10.8 清理后的复用边界（2026-10-11）

当前147相机地图/Sequence、七组准备源场景、成品视频和分享包保留。旧stable/library与非选中pilot关卡已按cleanup_current_pipeline_20261011_v1清单退休；前述历史prepare记录不表示这些旧包现在仍可加载。已编码原始PNG删除后，再编码必须先重新渲染。cam05/31/34的严格失败诊断原图及UE依赖保留，旧失败结论不改；轻量历史证据继续可追溯。当前来源与保留资产hash、UE重启引用验证由清理Run回执记录。

## 11 动作整理、竖屏与场景点位试点（2026-10-11）

本节拥有 `%OUTPUT_ROOT%/unreal_character_import/motion_portrait_scene_pilot_20261011_v1/`，主阶段WF-60，关联WF-50/80；沿用OUT-WF60-SEQUENCE-TEMPLATE、VAL-SCENE-01，输出unclassified保护。新计划为PLAN-2026-10-MOTION-PORTRAIT-SCENE-PILOT，试点真实媒体已完成交付、人工审查pending，不改变§10已接受横屏或第一批生产Gate。

### 11.1 动作窗口与相机派生

盘点全部新增动作的来源、源时长、完整水平轨迹及选用连续时间窗，以保留原地小范围活动或沿直线移动为主，允许次方向轻微浮动。优先完整保留；只有必要时截取，不能通过截取解决的大幅多方向移动从候选清单排除，原动作不删。轨迹不强制拉直；过短片段明确标注。向前行走源窗[0,6]秒，以0.6倍速得到10秒；其余动作不提前统一10秒。相机从最终选用窗口重新派生稳定跟随，仍不追逐身体朝向或局部抖动。

### 11.2 竖屏与场景试装边界

1280×720横屏与21配方保留，新增720×1280竖屏先验证行走、舞蹈、伸展。竖屏需重新求构图/距离，不能仅改输出分辨率；近景及剧烈动作允许原方案已明确的局部裁切，限制随媒体记录。

从 `D:/BaiduNetdiskDownload/场景` 的已完成压缩包选三个，导入前盘点版本、完整性、内容路径与占用，保留来源映射；只作为内部试点，不自动获得资产发布/训练权。每个候选点需覆盖保留动作最大活动范围及21配方相机运动包络；若不满足，记录障碍并优先换场景。空间检查及代表真实试拍共同支撑点位结论，不能仅凭空地截图宣布全部组合可用。

### 11.3 审查与状态

独立网页分动作审查、横竖对照、场景点位三个区域。支持可变时长，显示源窗口与处理原因，只开放编码与来源校验通过的媒体。新结果human_acceptance=pending，旧147媒体/分享包保持。网页及媒体契约在实施冻结后补充；开工状态由PROJECT_STATE及WF-60拥有。


### 11.4 试点网页实现

`build_motion_portrait_scene_gallery_v1.py`、`motion_portrait_scene_gallery_v1.html`、`open_motion_portrait_scene_gallery_v1.py`为experimental实现；针对性测试 `tests/test_motion_portrait_scene_gallery_v1.py` 为utility。新服务仅绑定本机8880，复用已验证的RangeHandler，支持完整视频拖动定位；不更改8879旧147审查。

输入为本Run `review_gallery_input_v1.json`，schema=`motion_portrait_scene_review_v1`，含motions/scenes/clips。motions保存id、label、decision、reason、源时长/选用窗口/输出时长及可选variant/sex；scenes保存id、label、anchor_note和limitations；clips保存id、section、motion_id、camera_id/label、可选scene_id、orientation、video及SHA、可选poster、width/height、duration_seconds/fps/decoded_frames、verification_status。上游仅在真实完整解码成功后标记encoded_verified，builder进一步核对路径边界、SHA、分辨率和时间一致性；无验证的片段不开放媒体路径。输出gallery/index.html、本地CMD和review_delivery_manifest_v1.json，不把媒体可播视作用户接受。

网页提供动作/镜头/场景切换、横竖联播、暂停/继续/循环、按比例定位及本机备注导出。备注不是正式接受回执，用户反馈仍需绑定媒体后独立记录。实际浏览器验收须待真实媒体交付，不以空页或单元测试代替。


### 11.5 本轮实施脚本所有权

`motion_location_pilot_analysis_v1.py`拥有离线动作轨迹审查，`motion_portrait_camera_planner_v1.py`拥有可变窗口与宽高比相机规划，`ue_motion_scene_sequence_v1.py`和`ue_motion_scene_render_v1.py`拥有可变时长Sequence/渲染适配，`ue_motion_portrait_scene_pilot_v1.py`拥有隔离准备/渲染/编码。这些实现登记为experimental，文件存在或测试通过不代表实际媒体完成；各阶段真实执行证据在Run冻结后补充。`tests/test_motion_location_pilot_analysis_v1.py`及对应本轮planner/sequence测试为utility。Catalog使用本节精确归属，不能因文件名含motion自动归类为CC动作传输或已验证生产能力。


`ue_motion_body_window_v1.py`（experimental）拥有隔离连续动作窗口及明确重定时，只在 `/Game/DataMake/Validation/MotionPortraitScenePilot20261011/BodyWindows` 创建派生动作；`tests/test_motion_body_window_v1.py`为utility。`all_motion_samples_v1.json`记录50份源动画10Hz全长采样、源SHA和dirty保护；`motion_window_decisions_v1.json`为root/pelvis PCA初步窗口建议，尚非冻结清单或自然度接受，尤其沿直线往返候选仍需决定单程窗口。新增20组与旧10独立动作分别报告，不能将男女性别变体重复计算为独立动作。13项分析/helper单元检查由 `motion_analysis_unit_tests_v1.xml`记录，实际UE派生和视觉证据另补。


### 11.6 动作窗口v2与代表相机试点边界

`motion_window_decisions_v2.json`绑定v1与变更说明：新增20组初步17整段、walk前6秒→10秒、035思考5.9–27.2秒原速21.3秒、036模特步行0–7秒原速避免后半明显折返；旧10独立表现初步9整段及M04 0–11.8秒。没有动作被直接删除，这些仍是几何建议，不等同自然度接受。新增男女40份加旧10份共50源采样，与30独立表现区分。

30条动作overview保留选定窗口的实际时长；行走/舞蹈/伸展×21配方×横竖的126条代表相机试点每条最多10秒，仅减少构图比较成本，不将完整动作库统一裁成10秒。两类合计156计划候选，实际完成数由媒体回执决定；场景试拍另列。其余动作全部21视角待动作审查选择后展开。

`tests/test_motion_portrait_camera_planner_v1.py`、`tests/test_motion_scene_sequence_v1.py`、`tests/test_motion_scene_render_v1.py`（utility）共12项通过，由 `pilot_camera_regression_v1.xml`记录：源时钟、不同选用时长、portrait fit、跟随抑制、试点/overview分流、可变endpoint及混合105/639帧MRQ配置。UE API stand-in测试不等同实际MRQ；真实准备/渲染另补。独立face动画section调用必须显式传本shot帧数，不能沿用helper默认300。


### 11.7 可变时长编码与中断恢复

`encode_motion_scene_pilot_v1.py`（experimental）读取本Run完成的 `render_receipts/<attempt>.json`及默认`camera_trial_plan_v1.json`，也可重复传`--plan`加入场景计划。执行 `python 00_engine/scripts/unreal/encode_motion_scene_pilot_v1.py <attempt>`。只接受terminal success，逐shot核对30fps、实际帧数、横/竖尺寸及冻结计划；按文件名逐帧核查PNG完整性/尺寸/SHA。

沿用已安装FFmpeg路径，先编码MP4再以FFmpeg -xerror完整解码并核对总帧数，另由OpenCV逐帧确认尺寸、帧数与FPS；不依赖未安装ffprobe。输出 `videos/<shot>.mp4`、同名poster、`contacts/<shot>_timeline.jpg`（20个均匀时点、竖屏不拉伸）、逐shot `media_receipts`和`media_validation_<attempt>.json`。20帧联系表仅是待观察材料，不自动表示视觉通过。

resume必须匹配源PNG、冻结shot、渲染回执和视频SHA，再重新完整解码；未知MP4、来源漂移、失败attempt和已有不同的最终报告均拒绝覆盖。多个attempt不能用同shot ID覆盖既有媒体；重新渲染需新的受控ID或明确恢复处理。本脚本不删除raw。`tests/test_encode_motion_scene_pilot_v1.py`（utility）以真实FFmpeg验证不同长度/方向及恢复保护；结果由encoder_unit_tests回执记录。首条真实walk竖屏验证见 `media_validation_portrait_walk_smoke_v1.json`，其余媒体完成情况以逐attempt回执为准。


### 11.8 渐进网页与场景/数值验证实施

`assemble_motion_scene_review_v1.py`（experimental）从动作decisions v2、冻结shot plans和已成功的media_validation报告生成 `review_gallery_input_v1.json` 并调用builder。逐片验证回执SHA、shot内容SHA和视频绑定后才开放媒体；未完成项显示生成中。可重复`--plan`追加场景计划，场景说明可由计划的scenes数组或`--scenes`输入。首次156计划只完成1片时网页明确展示1/156，不能把计划数量称为交付数量。入口为 http://127.0.0.1:8880/gallery/index.html，本地启动器已验证HTTP及Range；实际浏览器操作待可用浏览器接入，不用HTTP代替浏览器验收。

`ue_scene_location_pilot_v1.py`与`ue_motion_body_window_numeric_validation_v1.py`均为experimental、归本节所有。前者负责隔离场景点位试装，后者对派生动作做只读物理量验证。male walk旧统一1e-4检查失败回执保留；新具名sequencer_physical_v2检查以UE5.8源码常量归并/近等变换行为为依据，118骨全部纳入，平移向量≤0.00035cm、角度≤0.025°、缩放≤1e-5，root与曲线保留旧1e-4。启用必须显式指定validation_policy，默认旧gate不变；新阈值由具名报告绑定引擎源码和推导，不能倒写旧failed或当作视觉自然度证据。实际新gate结果由root运行回执提供。


### 11.9 共享骨骼旧动作复用与场景空间筛选（执行检查点）

`ue_legacy_shared_motion_reuse_v1.py`、`ue_scene_character_pilot_v1.py`、`motion_scene_space_screening_v1.py`登记experimental，归本节所有。旧10动作使用已有CFD40 ModularReview/Animations下男女A_CCWH_*_v002完整共享骨骼版本，非5秒inplace替代。`legacy_shared_motion_reuse_v2.json`当前UE只读验证success：118骨层级/reference、18个相机骨点全长10Hz检查，源/目标及既有全帧local pose证据的SHA一致，10个映射可用，源与dirty保持。v1的FrameRate对象比较失败保留，v2改用数值分量比较，不能将其称为原动画修复。root仅在成功proof存在时消费映射，冻结camera plan不改。新场景自然度仍待实际媒体。

`motion_audit_delivery_v1.json`确认male walk具名物理gate已真实UE通过并独立核对：601帧×118骨，平移向量最大约0.000132cm、旋转0.010774°、缩放8.94e-7，root约1.74e-7；报告/资产/引擎源码pin一致。旧walk_male_v1.json继续legacyfailed。156shot时钟与轨迹SHA检查通过，其中70份准备回执是该审计时的快照，不代表最终准备或渲染数量。

`scene_camera_space_screening_v1.json`覆盖30动作×21配方×横竖共1260条稀疏空间路径（0.5秒采样用于fit/包络，稳定中心仍用30fps），只做点位初筛，绝非1260段实拍或全部遮挡验证。停车场候选仅1114/1260路径清晰，顶棚约Z300及柱体会限制高机位/环绕，因此不作为通用点位交付。CHERRY_TREE和Evening_Highway另作为替代候选复制进项目，分别由import_copy_cherry_receipt_v1.json和import_copy_highway_receipt_v1.json记录无覆盖复制；这些回执ue_loaded=false，仅证明文件复制，不能宣布场景加载/点位/视觉已通过。最终交付目标仍是三个合适场景，不是自动保留所有试装候选。

`scene_transform_independent_audit_v1.json`独立检查15场景试拍镜头×4个yaw，逐帧刚体变换保持投影与视线（最大投影差约2.33e-15）。该离线结果不替代UE复制角色的衣发引用、follower绑定、旋转后地面footprint以及保存重载/真实遮挡检查。`ue_scene_character_pilot_v1.py`拥有这些隔离角色与场景试拍准备，完成情况由后续真实回执证明。


### 11.10 全部准备与首批动作渲染（过程检查点）

156/156动作/横竖候选准备成功；`sequence_playback_readback_v1.json`记录936条动画轨道当前UE读回通过。`motion_overviews_and_japanese_smoke_v1`提交30条完整时长动作overview与日式村庄行走横屏smoke，共31任务。日式村庄候选锚点[7000,-5500,66.2]cm、yaw0；场景计划`scene_trial_plan_japanese_village_v1.json`及网页说明`scene_review_metadata_v1.json`独立记录，人工接受pending。这里仅记录提交与准备，不提前宣称渲染/编码完成，最终以对应media_validation回执为准。


日式村庄v1的真实smoke在frame150/299被root观察到巨大高草遮挡躯干与腿部、面部逆光偏暗，当前锚点不能作为合格结果。该批仍可完成编码用于诊断，其余30条动作照常执行；网页meta明确needs_rework，最终合格画廊由新的scene revision取代v1，不能把旧失败候选混成通过。几何clearance即使通过，也不能替代实际植物遮挡与曝光审查。


`motion_audit_delivery_v2.json`补齐当前保存状态的独立核验：473个依赖SHA一致，156份序列/关卡与936条实际动画轨道读回匹配冻结plan；section rate及Animation RateScale均1，裁切偏移正确。旧10共享骨骼副本的层级/reference及18骨点全长10Hz检查通过，最大world差约0.0043707cm。该报告解决v1审计中RateScale及male物理结果消费者尚待检查的缺口，但不扩展为所有媒体或自然度接受；v1原记录保留。

### 11.11 动作概览媒体阶段检查点

`media_validation_motion_overviews_and_japanese_smoke_v1.json` 记录31条媒体完整解码、帧数、30fps、分辨率与SHA通过。`motion_overview_visual_samples_v1.json` 绑定30动作各20帧实际联系表观察，未见明显出框或骨骼崩坏；仅抽帧，不代表连续自然度或用户接受。日式村庄v1虽然编码通过，但高草遮挡与逆光导致视觉不合格，网页明确 `needs_rework`，后续新revision替代。当时32/171可播放只是阶段快照，不能称为三场景或全部相机完成。

`review_clip_notes_v1.json` 是独立的人工审查提示来源，按shot ID追加简洁备注，assembler把来源SHA写入网页输入；不改变冻结plan、媒体验证状态或用户接受。当前伸展横屏面部近景约2.6–3.7秒弯腰导致头部落到画面下缘，按用户允许的试验搭配保留并提示重点查看。

后续 `media_validation_landscape_camera_trials_v1.json` 记录63条横屏相机对照完整解码通过，网页阶段快照增至95/171。`raw_visual_spotcheck_landscape_v2.json` 是21条重点镜头各20帧观察，并非全部63条连续人工观看；8项近景取舍提示已进入独立备注配置。

### 11.12 场景副本清理与点位候选（过程记录）

公路候选 `[0,6000,0]` 的 `scene_body_space_highway_v1.json` 覆盖50个源男女动作版本，地面探测、骨段/时间扫掠均通过。只在 `SceneBases/L_highway_clear_v1` 副本移除4处阻挡相机的小道具（3道路围挡、1交通标志）；`highway_local_obstacle_clearance_v2.json` 锁定原场景SHA不变。清理后的 `scene_clearance_highway_cleared_v2.json` 记录1260/1260稀疏镜头路径通过、27258采样、0阻挡。它仍是碰撞通道与稀疏路径初筛，不保证无碰撞几何、完整衣发体积、相机近裁面或所有实际画面。

日式村庄候选 `[7000,-5500,66.2]` 的50个源男女动作版本通过同类身体空间初筛。旧v1因高草遮挡和面部逆光失败，保持独立。TypedElement Python句柄不可用后，采用受控局部重建，仅在 `SceneBases/L_japanese_village_clear_v2` 副本移除500个草/灌木实例（`japanese_foliage_rebuild_plan_v1.json.total_remove`）；`japanese_foliage_rebuild_saved_reload_v1.json` 明确 `explicit_save_reload=true`，验证保存重载后保留实例的位姿集合、可读材质/碰撞设置、非目标植被及非植被网格不变，原场景/网格/植被类型资产指纹不变。

该回退是拍摄试验副本，不升级为正式植被编辑方法：BaseId、BaseComponent、ZOffset、ProceduralGuid及编辑附着元数据不保留；实例索引和PerInstanceRandom/烘焙逐实例光照可能变化，不能声称逐实例随机值一致；不可读AdditionalRandomSeeds范围保持状态未知。目标保留实例位姿按明确浮点容差比较，非目标已记录字段要求严格不变。真实重拍仍必需，尤其检查植被外观变化、遮挡和逆光。

RUN内 `ue_local_foliage_clearance_helper_v1.py`、`ue_scene_body_space_check_v1.py` 为本节拥有的隔离实验辅助，不是production接口。樱花场景已载入并能正常做环境试拍，但初次网格搜索未得到平整通用点位；停车场顶棚过低，两者暂为备选。加油站点位仍细化，最终第三场景未确认。`scene_review_metadata_draft_v2.json` 仅准备新版本页面说明，没有接入当前gallery，也不修改冻结scene plan或实际媒体验证状态。

### 11.13 最终页面选择准备（已被后续版本替代）

`final_gallery_selection_preflight_v1.json` 锁定主计划及Japanese v3、Highway v2、Gas v1三份计划的SHA，合计201个唯一shot（30动作概览、126横竖对照、45场景试拍）。各场景15条：三个代表动作各4横屏（正面全身、俯视、360环绕、侧面推进）与1正面全身竖屏。`scene_review_metadata_selected_v1.json` 提供三个点位的页面说明，`final_review_readme_draft_v1.txt` 提供使用顺序、播放与备注方法。

此时只准备选择与说明，须待root视觉确认再编码修复后的smoke。assembler最终只消费这四份计划；旧日式v1/v2及公路v1不进入主页面，但原计划、失败回执和诊断媒体不删除。计划规模、几何通过和文件存在都不自动变为可播放或视觉接受。

### 11.14 修复smoke的状态复核与版本调整（过程记录）

`scene_fixed_smoke_v1_incident_reconciliation_v1.json` 是旁路核对，不修改原渲染回执。root最初报告UE不在、两个callback与Gas零帧；本次实际读取时回执已是 `completed/success=true`、三个callback成功，各目录300个连续PNG，备份日志14:15:09明确整队3个job完成。因此不把较早局部观察写成最终中断事实。日志在3D/Compute队列记录约5秒GPU timeout及Translucency/CopySceneColor、Slate上传breadcrumb；它们是警告与当时执行位置证据，不能单凭breadcrumb猜测崩溃根因。PNG计数不等于完整解码和视觉接受。

旧Japanese v3首帧仍有问题、Highway v2补光过曝，均未因此发布。当前预期改为Japanese v4（preroll试验）、Highway v3（减弱fill）、Gas v1。`final_gallery_selection_pending_v2.json` 与 `scene_review_metadata_selected_v2.json` 明确等待未来版本与root视觉确认；旧selection preflight标为发布前已替代，原计划/回执/媒体不变。新计划全部就绪后需重新核对SHA、201数量和源媒体，再接入页面；未确认之前不编码此次smoke。

### 11.15 相机真实预热与最终基底空间复测

`ue_scene_camera_preroll_v1.py` 为本节拥有的experimental辅助，输入严格限于明确列出的新Japanese v4/v5 SceneTrials；只复制Sequence到全新 `_preroll16_v1` 目标，禁止覆盖并保护输入map/sequence文件SHA。它在相机Transform/FOV的10条channel新增第-16帧常量key，并将camera cut起点扩展至-16；原0..300的301个相机key逐字段一致。正式playback/output保持0..300（30fps、300帧），6条身体/面部section的范围、动画引用、速率、偏移和开关不变。

`ue_motion_scene_render_v1.start_render(..., camera_cut_warmup_shot_ids=[...])` 是逐shot显式启用接口，默认空集合不改变其他镜头。ID必须唯一且属于当前队列，序列必须位于SceneTrials，并有一个至少覆盖前16帧的camera cut；启用ID写入render_contract。仅设置普通engine/render warmup计数不能替代这一真实camera-cut预热。`scene_camera_preroll_implementation_review_v1.json` 与19项定向测试说明代码边界；root已观察v4首帧正确，重复实拍仍待完成，不能提前写成全部场景修复接受。

`scene_clearance_{japanese_village,highway,gas_station}_final_base_v1.json` 与同名 `scene_body_space_*_final_base_v1.json` 已全部出现。三个最终基底分别为Japanese clear_v2、Highway lit_v3、Gas clear_v1，均有50/50源动作版本身体空间初筛与1260/1260稀疏镜头路径通过。当前空间证据指向这些final_base报告，先前源场景/旧副本结果保留为历史。`scene_final_base_documentation_crosscheck_v1.json` 进一步核对每对报告world路径一致且匹配当前scene plan；当前已保存基底SHA与plan源pin一致。原空间报告未内嵌探测时刻基底文件SHA，这一核对不反向证明当时字节相同；严格版本证明仍需执行方的状态/保存记录。空间初筛不覆盖无碰撞几何、完整衣发、逐帧遮挡及最终视觉接受。


### 11.16 当前发布选择与竖屏视觉证据

当前发布选择由 `final_gallery_selection_preflight_v3.json` 锁定：主 `camera_trial_plan_v1.json`、Japanese v4、Highway v3、Gas v1 四份计划；场景说明为 `scene_review_metadata_selected_v3.json`。最终清单仅包含这四份计划的shot，旧失败版本的媒体与原始回执留作诊断，不进入主页面。第11.12–11.14节的候选和待选状态保留为过程记录，不能当作当前发布状态。

`scene_final_smoke_visual_index_v1.json` 记录三场景walk/front_full各20帧视觉抽样。Japanese v4在两次独立渲染的首帧均正确，Highway v3较弱补光消除过曝，Gas v1代表片正常；范围仅这三个代表片，不推广到全部场景组合。`media_validation_scene_fixed_smoke_v1.json` 技术编码通过不代表其Japanese v3/Highway v2视觉通过；Gas可用，另外两条仍为失败诊断。Japanese v4与Highway v3最终媒体取自 `media_validation_scene_final_probe_v1.json`，同ID早期preroll媒体不重复发布。

`portrait_visual_audit_delivery_v1.json` 及 `portrait_visual_observations_v1.json` 记录63条竖屏各20均匀采样帧和首三帧核对，1386个去重raw指纹复核，未发现阻断缺陷；不是所有帧的连续人工验收。伸展面部近景、各上半身景别及舞蹈近景的局部裁切/朝向变化，以及行走个别侧面构图靠边，写入 `review_clip_notes_v1.json` 供用户判断，不自动剔除组合或改变跟随轨迹。

`media_validation_portrait_camera_trials_v1.json` 完成其余62条主竖屏的帧数、尺寸、30fps、全帧解码及SHA验证，与首条walk竖屏共同覆盖63条。发布进度以 `review_gallery_input_v1.json`、`review_delivery_manifest_v1.json` 和Status为准。页面只允许已验证媒体播放；全部条目完成时明确显示“全部样片已完成媒体验证，等待人工审查”，不会把技术成功标作用户接受。

RUN内 `audit_final_media_delivery_v1.py` 为本节拥有的离线独立验收辅助，四份冻结plan、网页输入、媒体验证回执与render job交叉核对，并检查video SHA、首/中/末raw抽样及源资产pin；最终运行结果仍待发布冻结后的实际报告。该脚本不操作UE、不修改页面或媒体。最新完整回归见 `regression_docs_final_summary_v1.json`，所有1143项通过；图形浏览器目前不可用，网页只完成HTTP/Range/JS技术检查，实际交互验证边界明确保留。


### 11.17 日式环绕后续遮挡与v5修复中

后续真实渲染发现Japanese v4的伸展/360环绕被前景石头遮挡脚部。`final_scenes_landscape_v1` 已取消并以failed回执保留，编码watcher终态退出，未编码或发布该批。前述walk/front_full抽样通过仍是该镜头的历史事实，不能推广为整个日式场景合格。`final_gallery_selection_pending_v4.json` 登记v5重拍待完成；主156、公路v3和加油站v1计划不变，日式v5将替换v4的15条目标，不增加盲目组合。

当前阶段页面使用 `scene_review_metadata_selected_v4.json`，明确日式needs_rework并保留原已发布walk代表片作临时参考；新的201发布选择尚未最终冻结。第11.16节中的preflight_v3仅是发现此遮挡前的选择记录，不能作为最终交付版本。面部亮度细节本次不调整，原失败回执和媒体仍保留。


Japanese v5修复期间，root授权preroll辅助做窄范围版本扩展：只允许明确v4/v5，并要求map、sequence、shot前缀同版本精确对应，不接受任意未来版本。`scene_camera_preroll_v5_offline_review_v1.json` 与 `scene_camera_preroll_v5_tests_v1.xml` 记录19项相关检查通过；此前完整1143回归属于增量修改前，保留原冻结证据不改写。当前最终媒体审计将固定使用 `final_gallery_selection_preflight_v4.json` 与JPv5计划，文件准备完成前不执行最终判定。


Japanese v5的当前修复证据为 `japanese_rock_saved_reload_v1.json`：只在新 `SceneBases/L_japanese_village_clear_v3` 副本实际移除14个明确候选岩石实例，`after_save_reload=true`；保留目标实例位姿集合、非目标可读字段和原source资产pin核对通过，clear_v2历史副本保留。重建仍继承前述编辑附着元数据及逐实例随机值限制，不升级为生产编辑方法。

本次暴露了碰撞检查的具体盲区：`japanese_landmark_visibility_v1.json` 共30645条Visibility射线报告0阻挡，但NO_COLLISION岩石仍能遮挡真实画面。`japanese_rock_bounds_candidates_v1.json` 通过368个附近岩石实例的AABB与6735条视线寻找候选，属于包围盒初筛而非网格精确遮挡判定；明确14实例列表来自 `japanese_rock_explicit_plan_v1.json`，不能把所有AABB命中视作应删除资产。

RUN内 `ue_scene_landmark_visibility_v1.py`、`ue_scene_rock_bounds_candidates_v1.py`、`ue_rock_foliage_explicit_plan_v1.py`、`ue_japanese_rock_fix_smoke_v1.py` 均属本节实验输出辅助，不列为production。`japanese_rock_fix_smoke_v1` 将复测伸展的360环绕和侧面推进；视觉QA通过前不编码发布。实际去除实例与保存重载成功不代替新的真实画面检查。


### 11.18 Japanese v5代表画面通过与当前发布版本

`final_scene_visual_observations_v2.json` 记录v5伸展360环绕与侧面推进的离散QA通过，root另看环绕frame142确认脚部不再被该岩石遮挡。`media_validation_japanese_rock_fix_smoke_v1.json` 对应两条媒体验证通过，只有这两条代表画面被确认，不扩展到全部场景镜头。

当前选择改为 `final_gallery_selection_preflight_v4.json`：主v1、Japanese v5、Highway v3、Gas v1，201个唯一ID。页面场景配置使用 `scene_review_metadata_selected_v5.json`；JPv4旧smoke移出主页面，诊断保留。其余场景渲染拆为每场景横屏/竖屏独立批次，某场景失败不会取消其他场景已完成结果。

日式新基底clear_v3的 `scene_clearance_japanese_village_final_base_v2.json` 与 `scene_body_space_japanese_village_final_base_v2.json` 实际复测1260/1260稀疏路径、50/50身体版本通过。`japanese_final_geometry_base_pins_v1.json` 记录只读检测前后相同地图SHA，补齐该新基底版本证明；旧final_base_v1仍对应clear_v2，只作历史。碰撞与稀疏采样的可见性边界继续保留。


`regression_docs_final_summary_v2.json` 已对包含v4/v5显式guard增量的当前冻结S代码完整复跑documentation/dataset/unreal：1143项通过，0失败、0错误、0跳过，431.687秒。v1回归与原日志保持历史，不改写为新版本结果。


### 11.19 最终技术交付（2026-10-12）

当前入口为RUN `final_delivery_summary_v1.md`。最终发布使用主v1、Japanese v5、Highway v3、Gas v1四份计划的201条媒体；`final_gallery_selection_preflight_v4.json` 保留计划pin，`final_gallery_publish_freeze_v1.json` 锁定最终输入、manifest、HTML、31项备注及更新后的 `scene_review_metadata_selected_v6.json`。v5 metadata是选择阶段历史，最终页面以v6嵌入内容为准，不改旧计划或失败回执。所有媒体全帧解码通过，用户接受pending。

`final_scene_visual_delivery_v2.json` 对45条当前场景样片做独立范围核对：43新条各22独立帧（20均匀+首0/1/2），2条原smoke复用已核验视觉报告；当前三个版本各15条与计划精确对应。`gallery_http_smoke_v4.json` 验证201全可播放标记、三个分区各一MP4 Range206及字节一致、HTTP页面字节等于保存HTML和JS语法；没有可用图形浏览器，实际交互核验未完成，不把HTTP测试说成浏览器视觉测试。

旧 `motion_audit_summary_v1.md`、`scene_point_geometry_delivery_v3.md`、本节中间检查点以及较早selection/metadata均为阶段快照，可能保留“仍在推进”的当时状态。当前总结果以最终交付摘要、发布freeze、最终视觉报告及最终媒体独立审计为准；旧文件被引用的SHA不改写。正式生产Gate和原pixel-exact失败不因本轮技术交付改变。


`independent_final_media_delivery_audit_v1.json` 已通过：201条选定媒体与四计划精确对应，804张代表原帧与563份源资产/依赖重新计算SHA，并复核各完整解码回执、渲染、准备与发布freeze。它不重复全帧解码或所有PNG哈希，不声称视觉/用户接受。


最终文档收尾以 `documentation_final_delivery_v1.json` 为证据；关闭检查前 `documentation_final_delivery_preclose_v1.json` 已确认16子系统及cross-layer通过。当前Catalog747脚本、Output Inventory186范围；源代码完整回归仍为 `regression_docs_final_summary_v2.json` 的1143通过，不重复无改动测试。计划R01/R02/R03/R05技术实现完成，R04保留无可用图形浏览器的实际交互检查缺口及人工审查pending。

### 11.20 用户审查接受与清理承接（2026-10-12）

用户已检查网页全部展示动作、横竖构图和三个场景，认为合理正常。新反馈保存于 `%OUTPUT_ROOT%/workspace_cleanup_20261012_v1/user_pilot_acceptance_v1.json`，绑定最终清单；11.19及原回执的pending是交付时快照，不覆盖新反馈。自动浏览器交互测试未执行，不声称通过；用户实际网页审查足以完成本轮交付接受。早期男女分库动作跨性别可用性仍待实际验证，原共享骨骼复用结果并未证明跨性别。全动作×全场景实拍和严格生产确定性不在接受范围。旧过时结果的后续删除/迁移由工作区清理回执明确，不再无条件承诺所有历史物理产物永远保留。

### 2026-10-12 旧一次性脚本退役

旧第一批动作/粗糙表情的单次执行和审查脚本已清理，精确列表见 `%OUTPUT_ROOT%/workspace_cleanup_20261012_v1/batch06_retired_scripts.json`。本页相关早期步骤仅为历史，不再作为当前命令；当前角色使用CFD40模块化入口及四类原速表情。旧字节证据不改写为新验收，现用脚本和配置按当前Registry读取。


## 12. 统一相机构图、旧动作跨性别与场景导入（2026-10-12）

当前计划为[PLAN-2026-10-CAMERA-MOTION-SCENE-ALIGNMENT](../../project_management/plans/active/PLAN-2026-10-CAMERA-MOTION-SCENE-ALIGNMENT.md)。本节拥有Run `%OUTPUT_ROOT%/camera_motion_scene_alignment_20261012_v1/`、本轮相机分析/校对、旧动作跨性别审查副本和场景导入证据；沿用`OUT-WF60-SEQUENCE-TEMPLATE`与`VAL-SCENE-01`。任务临时文件只放`00_engine/temp/camera_motion_scene_alignment_20261012_v1/`。新增结果不改旧201/147接受媒体的冻结证据，也不晋升生产Gate。

### 12.1 跨性别动作执行入口

[`ue_legacy_cross_sex_validation_v1.py`](../../../../../../00_engine/scripts/unreal/ue_legacy_cross_sex_validation_v1.py)由root在正确UE工程内调用`run()`；模块导入不会启动UE。输入为`00_engine/assets/character_creator/current_review_actions_20261012_v1.json`的10个BodyOnly动作及当前CFD40男女共享骨骼/代表网格。脚本检查实际118骨层级，逐帧重建108身体轨道到另一性别，保留原时长和帧率；不修改原动作、共享Skeleton或兼容骨骼配置，不切关卡、不改角色。数值误差沿用既有视觉副本上界，并对目标网格做18骨10Hz采样；源文件SHA及dirty状态检查保护现用资产。参考姿势差异明确记录，数值相等不等于服装/体型视觉正确。

新资产限定`/Game/DataMake/Validation/CameraMotionSceneAlignment20261012/LegacyCrossSex/`；单项回执与`legacy_motion/validation_v1.json`保存成功范围，失败独立报告不覆盖旧记录。未有成功回执的已有目标禁止直接覆盖。脚本准备不等于实际UE执行，网页视觉审查完成前不将主动作库`cross_sex_verified`改为true。部分旧动作不足7秒，本轮保留原长作兼容审查，不擅自慢放至10秒。

### 12.2 相机与场景边界

先比较冻结的竖屏舒展舞步/弯腰伸展的初始相对位置、FOV、取景中心及全动作范围约束，再形成统一尺度标准。全身构图不能为人物大小一致而静默裁掉必要部位；近景沿用已有允许局部裁切边界，不自动剔除动作镜头组合。稳定平移跟随与不跟随人物转身的语义继续保持。

场景完整包先盘点，保留原始包引用路径并按源包建映射；已存在资产以哈希比对去重，不覆盖冲突。只导入与UE加载检查，不选择表演点位或渲染场景矩阵；未完成下载、损坏、缺依赖和版本不兼容明确记录。所有UE状态修改由root统一串行，离线盘点/代码/文档可并行。精确资产、组合和通过数量由新Run实际回执拥有。

### 12.3 本轮独立准备与审查网页

`00_engine/scripts/unreal/ue_camera_alignment_review_v1.py`拥有本轮隔离关卡/Sequence准备与渲染调度；`assemble_camera_alignment_review_v1.py`组装计划和实际媒体验证回执。离线编码沿用`encode_motion_scene_pilot_v1.py`的完整解码及单片回执契约，但Run和计划须明确传入本轮目录，不覆盖旧结果。

`build_camera_alignment_gallery_v1.py`、`camera_alignment_gallery_v1.html`、`open_camera_alignment_gallery_v1.py`拥有新审查网页与8881独立服务。输入`review_gallery_input_v1.json`的schema为`camera_motion_scene_alignment_review_v1`，包含motions、cameras、clips、scenes。待生成组合保留可见格子，但删除可播放路径；只有媒体SHA和`motion_scene_encoded_shot_v1`回执的ID、尺寸、帧数、FPS及完整解码状态一致才可播放。输出为`gallery/index.html`与`review_delivery_manifest_v1.json`，人审状态保持pending。原8880和皮肤8893页面不改。

网页提供横竖对照、动作/镜头/构图例外筛选、全组合进度、旧动作相反性别对照、场景导入清单和可导出的浏览器本机备注。跨性别通过`reference_clip_id`绑定同动作原性别样片，禁止把男女同编号的不同表演混作同一动作。场景`copied_pending_ue`只表示文件复制，`imported_verified`才表示UE加载检查通过；本轮场景无拍摄点位或新视频。测试入口为`00_engine/scripts/unreal/tests/test_camera_alignment_gallery_v1.py`，验证路径、回执、配对和嵌入数据安全，不替代实际浏览器操作。详细字段由Run内`legacy_motion/gallery_input_schema_v1.md`列出。

### 12.4 统一尺度策略与v2近景校正

`camera_scale_cause_audit_v1.json/.md`已定位旧竖屏正面全身差异：相同35°水平FOV下，弯腰伸展距离217.31cm，舒展舞步382.38cm；舞步主要受横向手臂/移动范围限制。骨骼代理首帧高度占比分别约73.6%与42.0%，不是实际像素轮廓。序列回执轨迹SHA与旧计划一致，因此问题来自按动作单独安排距离，而不是计划意外未应用。

用户选择多数动作相近尺度、大幅度明确例外。当前`camera_calibration_planner_v1.py`及Run内`build_calibration_plan_v1.py`、`build_calibration_plan_v2.py`、`audit_common_camera_distance_v1.py`、`audit_common_camera_distance_full_v1.py`由本节拥有，后四者为输出范围实验辅助。主矩阵覆盖30独立表现×21镜头×2画幅；另一性别10个旧动作另作正面全身对照，不再重复完整矩阵。沿用已确认完整动作窗口和速度，不把全部素材重新裁成10秒，也不撤销行走已确认慢放。

v1计划尚未UE准备/渲染时发现上半身/面部近景距离由整段活动范围推得过远，因此保留其文件作未实施历史。v2以初始部位代理占画面高度定标，上半身目标中位数0.75、头部0.60；这些是离线候选参数，不是用户已接受视觉效果。全身保留幅度保护和明确例外，近景不因剧烈动作自动退化成全身。主准备读取`camera_trial_plan_v2.json`；新ID带`_v2`避免与旧计划混淆，`camera_plan_v1_superseded_by_v2.json`生成后绑定两版本SHA。确切产物是否已完成由Run和Status读取，不因本文命名即认为已冻结。

Run内`run_camera_batches.py`、`retire_verified_raw.ps1`、`launch_review_editor.py`、`ue_session_preflight.py`为本节拥有的root执行辅助，非独立生产入口。批次按横竖和小组串行，恢复需重查现存媒体/回执而非只见成功文件即跳过；每批发布后可退休可重建PNG，但保留MP4、封面、时间轴、媒体/渲染回执并核对SHA。原帧删除使用限定本Run的PowerShell原生路径、重解析点拒绝和前后回执，旧已接受媒体不受影响；再次取得原帧须重渲染。代表smoke原帧暂保留供视觉检查。UE启动须确认没有其他编辑器进程，场景离线复制结束后由root串行启动；另会话皮肤修改不属于本轮。


`camera_calibration_final_freeze_v2.json`已绑定最终v2计划与10条代表smoke，近景除初始尺度外加入最小深度保护，避免身体越过/过于接近相机；例外明确显示，不以裁切许可掩盖近裁剪问题。离线几何冻结与`camera_calibration_final_tests_v2.xml`属于准备验证，不等于实际画面通过。`regression_in_progress_summary_v1.json`记录全套1179唯一用例经27项精确环境复测后通过；初次沙箱运行1152通过/27临时文件与localhost权限失败，复测未放宽检查。期间仅assembler发生源码变化，另有两例实际发布器检查。此证据不是单次最终冻结全绿，也不包括UE运行或浏览器视觉交互。

网页显示层默认从正面全身开始，镜头顺序固定为五角度全身、五角度上半身、面部近景、俯仰全身、环绕、正侧背推近及拉远；不依赖计划文件的生成顺序。旧动作中文显示名称读取`00_engine/scripts/dataset/prompt_catalog_first_batch_v1.json`的`labels.action.<id>.zh-CN`，后缀标明原男/女动作以区分同名不同表演；只借用既有中文标签，不复用其历史生产配置。ID、源动作及相机计划均不修改。`gallery_readability_update_v1.json`记录代码SHA、标签来源、8项定向测试、JS语法与HTTP发布检查；不声称浏览器交互已完成。

网页另读取Run `smoke_visual_risks_for_review_v2.json`的逐shot视觉观察，发布来源SHA并保留`visual_acceptance=pending_not_passed`。它与`encoded_verified`分开：视频完好可播放，不表示构图通过。页面顶部、对应视频上方和矩阵格显示视觉待审提醒，支持仅看风险、优先跳到主体离框片段及指定抽样秒数；明确抽样时刻不能推断连续离框时长。`gallery_visual_risk_publication_v1.json`记录本次6条提醒（4条优先）、11项定向测试和HTTP/JS检查；舒展舞步近景的219/402原帧确认无脸，媒体仍保持编码通过，视频/相机计划不修改。该观察不推广为全时段离框比例，也不自动删除组合。


### 12.5 当前运行检查点与接续

`legacy_motion/validation_v1.json`已记录10项实际UE跨性别数值检查通过且原资产未改；不是只凭骨骼名称推断，视觉仍待生成与人工核验。`review_delivery_manifest_v1.json`当前1270计划中10条可播，`smoke_visual_risks_for_review_v2.json`的6条近景提醒仍待审，不改变编码通过状态。舒展舞步面部近景在两个抽样时刻完全无脸，不能按一般局部裁切忽略。

`scenes/scene_content_copy_receipt_v1.json`记录19个新增包复制及SHA核验完成；全范围24包/26主图由`scenes/ue_scene_import_verification_v1.json`持续记录UE加载，复制成功不等于加载成功，更不等于视觉接受。运行接续只维护本Run `WORKING_STATE.md`，实时数量归Status与实际回执；goal保持active。此轮轻量同步不重新运行完整回归，最终目录/审计待收尾统一执行。


### 12.6 批次恢复与场景加载后的运行边界

场景导入完成范围由`scenes/scene_final_summary_v1.json`、`imported_content_final_hash_check_v1.json`及`scene_staging_cleanup_receipt_v1.json`拥有。场景页按`needs_review`单独提示资源问题，可展开硬/软依赖候选，并展示全部`content_roots`；不是把所有加载成功视作资源完整。发布检查为`gallery_scene_ui_publication_v1.json`。

`scene_postload_runtime_limitation_v1.json`记录多场景加载后累计纹理编译/资源压力触发内存提交额度不足。先前主图加载及文件SHA结果不撤销，但新场景渲染稳定性仍未验证；后续应使用隔离会话及独立渲染证据。该会话故障不能归因于某个场景包损坏。

`run_camera_batches.py`支持指定attempt版本、按同组全部shot身份与保留媒体SHA恢复已完成版本，避免重复渲染；监控指定editor PID退出后及时失败，不在无编辑器时无限等待。清理必须使用PowerShell 7 `pwsh`，曾因Windows PowerShell 5环境缺Get-FileHash导致首次退休失败，恢复后复用已验证cross v2媒体并成功退休原帧。媒体验证报告是编码时快照，原帧是否仍在应查`raw_retirement/`最新回执。运行时PID只作当时检查点，不是持久控制目标。


跨性别视觉来源`legacy_cross_sex_visual_audit_v1.json`转换为同一网页风险结构，`visual_risk_sources`同时绑定相机及跨性别报告SHA；跨性别报告的媒体验证SHA亦需一致。M01女性宽蹲短裙提示按`outfit_pose_compatibility`保留，不能写成骨骼转换失败或剔除动作。`gallery_cross_risk_tests_v1.xml`记录12项定向通过；`batch_resume_targeted_checks_v1.json`记录5项离线mock恢复/清理调用检查，PID退出仅源码核查，未操作运行中UE。


远程执行prepare/render只打印短摘要，完整准备/渲染回执保存在磁盘。首次all000已在UE提交渲染，但完整回执打印超过远程接收缓冲导致控制端传输失败；恢复读取已有submitted回执而不重复提交，旧失败传输日志保留。控制端异常不等于UE作业未提交，恢复须先检查磁盘回执和编辑器状态。


`audit_delivery_coverage_v1.py`为本Run只读交付覆盖审计，输出`delivery_coverage_audit_v1.json`。独立核对冻结1260主矩阵与10跨性别ID集合、计划SHA、实际MP4 SHA和来源shot/完整解码回执，复用网页验证器而不重复全解码；逐条比对发布manifest与HTML嵌入数据。未生成列pending，不能按总数相等判完成。场景加载/文件SHA/暂存退休及cross源目标20资产SHA分别核查，技术交付不等于人工视觉接受；运行中文件变化要求重试，未齐全为partial。


网页继续接入`first_batch_visual_risks_for_review_v1.json`，与原smoke/cross来源逐ID合并并共同记录来源SHA，不覆盖原7条风险。新增只表示特定抽样时刻需审查，不更改媒体已验证状态或推断所有组合失败；发布证据为`gallery_first_batch_risks_publication_v1.json`，定向测试13项。长驻批次若缓存旧assembler，需由调度所有者在安全边界重载发布模块，避免后续发布丢失新来源。


长驻旧发布器确曾将44条页面的风险降回7条，原因是Python模块缓存。现`publish_and_retire`每次启动独立Python进程加载磁盘当前assembler，不能仅修改源码期待已运行模块自动更新；控制器由root在已提交作业且只等回执时安全重启，继续复用回执。`publisher_cache_fix_verification_v1.json`记录语法检查与实际独立构建：44条媒体、16条风险及3份来源完整保留；验证未操作UE或队列。


控制器发布模块更新已按`orchestration_reload_v1.json`在all_002已提交、控制器仅等待回执时完成：只停止Python控制器，保留UE和当前渲染作业，再由新控制器复用回执。不是重新启动UE或重复提交渲染。

`ue_motion_portrait_scene_pilot_v1.py`的本任务新建map最终保存由`levels.save_current_level()`改为显式`EditorLoadingAndSavingUtils.save_map(world,map_path)`，避开前者已查明的CheckoutPackages入口；碰撞拒绝、原来源SHA保护、保存后重载/绑定回读和已有回执保护仍保留。`map_save_source_protection_check_v1.json`记录AST语法与源保护定向检查，未执行UE保存；这项修改不能证明首次save_map曾耗时82分钟的异常已定位或解决，运行性能待真实后续回执。


`ue_motion_portrait_scene_pilot_v1.py`每次prepare批次仅首次读取`ue_motion_scene_sequence_v1.py`的原生动画段文本，随后给身体与跟随组件显式传入同一不可变文本；每条track仍粘贴新section、新参数并独立设置动画和时钟，不能共用可变section对象。原生模板加入source_pins，在每镜头及批尾重新核对SHA；缓存只在本次调用内有效。此变更减少重复开模板/读剪贴板的操作，但真实性能收益仍待下一批UE验证，不能据离线测试断言已提速或修复异常保存耗时。已完成渲染及原始证据不回改。


`native_section_reuse_test_record_v1.json`忠实转录实际工具测试输出（非JUnit）：`test_motion_scene_sequence_v1.py`与`test_camera_alignment_review_v1.py`共19项通过、退出0；记录保留命令和覆盖边界，未编造精确时刻。该证据验证独立section/参数及包装器保护，不包括实际UE性能测量。


原生文本复用现已有真实准备证据：`native_section_reuse_runtime_check_v1.json`为`preparation_verified`，all_004共12个序列逐个通过相机10通道完整关键帧、3个source_pins/新资产SHA和Body/Eyes/Teeth/Tongue/EyeOcclusion/Tearline绑定检查。该批已提交渲染，但此报告只证明准备内容，不宣称该批媒体通过；性能收益仍未量化，异常保存耗时亦未因此判定解决。总体goal继续进行。


`legacy_motion/legacy_cross_sex_candidates_v1.json`与同名中文说明拥有旧10动作的双性别候选映射：原性别引用`legacy_shared_motion_reuse_v2.json`验证的shared-body目标，反向引用本轮LegacyCrossSex目标；绑定20份body、两套Skeleton、原来源、相同选用窗口/速度、数值及20条视频证明。创建时核对SHA和合同一致，三份正式catalog/face配置未改。technical_available为true，human_acceptance为pending、active_menu/production均false；原菜单1–25保持。该产物落实“旧10保留并具备两性候选调用信息”，不声称菜单已全面开放，后续须显式overlay接入且不能伪造CC导出证明。


`legacy_original_reference_v1.py`拥有跨性别页原性别临时参考验证：`references/legacy_original/`保存从已审样片复制的原字节MP4/回执/封面，index绑定候选映射SHA。按稳定motion ID、性别、选用窗口/速度/FPS/帧数及实际文件SHA/完整解码回执校验；不符则参考pending。复用现有媒体验证器，无重复全解码。HTML在本轮同动作原性别front_full未可播时使用此前参考，本轮可播自动优先；标明构图可能不同、只比较姿态，参考独立于1270卡片及已验证数量。`legacy_original_reference_publication_v1.json`记录10参考、原16风险、14项测试、JS语法和选择逻辑检查；真实双播放器交互由root核验，未操作UE/队列。


`legacy_original_reference_browser_check_v1.json`记录root实际浏览器观察：F01女原片/男反向片、M01男原片/女反向片两组均readyState4且同步触发后正在播放，两侧各组时长一致。只验证这两组播放器加载/启动，不称10组都经过浏览器测试或全程同步/视觉接受。`audit_delivery_coverage_v1.py`另验证10个历史参考实际SHA与时钟、逐条比对发布字段，并确认独立于1270主ID/可播计数；参考不作为本轮新渲染。

## 2026-10-12：旧动作跨性别兼容确认

用户2026-10-12确认旧10动作全部可用于男女共享骨骼，并允许与新动作统一保留，兼容性验收结束。独立回执 `%OUTPUT_ROOT%/camera_motion_scene_alignment_20261012_v1/legacy_motion/user_cross_sex_acceptance_20261012_v1.json`绑定原候选映射SHA；原候选与媒体验证历史回执不改写。正式菜单接入未在本次汇报执行，相机批量任务继续暂停。


## 13. 场景专用资源目录整理（2026-10-12）

用户授权先Synthwave_city试点再分批将场景专用资源迁入`Content/Scenes`（UE路径`/Game/Scenes`）。唯一current计划的R06拥有要求；本节拥有新Run `%OUTPUT_ROOT%/scene_folder_organization_20261012_v1/`、离线盘点与路径overlay、迁移前后引用/包/地图检查及失败恢复证据，沿用`OUT-WF60-SEQUENCE-TEMPLATE`、`VAL-SCENE-01`。输出默认unclassified保护，不因目录整理授予额外清理权。

本节拥有`00_engine/scripts/unreal/ue_scene_folder_organization_v1.py`（UE端）及`00_engine/scripts/unreal/scene_folder_organization_v1.py`（外部准备/配置端），也拥有Run内`audit_scene_roots_readonly.py`、`build_scene_move_recommendation.py`等限定实验辅助。新入口当前处于准备/实现中，命名不代表资产已迁移。UE操作由root串行调度，文档agent不移动资产或控制编辑器。

迁移应依据实际资源归属和依赖，保护共享/插件/其他会话资产；不能用普通文件移动替代UE引用更新。先验证试点的实际迁移、地图加载、引用和保存回执，再分批扩展。具体机制由新脚本和实际执行记录确定，未完成项明确保留。当前配置通过源路径到当前路径overlay更新，冻结相机计划、已接受媒体和历史回执维持原字节，不把历史SHA改写成迁移后结果。

此次授权不恢复相机批量或paused goal。旧10动作人工接受已完成，独立回执为旧Run `legacy_motion/user_cross_sex_acceptance_20261012_v1.json`；动作菜单激活、相机构图验收与场景迁移互不代替。另一会话皮肤状态不改。当前R06执行中，尚无迁移完成声明。


### 13.1 试点迁移与路径overlay检查点

`backup_manifest_v1.json`及`external_referencer_backup_v1.json`已记录全根目录和外部引用包回退副本成功。`move_Synthwave_city_v1.json`记录UE `EditorAssetSubsystem.rename_directory`返回true，状态仍为renamed_pending_verification。`verified_Synthwave_city_v1.json`当前success=false，showcase结构比较有差异；actor计数相同不能替代结构一致。必须查清实际差异并取得成功verified回执，不能因文件名含verified而宣布成功，也不能直接改成功字段。

本节同时拥有`scene_path_relocation_v1.py`及`tests/test_scene_path_relocation_v1.py`。当前路径registry为 `00_engine/assets/scene_folder_relocation_20261012_v1.json`，精确发布范围由registry及[WF-60状态](../../project_management/status/workflows/WF-60.md)拥有；最初空映射只代表准备时检查点。新Run `gallery_scene_index_relocated_v1.json`保存新索引。消费者为`ue_scene_location_pilot_v1.current_map`、`ue_scene_character_pilot_v1`和`assemble_camera_alignment_review_v1`。映射必须绑定success=true验证回执与SHA才可启用；旧Run冻结证据不改写。`scene_path_overlay_implementation_v1.json`与JUnit `scene_path_relocation_tests_v1.xml`记录25项定向通过，仅证明离线路径契约，不代替UE迁移验证。相机仍暂停。

后续批次汇总只读取真实`verified_*.json`的success及差异范围，结合对应move/baseline/回退证据；rename成功、验证失败、验证完成分别计数。当前不将全部根目录视为已迁移，不写全面完成。


### 13.2 试点通过与批次推进

后续`verified_Synthwave_city_v2.json`已success=true、differences为空；原v1=false保留为故障过程证据。`pilot_original_repeat_probe_v1.json`来自原始回退文件建立的隔离项目重复加载，证明两类蓝图树组件自身的mesh/material/yaw随机变化。v2只允许已证实树组件候选及字段范围，位置、scale与其余结构仍严格比较，不以广泛忽略差异换取通过。

`pilot_visual_check_v1.json`为迁移后真实UE视口观察，所见道路、建筑、棕榈、天空和材质未发现明显缺失；只覆盖一个视角，不是逐像素比较或全场景视觉验收。该检查不启动相机批量。

本节拥有`00_engine/scripts/unreal/scene_folder_batch_driver_v1.py`及`tests/test_scene_folder_batch_driver_v1.py`，以及在新Run下的批次调度/恢复日志和回执。driver只按实际verified成功记录推进与汇总，不因启动就计为迁移完成。原始副本、失败证据和冻结历史维持可追溯，当前完成与发布范围由[WF-60状态](../../project_management/status/workflows/WF-60.md)拥有。相机拍摄及旧goal持续暂停。


### 13.3 原始冷启动与动态材质比较口径

`cold_baseline_racing_track_v1.json`、`cold_baseline_AsianArchitecture_v1.json`、`cold_baseline_QA_ModularParking_v1.json`及`cold_source_execution_v3.json`记录三个原始场景在独立项目中的真实冷启动检查通过。源文件完整集合、大小和SHA前后相同，saved_source_assets=false；冷启动签名补充冻结warm baseline，不改写其身份/旧证据。

动态材质实例MID的临时对象名不能当作持久资源身份。`signature_format=mid_parameters_v2`采用已通过实际UE反射的材质参数比较，处理临时材质名字造成的误报；这不是忽略全部材质差异，仍检查真实参数及其余结构。先前失败回执保留为历史，不改成成功。冷启动原始基线通过也不能替代迁移后verified回执。driver正在分批继续，整体尚未完成，相机拍摄持续暂停。


### 13.4 第一批验证与范围确认（2026-10-13）

`verified_Synthwave_city_v2.json`、`verified_racing_track_vdriver_20261012T160703510691Z_verify_racing_track.json`、`verified_AsianArchitecture_v3.json`均success=true；对应3项路径映射已在registry发布为verified。racing为136资产/1图，Asian为151资产/2图。稳定原始冷启动`cold_baseline_*_v2.json`及`settled_original_execution_v2.json`成功，后者明确saved_source_assets=false；之前失败和coldv1证据保留，不改写。

后续第二批成功证据为`verified_QA_ModularParking_vdriver_20261012T160853705279Z_verify_QA_ModularParking.json`、`verified_RedDesertPack_vdriver_20261012T161551249205Z_verify_RedDesertPack.json`、`verified_TheMetro_vdriver_20261012T161645152326Z_verify_TheMetro.json`，均success=true、differences为空，并各由registry的receipt SHA绑定。第二批验证与发布已完成，整体仍进行中。

授权整理范围依据`brushify_boundary_editor_history_audit_v1.json`允许Brushify整根（198资产、1个Dunes地图、0外部注册引用者）；StarterContent继续作为共享公共库保留。边界审计不替代Brushify自身的新baseline及迁移后verify；包内已记录的缺失依赖也不会因移动修复。相机R02/R05及原goal继续暂停，最终目录/审计待真实最终证据收口。


### 13.5 EditorViews恢复工具与RedDesert单项清理

本节拥有`00_engine/scripts/unreal/restore_scene_editor_views_v1.py`及`tests/test_restore_scene_editor_views_v1.py`。`editor_views_restore_tests_v2.xml`记录15项离线测试通过；工具尚未执行，必须等待24根verified、driver结束且主UE关闭后才恢复EditorViews。测试成功不能作为恢复已经完成的证据。

RedDesert native rename已产生251资产/2图，但唯一旧纹理因privateImportData保存失败残留。`red_desert_obsolete_texture_check_v1.json`在目标资产身份、两图结构/相对组件、新资产无旧根依赖、旧纹理0引用者及旧来源/backup SHA一致均检查后，限定该旧副本为可清理项。`red_desert_obsolete_texture_cleanup_v1.json`记录仅通过UE delete_asset移除此单项：success=true、dirty为空、旧根0资产、新根251资产。不是对未知旧根的通用删除授权。driver从verify续行，未重复rename；本阶段不因此宣布全部场景完成。

### 13.6 Madeline发现超时恢复与后续验证（2026-10-13）

`move_Madeline_v1.json`记录官方rename_directory返回true、dirty_after_rename和dirty_after_save均为空，状态为renamed_pending_verification。首次verify的`driver_20261012T164251454834Z_verify_Madeline.log`仅记录远程发现失败；旧12秒发现窗口未完成结构验证，不能视为结构比较失败，也不能重复rename。

driver dispatch已将`ue_remote_exec.py --discovery-timeout`改为90秒。`scene_folder_driver_tests_v4.xml`记录27项离线测试通过（0失败/错误/跳过）；`driver_session_20261012T164429721067Z.json`绑定本次代码SHA及完整授权根列表，新会话执行恢复。后续`verified_Madeline_vdriver_20261012T164529239596Z_verify_Madeline.json`实际success=true、differences为空，验证365资产/7图；此回执证明结构校验完成，但不能替代路径registry中的发布记录。当前verified与published分别计数，精确进度见[WF-60状态](../../project_management/status/workflows/WF-60.md)。EditorViews恢复工具仍仅ready，尚未执行。

`workflow_tests_v2.xml`及`workflow_tests_v2.log`记录当时documentation/dataset/unreal三个tests目录实际回归1247项通过、163.12秒，0失败/错误/跳过。先前v1在沙箱系统TEMP边界触发85失败/12错误；v2使用项目内TEMP/TMP并取得本机HTTP测试权限后通过，v1历史保留。此全回归在§13.9新增九龙verification_asset_contract之前执行，不能宣称已覆盖该新代码；后续定向测试独立记录，也不能替代尚未完成的全场景迁移及最终文档审计。

### 13.7 AmusementPark旧重复纹理单项恢复（2026-10-13）

`move_AmusementPark_v1.json`记录rename_returned=true，但旧`/Game/AmusementPark/Textures/T_DefultWhite`仍脏、move状态未完成；原move回执保持，不倒写成功。`amusement_park_obsolete_texture_check_v1.json`实际证明目标413资产身份完整、两张地图结构与相对组件一致，目标资产无旧根依赖，唯一旧重复纹理零引用，其旧物理SHA与原回退副本一致。

随后`amusement_park_obsolete_texture_cleanup_v1.json`绑定前置检查SHA，仅通过官方delete_asset移除此旧重复纹理，success=true、old_root_assets=0、dirty为空。driver续行只验证AmusementPark并继续后续批次，不重复rename；单项清理与地图诊断仍不能替代正式verified回执或整批发布。EditorViews恢复及相机批量仍未执行。

后续`verified_AmusementPark_vdriver_20261012T165259650870Z_verify_AmusementPark.json`正式success=true、differences为空，413资产/2图通过。此结果由新验证回执拥有，不修改旧move状态；本批最终发布范围由当前路径registry与WF-60状态拥有。

### 13.8 Cherry闭合旧重复集与唯一物理孤立包恢复（2026-10-13）

CHERRY_TREE官方rename已产生416个目标资产，保存旧19个重复包失败；`cherry_obsolete_duplicate_check_v1.json`实际success=true，证明旧19项形成闭合内部引用集，无外部引用者或目标目录对旧根依赖，目标416身份完整、两张实际地图结构及相对组件一致，19份原始回退副本完整。部分旧包已在native保存时重写，不能把19项都描述为旧源SHA未变。

官方delete_directory已移除19项AssetRegistry记录但返回false；`cherry_cleanup_attempt_state_v1.json`记录旧registry为空、新目录416项，唯一脏包为已删的旧SK_Mannequin，物理目录仍残留其uasset。官方unload拒绝脏包后，使用正常quit_editor退出；`cherry_deleted_package_shutdown_v1.json`只允许丢弃这一已删旧包。确认无主项目进程、路径与备份后，仅移除3.52MiB旧`SK_Mannequin.uasset`孤立文件，其原始SHA及backup SHA均仍为`0baddfbc17d5660967d125a507b88ccb1f4892cec565fc223a6a8c38bf8d6495`。精确范围见`cherry_physical_orphan_cleanup_v1.json`和`cherry_orphan_path_recheck_v1.json`，不构成普通文件移动或通用删除授权。

重启后的`cherry_duplicate_recovery_completed_v1.json`记录旧根0项/物理旧根已清除、新根416项、dirty为空；随后从磁盘执行的`verified_CHERRY_TREE_vrecovery_20261013_v1.json`正式success=true、differences为空，416资产/2图通过。原move、删除返回false和关机前记录均保持历史，不用人工恢复回执替代正式验证。当前批次已由driver发布，准确registry receipt SHA和动态计数从[WF-60状态](../../project_management/status/workflows/WF-60.md)读取，整体R06继续in_progress。

Cherry主地图保存耗时约8分17秒。本机UE5.8源码`Engine/Source/Runtime/Landscape/Private/Landscape.cpp`的`ALandscapeProxy::PreSave`（4265行起）在普通Editor保存中调用`BuildGrassMaps()`，非autosave还可调用并等待`UpdateNanite`；因此草数据生成/可能Nanite更新属于保存成本的源码依据，不能仅由耗时断定具体占比。592/1024草组件warning也不是迁移结构损坏证明；实际主地图已成功保存并取得后续结构验证。此轮不修改草或Nanite设置，相机继续暂停。

### 13.9 九龙原redirector重复移动失败、完整回退与限定退休合同（2026-10-13）

`move_Kowloon_v1.json`保留首次官方rename_directory的rename_returned=true但success=false/未完成保存结果。原Windows路径同一个包中有Blueprint、generated class和CDO三项ObjectRedirector，分别指向Prefabs的真实对象；目录遍历加载这些redirector会解引用真实对象，导致真实BP/class/CDO重复移动。`kowloon_obsolete_duplicate_check_v1.json`为false；最小`kowloon_blueprint_path_repair_v1.json`虽恢复目标Prefabs路径并rename_returned=true，但仅证明候选路径修复。磁盘重载后的`kowloon_obsolete_duplicate_check_v2.json`仍false，主地图Actor由2323变2184，139个窗户Actor丢失，地图结构及相对组件不等。资产身份恢复不能替代地图一致；不把这一步写成verified。

`kowloon_rollback_v1.json`成功将九龙完整463份原始文件从冻结snapshot恢复，并保留474份失败尝试文件用于追溯；只处理九龙，不回退已通过的其他根或外部包。`kowloon_original_redirector_targets_v1.json`在独立原始副本项目中实际读取三项原redirector各自的真实Prefabs目标，source SHA前后及原始backup SHA均为`b8d437f96e7f892400f0fa20fdc13b64b9042fcca126c765cd00417141f58e26`，saved_source_packages为空。此独立来源证据与旧baseline保持原字节，不能从已失败的移动结果反推原目标。

回退后`kowloon_content_only_move_v1.json`使用官方AssetTools.rename_assets，对462项实质资产各提交一次rename，原三项ObjectRedirector单独审计、排除于移动列表，避免再次解引用成第二次移动。移动及目标保存返回true，content identities一致；`kowloon_obsolete_duplicate_check_v3.json`成功，三张实际地图Actor为2323/63/104，signature及相对组件均匹配，139个窗户Actor保留。v3是本次恢复前置证据，正式verified及批次发布仍需后续独立回执，不由这一success字段自动取得。

`kowloon_redirector_retirement_v1.json`绑定原baseline、不可变原redirector backup、独立original_target_witness与content move SHA，并保存462项实际资产、三地图完整结构/相对组件、旧集全部引用者及新目录全部依赖。随后`kowloon_duplicate_cleanup_v1.json`仅通过官方delete_asset删除10项已证实不用的非redirector重复包，dirty_after为空，剩下同包三项redirector；不将redirector传给资产加载或删除，避免误删其新Prefabs目标。

`kowloon_retired_redirector_shutdown_v1.json`记录正常退出且dirty_discarded为空。仅对已退休的唯一旧Windows redirector包执行离线literal文件清理：首次要求current SHA等于原始backup SHA而被拒，未删除；该包已由正常native rename重写为新Prefabs目标，后续将当前SHA与成功v3前置证据的source pin核对。`kowloon_retired_redirector_file_cleanup_v1.json`记录仅删除此一文件，当前SHA为`b2ed84549937452d01dd66618937da767cf4e01ccd274413b647ef0af0e79d07`；原始backup仍保持上述b8d437f...。不把current已重写的文件描述为原始字节未变，不授予其他文件的通用清理权限。

本节拥有生产`ue_scene_folder_organization_v1.py`内新增的`verification_asset_contract`及`tests/test_kowloon_redirector_retirement_v1.py`。仅针对`/Game/Kowloon`且完整证据通过时，允许冻结原465项身份中精确三项原Windows ObjectRedirector退休，预期实质身份为462；验证原baseline/backup SHA、独立原目标证据、实际三地图signature及relative、全部旧引用者和462新资产依赖，最终verify仍重新检查实际地图/身份/旧根依赖。缺少退休证据时沿用原严格身份集合，畸形或不匹配证据拒绝，其他根不使用此例外；不修改原baseline，也不放宽Actor或相对组件比较。新增合同相关定向测试实际108项通过，旧1247项全回归不覆盖此新增代码。

后续`verified_Kowloon_vdriver_20261012T180001353254Z_verify_Kowloon.json`已正式success=true、differences为空，462实质资产/3图通过，回执绑定精确三项退休证据，原465身份baseline保持。九龙与同批后续根已实际发布；当前接受计数由Status/registry拥有，不从前置恢复结果提前累计。R06保持in_progress，相机R02/R05及原goal持续暂停，皮肤独立范围与EditorViews恢复边界保持。

### 13.10 Cyberpunk官方完整类名重定向（2026-10-13）

Cyberpunk_City官方native移动/保存完成、旧根为空；三项Render Preset加载后类由旧`/Script/MovieRenderPipelineCore.MoviePipelineMasterConfig`变为`/Script/MovieRenderPipelineCore.MoviePipelinePrimaryConfig`。本机UE5.8.1/CL56057345的`Engine/Config/BaseEngine.ini`第1181行在CoreRedirects明确这一完整class pair；该源SHA为`dc5b359ee95ccff0ccdfa4181b2875451b4a33474c0bb896fd8fef23aed1bf8e`，`Engine/Build/Build.version` SHA为`d35d3d5f4de0636fbb62386b63dee8056889fb2baf199d012dc32ee77f7a2997`。这是本地官方兼容重定向证据，不把任意短类名相似视为同类。

本阶段生产仅规范化该精确完整MRQ class pair；后续第二个UDS官方限定pair见§13.21，二者都仅用于registry资产身份比较，回执保留`raw_original_asset_records`、`raw_asset_records`和绑定来源/版本的`canonical_class_aliases`；地图Actor classes、其他类、地图signature、相对组件及依赖检查仍严格。`verified_Cyberpunk_City_vdriver_20261012T180729623059Z_verify_Cyberpunk_City.json`正式success=true、differences为空，467资产/2图通过。`tests/test_scene_official_class_alias_v1.py`由本节拥有；`official_alias_and_retirement_tests_v1.xml`实际127项通过（70退休、19alias、38场景/driver相关），0失败/错误/跳过。旧1247全回归早于该代码，不用于覆盖此次新增规范化。

### 13.11 UrbanJapan唯一异常材质对象迁移（2026-10-13）

UrbanJapan native目录rename返回false：原`/Game/UrbanJapan/Materials/MI_Ubc_Building`包内对象名为`MI_BuildingDetails05`，与另一真实同名材质冲突。`urban_original_material_signature_v1.json`在隔离原backup项目只读采集该对象，source SHA前后及不可变backup SHA均为`37b97ff708b16b6ef3f175b76aaf8ce6bf749c20e7bd1a5cbfe2163b2cd4abb7`、saved_source_packages为空。失败move回执保留。

`urban_material_move_v1.json`仅对该异常对象执行官方`rename_loaded_asset`：原完整对象路径`/Game/UrbanJapan/Materials/MI_Ubc_Building.MI_BuildingDetails05`迁为`/Game/Scenes/UrbanJapan/Materials/MI_Ubc_Building.MI_Ubc_Building`，包名与对象名统一；rename/save返回true，公开material_before/material_after设置一致，dirty为空，另一真实`MI_BuildingDetails05`未变。`urban_material_relocation_v1.json`绑定原backup、独立原材质witness与move SHA，并记录486实际身份、两地图结构/relative、旧根为空及全部新资产依赖。最终`verified_UrbanJapan_vrecovery_20261013_v1.json`正式success=true、differences为空，486资产/2图通过。

新增`urban_verification_asset_contract`及`urban_comparison_signature`只在有效独立witness完成验证后允许上述精确一对完整object path在比较中映射，generic `canon`未改；不改另一真实同名材质、其他对象叶名或不相关路径。参数证据覆盖九种公开parameter arrays（scalar/vector/double_vector/texture/texture_collection/parameter_collection/runtime_virtual_texture/sparse_volume_texture/font）、有效scalar/vector/texture/static-switch值、整个父链全部named global static-switch值与override状态、base_property_overrides及additional公开settings。受保护/私有static parameter structs未读取；这是明确范围的设置比较，不宣称所有隐藏状态或二进制byte equivalence。

本节拥有`tests/test_urban_material_relocation_v1.py`；`urban_material_contract_tests_v1.xml`实际276项通过（79 Urban、197既有相关测试），0失败/错误/跳过。本次生产`ue_scene_folder_organization_v1.py` SHA为`57ac95c73372c93b299ddec1a1064441c726baad89d33eea7023049fc84b3c6e`，由`driver_session_20261012T183149786096Z.json` source pin再次绑定；旧1247全回归在本次合同和helper前执行，不写成现代码全回归通过。

### 13.12 未迁移特殊根的前置准备与边界（2026-10-13）

Japanese_Village原baseline读取成功，记录616项身份/23图，其中原`HDRI/pizzo_pernice_puresky_4k`为一项ObjectRedirector。`japanese_original_redirector_targets_v1.json`在隔离原backup项目实际确认其目标为`/Game/Japanese_Village/HDRI/SKY_HDRI.SKY_HDRI`，source SHA前后及backup SHA一致、saved_source_packages为空。生产`japanese_verification_asset_contract`及`tests/test_japanese_redirector_retirement_v1.py`仅定义此精确原redirector的限定退休合同；`japanese_contract_application_tests_v1.xml`实际197项通过。候选测试v1的一项失败保留，v2的70项通过不倒写旧失败。Japanese尚未实际迁移，615潜在实质资产/23图不计入已验证或发布范围；实际迁移仍须完整独立退休witness及正式verify。

只读前置扫描另发现KyotoAlley有428个`(1)`重复包与正常名冲突；后续精确清理及已通过的源基线Gate见§13.15。VictorianStreet存在同包World与BuiltData顶层对象，已建立628身份/2图baseline，官方627个primary对象首次取消后neutral v2成功迁移，内嵌BuiltData随World保留，628身份/两图fresh正式验证并发布；见§13.18。Kyoto已native迁移但正式验证待解决，见§13.22；不能套用九龙或Urban限定例外，也不因重复或多对象现象自动删除/退休。当前目标与精确进度由WF-60/Plan/PROJECT_STATE拥有，相机持续暂停，皮肤独立范围不改。

### 13.13 Evening外部引用强制保存与旧文件清理（2026-10-13）

`evening_external_reference_repair_v2.json`实际success=true，限定18个现用SceneBases/Trials外部地图，按已审计旧到新对象路径修复hard/soft引用，并逐图记录原backup、前后source SHA、实际地图结构及相对组件。官方`EditorLoadingAndSavingUtils.save_packages([package], False)`明确`only_dirty=False`，强制保存才实际闭合旧引用；不能把先前dirty条件下返回保存成功视为旧引用已消失。该事件修改了18个现用UE地图包的引用与SHA，原backup及冻结历史回执保持，不倒写旧SHA。

`evening_obsolete_duplicate_check_v3.json`已success=true、destination_identities_match=true、differences为空、external_referencers为空、新目录无旧根依赖；这才构成残留清理前置证据。`evening_offline_cleanup_precondition_v1.json`进一步绑定v3与官方非redirector重复清理回执SHA，精确列出215份旧redirector文件、实际目标、逐文件当前SHA及原始backup，且只允许丢弃已官方删除包的残留状态。`evening_old_file_cleanup_v1.json`success=true，按literal列表清除这215文件；不把此限定清理推广到未知旧根。

fresh启动后`verified_Evening_Highway_vrecovery_20261013_v1.json`正式success=true、differences/dirty为空，旧根清零、510实际资产及`Maps/demo_level`一张地图通过。回执map_count=1，不凭同类场景经验计为两张。回执明确验证注册身份/类、实际Actor/mesh/material/instances/loaded levels及相对结构，MID scalar/vector仅按记录的rel_tol/abs_tol各1e-6比较且raw signatures保留，其余字段按原契约；不宣称像素确定性或拍摄通过。该根尚未发布到当前overlay，当前verified/published分别由Status计数。

### 13.14 Medieval保存残留与首次Castle加载崩溃（2026-10-13）

`move_Medieval_Environment_v1.json`记录native rename_returned=true但success=false/状态moving，八个旧`Asset/TX`纹理包因private AssetImportData保存失败仍脏；不能仅以rename返回true计为迁移通过。首次残留检查的Castle加载阶段发生GC崩溃，`editor_driver_20261012T190432526504Z.log`记录粒子组件/AttachParent引用链持有Castle World，EditorServer报告旧地图未被垃圾回收清理。此为首次残留检查，不是二次warm测试；日志中的LevelScriptBlueprint链项也不足以认定LevelScript是根因。

`medieval_residual_remote_v1.json`为零字节，不能作为成功残留检查或地图一致证据。后续隔离原源与目标水体完整几何/descriptor补充证据已成功，有限生成mesh规则已生产整合及离线测试，详见§13.17；此为恢复中间阶段历史。后续八旧TX精确清理、fresh整根正式验证及发布已完成，见§13.19；不改首次失败回执或零字节文件。相机保持暂停，不因这次加载崩溃重启拍摄。

### 13.15 Kyoto精确428重复文件清理与已通过的源基线Gate（2026-10-13）

`kyoto_duplicate_prepare_remote_v1.json`绑定`00_engine/temp/scene_folder_organization_20261012_v1/kyoto_exact_duplicate_retirement_preconditions_v1.json`，原准备回执保持prepared_not_deleted。前置将精确428份`(1)`文件与正常伙伴及原始backup逐对核对字节/SHA，所有全局已注册hard/soft、searchable-name、management引用类别均无引用；保留全部原始与正常伙伴backup及原baseline/history，不引入任意unused-name例外。

`kyoto_exact_duplicate_offline_cleanup_v1.json`实际success=true：无Editor进程，按精确literal428列表离线删除，绑定前置SHA`7d5eb327efccda10a111f2aea9b726e6c4f75814986cdfc9c114fd152e137337`，remaining_file_count=755；原始完整backup仍保留。清理只退休精确无引用复制文件，不代表Kyoto迁移通过。

后续`00_engine/temp/scene_folder_organization_20261012_v1/kyoto_exact_duplicate_retirement_postcleanup_v1.json`内容schema为`kyoto_exact_duplicate_retirement_postcleanup_v2`，SHA`93af36bca6d2160c35e9ce2a98f4b201e1e0c5a1d8bf29d0408a8748ebc947e6`，success=true/status=postcleanup_source_baseline_verified。fresh源目录精确755身份/四张正常地图、保留755文件SHA、四图结构及relative均通过；428对原/正常文件的856份backup SHA也核验一致。`kyoto_original_settled_witness_v1.json`在完整1183原始backup隔离源上读取，source前后SHA完全不变、未保存source，四正常图与755源baseline严格相等。

原preflight只有Overview的精确`SkySphere` actor/`Sky Sphere mesh` component呈加载完成差异；有限合同绑定该完整身份、原/settled实际记录、1183原文件SHA和引擎证据，仅解释该原源加载阶段差异，不泛化忽略天空、Actor、组件、材料或几何字段。此Gate只验收清理后的源基线，该源基线检查时尚未迁移；随后Kyoto native迁移已执行但正式验证失败，最新进度见§13.22，仍未计入迁移verified/published。原准备/失败历史保持，R06仍in_progress。

### 13.16 Seaside十六旧纹理残留清理与正式发布（2026-10-13）

`seaside_exact_residual_check_v1.json`实际success=true：565目标身份完整，两张实际地图及relative一致，旧16个真实纹理无引用，external_referencers为空、新目录无旧根依赖。`seaside_exact_real_duplicate_cleanup_v1.json`仅官方delete_asset删除这16个精确审计旧真实对象，remaining_source_assets/dirty_after为空；不是redirector解引用删除。后续`seaside_exact_offline_cleanup_precondition_v1.json`绑定残留检查及官方删除receipt SHA，逐文件钉住当前SHA和原始backup，`seaside_exact_offline_cleanup_v1.json`在无Editor进程时仅按16个literal物理路径清除残留，原backup保留。

fresh正式`verified_Seaside_Town_vrecovery_20261013_v1.json`success=true，565资产/两图、differences/dirty为空，旧根0；SHA`2675184eb59c99691094334a9a6ea8038db229da46dd46604cdd1870385aea1e`。`publish_evening_seaside_v1.log`记录本批Evening/Seaside正式发布，当前overlay两份receipt SHA与实文件一致。实际地图结构验收不等于渲染像素或拍摄完成；相机仍暂停，完整目录迁移及EditorViews恢复未完成。

### 13.17 Medieval原源与目标水体补充几何证据（2026-10-13）

隔离未改原源在四次water加载后生成`WaterInfoMesh_3`，目标为`WaterInfoMesh_6`。`medieval_original_water_geometry_supplement_v2.json`success=true，SHA`35e6273ca911cccae6cab85171af9f0ba1a6a248708c18a3615f2a6bd277c8b9`；`medieval_target_water_geometry_v2.json`success=true，SHA`b7d59e5e6d3ee90237742f70c3c24b846d60366dd32b7bb2716a395a5768d233`。原源前后文件SHA不变、未保存source；精确WaterBodyOcean_1/WaterInfoMeshComponent的公开fullgeometry与descriptor相等，Castle actor_count均3667。记录原始名字、owner/component/mesh路径与采集器/引擎source pins；没有据此删除或重写原baseline。

本节为生产模块`00_engine/scripts/unreal/ue_medieval_water_contract_v1.py`及生产测试`00_engine/scripts/unreal/tests/test_medieval_water_contract_v1.py`的Technical owner；模块SHA`cfb5c57f415044985e406b120c961520d4959b4a8ddddb2dc41acd0ef002d944`，由`ue_scene_folder_organization_v1.py`的verify在通用compare_map前仅对`/Game/Medieval_Environment`调用`validated_map_signature`，整合helper SHA`3a3dc330088b3bc12d40ad3b0ddcb18db5fa848f1e6bd7260b973a7b3a3bbbfd`。此前SHA`57ac95c73372c93b299ddec1a1064441c726baad89d33eea7023049fc84b3c6e`代码归档为`relocation_helper_before_water_contract_v1.py`，原历史receipt不改。生产模块无TEMP采集器运行依赖；仅用固定正式receipt SHA、引擎source/build SHA及516原backup文件逐项大小/SHA验真。

限定Castle_medieval_Map唯一`WaterBodyOcean_1`（类`/Script/Water.WaterBodyOcean`）的唯一`WaterInfoMeshComponent`（类`/Script/Water.WaterBodyInfoMeshComponent`），mesh必须为该Actor outer下的StaticMesh。原/目标完整mesh路径严格限定`WaterInfoMesh_3`和`WaterInfoMesh_6`，全部3667 Actor、地图/组件relative、材料/其他地图字段仍严格。公开完整SOURCE_MODEL LOD0几何包括124 vertex IDs/vertices、122 triangle IDs、三个UV channels、拓扑索引/位置、corner normals/tangents/colors、material IDs；descriptor包括bounds、LODs、LOD0 vertices/triangles/sections、build settings、材料与conservative raster信息。采集前后dirty必须为空，源/目标补充证据不保存资产，UObject私有flags仍标明unavailable，不宣称序列化StaticMesh字节相同。

verify结果的`maps`保存未改的raw_after；仅deepcopy比较副本中上述唯一component.mesh从完整`WaterInfoMesh_6`路径映射到完整`WaterInfoMesh_3`路径。新`water_name_witnesses`数组保留`schema=medieval_water_derived_name_validated_v1`、`source_mesh`、`canonical_target_mesh`、`receipt_pins`、`engine_source_pins`、`actual_water`、`module_sha256`、`scope`。只有实时完整几何/descriptor/身份与钉住的target原记录完全一致且所有source pins通过才允许映射；不修改raw签名、原baseline、live对象或全局路径规范，不对其他root安装alias。

`water_integrated_tests_v1.xml`/`.log`实测该生产测试12项passed，failures/errors/skipped均0；覆盖唯一精确名字对通过且raw不变、receipt SHA缺失/变化、普通资产同名叶子、错误outer/component、未知后缀、顶点/UV/材料参数/其他Actor位置/组件relative变化、完整几何缺失的拒绝。此为离线有限合同测试，旧1247全回归在该新规则前运行，不覆盖当前代码；后续独立实机正式验收及八旧TX精确清理已完成，见§13.19。12项离线测试本身不证明整根迁移，正式验收以fresh实际地图回执及完整actual_water witness为准。

### 13.18 Victorian同包对象迁移准备（2026-10-13）

`baseline_VictorianStreet_v1.json`实际success=true，628注册身份/两图；同package的World和内嵌BuiltData保留在baseline。官方627个primary对象首次rename返回false并取消，`move_VictorianStreet_v1.json`失败历史保留。`victorian_source_unchanged_after_cancel_v1.json`success=true，SHA`a375dc390dee2e504db5b9bf49a9f7eacf9a00511d8bf6d6136c5132d8febea5`：destination为空，原628注册身份不变，原627物理文件大小/SHA逐项与完整backup一致，dirty为空。

主UE正常退出后的neutral v2实际`victorian_primary_move_v2.json`记录native_api_return/rename_returned/save_returned=true，627个primary对象官方rename携带内嵌BuiltData，目标628身份；该move仍success=false/status=renamed_pending_verification，保留为中间回执，不改成整体成功。原13个旧root dirty包随后正常退出，fresh检查`victorian_exact_residual_check_v2.json`success=true：628身份/两图及relative一致，旧13形成无外部引用闭合集、新目录无旧根依赖。

`victorian_exact_real_duplicate_cleanup_v2.json`记录官方仅删除精确13旧真实对象，每项返回true；实际仍有2个旧registry对象和1个已删旧包dirty，不能把delete返回值等同旧根清零。`victorian_exact_offline_cleanup_precondition_v2.json`绑定检查/官方删除SHA，并仅许可discard已删除mi_flag_a_unique旧包；实际磁盘只余mi_flag_a_unique、pa_flag_a、skm_flag_a三个文件，其他十个已由官方删除落盘。正常退出后`victorian_exact_offline_cleanup_v2.json`在editor_process_count=0时仅删除这三个literal残留，逐文件当前SHA/原backup pin保留，不写为离线删除13。

fresh正式`verified_VictorianStreet_vrecovery_20261013_v2.json`success=true，628资产/两图、differences/dirty为空、旧根0，SHA`dcaba5b90bac7dd21903c2e4a2e643f24c10c9f77a1e06934bdd0e211ce6a90e`；raw资产记录仍包含`/Game/Scenes/VictorianStreet/Maps/Showcase` package下`Showcase_BuiltData`（`/Script/Engine.MapBuildDataRegistry`），内嵌对象身份完整，不单独二次迁移。正式发布见`publish_medieval_victorian_v2.log`，原首次取消与v2中间失败状态保持历史原样。


### 13.19 Medieval八旧纹理清理、实机水体合同验收与本批发布（2026-10-13）

`medieval_exact_residual_check_v2.json`success=true：516新身份完整、Castle实际图及relative严格验收，精确八旧TX无外部引用、新目录无旧root依赖，完整实时water_name_witnesses保留。`medieval_exact_real_duplicate_cleanup_v2.json`官方只delete这八旧真实对象，每项返回true、remaining_source_assets/dirty_after为空；`medieval_exact_offline_cleanup_precondition_v2.json`绑定检查SHA`34feb119ba89dbb0e7d4ee6d3a885af6e2e43f94f1376f7652e69952e36391c1`及官方删除SHA`96dde9c0eb144e9f0e4e9fb752960e261f787fd8de18834a00cb4bb46ee46788`。`medieval_exact_offline_cleanup_v2.json`在无Editor进程时仅清理八个literal物理残留，当前hash及原始backup保留，不扩展为通用旧根删除。

fresh正式`verified_Medieval_Environment_vrecovery_20261013_v2.json`success=true，516资产/一图、differences/dirty为空、旧根0，SHA`a195433883b4d057d9b7a347297dbe9151283c119d7aaf3fae82716b2e2e53ff`；其中一份实际`water_name_witnesses`含完整当前水体几何、材料、descriptor、身份、source/engine pins与生产模块SHA。raw地图记录仍保留WaterInfoMesh_6，只有有限比较副本对应原WaterInfoMesh_3，原baseline及失败历史未改。

`publish_medieval_victorian_v2.log`记录Medieval/Victorian本批正式发布，overlay两份正式receipt SHA与文件一致。下一批`batch_scifi_hong_futuristic_v2.log`首次启动记录Scifi_building_Bundle/Hong_Kong_Street/FuturisticMetaCity及driver lock；随后因Future恢复停止，Scifi/Hong已正式verified并独立发布，见§13.20。仅启动/baseline或native移动不计正式验证或发布。整体剩余根与EditorViews恢复尚未完成，所有原backup保留到全scope闭合及用户review；相机R02/R05与原goal保持暂停，皮肤独立范围保护。精确动态总量由Status/STATE拥有，不能把本批正式通过写成完整场景整理完成。


### 13.20 Scifi/Hong正式验证及发布与Future引用恢复（2026-10-13）

`verified_Scifi_building_Bundle_vdriver_20261012T202443972376Z_verify_Scifi_building_Bundle.json`正式success=true，684资产/三图，SHA`90e48237d44b7b18480f22e998655610c7de7832950ea1df63e6cd6f3afeefe7`；`verified_Hong_Kong_Street_vdriver_20261012T202634213643Z_verify_Hong_Kong_Street.json`正式success=true，684资产/两图，SHA`7c36433ec3e929b45d3ba5f8220821a3386eb9ff0fc289c31a651af19bd45a71`，两份differences/dirty为空。三根driver批次因Future恢复停止，两根随后由publish_scifi_hong_v1.log独立正式发布，Future仍待恢复与整根验证。

Future native已移动903身份，额外旧包保存失败，不计verified。`futuristic_partial_identity_inspection_v1.json`记录唯一F_Struct_Alphabet原/实际registry类路径差异，package/name一致，官方类型映射见§13.21。`futuristic_original_missing_dependency_ar_diagnostics_v2.json`在隔离完整原源上只查Asset Registry，success=true/source903与原/backup SHA不变，asset_or_map_loads=0；原包本来缺四资源、八依赖边，不能归因为移动丢失。`futuristic_old_reference_inspection_v1.json`记录目标仍有三条旧缺失纹理路径依赖；AR诊断明确exact_three_witness_accepted=false，不接受stale路径例外。

随后独立三材质references-only v2实际强制保存均返回true、完整公开before/after值一致，但三旧缺失纹理依赖仍在，整体receipt success=false，最新事实见§13.23；原源公开owner采集与整根地图恢复仍pending。不以原源缺失诊断替代真实地图结构验收，不新增通用missing-dependency忽略。原backup及所有失败/候选receipt保护，camera仍paused。

### 13.21 第二个精确官方registry class alias（2026-10-13）

本节补充生产`00_engine/scripts/unreal/ue_scene_folder_organization_v1.py`及生产测试`00_engine/scripts/unreal/tests/test_scene_user_defined_struct_alias_v1.py`的Technical owner；helper在本节检查点SHA`eae640ee12f0c5a07719f169eea1e7065a06ad4bfc6a50e567e51bca1c620429`，此前水体整合SHA`3a3dc330088b3bc12d40ad3b0ddcb18db5fa848f1e6bd7260b973a7b3a3bbbfd`已归档`relocation_helper_before_struct_alias_v1.py`。当地UE5.8.1 CL56057345官方`BaseEngine.ini:1326`明确`+ClassRedirects=(OldName="/Script/Engine.UserDefinedStruct",NewName="/Script/CoreUObject.UserDefinedStruct")`；ini SHA`dc5b359ee95ccff0ccdfa4181b2875451b4a33474c0bb896fd8fef23aed1bf8e`及Build.version SHA`d35d3d5f4de0636fbb62386b63dee8056889fb2baf199d012dc32ee77f7a2997`仍与§13.10相同。

`USER_DEFINED_STRUCT_CLASS_REDIRECT`记录完整old_name/new_name、source/section/source_line/declaration/source_sha256、engine_version/build_source/build_sha256。`canonical_registry_class`只允许此UDS及既有MRQ两对完全限定registry asset class路径；package/name、地图Actor/component类、材料/几何比较不放松。`class_redirect_witness`仅原始记录用到旧类时逐项校验官方声明与ini/build SHA，输出至`canonical_class_aliases`；`raw_original_asset_records`与`raw_asset_records`保留原类路径，原baseline/history不改。

`struct_alias_integrated_tests_v1.xml`/`.log`实测31focused tests通过，failures/errors/skipped=0；覆盖新增UDS与既有官方class alias测试。这是有限类型合同回归，其本身不代表当前helper完整回归；后续1509全回归证据见§13.24，不冒充旧1247回归，也不证明Future地图/引用/旧包清理或正式迁移通过；该正式门槛仍独立pending。


### 13.22 Kyoto native迁移后Showcase有限枚举差异候选（2026-10-13）

`move_KyotoAlley_v1.json`native rename_returned=true、dirty_after_rename/save为空，755身份/四图候选已移动；原move仍success=false/status=renamed_pending_verification。`verified_KyotoAlley_vdriver_20261012T211827402688Z_verify_KyotoAlley.json`正式success=false：资产755、地图四张、dirty为空，只有Showcase before/after actor_count均533但结构比较失败，失败receipt SHA`85cabb50c3d0dedf046ff000202a5b04e65325eff645c563b8644535a85f667a`保留不改。

TEMP `kyoto_showcase_exact_actor_tie_contract_v1.py`及`test_kyoto_showcase_exact_actor_tie_contract_v1.py`在该检查点为纯比较候选，本节拥有其诊断边界，当时未生产集成/未验收；后续正式代码集成见§13.30，整根实机验收仍独立pending。`kyoto_showcase_exact_actor_tie_offline_analysis_v1.json`success=true、ue_operations/production_modified=false，15测试通过：限定三组固定同名同class pair的原始完整记录双射，仅枚举次序差异，保留其他533 Actor全部字段与loaded-level次序。实际actor值/类/名称/材料/未知字段、非限定重复组、其他transform/mesh/instances改变均拒绝；不全局排序忽略同名冲突。原schema未保存owning-level不能推定Day/Night归属；正式失败receipt没有relative差异，候选不改relative检查。候选15测试不算Kyoto整根verified，不提高发布计数。

### 13.23 Future强制保存失败边界及其余原源准备（2026-10-13）

`futuristic_exact_three_material_force_save_v1.json`在Showcase地图严格比较失败，saved为空、success=false，历史保留。独立`futuristic_exact_three_material_references_only_v2.json`仅处理三材质包序列化：三个official save_only_if_is_dirty=false实际returned=true，完整公开materials_before/after相等，903原始目标registry保持；此阶段maps_not_loaded=true/maps_verified=false。三旧缺失纹理依赖仍在，整体success=false/error明确old-root dependencies persisted，missing_reference_exception=false。不以保存返回true或公开值相等认定旧引用修复、原始地图差异接受或Future整根发布；原源公开owner隔离采集与完整地图恢复仍进行中。

`baseline_PostCity_v1.json`success=true，原1200身份/两图建立、尚未move。TEMP `desert_primary_package_move_proposal_v1.json`钉住原629文件/backup SHA前后不变，627 package-primary候选加两原始placeholder metadata、16外部地图capture已准备；四独立BuiltData身份继续严格，候选不是退休metadata授权，也不是实际move成功。当时Desert未迁移；随后627primary首次native部分失败已完整回退，最新安全检查点见§13.26，仍未verified。

`brushify_original_missing_dependency_ar_witness_v1.json`与`brushify_original_public_owner_witness_v1.json`均success=true：原198注册资产，15 missing meshes与14个公开owners是原有不完整来源包事实；原source/backup SHA前后不变、未保存source、dirty为空。AR阶段不load资产/地图，公开owner阶段只load14 owners，map_loads=0/strict_map_baseline_captured=false；不把来源缺失视为迁移损坏，也不自动接受缺失引用或跳过全地图Gate。Brushify整体目录边界授权保持，实际迁移仍未执行。

### 13.24 当前生产全回归检查点（2026-10-13）

`workflow_tests_v3.xml`/`.log`完整documentation/dataset/unreal三个tests目录实测1509 passed、failures/errors/skipped=0，JUnit534.612秒、日志534.65秒；对应生产helper SHA`eae640ee12f0c5a07719f169eea1e7065a06ad4bfc6a50e567e51bca1c620429`。该代码已包含Kowloon、MRQ/UDS、Japanese、Urban及Medieval有限合同；当时尚未生产集成的Kyoto TEMP tie和Future候选不在此接受范围；§13.30后续生产集成及本轮generator修改均晚于该完整回归，不宣称1509已覆盖新代码。原v1环境失败/v2旧1247全回归保持历史，v3不改写它们；测试成功不代表未完成六根场景或最终文档/catalog审计完成。

### 13.25 最终一次文档与catalog收口影响清单（待root执行）

1. 先逐根对齐实际formal receipt、overlay SHA与当前registry身份/地图/引用Gate；明确源码缺失和已验收迁移的边界，任何TEMP候选只在真实集成与对应tests/实机Gate完成后晋级。Kyoto/Future失败原receipt、完整baseline/history与backup继续保护。
2. Script Catalog需核对本Technical owner下`ue_scene_folder_organization_v1.py`及UDS/MRQ/Japanese/Urban/Kowloon tests、独立`ue_medieval_water_contract_v1.py`与test_medieval_water_contract_v1.py，以及driver/path-relocation/EditorViews helper。当前production SHA以最终实际工作树为准；已归档57ac/3a helper是历史证据，TEMP tie/primary proposal不是production。
3. Output Inventory核对ORG新增formal/failed/candidate/cleanup/public-owner/回归receipt与旧helper archive的生产归属及保护状态；TEMP可重建候选仍为TEMP，不能因存在输出或测试通过升格接受，也不据文档引用自动长期保留。完整original backups保留到全scope闭合与用户review，清理需单独授权。
4. 五owner同步精确verified/published分数与下一动作，Registry只反查当前authority，原历史source路径和SHA不覆写；独立检查Technical/Status/Plan/Validation/Output/Registry定义与明确跨层合同，再由root统一重建catalog/Inventory及运行总审计。本轮仅窄事实/链接检查，没有执行这些收口动作。
5. R06整scope Gate、EditorViews恢复（全部24根通过/driver结束/主UE关闭）与最终文档审计完成后方可关闭R06；相机R02/R05及原goal保持暂停，不能因目录整理收口自动完成父current计划或恢复拍摄，皮肤独立会话owner不改。


### 13.26 Desert首次部分迁移失败与完整原源回退（2026-10-13）

首次627-primary native返回false，`desert_native_partial_ar_v1.json`只读记录old197/new626：缺原World `Maps/DesertGasStation_01`及原`Maps/LayerInfo/AssetsShowcase_01_BuiltData`，多`Maps/AssetsShowcase_01_BuiltData` canonical身份，不是628或629完整验收。TEMP `desert_native_partial_readonly_analysis_v1.json`绑定原629完整backup/16外图SHA、原四个独立BuildData及官方engine source，确认官方World携带attached BuiltData自动canonical重命名行为；先迁独立canonical BuildData使后续World关联LayerInfo BuiltData目标冲突。该解释结合实际身份与官方代码，未读取protected PersistentLevel指针、未instrument确切内部失败分支，不夸成内部指针实测。

`desert_offline_rollback_precondition_v1.json`精确审计当前old/new两根799文件、完整629 restore列表与16外图未改，并绑定只读analysis SHA。`desert_offline_rollback_v1.json`success=true，SHA`f0416e4eeba9daa7fd24464a9010a1d17fbdb24cbc1b651bae18d28d2d9f96a3`，完整原629文件恢复、16外图unchanged，799部分结果存于TEMP `quarantine_desert_native_partial_v1/`可恢复；没有删除部分失败历史或丢失原资产。

从完整原源安全检查点拟先移动一个World，再把其精确linked BuiltData回到原LayerInfo相对位置，之后分阶段其余primary迁移；TEMP `staged_desert_world_first_move_v2.py`/`test_staged_desert_world_first_move_v2.py`为候选，后续`move_DesertGasStation_staged_v2.json`已执行后实际status=failed_requires_inspection/success=false，remaining623阶段TEMP validator报告raw checkpoint身份不符；后续确认是旧redirectpackage转译方向错误，不能据此称native迁移本身失败；16外图修复与新Showcase引用待fresh检查点见§13.30。此前eae640执行pin是实际执行约束；任何新生产helper版本必须建立单独审核的执行pin，不能把v1 pin降为历史描述后直接复用。Desert不计verified/published，backup与隔离799保护。

### 13.27 Future公开child yaw及精确soft路径未闭合（2026-10-13）

`futuristic_exact_sign_yaw_restore_attempt_v2.json`仅精确`ShowcaseMap:PersistentLevel.BP__Building_Shop_B__2.BP_AlphabetSignMaker`的child-root rotation恢复：live yaw到0且地图save_returned=true，但正常reload后child-root yaw约90.0000076，persisted_public_row_equal_source=false、success=false。未扩大到同名子Actor或其他轴/其他层级，不以live修复/保存返回true认定持久化正确。

`futuristic_exact_soft_path_relocation_v1.json`只在三个精确材料package通过官方soft-path重写两个完整原/目标`T_SciFİVideo`/`T_SciFİVideo2`对象路径（原始U+0130保持，不用Unicode替代猜路径），force-save_only_dirty=false返回true；操作安装了session redirects，因此必须fresh持久化验收。立即Asset Registry仍有三条旧依赖，整体success=false/maps_verified=false/formal_scene_verified=false/missing_reference_exception=false，原source/target公开材料记录保留。随后fresh AR六类依赖旧根均0，证明soft重写已持久，见§13.29；两个完整地图/owner与yaw持久化仍待验收，不把候选session状态认定已清理或已发布。

### 13.28 只读独立文档审计与最小收口修正项（2026-10-13）

本轮按用户授权运行`python 00_engine/scripts/documentation/check_character_factory_docs.py --json`，未重建catalog/Inventory，exit1/success=false，7errors/0warnings。检查快照在本轮后续事实文档更新前：14独立子系统通过，Output因Inventory缺476 direct scopes/含1不存在scope失败；Technical因Script Catalog缺317 scripts、`scene_folder_batch_driver_v1.py`及`ue_scene_folder_organization_v1.py`的bytes/SHA各stale失败。cross_layer单项success=true不弥补两个独立子系统失败，不能接受总闭环。当前1509全测试通过与本次文档/catalog失败是不同Gate。

该只读审计轮仅列本scope最小修正列表，未修改生成器、catalog、registry或其他会话owner；后续用户单独授权的限定generator owner修正及8测试见§13.29，真实catalog/Inventory仍未重建：

- 审计时`build_script_lifecycle_catalog.py`的owner_for错误fallback需把`ue_medieval_water_contract_v1.py`、`test_medieval_water_contract_v1.py`、`test_scene_user_defined_struct_alias_v1.py`明确映射到本Technical；该审计时只读调用生成器实际落到CHARACTER_RUNTIME.md；后续精确owner mapping已修好，见§13.29。本scope新增`test_scene_official_class_alias_v1.py`、`test_kowloon_redirector_retirement_v1.py`、`test_japanese_redirector_retirement_v1.py`、`test_urban_material_relocation_v1.py`也须依已有明确Technical owner核对相同fallback，不能顺手修改角色Runtime内容。
- 当前catalog实际缺上述水体模块/测试与UDS测试项，driver/helper大小/SHA旧；按最终实际工作树重建这些机器条目，保留限域validated_pilot/utility或审定生命周期与未启动camera语义，不以production已整合推导全资产/拍摄接受。
- TEMP京都tie、Future soft relocation、Desert staged候选按已有路径生命周期规则处理；本次限定修正只改精确owner映射，未改生命周期规则，更不强制production。validated_pilot等机器分类不代替当前pending/失败实证边界，不能以分类提升候选接受状态；测试/纯只读诊断及实际运行证据保留各自范围。不得用整个TEMP目录通配规则统升accepted或清空失败历史；原source/backup SHA、候选SHA、producer/helper实际执行SHA与官方engine pins保持最小可重现链。
- 水体正式module只依赖固定ORG receipts、原backup和引擎源码pins，不依赖TEMP采集器运行；但原backup/current cleanup pins及Future/Desert TEMP候选仍被活跃诊断引用。原57ac/3a helper archive是历史记录，不改成当前production；临时重试脚本如要求helper=eae必须新版本重审，不能静默改旧receipt/pin。
- 317脚本/476输出全量缺项不可归因为本module，也不能据此删除其他scope；root最终Inventory应归类本ORG新receipt/失败/回退/quarantine与TEMP候选的所有权、保护/可重建性后处理完整受影响清单，再分别复核Technical/Output独立闭合与跨层结果。以上只是最小修正清单，本轮未执行最终closure。


### 13.29 限定generator owner修正与fresh进度（2026-10-13）

用户后续明确授权只修改documentation generator限定owner mapping及相关tests。`build_script_lifecycle_catalog.py`的owner_for新增九个完整relative path到本Technical：现有`00_engine/scripts/unreal/ue_medieval_water_contract_v1.py`及tests下`test_medieval_water_contract_v1.py`、`test_scene_official_class_alias_v1.py`、`test_scene_user_defined_struct_alias_v1.py`、`test_kowloon_redirector_retirement_v1.py`、`test_japanese_redirector_retirement_v1.py`、`test_urban_material_relocation_v1.py`，另预留`00_engine/scripts/unreal/ue_kyoto_showcase_tie_contract_v1.py`与`ue_futuristic_public_owner_contract_v1.py`精确名称映射。修改时两个预留module尚不存在，映射不是生产集成或候选接受证明。

`tests/test_build_output_inventory.py`新增同basename其他scope/不同版本不误归属、既有生命周期不升级及隔离fixture catalog只列真实文件不按预留名字造条目检查；`catalog_owner_mapping_tests_v2.xml`实际8passed、0failures/errors/skipped。这是既有相关test文件完整focused run，没有运行真实全catalog/Inventory生成或改变lifecycle_for规则；原1509全回归早于该generator修正，8专项结果不冒充新完整全回归。真实清单与最终独立审计仍待root正式code冻结后统一收口，不触碰角色Runtime/皮肤owner。

`futuristic_fresh_ar_dependency_categories_v2.json`success=true，903目标身份、dirty为空，在fresh会话before scene asset/map load对all/hard/soft/searchable/soft_manage/hard_manage六类查旧root依赖均0，SHA`136fce2aefd0bbdc3f7f46773c019acf6ea65af40509eab33d4afe754f8f1b8a`。这证明精确三package soft路径重写已落盘，之前立即AR旧三条来自loaded会话缓存；原失败receipt不覆写。此AR Gate不包含两个实际地图/sign yaw持久化接受，Future仍未verified/published。

`move_DesertGasStation_staged_v2.json`执行后实际status=failed_requires_inspection/success=false，绑定新候选SHA及当前helper执行pin，remaining623_no_world_no_linked_bd阶段TEMP validator报告raw checkpoint registry identities differ，此失败receipt保留；后续root确认新627/四BuiltData严格完整、失败为TEMP旧redirectpackage转译方向错误，最新实际引用Gate见§13.30；原首次失败/629恢复/799隔离历史仍保护，不将原恢复检查点冒充当前live root完整状态。当前发布计数保持不提高，camera R02/R05及原goal暂停。


### 13.30 Kyoto/Future有限合同生产集成、代码pin与当前引用Gate（2026-10-13）

`finite_contracts_production_integration_v1.json`实际success=true、ue_mutation=false，SHA`d4f4b40198953525c4485ebff62e29352b5e386c172a718f15ccdc706a7480ac`；本轮独立核对五个生产文件实际SHA与来源候选字节全一致。本Technical拥有以下生产入口/测试，文件集成不等于场景整根验收：

| 路径（Lance_Work相对） | 当前集成SHA256 |
| --- | --- |
| `00_engine/scripts/unreal/ue_scene_folder_organization_v1.py` | `7e92c8a0eb32711d58b0043440dd14b02b4443abf09e4a0ac9241a6a83c424be` |
| `00_engine/scripts/unreal/ue_kyoto_showcase_tie_contract_v1.py` | `6fe1ea04a69592ff101626496709305f8b53c20fd934f5b5a45f93f26a0c8d07` |
| `00_engine/scripts/unreal/ue_futuristic_public_owner_contract_v1.py` | `8eb7cf849eb863c0d49a2dd7badbf9963758bf923b269f2287235f3823b1c05f` |
| `00_engine/scripts/unreal/tests/test_kyoto_showcase_tie_contract_v1.py` | `0c1dff99d6468d916a70c910a77fa925e4f2648b7cfe18d61f5cb812f8ccc631` |
| `00_engine/scripts/unreal/tests/test_futuristic_public_owner_contract_v1.py` | `76351928d1866dd493e25e438744ccb8052aa29aa0a68eb983581feab793c2c6` |

helper的`finite_map_comparison_signature`在既有Urban/Water处理后、普通完整`compare_map`及`compare_component_transforms`前调用。两个module以相邻生产路径、精确代码SHA及导入文件路径检查绑定，重新加载后返回比较副本；正式receipt的`maps`、`component_transforms`仍保存raw实际采集，新增`finite_map_comparison_witnesses`，含expected_contract_sha256，`current_production_helper_sha256`记录本次实际helper。既有`water_name_witnesses`和raw registry/class alias字段保留；泛化比较函数未放松。

Kyoto仅原755/4不可变baseline SHA`9a2c02668d75f5119ddf8fdb0865c79e4aa3392747bb4a9094e2222ff7640a51`中的Showcase533 Actor三组固定同名同class二元完整记录允许双射枚举换位。原/实际索引、完整actor内容必须唯一匹配，比较副本全部递归JSON与原Showcase精确相等；无数值容差、字段省略、泛化排序或其他地图例外。relative仍普通全量严格比较；原捕获未存owningLevel，不推定Actor归属。witness保留permitted_groups、raw/comparison map SHA、contract路径/SHA、ownership_limit。原正式失败receipt不改，本轮只确认生产集成，未宣称Kyoto正式success。

Future合同绑定不可变baseline、原903完整source/backup witness、隔离原源两图公开owner witness及官方ChildActor/Camera/SceneComponent/Actor源码与Build.version SHA。`futuristic_generated_ownership_source_v2.json`实际success/source/saved_assets=false，SHA`52b3b97cbdb8e6556c19235750ffbbb5d4bf984bc3d490eb8a9d2507c4f1db7c`；`futuristic_original_missing_dependency_witness_v2.json` SHA`0d00d650c5f43123607b36cf840d284d730656d6063d20e3180585725766a989`。先证明原公开采集全signature/relative与baseline严格一致，再读取当前公开父子/相机attachment身份，仅14个原公开parent范围与一个相机attachment的具体运行时生成名称允许映射。transform/几何/材料/relative全部原值保持，不猜allocation编号、不调yaw、不读取private ChildActorTemplate/ActorOuter/native flags，不放宽原缺失引用。witness保存satellite_pairs/camera_pair、current_public_ownership_raw与原source/baseline/full903 SHA；两个实际地图与全引用/旧根/dirty Gate仍必须独立通过，Future尚未formal verified。

documentation generator再补两个完整测试relative path到本Technical，精确映射共11条；`catalog_owner_mapping_tests_v3.xml`实测8passed、failures/errors/skipped=0。隔离fixture覆盖两个新增真实test文件、同名其他scope/其他版本不误归属、映射不造不存在文件、生命周期不提升。没有运行真实catalog/Inventory生成；v2八测试、此前1509完整回归仍保留各自代码检查点，均不冒充本次新合同完整回归或实机通过。

Desert staged新627实际资产/四BuiltData身份严格完整，五次native返回true，旧206来自有限原627（182primary+24generated/default）；先前remaining623失败是TEMP validator旧redirectpackage转译方向错误，原失败receipt保留。`desert_exact16_external_reference_repair_v1.json`completed=16，本轮逐行核对16张外图before/after完整signature及component transforms全部精确相等，实际保存完成；SHA`12709fc43117e510727a401a5285cd315b7a182495931ed2ae06007d7e2110c6`。整体success仍false，因为`desert_after_exact16_external_ar_v1.json`旧206的117 outside-reference项仍指向唯一新Showcase，16外图旧refs已零；该AR SHA`78d8a42fe6b0dd21f0a1f957914b8abbed6c0b0baf20184b86e9f30e70d6bd05`，dirty为空。root正常fresh重启检查持久状态，不以外图成功或native返回提高正式计数。

保留规则：不可变baseline、原完整backups/外图backups、原正式失败/立即缓存诊断/后续fresh proof、精确source/public-owner/engine pins与代码集成回执构成可重现链，继续保护到全scope闭合及用户review。旧eae640归档SHA由集成receipt记录；57ac/3a旧helper档案、Desert799 quarantine及未分类输出保持保护，历史SHA不能改为当前代码。两个生产module运行读取固定ORG原证据/官方源码，不执行TEMP候选或采集器；TEMP候选源、测试树与可重建中间文件仍按既有路径生命周期区分，最终清单审查后再按授权清理，不整目录统升production或默认删除。真实catalog/Inventory及最后独立审计仍由root代码冻结后统一执行；该集成检查点正式18verified/18published不变；后续真实21发布见§13.31，R06与父计划未完成，EditorViews未运行，camera及原goal继续paused。


### 13.31 Kyoto/Future/Desert正式通过与21项发布检查点（2026-10-13）

`publish_kyoto_future_desert_v1.log`实际guard后串行发布三项，2026-10-12T22:40:04.363261Z成功。overlay SHA`7accddbcd921926c4124f36aee4f871c8acd44eaef7ba28d3ca863cf2c7408fe`；本轮独立逐项读取21个overlay所指正式receipt并核对SHA、success=true、differences/dirty为空及实际地图数量；另核对新增三份raw maps/component_transforms完整，求和21verified/21published、9756资产/48图，剩三根。不是从native返回或候选累计推算。

| 正式receipt（ORG相对） | 资产/图 | SHA256 |
| --- | --- | --- |
| `verified_KyotoAlley_vfinal_precleanup_v1.json` | 755/4 | `691208308f705b96b59912581a16634b7a9e236037a2e904ed42efd74a98a3a7` |
| `verified_FuturisticMetaCity_vfinal_clean_v1.json` | 903/2 | `0264ab69056e0160859fa3902d1d4231bee0ad023de4b73a095f64fc83b10a59` |
| `verified_DesertGasStation_vfinal_clean_v1.json` | 627/2 | `dcf1a95585647f1724acbcdc38950625e4dbac90005315d7428a64ba732b8915` |

三份formal success=true，raw实际地图及relative完整保留，有限比较合同witness按§13.30输出，当前helper7e92代码pin保持。Kyoto原533 Showcase仅三固定完整记录tie换位，Future精确公开owner生成名称映射后仍全signature/relative严格；先前failed receipts保持失败原值，不用formal成功覆盖原诊断历史。它们现在已正式通过并发布，§13.30的pending只属于此前代码集成检查点。

`desert_exact_showcase_reference_refresh_v1.json`success=true、asset_renames为空，仅保存新`Maps/AssetsShowcase_01`，candidate SHA`483de6f1282e14b82325708594db1c9f1d5d9408125cdaaefa2d58df17cc9655`；receipt SHA`7997c1afd9b45d9485dbcdaa53d2de7c7af3fc16626419047355ed839d3e0bed`。两图actual before/after完整signature/relative精确相等，119/879 Actor；其余626目标文件及16外图SHA保护。fresh_after target_old_dependencies为空，原117项新Showcase旧边已闭合；先前completed16但success=false的整体repair/AR原receipt保留，不能倒写为成功。后续final_clean正式再次从磁盘接受627/2。

Future和Desert分别使用`closed_original_root_FuturisticMetaCity_preconditions_v1.json`及`closed_original_root_DesertGasStation_preconditions_v1.json`验证完整原backup、all-category旧包引用闭包、目标不依赖旧根、限定旧dirty边界，再于主UE关闭后按PowerShell literal精确删除原旧文件。`closed_original_root_FuturisticMetaCity_offline_cleanup_v1.json`success=true，67文件，SHA`c39663112eea524e1f2f1768a8c180a1ebcbc3368b95ecd54eb254966f979cb3`；Desert对应cleanup success=true，184文件。两份receipt均editor_process_count=0、new_root_full_files_unchanged/full_original_backups_unchanged=true；fresh正式验证old0/new完整。此清理只覆盖两个已闭包旧根，原完整backups/外图backups和失败历史仍保护，不是通用其他目录删除授权。

`baseline_Brushify_v1.json`success=true，SHA`ba7eaccccdd0090b1373a5cbda26f2edf54401ae8467eda601d7c8784649384d`，原198身份/一图严格source baseline已建。原15missing meshes/14公开owner来源诊断保留，不把它们改成迁移丢失，也不以来源缺失放宽后续地图Gate。Brushify尚未move；PostCity原1200/2 baseline已建未move；Japanese content-v3当前由root串行UE执行，尚无结果，不提高21计数。

`workflow_tests_v4.xml`实际1545 cases、1544passed/1failure/0errors/0skipped，唯一`test_input_lock_is_reusable_and_contains_no_windows_file_uri`的fallback-graph fixture失败，文件为`tests/test_run_first_batch_render_jobs.py`；保留失败回归原receipt。root仅将fixture暂存改为repo内TEMP，报告该test文件12项在系统TEMP场景通过；runner/有限合同生产代码未改。新全回归v5正在跑，本轮未见完成XML，不宣称pass；v3旧1509与v4失败均保持独立历史。

### 13.32 最终收口填写合同（待全部根与代码冻结，当前未执行）

最终只在root得到真实证据后填写：①overlay所指每项正式SHA、verified/published根数与实际资产/地图求和、所有剩根旧/新身份和地图/引用Gate；②最终生产helper/独立合同/driver/相关tests工作树SHA与完整回归receipt结果，失败/重试历史不删；③EditorViews恢复前置全24根通过、driver结束、主UE关闭及实际恢复receipt；④root统一生成真实Script Catalog/Output Inventory，按独立Technical/Output/Status/Plan/Registry合同运行文档审计并报告各子系统，不能用cross-layer成功代替独立失败；⑤backup/quarantine/source witness与运行时engine pins当前引用、保护范围及任何清理另行授权/用户review；⑥R06收口证据和父计划仍current、R02/R05/camera及原goal暂停边界。

当前以上为待填条件：尚未24根/最终完整回归/EditorViews/机器清单与总审计完成，R06继续in_progress，不执行promotion、不关闭父计划、不自动恢复相机，皮肤独立会话owner保护。

### 13.33 Brushify正式发布与22根检查点（2026-10-13；最终收口pending）

`publish_brushify_v1.log`实际guard后发布Brushify成功；当前overlay SHA`3799e1ddeaef69ab79b4d9702d7cf8d5535035ee291fa8e63052c3a998a2f574`，状态仍in_progress。以下22项均直接读取overlay所指formal receipt，独立核对文件SHA与overlay pin一致、success=true、differences/dirty为空、map_count与raw实际maps数一致；求和9954资产/49图、22verified/22published。原地图与component_transforms保留在formal receipt，本表不替代全项目最终引用审计。

| 根 | 资产/图 | 正式receipt（ORG相对） | SHA256 |
| --- | --- | --- | --- |
| `Synthwave_city` | 223/2 | `verified_Synthwave_city_v2.json` | `0bdae46e9569fcb40c515912d2138f365326042a5953808a6b66013244a160d4` |
| `racing_track` | 136/1 | `verified_racing_track_vdriver_20261012T160703510691Z_verify_racing_track.json` | `f585c07c093438166d106abe0dbf527f3fb5f2c3e40dedac0df0f8a8a6b3e8f0` |
| `AsianArchitecture` | 151/2 | `verified_AsianArchitecture_v3.json` | `9541651831267413a11f75c26f49accb962ccad3a95a5006e1b85deec985e123` |
| `QA_ModularParking` | 234/2 | `verified_QA_ModularParking_vdriver_20261012T160853705279Z_verify_QA_ModularParking.json` | `acd194e008cc18c1274bbc310c1cf0e33f0add0d42186bc14c369c9e8c559ed4` |
| `RedDesertPack` | 251/2 | `verified_RedDesertPack_vdriver_20261012T161551249205Z_verify_RedDesertPack.json` | `b2c6bea4ba7cc91bedd4af80596a2b1260abf2298de70e01a1b99434c897173d` |
| `TheMetro` | 280/2 | `verified_TheMetro_vdriver_20261012T161645152326Z_verify_TheMetro.json` | `442be6276627b2ab90c2208b21a67f6acfd190d5ce4459795bd35c58bc21b326` |
| `Madeline` | 365/7 | `verified_Madeline_vdriver_20261012T164529239596Z_verify_Madeline.json` | `ca93b6dd3fca7ea719114a2401255f2eb59d69aaab571a26009781e3571d4082` |
| `AmusementPark` | 413/2 | `verified_AmusementPark_vdriver_20261012T165259650870Z_verify_AmusementPark.json` | `d879f49160b954c1fc7c6a12cd003c7f0696b24a623208bbf894ded691695644` |
| `CHERRY_TREE` | 416/2 | `verified_CHERRY_TREE_vrecovery_20261013_v1.json` | `4351935d4c91dc418be248af98190097f7f82012a2b95e6565a1a29f26dd973b` |
| `Kowloon` | 462/3 | `verified_Kowloon_vdriver_20261012T180001353254Z_verify_Kowloon.json` | `b3bd72811de00accd4d73cd4ede70e1b2859dfbee62f483c4d85372f18de2721` |
| `Cyberpunk_City` | 467/2 | `verified_Cyberpunk_City_vdriver_20261012T180729623059Z_verify_Cyberpunk_City.json` | `fb4394a6ed8cfc676bcb55f223f72a4f089ba72778f2bf03ab811974ad86f2cb` |
| `UrbanJapan` | 486/2 | `verified_UrbanJapan_vrecovery_20261013_v1.json` | `c84cd796b69f616dcc2aa69d1cfec499d6fa66647a057cfb5728ed29e7feba54` |
| `Evening_Highway` | 510/1 | `verified_Evening_Highway_vrecovery_20261013_v1.json` | `e52944af06c3c45fd7715224c89ac17c11256ab1a52df9e322ca9837d2dd5339` |
| `Seaside_Town` | 565/2 | `verified_Seaside_Town_vrecovery_20261013_v1.json` | `2675184eb59c99691094334a9a6ea8038db229da46dd46604cdd1870385aea1e` |
| `Medieval_Environment` | 516/1 | `verified_Medieval_Environment_vrecovery_20261013_v2.json` | `a195433883b4d057d9b7a347297dbe9151283c119d7aaf3fae82716b2e2e53ff` |
| `VictorianStreet` | 628/2 | `verified_VictorianStreet_vrecovery_20261013_v2.json` | `dcaba5b90bac7dd21903c2e4a2e643f24c10c9f77a1e06934bdd0e211ce6a90e` |
| `Scifi_building_Bundle` | 684/3 | `verified_Scifi_building_Bundle_vdriver_20261012T202443972376Z_verify_Scifi_building_Bundle.json` | `90e48237d44b7b18480f22e998655610c7de7832950ea1df63e6cd6f3afeefe7` |
| `Hong_Kong_Street` | 684/2 | `verified_Hong_Kong_Street_vdriver_20261012T202634213643Z_verify_Hong_Kong_Street.json` | `7c36433ec3e929b45d3ba5f8220821a3386eb9ff0fc289c31a651af19bd45a71` |
| `KyotoAlley` | 755/4 | `verified_KyotoAlley_vfinal_precleanup_v1.json` | `691208308f705b96b59912581a16634b7a9e236037a2e904ed42efd74a98a3a7` |
| `FuturisticMetaCity` | 903/2 | `verified_FuturisticMetaCity_vfinal_clean_v1.json` | `0264ab69056e0160859fa3902d1d4231bee0ad023de4b73a095f64fc83b10a59` |
| `DesertGasStation` | 627/2 | `verified_DesertGasStation_vfinal_clean_v1.json` | `dcf1a95585647f1724acbcdc38950625e4dbac90005315d7428a64ba732b8915` |
| `Brushify` | 198/1 | `verified_Brushify_vfinal_precleanup_v1.json` | `212685d6c828b4355c8120e2e055ee67ad2a4b3b029970d2a7a375e772fb237d` |

Brushify正式`verified_Brushify_vfinal_precleanup_v1.json`198/1、原baseline pin不变，当前helper仍`7e92c8a0eb32711d58b0043440dd14b02b4443abf09e4a0ac9241a6a83c424be`。fresh原根raw/files/dirty均0；`closed_original_root_Brushify_preconditions_v1.json`success=false，error为通用清理proof拒绝unknown old physical file或already cleaned root，此处实际已空，不需要删除。false原回执不改写；source/native/fresh既有证明和完整backup继续保护，不重新验证或覆写原始证明。

剩两未发布根：Japanese_Village内容615已native迁一次，原身份616含一原redirector；公开只读继续检查未有repair-save接受，前序v4编码失败是只读输出失败，无native/mutation。`japanese_original_cinematics_missing_v3.json`success=true、SHA`d33e2f03c245d73420ddae9afb284076f416a30eba26d2265eaeba993642b356`，原`Quick_Stills`/`Sequence_01`公开timeline捕获成功，缺`L_Showcase2`仅soft，未加载缺World/unused HDRI、未保存源，616完整source/backup前后不变。该source证明不替代目标23图、全部引用及正式验收。

PostCity原1200保持、native_call_count=0；两原legacy `/Script/PhysXVehicles.PhysXTireConfig`资产在主UE关闭时精确字节复制至Scenes，原/backup未改，目标只有这两项。`post_original_opaque_reference_closure_v1.json`success=true、SHA`930fec60e79de07054261188c967529c27d337067fa4829298af7b5db05f5712`；原WheelBack/Front Blueprint硬引用两资产，两World传递均可达，exact_two_unused_candidate=false，不能退休。copy后的4条旧PM依赖尚待有限兼容路线，当前未应用config、未native迁移，AR graph证明不宣称字面运行时字符串引用闭包。

Synthwave此前223/2 formal地图验收保持，最终引用Gate新增待闭合项：`synthwave_original_fence_ar_dependencies_v1.json`SHA`e2d5b85e42e52689a2f0f474507ba9be648be5091324b0937c2c7578b0badeee`success=true，原真实`Blueprint/BP_fence_spline`已有缺失naked `BP_fence_spline`soft边，原223/source/backup不变，无load/save。`synthwave_original_assets_relative_adjunct_v1.json`SHA`3d307e5e6057c69e8dc09f91e3aa7d3ebd3e3c1296f6e448ad5e5fb25321708c`success=true，原L_assets完整raw signature/relative补充已取得且source/backup未改；目标adjunct与最终引用接受仍pending。新Synthwave目录metadata1139字节经精确空引用检查、Editor0与literal备份后移除，receipt为`synthwave_new_exact_folder_metadata_cleanup_v1.json`；`new_scene_metadata_raw_registry_inventory_v1.json`另见CHERRY_TREE及QA_ModularParking两新metadata，仍待root审查清理，本次文档更新不授权删除。

`workflow_tests_v5.xml`独立逐testcase确认1545pass、0failures/errors/skipped；suite time405.652秒，`workflow_tests_v5.log`实际1545passed/405.68秒。v4 fixture失败与旧v3回归保留；v5覆盖当前代码检查点，早于下一次assembler编辑，不能作为后续代码变更的最终回归。当前生产helper7e92实文件SHA独立吻合；本轮仅文档与现有证据检查，未运行UE、改配置、重跑full pytest或生成catalog/Inventory。

R06继续in_progress、父计划current，R02/R05及原goal保持用户暂停，皮肤独立owner保护。§13.32最终合同仍pending：全24根、全项目引用/全局审计、EditorViews、gallery及最终catalog/Inventory与独立子系统审计均未完成；待root代码/输出冻结后统一生成机器清单和接受审计，不以22发布或v5通过代替最后闭环。backup/quarantine/source witness与失败回执保持既有保护边界。


### 13.34 冻结前文档独立检查与剩余闭合条件（2026-10-13）

先读实际 `documentation_pre_completion_audit_v1.json`：其历史快照152文档、599输出作用域、831 catalog脚本，15独立子系统通过，Output仅missing 1 direct scope，cross_layer通过但总success=false。随后本轮执行现用只读 `check_character_factory_docs.py --json`，exit1／success=false、17errors／0warnings：14独立子系统通过，Output缺635 direct scopes、含1不存在scope；Technical缺554 scripts，7个文件bytes／SHA均stale；cross_layer仍true。该新结果是执行时检查点，代码／产物继续变化后必须重查，不覆写旧回执或把cross_layer通过作为总审计通过。

本轮独立列举缺635项均在 `scene_folder_organization_20261012_v1/`，唯一不存在项为该Run的 `batch_driver.lock`。现有 `RETENTION_POLICY.json.ownership_rules` 已以精确该Run前缀绑定本Technical、WF-60和OUT-WF60-SEQUENCE-TEMPLATE；相机Run `camera_motion_scene_alignment_20261012_v1`也已有同owner合同。owner文件存在且直接说明两前缀，缺项是机器Inventory未随新产物重建，并非635项无owner。不新增retention／删除政策，不手改S／Catalog／Inventory或沿用旧计数冒称完成。七stale文件为documentation generator及其test、相机assembler及gallery test、scene driver／helper、first-batch render-job fixture test；最终按实际工作树冻结后重建，不在变化期间刷新历史pin。

已可先关闭的文档问题：现用链接／元数据／导航等14独立检查通过，无失败引用需要删除；[文档审计合同](../validation/DOCUMENTATION_VALIDATION.md#7-冻结后独立闭合检查单)已纠正“始终恰好一个current”的旧表述，使执行中唯一current与明确结项idle/null规则一致，并列出16独立子系统及跨层清单。此次修改不晋升任何UE／场景Gate。

root最终冻结后按以下顺序填写实际证据：

1. 逐根正式验收与overlay实际SHA／资产／地图求和，补齐所有剩根、最终全项目引用与dirty Gate；只读source／公开timeline／候选对比与native执行各保留实际边界，不能因拟议有限规则宣称通过。
2. 固定最终helper、独立合同、driver、assembler和测试的代码／输入pins；运行覆盖最后修改的相关完整回归，XML与log逐项核对，旧v5只覆盖其修改前检查点。
3. 全24根验收、driver结束且主UE关闭后，实际执行EditorViews恢复并核对receipt；gallery／current config／path consumer／全局引用另有实际验证，不以overlay存在替代消费端接受。
4. root统一重建真实Script Catalog／Output Inventory，核对实际文件集合、7stale／新脚本owner、Run现用scope和不存在项；既有精准ownership规则继续使用，保留分类与清理判断保持独立。
5. 依文档审计合同分别报告16独立子系统，再核验cross_layer；复核backup／quarantine／source witness／官方engine pins的当前引用与范围，保留旧失败回执，不混入另会话skin scope。审计时新增的正式证据scope也应纳入真实Inventory，不能重现“先建审计scope后忘重建”的漏项。
6. 同步R06及Workflow／Project机器状态与证据。现正式22／9954／49未变，R06in_progress、父计划current，R02／R05及原goal继续暂停；未获得各项真实结果前不填写最终总闭环，不关闭父计划、不自动恢复相机。

### 13.35 PostCity一次1198迁移、兼容恢复与fresh严格失败检查点（2026-10-13）

正式发布仍22／9954资产／49图，§13.33的22份formal表及其当时native0检查点保留历史；当前Post执行事实以下列既有实际receipt为准，不再按旧native0描述现live状态。

| receipt（ORG相对） | 实际结果／边界 | SHA256 |
| --- | --- | --- |
| `PostCity_exact_opaque_compatibility_content_v4.json` | success=false；native_call_count=1、submitted1198、native_returned=true；完整1200身份不符，禁止重试整根native | `41b39b799303f6bdc085050cd70937e648ffdb88af032adc97a5bc30dbb4af32` |
| `PostCity_single_native1198_continuation_v1.json` | success=true；无additional_native_calls/save/map load；只核验已迁1198，pending backup2恢复／config／fresh | `bd5bb70a7349efcf265e855fe510e97e38213e736558bca439bf279c5ed95aeb` |
| `post_exact_two_opaque_backup_recovery_v1.json` | success=true；Editor0只从保护backup恢复精确2个目标文件，原旧两文件仍不存在；不宣称opaque可加载 | `8539a3708fdcb694b667c7963b62b4351c8add5e8467cd3ae5648d81f8a2609e` |
| `post_exact_package_compatibility_config_offline_apply_v3.json` | success=true；Editor0实际应用两个精确PM package routes，整Config backup／before-after SHA保留；不是formal接受 | `fe722e2c70de4a8cc36a8b6185d28fc070d7762ba3f93bf4cd3d4dbf4a100c59` |
| `post_exact_package_compatibility_fresh_witness_v4.json` | success=false；当前1200／AR新4旧0／dirty0，公开PM/Wheel及原PM路径重定向实际验证通过；第一图严格差异失败，未验完两图 | `181283209dca20ba109327f64be355023b13ccd02cf948a5471c85a41c9ed71e` |

PostCity实际1198项已一次native迁移，原native receipt仍success=false（完整1200身份不符），后续continuation仅核验已发生状态、无再迁。Editor0从保护backup精确恢复两旧PhysX TireConfig至目标，已实际应用两个PM package routes；fresh-v4目标1200、公开PM/Wheel及旧路径加载验证通过，当前AR新4边/旧0、dirty0，但只捕获第一图即严格差异失败，错误“Full actual map changed; no geometry/name exceptions”，两图完整验收及Post formal仍pending。 原WheelBack/Front硬引用与两World可达证明继续有效，两opaque不是unused，恢复字节与原backup严格一致；旧serialized地址仍存在，实际AR重定向后新4旧0不等于原字节地址已清零。fresh-v4只读save/native/delete均0，opaque对象load成功未声称；原native false、continuation、恢复、config apply及fresh失败全部保持各自原值。

Japanese615内容已迁一次，原live旧raw331；保护的616完整文件是原backup及隔离冷源，不是现live仍616。两原Sequence缺L_Showcase2仅soft、公开timeline已取得；root当前v8有限修复执行中，结束结果与正式验收待真实receipt。 `japanese_after_public_readonly_actual_snapshot_v1.json`实际success=true、asset_saves=0／dirty0，old_raw331／target_raw615；616保护范围由原source receipt的backup和冷源证明，不推定原live完整。Japanese公开21项采集不代替23图／引用／保存重载及formal Gate，v8运行结果未接受。

本检查点只同步actual事实，不改S／Catalog／Inventory、不重跑全审计、不补写未知后续结果；仍按§13.34冻结条件关闭剩余独立及跨层检查，父计划不关闭、camera不恢复、skin独立owner保持。

### 13.36 Post重复几何、日本首保存与Fence即时AR失败检查点（2026-10-13）

以下只读取实际回执轻量字段、pin与文件集合差异，不打印完整raw exports，不执行UE。正式22表／9954／49保持§13.33原值，不宣称全24项完成。

| 实际证据（ORG或TEMP相对） | SHA256 |
| --- | --- |
| `ORG/post_current_construction_repeat_diagnostics_v2.json` | `13b6b471b9b3f8efc7beb9c9273a94ffb4d0f360b03e5d59d996f1198264d354` |
| `TEMP/post_current_construction_repeat_analysis_v1.json` | `6d84b13f6cbe4318f2688ae1f2469252f793faa3aa4feb5bcf69926fc20d308f` |
| `TEMP/post_current_hism_repeat_multiset_diagnostics_v1.json` | `19c040c149b2cc3023c56f627dcafed864e7b44286f5a2f7effca187e0f38fe7` |
| `ORG/japanese_exact40_reference_repair_v9.json` | `a060cde7c0061dda8b982ed57c32ea48b4fb5603f3be5d3be71cc0dde6cad727` |
| `TEMP/japanese_exact19_blueprint_transient_graph_official_source_v1.json` | `dc4754829133ea119122693401fadcc4dd80e3b113bc8a6ba37bd25a689c84ea` |
| `ORG/japanese_saved_first_blueprint_diagnostic_v1.json` | `eab408d2f16c20f7d030e9ecec6ca3eb1da91ba78cc6cdb7a490d9ec51b43f62` |
| `ORG/synthwave_fence_exact_navigation_soft_relocation_v3_failure.json` | `30da49db26e0b6b2c379a92253d16ca50e1bba712799ccb37ba324011631f27f` |

PostCity1198一次native、backup2恢复及2PM routes已应用，fresh1200/公开PM-Wheel/AR新4旧0/dirty0；current重复诊断完成，403 Actor世界变换与relative相同，但201HISM/74Actor/16classes完整实例集合真不同，order-only0。7BP/40公开图仅current前后相同，不是source-current等价；原source四次加载诊断仍待actual，不能接受19Actor几何例外或formal。 `post_current_construction_repeat_diagnostics_v2.json`success=true仅表示diagnostic_capture_complete，maps_verified=false／construction_compatibility_accepted=false；save/native/delete/manual_compile/seed_setters均0、dirty[]。TEMP analysis和multiset保留完整raw transform及数值hex比较，201组件完整multiset全部真不同，不能排序后掩盖差异。只读原source四次加载已启动，尚无actual成功回执；不能用current七BP前后相同推导source-current七BP或19Actor几何范围接受。

Japanese目标615/旧raw331，616仅原backup+隔离冷源保护；v9实际已保存BP_Bridge一次后公开缓存图比较失败，诊断确认仅该文件变化/其余614 SHA相同、dirty0，两个authored图EventGraph/UserConstructionScript保留。跳过首文件的v10剩20资产/19地图是后续未执行计划，正式23图/引用Gate pending，不重放首保存。 `japanese_exact40_reference_repair_v9.json`success=false、save_attempted=true、completed_assets/maps均0、error为“Public parent/CDO/template/timeline/geometry snapshot changed”，不能将计数0解释为没保存。`japanese_saved_first_blueprint_diagnostic_v1.json`success=true但自身save_attempted=false，仅核对首文件已发生delta及其他614不变。有限官方证据SHA`dc4754829133ea119122693401fadcc4dd80e3b113bc8a6ba37bd25a689c84ea`证明精确两个depth1生成EdGraph为Transient、持久保存不保留，比较实现pin`d6520d06325f0797ac6edac7eb1b3fb95b6eddd3deb32f765ef0230320466e75`；authored EventGraph/UserConstructionScript原内容完整保持。该解释不声称确切GC/内存清理事件或扩大图例外，v10执行和fresh全部验收仍待证据。

Synthwave Fence v3实际已保存唯一BP一次、其余222 SHA相同，BP/CDO/SCS旧根0、两个authored图保持，两图完整signature/relative按既有有限Palm profiles比较Gate通过，raw捕获保留；整体失败仅即时AR两个LastEdited导航缺soft边未更新，fresh重启证明pending，不重放save、不扩大Palm边界。 原v1/v2/v3及读取诊断失败保持。L_assets raw前后完整signature/relative相同；Showcase raw不同由此前已有原source Palm随机生成树有限profile按既有helper compare_map/fullrelative处理，Gate通过不等于raw字典相等。Fence v3最终error为“Current AR did not show exact two navigation addresses relocated, or other graph changed; fresh recheck required”，dirty_final=[]；不能把瞬时AR失败覆写成成功或提前认定持久化完成，后续fresh只验证，不重复唯一BP保存。

`00_engine/outputs/scene_folder_organization_20261012_v1/relocation_helper_before_post_compatibility_contract_v1.py`为本Technical拥有的冻结历史source，实际SHA`7e92c8a0eb32711d58b0043440dd14b02b4443abf09e4a0ac9241a6a83c424be`，用于既有执行receipt和source采集pin追溯；它不代表后续工作树代码已冻结或新规则已接受，不改变机器生命周期／保留政策。本节未修改S／Catalog／Inventory／皮肤owner；§13.34总审计条件仍待最终代码／输出冻结后真实执行。

### 13.37 原source重复、Fence fresh及日本第二次保存检查点（2026-10-13）

本节只补充下列actual证据轻量字段及SHA，§13.33正式22表与§13.36当时检查点原文不改。

| 实际证据（ORG／TEMP相对） | SHA256 |
| --- | --- |
| `ORG/post_original_construction_repeat_diagnostics_v2.json` | `93d4edb417c8d99f8e65406fabc7eea5dc5d50b9f846e66dc33605c20ac8c313` |
| `TEMP/post_source_current_construction_repeat_comparison_v2.json` | `feea30a934b61dddd6b3f5703d81ed6ad4835a0d3dd27d08de99b19f8cd0e873` |
| `TEMP/post_blueprint_t3d_exact_object_block_analysis_v1.json` | `eecca3cbe18ae82f57848039c5b9c22706b9e0750f90eaec5992c842e010d8d5` |
| `ORG/post_original_additional_authored_blueprint_witness_v2.json` | `47085ecd22bfaa702c5de578843bd82e4392bdf2c8d3ef3f59a43dca209d13a1` |
| `ORG/post_current_additional_authored_blueprint_witness_v2.json` | `46399426e638b2cb439b37f475ff66210741eb3c423936d11289dda9f85508e6` |
| `ORG/synthwave_fence_fresh_navigation_and_relative_v1_failure.json` | `2c8be62c43b637b311dfeecb0097a72499cfe95992439b9d39da53001768e2be` |
| `ORG/japanese_exact40_reference_repair_v10.json` | `b1872dff3811ad715fe4c6c9ea474e2e770ec613afcea7da23ba0b2c7d992284` |
| `ORG/japanese_saved_two_blueprints_public21_diagnostic_v1.json` | `7713d78af5403d20d2c377b0658199d84dff99d3efd02b5eb53e8ce2c2ce6f0e` |

PostCity原source四次加载诊断实成功，1200源/backup初末SHA同、dirty[]；原Dynamic完整signature/relative/local本就变化，Showcase同。source-current纯比较all7fullEqual=false；精确兄弟对象块分析只4BP同、7class/CDO的SourceAFTER与CurrentAFTER同，剩22PinId、一个BoxExtentInfo default metadata及编译Transient stub有限解释未接受。新增14BP仅10同/4残差pending，source/current追加14+父链15诊断成功但只literal21 subset SHA，未重哈希whole1200，不能接受几何例外或Post formal。 原诊断save/native/delete/manual_compile/seed_setters均0，success只证明diagnostic_capture_complete，maps_verified/construction_compatibility_accepted仍false。当前201HISM/74Actor/16classes真实完整实例变化仍如§13.36，不能以原Dynamic也变化一概放宽几何。精确object-block分析保留所有属性及Pin数组顺序，只处理完整兄弟块排列；4BP完全同与7class/CDO相同不能升成all7完整同。追加诊断复用之前完整1200证明，本collector whole1200_or_backup_sha_rehashed=false；14additional/15父链与literal21 subset范围不推导整个源/target当前所有文件闭包已重验。22PinId、BoxExtentInfo缺省元数据和Transient stub有限证据待root接受，19Actor几何例外未接受。

Fence同一fresh捕获的纯adopt-v2实际success=true，未UE调用/保存：有限完整兄弟顺序20字段比较后，完整BP/CDO/SCS、source/target223文件、两图fullrelative与currentAR旧0均接受；target L_assets adjunct-v4也成功，source/formal旧回执不改。原fresh/saved失败保持原值、不重放Save、不扩大Palm范围。下一步只将该实际接受proof接入最终全局检查及派生gallery，24总发布仍pending。 `synthwave_fence_fresh_navigation_and_relative_v1_failure.json`saved_assets=false，error为“Fresh full authored/root/CDO/SCS public changed”；此fresh已证明先前即时AR导航重写落盘，但整体验收仍false，不能沿用§13.36“fresh未执行”描述现状态，也不能覆写该failure。随后root纯adopt-v2实际已完成：`synthwave_fence_fresh_navigation_and_relative_v2.json`SHA`c78642b85fcdabe0be05d741b7367337f97e62cc6e2b4dc97ce0608ce1686dae`success=true，producer SHA`47c0f19d510bea39552b082bea8a8f9defa9ea42b924d859965f425a74d0d0e1`，mode=offline_actual_capture_validation、UE_called=false／saved_assets=false。同一实际v1 raw捕获依有限完整兄弟20字段compare接受source/target223、两图fullrelative/currentAR旧0与整个BP/CDO/SCS，没有忽略内容。派生`synthwave_target_assets_relative_adjunct_v4.json`SHA`fd7db5849730752ffc881666e0fef0a5e1f97ab49eea87b4d0adc3c96e8e0522`success=true，L_assets63 Actor完整signature/relative严格、metadata_exception_added=false，原baseline/formal不改。19项纯tests实际197.28秒（root回归记录）；真正接受来自该actual proof，不从测试数推定。两个失败30da/2c8不覆写、不新增UE query/save，不扩大Palm有限范围；待全局v6/消费端gallery接入，Post严格Gate与24总发布仍未完成。

日本v10实际失败，已接纳历史BP_Bridge1次保存并新增BP_FishHut_01 Save1，当前累计2saved/maps0；失败为完整BP/SCS兄弟对象顺序、数值相同，不能以未完成计数认定未保存。只读saved2/public21诊断自身false/save0/public_count20，19BP各2authored getter通过及Quick_Stills已读；Quick仅14export兄弟顺序，timeline/key/locator/顶层GUID按既有策略同，最后Sequence_01补读尚未执行。后续跳过前2，剩19资产/19地图pending，formal23图/引用未接受。 `japanese_exact40_reference_repair_v10.json`success=false、adopted_historical_saves=1/new_asset_save_count=1/completed_assets=1/completed_maps=0/save_attempted=true；实际第二保存发生后才因比较失败停止。`japanese_saved_two_blueprints_public21_diagnostic_v1.json`success=false/save_attempted=false/dirty[]/other613_file_sha_unchanged=true，actual_file_deltas=2；19 BP authored getters各EventGraph/UserConstructionScript2完整通过，20个已读public可由后续诊断复用，不能把public_count20写成全部21完成。错误原句为“Actual full-current21 literal semantic difference /Game/Scenes/Japanese_Village/Cinematics/Quick_Stills”。Quick的14export sibling order与timeline/key/locator/顶层GUID既有有限generation策略比较分开，后续只补最后Sequence_01；目标19资产/19图待执行，两个已保存BP只能核对并接纳，不重放其Save。

正式22published/verified9954资产/49图保持；R06in_progress、父计划current，相机R02/R05及原goal暂停，skin独立保护。全24根/最终引用/EditorViews/gallery/机器清单/最终回归与16独立及跨层总审计待代码/输出冻结；旧v5只属于其代码检查点。 本轮未执行UE、改S／Catalog／Inventory、读取／修改skin scope或重跑fullAudit；最终冻结步骤仍见§13.34。

### 13.38 日本saved2/public21-v2完整只读通过（2026-10-13）

`japanese_saved_two_blueprints_public21_diagnostic_v2.json`实际success=true、SHA`cbd9fba3970083f4a61a80d424cf3c5b722f696c539936f34dc3ddd46186e355`；producer`497ad0646f2ec6ffa4674ac215a780d2ae3c8c192c835eaf3360d1df4404cdfd`。复用原20完整公开捕获，新增只读取最后`Sequence_01`一次；current_public21=21、whole_raw_export_count=1061、all_current21_complete_public_strict=true、19BP各2 authored graph、dirty[]、save_attempted=false，other613 SHA保持。该只读通过不表示19资产/19地图修复或fresh正式23图已完成。

literal21 sibling模块SHA`efa1036c11852f8c05934016bb0c8e31ace1daa2c33772835b079c399170dc48`仅依官方完整UObject兄弟块语义处理consecutive siblings排列，全部properties/type/index/signatures保留；TOP Sequence随机generation签名沿既有精确有限策略，不扩展忽略字段、数值容差或Palm范围。原v1诊断false、v10保存后失败及两文件delta均保持原始receipt，不重复保存BP_Bridge/BP_FishHut_01。

当前v11 saved2 continuation已实际执行，采用并跳过前2历史保存，仅处理其余19资产/19地图；冻结候选`TEMP/continue_japanese_exact40_reference_repair_v11.py`SHA`837ec7695f81ada8d4925738ba41915851419c12a308a6ca6b514e042083c2f0`。`ORG/japanese_exact40_reference_repair_v11.json`为仍变化的progress，success=false且无error不作为终结失败，不钉滚动完成数或该receipt SHA。唯一下一步核验其实际结束结果，再独立fresh23图/引用/dirty及cleanup验收；fresh-v13定义已冻结但尚未执行。正式22／9954／49、R06in_progress、父计划current、R02/R05及原goal暂停保持；Post有限残差及Fence最终全局/派生gallery接入仍未完成，本节不构成24全局验收。总文档审计及真实机器清单待最终code/output freeze。

### 13.39 场景目录整理恢复与纯诊断边界（2026-10-13）

本节为当前恢复入口；§13.33–13.38及旧false回执保留当时事实。`ORG`为`%OUTPUT_ROOT%/scene_folder_organization_20261012_v1/`，`TEMP`为`%LANCE_ROOT%/00_engine/temp/scene_folder_organization_20261012_v1/`。

| 当前证据（ORG／TEMP相对） | SHA256 |
| --- | --- |
| `ORG/scene_user_pause_checkpoint_v2.json` | `3e0b9f5be2abe84e36f7fad3806e21b9ca7bb6162be148b33960180cba713a0e` |
| `ORG/scene_user_resume_preflight_v1.json` | `a6692fc32630c6a74b13613d7db5983f54341dad68d49ef2d7fac61db0af4267` |
| `TEMP/continue_japanese_exact40_reference_repair_v12.py`（实际caller） | `a5e636ce87c7485aea71e42437e715f2d0e857bf240d1ae673e3bc8ca96415ed` |
| `TEMP/post_exact21_authored_full_exports_finite_comparison_v1.json`（纯诊断） | `31d1b1251d0338e82543d5cbe05748ee650ccbe398a1ecd9beaf91465e8c1876` |
| `TEMP/post_runtime_root_review_diagnostics_v3.json`（纯诊断） | `474f03bb7a76a2748e57c2078c8f661acd645973d11b26f73fcea26a7620e12a` |
| `TEMP/post_runtime_compact_review_diagnostics_v3.json`（完整差异诊断） | `547f880b08cee53f318643b0798908462075118bb969578f31042f7c961885b0` |

暂停v11原partial SHA`84b052eba47c9482cc6d21f0c261a2a982048561517c38a7370289f6bb8f6996`仍false：21资产、6图实际已接受，第7图仅loaded、未saved且SHA等于原backup。用户pause写屏障PermissionError不等于资产失败；dirty0、未kill UE、receipt readOnly已恢复。root新主UE v19/PID5144的实际preflight为Entry、dirty0、map_loads/save_calls0，helper7e92与原engineBase dc5b/build d35冻结pin一致，UseCurves=true/ForceLastAuthority=0。

v12实际root session54066已成功完成：`ORG/japanese_exact40_reference_repair_v12.json`冻结SHA`3a88f5e2eb3e936001197a43a56ffb89ecf2ef0590cb4c3a3691789bf85c7c90`、success=true、status=`exact40_references_repaired_pending_fresh23`；completed_assets21／maps19，采用暂停21资产／6图，本轮newmap13／newasset0、dirty_after[]。完整map／relative before-after通过，当前target与outside旧引用均0、592 immutable严格保持。原v11 false与pause proof不改，不重放已接受保存。历史完整约188MB证明由摘要解析复用，不逐图重写。source正常quit后，root新Main v20/PID45804的fresh-v14已实际成功：`ORG/japanese_content_completion_v14.json` SHA`f895edfbc25ade864da8abec5a32a2ff7172aa4b0929b0df2668ff3bac79b7a5`、remote SHA`a19a7ef44a93b1d4fcf57ad74c2adb3d206ed7cd49174fd712e401dbb76c7ef3`，23 maps／21public／1061raw／592 immutable通过。固定`ORG/japanese_redirector_retirement_v1.json` SHA`962d85f7a2e62b7f28146d8d00b48311784bb10d8fe5a4e3bebb5a7e81a0cf7f` success=true，native production contract接受615／23。cleanup-v5实际preflight success，`ORG/japanese_old_file_cleanup_preconditions_v5.json` SHA`89867bc76aeb0a278d9a58075e5e90bd949a51be6fcc0ed1f96d631ad413c64d`；main正常quit／dirty0、UE进程全0后，PowerShell-v5已实际删除305 literal旧文件。`ORG/japanese_old_file_offline_cleanup_v5.json` SHA`53e368bf22bb183ac7d71c5f44fa57935a57e7037b6c1108079ba0b974e9e665` success=true，615 target／616 source backups／Starter均不变；cold formal及第23根发布现已实际完成，见下列固定proof；public21／fresh23、616 source／17外部backup／7旧引用及305物理文件对应331对象（额外26对象）的原严格范围保留。`ORG/verified_Japanese_Village_v2.json` SHA`245269438b16cf95963922ee9fbdf8902c19d89035906349a702045d0476ff46`为正式615／23；`ORG/japanese_postcleanup_formal_v1.json` SHA`32cc6c70f29c88db4a67c528f29f6629219e213f045be7d4c2584a251d1a22a7`独立cold证明616旧引用全0／旧physical0、完整615 target SHA同fresh14、dirty0／noSave。`ORG/japanese_formal_publication_v1.json` SHA`d798bdf0989dc28af191e72e9ccd78f722a4eaf336d59cb9ef2b8c306b18fd69`与overlay SHA`07e6acf2a460f503fca12ba9ae20c2a2e3966c82257fa3fe9d8697869bd91411`确认第23根已发布、前22 rows完整不变。原v12保存不重播，日本原检查点为23／10569／72；当前Post已formal并发布第24根，见下列最终数据检查点。

Post完整有限authored证明`TEMP/post_exact21_complete_finite_authored_proof_v1.json` SHA`27b00dc155c9743c679eb564d920f3dfc46f9a70f0f8b3240b7107e8a067b206`已实际得到145／145 equal（21完整BP、82 public图、42 class/CDO），38缓存图有精确ledger；无通用GUID／图／property／RFTransient过滤，原raw与旧142／145、all7 raw false回执不翻转。仅证明实际已加载21 authored在有限规则下相等，未重哈希whole assets／backup或旧proof；compatibility_accepted／maps_verified及runtime actor／component／geometry／Car spawn授权均false。
+
+Car2 source/current完整补采均success，`ORG/post_original_literal_car2_and_vehicle_enum_v1.json` SHA`e129811233c3bac3f693b8679a3160c921d80be240c794df826ac30828cc8771`／current SHA`d4e955e52c087d68165cd58cf054ae20281bcf7fea787e83590eb96c66736808`；旧ordinal domain incomplete保持。安全public-byte collector SHA`3aa3915de9d3e26310fae4be1a2d7154d279a639308dc979be78e4c5877d532a`通过官方`call_method`调用native public UFunction（缺Python glue）：GetEnumeratorName／GetEnumeratorUserFriendlyName／GetValidValue各覆盖0–255。`ORG/post_original_vehicle_enum_public_call_method_domain_v1.json` SHA`7e61e28c3050636dcd8b9e2e5f61c1009c67a032e4d2dbf8a87784c326d6e449`／current SHA`9d322a8ddb6fddab6d603140b4355c27ebcf247c7107e728a27ceb3e7c8596a0`均success，ordinal/index/private/mapload/save均0、dirty[]；未证明ordinal映射或hidden MAX元数据，prior完整enum raw保留。Car2+enum完整authored补证`TEMP/post_literal_car2_and_enum_complete_authored_proof_v2.json` SHA`dca5177a23fd461c3f730eb11e6f534ec753bf6475853c049760bce20ec194fb`：11 full exports与3×256 safe-byte比较同，compatibility_accepted／maps_verified=false。ParkedCars spawn控制仍待最小实际采样，不能依据AR边猜测Source0两Car生成出处；collector-v3实际终止：`ORG/post_original_minimum_dynamic_controls_v3.json` SHA`1868ac2cb2bbace58a324aa91c1e0ff5517f7a431fc65e8c8fd4903c8d4dd6b9` success=false，仅因`StaticMesh.get_static_materials`缺Python glue；dirty0、pinned5文件bytes不变，已采BP1／actor1／map1、exact89 missing0，不认定内容损坏。公开probe-v2 `ORG/post_source_static_material_public_probe_v2.json` SHA`56bfbb2f3cf306b346c6f82ecef1bb187402ac3941e43bd7650c94456edccc25`实际success=true：NativeObject.call_method(`GetStaticMaterials`)及public reflected `static_materials`两路完整ordered struct精确相同，mesh SHA不变、dirty0／mapload0／save0。后续actual v5源侧 `ORG/post_original_minimum_dynamic_controls_v5.json` SHA`8613211bf26d9745f533481dafa5bb83cadf8ce2815a34e1405c0c1264f3ad87` success=true、0 newload／Save；Source正常退出后Main-v21/PID25492当前侧 `ORG/post_current_minimum_dynamic_controls_v5.json` SHA`864104b817f30ac80f6920560ebd507bf2ef073d18b9365fc527ebc66e0fbdef` success=true、1 Dynamic load、own5 bytes同／dirty0、0 Save／compile／seed／1200hash。两侧均89输入／53palette／3CAT、145 actorGroups／2BP／19meshes／10materials；两个旧Car findNone单列，不伪造Source0父关系。原v3 false不翻转，v5 success仅诊断采集完成，这些v5原诊断compatibility／maps flags保持false；当前formal接受由后续有限contract及fresh/native独立证明，不翻转旧采样回执。Main21随后发生RenderCore fatal，当前Main23为NullRHI，详见下面画面边界；UE仍由执行统筹agent独占。

Post runtime纯诊断保留16848 fielddiff／4258 HISMdiff，6转换损坏负测拒绝，maps_verified／construction_compatibility_accepted=false。Dynamic Source0 signature/world405与2023HISM、Source1/current0/current1为403与2022；2 Car仅Source0，生成出处未知。4 HISM的Ivy／Undergrown mesh互换且各侧重复样本自身mesh稳定，但counts/transforms也变，不能写成全geometry same。78个actor world cross差异为76 source自身变化及2 chair约1e-14差异（非全仅几ULP），仍需具体有限验证；Showcase四core／六组合strict same。Car2及18 Macro clone补采已支撑上述有限authored比较，运行时车辆生成、四HISM mesh／instance及两chair精确差异仍未accepted。

当前数据检查点：`ORG/verified_PostCity_v2.json` SHA`c0fd0dd5de2dd2532c28c3368ed8c3c2fa11a0b19fa579dcad2386503fdd3e73` success=true、1200／2／dirty0；`ORG/post_exact_package_compatibility_fresh_after_cleanup_v5.json` SHA`7d63797895cd71bd17be6934205d29b56befbacf0218d3eea93f7ef0d7354f29`通过aftercleanup，`ORG/post_exact_routed_old_root_offline_cleanup_v3.json` SHA`c5e318393085dcf1ba0e3991e7699a32e42f8ee91d123ee092f84c5f481eec3b`限定112 literal旧文件清理成功。`ORG/post_formal_publication_v1.json` SHA`ef3bacc3bb60de3cb3bc9be80b839a775f81cdda7112cfe113c5b4a2c089cbbd`与overlay SHA`82115e25f0ed6c92ff9be0ae82a53f4f1c3670f20dfdc3d8479eba8df0d9a126`确认正式24／11769／74，前23 rows保持；这是首次24发布时in_progress检查点；当前complete overlay与正确finalglobal-v2见后面的最终数据接入证明，不再用该旧pin作为最终消费端依据。

当前实现归属（`S`为`%LANCE_ROOT%/00_engine/scripts/unreal/`；不修改原camera／motion plans）：

| 代码／实际调用范围 | 本Technical职责与边界 |
| --- | --- |
| `S/ue_scene_folder_organization_v1.py` SHA`3b59725a3b1a8c676d48a8d29bfd4d4574d66d6fe68508f5871a9173a95e4005` | 当前production helper，精确Post分支独立compatibility witness；generic capture／comparison和其他根边界保持。真实前身`ORG/relocation_helper_before_post_compatibility_contract_v1.py` SHA`7e92c8a0eb32711d58b0043440dd14b02b4443abf09e4a0ac9241a6a83c424be`归档保护，不改历史producer pin |
| `S/ue_post_city_compatibility_contract_v1.py` SHA`3e63dea55f52940298dccc3c19f8e024c5f57167c11771add006f2ca7f2c458e` | 当前production精确Post合同：仅2 PM package路由／原4 serialized imports及opaque2 literal preservation，fresh-aftercleanup proof与current routed old0要求；不是通用class alias或opaque退休 |
| `TEMP/ue_post_city_construction_finite_contract_candidate_v1.py` SHA`6aed3503bc1fef8e1e2324b5f4833660b370196336a25aeb3ea7fe97d61bb175`、`TEMP/post_actual_construction_mechanism_acceptance_v1.json` SHA`f00ae8c4e3e1304c4cd22ac949d16db674705d1c73bd92db8078443ae6eb5469` | 真实production依赖，虽在TEMP仍受保护。仅同完整programme／有效inputs的89精确UCS HISM owners允许已见mesh／materials／instances生成差异；403 actor身份／class／world、levels、完整relative与其余components严格，raw不改，不声称随机实例geometry精确同或重建Source0两Car父 |
| `TEMP/test_post_construction_finite_api_v1_sol.py`、`test_post_city_compatibility_contract_candidate_v3_sol.py`、`test_post_helper_integration_v1_sol.py`、`test_post_finite_fresh_cleanup_scope_v3_sol.py` | 当前有限API／package兼容／helper integration／fresh-cleanup scope实际测试owner；冻结后应随规定三suite纳入完整回归，不从旧候选测试推定新helper最终通过 |
| `TEMP/run_post_fresh_v5_before_cleanup_sol2.py`、`collect_post_fresh_exact_package_compatibility_witness_v5.py`、`run_post_fresh_v5_after_cleanup_and_formal_sol1.py`、`prepare_post_exact_routed_old_root_cleanup_v3.py`、`cleanup_post_exact_routed_old_root_v3.ps1`、`publish_post_actual_formal_v1_sol.py` | 已实际使用的root串行wrappers／collector／精确offline cleanup／官方publish；collector nativeformal输入及caller pins从对应actual receipts核对，不授权重放迁移／保存／删除 |

最终数据接入actual：complete overlay SHA`a9b5a5072f058ead777c9829449fb6c798edadd64235599695769438433ffb3c`；`ORG/final_registry_and_reference_check_v2.json` success=true、SHA`fa8f10ea4487c96a180b79d67be43d879221d79dd4401d12c80fc45cd40b50e5`，producer `TEMP/final_relocation_registry_probe_v8_sol.py` SHA`c493bbbf5addc9d11fccad5eb19f42faf9579d5e0a3d7b2983e8a3b2b9d4fa82`，实际绑定complete registry与24／11769／74。原global-v1数据closure真但6个receipt.path元数据loop覆盖错误，保留历史、不得作为最终Gallery provenance；v2是现用独立依据。

Cyberpunk仅2 LastEditedDocuments旧导航修复：新formal `ORG/verified_Cyberpunk_City_v2_editor_documents_sol3.json` SHA`4d321c03d85c4c47b31757886978f10de8a7d5eab26a32e6b1bbc2184b3cdf20`与`ORG/cyberpunk_editor_documents_formal_publication_sol1.json` SHA`57b2b2af0b19cc1e9ea41f53128c424d5940d648c30edccfd4da81ec3429600c`实际更新该row，其余23 row不变；原2 native maps／完整relative显式adopt，不重播。Asian原772B non-AR附属 `ORG/exact_original_asian_ancillary_archive_sol1.json` SHA`a170ff0245e3124177c063883d7c4458514dc13fed9e772651dc089fff54cb09`可逆归档、deleted0，不把非AR文件分类为ObjectRedirector。

Gallery-v5 producer为`TEMP/derive_gallery_scene_index_relocated_candidate_v5_sol.py`（本Technical拥有），实际刷新 `ORG/gallery_relocated_refresh_v5_sol1.json` SHA`f039b3b526ee6524a49063d7f08c0eda890e05c248a30ba4e022f15eccf0d6ea`绑定正确global-v2；现用 `ORG/gallery_scene_index_relocated_v2.json` SHA`e90ba207b52856dcb4d1f0701ab0a9f3637e2bebbf7e4704be1a7ed73d9d253e`包含24卡／77maps，原1270 clip rows／128 media／2 plans保持。HTTP实际 `ORG/gallery_relocated_http_check_v1_sol.json` SHA`90d9aab1dea0afbb245910d2cca8bc6b4b474a05ea10b8d0c0dad4f828996855` success=true；这不是新镜头或新媒体接受，camera／MRQ未启动。

Catalog generator精确Post owner／lifecycle分支已实际应用，当前raw SHA`0de9a2a67f5e37cfdb1176b3c9657304d48ada7fe4cb19d449783549ded4dcfa`，owner=`technical/unreal/SCENE_CAMERA_SEQUENCE.md`、production／active_batch=false；root focused test已通过。不是只准备patch，也不等于真实Catalog已重建或全回归已通过。

普通RHI小复测actual：`ORG/post_normal_RHI_sync_texture_probe_final_v1.json` SHA`9750474c61bbdb9e74417801964046e2aba444731376ccb71eb319e2685eda9e` success=true，native stable-v3 SHA`0df97c186592d8e790f1d64db3db5cb4ec8fa108ea11484e45d892bae00dad36`与`ORG/post_normal_RHI_sync_texture_probe_viewport_v1.png` SHA`d48ccfa40620f7a1fbbdae9b0232460357b866211a044d7fafe33b0f906a0dd0`（2276970B／1280×720）绑定。root／执行统筹及文档agent实际查看，道路、建筑、树、车辆与光照可见；Cvar临时async texture0、Ambient2默认effect保留，未再见同sampler fatal，Config不变、dirty0、normal quit／全部UE0、MRQ0。Main21原fatal及8544只读分析保留；默认async根因未证明，只有Post Dynamic编辑器viewport、含editor overlays，宿主reflection capture从2048限制到1024已记录，不称全74视觉或最终视频通过。

EditorViews实际dry/apply：`ORG/editor_views_restored_20261013T145335357968Z.json` SHA`22dc578f735ed46ef9e4732d476161e667689a9d394b6b5eb6e449e513cfcc7f` success=true／applied=true。原649804B／SHA`4b5a7ae892213b676b7103fbe225fa7b07533344edfb02f10a9af84d84bf0eb6`的748 saved paths已恢复、30 replacements，retired NightLight(1)零matches；其余当前INI字节严格保持，currentINI SHA`f709910ed2d07978985f5df2f26146caf89263ee66df697335eb314977819080`。`S/restore_scene_editor_views_v1.py`及对应测试为既有正式入口，source原大小不是旧323230B currentINI。

空目录实际清理 `ORG/old_scene_empty_directories_cleanup_sol1.json` SHA`15402984befe0cca6d1f518d9d7f993efb8695a306f0920564ea467c0b307d48` success=true，仅439精确已知旧根空目录非递归移除，files deleted0；Content root／Starter／SourceCold Content junction保持。Asian772B non-AR可逆归档、全部原backup／有效TEMP生产依赖与原false证明仍保护，不因目录名TEMP而删除现用finite模块。

当前交付范围（用户2026-10-13缩小goal后）：场景整理、旧引用处理、配置／网页／编辑器视角同步已完成。沿用实际全局检查，不重放UE加载或保存。本轮确认24个场景目录存在、网页HTTP200；`test_kyoto_showcase_tie_contract_v1.py`相关20项通过。旧完整回归1651通过／1失败记录保留；失败是通用fallback测试误用PostCity配京都基准，测试已改为独立通用场景，并保留PostCity错误基准拒绝负例。生产代码和资产未因该测试修正而改变。

交付结果写入既有owner范围 `scene_folder_organization_20261012_v1/audit_scope/final_scope_closure.json`，相关测试为 `audit_scope/handoff_focused_test_v2.xml`。首次定向执行缺少PYTHONPATH导致收集失败，记录保留；补齐脚本路径后20项通过。该closure只表示用户批准的简化交付完成，不表示完整测试重跑、Catalog／Inventory重建或16项文档审计完成。此前§13.32／§13.34及audit_scope原manifest中的扩大检查计划已被本次用户范围调整替代，不再作为当前goal的执行要求；历史证据及备份保持原状。

等待用户检查整理后的场景。相机批量拍摄仍暂停，父计划保留；PostCity默认异步纹理报错原因未知，已接受的普通画面复测仅限同步纹理条件下的Post Dynamic编辑器画面。

### 13.40 早期场景清理（2026-10-14）

2026-10-14：早期场景清理完成。田园、哥特城堡及对应旧关卡已删除，释放约3.6 GiB；东京和两张仍被模板引用的工作关卡统一迁入Content/Scenes/TokyoStylizedEnvironment。旧DataMake/Scenes和旧东京目录已移除。当前25个场景包、12138个包内资产文件（含77张关卡），东京已从新路径正常打开；相机拍摄继续暂停。

本次输出 `%OUTPUT_ROOT%/legacy_scene_cleanup_20261014_v1/` 归本Technical／WF-60／OUT-WF60-SEQUENCE-TEMPLATE。`delivery.json`、`deleted.json`、`move_v2.json`、`final_ue_check_v2.json`记录实际删除、迁移和重新加载结果。田园／城堡及对应旧图1646文件删除前确认无保留范围外引用；东京通过UE原生迁移369项资产，其中两张工作关卡保留动画模板引用。旧264跳转文件零引用后清理，旧管理目录移除。仅更新4处东京视角路径，其他视角保留。6个脚本／JSON路径已更新并做语法检查，旧文本保存在`previous_path_configs/`。原24包overlay及验收记录维持历史范围，本次以delivery补充。Scenes根的UE_Placeholder为引擎目录占位文件，不计为场景包。无新增全项目测试或相机渲染。


## 14. 共用镜头三动作120条试拍（2026-10-14）

本节拥有 `%OUTPUT_ROOT%/camera_common_presets_20261014_v1/`、`00_engine/temp/camera_common_presets_20261014_v1/` 及本轮共用相机计划、独立网页与运行回执，沿用 `OUT-WF60-SEQUENCE-TEMPLATE` 和 `VAL-SCENE-01` 的实验范围。R07归唯一current计划；输出默认unclassified保护，不新增删除或保留晋升政策。

2026-10-14新授权：只恢复本轮共用相机120条试拍（行走、舞蹈、伸展×20镜头×横竖，排除面部近景）。每个镜头/画幅三个动作共用参数，仅叠加柔和XYZ跟随；允许肢体局部出画并明确标记待审。旧1260相机批次仍暂停；皮肤及其他域受保护。当前仅开工，实际媒体与人工接受尚未完成。

网页复用既有相机媒体核验与Range服务器，默认同镜头三个动作并排，横竖切换，展示共用参数、跟随说明、实际媒体完成进度与局部出画待审说明。只有最终视频SHA、完整解码、尺寸、FPS、帧数及逐片receipt一致才开放视频地址。页面播放成功不代替人工构图接受；其他域及旧批次证据不改。

本轮按用户限定只做相关轻量检查；全套测试、Catalog/Inventory重建和16子系统审计不执行，不沿用历史报告称本轮通过。开工状态不代表UE准备、渲染或120条媒体已完成。

本节拥有 `S/ue_common_camera_review_v1.py` 和 `S/run_common_camera_review_v1.py` 的隔离执行入口：旧adapter只在新进程内存中替换RUN/ASSETS/PLAN_NAME，保留动作源时钟验证；先12条smoke，再108条，仅在真实 `smoke_visual_review.json` 的 `proceed_to_remaining=true` 且plan SHA一致后继续。每次媒体编码沿 `encode_motion_scene_pilot_v1.process(attempt,[newplan],run=RUN)`；`media_validation_<attempt>.json` 和 `media_receipts/` 保存逐片实际验证。

本节拥有 `S/build_common_camera_gallery_v1.py`、`S/common_camera_gallery_v1.html`、`S/open_common_camera_gallery_v1.py` 的本轮审查入口（限定pilot/utility，不推定production）。Builder当前读取 `camera_trial_plan_v2.json`（schema `camera_common_presets_trial_v2`，兼容v1结构）及成功的 `media_validation_*.json`，检查逐片receipt与shot-plan SHA，再复用旧相机媒体validator；原子发布 `review_delivery_manifest_v1.json` 和 `gallery/index.html`。每批完成后执行 `python S/build_common_camera_gallery_v1.py --run-root RUN` 增量发布；网页30秒刷新清单。独立launcher首选8882，占用时选后续空闲端口并避开8880/8881/8893，最终端口由 `gallery/launcher_status_v1.json` 拥有；不停止旧服务器。

2026-10-14开工入口检查：独立页 `http://127.0.0.1:8882/gallery/index.html` 已实际HTTP200、返回HTML与磁盘精确一致；120组合、20镜头、三动作及40组共用参数检查通过，未验证格子无视频地址。`gallery_lightweight_check_v1.json` 仅拥有初始入口与Python/JS语法检查，当前0/120可播；实际浏览器交互未检查，媒体Range检查待真实视频。`camera_common_freeze_v1.json` 与 `camera_common_targeted_checks_v1.json` 拥有离线计划冻结及针对检查，离线成功不代表构图人审接受。

### 14.1 v2共用纵向跟随与限定发布检查点（2026-10-14）

当前使用 `camera_trial_plan_v2.json`，SHA `099555a085491042c905bf8b33ddde2c1bb4af573a2976a180da4cac201f2a01`。54个full-only shot对象与ID原样保留（不表示54条视频已复用完成），66个upper/推拉shot使用v2；基础距离、初始取景高度、FOV、角度及XY路径不变，只增强全部upper的共用纵向跟随：15%pelvis/25%spine02/60%neck，平滑0.9秒，gain=1.0，soft-limit=70cm，不按动作另调参数。12条smoke由6条原full媒体及6条v2upper复测构成；`smoke_visual_review.json`明确允许带局部裁切限制继续108条，人审仍pending。

中途检查点（已由§14.2最终媒体交付覆盖）：当时66/120，竖屏60＋横smoke6；该检查点不作为最终完成证明。

弯腰伸展front_upper两画幅已标注深弯腰主要见头发和肩背、约4.4–4.8秒起身可能短暂裁头；舞蹈portrait/back_upper约12.2秒的采样躯干靠左边缘并局部出画，下一采样13.4秒恢复。后者仅离散采样，不能推定持续时长；说明来自本轮样片观察，非用户验收，仅各指定组合有效。

本轮实际浏览器由root确认12/120时的横竖切换、三个视频同步起播（currentTime约0.199/0.198/0.198、readyState=4、无error）及暂停；只拥有该交互范围，不代表所有120媒体实际播放或全套浏览器测试。`smoke_visual_observations_v2_agent.json`拥有6条upper各20时点及11张bend原帧观察；原6full引用v1观察，不重写历史失败/限制。最终代表抽样报告待交付，未声称逐帧连续审查。

### 14.2 本轮120条最终技术交付（2026-10-14）

2026-10-14最终媒体交付：v2矩阵120/120已完成真实编码、逐片回执核验并发布（横屏60、竖屏60）。`remaining_recovery_execution.log` 最后一批 `remaining_006_landscape_v2` 成功；`review_delivery_manifest_v1.json`拥有最终媒体清单。局部出画限制与人工构图验收仍待用户检查，旧1260批次不恢复。

独立入口 [三动作共用镜头审查](http://127.0.0.1:8882/gallery/index.html) 实际HTTP200且HTML与磁盘一致；限定各一条横竖视频Range206、1024字节精确比对通过，证据为 `gallery_final_check_v1.json`。root实际浏览器确认横竖切换、三视频同步起播/暂停及两处观察备注显示；该范围不等于120条逐片浏览器播放。未执行全套测试、Catalog/Inventory重建或16子系统审计，不套用历史通过记录。

最终代表抽样已交付：`remaining_visual_observations_agent.json`覆盖23条成功样片、460张离散采样图像，结果为 `no_observed_delivery_blocker`、`can_deliver=true`。这仅是限定样片/时点的观察，未声称全部120条连续逐帧视觉通过；已有局部出画备注保留，人工构图验收pending。

本轮R07按媒体与审查入口技术交付完成，唯一父计划仍current，原R02/R05的大矩阵及其他pending范围不因此完成或恢复。没有生产Gate晋升；所有观察备注和human_acceptance继续pending，媒体核验不代替构图接受。

本节同时拥有 `final_delivery_summary_v1.md` 简明交付说明，及固定最终代表抽样 `remaining_visual_observations_agent.json`（SHA `a6efff005f097cd7faa93f9e58452128387c613f40f9512a92267f5777e5f03b`）。报告落实限定视觉观察，不升级人工验收或生产Gate。

## 15. 全部有效动作横竖镜头与竖屏距离1.15倍（2026-10-14）

本节拥有 `%OUTPUT_ROOT%/camera_all_motions_portrait115_20261014_v1/`、同名temp、全动作计划/运行回执/新审查页及本轮媒体。沿用唯一current计划R08、WF-60/WF-80、OUT-WF60-SEQUENCE-TEMPLATE及VAL-SCENE-01实验范围；输出默认unclassified保护，不新增清理或production晋升。

用户已认可§14的三动作横屏，要求全部竖屏镜头拉远15%。新矩阵30个新旧有效动作×20非face镜头×横竖=1200，各沿用已接受代表性别（23女性、7男性），不扩成两性矩阵。横屏基础参数不变；portrait的full/upper距离以及dolly两端都×1.15；FOV/角度/初始取景高度、柔和XYZ跟随、动作窗口和速度保持。7秒推拉设计时间保持；动作短于7秒只提示镜头可能未走完，不更改动作时钟。

机器计划为 `camera_trial_plan_v1.json`、schema `camera_all_motions_portrait115_trial_v1`；生成实现 `RUN/camera_all_motions_planner_v1.py` 复用既有共用镜头定义，动作源proof由本轮motion_sources拥有，离线冻结不能代替真实UE媒体或构图接受。执行由root独占共享UE；运行入口和逐批回执按本节后续实际检查点登记，不从脚本存在推定1200完成。

本节拥有 `S/build_all_motion_camera_gallery_v1.py`、`S/all_motion_camera_gallery_v1.html`、`S/open_all_motion_camera_gallery_v1.py` 的限定pilot/utility入口。Builder接受完整1200唯一组合，逐片核验receipt SHA与shot-plan object SHA，复用§12现有media validator后原子发布 `review_delivery_manifest_v1.json` 和 `gallery/index.html`。未核验行不包含video/poster地址。每批完成后调用builder；页面30秒刷新清单，按动作/镜头/横竖审查，备注只存在本浏览器，可导出。

旧10动作的中文显示名称复用§12的 `presentation()` 与现有 `S/../dataset/prompt_catalog_first_batch_v1.json` 的 `labels.action.<lowercase_action_id>.zh-CN` 字段，括号注明原男女动作来源；来源path/SHA登记在manifest的 `display_label_source`。这仅替换网页显示别名，保留动作ID、计划和逐片receipt，不导入旧生产参数；因此观众回应、打招呼等同名动作仍可分辨来源。

独立launcher首选8883，占用时选后续空闲端口并避开8880/8881/8882/8893；不停止既有服务器。旧§14三动作portrait对照经既有validator只读验证，在新server固定 `/previous-common/` 路由中提供Range访问，不复制或覆盖旧媒体；不计入本轮完成数。上一轮横屏认可仅属于已展示三个动作，新portrait和其余构图仍pending。

命令：`python S/build_all_motion_camera_gallery_v1.py --run-root RUN`；`python S/open_all_motion_camera_gallery_v1.py --run-root RUN --no-browser`。逐批媒体验证、恢复、Range和有界浏览器交互保持独立证据。只做本相机scope相关轻量检查，不执行全套测试、Catalog/Inventory重建或16子系统审计，不把旧报告作为本轮通过。旧120/8882、旧1260暂停及另会话皮肤等范围保持。

### 15.1 冻结与独立审查入口检查点（2026-10-14）

实际plan SHA `30ef018c59b17ac2daa2e58a2596eb8eb964fc3c26b35fda41c188e0eed05792`；`camera_all_motions_freeze_v1.json` 和 `camera_all_motions_targeted_checks_v1.json`拥有本轮离线冻结与有限检查。60条原三动作横屏shot对象/ID保留，1140条新增或竖屏修订；landscape复用按真实 `media_validation_reused_landscape_v1.json` 发布，不假称重新渲染或把旧portrait计入本轮完成数。

`geometry_risks_require_review`仅列旧女性CatchBreath的portrait/dolly_out_back：初始upper阶段的非活动full代理范围有13采样深度≤1cm，inactive minimum约−26.0cm；实际使用upper阶段min depth约101.2cm，结束full阶段约150.6cm均正。网页逐组合保留明确待审说明，不能依据代理范围推定实际画面穿模，也不为消除提示更改已冻结相机。

本节拥有 `S/run_all_motion_camera_review_v1.py`、`S/ue_all_motion_camera_review_v1.py` 及对应有限 `S/tests/test_all_motion_camera_runner_v1.py` 的隔离执行入口。`batch_schedule_v1.json`按plan SHA冻结12条一批的串行安排，`batch_intents/`、`render_receipts/`、`media_receipts/`、`media_validation_*.json`及执行log分别保存真实意图、UE准备/渲染、编码核验和恢复结果；主agent是唯一共享UE执行者，不能因schedule存在而写成整批已渲染。

首次独立入口 [全部动作镜头审查](http://127.0.0.1:8883/gallery/index.html) 已实际启动。首检为60/1200；`gallery_lightweight_check_v1.json`按后续真实发布增量更新，84/1200时拥有HTTP200/HTML精确磁盘一致、Python/JS语法、1200组合及1116 pending行无媒体URL、旧portrait对照与本轮landscape/新portrait各一条Range206/1024字节精确比对。默认sandbox的本地连接WinError10013曾阻止首次启动核验；按已有授权完成本地loopback escalation后成功，未更改旧服务器。该检查不等于1200逐片浏览器播放；有界浏览器交互由root另存实际证据。新页进度以后续manifest为准。

### 15.2 有界浏览器与代表样片观察（2026-10-14）

`browser_interaction_check_v1.json`拥有root实际有界浏览器证据：弯腰伸展portrait/front_upper本轮与旧原portrait同时起播，两播放器readyState=4且error=null，播放时刻约0.430/0.428秒，实际暂停时刻约9.896/9.895秒；动作选择、1.12m距离显示及新旧对照可见。该证据观察时发布数为84，只覆盖这两条视频及指定交互，不是全部1200逐片播放或构图接受。

`bounded_visual_review_v1.json`拥有预先固定36条代表样片的离散图像审查；固定抽查现已完成36/36条、720个采样时点，人工验收仍pending，不代表全部1200视觉通过或连续逐帧审查，不自行加样本。原34条/680图和2条横屏待生成是此前检查点。本节builder只把实际observed且已媒体验证的对应shot附上简短中文构图观察，检查report plan SHA、具体组合、receipt pin及图像SHA后发布；所有注释仍human_acceptance=pending，明确每条20离散图、不能判断精确裁切持续时间，不外推其他动作镜头画幅。后续显示以实际报告为准。

报告中4条既有服装范围观察从相机逐片提示剥离，保留在manifest的 `out_of_scope_observations_for_summary` 供交付总结读取，不将服装缺口归因于本轮距离、不启动服装修复。`bounded_review_source`保存实际报告SHA及选择/观察/附注数量；旧源码已import的在跑batch可能仍发布旧版页面，最终由root重新调用新builder落实最新版显示，不更改当前runner。

### 15.3 batch011单段缺帧与有界恢复（2026-10-14）

本节是 `S/recover_all_motion_camera_batch_v1.py` 的production实现所有者，范围仅本轮固定计划下明确一段缺PNG的恢复；不因此晋升相机构图或整个批次的production Gate。原 `allmotion115_portrait_011_30ef018c59_32c360a22e_v1` 的UE render receipt记录success=true，但 `allmotion115_motion_cand_009_female_p_dolly_in_front_v1` 实际只有416/417帧，缺 `frame_0211.png`，encoder按合同拒绝；成功回执不覆盖原帧不完整事实。

root实际完成两步恢复：`encode-good`只选择其余11段完整原jobs，绑定未改写的原render receipt与source pins；已存在8条MP4和媒体receipt字节保留，补齐3条，并生成标准 `media_validation_allmotion115_portrait_011_30ef018c59_32c360a22e_v1_complete_subset_v1.json`（videos=11）。子集说明不是合成的新render receipt。随后 `recover-missing` 仅重拍该1段，新attempt为 `allmotion115_recovery_30ef018c59_56d6d3191e_a2f607b295_v1`，该段真实编码核验成功；原缺帧raw及原回执继续保护，既有合格视频不重拍或覆盖。

证据目录 `recovery_evidence/allmotion115_portrait_011_30ef018c59_32c360a22e_v1/` 拥有 `original_render_receipt.json`、`missing_png_failure_v1.json`、`complete_subset_descriptor_v1.json` 和 `replacement_attempt_v1.json`；恢复命令与实际结果由 `recovery_011_encode_good.log` / `recovery_011_retry.log` 记录，新段回执由新attempt的render/media validation拥有。恢复后发布204/1200是当时检查点，batch012继续，最终数量待全部完成。本轮同期UE日志有OutputBuilder/unknown frame相关ensure，但与单帧缺失的因果尚未证实，不称根因确定，也不放宽完整帧/解码核验。

### 15.4 全部1200条技术交付（2026-10-14）

本轮串行runner已正常结束，最终plan SHA仍为 `30ef018c59b17ac2daa2e58a2596eb8eb964fc3c26b35fda41c188e0eed05792`。root fresh builder按真实逐片回执发布 `review_delivery_manifest_v1.json`：1200/1200（30新旧有效动作×20非face镜头×横竖，横竖各600）。其中60条横屏沿原完整证据复用，1140条新增或修订；横屏参数不变、竖屏全部距离及dolly两端×1.15，跟随/动作窗口/速度保持，面部不在范围。§15.3单段缺帧已单独重拍并通过核验，原失败证据继续保留。

`bounded_visual_review_v1.json`固定代表抽查36/36、720个离散采样时点已完成，结论为 `no_observed_camera_delivery_blocker_in_36_bounded_representatives`。36条对应注释已由fresh builder发布；局部裁切仍待用户判断。这是限定代表样片和时点的观察，不是全部1200连续逐帧或视觉接受，不自动晋升生产Gate。

独立入口 [全部动作镜头审查](http://127.0.0.1:8883/gallery/index.html) 的最终 `gallery_lightweight_check_v1.json` 记录1200发布检查：HTTP200/HTML精确磁盘一致、Python/JS语法、30×20×2矩阵及旧portrait/本轮横屏/本轮竖屏各一条Range206与1024字节精确比对通过。该检查未重复视频全解码、未操作UE，也不表示1200逐片浏览器播放。root最终有界浏览器证据 `browser_final_delivery_check_v1.json` 实际记录可见1200/1200、横竖各600、30动作、20镜头及 `playback_new_and_previous_verified=true`；新/旧舞蹈portrait/front_upper两视频ready=4、error=null，实际成功暂停（时刻约21.801/21.799秒）。原始JSON没有status字段，State按这些实际字段登记有界证据，不补造原回执状态。完整页面截图为 `gallery_final_screenshot.png`；此证据只拥有指定UI与两视频交互，不是全部1200逐片播放或构图接受。原两bend新旧播放/暂停证据保持§15.2范围。

R08按媒体和审查入口的技术交付范围completed；后续用户限定接受见§15.5，父计划仍唯一current，并按新授权推进§16面部近景。旧120/8882、旧1260暂停及其他域保护保持。`owner_docs_lightweight_check_v1.json`只核对本轮五份owner文档的Plan R08/Technical15/Status/State对应关系；全套测试、Catalog/Inventory重建及16子系统审计未执行，不用旧报告称本轮通过。

### 15.5 用户对非面部镜头的限定接受（2026-10-14）

`user_acceptance_20261014_v1.json`绑定本轮计划及1200条发布manifest的SHA，登记用户接受：横屏完全合理、竖屏基本合理，少数局部裁切允许保留。接受仅属于30动作×20个非面部镜头×横竖；原浏览器/代表抽样报告的pending字段是其生成时的历史快照，不原地改写。后续现用相机标准与旧基线对照退役归§16；面部近景尚待新一轮实施和人审，不由本接受推定通过。

## 16. 面部近景与现用标准（2026-10-14）

本节拥有 `%OUTPUT_ROOT%/camera_face_closeup_20261014_v1/`诊断、`%OUTPUT_ROOT%/camera_face_closeup_20261014_v2/`最终候选及同名temp，并拥有本轮现用标准固化、面部计划/运行回执/媒体/独立审查页与轻量检查。沿用唯一current父计划R09、WF-60/WF-80、OUT-WF60-SEQUENCE-TEMPLATE和VAL-SCENE-01实验范围，输出默认unclassified保护，无生产Gate晋升。旧1200原媒体和冻结证据保留；现用标准和旧对照退役已由§16.1/16.2登记，最终60条技术交付与人工待审边界见§16.6。

R08已接受的横屏保持；竖屏全部距离及推拉两端统一×1.15作为现用标准，不重复叠乘。面部范围为同30个有效动作各现用代表性别×1近景×横竖=60条；先站立、弯腰、舞蹈、行走、转身五类10条，再按实际结果调整并完成其余50条。采用柔和头部位置跟随，不追逐头部yaw；允许每动作调整跟随与距离，动作窗口/播放速度保持。精确动作ID、距离、跟随参数和计划SHA由对应revision的freeze/参数表拥有；执行入口见§16.3/16.4。离线参数或样本存在不代替UE媒体及人工接受。

共享UE只由root串行执行。v1诊断页8884保持，最终v2页8885已发布60/60；未验证媒体不得暴露播放地址。只执行受影响相机实现/媒体/网页及五份owner合同检查，不运行全套测试、Catalog/Inventory重建或16子系统审计。旧1260暂停、另会话皮肤与其他域保护保持。

### 16.1 离线冻结与现用标准登记（2026-10-14）

现用非面部标准已由 `00_engine/assets/cameras/nonface_camera_standard_20261014_v1.json` 实际生成，schema `camera_nonface_standard_config_v1`，version `nonface_camera_standard_20261014_v1`，本检查点SHA `ad07966c2112f286d7936b4d3fd6db7c4da931533719c65484a8c60d53ab25bb`。其orientations绝对数值与R08 source_config相同；`portrait_distance_revision_already_baked=1.15`表示已含拉远，`portrait_distance_multiplier=1.0`要求使用存储距离，不能再乘1.15。scope明确20个非面部镜头，面部配置独立。旧对照移除实际publisher核验见§16.2。

本轮 `face_closeup_freeze_v1.json` 实际绑定60条离线计划 `camera_trial_plan_v1.json`（SHA `b5f59b4b2d3c586f0d51d658fa3a098e1fdacd5355603de876a52d7096d01b6c`）、`camera_face_closeup_config_v1.json`、`face_closeup_action_parameters_v1.json`及`face_closeup_targeted_checks_v1.json`。有限参数检查success=true，逐条检查源动作时钟/代表性别、consumer key schema、有限轨迹值、不追yaw的固定相对向量、固定FOV、头部代理margin/正深度、离地及trajectory SHA；这是缓存骨骼平移与头部包围代理检查，不保证真实轮廓、可见性或渲染构图。freeze明确ue_operations=false、rendered=false、human_acceptance=pending。

首批五代表ID按 `pilot_shot_ids` 固定：MOTION_CAND_002女性站姿、003女性弯腰、030女性舞蹈、008女性行走、029男性转身，各l/p共10条。各动作精确距离/平滑参数和source clock归 `face_closeup_action_parameters_v1.json`；配置支持按动作调整，不将离线统一默认推定为最终采用参数。60条真实准备/渲染、媒体核验及独立网页待root执行证据。

### 16.2 现用标准发布与面部空审查页（2026-10-14）

两Run分别拥有 `gallery_publisher_check_v1.json` 实际发布检查。旧R08页8883仍1200/1200，接受记录独立读取 `user_acceptance_20261014_v1.json`；原冻结plan未改，manifest不再包含旧portrait对照引用，HTML不再包含旧对照界面或previous-common地址。新面部页8884首检60行、0可播、30动作，pending行无video/poster URL，默认front_head。两页HTTP200且HTML与磁盘一致，轻量DOM执行核对动作选择与画幅切换。检查没有success字段，按具体字段登记通过；这不是实际浏览器、视觉媒体检查或新面部60条完成。旧媒体未删除/重编码，后续可播数量只从实际媒体回执发布。

### 16.3 实施入口、复现与有限验证所有权（2026-10-14）

本节拥有 `S/face_closeup_camera_planner_v1.py`、`S/run_face_closeup_camera_review_v1.py`、`S/ue_face_closeup_camera_review_v1.py`、`S/build_face_closeup_camera_gallery_v1.py`、`S/face_closeup_camera_gallery_v1.html`、`S/open_face_closeup_camera_gallery_v1.py`，均为本轮隔离pilot/utility入口。UE适配器仅复用§15已有prepare/render/receipt合同，Run Root隔离，资产命名空间为 `/Game/DataMake/Validation/FaceCloseupCamera20261014`；实际共享UE操作只由root执行。planner同内容可幂等再现，拒绝覆盖变化的冻结结果。

从Lance Root复现离线配置用 `python 00_engine/scripts/unreal/face_closeup_camera_planner_v1.py`。root按实际状态调用 `python 00_engine/scripts/unreal/run_face_closeup_camera_review_v1.py pilot`，检查五代表10条实际结果后再用同入口 `all` 完成其余50条；`status`只报告当前回执。批次安排、意图、render/media回执、逐片验证和 `batch_progress.json`分开保留，progress是滚动检查点，不将其SHA或完成数当最终冻结。执行失败先检查具体回执及UE状态，不能因命令超时或暂未返回便重复提交。

面部网页构建为 `python 00_engine/scripts/unreal/build_face_closeup_camera_gallery_v1.py`，独立launcher为 `python 00_engine/scripts/unreal/open_face_closeup_camera_gallery_v1.py --no-browser`，默认8884。每次发布仅按实际合格receipt开放媒体地址。§15旧builder/HTML/launcher已改为读取独立非面部接受记录及标准版本，移除当前对照，原媒体和原计划保持。

本轮没有新增仓库pytest；planner内 `checks()`对60条做§16.1有限参数验证，并调用既有 `ue_camera_alignment_review_v1.validate_body_contract()`核对全部源身体合同；线性运动平滑误差<1e-9、同内容重跑SHA不变、旧nonface plan SHA不变均由planner交付。图库agent完成四个builder/launcher的Python语法及两页脚本语法检查，临时DOM/HTTP harness位于同名temp范围，耐久证据只保留两Run的 `gallery_publisher_check_v1.json`。`owner_docs_lightweight_check_v1.json`拥有五份owner、R08接受范围、R09状态、非面部1.15 baked/apply1.0与离线freeze合同检查；该文件后续文档更新后刷新。没有运行全套测试、机器目录重建、完整文档审计或真实视觉验收，不以这些有限检查代替缺失Gate。

### 16.4 v1诊断与v2竖屏必要修订（2026-10-14，历史实施检查点）

v1首批10条真实编码核验已完成，`face_closeup_bounded_visual_review_v1.json`绑定10条媒体、10张timeline contact及200离散采样帧；完整视频播放数为0。采样未见穿入/跟丢，5L适合保留，5P构图偏宽可见腰。低头/背身是动作方向，位置跟随不保证脸始终可见；以上为限定观察且human_acceptance=pending。v1保留诊断历史，不直接扩大为最终交付。

本节同时拥有新Run `%OUTPUT_ROOT%/camera_face_closeup_20261014_v2/`及同名temp。`S/face_closeup_camera_planner_v2.py`默认preview，root批准后以 `python 00_engine/scripts/unreal/face_closeup_camera_planner_v2.py --freeze`冻结；当前计划文件名仍为 `camera_trial_plan_v1.json`，schema仍`camera_face_closeup_trial_v1`、revision=2，SHA `d4da981bb3aaf8abd730ba34cb805bb1684a988ebe275ce338c6b334814143aa`。`face_closeup_freeze_v2.json`绑定 `camera_face_closeup_config_v2.json`、`face_closeup_action_parameters_v2.json`及`face_closeup_targeted_checks_v2.json`。30条landscape完整shot对象与v1精确相等；30P改为nominal60cm、targetZ+3cm，且仅029/030 sigma=0.18，逐动作实际安全距离以参数表为准，动作窗口和播放速度不改。60条离线检查及runtime身体合同通过，旧nonface plan不变；这些不代表v2已渲染。

`run_face_closeup_camera_review_v1.py`现支持 `--revision v2`，由root串行执行 `python 00_engine/scripts/unreal/run_face_closeup_camera_review_v1.py pilot --revision v2`先重拍5P，再按真实观察决定 `all --revision v2`；同名UE适配器继续隔离本轮Run。30L对象复用不等于30L视频已有，媒体只能按真实receipt复用。最终目标仍60，独立页预计8885待发布核验；v2实际可播数量、pilot观察与其余渲染待真实证据。本检查点不结项，R09in_progress。

### 16.5 v2试点通过与剩余批量执行（2026-10-14，历史实施检查点）

v2试点10/10已支持继续：5条横屏精确复用v1媒体与观察，5条新竖屏实际观察5张拼图/100离散帧，头肩突出、正常姿态不再见腰，采样未见裁头、穿入或明显跟丢。`face_closeup_bounded_visual_review_v2.json`结论为 `pilot_composition_suitable_to_advance_remaining_batch`；累计跨v1/v2实际观察15条/300帧，完整视频播放数0，非逐帧检查、非用户接受。其余50条由root串行继续；本检查点v2已发布20/60，滚动完成数以当前manifest为准，不据此结项。

本节新增拥有 `S/reuse_face_closeup_landscape_v1.py`，仅复制5条既有合格landscape及匹配media receipt，核对完整shot和源媒体/拼图SHA；耐久证据为v2的 `media_validation_reused_landscape_pilot_v1.json`，不把复制说成重拍。UEwrapper已独立使用live属性而非误读旧adapter全局值，具体运行结果仍由真实receipt拥有。

面部builder/launcher支持 `--run-root`，默认已切v2/8885，保护v1/8884诊断页；标准非面部页仍8883。v2初始 `gallery_publisher_check_v1.json`是0/60时的轻量DOM/HTTP证据，不覆盖后续动态可播数。root报告实际浏览器起播成功，自动刷新重置选择/播放的问题已由图库实现修复，正在复测；当前不把修复存在称作最终交互通过。最终媒体与最终网页结果待证据；最多4条极端补充观察尚未执行，不作为本检查点已完成事项，不结项、不扩成全量视觉审查。

### 16.6 最终60条技术交付及人工待审边界（2026-10-14）

v2串行runner已实际结束，`batch_progress.json`verified=60/target=60；最终`review_delivery_manifest_v1.json`发布60/60、横竖各30，计划SHA保持 `d4da981bb3aaf8abd730ba34cb805bb1684a988ebe275ce338c6b334814143aa`。5条v1合格横屏媒体按§16.5精确复用，55条新编码，原v1诊断10条与被替换5P不额外计入最终60。非面部已接受标准和旧对照退役保持，旧1260不恢复。

最终 `face_closeup_bounded_visual_review_v2.json`status=`bounded_review_complete_with_wider_extreme_compositions`、scope_complete=true：新看9条/9张contact/180帧，引用5条同SHA旧L/100帧，当前交付限定14条/280帧。跨版本历史19渲染版本/380帧含5条被替换旧P，仅作历史，不当当前覆盖数。033与ACT_M01_BATTLE_DANCE各横竖4条头完整且采样未见穿入/明显跟丢，但明显宽于pilot、包含较多上身，归 `extreme_motion_wider_composition_review_candidate`供用户判断。full_video_playback_count=0、all_60_clips_visually_passed=false、human_acceptance=pending；稀疏contact不能确认帧间微抖或整段舒适度，不再扩大抽查。

`gallery_final_check_v1.json`实际核验60/60、30L/30P、30动作名称与已接受页匹配；HTTP8885=200且HTML精确磁盘一致，横屏002与竖屏033分别Range206、1024字节精确匹配。最终四条较宽组合提示分别绑定各自画幅；只增加提示后重新发布HTML/manifest，原两条未变媒体的Range证据沿用，不重复请求或解码。该检查复用既有encoder receipt而不重复全解码，其轻量DOM不冒充实际浏览器。独立root实际浏览器证据 `browser_refresh_playback_check_v1.json`观察进度20→25、多次自动刷新仍播放，paused=false、ready=4、error=null，修复选择/播放重置；只覆盖指定交互，不是60条逐片播放或视觉接受。

R09按技术交付范围completed，父计划仍唯一current，用户在8885审查60条尤其四条极端较宽组合；v1/8884保留诊断，非面部标准页8883保持。`owner_docs_lightweight_check_v1.json`归本v2 Run，拥有本轮五owner/Plan R09/State/最终媒体与有限证据指向合同；不跑全套测试、Catalog/Inventory重建或16子系统审计，不用历史报告代替当前检查。无生产Gate晋升。

§16.6最终root执行确认：runner正常exit0；实际浏览器页面显示60/60，切换横屏成功播放约12.03秒、ready=4且无报错，随后暂停并保留tab，截图为v2的 `gallery_final_screenshot.png`。该事实来源为root实际操作报告及保存截图，不补造原JSON字段，也不视为60条逐片播放或用户接受。没有新增检查或扩大抽样。

### 16.7 当前60条面部审查网页离线分享包（2026-10-14）

用户要求将当前60条face审查网页打包供他人查看，不包含1200条非面部媒体。本节拥有离线交付包 `%OUTPUT_ROOT%/camera_face_closeup_20261014_v2/share/FaceCloseup_60_Review_20261014.zip`及同名解压目录；本机绝对路径为 `D:/UE/Lance_Work/00_engine/outputs/camera_face_closeup_20261014_v2/share/FaceCloseup_60_Review_20261014.zip`。ZIP成功生成，大小354632744字节（约338MiB/355MB）。

解压后包根 `index.html`内嵌审查数据，`media/`含60条MP4（30横屏、30竖屏）和60张poster，并附README与 `打开审查网页.cmd`入口；不依赖服务器、Python或UE，供接收者在本地打开审查。`share/package_check_v1.json`记录60条复制视频SHA与来源一致、ZIP CRC通过、离线HTML无fetch。包检查不改变面部human_acceptance=pending，也不将60条视觉接受或四条较宽极端组合改为通过。

工具策略不支持file URL，因此本轮未实际验证离线页面在浏览器中的播放；来源网页此前已完成的有界播放验证不能替代离线包实际播放验证。本次仅追加打包交付事实，没有扩展检查或更改其他owner状态。


## 17 拍摄点审查工具与两场景试点（2026-10-14）

本节拥有 `scene_site_review_20261014_v1` 的代码、配置、问题预览、试拍与恢复证据；沿用 `WF-60/WF-80`、`VAL-SCENE-01`、`OUT-WF60-SEQUENCE-TEMPLATE` 的隔离实验范围。正式输出放 `%OUTPUT_ROOT%/scene_site_review_20261014_v1/`，可重建中间文件放 `00_engine/temp/scene_site_review_20261014_v1/`。新输出默认为unclassified_protected，不因工具可重跑而授权删除，也不升级生产Gate。

### 17.1 授权、输入与风险边界

用户确认现有面部近景参数保持，授权实现并试点拍摄点审查工具。输入为现用地图、角色、动作窗口/速度、相机标准与轨迹，以及点位位置/朝向。工具需支持起点贴地、角色预览、活动范围/相机轨迹展示，环境碰撞/遮挡与地面起伏风险检查，问题动作/镜头/时间预览，配置保存恢复与配置变化重检。起点贴地只设置起始高度，不能据此宣称整段脚接触、自动地形适配或楼梯行走。

位置、朝向、地图/资产、角色、动作窗口/速度、相机配置、检测阈值或工具版本变化后，旧结果必须标记stale并重检。检测报告需保存输入签名、检测类型和采样边界；无碰撞几何、衣发体积和离散时间之间的情况仍需实际画面检查。共享UE修改和渲染由root串行执行，不保存修改原场景；如试拍需要派生资产，仅使用本轮隔离输出，不能改写旧冻结计划或历史回执。

### 17.2 候选与可复用证据

只读候选见本Run `scene_candidate_recommendation_v1.json`。空旷候选为当前 `/Game/Scenes/DesertGasStation/Maps/DesertGasStation_01`，历史点位 `[15000,-2200,-7708.5]`、yaw=0；局部遮挡候选为 `/Game/Scenes/QA_ModularParking/Maps/Map_demonstration`，历史点位 `[0,2100,0]`、yaw=0。当前路径由 `00_engine/assets/scene_folder_relocation_20261012_v1.json`解释，历史报告内原路径不改。

旧 `ue_scene_location_pilot_v1.py` 的ground_grid/clearance与 `ue_scene_character_pilot_v1.py` 的scene_plan/prepare提供参考，`ue_motion_scene_render_v1.py`拥有既有试拍渲染实现。旧survey/prepare保存派生UE资产，不是新工具只读检测的直接替代。旧报告来自 `unreal_character_import/motion_portrait_scene_pilot_20261011_v1`：停车场clearance记录柱子遮挡，可复现问题动作/镜头/时间；加油站已接受代表样片仅支撑候选，不替代现用标准的新检测。

### 17.3 当前交付、实现所有权与入口

首版R10实现及限定双场景试点于2026-10-14交付completed，human_acceptance=pending；2026-10-15操作升级与当前版本证据见§17.9。首版worker SHA `98afa166ef26ea4f47bc0ea6039fb3bc7bf7521dbea8782aee461e8715837c0e`、runtime_version=3，`delivery_validation_v1.json`拥有汇总与SHA，`delivery_runtime_v1.json`拥有真实执行过程；下一步用户手选点位并人工确认可用组合。正式固化非面部/面部参数、动作窗口/速度保持，旧1260和相机批量继续暂停；无生产Gate晋升。

本节拥有以下实验/utility实现（路径均相对项目根）：

- `00_engine/scripts/unreal/scene_site_review_geometry_v1.py`：冻结动作/相机输入、空间代理与刚体放置。
- `00_engine/scripts/unreal/ue_scene_site_review_v1.py`：编辑器点位、预览、轨迹/文字/俯看、检测、保存恢复及失效控制。
- `00_engine/scripts/unreal/scene_site_review_panel_v1.py`、`open_scene_site_review_v1.py`：独立中文面板与launcher；`tests/test_scene_site_review_worker_v1.py`、`tests/test_scene_site_review_geometry_v1.py`为本范围精准测试。
- `00_engine/scripts/unreal/scene_site_review_pilot_v1.py`、`run_scene_site_review_pilot_v1.py`：保存点位生成明确试拍计划、隔离准备/渲染/编码控制，复用既有 `encode_motion_scene_pilot_v1.py`。
- `00_engine/scripts/unreal/build_scene_site_review_gallery_v1.py`：媒体/报告发布为独立审查页，不启动UE或服务器。

从项目根执行 `python 00_engine/scripts/unreal/open_scene_site_review_v1.py`，或双击本Run `打开拍摄点审查.cmd`；连接现有datatry_02，不另开UE。单次调用为 `python 00_engine/scripts/unreal/scene_site_review_panel_v1.py --action <action> --request-file <JSON>`，仍会操作共享UE，只能在串行使用窗口执行。`launcher_status.json`、`panel_lifecycle.json`拥有启动状态；remote/replies保存请求/回执，避免超时后盲目重复提交。

### 17.4 空间输入与轨迹人工校验

`python 00_engine/scripts/unreal/scene_site_review_geometry_v1.py`默认准备30动作×21镜头×横竖=1260冻结组合，输出 `site_review_catalog_v1.json`、`site_review_local_geometry_v1.json`；`--motion-id`、`--camera-id`、`--orientation`可重复筛选，`--sample-step-frames`默认15。CLI的prepare_inputs覆盖本轮派生缓存，prepare_geometry只返回内存对象。place_geometry从原始局部空间一次刚体变换XYZ/yaw，不重拟合镜头或改变身体时钟。消费缓存前verify_sources检查源签名。

人物路线/骨点源缓存10fps，范围包含30fps插值骨点，并不等于完整衣发网格边界；检测采样为0.5秒及终点。baseline_ground_z_cm保留原地面，baseline_height_cm保留抬脚/跳跃高度。正常抬脚不能直接算地面异常。`geometry_targeted_checks_v1.json`的27258冻结相机采样精确比较、30动作插值一致性、无NumPy环境导入/完整放置检查为离线证据；3项geometry测试计入最终23项，不重复累计。

用户主要目标为清楚标出人物/相机轨迹供人工校验。绿色显示人物root路线、约八组采样肢体和活动AABB，蓝色显示相机路线；编辑器可见TextRenderActor标BODY绿色/CAM黄色的START/END及中间秒数。轨迹线/框duration=3600秒（1小时），刷新/切换显示前清除旧debug线和本工具RangeLabel再重画，restore亦清理，不沿用30秒描述。overview退出相机pilot，按人物与相机联合范围俯看并重画；面板按钮为“俯看人物与相机轨迹”。实际 `trajectory_overview.png`可见完整绿活动框/骨架、蓝相机路线和正向BODY/CAM时间标记。按G隐藏编辑器图标可更清楚；截图不等于任意视角所有标记始终无遮挡。

### 17.5 检测、签名失效与保存恢复

检测提供疑似body_collision、camera_collision、occlusion、visibility_unmeasured、ground_height/ground_missing。身体用骨段代理，相机附近/路径用8cm球代理，视锥内至多五个分散骨点用Visibility通道初筛；未能取得可测可见目标时显式保留未测提示。支持面假遮挡例外仅针对foot/ball、向上法线、目标与命中Z均在site基准5cm内；墙法线、非脚目标、超差地面仍提示。ground_height独立保留，起点贴地不等于自动地形/楼梯适配。

指纹覆盖冻结计划、采样/派生geometry/catalog、geometry与worker脚本（stat变化触发SHA，检查起止强校验）、点位map/id/XYZ/yaw、非工具Actor增删/变换、可读取PrimitiveComponent变换/可见性/mesh/material引用/碰撞profile及Visibility响应/形状与local bounds、dirty package成员。不可读字段记录unavailable；同路径且已dirty的资产内部几何或材质编辑不保证捕捉。过程每3秒和结束强制复核输入/场景，每tick复核点位；几何采样仍0.5秒，两者不能混同。变化后stale，cancelled/failed/current-only/incomplete不得冒充全量通过；只有complete、scope all、全部样本完成且当前stamp匹配才full_matrix_fresh=true。

人工三态为allowed/excluded/未确认；仅明确点击的组合写allowed_combinations，未选不自动允许。review_stamp变化清除旧草稿；保存附decisions_stamp，人工字段不进入几何stamp，过期决定不作为当前允许项。sites/<site_id>.json保存点位/报告/决定，恢复要求当前关卡匹配，不自动切图。当前复核使用 `gas_pilot_annotated`、`parking_pilot_annotated`；`sites/gas_pilot.json`、`sites/parking_pilot.json`为v2媒体冻结快照，保持原pin。

“仅关闭面板，保持 UE 现场”和窗口X暂停预览播放，不发UE取消/恢复，运行中检查可继续；“移除预览、恢复原视口并关闭”走cancel/restore，清理本工具临时Actor和标注并还原原视口。共享UE由root串行操作，不保存修改原场景。失败后先核对当前会话与已有自有job，不能因超时重放。

### 17.6 最终双场景与功能证据

`delivery_runtime_v1.json`及 `delivery_validation_v1.json`绑定最终98afa166版本。gas_pilot_annotated在 `/Game/Scenes/DesertGasStation/Maps/DesertGasStation_01`、`[15000,-2200,-7710.022602873226]`、yaw0；parking_pilot_annotated在 `/Game/Scenes/QA_ModularParking/Maps/Map_demonstration`、`[0,2100,0.40999999642349394]`、yaw0。两者各all/1260、27907/27907采样complete且记录时full_matrix_fresh=true。

加油站10项=4camera_collision＋6visibility_unmeasured；停车场221项=160occlusion＋53camera_collision＋6visibility_unmeasured＋2body_collision。各28个unmeasured_visibility_samples，ground未提示不表示脚接触/地形普适安全；全采样不等于可见性全可测或全组合人工允许。检测/衣发/无碰撞物体/采样间隙仍需人工审看。

真实preview_problem为001/front_three_quarter_full/landscape、6.5秒，SM_ColumnA3遮挡；overview成功。decision_saved保存此组合excluded；moved的X+25cm及yaw+15度使current/full/decisions_fresh均false且allowed为空；restored载入后full/decisions_fresh均true。最终Rotator明确使用pitch/yaw/roll关键字；实际yaw=14.999999999999998在15度浮点容差内，turned_actor_camera_poses显示marker/character=[0,15,0]、camera=[0,-30,0]，与expected_camera_yaw=-30一致。旧位置参数导致pitch误设的候选结论已被修复后的真实重检替代。raised_ground_probe将Z抬高20cm，当前单组合58/58采样complete、full=false，包含ground_height提示；恢复原记录后current/full/decisions_fresh均true。此阳性检查证明风险提示有效，不是自动修正地形。

`worker_offline_validation_v1.json`23项（3geometry＋20fake-UE）已绑定当前98afa166 SHA，命令为 `python -X utf8 -m pytest 00_engine/scripts/unreal/tests/test_scene_site_review_worker_v1.py 00_engine/scripts/unreal/tests/test_scene_site_review_geometry_v1.py --basetemp D:/UE/Lance_Work/00_engine/temp/site_review_pytest_yawfinal_20261014 -q`。该receipt由geometryagent按root实际23项/0.32秒执行结果刷新，不新增重复运行。`panel_offline_validation_v1.json`18项fake executor/Tk检查和 `gallery_offline_validation_v1.json`14项合成静态检查各有独立范围，不称为真实UE/媒体解码。

### 17.7 四条媒体、网页与操作面板交付

四条真实v2样片为加油站008/front_full/portrait、030/orbit_360/landscape，停车场001/front_three_quarter_full/landscape、003/front_full/portrait。root控制器命令 `python 00_engine/scripts/unreal/run_scene_site_review_pilot_v1.py`；make_plan只按保存点刚体变换，动作时钟/镜头参数保持；派生资产仅 `/Game/DataMake/Validation/SceneSiteReview20261014`。pilot_execution.log、pilot_commands/、scene_sequences/、render_receipts/及四份media_validation_site_*_v2_render.json分别记录执行、准备、渲染与真实编码核验。render按单画幅批次，receipt/plan/source pins不匹配时停止。

`python 00_engine/scripts/unreal/build_scene_site_review_gallery_v1.py [--run-root <run>]`生成gallery/index.html与review_delivery_manifest_v1.json，不启动服务器。只发布匹配plan、encoder receipt、视频/海报SHA和已有完整解码元数据的encoded_verified条目，未验证无URL。每site只取最新数字revision，再mtime_ns/filename排序；active_plan_paths/superseded_plan_paths/plan_selection_policy记录规则，旧计划/媒体不删除也不混入当前。最终4/4 playable、0pending/0warnings，active为两份v2，原sites pin保持。

服务器入口 `python 00_engine/scripts/unreal/open_common_camera_gallery_v1.py --run-root <本Run> --port 8886 --no-browser`复用Range支持，真实页面为 http://127.0.0.1:8886/gallery/index.html 。root实际浏览器四条均readyState=4、尺寸/时长正确、播放paused=false，停车场问题跳至6.5秒；证据gallery_browser.jpg。每条20张共80离散抽帧：停车场转身柱子遮挡与提示一致，为不宜组合演示；加油站环绕背光较暗；不升级为整段逐帧或全矩阵视觉通过。

独立Tk面板实际启动PID38208、launcher_status ready=true；没有Tk实拍截图或全按钮人工验收主张。实际UE视口CaptureViewport与浏览器截图不能替代Tk界面实拍。使用说明拥有手选点位、轨迹/俯看/问题预览和人工允许/排除保存的简短操作步骤；human_acceptance保持pending，下一步由用户审查。

### 17.8 输出保护、旧尝试与限定收口

沿用OUT-WF60-SEQUENCE-TEMPLATE、VAL-SCENE-01的隔离实验范围，正式输出/配置/媒体/截图在本Run，temp为可重建过程文件，新输出unclassified_protected，不授权删除或生产晋升。当前工具保存点为sites/*_annotated.json；v2媒体site_pin、冻结计划、原正式镜头、旧相机暂停证据保持。

早期runtime_pilot_parking_v1.json实际地图Highway，报告failed578/1290，取消因节点未发现未成功；不算停车场通过。shared_ue_wait_checkpoint_v1.json、runtime_resume_checkpoint_v1.json及早期a94/6d11报告只作版本历史；最终以delivery_*和_annotated记录为准。原始失败/旧计划不改写。

本轮只检查六个受影响owner、唯一current父计划/R10、当前源与交付证据、媒体原site pin及明确相关合同，耐久报告owner_docs_lightweight_check_v1.json；不运行全套测试、Catalog/Inventory重建或16子系统审计，不将历史检查当新结果。上述首版R10实现completed、人工pending；2026-10-15追加操作升级状态见§17.9。父计划保持唯一current，R02/R05和原相机批量不自动恢复。


### 17.9 拍摄点审查操作升级（2026-10-15）

本轮沿用R10追加操作升级：后台视口立即刷新、指定时刻真实身体求值、完整选用时长的人物/相机同步播放、点位内批量排除，以及逐问题人工审看与备注。前述98afa166/runtime_version=3及23项测试只证明上一版交付，不证明本次改动；本轮实现与限定验证已完成，R10按技术交付范围completed、人工审查pending；本轮证据绑定runtime_version=4、worker SHA `0c4d28d596db36e9c2b9886cc99516fb5bad53c775ec08dd15a308024f566941`。不重新启动双场景全矩阵或扩大视觉抽查。

指定时刻预览必须以当前冻结shot的身体窗口与相机帧共同求值。已定位旧缺陷：override_animation_data记录了6秒，但运行实例仍在0秒；仅保存动画参数不足以更新当前姿态。修复路径为显式set_animation_mode/set_animation/set_position，继而立即求值并刷新实时视口；后台操作需避免UE失焦后延迟到重新点击视口才显示。预览会开启实时视口并关闭后台CPU节流；“仅关闭面板”暂停播放、保留现场及后台设置，“移除预览、恢复原视口并关闭”还原原后台节流设置。它不改项目固化配置或源资产。

播放使用冻结shot的完整duration_seconds和既有window_start_seconds，人物与相机共享墙钟进度；沿用既有动作窗口、身体速度与镜头路径。面板提供播放/继续、暂停、停止回到起点、循环和当前秒数/总时长。当前同组合暂停后继续从保留时刻走，停止归零，非循环到终点结束，循环按完整时长回绕；跳转按冻结相机最近帧定位。真实UE回调下的完整播放及控制结果见下方本轮回执，测试替身不代替实际UE。

批量排除属于当前点位的人工决定，可按当前组合、当前动作全部镜头或当前镜头全部动作展开，并选择当前画幅或横竖两画幅。面板先列出具体动作/镜头/画幅及数量，再应用排除；保存仍使用allowed_combinations中的decision=excluded逐组合记录，不新增跨点位全局黑名单。默认检查剩余组合；排除后的scope=remaining不得当作全1260组合通过，全部排除时应拒绝空检查。已排除列表可恢复选中项或撤销上次选择，未选择/恢复项仍未确认。

每条问题可标confirmed_problem、acceptable、unreviewed并添加文字note，存为site.issue_reviews。问题标识按kind/action_id/camera_id/aspect/time_seconds/message稳定生成，不依赖表格排序。人工问题结论与允许/排除组合决定各有用途，标问题“可接受”不自动允许组合；两类人工内容同受review_stamp/decisions_stamp保护，输入、点位或场景改变后不能作为当前结论保存或恢复。恢复旧点位前先打开对应关卡，变更后重新检查；旧v2媒体冻结sites及其pin保持。

本轮仅对上述实现、面板、保存恢复与受影响文档合同做必要验证；无全套测试、Catalog/Inventory重建或16子系统审计。本轮限定证据为 `interaction_runtime_validation_v1.json`，旧 `delivery_validation_v1.json`继续只代表首版。root实际UE核对001/003/036各0/3/6秒共9个姿态：运行实例时刻正确，pelvis/head/hand_l/foot_r相对冻结空间输入最大误差约0.0061cm。完整12.3667秒动作由外部等待期间UE回调真实播放结束，采样身体时间与共享进度一致、background_throttle=false；循环回绕0.5秒、暂停保持、继续推进和停止归零均通过。另yaw15度的pelvis误差约0.00169cm。

当前点位实际保存并恢复1258条排除及问题confirmed_problem备注，剩余2组合88/88采样完成，scope=remaining；该演示不等于全1260检查或用户排除了这些项目。修改点位后组合决定与问题审看失效，旧签名保存被拒绝。测试替身与离线合同共43项通过，覆盖worker、geometry及panel三份定向测试；测试文件为 `tests/test_scene_site_review_worker_v1.py`、`tests/test_scene_site_review_geometry_v1.py`、`tests/test_scene_site_review_panel_v1.py`；root最终重跑43项通过、耗时5.97秒，`interaction_delivery_validation_v1.json`记录测试范围与worker/panel源SHA。当前源资产和固化相机计划保持，原v2媒体及site pin保护。

新版面板PID32384已实际启动ready、连接当前gas点位，窗口标题确认；证据为 `interaction_delivery_validation_v1.json`及launcher_status/panel_lifecycle/panel_state，面板SHA `8fd18ce19344ef92341ce02d66eddd1db92d1c38691dd700bac8cf45bcf6077d`。验证用大排除点位另存 `interaction_saved_point_validation_v1.json`，不列入用户点位菜单。实际启动与真实Tk/fake-executor测试不等于所有按钮已人工逐一验收，human_acceptance=pending。六owner限定文档/状态合同由 `interaction_owner_docs_lightweight_check_v1.json`拥有，不把该检查扩大为完整审计。

### 拍摄点俯看选择同步修正（2026-10-15）

面板 overview 请求携带当前 action_id/camera_id/aspect/time_seconds；worker runtime_version=5 先同步该选择的预览，再计算俯看范围。没有选择参数的旧调用保留当前预览行为。真实 UE 验证向前行走 MOTION_CAND_008、side_full、portrait 直接切换成功，见 scene_site_review_20261014_v1/overview_selection_fix_validation_v1.json；旧交付哈希仅对应上一版，最新 worker 哈希见该修正回执。


## 18 双动作跟随修正、横屏近距对比与全场景目录（2026-10-15）

本节拥有本轮新Run `%OUTPUT_ROOT%/camera_follow_compact_scene_20261015_v1/` 与同名temp，沿用唯一current父计划 `PLAN-2026-10-CAMERA-MOTION-SCENE-ALIGNMENT/R11`、WF-60/WF-80、VAL-SCENE-01及OUT-WF60-SEQUENCE-TEMPLATE的隔离实验范围。R11按实现与限定媒体交付范围completed，人工接受pending。只做下列三项，不恢复旧1260批次，不切换正式镜头标准，不改皮肤或其他会话输入；共享UE及渲染由root串行操作。

### 18.1 授权与有限验收

1. 修复模特步行MOTION_CAND_036与ACT_F02_CATCH_BREATH的水平跟随偏差；保留身体源、已选窗口、速度、相机相对距离/角度及镜头设计，不覆盖旧冻结计划。修正后需要真实UE预览/必要媒体和相关定向检查。
2. 制作横屏12条距离/FOV对比：弯腰伸展正面全身与正面上半身、向前行走120度环绕、起跑侧面推进，共4组×原距离/0.85/0.75。只供用户比较，未接受前不将近距变体写成现用标准。
3. 在拍摄点面板接入全部现有场景目录：当前25包、77地图、26主场景与4个既有保存点，区分主图/子关卡/资产总览/工作图，便于选择关卡并进入点位审查。目录可见不等于每图已选点或通过碰撞、构图和渲染稳定性验收。

### 18.2 双动作跟随原因与派生修正

已确认旧水平趋势使用较宽居中滤波，开头预测位置与实际起点有偏差；再强制起点归零时把这段差异带入后续轨迹。模特步行与喘气动作在上半身镜头终点形成约26.5cm和50.3cm的偏差。该问题属于这两个动作的XY跟随，不需要修改身体源或统一缩放镜头。

本节拥有 `00_engine/scripts/unreal/build_camera_follow_correction_v1.py` 与 `tests/test_camera_follow_correction_v1.py`。当前派生修正以0.18秒局部平滑、首尾残差在3sigma范围内平滑消除，保持原始首尾XY；对相机和look_at施加同一XY平移，保留原始camera-to-target向量、全Z、旋转、FOV、距离/推拉/环绕参数、身体时钟和相对躯干表现。80条受影响非面部轨迹派生到本Run，原shot_id供场景几何关联，旧冻结输入不覆盖；其余28动作及60个面部shot对象保持。

`follow_correction_v1.json`与 `follow_correction_evidence_v1.json`拥有派生版本和离线限定合同；`corrected_full_nonface_plan_v1.json`为修正后的完整派生输入，`camera_trial_plan_v1.json`为必要试拍子集。离线success只证明绑定的数值/字段/骨点代理检查，不代表真实UE姿态、衣发轮廓或媒体已验收。当前工具runtime_version=6已消费带签名的修正overlay；真实UE验证见§18.5。改用派生输入后原点位检查/人工决定应按既有review_stamp规则重检。

### 18.3 横屏近距/FOV对比

本节拥有 `00_engine/scripts/unreal/build_camera_compact_comparison_v1.py` 与 `tests/test_camera_compact_comparison_v1.py`。脚本离线生成 `camera_compact_comparison_plan_v1.json`、`compact_comparison_geometry_v1.json` 及 `compact_review_delivery_manifest_v1.json`/独立网页；不连接UE或修改已接受输入。计划为12个横屏1280×720变体，保留各动作现有选用时长/速度。最终12条比较媒体全部合格可播，合并16条跟随前后对照，共28/28由compact_review_delivery_manifest_v1.json发布。

相机位置按 `C_new=A+k*(C_old-A)`靠近冻结瞄准点，水平FOV满足 `tan(hfov_new/2)=tan(hfov_old/2)/k`，k为1/0.85/0.75。该关系精确保留穿过瞄准点且垂直视线的平面投影，不保证具有前后深度的人物、衣发和场景各点投影完全相同；近距离透视变化及穿模风险仍需看真实样片。原距离为对照，0.85/0.75是候选；human_acceptance=pending，不切换标准。网页只按匹配plan/媒体receipt及SHA核验结果开放URL，未验证项不得伪装可播。

### 18.4 全场景目录与面板入口

本节拥有 `00_engine/scripts/unreal/scene_site_catalog_v1.py` 与 `tests/test_scene_site_catalog_v1.py`；面板和UE入口继续由§17拥有，本节解释新增目录接入。目录只读当前Content/Scenes地图、现用路径overlay及scene_site_review_20261014_v1/sites保存点，不导入UE、不移动资产。输出 `scene_site_catalog_v1.json` 当前统计为25包/77地图/26主图/4已保存点；这4点不是77图各有4点，且包含两份旧媒体冻结sites快照及两份_annotated操作记录；日常复核用_annotated，保持旧site pin。重新读取应能看到后来新增的保存点，只有明确选择后才由串行UE入口操作场景。

主图分类来自现有主场景索引并应用当前迁移路径；工作图、灯光子关卡、建筑组合和总览图显式区分，不能让用户误以为全是独立可拍场景。真实UE已按目录打开停车场、拒绝无效图，并在修正动作/镜头选择后俯看，随后恢复拍摄前隔离Recovery现场；新版面板PID47140已启动ready。目录及入口不等于77图逐一加载、选点、检查或渲染通过。

### 18.5 当前验证与恢复边界

本节还拥有 `00_engine/scripts/unreal/run_follow_compact_review_v1.py`、`ue_follow_compact_review_v1.py`：root串行复用既有prepare/render/encode/receipt流程，默认渲染本Run的camera_compact_comparison_plan_v1.json；跟随必要样片使用 `--plan camera_trial_plan_v1.json --prefix follow`，可用 `--ids`限定shot。UE派生资产隔离在 `/Game/DataMake/Validation/CameraFollowCompact20261015`，每次校验冻结plan SHA，批次锁与逐片合格receipt决定重用/续跑，不能因进度文件或命令退出码认定媒体可播。示例入口为 `python 00_engine/scripts/unreal/run_follow_compact_review_v1.py`，只由共享UE执行者操作。

`scene_recovery_v1.json`记录本轮开拍前的游乐园现场被保存在隔离Recovery关卡，以保护既有未保存状态；原现场与后续恢复由root串行核对，目录生成器不承担恢复操作。当前 `follow_correction_regression_v1.json`记录4项离线跟随定向测试通过（5.23秒），其范围不包含UE姿态或媒体。

最终限定验证完成，`delivery_validation_v1.json`汇总28媒体、82测试、面板及限定浏览器事实并绑定五份证据SHA。`follow_scene_runtime_validation_v1.json`记录真实UE：036与ACT_F02_CATCH_BREATH各0/1/3/6秒共8个时点实际时间一致，相机与派生轨迹位置误差为0、pelvis对冻结骨点最大误差约0.00536cm；目录打开停车场、无效图拒绝、喘气/rear_three_quarter_upper/portrait在3秒正确俯看及恢复隔离Recovery现场均通过。worker SHA `9a57975206aa5035745553cad0a7fddda2a6427d49cc473bc5a2e998f225edc7`，geometry SHA `ba45aa2034f23acbae679a21d41d92d8eb4a578cfabdb304e0522f9e41315202`，修正manifest SHA `34876f086b23697621855890d62231d6045da969e02f47b20862e5715729a9e7`。

相关六份定向测试最终82/82通过（root执行50.76秒），覆盖follow修正、场景geometry/worker/panel、compact比较及scene catalog；`follow_correction_integration_tests_v1.json`内62项是其中离线整合范围，不与82或较早4项相加。代码/plan pins保护、错动作/错身份/时钟篡改拒绝、修正缓存与非目标动作/面部对象保持已覆盖；没有借R10旧33/33或43项作为本次通过。

最终 `compact_review_delivery_manifest_v1.json`发布28/28：12条横屏近距/FOV比较，16条跟随前后对照（8条原媒体精确复用、8条新修正媒体），原媒体来源由media_validation_reused_follow_baseline_v1.json拥有。root实际浏览器 http://127.0.0.1:8896/gallery/index.html 显示28/28及风险说明，第一组前后同步起播的两个video均readyState=4、paused=false、time约0.132/0.128秒；后续筛选测试时tab不可用，因此不声称筛选交互或28条逐一浏览器播放通过。新版面板launcher ready=true、PID47140，已为用户重新打开。

`compact_visual_review_v1.json`拥有12条/240离散帧限定观察：没有观察到近距新增的明显极端变形或整体出画；原上半身约4.53秒头顶裁切、侧面推进后段原有裁腿保留。`follow_visual_review_v1.json`拥有16条/320离散帧、8组前后对照，均可见水平跟随改善；ACT_F02_CATCH_BREATH竖屏两个镜头深弯腰仍向右裁头，all_framing_pass=false、human_acceptance=pending。没有连续逐帧视觉审查，也未审看全部80修正路径。

R11按技术交付范围completed，父计划仍唯一current。下一步用户审看8896跟随改善、喘气竖屏剩余裁头及k1/.85/.75透视/构图，决定近距候选是否采用；当前正式横屏/竖屏标准不变，旧1260批次继续暂停，无生产Gate晋升。本轮仅六owner与受影响合同检查，结果由本Run `owner_docs_lightweight_check_v1.json`拥有；不运行全套测试、Catalog/Inventory重建或全树审计。新输出unclassified_protected，旧媒体、旧冻结计划、正式标准和原暂停记录保持。


## 19 全动作跟随审计、横屏近距标准与七档对照（2026-10-15）

本节保留v2交付范围与当时接受状态；当前全部新增240路径接受及50%横屏标准以§20为准，26主场景后续执行以§21为准。

本节拥有新Run `%OUTPUT_ROOT%/camera_follow_general_compact_20261015_v2/`与同名temp，沿用唯一current父计划R12–R14、WF-60/WF-80、VAL-SCENE-01与OUT-WF60-SEQUENCE-TEMPLATE隔离实验范围。R12–R14按实现与限定交付范围completed，新增6动作跟随及本轮新距离取舍human_acceptance=pending。`delivery_validation_v2.json`为最终汇总，绑定13份证据SHA；新输出unclassified_protected，不授权删除旧媒体或旧冻结计划。

### 19.1 已接受范围与本轮边界

`user_acceptance_20261015_v1.json`绑定前轮跟随/比较/交付SHA：用户接受§18的8组跟随前后对照，喘气竖屏局部裁切为有意保留；采纳横屏靠近25%（k=.75）及相应FOV补偿。接受只覆盖前轮已审范围与非面部横屏标准，不代签本轮新增6动作或新距离档。旧follow_visual_review_v1.json为接受前观察，不改写旧报告。

现用标准只改变20个非面部横屏配方的600条轨迹，竖屏600条与独立面部60条保持。身体源、既有窗口/速度与原镜头设计保持；旧1260批次继续暂停，无生产Gate晋升，皮肤和其他会话输入保护。

### 19.2 全30动作审计与320条跟随overlay

本节新增拥有`00_engine/scripts/unreal/build_camera_follow_general_correction_v2.py`、`tests/test_camera_follow_general_correction_v2.py`；生成命令为`python 00_engine/scripts/unreal/build_camera_follow_general_correction_v2.py`。§18的v1脚本/输入保持已接受算法来源。

`follow_correction_evidence_v2.json`完成全30动作数值审计：前轮036/喘气2动作的80条修正对象逐字保持；其余28中新增6动作需要同类修正：摆臂转身001、向前行走008、边走边思考030、起跑035、ACT_F01_SEXY_DANCE、ACT_M04_LIVING_ROOM_SWING。新增240条路径，累计320条原ID overlay由`follow_correction_v2.json`拥有；其他22动作880个shot对象保持，全部60面部计划SHA保持。

本库以pelvis平面活动范围对角线超过100cm且旧趋势P95误差超过20cm筛出明显平移失真，是冻结库诊断阈值，不是普适生产Gate。原因同时包含1.15秒平滑抑制真实加减速/反向，以及原始起点锚定将滤波初始预测误差带入整段；仅修边界而保持旧平滑不足以解决整段误差。共用算法沿用已接受0.18秒局部线性平滑及3sigma首尾残差平滑移除，保留0.9秒躯干局部跟随、全Z、原相机向量、身体时钟及镜头设计，不按动作另找数值参数。

`corrected_full_nonface_plan_v2.json`为完整1200条跟随派生，`camera_trial_plan_v2.json`为新增240条after输入；`follow_comparison_plan_v2.json`为13组26条原距离before/after。`follow_camera_kinematics_v2.json`记录13组camera XYZ速度/加速度/jerk：响应真实位移更快，也比旧过度平滑方案更急，尤其F01/M04需通过连续播放判断舒适度；误差下降不等于构图或舒适度接受。

### 19.3 横屏靠近25%的现用机器标准

本节新增拥有`00_engine/scripts/unreal/camera_standard_v2.py`与`tests/test_camera_standard_v2.py`；机器配置为本Run `horizontal_camera_standard_v2.json`，schema=camera_horizontal_standard_v2，standard_id=nonface_landscape_distance075_fov_compensated_v2，配置SHA `df6c0d473de4173b252885450d3086ebfc4e7eaace5fff3cab0321ac7a6caad8`。

先在原距离shot上完成跟随overlay，再执行`C_new=A+.75*(C_original-A)`与`tan(hfov_new/2)=tan(hfov_original/2)/.75`。这只精确保留瞄准平面投影，人物前后深度和背景透视仍会变化。`load_config()`核对原计划/用户接受pins，`apply_standard()`复制派生而不修改输入；相同配置重复应用只有在完整派生trajectory SHA一致时幂等，配置/标记/路径改变则拒绝，避免二次变成0.5625。旧构图/距离诊断标记superseded，派生路径指标重算；竖屏不重复叠加原15%。

§17拥有的geometry/worker已实际接入新320 overlay及600横屏标准，runtime_version=7。geometry与worker消费相同1260条shot；加载/cache依赖涵盖接受文件及原始源的传递pins，输入改变后旧点位检查/人工决定须重检。现场数据仍位于`scene_site_review_20261014_v1/site_review_local_geometry_v1.json`与`site_review_catalog_v1.json`，当前SHA分别为`0a4546bdfe267da1f612c3862c237cc7dff4cd5a98958c6d4ddd33fb2c0ca2f5`、`8b4d9d317683c7d054a4ff324428dffffc4695c952927c3a01c9b3abd38a122e`；源指纹为`022b9de97549e4495676bf7b557ea0b777aca6ccc0ddab8b702a8a0baf79a50a`。

### 19.4 七档距离与13组跟随媒体

`build_camera_compact_comparison_v1.py`及其定向test继续由本节新增扩展拥有；`--general-six`生成`camera_compact_comparison_plan_v1.json`，SHA `6874a5df43637cdbdf3b90db490dfa799eb145493d033d06ae3693f6225d3b77`。四组为伸展正面全身/上半身、行走120度环绕、起跑侧面推进，各靠近0/10/20/30/40/50%并加25%现用参考，共28条。所有比例基于不可变原横屏距离，不在k=.75上重复相乘；`compact_comparison_geometry_v1.json`校核所有键及终点公式，不证明身体轮廓/碰撞/遮挡。

`follow_comparison_standard_v2.json`（SHA `d77f9ca00eb10286cfe11749800ee2fbd825de3e4f6dcca682bd8ffb5298f0f2`）是最终跟随13组26条：12横屏before/after两侧共同采用k=.75，14竖屏距离保持，仅比较跟随变化。原comparison_pairs保留原始源ID作历史映射；最终媒体按comparison_group_id/variant解析，准确解析由follow_visual_review_v2.json记录，不把旧ID当作当前视频索引。

本节新增拥有`00_engine/scripts/unreal/reuse_camera_follow_portrait_v2.py`。最终54条=28距离＋26跟随，39新渲染＋15重新完整解码复用：距离8条k1/k.75由`media_validation_reused_compact_reference_v2.json`拥有；跟随7竖屏before由`media_validation_reused_follow_portrait_baseline_v2.json`与`follow_portrait_standard_binding_v2.json`拥有。后者明确comparison metadata派生回执、最终竖屏shot对象保持及runner核验7条，不伪称全部原始shot字段完全相同。

root串行复用§18 `run_follow_compact_review_v1.py`、`ue_follow_compact_review_v1.py`及prepare/render/encode/receipt流程，使用`--run-root 00_engine/outputs/camera_follow_general_compact_20261015_v2`，距离计划为camera_compact_comparison_plan_v1.json，跟随计划用`--plan follow_comparison_standard_v2.json`；派生UE资产隔离于`/Game/DataMake/Validation/CameraFollowGeneralCompact20261015`。逐片合格receipt、plan/source pins决定复用和续跑，不从进度文件认定可播。`compact_review_delivery_manifest_v1.json`最终54/54才开放全部URL；`gallery_structure_validation_v2.json`绑定最终HTML/plan/manifest，13组跟随画幅独立、四组距离各七档。

### 19.5 实际UE、定向测试与视觉边界

`follow_general_runtime_validation_v2.json`记录root实际UE36检查：新增6动作×横竖×3时点，运行实例时钟正确；相机位置最大误差约7.1e-15cm、FOV约1.12e-6度，pelvis对缓存骨点最大误差约0.878505cm（缓存插值边界），不是像素一致性或逐帧全组合检查。runtime7消费当前标准与overlay，通过后恢复`/Game/DataMake/Validation/CameraFollowCompact20261015/Recovery/L_AmusementPark_PreReview_20261015`现场。worker/geometry准确源码及全部传递输入pins在该回执sources中。

四份当前定向测试分别记录：`follow_correction_regression_v2.json`5项/6.53秒，`camera_standard_v2_tests_v1.json`12项/13.79秒，`scene_standard_composition_tests_v2.json`61项/42.56秒，`compact_comparison_tests_v2.json`21项/10.80秒。其源码/test/config SHA由各回执绑定；geometry/worker测试含actual1260离线对象相等、320严格scope、600标准、60face保持及传递cache guard，UE部分为fake fixtures，不代替上段实际UE。没有借旧82项、旧runtime6或历史全套结果。 最后将网页引导中的“原速”改为“同组使用相同片段、时长和播放速度”，以保留向前行走既有0.6倍速度；21项测试早于这次纯文案修正，其builder pin对应修正前源码。最终文字由更新后的gallery_structure_validation_v2.json及root浏览器重载核验，未重复测试或改媒体/计划。

`follow_visual_review_v2.json`为13组26条×20=520离散采样图直接观察，13组均看到横向跟随改善；after采样无明显头部出画，M04竖屏两组头顶仍近边缘，all_framing_pass=false。`compact_visual_review_v2.json`为20新片400图＋4基线80图，共24条480图；伸展front_upper原已有头顶贴边/局部裁切，k=.5约4.53秒更明显，网页提示可按构图取舍保留。两报告均非连续逐帧或舒适度人工接受，未覆盖全部240新增路径；F01/M04快速反转的响应取舍仍待用户。

### 19.6 网页、使用与限定文档收口

当前入口为 http://127.0.0.1:8897/gallery/index.html ，或本Run `gallery/打开相机比较.cmd`。root实际浏览器显示54/54，第一组双视频readyState=4且起播；切到距离比较显示4组，首组7个video已发起播放，立即采样为6个ready4、1个ready1。页面随后暂停并保留打开；没有声称54条均在浏览器逐一播放。精确有界事实归delivery_validation_v2.json.browser。

`使用说明.md`说明同步播放、原距离百分比、F01/M04舒适度、可接受局部裁切和点位变化后重检；场景目录仍为可选择入口，不等于全部77图通过选点/渲染。R12–R14技术交付completed，父计划保持唯一current，R02/R05原暂停及R06人工检查边界保持；下一步用户查看8897并在拍摄点面板重新检查实际可用组合。

本轮只检查六个受影响owner及因机器权威变化新增的Registry反查、明确相关合同；最终报告为`owner_docs_lightweight_check_v2.json`。不运行全套测试、Catalog/Inventory重建或16子系统审计，未执行项不标通过，不晋升生产Gate。


## 20 新增跟随接受与横屏靠近50现用标准（2026-10-15）

本节拥有Run `%OUTPUT_ROOT%/camera_standard050_accepted_20261015_v3/`及同名temp，沿用唯一current父计划R15、WF-60/WF-80、VAL-SCENE-01、OUT-WF60-SEQUENCE-TEMPLATE。R15按当前标准发布、工具接入与限定验证范围completed；整个goal已扩展到§21的R16，不在此结项。仅必要受影响检查，无全套测试/清单重建/全树审计或生产Gate晋升。

### 20.1 当前接受与不可变来源

`user_acceptance_v3.json`拥有用户当前接受：新增6动作全部240条修正路径、所有20非面部配方与两画幅均接受，不限26条展示媒体；前轮80条保持，累计320条overlay。当前接受由外部回执关联`camera_follow_general_compact_20261015_v2/follow_correction_v2.json`（SHA `2b8e12b4628111b3d64050c4cef8171e0abee5cdcbebcfab723cff670e130817`），旧文件内pending与旧视觉报告不改写，不假称用户逐片看过240条。

横屏标准改为最初原距离k=.5并补偿FOV，作用600条非面部横屏；600竖屏与独立60面部保持。旧k=.75配置、比较计划/媒体及320overlay冻结；旧8897网页的25%现用参考是当时标注，不再决定当前面板参数。现用50%只应用一次，不在k=.75上再乘.5。

### 20.2 实现、机器权威与复现边界

本节新增拥有`00_engine/scripts/unreal/camera_standard_v3.py`、`tests/test_camera_standard_v3.py`。配置为本Run `horizontal_camera_standard_v3.json`，实际兼容schema仍为`camera_horizontal_standard_v2`，standard_id=`nonface_landscape_distance050_fov_compensated_v3`；配置SHA `f11d2f1a6dd211a0b4ce088227f78893d411243dc7777b81630bcaafe8d79402`，helper SHA `0fdc734416b4b45b571bf2b3308569e7d1fca07bf5b3dbe1c076113decc10074`。

先从冻结原距离shot加载已接受320跟随overlay，再以`C_new=A+.5*(C_original-A)`及`tan(hfov_new/2)=tan(hfov_original/2)/.5`派生。保持身体源/窗口/速度、镜头方向与设计；来源/接受pins校验、完整派生轨迹幂等保护及旧诊断superseded语义沿用§19，不接受重复缩放或把比较候选当原始标准输入。视差/碰撞/局部裁切仍按实际场景判断，标准采纳不代替全部场景适拍接受。

§17 geometry/worker现为runtime8，已消费600个k=.5横屏与完整320 overlay；输入/缓存签名包含当前接受、配置、helper及传递来源。`site_review_local_geometry_v1.json`、`site_review_catalog_v1.json`仍在scene_site_review_20261014_v1，其v3派生SHA分别为`2ba0ad0d64f5098e8363717c9d0a3de99bcdb525ba50d9d6640ffa20672633c8`、`08e21ce88f941634fa8b89ec0e45ed5f7825586e38ce53855bd4a69fffd966d8`。旧点位检查与人工决定须按新签名重检；原媒体冻结sites保护。

### 20.3 当前实际验证与下一工作

`matrix_validation_v3.json`记录1260条离线消费成功：600横屏k=.5、600竖屏及60面部原对象保持；8个已接受修正动作各40条完整320生效。最大距离公式误差约1.14e-13cm，传递源pins在sources中；此为数值/输入闭包，不是新增1260条媒体。

`runtime_validation_v3.json`为root真实UE36时点（6动作×横竖×3）验证，runtime8、相机最大误差约1.42e-14cm、FOV约1.55e-7度，pelvis对缓存源姿态最大误差约0.878505cm。actual_time是选用组合片时间，source_time按原源窗口/速度映射，向前行走原0.6倍保持；不再把两种时钟直接相减。验证后恢复隔离Recovery游乐园现场。准确worker/geometry及全部来源pins归该回执。

`delivery_validation_v3.json`记录12项通过、13.40秒及7份源SHA，包括当前接受回执与原320 overlay；测试从`00_engine/scripts/unreal`执行`python -m pytest tests/test_camera_standard_v3.py -q`。本轮不重跑旧99项或借旧runtime7，准确helper/test/config pins由该汇总拥有。新标准已可用于拍摄点工具，但全部26主场景的点位/曝光/代表视频尚未交付，继续R16；不能在R15完成时结束扩展goal。


## 21 全部主场景拍摄点与曝光审查（2026-10-15）

本节拥有新Run `%OUTPUT_ROOT%/all_primary_scene_sites_20261015_v1/`与同名temp，沿用唯一current父计划R16、WF-60/WF-80、VAL-SCENE-01与OUT-WF60-SEQUENCE-TEMPLATE。R15发布与限定实际验证已完成，当前R16 in_progress，由root串行执行UE选点/场景调整及必要代表渲染；独立agents仅并行准备选点/网页媒体实现，不并发覆盖共享UE场景。

用户最新范围只要求渲染所用关卡来自既有主场景：直接使用现成26主关卡清单，不重新筛选主目录、不整理目录，也不扩展到其余51层。授权为这26张主场景各选1个拍摄点；每点以当前k=.5非面部横屏、保持竖屏和独立面部的完整30动作×21镜头×2画幅1260组合检查，总计划32760组合。可排除不合适组合，但需保存具体动作/镜头/画幅、问题时刻、理由和未覆盖边界；剩余范围通过不得冒称全1260允许。自动几何/碰撞/地面/可见性检查仍有§17既有局限，点位与曝光合理性需代表真实画面支撑。

允许按场景考虑曝光与相机调整，须记录场景级配置、适用范围和调整前后依据；全局相机标准与身体源/窗口/速度不静默改写，旧冻结计划/媒体不覆盖。禁止借此删除源场景或角色资产。每场景最终应有保存点/源指纹、检查范围、可用/排除/失败状态、场景曝光/相机例外及代表媒体/网页入口，未完成和资源问题明确登记，不把目录可选或命令成功当作26场景完成。

准确执行脚本、machine manifests、实际点位/检查/曝光/媒体与恢复证据由root完成后在本节登记；不凭脚本准备晋升完成。当前goal已扩展，不能在R15完成时结项；要等R16本轮场景结果与网页/必要媒体完成后再判断交付范围。只做本轮受影响检查，不恢复旧1260相机批次、全套审计或无关清理。



### 21.1 本轮脚本所有者与执行边界

下列脚本均由本节拥有，生命周期为本轮`experimental`选点/代表渲染执行范围，不因存在或单次成功晋升正式数据生产能力。共享UE的加载、预览、渲染与恢复仅root串行执行；离线agent不能调用实际UE入口。

| 脚本 | 职责与边界 |
| --- | --- |
| [scene_site_survey_v1.py](../../../../../../00_engine/scripts/unreal/scene_site_survey_v1.py) | 离线准备固定26目录、当前1260几何与初筛代理；不连接UE、不重判地图用途 |
| [ue_all_primary_scene_survey_v1.py](../../../../../../00_engine/scripts/unreal/ue_all_primary_scene_survey_v1.py) | root对已加载关卡执行只读分片选点/完整矩阵采样；本模块不加载地图、不spawn、不保存资产 |
| [ue_primary_scene_candidate_retry_v1.py](../../../../../../00_engine/scripts/unreal/ue_primary_scene_candidate_retry_v1.py) | root复用已保存候选，重测现场与完整矩阵；不重新搜索锚点、不加载/保存地图 |
| [run_primary_scene_surveys_v1.py](../../../../../../00_engine/scripts/unreal/run_primary_scene_surveys_v1.py) | root唯一串行地图调度器，按固定26清单加载并执行测量；命令内失败也须拒绝，不重新筛主图 |
| [build_primary_scene_samples_v1.py](../../../../../../00_engine/scripts/unreal/build_primary_scene_samples_v1.py) | 离线初始化固定26卡片、按选点revision冻结代表片计划与生成网页；不连接UE |
| [ue_primary_scene_samples_v1.py](../../../../../../00_engine/scripts/unreal/ue_primary_scene_samples_v1.py) | root的隔离样片准备/相机曝光适配，仅保存本Run副本并拒绝原场景及streamed子层Actor写入 |
| [run_primary_scene_samples_v1.py](../../../../../../00_engine/scripts/unreal/run_primary_scene_samples_v1.py) | root串行准备/渲染/编码/receipt核验，按site和画幅小批推进，已核验媒体可复用，STOP阻止后续提交 |

定向test同归本节：[test_scene_site_survey_v1.py](../../../../../../00_engine/scripts/unreal/tests/test_scene_site_survey_v1.py)、[test_primary_scene_candidate_retry_v1.py](../../../../../../00_engine/scripts/unreal/tests/test_primary_scene_candidate_retry_v1.py)、[test_primary_scene_samples_v1.py](../../../../../../00_engine/scripts/unreal/tests/test_primary_scene_samples_v1.py)。`survey_script_validation_v1.json`记录6项/0.14秒及语法检查，含模拟完整矩阵；`candidate_retry_validation_v1.json`记录4项/0.04秒，覆盖明确候选、无输入修改和命令失败拒绝；`scene_sample_code_tests_v1.json`记录18项/0.97秒，覆盖固定26目录、原0.6倍身体时钟、隔离保存/原子层保护、点位revision、曝光readback、逐片复用及STOP。这些是各自受影响离线/替身合同，不是26图实际通过；本次文档维护不重复测试、不重建Catalog或全树审计。

### 21.2 固定目录、候选输出与样片机器入口

`survey_inventory_v1.json`是现有primary标记26图的原样使用清单，不重新筛选/组织主目录，不运行另外51非主层。`survey_local_geometry_v1.json`为当前1260组合，`survey_screen_proxies_v1.json`为有限初筛代理；有限代理只用于找候选，必须再做完整采样。

实际测量分图写`surveys/`、`candidate_sites/`，`checkpoints/`约15秒保存进展，`survey_progress.json`表示当前执行，不代替完成报告。疑似碰撞/遮挡不自动转成confirmed_exclusions，也不据此把整张主图判作不可用；候选变化需重测，保留先前尝试与来源pins。

代表媒体输入为`scene_samples_sites_v1.json`（固定26图的site/position/yaw/exposure_compensation/exclusions/revision）、`scene_samples_index_v1.json`和各site独立`plans/`。默认每点各一条横屏环绕与竖屏正面全身代表片，默认组合被排除时使用兼容候选并明确标注；无可用组合仍保留场景卡与原因。点位/曝光/排除改变须用新revision，不覆盖已经冻结的样片计划。`scene_samples_delivery_v1.json`与`gallery/index.html`只为真实receipt/源pin和媒体SHA核验合格的片提供URL；26张卡片存在、准备成功和渲染进度都不等于26场景完成。

相机曝光补偿0保留场景设置，非0只覆盖样片相机bias并读回核对，不为提亮直接改写原地图灯光。隔离样片资产只在`/Game/DataMake/Validation/AllPrimarySceneSites20261015`，原场景与原streamed子层Actor写入被拒绝。`scene_sample_gallery_preparation_v1.json`仅代表最初26卡片/0媒体的页面准备与JS语法检查，后续媒体进度以当前delivery逐片回执为准，不把最初0或后来的局部可播当作全体交付。

### 21.3 游乐园初始检查点与预览恢复

游乐园首轮`surveys/primary_00_r0_20261015_031245.json`已完成1260组合、27907/27907离散采样：1249组合未报代理冲突、11组合有16项疑似问题，无自动confirmed排除。`primary_00_initial_issue_diagnosis_v1.json`将疑似问题定位为orbit_360轨迹与同一SM_Swings_A_6秋千相关，ground/body问题0；此为代理风险，不是实际穿模或不可避免组合结论。较远候选`[-5114,7686,100]`、yaw0已按独立r1尝试复核，完整1260组合采样未报代理冲突；原r0疑似报告保持。两条代表样片已完成核验，`root_execution_progress_v1.json`保存有限画面观察：人物/地面清楚，暖亮场景暂不加正曝光；该结果不是全部动作镜头人工接受。

root已在丢弃脏预览现场之前成功保存隔离备份`/Game/DataMake/Validation/AllPrimarySceneSites20261015/Recovery/L_AmusementPark_PreviewBackup_0315`；对应本地umap存在已由本轮文档检查确认。该备份保护当时预览，不能替代原场景资产或宣称全部26场景有备份/已恢复。恢复、再开图及共享现场变更继续由root协调。

R16保持in_progress，后续批量进展、重试/过期结果与媒体分别由survey_batch_progress、各surveys和scene_samples_delivery拥有；不在这里复制变化中的总计。R15保持completed。只有本轮26图场景结果、可用/排除/限制及网页/必要代表视频完成后才判断扩展goal交付，不因首图通过或脚本准备完成结束goal。


### 21.4 有界后续辅助脚本与冻结v1

以下辅助脚本同归本节，保持本轮experimental/诊断范围；实际UE调用仍由root串行协调。

| 辅助脚本 | 职责与边界 |
| --- | --- |
| [merge_primary_scene_surveys_v1.py](../../../../../../00_engine/scripts/unreal/merge_primary_scene_surveys_v1.py) | 离线合并完整且源pin匹配的1260报告；只给空点位选择候选，保留root点位/曝光/排除、冻结计划及并发编辑保护；疑似项只留警告 |
| [ue_primary_scene_candidate_retry_v2.py](../../../../../../00_engine/scripts/unreal/ue_primary_scene_candidate_retry_v2.py) | 单独v2入口，允许root对有初筛疑似项的明确既存候选显式opt-in并写理由；原findings保留，不修改v1或消除疑似记录 |
| [ue_scene_signature_diff_probe_v1.py](../../../../../../00_engine/scripts/unreal/ue_scene_signature_diff_probe_v1.py) | root只读比较runtime8场景签名即时/下一tick的具体component字段变化；不放宽签名、不接受stale报告 |
| [scene_site_terrain_probe_v1.py](../../../../../../00_engine/scripts/unreal/scene_site_terrain_probe_v1.py) | 离线依据已测Landscape边界/Z范围生成有界地面网格计划，不修改地形/动作/平地阈值 |
| [ue_scene_terrain_probe_v1.py](../../../../../../00_engine/scripts/unreal/ue_scene_terrain_probe_v1.py) | root只读分片执行地面平坦区探针，保持既有3cm条件；探针结果不是点位完整矩阵或场景排除结论 |
| [ue_primary_scene_survey_guarded_v2.py](../../../../../../00_engine/scripts/unreal/ue_primary_scene_survey_guarded_v2.py) | 独立root入口增加Slate回调重入保护：嵌套回调跳过推进，普通下一tick恢复；不加载地图，不修改冻结v1算法、源核验和完整矩阵 |

对应定向test同归本节：[test_merge_primary_scene_surveys_v1.py](../../../../../../00_engine/scripts/unreal/tests/test_merge_primary_scene_surveys_v1.py)、[test_primary_scene_survey_followups_v1.py](../../../../../../00_engine/scripts/unreal/tests/test_primary_scene_survey_followups_v1.py)。`scene_survey_merge_tests_v1.json`的26项/1.91秒包含既有代表样片合同及新增合并合同，不与早期18项相加；`survey_followup_helpers_validation_v1.json`记录5项/0.04秒离线检查和语法检查。`guarded_callback_validation_v2.json`是独立guard的五项离线行为检查（嵌套跳过、异常时flag复原等），ue_execution=false，不把它当作京都真实重试完成。冻结`ue_all_primary_scene_survey_v1.py` SHA保持`37a461c1c87e88af05d91355fe388b895e108965bbdfcfbac09f5d2659069cc2`；新guard不覆盖历史失败或重新签发旧报告。

### 21.5 批次恢复与当前执行边界

首轮已推进到现有固定目录中的京都小巷（index11），其r0报告`surveys/primary_11_r0_20261015_035652.json`明确failed，异常为`generator already executing`，不是场景被判不适合。root改用独立guarded_v2重试，实际结果仍以新尝试回执为准，不因离线guard检查成功把旧失败翻成通过。

随后index12远程发现连接失败时，root确认既有UE进程53452仍存活且能响应，恢复连接后继续，没有重启UE。此为当时恢复检查点，不以旧PID作为后来自动重启/恢复依据。京都重试后由root串行driver会话54691继续剩余index12..25；准确当前进展由survey_batch_progress、commands与各surveys拥有，文档不重复变化中的成功/失败总数。

游乐园r1已有1260采样无代理冲突及两条合格代表媒体。日式村落`surveys/primary_09_r0_20261015_035513.json`也有完整1260采样无代理冲突，代表计划已准备但本检查点尚未渲染；准备不等于媒体可播。其他疑似冲突、地面候选不足或stale结果继续有向诊断/重试，既不自动排除整图，也不把stale结果合并为当前安全点位。原目录26张不重筛、不改变用途、不运行其他51层。

R16继续in_progress，完整场景结果、曝光/相机取舍及网页代表媒体尚未全部交付。没有本轮整体完成、全26图安全或人工接受主张，不执行全套审计、清单重建、资产删除或生产Gate晋升。


### 21.6 近主景指定点位与最小新增入口

初期自动候选存在远离主要建筑/场景特色的问题，低代理冲突不能代替合适拍摄内容。root正在重选靠近主景的点位；固定26主场景目录不变，不因点位不足重新筛目录或把整图拒绝。后续点位必须结合代表画面判断主景内容、人物可见性和曝光，不能把远处空地作为无冲突兜底。

以下入口同归本节experimental范围，实际UE仅root串行执行：

| 入口 | 作用与保护边界 |
| --- | --- |
| [ue_primary_scene_explicit_point_v1.py](../../../../../../00_engine/scripts/unreal/ue_primary_scene_explicit_point_v1.py) | root强制指定XY/yaw，原九点地面/站立→初筛→完整1260；请求Z与实测支撑Z分存，不退回远处自动锚点，初筛疑点需显式flag及理由，地面失败只拒绝该点 |
| [ue_primary_scene_survey_dual_v3.py](../../../../../../00_engine/scripts/unreal/ue_primary_scene_survey_dual_v3.py) | 仅survey的独立私有worker入口，碰撞代理稳定性与完整原始外观证据分存；不修改全局runtime8，不追认旧stale |
| [run_primary_scene_candidate_retries_v1.py](../../../../../../00_engine/scripts/unreal/run_primary_scene_candidate_retries_v1.py) | root根据root_candidate_reselections_v1.json显式点位/朝向/理由串行复查；复用须位置/朝向及源pins匹配，其他survey/MRQ未结束时不得并发切图 |

`explicit_point_validation_v1.json`只记录强制XY/yaw、Z分存、明确允许初筛疑点和地面失败无fallback的离线检查，ue_execution=false；不把它当作点位实际完成。指定点位现场仍保留源pins、原签名与重入保护，坐标/曝光改变须新revision，不改已冻结样片。

### 21.7 草层原始变化、独立dual入口与待实测边界

樱花近主景旧r2 `surveys/primary_03_r2_20261015_041926.json`仍为stale，`signature_diagnostics/primary03_actual_change_diagnosis_v1.json`定位检查期间Landscape自动生成可见草层。名字不证明实际类，后续`primary03_grass_actual_classes_v1.json`另核对实际runtime class；原r2不追认为通过，不覆盖原diff，也不据此排除整图。

新dual_v3只在**实际类精确为GrassInstancedStaticMeshComponent，且同时NO_COLLISION与Visibility IGNORE**时，把该组件单列为外观层而不计入碰撞代理hash；并非按名字匹配，也不排除其他粒子、无碰撞组件或带碰撞草层。所有Actor变换/可见性、其他组件、脏包与源pins保持，读取不完整仍按原unavailable规则处理，不能获得草层豁免。

每个fresh尝试写`dual_signature_bindings/`、`dual_signature_snapshots/`、`dual_signature_reports/`：保存完整raw payload、碰撞代理payload、起终原始签名、所有原始diff、proxy diff及草层明细。只有该次完整1260采样与碰撞代理稳定，才可标为collision_proxy_qualified；raw_scene_unchanged_certified=false、rendered_visibility_or_exposure_passed=false始终明确。原始草层有变化仍必须显示mandatory visual warning，角色/背景遮挡与曝光需真实渲染检查，不能把碰撞代理稳定等同于原始场景不变或视觉通过。

实现只加载私有runtime模块，在该survey结束/取消/异常时恢复原survey.worker；全局runtime8函数不改，不作为全局runtime9或原验证规则放宽。旧stale不得由dual overlay回签；只能用新的源pin匹配、原始采集完整且base为complete的fresh尝试。`merge_primary_scene_surveys_v1.py`/网页消费fresh dual证据时必须保留raw变化与草层视觉警示，缺dual、错误base签名/非原始capture、错误类/被削弱payload均拒绝。

对应[test_primary_scene_survey_dual_v3.py](../../../../../../00_engine/scripts/unreal/tests/test_primary_scene_survey_dual_v3.py)同归本节。`dual_signature_validation_v3.json`记录3项针对性离线测试与编译、ue_execution=false；`dual_merge_validation_v3.json`记录42项受影响合并/样片合同和JS语法检查，同为离线范围，不能与前述26/18累加冒称新完整回归。该更新检查点尚待root的fresh UE首测；不因独立脚本存在、离线测试通过或旧r2数值清楚就宣称新点位已通过。

当前游乐园两代表片已技术核验并抽图观察，human_acceptance=pending；樱花近主景点两片正在生成，尚未计作已核验媒体。其他点位继续靠近主景重选，准确动态数量由machine authority拥有。R16仍in_progress，未完成26场景结果、视觉/曝光取舍及网页/代表媒体交付，不执行全树重建、扩大测试或整体完成声明。


### 21.8 定向地面查询与严格消费链

全部既定26主图已完成首轮尝试，root替代点队列已跑完一个检查轮次；这不等于全部近主景点合格或代表媒体完成。准确逐图状态、重试和冲突由现有batch、followup queue、各surveys/dual报告与media delivery拥有，不在文档复制变化总数。已接受相机标准继续保持R15完成，主场景画面与曝光仍未完成。

以下新增入口同归本节experimental范围，不改原worker/原survey/dual源文件：

| 入口 | 精确范围 |
| --- | --- |
| [ue_primary_scene_ground_objects_v1.py](../../../../../../00_engine/scripts/unreal/ue_primary_scene_ground_objects_v1.py) | 独立私有地面适配：仅锚点/九点、screen地面、full动作地面三域改用指定物体类型complex查询，恢复VisibilityIGNORE但实际可查询的命名路面；身体/站立/相机/遮挡仍原Visibility |
| [ue_primary_scene_ground_simple_v2.py](../../../../../../00_engine/scripts/unreal/ue_primary_scene_ground_simple_v2.py) | 在冻结objects_v1私有clone中，仅地面改simple查询；必须绑定同XY、同实际组件的complex miss/simple hit诊断及原base pin；simple代理支撑不等于渲染网格接触 |

objects_v1只对明确指定的实际支撑组件/actor+mesh启用WorldStatic；只有命名目标确实为WorldDynamic才加入该类型，不查询Pawn/Vehicle，也不创建碰撞。九点/80cm站立区域、3cm平坦容差、动作5cm地面高度条件和完整1260组合保持；NoCollision/PhysicsOnly仍不变成可查询支撑。维多利亚真实路面VisibilityIGNORE的fresh尝试由`ground_consumer_validation_v1.json`及其引用的`primary_25_r5`、ground_object/dual报告链拥有：恢复实际地面支撑后1242/1260组合未报代理冲突，余项不隐去，视觉仍pending。

九龙与教堂同XY诊断显示complex miss而simple准确命中实际命名地板；simple_v2要求诊断SHA、目标component/mesh和同向下射线匹配，仅切地面trace_complex=false，身体/相机/站立仍原complex Visibility，阈值不放宽。`root_simple_ground_results_v2.json`及其fresh报告拥有实机全查进展；`simple_ground_consumer_validation_v2.json`初始离线pending不冒充实机完成，也不把simple代理高度当成网格接地或视觉通过。

merge的`_validate_ground`必须完整绑定fresh base、dual报告、ground receipt/binding、adapter source、命名实际目标、每地面域计数及原阈值；simple分支另核对diagnostic和冻结complex base。缺字段、错目标、错策略/trace_complex或伪造支撑不得合并，旧报告不追认。网页保留complex地面与simple代理的不同限制，以及真实接地/草叶遮挡/曝光必看提示。

本节直接拥有[test_primary_scene_ground_objects_v1.py](../../../../../../00_engine/scripts/unreal/tests/test_primary_scene_ground_objects_v1.py)、[test_primary_scene_ground_simple_v2.py](../../../../../../00_engine/scripts/unreal/tests/test_primary_scene_ground_simple_v2.py)；offline对象2项、simple4项（含原对象2项）与consumer各自范围由ground_object_adapter_offline_validation_v1、ground_simple_adapter_offline_validation_v2、ground_consumer_validation_v1、simple_ground_consumer_validation_v2拥有，不相加冒称新全套测试，本次只读证据不重跑。

### 21.9 面板离线同步与独立私有adapter待实机验收

| 入口 | 精确范围 |
| --- | --- |
| [ue_primary_saved_site_review_v1.py](../../../../../../00_engine/scripts/unreal/ue_primary_saved_site_review_v1.py) | 新面板私有adapter导入目录排除与相机EV；旧worker字节冻结，独立LIVE/前缀，原检查进行中禁止交接，首次交接仅恢复旧预览 |

已存在的`merge_primary_scene_surveys_v1.py`新增离线命令，从仓库根运行：

```powershell
python 00_engine/scripts/unreal/merge_primary_scene_surveys_v1.py --sync-panel-sites
python 00_engine/scripts/unreal/merge_primary_scene_surveys_v1.py --sync-panel-sites --apply
```

默认只预览本26主目录已选点的upsert，不执行survey merge、不生成gallery、不连接UE。`--apply`才写现有panel Run的sites及本Run panel_saved_points_sync_v1.json；旧managed点先备份，非本目录ID/用户改过的点拒绝覆盖，目录或目标中途变化则中止。旧gas/parking等点位与当前选中状态保持。

同步只导入位置/朝向、排除和EV，并写needs_recheck、人审pending和空真实签名；不伪造allowed/pass、decisions_stamp、input_fingerprint或scene_signature。排除展开必须匹配当前1260与50%标准，不能因文件已写就称面板行为已通过。`panel_saved_points_sync_validation_v1.json`只有离线2项，actual_sync_executed=false。

私有adapter由原启动器/面板的WORKER入口单独加载，原`ue_scene_site_review_v1.py`保持SHA `ef6fc7e8b1a3b6b93cd9e9d7a555d89e7ae1c5d89c0521f8355ea73bfa30ca29`以保护历史pins。导入排除参与remaining范围和签名；EV只临时相机bias，EV0须关闭前次override以恢复继承，场景/FOV/aspect保持。`panel_private_adapter_validation_v1.json`记录5项离线测试、original_worker_unchanged=true、ue_executed=false，未实际同步或实机验收。必须等survey/MRQ idle后root串行验证原点位/新点位载入、临时排除及EV2→EV0读回，再判断可交付；本轮文档维护不操作面板。

对应[test_primary_saved_site_adapter_v1.py](../../../../../../00_engine/scripts/unreal/tests/test_primary_saved_site_adapter_v1.py)同归本节，旧worker与历史现场回执不因此重签。

### 21.10 樱花代表渲染失败、恢复与独立草层设置

樱花近主景样片v1因草层实例达到约16M限制取消，后续v2 prepare出现显存失败；失败/取消记录保留，不能计为合格媒体。root已重启UE，恢复检查点进程为35692；`restart_readiness_v1.json`确认MRQ idle、无active executor且无脏map后才继续，不把旧PID当作后来恢复指令，也不宣称显存根因已修复。

`ue_primary_scene_samples_v1.py`新增隔离样片队列的草层设置，由`sample_grass_streaming_fix_v1.json`拥有：关闭本样片queue的flush_grass_streaming与override_grass_cull_distance_scale，避免默认草层强制刷新/放大距离；render_contract.landscape_grass_streaming记录实际设置。原地图、全局renderer、草层资产与已接受相机标准不改。该回执5项/0.62秒及compile只证明限定离线grass_policy/exposure行为，actual_render_validation=pending_root_v2_attempt；新重渲染及最终草叶可见性、曝光和代表媒体仍待实际结果。

R16保持in_progress：固定26图不筛目录，首轮与替代队列已执行不代替近主景视觉/曝光接受；面板私有adapter和草层样片修复均待实机边界。只做本轮owner对应检查，无全树重建、扩大测试、删除资产或整体完成主张。


### 21.11 选定点位数字证据完成、代表组合应用与资源重试

本节保留樱花v2终止后的检查点；最新已验画面与樱花v3竖屏恢复见§21.12，不以本节旧可播数量覆盖后续证据。

当前26/26选定点位的完整1260组合数字证据已merge，准确报告和源pin由scene_survey_merge_v1.json、scene_samples_index_v1.json及逐图survey/dual/ground链拥有。数字完整不等于媒体或视觉接受：本检查点仅游乐园2条视频已核验，所有主场景human_acceptance仍pending，R16继续in_progress。

`sample_selection_application_v1.json`记录其余24场景已选择48条代表组合：22条横屏360、2条横屏120、24条竖屏正面全身。仅选择实际渲染样本，不增加数据集排除，不改map/XYZ/yaw/EV或既有排除；原survey pins/数值元数据和既存冻结计划保持。游乐园/樱花既有版本受保护，日式既有v2新建计划不冒称本次又升级revision。新组合已落盘不等于48媒体已渲染或可播；当前发布仍以逐片receipt和scene_samples_delivery为准。

`panel_sites_sync_application_v1.json`已实际离线写入26个primary保存点，并保留原gas/parking共4个用户点及面板状态文件。该应用不连接UE、不调面板、不改当前现场选择；全部导入report=null、真实freshness stamp缺省、人审pending，未把survey数字报告伪装成panel现场检查。§21.9的离线待应用是当时检查点；当前文件写入已完成，但私有面板载入、排除与EV行为仍未实机验收。

樱花v2即使两项grass flags已false，PIE后仍达到约90GB私有内存并GPU timeout。`sample_resource_recovery_v1.json`记录root正常cancel已确认，最终terminal_status=failed，随后切到空关卡且executor=None释放资源；旧尝试保留，不按cancel请求或已退出就记成功。原地图保持。当前升樱花v3，重建独立版本计划后重试，尚无合格新媒体或资源问题已解决的主张。

本节已拥有的`ue_primary_scene_samples_v1.py`新增`scene_inherited_resources_v1`，只作用独立样片MRQ队列：关闭cinematic_quality_settings、强制LOD0、HLOD禁用、视距/高质量阴影/VT反馈倍率覆盖和streaming强制刷新，texture_streaming=NONE表示不覆盖现有纹理流而非禁用纹理流。保留grass两flags=false；读回逐job配置并写render_contract.scene_resource_policy。沿用当前工程/场景资源设置，不改变原地图/材质输入及已接受镜头、分辨率或AA采样；也不承诺修复早前任务已改变的HLOD状态。LOD/streaming与背景细节仍需重渲染检查，不能仅凭配置变更称画质已验。

该模块内引擎本地源码依据与策略字段可追溯；root报告3项针对性资源策略测试通过，未实际渲染验证。本轮文档不重跑这些测试或扩大全套检查。R15接受的相机标准继续completed，R16在数字证据、离线点位写入后仍须完成主场景代表媒体、曝光/视觉审查、面板实机边界和最终网页交付；不虚报整体完成。


### 21.12 实际代表画面、沙丘曝光建议与樱花v3竖屏准备恢复

本节保留v3横屏成功、竖屏prepare恢复时的检查点；后续双画幅成功与资源释放实证以§21.13为准。

本轮实际画面依据为Run根目录`root_execution_progress_v1.json.sites`中的reviewed_contacts及visual_result，不把该文件旧latest_checkpoint中的PID/进度当作最新恢复状态。游乐园和中式庭院双片已完成核验并看过各20帧时间线图：人物与真实地面/背景清楚，未观察到重大遮挡；庭院竖屏后段有方向阴影但人物仍可读。两处暂保留EV0，human_acceptance均pending，非连续逐帧或全镜头人工接受。

沙丘baseline横竖两片偏暗；root已实际对照EV+1.5的v2横竖两片时间线图，面部/衣服可读性改善，沙地和天空仍有细节，建议保留EV+1.5供用户审看。日落逆光和继承的lens flare仍在，不把提亮建议写成光照问题全部消失或用户接受；抽样脚下未见明显穿沙也不等于所有动作网格接地通过。

樱花v3横屏环绕已成功渲染并看过20帧图：树林、阴影和有纹理地面存在，未见棋盘格或重大遮挡，保留EV0。该实际样片证明`scene_inherited_resources_v1`至少已在本组合运行，不再仅为离线准备；不能据此证明后续prepare峰值或全部场景资源故障解决。

随后樱花v3竖屏在prepare阶段出现GPU E_OUTOFMEMORY弹窗退出，旧UE PID35692已终止。`cherry_v3_portrait_recovery_v1.json`记录新UE PID35628、node `862B24F54E057FC729A810A7A6383BAE`及idle Entry确认；意图为prepare_requested、render_receipt_absent=true，尚未提交该竖屏渲染。因此只恢复同revision的prepare，不凭空生成render receipt、不重复已合格横屏；横屏复用由实际核验回执决定，不把旧退出误当作渲染完成。

已归本节的私有`run_primary_scene_samples_v1.py`新增`release_owned_world()`边界：每次prepare前先发**独立远程命令**，仅对当前工程内干净的owned SceneTrials关卡切Entry并collect_garbage，等命令返回/编辑器释放后，再单独提交prepare。MRQ/scene survey/check进行中或有dirty map/content时拒绝释放；非owned源图/用户图跳过，不保存源资产，不擅自丢弃用户现场。独立边界旨在减少相邻大图并存峰值，共享引用资源和prepare内部复制峰值仍无释放保证；recovery回执actual_boundary_validation=pending，本检查点尚未证实缓解效果。

同runner新增`--gallery-every-scenes 6`，只把有新合格视频的网页刷新频率合并到每6个场景；每次刷新仍做完整校验，尾部与reuse-only结束也完整刷新，不减少逐片receipt/来源/哈希或最终完整验证。root报告新runner35666已续跑，准确进度继续由runner/逐片回执与delivery拥有，不在文档复制动态总数。

`commands/validate_primary_saved_panel_v1.py`为root实际面板验证脚本，已编译但尚未执行；编译不等于点位载入、排除或EV实机通过。R15的接受相机标准、分辨率与材质输入保持，R16继续进行，代表媒体、主场景视觉/曝光与面板实机及最终网页交付尚未全部完成。本轮只补这两份owner文档与对应少量检查，不操作UE、不扩展测试或全树审计。


### 21.13 既有主关卡范围、樱花双片与待改善画面

用户最新澄清仅约束实际渲染关卡必须为现有主场景，既定26主关卡清单保持；没有重新筛选主目录或整理目录的任务。点位/曝光与代表画面继续在这些既有主关卡中完成，不改目录分类、不迁移资产、不把其他51层扩入本轮。

root的串行会话35666继续渲染。日式村落v2横竖两片已有encoded_verified回执；agent实际查看时间线图后仍有前景草遮挡疑问，媒体核验不等于视觉适拍。樱花v3横竖两片均成功，root实际看过两份20帧接触表作初审：人物、纹理地面与樱花林可见，未观察到重大遮挡/棋盘格，保留EV0建议；这是有限抽样初审，human_acceptance仍pending。

资源释放新增实际证据为`resource_boundaries/ps_fd0160accbd4_4dbde607_prepare.json`：前一樱花v3竖屏owned SceneTrials副本在MRQ idle、dirty_packages=[]时已released_to_entry，GC已请求，source_assets_saved=false。随后对应`media_validation_ps_fd0160accbd4_4dbde607.json`成功，表明该次独立释放边界之后的赛博朋克横屏准备/渲染走通。此结果补充§21.12当时的pending边界，不回写旧恢复回执，也不证明所有共享GPU引用已释放或OOM根因永久解决。后续driver、来源与逐片核验保持。

沙丘EV+1.5仍是root比较baseline/v2实际画面后的推荐，逆光/lens flare仍在；不是用户已接受的场景曝光。已接受的相机标准、分辨率及材质输入继续保持，不以场景光照建议改写相机接受范围。

`scene_visual_retries_v1.json`当前已记录加油站、公路和香港街道的待改善项：加油站室内点近黑，先复核旧室外候选并做新完整检查，不盲目加EV；公路部分环绕方向看到背景边界/悬空树基，比较道路点位或窄范围方向取舍，不把整场景拒绝；香港街道人物处于深建筑阴影，先做小幅相机EV预览，必要时找邻近受光路面，保留场景。它们是待处理队列，不是已经修好或新增全局排除。

`agent_scene_visual_notes_v1.json`新发现日式村落草遮挡待纳入同一画面问题队列：横屏约1.83/6.23秒草叶跨人物轮廓，竖屏后半段部分小腿/足部被遮；先保留EV0建议，重点连续播放判断草遮挡/接地，不归咎曝光，也不在本轮文档直接追加排除或声称用户接受。该条在本检查点尚待root纳入/处理，准确队列以machine authority为准。

R16保持in_progress。只同步上述范围和实际证据，不操作UE/运行器，不扩大测试或全树审计；所有主场景人工仍待审，待改善画面、曝光取舍和面板实机/最终网页尚未完成，不能把媒体成功或一次资源释放走通当成整体完成。

### 21.14 样片网页的初审提示

`build_primary_scene_samples_v1.py`逐卡区分文件核验与画面初审：仅可播放仍为“未查看”；当前版本的`scene_visual_retries_v1.json`待处理项优先显示“待改进”。`agent_scene_visual_notes_v1.json`须匹配当前冻结plan的路径、哈希及全部当前样片contact，才可显示“初审未见明显问题”；部分查看不自动升级。root的`root_execution_progress_v1.json`须逐张匹配当前contact，显式`visual_status=sampled_no_obvious_issue`才显示相同初审结论。旧版记录不套用于新样片，来源小JSON的pin随下次delivery记录。

每卡始终保留“待用户审查”，初审只限已有抽帧记录，不表示动态视频或全部1260组合通过。网页同时明确“视频可播放仅代表文件已核验，不代表场景适用或画面已通过”。本轮只更新生成器和root授权的四条初审状态字段，未触发网页重建；由root独占runner在后续正常刷新时生效。`gallery_visual_status_validation_v1.json`拥有13项限定逻辑检查、来源pin与网页未重建证明，不是本轮媒体复验或浏览器验收。R16继续进行。


### 21.15 首轮样片完成与定向改善检查点

首轮固定26主场景共52条代表样片已生成，串行runner35666以exit0结束；`scene_samples_delivery_v1.json`记录26场景、52/52文件核验及human_acceptance=pending。root已看首4场景接触表，agent的`agent_scene_visual_notes_v1.json`记录其余22场景44张接触表全部实际看完；这是离散抽帧初审，未据此宣称连续视频、所有瞬间接地或全部动作镜头画面通过。`scene_visual_retries_v1.json`在本检查点有16条问题记录，包含已解决的Gas历史项；准确待处理状态由该队列拥有，不把历史项总数等同于尚未解决数量。

Gas已改用户外v2点位，完整1260组合未发现代理疑点；两条新代表样片已生成并由root实际看过接触表，保持EV0。runner28257以exit0结束，该队列项为resolved_in_v2_root_sampled_review_human_pending，用户审查仍pending；旧室内问题记录与旧v1媒体保留，不追认旧点或把一次改点提升为整场景任意组合适用。

红沙竖屏首编码帧朝向异常已用`red_desert_initial_rotation_readback_v1.json`实际读回确认：`Rotator(0,-45,0)`得到pitch=-45/yaw=0，与期望pitch=0/yaw=-45不符，已保存相机也为前者。私有`ue_primary_scene_samples_v1.py`仅对新红沙portrait样片显式按pitch/yaw/roll设置初始化，并核对读回；Sequencer轨迹、时钟及其他样片不改。本检查点尚未补拍，不能把修正实现或初始化读回当成首帧媒体修复已验。

HK原生曝光预览已成功完成0/1/2三档PNG，root均实际看过；`root_exposure_choices_v1.json`提出绝对auto-exposure bias=2候选，人物面部/衣服/脚更可读，但日照路面更亮，完整环绕仍需验证。0档在本次receipt中为不覆盖场景继承值，不能把各档简单称为在原场景上加0/1/2；候选尚未MRQ或用户接受。曝光辅助[ue_primary_exposure_preview_v1.py](../../../../../../00_engine/outputs/all_primary_scene_sites_20261015_v1/commands/ue_primary_exposure_preview_v1.py)仅供root在空闲的已准备owned SceneTrials副本做原生截图对照；[start_hk_exposure_v1.py](../../../../../../00_engine/outputs/all_primary_scene_sites_20261015_v1/commands/start_hk_exposure_v1.py)负责root串行启动该预览，[read_red_desert_initial_rotation_v1.py](../../../../../../00_engine/outputs/all_primary_scene_sites_20261015_v1/commands/read_red_desert_initial_rotation_v1.py)是空闲时只读初始化诊断入口。上述Run内辅助命令归本节，保留逐次receipt与来源pin，不扩为新生产体系或修改源关卡。

R16保持in_progress。面板实际验证、最终组合排除、剩余点位/曝光修复与最终审查网页交付均未完成；已接受的相机标准、分辨率与材质保持。此次只同步Technical和当前计划，不操作UE/运行器，也不触发全库审计。


### 21.16 曝光动态试片进行中与未采用的候选点

用户再次明确只要求实际渲染map属于既有主场景；固定26主关卡清单保持，不重新筛选或整理主目录。`agent_exposure_comparison_notes_v1.json`已记录10组30张原生曝光PNG全部实际审看，结果仅为候选建议：静态编辑器截图不是MRQ逐像素等价，也不证明动态曝光收敛、完整运动或用户接受。0档沿用场景，非零档为绝对相机bias，不在场景值上叠加。

root已执行[stage_exposure_dynamic_trials_v2.py](../../../../../../00_engine/outputs/all_primary_scene_sites_20261015_v1/commands/stage_exposure_dynamic_trials_v2.py)；`exposure_dynamic_trial_selection_v2.json`状态为staged_not_accepted，已为8个曝光候选场景、HK曝光候选及红沙首帧修复共10场景建立v2动态试片。当前index/catalog与该选择一致，均为human pending；这些试片配置已暂存，不能继续描述成尚未配置，也不能称作曝光已正式接受。串行runner在本检查点由session1286运行，动态渲染与实际画面验收尚未完成，红沙新portrait首帧修复仍待新媒体证明；准确进度由runner及逐片receipt拥有。原生批量截图辅助[run_primary_exposure_batch_v1.py](../../../../../../00_engine/outputs/all_primary_scene_sites_20261015_v1/commands/run_primary_exposure_batch_v1.py)与上述stage命令归本节，保留各自预览/选择回执，不扩大为新的目录筛选或生产体系。

公路候选`surveys/primary_06_r9_20261015_080342.json`完成1260数字采样，其中1075未发现代理疑点、185仍疑似；京都候选`surveys/primary_11_r8_20261015_080122.json`为974未发现代理疑点、286仍疑似。两者仅待视觉试点，均未应用到catalog，不能称新点已替换、净空或场景已适拍。京都随后第三候选`surveys/primary_11_r10_20261015_080616.json`实际命中SM_KYT_StoneStairs3，站立区域高度不平，ground候选eligible=false且full_attempts为空；此点不适合，结果为unresolved_search_not_scene_rejection，不代表京都场景不可用，也不取消既定主场景身份。

R16继续in_progress。保留已接受相机标准、分辨率和材质；动态试片验收、剩余点位/曝光改善、最终排除、面板现场及最终交付仍未完成。本轮只同步已有owner文档与限定证据检查，不操作UE/运行器、不重建网页或执行全库审计。


### 21.17 曝光动态片完成与五场景新候选试片

曝光动态试片10场景20条已完成，runner1286以exit0结束；随后生成的`scene_samples_delivery_v1.json`为26场景/52条文件已核验、human_acceptance=pending。该网页快照不证明接下来新stage版本均已完成。`agent_dynamic_exposure_notes_v2.json`记录除HK之外9场景18张接触表均实际看过，并对红沙v2横竖首两编码帧作精确解码补查；HK两片由root实际看接触表。均为抽帧初审，不是连续视频或用户接受，曝光改进也不自动解决实体遮挡、背景断边或全部动作接地。

红沙v2竖屏精确frame0/1均正常，横屏frame0仍只见地面/近岩，frame1才恢复全身。现已将私有`ue_primary_scene_samples_v1.py`初始化keyword-rotation修正扩展到同一RedDesert新revision的横竖两画幅；仍排除v1、其他scene/非camera，不改冻结轨迹、动画和时钟。policy为red_desert_both_aspects_initial_rotation_keywords_v2，旧prepared receipt不冒充新策略；6项initial_rotation定向测试通过，旧媒体保留。当前catalog红沙为v3，双片补拍及精确首帧实证仍待本轮新媒体，不能从离线测试推断画面已修好。

新一轮五场景十片已stage，串行runner在本检查点为session40909，raw保留：公路采用r9点为v2，京都采用r8点为v2，均用MOTION_CAND_030横屏front_three_quarter_full、竖屏front_full作定向视觉试片。它们不再是§21.16当时的“尚未应用catalog”，但原完整报告仍分别有185/286组合疑点，不能因选中代表镜头而称整点净空或全部组合适用。

SciFiMain的`surveys/primary_18_r11_20261015_083959.json`新点实测约[2999.982,-2999.991,20]cm、yaw315°，完整1260组合未发现代理疑点，已stage为v2。日式村落由root实际原生俯视图选干路，再以`surveys/primary_09_r12_20261015_084414.json`测得[3800,-2200,89.99988674944683]cm、yaw0°，完整1260未发现代理疑点，已stage为v3；图上选点不替代实测地面。两新点和公路/京都均仅候选，尚未本轮样片视觉通过，不修改既有主场景目录分类。

三份Run内定向stage辅助命令归本节：[stage_inner_road_trials_v2.py](../../../../../../00_engine/outputs/all_primary_scene_sites_20261015_v1/commands/stage_inner_road_trials_v2.py)、[stage_scifi_and_red_v3.py](../../../../../../00_engine/outputs/all_primary_scene_sites_20261015_v1/commands/stage_scifi_and_red_v3.py)、[stage_japanese_dry_path_v3.py](../../../../../../00_engine/outputs/all_primary_scene_sites_20261015_v1/commands/stage_japanese_dry_path_v3.py)；各自保留旧catalog备份、冻结计划与选择/merge依据。`metro_completed_receipt_recovery_v1.json`记录地铁已完成状态在写回receipt时遇WinError5：root核实原UE内存completed/success及MRQ idle后，只调用原persist一次成功，没有重提交或重新渲染。此恢复不提升画面接受状态。

R16保持in_progress。待做九龙限制镜头代表样片、272条建议组合的最终排除取舍、剩余点位/曝光改善、面板最终点位/曝光同步及实际测验、最终网页与文档交付；建议不等于已应用排除。只用固定26既有主关卡作为渲染map，不重新筛选整理目录。已接受相机标准、分辨率与材质保持；本轮文档同步不操作UE/runner，不扩大审计。


### 21.18 交付末验检查点与实际面板验证

root报告最后runner70741成功；`scene_samples_delivery_v1.json`拥有固定26主关卡、当前52条已核验代表媒体。`new_final_repairs_visual_notes_v4.json`已完成日本村落v4与SciFiMain（8f7e）v3最后4片接触表及精确输出frame0/1实际查看，4/4均正常开头；`agent_new_point_visual_notes_v3.json`保留旧记录并追加当前4条，网页仅按当前plan/shot/媒体SHA采用。只完成候选点与代表样片供人审查，不把媒体或抽帧初审等同于全部画面通过。用户明确只使用既有主场景作为渲染map，不重新筛选或整理主场景目录。

[scene_exclusion_policy_application_v1.json](../../../../../../00_engine/outputs/all_primary_scene_sites_20261015_v1/scene_exclusion_policy_application_v1.json)已实际应用v3保守提案247个组合：九龙135、模块停车场49、海滨2、地铁6、日本城市55，全部26场景保留，剩余32513/32760组合，代表样片冲突0。它们是具名实体相机代理/明确场景镜头政策的兼容性决定，不是逐组合逐帧像素穿模证明；不自动增加纯遮挡、草层、小物或地面疑点。九龙r13新点[720,-230,约0]cm/yaw90°的M030横front_full、M036竖front_full保留；旧点规则不迁移成新点“已检测失败”。旧v1/v2提案及raw/媒体保持，应用不代替用户视觉接受。

最新`merge_primary_scene_surveys_v1.py --sync-panel-sites --apply`实际回执是[panel_saved_points_sync_v1.json](../../../../../../00_engine/outputs/all_primary_scene_sites_20261015_v1/panel_saved_points_sync_v1.json)：26个现用primary点位已更新，来源catalog pin与当前catalog一致，原其他4点与当前选择不变。早期`panel_sites_sync_application_v1.json`为初次离线同步历史，不能用其旧source SHA冒充最新同步。导入数字报告不等于面板现场fresh full check；保存点的点位、曝光和排除策略仍须按当前输入使用。

root完成[panel_validation/panel_4c9578397c53.json](../../../../../../00_engine/outputs/all_primary_scene_sites_20261015_v1/panel_validation/panel_4c9578397c53.json)实际验证，SHA为`0e45dadd26407374dfb4cc824a0745455bd86c83de96d8a6bde7cd3cc65d077c`，success/checks_passed/protected_files_unchanged为true。游乐园已存点load/preview、EV1.5相机覆盖、EV0取消覆盖恢复继承均通过；EV0时stored bias仍可为1.5但override=false，不能误说仍生效。临时排除M008/front_full/portrait先于异步job拒绝，随后原site/相机和选择恢复；原4保存点、26primary文件及源地图保护不变，source_maps_saved=false、saved_point_or_user_configuration_written=false。首次直接--script因缺少__file__未开始测试，改runpy.run_path后完成；没有借未开始的尝试宣称通过。该代表实机操作不认证26点完整画面或矩阵网格接地。root随后先把本次panel测试唯一脏包另存`/Game/DataMake/Validation/AllPrimarySceneSites20261015/Recovery/L_AmusementPark_PostPanelValidation_4c9578397c53`，save_map返回True且备份资产存在，再load_level原`/Game/DataMake/Validation/CameraFollowCompact20261015/Recovery/L_AmusementPark_PreReview_20261015`返回True；未覆盖源图。两份.umap已离线确认存在，实际调用成功由root记录。

私有`ue_primary_scene_samples_v1.py`初始化修复已通用于本任务SceneTrials新revision两画幅：必须schema、document/site身份与revision一致且非v1、shot精确属于冻结document，相机处于本任务owned路径；显式pitch/yaw/roll关键字设置，保留源码pin/expected/readback/首次receipt/fresh revision保护。11项initial_rotation定向测试通过，证据`initial_camera_rotation_all_scenes_validation_v3.json`；不改其他task、v1资产、冻结轨迹或时钟。[current_samples_opening_frames_audit_v1.json](../../../../../../00_engine/outputs/all_primary_scene_sites_20261015_v1/current_samples_opening_frames_audit_v1.json)对该历史52片精确0/1共104帧实际查看，仅日本v3两片frame0异常；该历史审查不覆盖新日本v4/SciFiMainv3最后4片；当前独立补查已由`new_final_repairs_visual_notes_v4.json`完成。`current_samples_opening_frames_coverage_v2.json`（SHA `f1e2024166e62e436b77aae5e35521f6fae9a1720ffa226a7709a769a19f01a5`）聚合当前52条/104精确帧：48条复用旧具名证据、4条采用新独立证据，当前错位0、缺失0，逐plan/video/receipt/frame pin与当前delivery一致；并非重新审全片或认证所有瞬间。


root已fresh build最终网页exit0，26/26点位、52/52媒体。IAB实际页面展示数量及筛选/视频控件正常；搜索“沙漠加油站”的两条视频readyState=4、duration=10、error=null，未声称所有52条已在浏览器连续播放。[gallery_http_validation_v1.json](../../../../../../00_engine/outputs/all_primary_scene_sites_20261015_v1/gallery_http_validation_v1.json)记录所有52条Range请求HTTP206成功，continuous_browser_playback_certified=false。网页显式展示逐画幅建议与remaining提醒，needs_improvement才标待改进；可播放、已有初审或风格/构图取舍不等同于全组合通过。

保留的限制包括教堂部分环绕灰背景/平台边、赛车场阴影、维多利亚暗街，具体以当前精确绑定的初审台账为准。SciFiMain新竖屏中央楼背景改善，但横屏约3.1–8.4秒仍偏暗；Japanese v4强日光亮部及连续舒适度仍供用户取舍。R16技术交付completed，scope为ready_for_human_review，human_acceptance=pending；没有宣称全部1260组合每帧视觉/接地/曝光通过，没有生产Gate晋升。用户接下来在网页连续播放并判断候选点与代表镜头；后续修改输入须重新核对相应证据。当前父计划保留current，不擅自归档其他未收口需求。

最终集中依据为[final_delivery_checkpoint_v1.json](../../../../../../00_engine/outputs/all_primary_scene_sites_20261015_v1/final_delivery_checkpoint_v1.json)：ready_for_human_review/human_acceptance=pending，绑定当前delivery、catalog、已应用策略、最新同步、面板实机、首帧覆盖、最后4片及HTTP回执；26现用点均有完整1260数字证据。最终fresh网页已实际确认日式v4显示“已有初审记录（有提醒）”，含正常首两帧和强日光提醒，浏览器交付页保留。最终建页更新初审来源后delivery整体SHA可与首帧聚合时的快照不同；以当前52条逐shot的plan/video/verification receipt身份一致性关联，不能把展示元数据变化误当媒体重新验证。

### 21.19 2026-10-16 面板切换与常用操作修复

本次只修复 `ue_primary_saved_site_review_v1.py` 私有适配层（revision 4）及 `scene_site_review_panel_v1.py`，冻结 worker 保持不变。旧关卡卸载后的 TargetPoint 引用曾使状态同步报错；现先核对 map 并安全处理失效引用，同场景点位被删除时清除工具预览。切换前若当前地图未保存，先独立另存至 `/Game/DataMake/Validation/SceneSiteSwitchRecovery/L_<id>`，恢复记录写入 `scene_site_review_20261014_v1/switch_recovery/`；备份失败或存在其他未保存地图时拒绝切换，并在面板顶部显示原因。源场景不自动覆盖保存。地图备份/切换之间只保留包名称字符串，避免 Python 包引用阻止旧地图卸载。

常用操作补查修复：点位变化后的旧排除清单不能继续用于启动检查，需刷新并重新确认；停止播放按当前预览组合回零，不回跳旧动作；恢复预览清除旧播放状态；滚轮事件允许 Tk 字符串 widget，不再触发属性错误。面板顶部同步显示进度和失败原因。

实机证据位于 `00_engine/outputs/scene_panel_repair_20261016_v1/phase_1.json`、`phase_2.json`、`phase_3.json`：游乐园与停车场来回切换、切换后载入点位、失效点位清理、新组合俯视轨迹、实际播放暂停（读回3.5秒）、停止回零、编辑/读取/贴地、隔离保存及恢复排除均通过；单组合42个采样检查完成。全部用户已存点位及两份源地图 SHA 保持不变。验证脚本 `verify_runtime.py` 为本节拥有的一次性验证产物，隔离保存不是正式候选点。首次试验旧包引用造成 UE 退出的日志保留为 `package_reference_failure.log`，修正后重试通过；不隐去失败记录。

两份定向测试文件共20项通过。本轮按用户要求仅检查面板常用功能，没有扩大到全部1260组合、场景画面验收或全库审计；R16仍为 ready_for_human_review，人工接受待定。恢复备份含未保存现场，应在用户确认不再需要后再清理。

### 21.20 2026-10-16 大量人工审查记录保存回执修复

用户中式建筑点 `site_def046be4c` 保存时出现 UTF-8 unexpected end of data。两份失败 remote 回执实际对应成功的 UE replies；最后一次265条人工问题审查已完整写入 sites。原因是 UE 原始 remote TCP 接收将短 recv 当作消息结束，长命令回显可在汉字字节中间被截断，不是保存文件编码损坏。

`scene_site_review_panel_v1.py` 现将请求原子写入 Run/requests，远程命令只传请求文件路径；面板私有 remote 模块接收完整 JSON 才解析回执，短分段继续读取，断连/超时明确失败，不自动重发保存。不修改 UE 引擎文件。`tests/test_scene_panel_transport.py` 覆盖5000条中文记录、汉字中间分段、普通短分段及断连；与原面板测试合计14项通过。

原点位、草稿和界面状态备份在 `scene_site_review_20261014_v1/save_recovery_20261016/`。`validation.json` 记录核对原保存内容与原请求一致、当前点位指纹未变后，使用修复通道再次保存成功，265条审查完整保留。场景、相机与点位位置未修改。本节拥有该恢复证据及上述测试；这次仅修复保存回执，不扩展场景审查范围。


## 22. 正式拍摄工作流整合（2026-10-17，实现完成、用户视觉审查待确认）

R17拥有Run `production_workflow_20261017_v1`及动作Run `production_motion_library_20261017_v1`。配置 `00_engine/assets/character_creator/production_motion_library_20261017_v1.json`记录用户确认的26动作10秒规则，`production_motion_contract_v1.py`及`build_production_motion_contract_v1.py`维护时钟；`ue_production_motion_library_v1.py`由root串行生成正式Body/Source和Body/Production男女资产，`run_production_motion_bake_v1.py`逐项执行并写回执。`build_production_camera_library_v1.py`维持已接受镜头构图并把跟随与新身体时钟同步，环绕仍10秒、推拉7秒完成。`scene_site_appearance_v1.py`、`ue_scene_site_appearance_v1.py`、`ue_production_site_runtime_v1.py`接入已接受外观目录与当前面板，已完成13步真实UE功能冒烟。`ue_production_trial_render_v1.py`负责四试片受限复制场景/序列及串行MRQ。原冻结worker不改。

本Run的asset_inventory系列脚本与JSON为本节拥有的资产清理、引用闭包、正式目录映射、迁移回执和运行目录快照。已授权清除历史镜头/动作媒体及已被替代的测试资产，必须按明确清单执行；用户点位、审查记录、排除策略、当前源资产、场景与其他会话皮肤范围保护。正式内容迁移通过UE引用更新，历史证据与当前运行目录分开，不能用旧位置的哈希声称迁移后文件未变。资产整理与清理已按§22.5回执完成，实际视频交付仍按§22.4验收。

### 22.1 新面板实现与独立外观保存

本节拥有 `00_engine/scripts/unreal/scene_site_review_panel_v1.py`、`scene_site_appearance_v1.py`、`ue_scene_site_appearance_v1.py`、`ue_production_site_runtime_v1.py`、`ue_primary_saved_site_review_v1.py`（revision 5）及 `ue_production_trial_render_v1.py` 的R17实现。面板继续通过原子请求文件和完整TCP JSON回执连接现有编辑器；冻结 `ue_scene_site_review_v1.py` 的原SHA检查、场景切换备份、失效点位保护及相机EV继承恢复保留。新/缓存private worker均安装production适配；源码或正式目录指针更新在命令边界刷新，不在播放tick重复读取整套目录。销毁临时角色或切场景前先清除持有Actor/组件的外观缓存。

单人外观字段为 `character_id/sex/choice/hair_color/eye_color/face_id/sources`；choice复用原服装系列、合法组、分离槽位、可选配件、共享鞋和发型规则。40角色、性别对应发型、含原色共10发色及 `idle/smile/displeased/sad` 四种验收表情从当前目录读取；`none`恢复身体动作。四表情以既有已接受曲线叠加实际身体动画，复用全帧保护身体骨骼/无关曲线的合成器，不用旧六种预合成身体限制新26动作。正式骨架搬移后只在私有合成器中精确替换旧骨架期望路径，原合成源码保持，适配源码/原合成器/正式目录同时进入证据。

`scene_site_review_20261014_v1/appearances/appearance_<uuid>.json`为完整外观独立记录，保存时新增ID、校验来源和内容摘要，不覆盖旧搭配。`save_appearance/load_appearance/set_appearance`不写用户点位文件；`save_site`仅由用户明确保存时写外观ID链接及预览时长。旧完整配置仅在来源指纹精确对应搬移前快照时迁移到正式目录，原文件保持。操作说明为本Run `面板使用说明.md`，本节拥有该说明与相关配置/回执输出；默认unclassified保护，不据目录名删除。

#### 2026-10-17 清理后发型跟随动画缺失修复

用户点击`set_appearance`时，女性发型`HAIR_HB2_17`仍请求已退休的`/Game/DataMake/Validation/CompleteCharacterWardrobeHair20261005/Followers/ABP_CCWH_CopyPose_8e9908b26179`，正式路径overlay未包含该运行依赖。原13步smoke使用的默认发型没有触发Copy Pose分支，因此不作为本次问题已覆盖的证明。

`ue_scene_site_appearance_v1.formal_copy_pose_blueprint(u, mesh)`在正式运行分支复用`review.copy_pose_blueprint`的代码和独立globals副本，仅注入当前UE接口及正式输出路径；不修改原生成器全局状态或非formal分支。以当前部件Skeleton对象路径SHA256前12位命名`/Game/DataMake/Appearance/Followers/ABP_CCWH_CopyPose_<suffix>`，按需生成并保存，复用前检查AnimBlueprint、generated class和目标Skeleton。原图保留附着父身体姿态复制及额外头发骨的本地参考姿态，不引入头发物理。

本节拥有Run/follower_repair内`verify_followers.py`、`protected_before.json`、`state_before.json`、`verify_remote.json`、`user_selection_applied.json`和`validation.json`。实际失败选择`CFD40_AF_003`、`HAIR_HB2_17`、紫色、`idle`、`pants_with_bra_and_coat`已成功应用；正式派生资产`ABP_CCWH_CopyPose_49f96e8dc7f6.uasset`已保存41733字节，SHA256为`8014c7243844c8c82ef6d4bbd1ec8aca8b516f895ceba493bdc12576f170d04a`。它是现用Appearance/Followers运行依赖，可由上述生成器重建，不得再按旧Validation测试资产归入无用清理范围。

[定向验证](../../../../../../00_engine/outputs/production_workflow_20261017_v1/follower_repair/validation.json)记录5项本地回归通过：当前骨架生成不同路径、原生成器globals隔离、正确且已编译蓝图接受、错误骨架拒绝、无generated class拒绝；32份已保存点位/外观文件摘要无变化。男性代表AM003与HB1_01/02使用既有leader_pose，不要求新CopyPose；男性prepare曾执行，但用户继续切换发型并播放，最终场景回读未完成，后续UE请求停止。本次不宣称男女完整实机回归、编辑器重启后检查、全搭配矩阵或视觉接受。最初辅助诊断将leader_pose发型也断言为copy_pose的失败保留在验证局限中。

#### 2026-10-17 可选路径、粉色外套和近镜服装消失定向修复

当前可选资产的有效离线检查为Run/panel_followup_audit/`active_runtime_selectable_closure_offline_v1.json`：1204处直接引用、856个入口，访问6168个包，6132个包已解析，直接缺失与已解析导入缺失均0。36个旧格式shader叶节点未深入解析，174条旧路径依赖仍存在且必须保留；这不是整个项目所有包和所有软件路径的零旧引用证明。较早`active_catalog_dependency_closure_offline_v1.json`混入未验收发型fit和目录提示，已标`superseded`，其479项不能作为当前可选外观故障计数。

“人物1”粉色外套源CC内容实际导成内裤，目录名正确不能证明网格正确。经用户明确授权，由同款正常紫色外套派生独立粉色mesh与MI，保存于正式`Bikini_Cover_up_Pink/Corrected/`，不改源CC或原紫色资产。颜色线性值为(.9,.18,.38,1)，BaseColor使用白贴图配合染色，Normal、Opacity等其余11个贴图参数保留。Run/`wardrobe_component_corrections_v1.json`绑定原正式catalog身份、唯一asset_id和旧mesh、派生mesh/MI、源与派生文件SHA；本节及§22.5拥有`asset_inventory_formal_runtime_v1.py`的精确修正加载逻辑。`scene_site_appearance_v1.py`把active指针、helper和修正清单纳入缓存签名，`ue_production_site_runtime_v1.py`把修正清单及源/派生文件pins纳入输入保护；原catalog和已保存外观身份保持，运行时只替换该件错误网格。正式修正资产及manifest是现用依赖，不列入旧测试清理。

近镜Misaki外层蕾丝裙摆消失是动态可见范围未随身体移动：身体没有PhysicsAsset，`use_bounds_from_leader_pose_component`回退参考姿态范围，BundlePart03/04的范围未跟随动作根位移。`misaki_bounds_probe.json`记录0–8秒18帧对照，同5秒的`misaki_before_5.png`与`misaki_parent_bounds_5.png`直接显示外层肩袖和裙摆恢复。`ue_scene_site_appearance_v1.apply_actor`现对leader_pose跟随部件启用`use_attach_parent_bound=True`，异常回滚恢复原值；copy_pose保持其原有策略。修复不修改导入mesh或用户曝光。

本节拥有Run/panel_followup_audit的定向检查报告、`build_pink_coat.py`、`inspect_live.py`、`run_in_ue.py`、bounds/集成验证辅助及其JSON/PNG证据，并拥有`tests/test_wardrobe_component_corrections_v1.py`及现有`tests/test_ue_production_site_runtime_v1.py`对应21项回归。实际loader绑定验证见`pink_correction_offline_binding_validation_v1.json`；两份测试最终21 passed/1.78s，首次sandbox临时目录失败后改为workspace basetemp通过，不作为产品失败。

[正式路径集成验证](../../../../../../00_engine/outputs/production_workflow_20261017_v1/panel_followup_audit/integrated_clothing_validation.json)success=true，共7帧：用户最新CFD40_AM_001/mercenery在0、5秒；人物1粉色在0秒；Misaki在0、3、5、8秒。粉色UpperOuter实际绑定Corrected mesh/MI，染色读回与目标浮点值一致；Misaki四时刻BundlePart03/04范围与Body一致。root实际查看current_5、pink_0、misaki_5，确认粉色整件外套和5秒蕾丝裙摆可见。SceneCapture画面明显偏暗，仅用于网格/可见性判断，不代表最终曝光画面验收。`followup_validation_summary.json`success=true，34份既有用户点位/外观JSON摘要保持不变，生产修复脚本AST检查通过。验证结束已恢复用户刚切换的男角色和预览；本次不是全人物/服装/动作/镜头矩阵认证，仍需用户实际使用审看。

追加共用逻辑与配置覆盖检查见Run/panel_followup_audit/`all_clothing_bounds_config_audit.json`：38个服装系列，717个合法选择探针覆盖全部290个可选系列资产及共享鞋路径，共299个不同服装mesh路径、13个实际使用槽位。以当前生产`apply_actor`实际赋值循环做离线分支检查，2106次leader_pose部件赋值均启用父级范围，无遗漏系列资产或槽位；另26次copy_pose检查确认保留原策略。面板预览、换装/恢复和试渲染均进入该组装器，代码变化会失效旧实例缓存。此检查模拟跟随模式，未读取全部UE网格的实际骨骼，也未渲染；不能据此声称299个mesh全部属于leader_pose或全部通过视觉验收。未修改资产与用户配置。

#### 2026-10-17 其他可选服装与共享鞋的错配、缺失和材质定向检查

本节拥有Run/panel_followup_audit/`audit_wardrobe_assets_ue.py`、`wardrobe_asset_audit_inputs.json`、`audit_wardrobe_assets_ue_remote.json`、`wardrobe_asset_material_audit_ue.json`，以及离线`wardrobe_semantic_mapping_probe_v1.json`、`wardrobe_semantic_source_probe_v1.json`和`current_wardrobe_semantic_mapping_audit_v1.json`。范围为当前正式目录实际可选的290项衣物与31项共享鞋，共321个目录项、299个不同mesh；已应用原粉色外套的修正manifest，不扩大到未验收衣服或其他历史目录。

[UE只读检查](../../../../../../00_engine/outputs/production_workflow_20261017_v1/panel_followup_audit/wardrobe_asset_material_audit_ue.json)complete=true，299/299完成，实际检查mesh类型、骨架、材质槽、MI父链及显式texture参数，覆盖937项材质，mesh与材质报告errors均为空。检查不渲染、不切换当前人物选择、不保存资产或点位；可选空贴图参数不自动判为缺失。此结论证明本次检查范围可加载且未见上述缺失，不代表穿着变形、所有颜色、透明效果或全部动作画面已经通过人工验收。

[离线语义检查](../../../../../../00_engine/outputs/production_workflow_20261017_v1/panel_followup_audit/current_wardrobe_semantic_mapping_audit_v1.json)覆盖相同321项：320项原导出sidecar可核对且mesh名全部匹配，未发现粉色外套之外新增的已证实错资产映射。粉色原错误仍记为既有已修正项，不能改写历史catalog或原始错误证据。

F003/Shoes3的原FBX及sidecar已在此前明确清理清单中删除，精确删除记录及回执由上述离线报告绑定；其当前正式`sneakers_18172_shape`仍有效，UE只读检查通过。该项单列为重导来源限制，不作为当前运行资产缺失；若需要重新导入，必须先恢复或重新导出源，不能沿用已删除路径。本轮未再删除或修改资产，没有生产代码变化，因此不刷新Script Catalog或运行全库审计。

#### 2026-10-17 发色第一步：独立去底色对照试验（前序证据）

用户同意先尝试减弱头发栗色底色，并要求保留黑色改前/改后对照。本轮在原10色之外添加`black_neutral_v1`、`blue_neutral_v1`、`pink_neutral_v1`三个试验ID，面板标为“黑色/蓝色/粉色（改后·试验）”。原10色ID和数值保持，未将试验色发布为新的已接受配色。`scene_site_hair_color_trials_v1.py`只拥有追加选项合同；`scene_site_appearance_v1.py`、`scene_site_review_panel_v1.py`、`ue_production_site_runtime_v1.py`与`ue_primary_saved_site_review_v1.py`负责菜单、来源签名、命令边界刷新和runtime输入保护，旧保存外观只在来源精确对应时兼容读取，不改原保存文件。

`hair_color_neutral_trial_runtime_v1.py`复用原颜色分类与回滚逻辑，复制源MI的有效scalar/vector/texture/static参数，仅切换到独立中性底色shader并沿用旧黑/蓝/粉的染色数值。shader从`/Game/CC_Shaders/HairShader/RL_Hair_Specular`独立复制到`/Game/DataMake/Appearance/Materials/NeutralHairTrialsV1/M_Hair_NeutralBase_v1`，只在BaseColorMap RGB至原Power_4之间插入Fraction=1的Desaturation，原145节点变为147节点；原shader SHA保持`eb9844286b173ec73f7f09145d2651889e87d853637c5cb7b5e1192bc2f4df80`。派生MI位于独立`NeutralHairTrialsV1/Instances/`，不改原纹理、高光参数或场景曝光。runtime签名及输入pins覆盖试验合同、试验模块和实际shader文件，参数/来源变化不能冒用旧缓存。

本节拥有上述两个新增模块，`asset_inventory_formal_runtime_v1.py`的追加配色与旧来源兼容分支，`tests/test_scene_site_hair_color_trials_v1.py`、`tests/test_formal_palette_compatibility_v1.py`及现有runtime/primary adapter测试对应改动；Run/panel_followup_audit的`build_hair_neutral_shader.py`、`inspect_hair_nodes.py`、`inspect_hair_shader.py`、`validate_hair_trials.py`和shader构建、合同、status/reload及六色集成JSON/PNG证据归本节。初版合同29项通过且原保存外观不变，status/reload补充23项通过；最后shader输入保护另有10项定向测试通过，检查范围不合并冒称全套审计。

[六色实机集成](../../../../../../00_engine/outputs/production_workflow_20261017_v1/panel_followup_audit/hair_trial_integrated_validation.json)success=true：CFD40_LF_001、HAIR_HB1_16同镜头切换原黑/蓝/粉及三个试验色，四个hair MI×三色形成12份派生MI；原选择已恢复，曝光未修改。root查看六张截图，但用户已切换到中式暗场，SceneCapture画面偏暗且可见绿色轨迹，不能作为最终观感接受。当前只验证去底色第一步；旧补偿染色数值仍沿用，蓝色可能更强、粉色可能更紫，不能据此宣称颜色更好。

最终只读`hair_trial_final_status_validation.json`记录实际status已返回13色及三个中文试验标签，shader文件已纳入runtime输入pin；原`hair_eye_color_runtime_v1.py` SHA仍为`d714c2fd41a7f8d1929394d2f97cd0a47c123b0ca3c702aac73a4420326c7400`。当前用户地图为`AsianArchitecture/Scenes/ExampleGathering`，未为验证切回游乐园；原选中blue已恢复。

以上记录为三个试验色阶段，保留其13色回执和原截图；当前菜单与下一步以随后中性底色九染色段为准。面部问题仍待用户说明和后续讨论，本轮未实施面部修复，未改变其他会话皮肤范围、R17人工接受或生产Gate。

#### 2026-10-17 中性底色扩展至九种染色（前序十色验证，银白后续比较见下段）

用户在另一场景光照下确认改后黑色正常，并授权全部染色采用去栗色底色的方法；原色／原栗色继续使用原材质。现用面板为原色加黑、蓝、粉、紫、红、青、橙、金、银白，共10项；去掉三个重复“改后·试验”菜单项。旧保存记录的`black_neutral_v1/blue_neutral_v1/pink_neutral_v1`仅作为输入别名分别映射到`black/blue/pink`，不改写磁盘上的旧外观文件。方法接受只覆盖采用中性底色的决定，新九色调色仍待用户视觉复核。

`scene_site_hair_color_trials_v1.py`现为`neutral_base_v2`菜单、别名和`NEUTRAL_TINTS`数值的唯一来源，文件名保留用于来源兼容。黑色、蓝色沿用已比较的试验值，粉色改向玫瑰粉、紫色改向蓝紫、金色改向黄色、银白使用中性等量染色；其余染色也在该独立表显式定义，不套用旧栗色底色的补偿。`hair_color_neutral_trial_runtime_v1.py`复用原分类、输入哈希、绑定核验和回滚，仅在当前面板路径将九染色的hair MI派生到同一个中性shader，并覆盖`Base Color Tint`；其他有效scalar/vector/texture/static参数逐项保持。派生MI的版本2规格同时绑定方法、源MI SHA、shader SHA及有效参数，变化后不会复用旧规格缓存。原色直接恢复源MI；原`hair_eye_color_runtime_v1.py`和正式资产目录未改写。

本节同时拥有Run/panel_followup_audit的`hair_color_neutral_base_v2_compatibility_v1.json`、`hair_color_trial_catalog_before_neutral_base_v2.py`、`hair_color_neutral_base_v2_contract_validation_v1.json`、`hair_neutral_palette_doc_validation_v1.json`、`validate_hair_neutral_palette.py`及其验证JSON/截图。前两项是现用来源兼容依赖，必须保留且加入输入pin，不能作为可丢弃的试验残留；只认可已发布旧试验合同的精确SHA，篡改来源或未知发色仍拒绝。现用选择和方法来源由`scene_site_appearance_v1.py`、正式helper、production runtime与`ue_scene_site_appearance_v1.py`接入。

[合同验证](../../../../../../00_engine/outputs/production_workflow_20261017_v1/panel_followup_audit/hair_color_neutral_base_v2_contract_validation_v1.json)success=true：34项定向测试通过，两份真实已保存金色外观读取后磁盘字节保持，旧试验别名和精确来源保护通过；原染色runtime SHA仍为`d714c2fd41a7f8d1929394d2f97cd0a47c123b0ca3c702aac73a4420326c7400`，当前正式catalog SHA保持。

[十色实机验证](../../../../../../00_engine/outputs/production_workflow_20261017_v1/panel_followup_audit/hair_neutral_palette_validation.json)success=true：游乐园DemoMap、CFD40_LF_001／HAIR_HB1_16下依次应用全部10色，每色4个hair MI与2个原色eye绑定均核对。原色恢复源MI，九染色共36个不同派生hair MI的父shader、版本2方法、色名及染色参数读回通过，全部源材质保持。实际status恰有10色且标签与源码目录一致，结束恢复原紫色外观与预览，地图、曝光未改。该报告只证明绑定、参数和源保护；SceneCapture截图偏暗且疑似存在切色后一帧延迟，不能作为配色视觉依据或发布的颜色参考。当前验证不覆盖全部发型或场景受光，新九色用户复核、面部问题讨论和R17人工审查仍pending，未晋升生产Gate；本轮仅定向合同、实机及文档交叉检查，未运行全库审计或完整测试。

#### 2026-10-17 银白旧版对照（前序比较，后续白发微调见下段）

用户反馈除银白外的其他新染色均满意，认为新银白不美观，要求查看旧版。仅追加`silver_white_legacy_v1`“银白色（旧版对照）”，当前共11项；原色、九个现有染色ID及`NEUTRAL_TINTS`保持，不将旧版对照替换成当前银白，也不预先作恢复决定。原`silver_white`仍为中性底色／等量`(2.5,2.5,2.5,1)`；旧版ID直接交给原runtime的`apply(hair_color='silver_white')`，沿用原栗色源MI和`(12,24,40,1)`染色，不能只在中性shader上改成旧数值。

本节拥有Run/panel_followup_audit的`hair_color_silver_comparison_compatibility_v1.json`、`hair_color_neutral_base_v2_catalog_before_silver_comparison.py`、`hair_color_silver_comparison_contract_validation_v1.json`、`validate_hair_silver_comparison.py`、`hair_silver_comparison_validation.json`及`hair_silver_comparison_doc_validation_v1.json`。新增proof和此前十色目录源码快照是现用保存外观来源兼容依赖，按精确SHA识别并加入输入pin；与此前三试验色兼容依赖一并保护。旧试验别名、此前十色来源、当前旧版银白ID均可读取；旧保存文件不改写。

[银白合同验证](../../../../../../00_engine/outputs/production_workflow_20261017_v1/panel_followup_audit/hair_color_silver_comparison_contract_validation_v1.json)success=true，38项定向测试通过，确认仅新增一行、此前十行和九色参数不变，两份真实已保存外观原字节保持；原runtime与正式catalog SHA保持。[新旧银白实机验证](../../../../../../00_engine/outputs/production_workflow_20261017_v1/panel_followup_audit/hair_silver_comparison_validation.json)success=true：CFD40_LF_001／HAIR_HB2_15下两路的父材质和精确染色读回通过，源材质保持，实际status为11项，结束恢复原`silver_white`外观与预览，曝光未改。本轮不以诊断截图代替视觉判断；当前下一步为用户比较两个银白并决定保留、恢复或再调色。面部问题仍待讨论，R17人工接受和生产Gate不晋升；仅检查本轮受影响范围。

#### 2026-10-17 白色为主、微银效果（前序白发调整）

用户明确目标为白色占主导、只有轻微银感。保留`silver_white` ID，标签改为“白色（微银）”，染色为`(4,4,4.2,1)`，并仅为该色设置`NEUTRAL_SCALAR_OVERRIDES['silver_white']['Compensate Color Power']=0.4`，提亮去底色基底的中间调；其他有效参数仍复制原源MI。原色、其他新染色和“银白色（旧版对照）”均保持，菜单仍11项。此前两轮银白回执不回写，新白发尚未获视觉接受。

本节拥有Run/panel_followup_audit的`hair_color_white_refinement_compatibility_v1.json`、`hair_color_silver_comparison_catalog_before_white_refinement.py`、`hair_color_white_refinement_contract_validation_v1.json`、`validate_hair_white.py`、`hair_white_validation.json`和`hair_white_doc_validation_v1.json`。新增proof与此前11项源码快照为现用兼容依赖，按精确SHA保留并纳入输入pin；旧保存文件不改写。[合同验证](../../../../../../00_engine/outputs/production_workflow_20261017_v1/panel_followup_audit/hair_color_white_refinement_contract_validation_v1.json)success=true，43项定向测试、两份真实外观字节保护及其余参数保持通过；[白发实机验证](../../../../../../00_engine/outputs/production_workflow_20261017_v1/panel_followup_audit/hair_white_validation.json)success=true，LF001/HB2_15的5个hair槽位父shader、染色和Power约0.4读回通过，除预期染色与该scalar外其余参数及源材质保持。当前有意保留白色供用户查看，其他外观与预览保持，曝光未改；这只证明绑定和参数，下一步由用户判断是否达到白色微银目标，面部与生产Gate边界保持。

#### 2026-10-17 三色柔和反光试点（已取消，保留材质层历史证据）

本轮只追加`black_soft_reflection_v1`、`blue_soft_reflection_v1`、`silver_white_soft_reflection_v1`，分别显示“黑色（柔和反光）”“蓝色（柔和反光）”“白色（柔和反光）”，菜单共14项。原11项、全部染色、白色Power 0.4和旧版银白对照保持；新选项作为独立ID保存，不自动替换原色。`scene_site_hair_color_trials_v1.py`拥有三色至原黑／蓝／白的映射和`neutral_base_soft_reflection_v1`方法。

`hair_color_neutral_trial_runtime_v1.py:soft_reflection_scalars()`仅将源`Specular Multiplier`乘0.75，并将`Roughness Multiplier=r`改为`r+min(0.06,max(0,1-r))`；`Specular Strength`、`Scatter`及其余有效参数保持，白色仍继承既有染色和Power覆盖。派生规格增加`reflection_method`并参与缓存键，原11项不走该覆盖。此为参数试点，不能由高光降低和粗糙度增加直接推导颜色在不同场景更稳定。

本节拥有Run/panel_followup_audit的`hair_color_soft_reflection_compatibility_v1.json`、`hair_color_white_refinement_catalog_before_soft_reflection.py`、`hair_color_soft_reflection_contract_validation_v1.json`、`validate_hair_soft_reflection.py`及`hair_soft_reflection_doc_validation_v1.json`；前两项作为现用精确来源兼容依赖继续保护并纳入输入pin。[合同验证](../../../../../../00_engine/outputs/production_workflow_20261017_v1/panel_followup_audit/hair_color_soft_reflection_contract_validation_v1.json)success=true，50项定向测试通过，原11项和参数保持，两份真实保存外观字节不变。live helper语法检查通过，但用户正在切换点位，最近只读状态尚无已恢复的人物和相机，尚未执行人物预览检查；计划输出`hair_soft_reflection_validation.json`目前未生成，不能作为已有证据。下一步待人物／相机预览就绪后检查当前场景三组原版与柔反光参数，再由用户跨场景比较；未完成三场景验证、未接受柔反光观感、未证明颜色稳定。面部和R17生产Gate边界保持，本轮无广域检查。

独立材质层补充验证已完成：[9个派生MI验证](../../../../../../00_engine/outputs/production_workflow_20261017_v1/panel_followup_audit/hair_soft_reflection_material_validation.json)success=true，使用HB3_14的3个源材质×黑／蓝／白3色，核对完整有效参数快照、父shader、反光方法和源文件SHA，9项全部通过；只改变派生材质资产，没有修改场景、人物、相机或曝光。本节拥有`hair_reflection_source_probe.json`、`validate_hair_soft_materials.py`、该材质报告及`hair_soft_material_doc_validation_v1.json`。该次没有完成同机位人物预览或跨场景比较；用户随后取消发色试验，不再安排继续，也未将柔反光提升为正式材质策略。

#### 2026-10-17 停止发色试验，保留标准10色

用户要求停止发色工作、保留标准10色。现菜单只保留原色和9种现有染色，标签、染色及白色Power保持；旧银白对照和三个柔反光选项退役，不进入菜单。读取旧保存记录时，`silver_white_legacy_v1`与白色柔反光映射到`silver_white`，黑／蓝柔反光映射到对应黑／蓝；仅在内存中规范化，不改写原保存文件，不将柔反光材质提升为标准色。

本节拥有Run/panel_followup_audit的`hair_color_canonical_ten_restore_compatibility_v1.json`、`hair_color_soft_reflection_catalog_before_canonical_ten_restore.py`及[恢复标准10色验证](../../../../../../00_engine/outputs/production_workflow_20261017_v1/panel_followup_audit/hair_color_canonical_ten_restore_validation_v1.json)。54项定向合同测试通过，标准10色参数保持、旧ID与来源兼容、两份真实保存外观字节保持；新增proof与此前14项目录源码快照继续作为精确兼容依赖保护。本轮不再等待发色取舍，后续发片修正与未关闭边界由[独立正式槽位头发审查](./CHARACTER_RUNTIME.md#321-独立人物与头发审查关卡2026-10-17)承接，R17及生产Gate不晋升。

#### 2026-10-17 共用头发覆盖修正接入（技术交付、待用户视觉；皮肤／睫毛未解决）

`ue_scene_site_appearance_v1.apply_actor`在现用发色应用之后调用`ue_hair_coverage_runtime_v1.apply`，并将helper版本纳入装配缓存签名、将`hair_coverage`写入返回读回。独立审查调用同一正式38槽装配器，因此不会形成只在审查关卡有效的专用修正。helper、HB1_01双性别遮罩恢复、clip=.34/.44的依据及派生MI所有权归[Runtime §3.21](./CHARACTER_RUNTIME.md#321-独立人物与头发审查关卡2026-10-17)。当前颜色父材质和反光参数继续继承，标准10色、源资产及阴影保持；本次不重新启用已取消的柔反光选项。

旧男性及更晚图因Slate回调重入与重叠Actor污染而无效；恢复后busy guard驱动已完成14张对照图并恢复原选择，root实际查看AM001/HB1_01及HB3_02前后图确认改善，女性两款也已重拍。可选目录Python绑定检查33case／117网格／199槽通过，130Hair槽修正、59零遮罩及10发饰保持，继承参数和源资产不变、重复应用幂等；详细证据归Runtime §3.21。adapter命令边界重载列表包含coverage helper；receipt区分`source_material_bindings_unchanged`与`source_assets_modified`，派生组件绑定变化不等于源资产改动。

实际游乐园既有点位WF003/HB1_01、`MOTION_CAND_008`在0.5／1.3秒与独立review全部38槽一致，`hair_production_parity.json`为success=true、differences=[]、头部运动已观察，点位文件SHA保持；`targeted_pytest.json`实际42passed／11.63秒。`color_coverage_check.json`success=true、count=10，在LM002/HB1_02一代表逐一核对标准10色的scalar／vector／switch继承及源材质保持，场景组件未改；不是全发型十色渲染。头发修复本轮技术交付完成，用户重点审查男女1号及其他边缘；MRQ全片与全款视觉不自动通过。

皮肤／睫毛诊断与尝试已完成但未解决。颈胸低高光未修复，常量Normal虽减弱但损细节，简单Diffuse＋Normal、物理源Normal重导及保留导入法线／关闭加权法线／重算Mikk的独立clone均仍有边界，原网格已恢复、未推广；不能据此断言CC法线损坏或排除所有切线框架。睫毛隐藏槽对照支持源诊断，CC候选尚未实施。后续CC处理交接与所有证据由Runtime §3.21及其源审计拥有。R17继续in_progress等待用户视觉，生产Gate保持原边界。

### 22.2 两种动作时钟、旧审查与正式目录

`source_mode=production10`直接采样正式10秒身体；`source_mode=full`保留既有选用段的完整时长和速度，由 `production_motion_contract_v1.map_output_time`转换原始动作采样时刻。full不是强行展开整份源动作所有区间。相机分别读取 `production_workflow_20261017_v1/camera_library/{full,production10}/{camera_plan,catalog,geometry}.json`，每模式26动作×21镜头×横竖1092组合；沿用原检查函数与局限，本轮不增加碰撞认证。检查进行时拒绝更换人物或时长。模式/外观/输入变化进入签名，旧报告不继续充当新时钟通过。

载入旧点位时，原点位JSON不改，完整记录另存 `scene_site_review_20261014_v1/historical_site_reviews/`；四个已移除动作的旧排除单列保留。仍存在的明确 `excluded` 保持为当前保守限制，不因时长、人物或输入版本变化重新启用。保存过的用户逐组合选择优先于旧导入默认；旧 `allowed`、问题结论和几何报告不因此晋升，保留在历史/待复核信息。迁移限制另存来源archive、逐组合origin和点位位置/朝向绑定，以 `decisions_stamp_kind=exclusion_intent_only`供原检查入口读取排除；该签名仅绑定“继续排除”的意图，不是检测通过。只在同site/map/位置/yaw且当前行仍保留这些排除时重绑；点位移动后原绑定失效，用户明确恢复并保存可解除限制。当前runtime保存的决定可保留原签名按freshness核对；输入改变时也只保留其中明确排除，不提升旧允许或旧问题结论。

资产搬移前由root执行 `ue_production_site_runtime_v1.capture_motion_before_relocation()`，完整核验52bake及104正式body文件；搬移后先发布 `asset_inventory_formal_runtime_v1.py` 的正式资产目录，再执行 `publish_formal_motion_runtime()`。新动作目录绑定搬移前快照、原不可变bake回执、成功move receipts的精确 `saved_referencers` 重存解释和104当前SHA，发布 `production_motion_formal_runtime_active_v1.json`。这继承搬移前全帧证明并补迁移来源，不声称搬移后重新逐帧验证。正式资产指针存在但新动作目录未发布时拒绝复用旧hash。试片按外观性别选择正式身体/模板，场景、地图/序列及plan pins校验通过后才提交MRQ。

### 22.3 定向验证与待执行冒烟

本节新增测试所有权为 `00_engine/scripts/unreal/tests/test_ue_production_site_runtime_v1.py`、`test_ue_production_trial_render_v1.py`；原 `test_primary_saved_site_adapter_v1.py`、`test_scene_site_review_panel_v1.py`继续覆盖场景保护、曝光、面板外观与保存行为。离线覆盖正式文件无重存证据拒绝发布、后续hash变化拒加载、旧排除归档且不自动通过、缓存worker升级、实际按外观性别解析动作、外观与点位分开保存等合同；离线通过不替代真实UE、整矩阵、服装适配或画面接受。

`panel_exclusion_intent_validation_v1.json`绑定保守排除保留修正的源SHA与22项定向离线测试（1.05秒）；核对有效旧排除持续、原site字节不变、历史完整归档、输入/时长变化只重绑排除意图、点位移动失效，以及用户明确解除后不被旧默认复活。该回执没有UE操作或全矩阵执行，不替代待执行smoke。

本Run `production_panel_smoke_plan_v1.json`为root串行执行的待执行请求计划，初始 `prepared_not_executed`。它要求当前已打开用户“游乐园 / 1”的精确主图，读取该点用于不保存的临时预览，切换男女、蓝/银白发色、微笑/静息，保存两个独立 `__SMOKE_ONLY_` 外观并恢复，预览正式10秒与M008完整慢速时钟，最后恢复编辑器；禁止 `save_site/open_scene/check_start/check_all`，只核对原用户sites/drafts哈希与有限预览。全部4表情只核对菜单与来源，不把两种代表预览扩大为四表情全动作实机验证。实际运行后由root另写 `production_panel_smoke_validation_v1.json`，记录请求/回执、实际角色部件/颜色/表情、时钟、耗时及文件保护。当前没有声称该计划已执行；全局状态、Catalog/Inventory和完整文档审计由root代码冻结后统一维护。

本Run `production_panel_smoke_v1.py`是对应root-only验证辅助，仅显式调用 `run(u, request)` 或注入 `DM_PRODUCTION_PANEL_SMOKE_REQUEST` 才执行；单独导入不连接UE。先以 `action=start` 和具名 `run_id`固定用户点与原sites/drafts摘要，再以 `action=step`每次执行一个后续请求，避免首次脸部合成长调用；共13步，可用 `action=run`串行执行剩余步骤，`action=finish`清理并核对文件保护。脚本只允许当前正确主图、无渲染/检查，绝不调用load_level/save_map/save_site；返回实际38组件、6基础身份、身体动画与时刻、颜色材质参数、表情来源及有限骨点读回。两份独立测试外观以__SMOKE_ONLY_命名，记录落在Run/panel_smoke/&lt;run_id&gt;/；临时UObject不写入JSON，失败也清缓存并恢复预览。全源动作哈希只由正式目录首次验证，逐步调用复用private worker和目录缓存。此脚本已离线编译及13步禁用动作检查，尚未执行UE。

### 22.4 四条正式试片的编码、网页与资源记录

本节拥有 [encode_production_trial_v1.py](../../../../../../00_engine/scripts/unreal/encode_production_trial_v1.py)、[build_production_trial_gallery_v1.py](../../../../../../00_engine/scripts/unreal/build_production_trial_gallery_v1.py)、[open_production_trial_gallery_v1.py](../../../../../../00_engine/scripts/unreal/open_production_trial_gallery_v1.py) 及 root 使用的 [monitor_production_resources_v1.py](../../../../../../00_engine/scripts/unreal/monitor_production_resources_v1.py)。四条试片由 §22.1 的 UE helper 串行准备和渲染，离线交付脚本不操作 UE、不触发 MRQ，也不删除原帧。当前修订计划4条新片均已实际prepare、render、编码并完成300帧/10秒文件核验，implementation_status=completed_pending_user_visual_review；root抽帧检查见贴图恢复，用户画面接受仍pending。旧失败首片及其原回执不改写。

全部产物限定在 `production_workflow_20261017_v1`：`four_trials_plan.json` 固定四片选择和来源；`prepared/<shot>.json`、`render_receipts/<attempt>.json` 与 `renders/<attempt>/<shot>/frame_0000.png` 至 `frame_0299.png` 分别记录准备、实际渲染和原帧。编码命令为 `python 00_engine/scripts/unreal/encode_production_trial_v1.py <attempt>`，只接受成功结束、零起点的 30fps/300帧/10秒回执，横屏 2560×1440、竖屏 1440×2560。H.264 CRF18 临时文件须同时通过 FFprobe 全帧时间戳/帧数/分辨率/时长、FFmpeg `-xerror` 全片解码，以及视频首帧与 `frame_0000.png` 的有损RGB比较，再原子发布至 `videos/<shot>.mp4`；对应首帧缩略图为 `videos/<shot>.jpg`。RGB比较不称逐像素一致，零起点输入编号及全部300个时间戳另外证明无编码帧偏移。

本节拥有 `media_receipts/<shot>.json` 和 `media_validation/<attempt>.json`：绑定冻结plan、渲染回执、PNG顺序摘要、编码工具/命令、视频SHA、完整解码/首帧结果，以及真实准备、渲染、编码和校验耗时。已有合格视频仅按原来源和当前视频/缩略图SHA复用；来源冲突或无回执媒体拒绝覆盖。原帧清理必须由root另行授权并记录，编码器不因成功而自动删除。

`python 00_engine/scripts/unreal/build_production_trial_gallery_v1.py` 生成 `trial_gallery/index.html` 与 `gallery_data.json`，固定四张中文卡片，展示动作、镜头、分辨率、时长、文件大小及耗时表；未有合格媒体回执的卡片保持待生成，不提供未验证的视频地址。`--resource-report <本Run内JSON>` 可附资源记录链接。人物配置由同一试片plan呈现，文件校验与人工画面接受分开；本次新增定向测试为 `tests/test_production_trial_delivery_v1.py`，不以测试替代实际编码或浏览器审查。

本节拥有Run内 [打开四条样片审查.cmd](../../../../../../00_engine/outputs/production_workflow_20261017_v1/打开四条样片审查.cmd)，它只调用既有官方 `open_production_trial_gallery_v1.py` 提供双击入口，不操作UE或创建新渲染。

启动器默认隐藏启动后台服务，也可由root用 Windows `Start-Process -WindowStyle Hidden` 运行 `--serve --port 8886`。它只监听 `127.0.0.1`、只服务当前Run，复用既有RangeHandler支持视频拖动，从8886起实际绑定可用端口并跳过已保护端口，不停止其他服务。真实URL/PID、服务范围和索引SHA记录为 `trial_gallery/launcher_status_v1.json`；默认方式的日志为 `server_stdout_v1.log`、`server_stderr_v1.log`。root显式启动 `--serve` 时负责日志重定向，不能在尚未启动时把8886写成已可访问地址。操作说明归本节的 [README_TRIAL_GALLERY.md](../../../../../../00_engine/outputs/production_workflow_20261017_v1/README_TRIAL_GALLERY.md)，26动作时长说明为 [README_PRODUCTION_MOTIONS.md](../../../../../../00_engine/outputs/production_workflow_20261017_v1/README_PRODUCTION_MOTIONS.md)。

资源采样器每5秒只读记录可用内存、UE进程内存、GPU显存/利用率及D盘余量，输出 `resource_samples.jsonl`、`resource_latest.json`；root显式创建 `resource_monitor.stop` 后生成 `resource_report.json` 汇总。启动前若已有stop文件则拒绝，避免把未运行冒充新采样。它不改渲染质量、不自动取消UE或停止其他进程；5秒抽样不保证捕获瞬时峰值，GPU查询失败如实记入样本。上述资源文件及画廊/媒体回执由本节拥有，保留策略另由本轮明确清理清单控制；本次只追加此节并核对新增链接，不执行全库审计。

同节可选辅助 [run_serial_four_trials_v1.py](../../../../../../00_engine/outputs/production_workflow_20261017_v1/run_serial_four_trials_v1.py) 仅在root显式 `--execute` 后串行调用现有prepare/render/status并编码；默认只显示计划。每次开始prepare/render前核对可用RAM至少5GiB、D盘至少10GiB；复用精确匹配的媒体/准备/渲染证明，每10秒读取同一渲染回执。提交意图先落盘，短runpy远程入口把实际小回复写入 `serial_trials/commands/`，避免长TCP回显；`serial_trials/events.jsonl`、`progress.json`及独立失败JSON拥有实际阶段、资源快照和耗时。提交不明、失败或超时均停交root，不重试、不杀进程、不重启UE、不改拍摄参数或清理原帧；已有GPU采样器独立保留。本辅助已串行完成当前4片，实际回执及阶段事件保留；新增 `tests/test_serial_four_trial_driver_v1.py` 仅做离线回执/资源边界检查。

本节同时拥有Run内 [summarize_four_trials_delivery_v1.py](../../../../../../00_engine/outputs/production_workflow_20261017_v1/summarize_four_trials_delivery_v1.py) 及其 [delivery_summary_v1.json](../../../../../../00_engine/outputs/production_workflow_20261017_v1/delivery_summary_v1.json)、[four_trials_resource_summary_v1.json](../../../../../../00_engine/outputs/production_workflow_20261017_v1/four_trials_resource_summary_v1.json)。此离线汇总只使用当前plan的4个精确shot/attempt、合格媒体回执及serial事件：MRQ实际渲染合计89.494708秒，逐片prepare_start至trial_verified实际用时合计358.474203秒；处理五阶段合计另列，不能与实际用时混同。资源汇总限定4次成功批次各自准备/渲染/编码/校验区间，37样本可用内存最低7.451GiB、显存最高7584MiB；采样在每轮查询后等待5秒，探测本身有耗时，不是固定5秒连续采样或绝对峰值。全监控时段的resource_report与本四片区间汇总范围分开。

当前 [本机审查页](http://127.0.0.1:8886/trial_gallery/index.html) 的实际启动及HTML摘要由launcher_status_v1.json绑定；[http_delivery_validation_v1.json](../../../../../../00_engine/outputs/production_workflow_20261017_v1/trial_gallery/http_delivery_validation_v1.json)记录实际HTML HTTP200及4条video/mp4 Range206通过，浏览器视觉自动化未执行，不把Codex面板queued当作实际打开。root实际查看新首片0/150帧及其余三片150帧，皮肤/头发贴图与眼睛已恢复；正面受光较强、脸部偏亮，曝光保持用户设置，用户连续全片视觉接受pending。该交付不认证全部角色搭配、全场景或完整碰撞矩阵。

### 22.5 正式资产迁移、兼容保留与清理工具所有权

本节拥有Run内以下执行/恢复辅助及其策略、证明、逐项日志、发布目录和说明文档；这些是本轮受限执行证据，不作为另一个可自动扫描删除目录的生产入口。所有UE操作与删除由root串行执行，原失败回执不改写。

| Run内辅助 | 职责与边界 |
| --- | --- |
| `asset_inventory_ue_execute_fast_v1.py`、`asset_inventory_ue_driver_v1.py`、`asset_inventory_nullrhi_supervisor_v1.py` | 固定映射分批迁移及资源守卫；仅明确RAM不足且无未保存包时正常重启NullRHI，不杀健康编辑器。supervisor默认move，delete/delete_extra须显式选择。 |
| `asset_inventory_ue_copy_world_stages_v1.py`、`asset_inventory_ue_restore_parent_bridges_v1.py`、`asset_inventory_restore_skin8_v1.ps1` | 精确3个World正式副本、4个旧父材质兼容副本与8个皮肤材质文件恢复；复制不记作重命名，恢复前要求匹配记录中的当前摘要。 |
| `asset_inventory_ue_reconcile_crash_v1.py`、`asset_inventory_ue_reconcile_skeleton_batch_v1.py` | 只读核对原失败批次的实际类、路径、文件和引用；骨架批次另核对31目标、2份非保护源动画重存、104份身体文件及107份保护文件，生成新的成功恢复证据。 |
| `asset_inventory_ue_offline_delete_proof_v1.py`、`asset_inventory_delete_exact_packages_v1.ps1` | 对固定9038候选合并查询新鲜registry引用，不load资产；外部引用及其候选依赖保留。编辑器正常关闭后，按证明SHA和每文件路径/大小/修改时间校验并精确删除，逐文件记录删前与删后，不递归删除目录。 |
| `asset_inventory_remove_empty_legacy_dirs_v1.ps1` | 只遍历Validation/CharacterFactory，跳过皮肤范围和目录链接，逐目录确认零条目，再调用禁止递归的删除接口。默认仅预览。 |
| `asset_inventory_formal_runtime_v1.py` | 发布并验证当前人物外观目录及原路径映射，保留历史源证明；当前palette代码兼容仅按精确来源摘要和已批准的AST差异规则绑定，不篡改历史快照。 |

实际完成证据：6262项正式映射、材质恢复后1385份当前文件摘要及52个动作版本运行目录已发布；9038个旧文件共33,287,811,235字节由 `asset_inventory_exact_file_delete_20261016T182824_55b4cf78.json` 确认删除；2554个空目录由 `asset_inventory_empty_dir_cleanup_20261016T183257_68bf6a12.json` 确认删除；旧审核渲染媒体回收57.585 GiB。新鲜9038项合并引用证明无外部保留引用阻塞，删除排除当前正式文件和107份保护文件。

必要兼容源仍保留：79份共享资产使用正式副本，4份旧父材质支持恢复后的皮肤引用，3份旧场景支持正式舞台副本；其他迁移源保留重定向。实际迁移两套Skeleton时，2份未受保护的旧源动画及104份正式Body因引用更新重存，由 `asset_inventory_execute_recovery6144_01.json` 和明确例外策略绑定当前摘要，不声称旧字节不变。用户点位、审查记录、历史接受证明、主场景来源和必要导入源保留。实际面板13步检查已通过，4条新片渲染、编码和文件验证完成，用户视觉审查pending。

本节拥有的面向使用者说明为Run内 [正式资产目录说明.md](../../../../../../00_engine/outputs/production_workflow_20261017_v1/正式资产目录说明.md) 与 [清理结果说明.md](../../../../../../00_engine/outputs/production_workflow_20261017_v1/清理结果说明.md)。本次只核对本节新增指针及实际回执；全局状态、脚本Catalog、Output Inventory与全库审计由root最终统一维护。


#### 2026-10-17 追加清理执行与恢复边界

本节继续拥有Run内`delete_reviewed_cleanup_targets_v1.ps1`、`exports_reviewed_cleanup_plan_v1.json`、`temp_outputs_reviewed_cleanup_plan_v1.json`、`old_scene_media_cleanup_plan_v1.json`及三份同名`.receipt.json`回执，另拥有`root_pytest_cleanup_20261017_v1.json`。它们为用户明确追加授权的临时树、旧导出、旧审查媒体和PNG原帧清理证据；不构成通用自动删除授权。三份批次回执及pytest回执均已完成，增量统计见Run/清理结果说明.md，与此前88.587GiB分别记账。

当前四条合格视频和海报、试片网页、正式资产、轻量清单与冻结配置保留；Run/renders五组原始PNG帧已退休，重新编码必须先按冻结配置重新渲染。media_receipts与media_validation中的原帧摘要仅证明当时生产和校验过程，不表示原帧仍存在。旧all_primary_scene_sites媒体已退休，其gallery/index.html只保留退休说明及当前8886审查页链接。32点位独立审查、其他会话皮肤范围及现用CC/重建输入保护，未证明可退休的bridge源不记为清理完成范围。

### 22.6 首片视觉失败后的正式材质引用恢复（引用恢复及新四片已完成，用户待审）

26动作男女52版全帧数值通过、6262项正式迁移及初版952项文件目录发布，以及13步面板实机功能通过，不等于四片画面交付。`formal_trial_01_v1` 已编码300帧/10秒并通过完整解码，但首片皮肤、头发发白，实际视觉失败；当时其余3片尚未渲染，原失败媒体不计入当前交付。旧媒体73617文件与旧UE资产9038文件清理合计释放88.587GiB，另清2554空目录，清理回执保留。454个正式材质实例引用已完成恢复，涉及971贴图、1父材质、11皮肤散射配置；独立after审计实际解析6262个正式包，缺失旧导入为0。原INI已逐字节恢复；移除临时重定向后新GPU进程PID12540只读核对454项当前SHA及规范化快照通过，未保存资产。当前正式目录已重新发布，包含1385项当前文件指纹。新首片已以materials_v2独立版本完成，与其余3片共同通过文件验证；root有限抽帧检查恢复，用户全片审查pending，准确结果归Run/delivery_summary_v1.json。

本节拥有 [asset_inventory_offline_dangling_imports_v1.py](../../../../../../00_engine/outputs/production_workflow_20261017_v1/asset_inventory_offline_dangling_imports_v1.py)、[inspect_trial_materials_v1.py](../../../../../../00_engine/outputs/production_workflow_20261017_v1/inspect_trial_materials_v1.py)、[ue_formal_material_redirect_repair_v1.py](../../../../../../00_engine/outputs/production_workflow_20261017_v1/ue_formal_material_redirect_repair_v1.py) 、[ue_formal_material_post_redirect_verify_v1.py](../../../../../../00_engine/outputs/production_workflow_20261017_v1/ue_formal_material_post_redirect_verify_v1.py) 及 [asset_inventory_formal_runtime_v1.py](../../../../../../00_engine/outputs/production_workflow_20261017_v1/asset_inventory_formal_runtime_v1.py) 的材质修复发布边界。`trial_material_actual_v1.json`、`trial01_material_diagnosis_offline_v1.json` 和 `asset_inventory_material_old_import_audit_v1.json`保存初始诊断；原 `asset_inventory_formal_dangling_imports_v1.json` 独立解析6262个正式包的实际NameMap/ImportMap，定位454个材质实例仍引用983个已不存在的旧包：971张贴图、1父材质、11个SubsurfaceProfile。983个对应正式目标均存在，问题是旧导入引用未持久重绑定，不能凭目标文件存在判为材质完好。

恢复必须由root串行操作：helper的 `redirects('install', run_id)` 只从冻结moveplan和原审计生成精确PackageRedirects，备份项目DefaultEngine.ini，不使用wildcard/substring；root自行关闭并以该临时配置启动干净UE，确认后再 `run(u, {'action':'start', 'run_id':..., 'fresh_process_with_exact_redirects':True})`。454个正式材质原包先按SHA备份，`step`先全体preflight只读核对已恢复贴图/父材质/散射引用，再进入白名单保存阶段；默认每步50项，限定1–100项。保存前后记录标量、向量、开关、基础覆盖及引用快照，不调用贴图参数setter，不保存源场景或另一会话皮肤原资产。已经在旧进程加载成空引用的对象不能直接重存冒充恢复。helper不自动重启编辑器、改画质或推送下一阶段。

`material_redirect_repair/<run_id>/`拥有原材质备份、`context.json`两阶段进度、preflight快照、临时INI备份与 `temporary_redirects.json`；失败保留 `failure.json`，成功仅产生 `asset_inventory_execute_material_restore_<run_id>.json`，列出454项 `saved_referencers` 当前SHA及参数保护边界。成功保存回执仍明确无重定向新进程验证pending。root须用 `redirects('remove', run_id)`在安装后INI与备份SHA完全匹配时恢复原INI，随后自行启动不带临时重定向的新UE核对454项实际绑定及快照。INI存在其他改动时拒绝覆盖，交root协调，不回写另一会话配置。

原before审计不可覆盖；after审计须用新的 `--output-name asset_inventory_formal_dangling_imports_after_material_repair_v1.json` 保存，重新核对6262正式目标且 `assets_with_missing_old_imports=0`。新UE证明另存 `asset_inventory_formal_material_post_redirect_validation_<id>.json`，绑定修复回执、after审计、INI移除记录和当前文件，逐项证明454份保存SHA及preflight快照一致。前后审计均不可变；新结果不能覆盖原失败审计或把“原先有问题”改写为“从未有问题”。`formal_material_redirect_repair_offline_validation_v1.json`仅记录helper的离线边界检查，`ue_executed=false`不当实机修复证明。

发布器新增 `--verify-material-repair` / `verify_material_repair()`，只有精确454项修复回执、全6262 after审计、去临时重定向新进程证明及当前454文件均匹配才通过；`--publish-current`才创建新版本目录并更新active指针。目录记录 `material_reference_repair.proofs`并让当前指纹覆盖已修复材质，运行加载器继续核对这些证明，旧before快照、旧正式目录和旧媒体回执保持不可变。实际完成证明为 `asset_inventory_formal_material_post_redirect_validation_formal_material_post02.json`（PID12540、454项通过）和 `asset_inventory_formal_runtime_catalog_20261016T191604.json`（1385项当前指纹）；原INI字节恢复及6262包after审计缺失旧导入0已绑定。after仍记录78个含映射旧导入的包，不把“零缺失旧导入”写成“零旧引用”。身体运行目录重发、修订计划及新4片技术交付已完成，有限抽帧检查见贴图恢复；不把该检查写成用户已接受全片。

只读postverify辅助由本节拥有：`run(u, {action:start|step, run_id:...})`要求root确认移除临时重定向后的新进程，绑定修复、after审计、INI恢复及helper摘要，分批核对454项实际绑定、当前文件SHA和preflight快照。只将 `base_property_overrides` 不透明repr的进程内存地址规范成 `0xADDRESS`；不声称该结构隐藏flags可读或已比对，其他已读取标量、向量、开关、贴图、父材质及散射引用精确比较。辅助不保存资产、不加载场景、不改INI，并核对dirty packages不变；实际证明、context、失败记录各归独立验证批次，不改写修复回执中的历史pending字段。

材质修复后首片须另存旧plan原文/SHA与旧批次对应关系，当前计划刷新相同外观选择的来源指纹，并使用新shot_id、prepare地图/序列和新attempt复拍；只换attempt仍会碰到旧prepared或已核验视频复用。原白材质视频、PNG和准备/渲染/编码回执保留为视觉失败证据。root已查看新首片0/150帧及其余3片150帧并完成4片网页技术交付，用户视觉审查仍pending；历史版本切换方法见Run [README_TRIAL_GALLERY.md](../../../../../../00_engine/outputs/production_workflow_20261017_v1/README_TRIAL_GALLERY.md)。本次只同步R17有关段落与链接，不改其他会话皮肤状态/历史，不运行全库审计或完整测试。

### 22.7 轻微地形整体高度跟随（2026-10-19，运行确认完成，用户视觉待审）

用户授权仅处理轻微地面高低变化：人物整体Z随地面差值升降，保持直立，不做脚部IK、楼梯适配、骨骼姿态修正或视频交付。以下实现及测试由本Technical拥有；新helper为`experimental`，本次接入不晋升生产Gate：

| 入口 | 所有权与作用 |
| --- | --- |
| `00_engine/scripts/unreal/ue_ground_height_follow_v1.py` | 预览与Sequence共用高度采样/绝对ActorZ公式；无前帧累计 |
| `00_engine/scripts/unreal/ue_production_site_runtime_v1.py` | 预览在每次原点位放置和身体姿态装配后调用helper；full模式以`map_output_time(0)`的真实source start作地面基准 |
| `00_engine/scripts/unreal/ue_production_trial_render_v1.py` | 未来新prepare按实际合成动画与同helper采样；保存策略/采样与轨道回执，拒绝以缺少当前策略的旧prepared执行新提交 |
| `00_engine/scripts/unreal/ue_motion_scene_sequence_v1.py` | 30fps含终点的逐帧绝对ActorZ轨道；X/Y、旋转、缩放保持默认，不改身体动画自身Z或相机轨迹 |
| `00_engine/scripts/unreal/tests/test_ue_production_trial_render_v1.py`、`tests/test_motion_scene_sequence_v1.py` | 轨道采样网格、绝对高度/起点、prepared策略与提交拒绝等有界离线回归；root记录两文件21项通过，本次文档同步不重复执行 |

采样先用动画pose的`pelvis`在`AnimPoseSpaces.WORLD`（模型空间）位置，经Body的实际`get_world_transform()`转到场景XY，只在起点与当前XY向下trace可碰撞地面。公式为`actorZ = siteZ + ground(t) - ground(start)`，不读取poseZ去抵消原动作起伏，也不沿前帧累加；相机保持原路径，人物不随坡面倾斜。trace忽略角色及拥有的附属部件，当前位置无可碰撞地面时明确报错，不能将该路径理解为自动选择可行地形。

[installation.json](../../../../../../00_engine/outputs/pair_scene_review_20261019_v1/ground_height_follow/installation.json)success=true：当前AM001、沙漠加油站/1、ACT_M04_LIVING_ROOM_SWING、红发HB1_20/idle接入成功。[runtime_check.json](../../../../../../00_engine/outputs/pair_scene_review_20261019_v1/ground_height_follow/runtime_check.json)仅覆盖2.5→5→2.5秒三次真实UE调用，offset分别0.8424026813/0.2602549983/0.8424026813cm，same_time_no_drift=true、original_preview_restored=true。UE内部各约0.067–0.076秒，不是完整UI响应时长。这里只确认运行和重复时刻不漂移，未做画面视觉审查或实际渲染。

新Sequence源码已接同helper，并烘焙含终点绝对ActorZ键；实际正式render仍未执行，不能用离线21项或预览3点推定渲染画面通过。旧prepared缺`ground_height_follow_v1`策略时拒用于新提交，保留旧回执/视频并用新trial ID重新prepare；不改写历史媒体。该实现不保证脚掌贴合、复杂坡地、台阶或全部人物/动作组合适配。root已重开面板ready（PID23716，error=null）并恢复当前搭配/时刻；用户自行视觉审查，R17继续in_progress，余38人未启动。

### 22.8 已审查点位继续迭代（2026-10-20）

本轮沿用`PLAN-2026-10-CAMERA-MOTION-SCENE-ALIGNMENT/R17`、`WF-60`、`OUT-WF60-SEQUENCE-TEMPLATE`及`VAL-SCENE-01`的受影响范围，Run为`%OUTPUT_ROOT%/scene_review_iteration_20261020_v1/`，入口为[WORKING_STATE.md](../../../../../../00_engine/outputs/scene_review_iteration_20261020_v1/WORKING_STATE.md)。用户已审查保存的“场景名/1”，未标记问题按其本轮审查接受，已保存排除保留；不扩展为全身份/外观/镜头/地形接受或最终冻结。`R17=in_progress`，不改变生产Gate。

#### 基线与恢复

`baseline/manifest.json`逐项绑定当前点位、独立外观、面板草稿/状态、源目录/几何/脚本及直接文本引用；`baseline/inventory.json`与`inventory_analysis.json`拥有精确计数、排除和下一次接手清单。基线复制配置和轻量来源，不复制UE二进制或渲染媒体；恢复时按清单的`source_path`与`snapshot_path`映射，不假定其中绝对引用已重写。现用动作合同/指针/目录另有gzip原字节快照。相机改前7份配置及原builder仅由`camera/before/`拥有，基线引用其路径与SHA避免重复。

基线51份点位中21份为用户`site_*`保存点，29份独立外观、3份签名草稿。地铁站/1保存642项排除；旧停车场试点的1项排除另列。草稿中的292/342排除及7项可接受问题保留各自签名，不相加或自动覆盖保存值。中式建筑/1的265项及加油站/1的1项问题已保存为可接受。19份外观链接存在；游乐园`site_4e6b9c18d9`与中式建筑`site_def046be4c`未带外观ID，继续使用当前外观，不自动补绑。

#### 镜头、主图与地面实现所有权

本节显式拥有`00_engine/scripts/unreal/build_production_camera_library_v1.py`及`tests/test_production_camera_library_v1.py`的本次修复，Run内`camera/repair_library.py`、`repair_validation.json`、`preservation_audit.json`及`derivation.json`拥有一次性离线派生与来源解释。横屏标准把运动preset收进`camera_standard_v2.superseded_source_diagnostics`后，十秒builder原先静默默认成静止；现读取归档preset，缺失时拒绝。基于既有接受后的key向量恢复208条正式10秒横屏运动镜头：26动作各8镜头；该模式其他884条及full模式1092条轨迹/shot对象均保持，身体几何及动作时钟保持。416条正式运动组合离线覆盖通过，实际runtime loader两模式各1092条及source pins检查通过，17项定向测试通过。旧几何加载入口仍因历史sequence SHA不符拒绝，故从改前full现成key派生；本轮没有重新抽样身体几何，不把离线派生称为真实UE或视觉检查。

`scene_site_catalog_v1.py`及`tests/test_scene_site_catalog_v1.py`、`tests/test_scene_review_catalog_iteration_20261020_v1.py`拥有当前主图选择：原源索引与迁移表保持，新增`PRIMARY_MAP_REPLACEMENTS`将未来都市改为`/Game/Scenes/FuturisticMetaCity/Maps/VirtualMetaCity`，`RETIRED_REVIEW_PACKAGES`将科幻建筑3张候选退出primary，仍保留源图/资产/旧点。双人面板现有primary过滤自动消费此选择；本地只读[目录验证](../../../../../../00_engine/outputs/scene_review_iteration_20261020_v1/catalog/catalog_policy_verification_v1.json)为23主图/23包、其他72行完全保持，13项catalog/pair定向测试通过。21份用户点尚缺沙丘Dunes与未来都市新图；新图点位待用户指定，不移植旧ShowcaseMap的坐标或接受。

`ue_ground_height_follow_v1.py`及`tests/test_ue_ground_height_follow_v1.py`拥有三指定点的`fixed_saved_site_plane_v1`解析地面；`ue_production_site_runtime_v1.py`及`tests/test_ue_production_site_runtime_v1.py`接入预览、贴地和地面probe；`ue_production_trial_render_v1.py`接入未来新prepare及旧prepared拒复用。只匹配九龙`site_98aac485de`、教堂`site_235511f7b9`、赛车场`site_cbee266c51`的精确ID+map，覆盖无限XY，平面Z读取当前点位有效高度，原XYZ另存来源；不创建地面Actor、不改源场景或保存点、不做IK，也不抹去动画自身跳跃。检测仅替换地面probes，身体/射线/球扫/相机/遮挡原检查保留，作用域写`job.scope.ground_support`。29项初始及扩展43项ground/runtime/trial/sequence离线测试通过，准确依据为`ground/source_implementation_v1.json`、`source_tests_v1.xml`、`runtime_integration_tests_v1.xml`；这些不是实机画面或全地形接受。

#### 当前运行与下一步

共享UE由root串行验证已完成。公路15点、海滨小镇5点、京都5点共25个真实相机Actor读回经[独立比对](../../../../../../00_engine/outputs/scene_review_iteration_20261020_v1/camera/runtime_readback_audit.json)与修复计划逐点位置一致；三个代表场景的数值通过不替代全镜头/全动作或连续画面接受。`camera/final_integrity.json`统一绑定相机来源及最终证据51条引用。三指定点的[地面运行验证](../../../../../../00_engine/outputs/scene_review_iteration_20261020_v1/ground/runtime_validation.json)使用AF001/MOTION_CAND_003、横屏，九龙/赛车场为front_full，教堂为front_upper；各0→5→10→5秒预览、重复时刻无漂移、贴地成功，每处301个实际UE轨迹采样，共903样本，实际轨迹通过共用Sequence-builder入参校验。此范围未实际提交MRQ或播放新Sequence，不证明全动作/独立跳跃画面接受。继续使用新版AF001/AM001两人的完整面板。修改后40人独立导入已全部完成，权威为[当前导入交接](../../../../../../00_engine/outputs/character_refresh_20261018_v1/CURRENT_IMPORT_HANDOFF_20261019.md)及夜间delivery；本轮不将另38人加入面板，不修改独立导入回执，也不晋升新版动画/试穿/视觉接受。§22.7及旧段落的“余38未启动”仅指当时白天检查点。

私有快速审查启动在选定图中跳过继承几何的历史来源重审，新增隔离测试及四份pair测试共37项通过；缺文件仍失败，全局正式加载器及另一私有图保持错误SHA拒绝。该源码与测试继续由[角色Runtime §3.22](./CHARACTER_RUNTIME.md#双人审查启动继承几何的私有快速路径2026-10-20)拥有，不借此放宽正式渲染输入验证。

曝光适配为部分尝试后停止，准确依据是[lighting_summary.json](../../../../../../00_engine/outputs/scene_review_iteration_20261020_v1/lighting_summary.json)与`survey_progress.json`：计划21个用户点，实际串行尝试九龙/教堂2点，九龙截图未成功，教堂原EV及临时+1EV有两张比较图，另保留赛车场原值截图，共3张编辑器小图。只读取公路、海滨小镇、京都、教堂、九龙和赛车场6图灯光元数据，未完成全部场景亮度适配。可用物理内存低于3GiB后按用户允许停止，UE保持存活；稍后资源读回不是连续峰值。教堂平均RGB约58.82→63.38，但脸部仍明显背光，单纯补偿未解决主体/背景对比。未发布新EV，原保存值已恢复，不自动继续补光改造。

[保存保护](../../../../../../00_engine/outputs/scene_review_iteration_20261020_v1/saved_state_preservation.json)确认51点位+29外观+1草稿文件共81份SHA保持，642条用户排除均仍属当前相机目录，三份草稿未合并。[最终实机读回](../../../../../../00_engine/outputs/scene_review_iteration_20261020_v1/final_runtime.json)及[面板ready](../../../../../../00_engine/outputs/scene_review_iteration_20261020_v1/panel_ready.json)确认PID33468的UE与PID27088面板，教堂/1、front_upper横屏5秒、EV0且相机补偿override关闭、23主图与两人菜单；未来都市明确“待选拍摄点”。内容dirty为空，教堂map的dirty只来自临时预览Actor，本轮没有保存源场景。当前交付限定技术修复并等待用户继续迭代，复查顺序见[NEXT_REVIEW.md](../../../../../../00_engine/outputs/scene_review_iteration_20261020_v1/NEXT_REVIEW.md)，不是全部亮度处理完成或最终冻结。

本Run及新增源码/定向测试由本节拥有，Output ownership rule只新增本Run，默认`unclassified`继续保护。`documentation_import_pointer_reconciliation.json`保留过期场景执行指针的历史副本并证明独立40人导入对象未改，`documentation_closure.json`记录最终有界收口。最终只做本轮链接/锚点、来源SHA、单current计划、R17、输出/脚本所有权与机器状态的有界检查；既有导入交接报告的890项全库问题保留，不扩展修复。当前由`WORKING_STATE.md`和Status给出唯一下一步，点位/镜头稳定后再讨论新渲染计划，旧prepared与媒体不改写。

### 22.9 教堂相机遮挡漏检与简化碰撞补查（2026-10-20）

本轮在R17/WF-60范围修复双人面板的相机检查，Run为`%OUTPUT_ROOT%/church_camera_occlusion_20261020_v1/`，本节拥有该输出范围，默认`unclassified`保护。当前教堂`site_235511f7b9`位于`/Game/Scenes/Madeline/Maps/Exterior`、XYZ=`0,-1200,0`；不沿用早期`0,0,0`点位推断现场。旧报告`check_13d94791206b.json`虽完成1092组合/23478采样且0问题，只能说明旧查询没有命中，不能证明画面无遮挡。

[collision_census.json](../../../../../../00_engine/outputs/church_camera_occlusion_20261020_v1/collision_census.json)记录场景碰撞状态；1607个场景静态网格均启用查询并阻挡Visibility，不能将本次漏检归因于全部关闭碰撞或忽略该通道。[nearby_meshes.json](../../../../../../00_engine/outputs/church_camera_occlusion_20261020_v1/nearby_meshes.json)显示同位置复杂查询漏过附近物体、简化查询可命中。[mesh_collision_settings.json](../../../../../../00_engine/outputs/church_camera_occlusion_20261020_v1/mesh_collision_settings.json)进一步确认五项`SM_Altar_Floor`、`SM_Altar_Stair_01`、`SM_Base_Pillar_Holder03`、`SM_Altar_Stair_Fence`、`SM_Inner_Floor01`的网格section碰撞均为false，但各有1个convex简化碰撞体；对照`SM_Roof01`的section碰撞为true、convex为2且复杂查询可命中。旧worker只做复杂Visibility查询，因而漏过这些有可用简化碰撞的可见物体；本次没有修改任何源资产的碰撞设置。

[fallback_probe.json](../../../../../../00_engine/outputs/church_camera_occlusion_20261020_v1/fallback_probe.json)使用当前`MOTION_CAND_001/orbit_360/landscape`的21个原有时刻和最多五个画内骨点：复杂查询命中0，简化查询命中61，涉及9个Actor。0秒足部射线已命中`inner_floor`高于点位的17.5cm表面；3/3.5秒栏杆、4.5/6秒相机起点处台阶、7.5秒柱脚均另有命中。该证据区分“原查询无结果”和“实际画面无遮挡”，简化碰撞仍可能封住栏杆等真实空隙，不能直接据此自动排除镜头。

实现与测试所有权：`00_engine/scripts/unreal/ue_camera_collision_proxy_review_v1.py`及`tests/test_ue_camera_collision_proxy_review_v1.py`为本节的实验性私有补查；`pair_scene_review_20261019_v1.py`、`tests/test_pair_camera_check_integration_v1.py`拥有双人面板集成及旧报告失效。本次不改冻结`ue_scene_site_review_v1.py`，也不向其他面板或正式渲染路径自动推广。新installer先执行原复杂检查，再为尚无原同类发现的相机8cm球扫和人物可见骨点补做简化Visibility查询；忽略角色及其附属Actor，沿用原0.5秒/终点、最多五点和脚/前掌支持地面例外，身体碰撞与地面策略保持。代理发现分别为`camera_collision_proxy`和`occlusion_proxy`，按镜头、类别、component/Actor保留每个障碍的首次时刻，避免首个足部/地面发现掩盖后续栏杆；消息带Actor名并提示需预览确认。hit另存查询方法、起止点、component、起点是否已在碰撞体内及球半径。

检查方法为`complex_visibility_with_simple_camera_proxy_v1`、installer revision=1。报告写入方法、版本和简化碰撞局限；已有`scope.ground_support`时，其`camera_occlusion_policy`改为该方法，避免继承的`unchanged`误示未补查。安装幂等，报告扩展先复制字典，不污染旧报告对象。私有集成把方法加入stamp，旧方法报告明确要求重查；显式检查启动及结束刷新场景快照，日常浏览继续使用快速缓存，不恢复逐次浏览的全场景/文件哈希验证。面板显示“采样已完成”及“结果为检查时快照；在UE中改动场景后请重新检查”，不承诺持续自动发现后续场景修改。

12项补查离线测试通过；root另完成25项有界集成测试，覆盖旧报告失效与私有安装。实际单组合报告[check_cb00e4f6d1a1.json](../../../../../../00_engine/outputs/pair_scene_review_20261019_v1/reports/check_cb00e4f6d1a1.json)为complete、42/42采样，发现15项：6项相机代理碰撞、9项遮挡代理；证明新查询能揭示本次漏检，不代表这些15项均经人工确认，也不是1092组合重新通过。最终元数据重跑[check_fb9833853bcf.json](../../../../../../00_engine/outputs/pair_scene_review_20261019_v1/reports/check_fb9833853bcf.json)同样42/42、15项，方法字段一致；[runtime_validation.json](../../../../../../00_engine/outputs/church_camera_occlusion_20261020_v1/runtime_validation.json)确认点位/外观关联及预览保持、内容dirty为空。两个历史报告均保留。原现场记录见[before_install.json](../../../../../../00_engine/outputs/church_camera_occlusion_20261020_v1/before_install.json)；本轮不改相机轨迹、点位、外观保存或场景资产，R17继续in_progress，视觉确认与生产Gate不晋升。

### 22.10 同一拍摄点的人工排除持续保留（2026-10-20）

用户要求同一拍摄点的排除项在刷新、移动、转向、外观切换和检查版本变化后继续保留，直至本人取消。该范围继续归R17/WF-60、`OUT-WF60-SEQUENCE-TEMPLATE`与`VAL-SCENE-01`；本节拥有Run `%OUTPUT_ROOT%/site_exclusion_persistence_20261020_v1/`，默认`unclassified`保护。排除是用户对组合的限制，不是新位置已检查通过；旧报告、允许决定和具体问题的审查仍按原检查签名失效。

旧面板把点位坐标、朝向和检查签名纳入草稿键；同点位变化后会转到另一个草稿，冻结worker也会在签名过期时隐藏决定，保存时清空，原私有迁移限制还绑定坐标/朝向。新增`00_engine/scripts/unreal/pair_review_site_intent_v1.py`为本节拥有的`experimental`私有installer，装在双人面板的快速路径与相机补查之后；`pair_scene_review_20261019_v1.py`拥有装配入口。既有冻结`ue_scene_site_review_v1.py`和共用`ue_production_site_runtime_v1.py`保持，不把本私有语义自动推广给其他工作流。

保存点新增`manual_site_intent`：schema=`pair_review_manual_site_intent_v1`，只以`map`与`site_id`绑定，`excluded_combinations`保存完整排除快照。显式空列表表示全部取消，也是权威快照；载入时不得与旧导入排除求并集或复活已取消项。旧文件已有`allowed_combinations`时，准确读取其中排除项，包括空列表；仅该字段缺失时才读取导入排除。私有stamp调用临时隔离旧迁移器的隐式重签行为，状态在旧签名失效后仍显示独立排除；报告的新鲜度、全矩阵标记、当前允许决定及问题审查保持原判定。保存过期签名的排除快照可行，但非空旧问题审查继续拒绝；没有新决定的普通保存保留仍有效的允许/问题记录，过期时只保留排除。保存调用沿用原外观/报告序列化，再把独立排除写入同一保存记录。

所有私有保存与检查请求必须携带`decision_site_id`和`decision_map`并与当前点一致，防止切换点位后才到达的请求写错点位。检查接受同一拍摄点的旧签名排除，未显式传列表时使用独立保存排除，显式空列表覆盖本次检查；作业与报告仍使用检查启动时的新签名，位置/场景变化的原过期机制不变。此机制不把已排除组合当成已检查，也不把“剩余组合完成”晋升为全矩阵通过。

`00_engine/scripts/unreal/pair_review_site_drafts_v1.py`及`tests/test_pair_review_site_drafts_v1.py`拥有私有面板草稿：键仅由map/site_id组成；同点位签名变化保留排除，清除旧允许决定、旧问题审查与撤销记录，保存/检查自动携带点位绑定。草稿恢复对旧签名只提取排除，按每点的最后完整快照恢复，不能把多个历史草稿累加；最后快照为空时保持为空。保存成功后的草稿清除继续沿用原面板行为。

`tests/test_pair_review_site_intent_v1.py`为本节拥有的14项离线回归，直接运行冻结worker的状态、保存和检查函数，并隔离UE操作；覆盖移动/转向/场景/外观/检查方法变化、同点位旧排除、空快照保存重载、禁止旧导入复活、当前允许/问题记录保持、过期问题拒绝、跨点请求拒绝及报告新鲜度。root最终33项有界测试通过，其中含6项实际Tk草稿策略与14项运行时测试；前序运行时与相机集成17项也通过。扩大到旧worker测试时另有3项既有失败：一项预期runtime7而现用源码为8，两项仍使用v2相机标准夹具而当前为v3；同次其余49项通过，不修改历史测试或以此宣称全库通过。

[draft_recovery.json](../../../../../../00_engine/outputs/site_exclusion_persistence_20261020_v1/draft_recovery.json)记录当前九龙`site_98aac485de`从最后可证草稿恢复842项排除；原保存文件随后出现的空列表对应本次用户报告的重置，不能用它反向证明用户已经主动取消。地铁`site_91fc32ba93`保持更新保存的642项，不退回旧342项草稿；京都`site_9a6519ec02`保持更新保存的空列表，不复活旧草稿1项。恢复逐点采用最后可证完整快照，不求历史并集；全部6份旧签名草稿保留，unresolved为空。该恢复写入新的稳定键草稿及当前临时状态，未改既有保存点文件。

[runtime_validation.json](../../../../../../00_engine/outputs/site_exclusion_persistence_20261020_v1/runtime_validation.json)为success=true：安装并恢复、X移动1cm且转向1°、同点刷新、恢复原位/原朝向四阶段均保持842项排除，报告fresh始终false；原预览和最终位置/朝向均恢复。最终九龙XYZ约`868.468,-240.807,0`、yaw约90°。[panel_ready.json](../../../../../../00_engine/outputs/site_exclusion_persistence_20261020_v1/panel_ready.json)确认重开面板PID9000、ready、error=null并读回842项；[saved_site_preservation.json](../../../../../../00_engine/outputs/site_exclusion_persistence_20261020_v1/saved_site_preservation.json)确认21份用户保存点SHA保持。这是当前一点的运行保留验证，不是全点/全组合检查或视觉接受；用户可继续审查并显式保存当前排除，R17仍为in_progress，生产Gate不晋升。Run简明恢复入口见[README.md](../../../../../../00_engine/outputs/site_exclusion_persistence_20261020_v1/README.md)。

### 22.11 当前拍摄选择与保存检查点（2026-10-20）

用户已确认公路、京都的相机恢复正常，并要求先保存当前进度和同步文档。当前选择退出教堂`Madeline`与赛车场`racing_track`，既有科幻建筑退役选择继续有效；源场景资产、旧拍摄点与历史检查保留。“四周张望”`MOTION_CAND_007`退出当前面板拍摄动作，不删除原动作或重写冻结26动作/1092组合相机库。当前有效选择为25动作、21镜头、横竖2种，每模式1050组合；这只是选择范围，不能称为1050组合已检查通过。沙丘`site_2831090e60`与未来都市`site_33328cb3f4`两份用户点已存在，当前选择覆盖21张主图、21个用户点，替代§22.8当时的“两个点待选”。

本节拥有`00_engine/scripts/unreal/scene_review_selection_policy_v1.py`及`tests/test_scene_review_selection_policy_v1.py`，生命周期为实验性私有审查；`scene_site_catalog_v1.py`及`tests/test_scene_site_catalog_v1.py`、`tests/test_scene_review_catalog_iteration_20261020_v1.py`继续拥有主图选择，新增退役包只影响当前目录选择。双人入口`pair_scene_review_20261019_v1.py`在私有生产runtime中安装动作选择，再安装当前目录计数；共用生产加载器与冻结库保留。选择层同时筛选动作、镜头、geometry、frame索引并改变选择指纹，防止旧全矩阵结果误用到新选择；精确实现和本轮定向测试结果以最终回执为准。§22.10同点位独立人工排除继续生效，取消的排除不从旧导入或历史草稿复活。

本节拥有输出Run `%OUTPUT_ROOT%/scene_review_checkpoint_20261020_v2/`，归`OUT-WF60-SEQUENCE-TEMPLATE`和`VAL-SCENE-01`，只增加精确输出所有权，默认`unclassified`保护。检查点负责绑定当前保存点、外观关联、独立排除、面板草稿与选择配置；[checkpoint.json](../../../../../../00_engine/outputs/scene_review_checkpoint_20261020_v2/checkpoint.json)、`before_manifest.json`和`saved_manifest.json`已保存：当前21个有效用户点，含退役点共23个用户点，1428项有效排除逐点保留；全部点位历史继续保存。[runtime_applied.json](../../../../../../00_engine/outputs/scene_review_checkpoint_20261020_v2/runtime_applied.json)为success=true，实际UE读回25动作／21镜头／横竖1050组合，目录21图／21包；当前沙丘点明确保存后XYZ、朝向、预览和排除保持。面板已重开。因截止时间优先，本轮未运行新测试，不借用旧测试结果宣称本轮通过。旧Run及§22.8–§22.10证据保留，不把历史候选坐标或旧检查通过移植到新点。

本Run的[camera_audit.json](../../../../../../00_engine/outputs/scene_review_checkpoint_20261020_v2/camera_audit.json)与[简要说明](../../../../../../00_engine/outputs/scene_review_checkpoint_20261020_v2/camera_audit.md)已完成独立离线核对：完整与正式10秒共2184条轨迹、680946个相机键，移除动作后的有效子集为2100条；每模式416条运动镜头（有效400）未见旧静止／角度问题。正式10秒1092条重新推导与当前键值一致；原208条横屏修复保持，完整模式1092条与改前一致。排除退役场景后46份保存文件含21个用户点／21张图，共2206344次相机采样点位变换核对通过。52份男女动作版本的104条资产元数据匹配；本审计未重hash动画二进制、重采男女身体几何或调用UE，没有新增渲染、碰撞、遮挡、地面和全场景视觉通过结论。

保存同步完成后，后续议题是剩余场景光照和把独立导入完成的另38人接入现有双人面板；本轮不执行这些工作，不启动批量渲染。当前面板仍只有AF001/AM001，独立40人导入终态继续由[当前导入交接](../../../../../../00_engine/outputs/character_refresh_20261018_v1/CURRENT_IMPORT_HANDOFF_20261019.md)拥有，不能把导入完成等同运行接入或视觉接受。R17保持`in_progress`，唯一current父计划和生产Gate边界保持。

### 22.12 夜间完成导入的40人接入既有面板（2026-10-20）

用户新增授权：现在把昨晚已经完成导入的40人全部接入现有场景审查面板。本节替代§22.11当时“另38人留待后续”的下一步；此次只做接入，光照和渲染尚未开始。沿用`pair_scene_review_20261019_v1.py`与原面板启动路径、`pair_scene_review_20261019_v1`的点位／外观／草稿保存位置，人物目录改为完整40人；不迁移用户保存、不改源资产，不自动接受新人物的试穿、动画或视觉质量。

本节拥有`00_engine/scripts/unreal/night_character_review_v1.py`的私有审查配置和Run `%OUTPUT_ROOT%/night_character_panel_20261020_v1/`，输出归`OUT-WF60-SEQUENCE-TEMPLATE`、默认`unclassified`保护。helper直接读取`character_refresh_20261018_v1/user_edited_night_import_20261020_v1/delivery.json`的精确身份、Skeleton和部件路径，要求imports_completed／40人，不从旧两人交接猜测另38人来源。每人读取六主体件及全部独立睫毛：34人各2片、6人各4片，共332网格；BF001实际使用MeshesRecovery01中的已完成导入部件。独立导入终态与结构验收仍由其交接拥有，不改写导入证据。

既有`ue_pair_revision_runtime_20261019_v1.py`按每人的精确部件集合扩展绑定与睫毛数量，不再假定所有人只有两片；面板通过新helper提供完整40人配置，服装、发型、十色、表情、25动作、21镜头、横竖、21图／21有效点和独立排除沿用现有功能。相关旧装配实现与测试所有权仍见[角色Runtime §3.22](./CHARACTER_RUNTIME.md#322-用户修改后双人完整场景点位审查2026-10-19限定接入完成)。本轮按截止时间优先，未重跑测试或重建目录。[integration.json](../../../../../../00_engine/outputs/night_character_panel_20261020_v1/integration.json)为success=true：实际目录40人，AF002、AM002和BF001三次预览切换成功，六主体件与全部睫毛绑定通过，其中BF001的4片独立睫毛均绑定；[switches.json](../../../../../../00_engine/outputs/night_character_panel_20261020_v1/switches.json)记录精确部件和首次加载耗时约4.68／2.93／12.19秒。53份点位文件SHA保持，当前点位置、原选择与原预览均恢复，实际菜单矩阵25／21／2／1050。面板已以“新版40人”标题打开。此为三代表实机切换，不是40人逐个实机或全搭配／视觉通过。

`night_character_review_v1.bind_saved_selections`仅兼容外观配置来源中的`character_revision`变化，使原保存搭配继续可读；其余来源仍按原规则匹配，不重写保存文件。

当前接入完成，下一步由用户在同一面板审看40人；之后再讨论剩余场景光照与渲染计划。本轮不做光照调整或批量渲染，R17继续`in_progress`，唯一current父计划与生产Gate边界保持。

### 22.13 当前发色与RedSoul选择及女性赤脚反馈（2026-10-20）

用户报告已为所有当前场景加入PostProcessVolume并调好光照；这是用户提供的当前状态，尚未独立核对21张图是否全部保存，也没有新的正式渲染或全场景画面接受。本轮agent不把该报告写成已经逐图验证或渲染通过，40人接入完成的§22.12事实保持。

当前发色选择缩为7项：原色、黑色、金色、白色、红色、蓝色、粉色；机器ID分别为`original`、`black`、`gold`、`silver_white`、`red`、`blue`、`pink`，其中旧`silver_white`保留ID、显示名改为“白色”。男性`male.redsoul`的兜帽`male.redsoul.asset.b37f9c3bd4cf`退出必需部件，并开放发型选择。源资产不删除，冻结资产manifest不改写。

本节拥有`00_engine/scripts/unreal/appearance_selection_policy_v1.py`，由现用`production_workflow_20261017_v1/asset_inventory_formal_runtime_v1.py`在载入后的runtime副本上应用于衣柜、装配注册和发色目录；该共享正式loader既有路径／发布证据所有权保持，新选择不重写冻结来源。输出Run `%OUTPUT_ROOT%/appearance_choices_20261020_v1/`归本节、`OUT-WF60-SEQUENCE-TEMPLATE`，默认`unclassified`保护。[result.json](../../../../../../00_engine/outputs/appearance_choices_20261020_v1/result.json)为success=true：读回7种发色，RedSoul去兜帽并配发型成功，点位文件保持、原预览和选择恢复，agent未改场景光照；`redsoul_readback.json`保留限定真实预览及装配读回。此证据不代表所有人物／衣服／发型搭配都已视觉接受。

用户另报告女性不能赤脚。来源与实际UE读回均为原有13组鞋可选、4组鞋必需，面板选择和验证逻辑一致，未复现新的错误。4个必需鞋组为`female.pretty_dresses/pants`、`female.pretty_dresses/skirts`、`female.dress_collection/full_body`、`female.dress_collection/shirt_with_skirt`。当前`female.shirts_pants_a_i/default`属于原有13个可选鞋组，规则允许赤脚。[footwear_runtime.json](../../../../../../00_engine/outputs/appearance_choices_20261020_v1/footwear_runtime.json)记录各组运行选择规则；这不等于用户反馈已解决，也不把13组可赤脚改写为全部女性服装均可。当前等待用户指出仍不能赤脚的具体服装／组合，以明确复现位置，再决定是否需要修正规则；第三项继续pending，不能宣称修复。面板已重开并确认ready（PID29316，error=null，2026-10-20T15:06:16Z）。

本轮不扩大测试、不重建目录，不改源资产或生产Gate；正式渲染尚未启动。当前先处理上述女性鞋子具体反馈，再按用户需求讨论最终渲染计划；R17继续`in_progress`。

### 22.14 禁用发型组合的面板状态（2026-10-20）

用户要求确认禁用发型的服装在面板中确实不可选。现用组合只有`male.rugged_trendy`的第58个preset“Rugged & Trendy Men ProtectiveGear”禁用发型。库存中另有女性streetwear的WarriorCloak A/B/C和Windbreaker A/B/C六件历史禁用标记，但这些部件没有进入当前group／preset，不能把它们列为当前禁用组合。RedSoul继续沿用§22.13的新选择，允许发型。

问题是原运行装配已按规则隐藏禁用发型，面板控件却一直可选。本节拥有`00_engine/scripts/unreal/panel_hair_availability_v1.py`及`scene_site_review_panel_v1.py.render_appearance`的本次集成：依据当前family与实际选中／必需部件的`hair_interface`判断，禁用时将发型控件设为disabled并清空选择；允许时恢复readonly。换family、槽位或配饰均重新计算，未选择服装时允许发型。源服装、发型、点位和光照不改。

本节拥有Run `%OUTPUT_ROOT%/hair_selection_availability_20261020_v1/`，归`OUT-WF60-SEQUENCE-TEMPLATE`，默认`unclassified`保护。[checks.json](../../../../../../00_engine/outputs/hair_selection_availability_20261020_v1/checks.json)为success=true，324个实际目录case与运行解析器的禁用结果一致；[ui_checks.json](../../../../../../00_engine/outputs/hair_selection_availability_20261020_v1/ui_checks.json)的实际Tk三状态通过：Rugged禁用且hair_id=null，RedSoul允许，未选服装允许。此为控件和规则核对，不代替全人物／全搭配的画面接受；本轮仅重开面板，最终ready／error=null（PID15664，2026-10-20T15:13:12Z）；不改UE资产、点位或光照，也不扩大审计。

7种发色和RedSoul调整保持完成，40人接入保持。女性赤脚反馈仍待用户指出具体服装／组合，未宣布修复；用户调好全场景PPV和光照的报告保持其原验证边界，正式渲染仍未开始。R17继续`in_progress`，生产Gate不晋升。

### 22.15 用户确认后汇总与首批渲染准备（2026-10-20）

用户在阅读旧JSON允许赤足搭配清单后答复“那就没问题”，确认保留现有规则，不再要求具体问题服装。来源是`00_engine/assets/character_creator/wardrobe_registry_ue_v4_reviewed_pool_20261006_v2.json`；`formal_wardrobe_registry_v1.reviewed_pool_v4_expected`将旧组中“鞋不在required_slots、required_assets也不含shoes”的情况迁移为允许赤足，并非旧JSON逐组写有明确allow_barefoot标志。

允许的13组为：workout_color_outfits/default、summer_girl_four_colors/default、elise/default、jumpsuits_accessories/default、misaki/default、bikini_ruana/default、streetwear_collection/full_body及skirt_with_shirt、shirts_pants_a_i/default、off_shoulder_dresses/default、african_casual/full_body及pants_with_shirt及pants_with_bra_and_coat。均为female系列。4组必需鞋保持pretty_dresses/pants、pretty_dresses/skirts、dress_collection/full_body、dress_collection/shirt_with_skirt。此次仅确认并记录，不修改注册表、资产或保存搭配。

当前汇总：40人已导入并接入面板（§22.12）；21有效场景点位齐全、25动作／21镜头／横竖1050候选组合及既有排除保持（§22.11）；7发色、Red Soul去头罩并允许头发（§22.13）；当前男性第58套Rugged & Trendy禁止头发并禁用面板控件（§22.14）。旧1428排除数属于§22.11归档快照，后续继续以用户实时保存为准。

用户已报告各场景添加后期处理体积并调好亮度。本次没有操作UE或独立验证所有关卡已保存。下一步不再重复调光，而是快速衔接用户设置与首批渲染：目前`ue_production_site_runtime_v1`预览仍调用`apply_camera_exposure`读取点位exposure_compensation，前述“相机统一沿用关卡曝光”仅是讨论方案，尚未实施。先处理必要继承／覆盖关系并简短确认，再按确定的首批组合、数量、规格和目录出样片。正式批量渲染未启动，未将40人或全组合视觉验收自动晋升。R17继续in_progress。


### 22.16 旧发色拍摄点恢复与后期处理体积核对（2026-10-20）

用户暂停曝光继承接入，优先修复已移除发色导致保存点无法加载，并检查遗漏后期处理的场景。`night_character_review_v1.bind_saved_selections`在现用私有审查contract中将旧purple／teal／orange仅在内存中回退original；其余7色保持，未知色仍报错，来源与保存摘要检查继续有效。不改写旧外观、点位、坐标、排除组合，不重新开放旧颜色。此脚本既有生产所有权沿用§22.12，本节拥有此次兼容变更及`tests/test_night_character_saved_appearance_v1.py`回归。

12项定向回归通过。34份现用保存外观均可加载，4份旧色回退；其中关联现用点位为日式部落/1、沙丘/1、未来都市/1。UE已热更新共享contract，三个关联外观在UE中加载通过，当前未来都市/1真实load_site成功，保存点位及外观文件哈希不变。无需迁移或重置人工排除。

Run `%OUTPUT_ROOT%/saved_hair_postprocess_20261020_v1/`由本节产生，归`OUT-WF60-SEQUENCE-TEMPLATE`，默认unclassified保护；`hair_result.json`记录实机恢复，`volumes.json`记录21张现用World的只读体积清单，`current.json`记录起始场景。该run的诊断／同步脚本仅服务本次维护，不是正式渲染入口。

21个场景均读到后期处理体积。19个场景存在启用、无限范围、混合权重1且覆盖为手动曝光的体积。两处例外：傍晚公路（用户称夜间公路，`/Game/Scenes/Evening_Highway/Maps/demo_level`）只有自动曝光基本模式，补偿约0.433；未来都市（`/Game/Scenes/FuturisticMetaCity/Maps/VirtualMetaCity`）只有自动曝光直方图模式，计量模式未勾选覆盖，补偿0。不能仅凭体积名称确定是否用户添加；这两处需用户确认是否漏调，而非断言完全没有后期处理。只读检查加载World对象，没有切换当前编辑关卡、写关卡、改灯光或替用户设置曝光；未作所有点位最终画面曝光验收。

曝光继承的前一任务保持暂停：相关源码已初改、两项定向测试曾通过，但尚未完成实机接入核对，不记作已交付；暂停前pytest另有3个无关测试因临时目录权限错误未运行。正式渲染未开始。下一步先由用户补看公路／未来都市，待继续指示再完成曝光继承，然后确定首批渲染安排。R17仍in_progress。


### 22.17 当前会话纹理模糊恢复（2026-10-21）

用户确认已补正公路和未来都市曝光。当前香港街道预览模糊已定位为纹理池预算1000MB，而Non-Streaming Mips约6042.89MB，剩余流送池为0；执行未引用对象回收并将当前编辑器会话r.Streaming.PoolSize设为7000。读回剩余池907.49MB，Current/Target均243.77MB，当前视图需求已满足；12GB RTX4080 Laptop整体显存约9582/12282MiB。只恢复当前会话，不改关卡、材质、曝光或持久项目配置，不代表全场景／正式渲染验收。面板已重新打开，画面由用户复看。正式渲染曝光继承仍按先前指示暂停；后续继续时应一并处理开拍前纹理预热，尚未实现。

本节拥有Run `%OUTPUT_ROOT%/texture_streaming_recovery_20261021_v1/`，归OUT-WF60-SEQUENCE-TEMPLATE，默认unclassified保护。before.json、applied.json和streaming_stats.txt为诊断、会话操作及读回证据；本run脚本仅为此次会话维护工具。未做代码或资产修改，不新增测试。


### 22.18 当前进度统计与接续边界（2026-10-21）

本次仅同步记录，不操作UE。当前精确统计由`%OUTPUT_ROOT%/review_progress_sync_20261021_v1/checkpoint.json`拥有：21有效场景各1个保存用户点，19点有单独外观ID；游乐园和中式建筑两点仍是继承点，没有固定外观ID，不能据此认定二者已有独立保存的40人外观搭配，正式渲染计划需明确选择。25动作×21镜头×2画幅=每点1050候选。已保存排除原始1484项，扣除被移除动作MOTION_CAND_007的56项后有效1428项（九龙810、地铁618），与先前快照一致。保留原排除行、点位坐标、外观ID和源文件SHA，未改源文件，不把未保存UI草稿计入，也不预先确定最终批渲染组合。

40人、7发色、Red Soul／Rugged发型规则、赤足规则确认、旧色兼容沿用§22.12–§22.16；用户已确认补正公路和未来都市曝光，§22.16的两处待补为补正前事实，不再是当前待办。§22.17纹理恢复只对当时会话／当前画面有数值证据，未修改持久配置，未声明全场景画面已验收。

暂停中的曝光接入源码边界：`00_engine/scripts/unreal/level_exposure_policy_v1.py`（experimental）清除相机曝光覆盖；`ue_primary_saved_site_review_v1.apply_camera_exposure`和`ue_primary_scene_samples_v1.exposure`调用同一helper；`ue_production_trial_render_v1.py`记录策略并拒用不含当前策略的旧准备收据。源码已初改，两项定向测试曾通过；UE字段兼容、当前缓存接入、实际新准备与正式渲染曝光均待核对，不作为已交付功能。本节拥有helper及上述本次修改；测试文件`test_primary_scene_samples_v1.py`与`test_ue_production_trial_render_v1.py`保持原测试范围。Run `%OUTPUT_ROOT%/level_exposure_inheritance_20261020_v1/`仅有未完成任务材料，不能据其存在认定完成。

尚未实现：正式渲染的纹理预热／需求满足等待，以及当前7000MB会话设置的持久化或按设备预算配置。首批组合、数量、规格、输出目录待定；当前版本正式批量渲染未启动。已有20261017四片试渲染是历史技术样片，不与此状态矛盾。

本节拥有`%OUTPUT_ROOT%/review_progress_sync_20261021_v1/`的统计快照与定向文档一致性记录，归OUT-WF60-SEQUENCE-TEMPLATE；保留unclassified保护，不触发清理。与§22.16、§22.17、暂停曝光Run一并补齐输出所有权；本次只检查涉及的状态、计划、机器状态、证据路径和脚本目录归属，不扩大为全库测试或全场景重审。

本次同步结果：Script Catalog与Output Inventory已重建；`verification.json`的12项定向一致性核对通过，包括源点文件哈希保持、统计一致、唯一当前状态／R17段落、暂停边界、输出及脚本归属和曝光helper的experimental生命周期。未运行全库测试或全树文档审计，未操作UE、改关卡或启动渲染。历史BATCH-001仍为既有冻结参考，没有创建新的活动生产批次。

### 22.19 恢复曝光继承与正式开拍前纹理预热（2026-10-21）

用户已恢复此前未完成的任务。本节替代§22.16–§22.18中“曝光接入暂停、纹理预热尚未实现”的当前待办；旧段保留当时状态。当前曝光helper与现用预览已在UE验证，MRQ预热／本机分离预算已接入，香港街道1024×576、3帧静态管线小样输出与现场恢复通过。小样复制当前预览的场景和人物，不是40人重新正式装配或动作播放接受，也不是全场景渲染验收。R17继续in_progress，不创建生产批次或晋升生产Gate。

本节拥有`00_engine/scripts/unreal/level_exposure_policy_v1.py`及`ue_primary_saved_site_review_v1.apply_camera_exposure`、`ue_primary_scene_samples_v1.exposure`的共用接入。helper清除15项相机曝光覆盖，让关卡保存的后期处理体积决定曝光；旧点位的曝光补偿值不再重新覆盖相机。非曝光的Bloom、视场角和后期混合权重保留，关卡后期体积、灯光及保存点文件不改。`ue_production_trial_render_v1.py`在新准备回执记录`inherit_saved_level_exposure_v1`，`require_level_exposure`拒绝不含该策略的旧准备回执，需重新准备当前拍摄任务，不能直接复用旧相机。

[exposure_result.json](../../../../../../00_engine/outputs/render_readiness_20261021_v1/exposure_result.json)为success=true，UE版本5.8.1：香港街道真实临时CameraComponent的15项覆盖全部清除，Bloom／FOV／混合权重保持；现用预览缓存和真实相机已热更新，原预览、点位、外观及保存文件保持，关卡后期体积读回不变。这是共用正式helper和当前预览的限定字段验证，不等于所有关卡或最终媒体亮度已接受。曝光helper由此前experimental更新为validated_pilot，仍不是production脚本。

本节拥有`00_engine/scripts/unreal/mrq_streaming_warmup_v1.py`及`tests/test_mrq_streaming_warmup_v1.py`，集成点是`ue_primary_scene_samples_v1.sample_renderer`。`ue_production_trial_render_v1.renderer`沿用该包装；在保存submitted回执、调用executor之前，为每个job设置并逐项读回：`engine_warm_up_count=120`、`render_warm_up_count=32`、`render_warm_up_frames=True`、`use_camera_cut_for_warm_up=False`。回执新增`render_contract.streaming_warmup`并将顶层旧16／8计数替换为实际120／32；任何读回失败都在提交前报错。`tests/test_primary_scene_samples_v1.py`拥有提交顺序、失败阻止执行及原资源设置保持的集成回归。

依据本地UE5.8源码`MovieRenderPipelineCore/Public/MoviePipelineAntiAliasingSetting.h`、`Private/MoviePipelineTiming.cpp`和`Private/MoviePipelineRendering.cpp`：上述设置让引擎预热tick也提交GPU视图，最终tick执行渲染预热采样；序列保持在首个输出帧，不推进或增加身体／相机轨迹，不改变输出帧区间、分辨率或空间／时间AA采样数。已有显式camera-cut preroll会被helper拒绝，不能静默替换。120个tick提供有限预热机会，32次渲染采样并不等于额外32次流送tick，更不保证全部贴图已驻留；后续镜头新显露区域与不足的预算仍需样片检查。

原`sample_scene_resources`和草地策略保留：texture_streaming为NONE（不覆盖现用流送方式），`flush_streaming_managers=False`，不强制全纹理驻留、LOD0、Cinematic最大质量或草地全量同步。UE5.8的GameOverride流送flush直接调用C++ `BlockTillAllRequestsFinished()`，默认TimeLimit=0且该MRQ设置未公开有界超时；本次没有开启无界等待，也没有声称实现了“需求全部满足后才开拍”的完成门。

本机配置由`mrq_streaming_warmup_v1.pool_profile(pool_size_mb=None, profile_path=None, *, for_render=False)`统一读取。默认文件为[local_render_profile_v1/profile.json](../../../../../../00_engine/outputs/local_render_profile_v1/profile.json)，schema=`local_texture_streaming_profile_v1`，要求machine_name与本机一致、所选预算为1–131072的整数。当前RTX4080 Laptop／12GB本机采用编辑器`pool_size_mb=7000`、仅MRQ的`mrq_pool_size_mb=10240`，不能通用于其他显存设备。`for_render=True`优先读取MRQ预算；旧profile缺该字段时兼容原pool_size_mb，缺文件则继承会话预算并在回执标明，错误设备／格式在提交前报错。`apply(u, queue, *, pool_size_mb=None, profile_path=None)`自动使用渲染预算，也允许明确传入预算；通过MRQ `MoviePipelineConsoleVariableSetting.add_or_update_console_variable`和启用状态API设置`r.Streaming.PoolSize`，再读取`get_console_variables()`核对。按本地`MovieRenderPipelineSettings`源码，正常pipeline teardown恢复先前CVar值；本次另由结束读回确认实际恢复7000，而非仅根据配置推断恢复。

`pair_scene_review_20261019_v1.ensure_local_texture_budget`由worker入口调用，首次编辑器会话按同一profile设置并读回本机纹理预算，使用私有会话缓存，后续不会每次请求重设；这是本机审查启动恢复，MRQ仍使用独立任务级覆盖。profile变更在新会话生效，既有会话需受控刷新缓存；不把7000写入跨设备项目默认配置。该入口整体既有角色Runtime所有权保持，本节只拥有本次纹理预算接入。

实现初轮15项定向测试通过，随后补入编辑器／MRQ预算分离与旧profile兼容回归。root本轮运行`tests/test_mrq_streaming_warmup_v1.py`和`tests/test_primary_scene_samples_v1.py`，共83通过、1失败：失败为既有`test_gallery_keeps_pending_cards_and_does_not_claim_all1260_visual_acceptance`的gallery中文断言，与本次预热／预算逻辑无关，保留而未扩大修改；新helper边界测试全部通过，另两项曝光／旧准备回执保护测试通过。此次文档同步不再运行广泛测试或全树审计。预热helper更新为validated_pilot，仅覆盖本次香港街道静态小样，不把固定预热次数晋升为全纹理驻留或跨设备视觉保证。

本节拥有`%OUTPUT_ROOT%/render_readiness_20261021_v1/`与`%OUTPUT_ROOT%/local_render_profile_v1/`两个scope，归`OUT-WF60-SEQUENCE-TEMPLATE`、WF-60，默认unclassified保护；本次只登记输出所有权，不新增清理或保留晋升。前者含曝光验证、源场景／预览快照、初轮模糊失败及预算诊断、独立MRQ小样片与终态／媒体核对；后者是当前机器专用配置输入。初轮512×288和1024×576在7000预算下衣服格纹严重丢失，不能以executor成功当作画面通过。启动时另曾遇无关BP_TestPlayer编译提示，由root处理；此提示与后来的贴图模糊原因分开记录。

纹理诊断的直接根因是有效流送预算归零：7000预算下，Non-Streaming Mips从约6043MB升至9372.93MB，可流送池从约920MB降为0，衣服Diffuse的current从2048降为64而wanted仍为2048，说明视图需求存在但被预算压低。UE5.8 `AsyncTextureStreaming.cpp`从pool扣除非流送资源及安全余量后钳为0，再降低mip。新增非流送占用的具体来源尚未分类，不能将差额断言为MRQ RenderTarget；`RHICoreStats.cpp`对RenderTarget／Depth／UAV另行核算。没有通过关闭流送、强制全库最高贴图或无限提高pool解决。

最终[readiness_budget10240_v1.json](../../../../../../00_engine/outputs/render_readiness_20261021_v1/render_receipts/readiness_budget10240_v1.json)为completed／success=true、errors为空，记录3帧、1024×576、120／32预热和10240MB任务级预算，global_queue_unchanged及input_files_unchanged均true。root观察第0／2帧衣服格纹、皮肤及背景清晰恢复；这是首末帧限定观察，非连续全动作审查。[finish_probe.json](../../../../../../00_engine/outputs/render_readiness_20261021_v1/finish_probe.json)确认原场景、点位、外观、预览、PPV均保持，结束pool_after=7000。[gpu_budget10240.json](../../../../../../00_engine/outputs/render_readiness_20261021_v1/gpu_budget10240.json)含35次离散GPU采样，样本内最大used为10015MiB、最低free为1981MiB；不称连续峰值或其他场景／分辨率的显存保证。10240是本机MRQ预算上限，不是立即预分配10GiB，其他设备和更重场景仍须按实际预算验证。

该小样由当前预览的独立场景副本和静止相机产生，证明本次曝光／预热／预算／恢复管线可执行；未重新构建正式40人装配、验证身体／表情／相机动作或首批生产组合。最终媒体核对由[media_validation.json](../../../../../../00_engine/outputs/render_readiness_20261021_v1/media_validation.json)集中拥有，状态为bounded_static_smoke_passed，三帧解码尺寸与SHA已登记；[HANDOFF.md](../../../../../../00_engine/outputs/render_readiness_20261021_v1/HANDOFF.md)提供后续准确复用入口。渲染参数及数据矩阵由用户新建分支会话继续规划，原会话保留UE资产／场景／面板维护；不以本次静态小样替代正式任务准备与视觉确认。


### 22.20 男性 Rugged & Trendy 退出拍摄选择（2026-10-21）

用户决定将男性 Rugged & Trendy（male.rugged_trendy，原第58套 Men Protective Gear）从当前拍摄选择中移除。共用 appearance_selection_policy_v1 同时过滤正式运行注册表、服装菜单与预设，源资产和冻结清单保留。实机刷新后男性25个服装系列／72个预设，男女全部剩余预设的禁用发型项为0；已保存外观未发现该系列引用。当前点位、预览与点位文件保持，审查面板已重新打开。此项覆盖此前“Rugged保留但禁用发型”的现用规则；历史记录及分支数据探索快照不回写，后续枚举须读取更新后的现用目录。

实现沿用本节已有所有者 `00_engine/scripts/unreal/appearance_selection_policy_v1.py`，新增 `RETIRED_FAMILIES` 及 `remove_retired_wardrobe(registry, wardrobe)`，在共用 `apply` 内调用；不会给所有服装强制改写发型兼容规则。离线现用目录和真实UE两处读回一致，不扩展视觉／全库测试。缓存须刷新后生效；本次重建私有worker并恢复原点位和预览，未保存场景。执行记录沿用已有appearance_choices输出scope，详见[移除回执](../../../../../../00_engine/outputs/appearance_choices_20261020_v1/retire_rugged_result_20261021.json)。尚不代表分支已重新计算其历史候选数据规模。
