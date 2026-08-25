# Character Creator 角色工厂当前状态

> 文档角色：`current_status_snapshot`
> 状态：`current`
> 适用阶段：`global`
> 权威范围：当前可用能力、第一批数据基线、未完成项和唯一下一步
> 上级入口：[`CHARACTER_FACTORY_MASTER_SPEC.md`](./CHARACTER_FACTORY_MASTER_SPEC.md)
> 上游：机器配置、验证报告、人工验收与 [2026-08-19 周报](./history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md)
> 下游：[`FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md`](./planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md) 与各 Workflow
> 最近核验：2026-08-24
> 更新方式：覆盖更新；完成事件只追加到 [`MILESTONE_LOG.md`](./history/MILESTONE_LOG.md)

## 1. 当前结论

角色工厂已经有可用的 CC 角色基础、服装规则、首批 8 个冻结身份、32 个已保存并导出的 FullReference Look、12 个已导出并锁定五秒窗口的 Motion FBX，以及 Happy/Angry/Sad 的 UE 轻动态表情实现。完整 `4 身份 × 4 服装 × 2 性别` 矩阵已通过 CC 32/32 合并审计和 UE 5.8.1 + Auto Setup 2.03 的 32/32 导入门禁；所有 Skeletal Mesh 按性别统一引用女性/男性各一套规范 Skeleton。原始 12 个 Motion 已通过 Skeleton、五秒窗口、轨道与静态运行时门禁；2026-08-24 冻结的生产动作池删除 F04 Audience 09 与 M03 Audience 12，当前实际生产为每性别 5 条、共 10 条。

Day 02 的技术工作已经收口，不再受 UE 恢复包窗口阻塞。用户已检查六个动态案例，确认三种表情差异可见但较轻微，并接受其用于第一批数据；人工决定记录为 `day2_dynamic_visual_review_20260822_v1.json`。Day 02 的人物、动画和面部表情门禁现已全部关闭。

WF-08 已完成本地参数化代表矩阵：TokyoStylized 场景、安全角色锚点和 `near/far/high/side` 四台静态相机通过几何审计；`firstweek` 固定为 30 fps、600 帧和四个顺序 Camera Cut。历史 12 动作与 36 条动作/表情派生 AnimSequence 已通过轨道审计；当前生产池只使用 10 动作与对应 30 条派生资产，有效短动作 F03/M02 已补齐到精确 150 帧。32-Look 矩阵按 2560×1440、30 fps、150 帧输出 4,800 张 PNG 与 32 个 H.264 MP4，32/32 通过并覆盖全部 Look、10 动作、四相机和三表情。首次批处理暴露出替换 Look 后整段 T-pose，根因是 CC Blueprint 默认动画模式不一致；构建器现对男女全部 Section 强制 `force_custom_mode=true`，执行器在 MRQ 前硬校验 pose-driver contract。既有极端动作服装穿模仍是视觉兼容性警告，不能因机器门禁通过而忽略。

当前唯一活动目标是 [第一批多轮编辑数据 Sprint](./planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md)：在服务器完整渲染 `32 Looks × 5 同性动作 × 4 相机 × 1 Happy 表情 = 640` 个唯一节点，并生成精确 4,000 条 3–5 轮编辑链。节点按 female/male 分为两个各 320 节点的兼容域，域内必须连通；链采用 `progressive_shortest/freeform_walk` 50/50。Angry/Sad 只保留为历史候选，不进入本批正式节点或编辑轴。

2026-08-24 已完成正式配置图与模型文本层：真实源清单、两个兼容域、640 节点、8,320 条同域原子边、4,000 条编辑链、640 个 render job 和 15,000 个双语 `video_in + prompt + video_out` 回合已生成，报告均为 `passed`。四个编辑轴各占 25%，640/640 节点均被链引用；模型文本中内部 ID 泄漏为 0。男女各一条 UE 候选链随后完成本地 smoke：11 次路径引用去重为 9 个视频，9/9 为 150 帧、1440p30、Happy，pose-driver、temporal-motion 和视频哈希全部通过；assistant 预检无 T-pose、白块或新严重服装故障，用户已于 2026-08-24 接受代表链。该结论尚未关闭正式 640 节点媒体、GT/sidecar 和服务器发布门禁。

本轮不等待十体型、全部动画、Headshot 身份迁移、三发型、道具或通用模块化换装完成。

## 2. 第一批冻结基线

| 维度 | 本轮值 | 当前状态 |
| --- | --- | --- |
| BodyFit | 女性 `F02_Average`、男性 `M02_Average` | 已有 CC/UE 参考证据 |
| 身份 | 每性别 4 个，共 8 个 | `F_ID01..04`、`M_ID01..04` 已冻结、保存并有哈希证据 |
| 服装 | 每性别 4 套，共 8 套；完整 32 Look | CC Bundle 合并审计 32/32、UE 导入门禁 32/32；女性 O04 使用 `CasualJacket_C` |
| 身体动作 | 当前 10 个：女性 5 条、男性 5 条；每个 Look 使用 5 条同性动作 | 12 条源曾全部通过门禁；`cc_first_batch_action_pool_20260824_v1.json` 排除 F04/M03。只有 F02 Catch Breath 使用批准的 InPlace，其余 9 条保留源位移 |
| 表情 | 正式节点固定 Happy；Happy/Angry/Sad 候选均有 F02/M02 3 秒可循环轻动态 Morph clip | 30 条三表情派生资产保留为历史技术候选；正式队列只引用 10 条动作 × Happy，不生成 `E11` |
| 场景 | `/Game/DataMake/Scenes/TokyoStylized/L_DM_TokyoStylized`、1 个安全锚点、固定灯光 | 场景与锚点几何门禁通过；32-Look 本地代表矩阵通过，既有极端 Look/动作穿模继续作为兼容性警告 |
| 相机 | `near/far/high/side` 四台静态相机 | `firstweek` 的四段顺序 Camera Cut 通过结构和取景审计；首批节点按单镜头 5 秒媒体输出，20 秒序列只作四镜头审核容器 |
| 节点 | 服务器正式预算 `32 Looks × 5 Actions × 4 Cameras × Happy = 640` | 正式源与 640 个唯一节点已生成；两个兼容域各 320 且各自连通，媒体仍待渲染 |
| 链 | 3–5 轮，精确 4,000；`progressive_shortest/freeform_walk` 各 2,000 | 已按精确域/策略/长度配额生成；四轴各 25%，五事实标签重算通过，640/640 节点被引用 |
| 文本 | `zh-CN/en` 双语；每轮同时提供 history-aware `dialogue` 与直接目标 `standalone` | 4,000 dialogs / 15,000 turns 已通过原子性、轴配额、双语、确定性和零内部 ID 泄漏门禁；E1 当前由配对目标视频精确 grounding |
| 输出 | 节点媒体、sidecar、哈希、配置图、链和报告 | 本地 32/32 可续跑矩阵、PNG→H.264 和媒体门禁已通过；正式 GT/sidecar、服务器批队列、重试和交付门禁待实现 |
| 服务器 | 服务器 checkout 仍是早于本地 v4 冻结与 2026-08-21 契约修复的快照；Linux/NVIDIA + UE 5.8 Editor 离屏运行 | `--environment-only` 已在本地实现并验证参数分支；代码同步、二进制资产包、项目 smoke 与 10 节点基准待完成 |

完整冻结范围、日程和降级顺序只在 Sprint 文档维护。

## 3. 已验证且本轮可复用

| 能力 | 成熟度 | 可复用边界 |
| --- | --- | --- |
| 成人 BodyFit | `production` | 10 个源项目有 hash 锁；本轮只使用 F02/M02 |
| Face V3 | `production` | 20 seed、17 个生产主原型、200 条配方；本轮身份仍从该稳定池选择 |
| 面部外观池 | `production` | 21 皮肤、12 眼球材质、13 眉毛、9 睫毛、2 牙齿、5 胡须、58 发型 |
| CC Bridge | `validated_pilot` | 受控离线文件队列可工作；CC 必须由用户按离线许可方式启动 |
| 完整角色装配 | `first_batch_32_export_validated` | 8 身份、32 Look 已确定性装配；CC 合并审计 32/32、失败 0、partial 目录 0 |
| 服装规则 | `validated_pilot` | 41 family、53 逻辑组；极端体型静态 159/159、动作压力 53/53，用户已接受/抽查 |
| P0 动作 | `validated_pilot` | 16 条已完成 CC 动态检查和用户视觉接受；4 条代表动作完成 UE Pilot |
| 首批生产动作 | `first_batch_10_frozen` | 原始 12/12 已验证；当前女性 5、男性 5，F04/M03 被生产池排除；F02 为唯一 InPlace 例外 |
| 首批表情候选 | `validated_pilot` | F02/M02 共 6 个 UE 曲线资产；三表情动态案例通过，但首批正式节点只使用 Happy |
| 精确五秒动作补齐 | `validated_pilot` | 当前有效短动作 F03/M02 以端点保持补齐为 150 帧；F04/M03 的旧派生只保留历史证据，不进入生产池 |
| 首批动作/表情组合 | `validated_pilot` | 历史 36/36、当前候选 10 动作 × 3 表情均通过；正式 640 节点只引用 10 条 Happy 组合 |
| 本地 MRQ 代表矩阵 | `first_batch_32_local_matrix_validated` | 32/32 Look、4,800 PNG、32 MP4；每例 2560×1440、30 fps、150 帧、5 秒，10 动作/4 相机/3 表情全覆盖，pose-driver 与五帧 temporal-motion contract、OpenCV 媒体复核均通过；服装兼容性仍需逐例视觉判断 |
| 防 T-pose 渲染契约 | `validated_and_enforced` | 男女 CC5 动画 Section 全部强制 Custom Mode；执行器要求四段 Section、原生 Actor binding、目标 Actor 和 `force_custom_mode=true`，并在渲染后检查五个时间采样帧；不合格案例不继续也不复用旧结果 |
| 第一批配置图生成器 | `first_batch_graph_machine_gate_passed` | 正式源、640 nodes、8,320 atomic edges、4,000 chains、640 render jobs 已生成；图测试通过，代表链 UE 视觉子门禁已关闭，仍需正式媒体执行器 |
| 第一批模型文本层 | `first_batch_prompt_layer_machine_gate_passed` | 4,000 dialogs、15,000 turns、E1/E2/E3/E7 各 3,750；双语完整、原子性和字节级确定性通过，内部 ID 泄漏 0；E1 暂为 `paired_target_video/class_only` |
| 代表编辑链本地渲染 | `representative_chain_visual_accepted` | 男女两链、11 次路径引用、9 个唯一视频全部通过；用户决定文件 `user_visual_review_20260824_v1.json=accepted` |
| CC→UE FullReference | `first_batch_32_import_validated` | 32/32 Look 的源哈希、Mesh、Morph、HQ 材质、Auto Setup、Rig 和同性交付 Skeleton 复用门禁全部通过；聚合报告为 `OUTPUT_ROOT\unreal_character_import\first_batch_full_reference_expansion_20260822_v2\aggregate_import_gate.json` |
| 首批动态皱纹材质 | `first_batch_32_wrinkle_texture_fixed` | 32/32 Look 的 13 个头部皱纹纹理槽已从 Auto Setup 占位图修复为有效 CC 标准贴图；Happy/Angry/Sad 和原始头部材质同帧 A/B 均无白块 |
| UE 身体/面部分层 | `validated_pilot` | F02/M02 的 4 body × 4 direct-Morph face 为 16/16、24/24 图 |
| UE 模块化 M02 | `validated_pilot` | 20 组件、19 follower、Morph 广播可用，但不作为本轮通用换装前提 |
| UE Elder Morph | `validated_pilot` | M02 Pilot 可连续变化；本轮不使用年龄编辑 |
| 可视化门户 | `production_utility` | 可登记、筛选、放大和审查当前截图/结果分支 |

FullReference 直接 Morph 路线必须禁用角色组件的 Post Process Blueprint，否则会与 RL 求值重复并产生眼部伪影；当前 Pilot 不声明 eye-bone gaze。

首批 Bundle 的 `Wrinkle.Textures` 为空，Auto Setup 曾把动态皱纹层绑定到白色/灰色占位图，导致表情增强时额头和面颊出现白块。`ue_patch_first_batch_head_wrinkle_textures.py` 已修复 32/32；任何重导入后必须重新执行该门禁。

## 4. 本轮尚未完成

1. 把本地 32 例执行器提升为正式节点执行器：补齐 GT/sidecar、按 node_id 重试、媒体/配置哈希和交付验证。
2. 服务器先完成环境预检；项目与二进制资产同步后，完成项目 smoke 和 10 节点基准，随后完整渲染 640 节点。
3. 渲染后把 `turns.jsonl/dialogs.jsonl` 的节点 URI 解析到权威媒体，并执行 15,000 回合零悬空引用门禁。
4. 在正式节点抽检中继续记录头发/头部服装相交和极端动作服装穿模；这些是兼容性限制，不回退已经通过的 32 例机器门禁。

这些项目的顺序和退出条件见 [Sprint](./planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md)，不能从旧实验日志推断。

## 5. 当前已知限制

- 头发与头巾、兜帽、高领服装可能相交；本轮 32 Look 沿用已选 8 套服装，不在本周建设通用兼容系统。
- 服装按烘焙 FullReference Look 导出，不支持 UE 内任意单件组合。
- Headshot 10 人候选保持冻结且 0 个生产启用；本轮继续使用 Face V3。
- 69 条 P0 剩余动作的离线人工决定仍可继续，但不阻塞本轮 10 动作生产池。
- 原始 12 动作的 UE 导入与门禁已完成；当前 10 动作、30 条候选表情组合已进入参数化 Sequence 并完成 32-Look 代表矩阵。正式 640 节点只使用其中 Happy 组合，scene/camera/Blueprint ID 已冻结；仍需 sidecar、正式节点执行器和服务器模板。
- 首批动作旧 v1 自动导出曾被软件内容许可对话框阻断并已失败收口；受阻动作随后被替换，当前人工导出的 v4 Motion FBX 已 12/12 通过文件哈希门禁，不再重试旧作业。
- CC 的额外 `textures\` 目录是否必需必须按 JSON 实际引用判定；布料权重图和动态皱纹贴图都可能位于其中。首批 JSON 的皱纹路径为空曾通过旧结构门禁但造成 UE 白块，因此后续 Bundle 必须同时检查 `Wrinkle.Textures`，不能只检查服装权重图。
- `WF-08` 的第一批本地代表矩阵已通过：动作/表情/四镜头结构和 32-Look 参数化装配贯通；正式服务器节点仍需视觉抽检。`WF-09` 为 `in_progress`：本地 32/32 可续跑矩阵已验证，正式数据集封装尚未完成。
- CC 未知弹窗、Undo 警告、private memory 达到 24 GB、UE 资产/哈希漂移均要求停止，不允许自动猜测。
- 新 FullReference + Auto Setup 导入在同一 UE 进程内最多执行 3 个 Look，随后正常关闭并重启 UE。2026-08-22 的长批次在完成 9 个新增 Look 后使 UE private commit 增长到约 84–90 GB 并崩溃；失败的 `M_ID02_O01` 在干净重启后通过，证明它不是坏资产。交互导入不得使用 `--continue-on-error` 掩盖编辑器退出。

## 6. 关键入口

| 需求 | 权威入口 |
| --- | --- |
| 本周做什么 | [第一批数据 Sprint](./planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md) |
| 配置图字段 | [Config Graph Schema V1](../../schema/CONFIG_GRAPH_SCHEMA_V1.md) |
| 3–5 轮链如何采样 | [Multi-round Sampling V1](../../sampling/MULTI_ROUND_CHAIN_SAMPLING_V1.md) |
| prompt 字段与生成规则 | [Multi-round Video Edit Text Schema V1](../../schema/MULTI_ROUND_VIDEO_EDIT_TEXT_SCHEMA_V1.md) |
| 服务器怎么预检和渲染 | [Server Runbook](../../../implementation/FIRST_BATCH_SERVER_RUNBOOK.md) / [Executable Preflight](../../../implementation/FIRST_BATCH_SERVER_PREFLIGHT.sh) |
| 当前代码/JSON/UE 资产 | [Implementation Index](./reference/IMPLEMENTATION_INDEX.md) |
| 本地 32 视频怎么一键复现 | [WF-09 Render Dataset Package](./workflow/WF-09-RENDER-DATASET-PACKAGE.md) |
| 后续而非本周工作 | [Roadmap](./planning/ROADMAP.md) / [Backlog](./planning/BACKLOG.md) |
| 已完成过程与证据 | [Milestone](./history/MILESTONE_LOG.md) / [周报](./history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md) |

## 7. 唯一下一步

继续 [`WF-09`](./workflow/WF-09-RENDER-DATASET-PACKAGE.md)：把现有执行器提升为按 `render_jobs.jsonl` 驱动的正式节点执行器，补齐 GT/sidecar、node_id 重试、媒体/配置哈希和文本回合媒体解析，再执行服务器预检、项目 smoke 与 10 节点性能基准。
