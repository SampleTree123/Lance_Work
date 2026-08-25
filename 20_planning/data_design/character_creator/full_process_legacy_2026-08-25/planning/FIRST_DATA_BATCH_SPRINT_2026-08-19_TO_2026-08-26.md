# 第一批多轮编辑数据 Sprint

> 文档角色：`active_sprint_plan`
> 状态：`current`
> 适用阶段：`WF-07..WF-09`
> 权威范围：2026-08-19 至 2026-08-26 第一批数据的冻结范围、交付定义、执行顺序、责任和降级规则
> 上级入口：[`README.md`](./README.md)
> 上游：[`../CURRENT_STATUS.md`](../CURRENT_STATUS.md)、F02/M02 P0 UE Runtime Pilot 与用户确认的本轮范围
> 下游：[`CONFIG_GRAPH_SCHEMA_V1.md`](../../../schema/CONFIG_GRAPH_SCHEMA_V1.md)、[`MULTI_ROUND_CHAIN_SAMPLING_V1.md`](../../../sampling/MULTI_ROUND_CHAIN_SAMPLING_V1.md)、[`MULTI_ROUND_VIDEO_EDIT_TEXT_SCHEMA_V1.md`](../../../schema/MULTI_ROUND_VIDEO_EDIT_TEXT_SCHEMA_V1.md)、[`FIRST_BATCH_SERVER_RUNBOOK.md`](../../../../implementation/FIRST_BATCH_SERVER_RUNBOOK.md)、`WF-08` 与 `WF-09`
> 最近核验：2026-08-24

## 1. 交付定义

本 Sprint 的目标是在一周内交付第一批可检查、可追溯的多轮编辑样例，而不是完成角色工厂的全部长期功能。

| 项目 | 本轮目标 |
| --- | --- |
| 多轮编辑链 | 精确 `4,000` 条；不以少于配额的链集作为正式交付 |
| 每条链长度 | `3..5` 次原子编辑 |
| 独立渲染节点 | 正式 `640` 个；服务器完整渲染，每个节点只渲染一次 |
| 视频 | 默认 `5 s × 30 fps × 2560×1440`，服务器基准后允许按第 9 节降级 |
| 角色 | 女性 F02、男性 M02；每个性别 4 个身份、4 套服装 |
| 表演 | 10 个无道具或低依赖生产动作：女性 5 条、男性 5 条；每个 Look 使用 5 条同性兼容动作；正式节点统一使用 Happy 轻动态表情 |
| 场景 | 1 个固定场景、1 个安全角色锚点、固定灯光 |
| 镜头 | 正式使用 `near/far/high/side` 四台已验证静态相机 |
| 数据 | 配置、节点、原子边、链、双语 prompt 回合、渲染作业、媒体、sidecar、哈希和失败清单 |

核心原则：`4,000` 条链是从可复用节点图中采样的路径，不是独立渲染 `12,000..20,000` 个视频。链目录只引用已有节点媒体；不得为了每条链重复复制或重渲染同一节点。

## 2. 冻结范围

### 2.1 本轮包含

| 编辑轴 | ID | 约束 |
| --- | --- | --- |
| 身份 | `E1` | 同性别、同 BodyFit、同服装及其余状态下切换 |
| 服装 | `E2` | 同一身份在同性完整 4 套服装矩阵中切换 |
| 身体动作 | `E3` | 在角色同性兼容的 5 条生产动作中切换；底层源注册表保留 12 个已验证文件，生产池启用 10 个 |
| 相机 | `E7` | 在 `near/far/high/side` 四台生产相机间切换 |
| 表情 | 不可编辑 | 所有正式节点固定 Happy；本批不生成 `E11` 边，编辑指令不得要求改变表情 |

### 2.2 本轮明确不包含

- 十个 BodyFit 全量导出和体型编辑。
- 场景替换、灯光/天气/时间编辑、移动镜头和表情编辑。
- 道具交互、配件编辑、三发型切换和头部服装冲突修复。
- Headshot 身份池生产迁移、年龄编辑和儿童体型。
- 任意服装单件组合或完整模块化换装系统。
- Shipping 打包；服务器使用 UE 5.8 Editor 命令行离屏渲染。

这些内容仍可保留为后续 Roadmap 项，但不得进入本轮依赖链。

## 3. 角色与服装覆盖

2026-08-20 的 v2 基线曾让每个性别使用 4 个身份和 4 套服装，但每个身份只导出两个稀疏 Look：

| 身份 | 允许服装 |
| --- | --- |
| `I1` | `O1`, `O2` |
| `I2` | `O2`, `O3` |
| `I3` | `O3`, `O4` |
| `I4` | `O4`, `O1` |

两性共 `16` 个 FullReference Look。这个环形方案降低了初次 CC/UE 验证成本，但只保证图连通：

- 每个身份只有两套服装。
- 每套服装只覆盖两个身份。
- 并非任意身份对都能在同一服装下执行 `E1` 身份替换。

服装仍烘焙在 FullReference Look 中，不临时改造为通用模块化服装系统。身份切换必须保持性别、F02/M02 BodyFit、服装、动作、表情和镜头不变，只改变身份相关外观；因此后续改用完整 32 Look 矩阵。

截至 2026-08-20，8 个身份和 16 个 Look 已冻结并完成 CC 项目与 FullReference FBX/JSON 导出。权威配置为 `cc_first_batch_full_reference_looks_20260820_v2.json`，最终审计为 `OUTPUT_ROOT\character_creator_bridge\artifacts\first_batch_full_reference_assembly\final_audit_20260820_v1.json`，结果 16/16、失败 0。女性 O04 最终固定为 `YogaPants_B + CasualJacket_C + Pump Heel_B`，不再使用会与头发相交的 `Windbreaker_C`。

2026-08-22 的数据编辑复核发现，稀疏环只保证图连通，并不能保证任意两个身份都有共同服装，身份替换轴因此不能覆盖全部身份对。首批资产目标改为每性别 `4 身份 × 4 服装` 的完整矩阵，共 32 Look。`cc_first_batch_full_reference_looks_20260822_v3.json` 定义完整矩阵，`cc_first_batch_full_reference_missing_looks_20260822_v1.json` 记录补齐的 16 个 Look，`cc_first_batch_look_matrix_20260822_v1.json` 保留原 16 与新增 16 的来源区分。

新增 16 已由 `run_20260822_missing16_v1` 完成，合并审计 `OUTPUT_ROOT\character_creator_bridge\artifacts\first_batch_full_reference_expansion\final_audit_20260822_v1.json` 为 32/32、失败 0、partial 目录 0。当前生产机器清单为 `first_batch_required_exports_20260824_v3.json`；完整 32 Look 已导入 `/Game/Vendor/Reallusion/CC5/FirstDataBatch/Looks`，聚合门禁 `OUTPUT_ROOT\unreal_character_import\first_batch_full_reference_expansion_20260822_v2\aggregate_import_gate.json` 为 32/32。每个 Look 在服务器运行全部 5 个同性生产动作、四台正式相机和固定 Happy 表情，因此正式预算为 640 节点；本地不全量渲染。2026-08-24 已完成额外的 32 例本地代表矩阵，每个 Look 一例，轮转覆盖 10 动作、四台审核相机和三表情；该三表情覆盖只作为历史技术证据，不进入正式 640 节点清单。

## 4. 动作与表情

### 4.1 身体动作

用户最初从 P0 候选中选择并验证了 12 个物理动作文件。2026-08-24 删除女性 `ACT_F04_AUDIENCE_09` 与男性 `ACT_M03_AUDIENCE_12` 后，生产池为女性 5 条、男性 5 条；配置图中的每个 Look 只引用同性兼容的 5 条。选择标准：

- 无道具，或只有不影响语义的轻微手势。
- 不依赖椅子、门、杯子、箱子或第二角色。
- 至少覆盖 Idle、行走/位移、站立手势和观察/反应。
- 面部策略必须为 `replaceable`，不得锁定冲突面部通道。
- 记录循环/一次性、Root Motion 和性别偏好；动作可以共用 Skeleton 资产，不按 Look 重复导入。

原动作集中 3 条 `Conversation` 动作未通过 CC 外部 FBX 导出许可门禁，已由用户提供的 `Sexy Dance`、`Battle Dance`、`Cheer Hands & Step Dance` 替换。12 个已验证源动作的 ID、源路径、字节数、SHA-256 与已导出 FBX 保留在 `cc_first_batch_action_registry_20260821_v4.json`，最终窗口保留在 `first_batch_action_window_selection/frozen_20260821_v4/frozen_action_windows.json`。当前生产选择由 `cc_first_batch_action_pool_20260824_v1.json` 冻结，机器清单 `first_batch_required_exports_20260824_v3.json` 锁定 32 Look 和 10 Motion；其中残留的三表情配置属于旧契约，正式节点源必须迁移为 Happy-only 后才能冻结。只有 `ACT_F02_CATCH_BREATH` 使用批准的 InPlace 派生资产，其余 9 条保留源 Root Motion。动作与表情已通过自动运行时门禁；用户接受当前 Happy 轻动态质量用于第一批，但表情不参与编辑链。

### 4.2 表情策略与历史验证

| 表情 | 基础形态 | 动态范围 |
| --- | --- | --- |
| Happy | 轻微嘴角上扬、脸颊抬起、轻度眯眼 | 小幅呼吸式变化与自然眨眼 |
| Angry | 眉间下压/聚拢、轻度眯眼、嘴唇收紧 | 小幅眉眼与嘴角变化 |
| Sad | 内眉抬起、嘴角下压、轻微下唇/下巴变化 | 小幅眉眼与嘴角变化 |

三种表情均已作为技术候选完成本地动态验证，但本 Sprint 的正式节点只启用 Happy。Angry 和 Sad 保留为后续扩展资产，不进入节点预算、链或服务器正式渲染队列。

正式 Happy 规格：

- 表情曲线自身为 `3 s`、`30 fps`、可无跳变循环；在 5 秒节点视频中循环或按 Sequence 区间复用。
- 第 0 帧已经处于目标情绪，不使用 Neutral 作为视频开头。
- 自然眨眼时间点在同批节点中保持一致，便于原子比较。
- 局部动态建议控制在 `±0.03..0.06`，允许轻微左右不对称。
- 不控制 head、neck 和 eye-gaze；这些由身体动画保留。
- 避免大幅张口、极端露齿和极端睁眼。
- 本轮直接使用已验证的 CC `CTRL_expressions_*` Morph 曲线路径，不以 MetaHuman 动画资产作为阻塞依赖。
- `expression_id=happy` 进入 node ID，但由于所有节点值相同，本批没有合法表情边。

## 5. 节点预算与兼容域

每个 `Look × Action` 在固定 Happy 表情下生成四个相机状态：

1. `near + Happy`
2. `far + Happy`
3. `high + Happy`
4. `side + Happy`

因此设计节点数为：

```text
32 Looks × 5 same-sex Actions × 4 Cameras × 1 Expression = 640 nodes
```

节点按兼容性分成两个连通域：

```text
female_v1 = 4 identities × 4 outfits × 5 actions × 4 cameras = 320
male_v1   = 4 identities × 4 outfits × 5 actions × 4 cameras = 320
```

域内必须连通，禁止跨域边和跨域链，不要求男女域全局连通。正式服务器队列采用 `full_pool`，必须包含全部 640 个节点；每个节点只渲染一次，由多条链复用。

当前 32 例代表矩阵让每个 Look 出现一次并覆盖 10 动作、四相机和三表情，它是跨资产链路的历史本地验收，不替代 Happy-only 的正式 640 节点队列。

## 6. 多轮链规则

完整契约见 [`MULTI_ROUND_CHAIN_SAMPLING_V1.md`](../../../sampling/MULTI_ROUND_CHAIN_SAMPLING_V1.md)，架构理由见 [`ADR-0014`](../decisions/ADR-0014-COMPATIBILITY-DOMAINS-AND-CHAIN-POLICIES.md)。本轮冻结：

- 4,000 条链；每条 3–5 次编辑、4–6 个节点。
- `progressive_shortest` 2,000 条：男女各 1,000；长度 3 和 4 各 1,000，不生成长度 5。
- `freeform_walk` 2,000 条：男女各 1,000；长度 3/4/5 分别为 667/666/667。
- 每条边只改变 `identity/outfit/action/camera` 中一个轴；禁止 `A→A`。
- `progressive_shortest` 每个轴最多一次、无回退，链长等于起终状态语义 Hamming 距离。
- `freeform_walk` 可连续修改同一轴、重复节点或边、回退、闭环，也允许偶然成为最短链。
- 每条链保存并重算 `is_semantic_shortest`、`has_repeated_axis`、`has_consecutive_same_axis`、`has_rollback`、`returns_to_start`。
- 男女兼容域各 2,000 条链；全部 640 节点至少被一条链引用。
- 四个编辑轴全局目标各 25%，默认容差为每轴 ±2 个百分点。
- 链唯一性按规范化有序节点/边路径判断；节点和视频可以跨链复用。
- 文本指令必须感知链历史，并且每轮只描述当前原子边。正式字段、`dialogue/standalone` 差异和身份 grounding 限制只按 [Text Schema V1](../../../schema/MULTI_ROUND_VIDEO_EDIT_TEXT_SCHEMA_V1.md) 执行；`chains.jsonl.instructions` 不得作为模型输入。

## 7. 执行顺序与日门禁

| 日期/阶段 | 主要工作 | 当日退出条件 |
| --- | --- | --- |
| Day 1 | 冻结 schema、10 动作生产池（每性别 5 条）、8 个身份/8 套服装映射；同步 Git 并准备服务器预检 | 12 个源动作与窗口保留证据，10 个生产动作已由独立池冻结；服务器环境预检仍待完成 |
| Day 2 | 导入 32 个 FullReference Look 和 12 个动作；完成身体/表情叠加门禁 | CC 合并审计与 UE Look 导入均为 32/32；12 Motion 技术门禁和六个身体/表情动态案例通过；用户接受轻微但可见的表情差异，Day 02 全部完成 |
| Day 3 | 固定场景锚点、四台生产相机、灯光和参数化 Sequence；构建 640 节点正式输入 | 本地 32-Look 代表矩阵 32/32 已通过；Happy-only 四相机正式源仍待写入 |
| Day 4 | 迁移配置图生成器；生成两个连通域、4,000 条链、15,000 回合双语 prompt 与 640 个渲染作业；本地跑通代表完整链 | 图、精确配额、事实标签、文本层和代表链媒体/哈希通过机器与人工门禁 |
| Day 5 | 服务器渲染 10 节点基准并修复 Linux/插件/路径问题 | 10/10 节点成功，得到 p50/p95 和全量 ETA |
| Day 6 | 按已验证的 640 作业批量渲染完整节点库 | 节点完成率达到目标，失败可按 node_id 重试且不改变配置 |
| Day 7 | 重试失败、回填媒体、链引用/哈希审计、抽样视觉验收和交付封装 | 4,000 条有效链、640 节点媒体齐全、0 悬空引用 |

任何一天未通过退出条件，不假装进入下一阶段；优先启用第 9 节降级而不是扩大排错范围。

Day 2 的 CC 自动动作导出曾被内容许可交互阻塞，因此最终 12 个 Motion FBX 采用 [`FIRST_BATCH_MANUAL_EXPORT_HANDOFF_2026-08-21.md`](./FIRST_BATCH_MANUAL_EXPORT_HANDOFF_2026-08-21.md) 的人工导出与机器验收路径；3 条许可受阻动作已替换，不再尝试绕过许可门禁。UE FullReference 导入阶段已经为已知 FBX 导入与 Auto Setup 对话框建立精确守卫，并完成 32/32 自动编排和机器验收；未知对话框仍必须停止交由用户处理。

Day 3 本地结果位于 `OUTPUT_ROOT\unreal_render\first_batch_32look_matrix_20260824_v002`：32/32 视频、4,800 PNG、10 动作、四审核相机和三表情覆盖通过。首次运行中后续 Look 整段 T-pose 的原因是 CC Blueprint 默认动画模式不一致；男女 Section 现均强制 Custom Mode，执行器会在 MRQ 前检查 pose-driver contract。Day 3 的本地参数化渲染部分已经关闭，剩余工作转入正式 640 节点源和 Day 4 数据封装。

Day 4 的结构、文本与代表链门禁已经关闭：正式图为 640 节点、8,320 条原子边、4,000 条链和 640 个 render job；独立文本层为 4,000 dialogs / 15,000 turns，E1/E2/E3/E7 各 3,750，双语完整且内部 ID 泄漏为 0。男女各一条代表链的 9 个唯一视频通过机器门禁、assistant 预检和用户视觉签字。当前剩余路径从 Day 5 服务器环境/项目 smoke 与 10 节点基准开始。

长批次在连续完成 9 个新增 Look 后使 UE private commit 增长到约 84–90 GB 并崩溃。`M_ID02_O01` 在干净重启后通过，证明故障来自进程累计资源而非该资产。此后新 Auto Setup 导入固定为每个 UE 会话最多 3 个 Look，批间正常重启；交互导入禁用 `--continue-on-error`，窗口守卫必须与 UE 使用相同 Windows 权限级别。既有 32 Look 的无弹窗重验可以在同一会话完成。该实施结果不改变冻结的 32 Look 或 5 秒生产时长；12 个已验证 Motion 的历史集合由 2026-08-24 的 10 动作生产池进一步收敛。

## 8. 职责划分

| 责任方 | 本轮职责 |
| --- | --- |
| 用户 | 对正式 Happy 动态和代表视频结果签字；处理未知 CC/UE 图形界面交互，并确认服务器访问与资产上传边界 |
| Agent | 生成配置和导出清单；构建 UE 场景/相机/Sequence/渲染入口；生成节点图与链；运行机器验证、失败重试、文档与报告 |
| 双方 | 决定 10 节点基准后的分辨率、时长和并发策略；处理未知 CC/UE 弹窗与视觉异常 |

## 9. 性能基准与降级顺序

服务器必须先渲染 10 个覆盖两性、四相机和不同动作的 Happy 节点，再计算全量 ETA。只有基准通过后才能发出完整节点队列。

若 ETA 无法在剩余时间内完成，依次处理：

1. 调整服务器并发、批次大小、失败重试和缓存策略，不减少节点。
2. 分辨率按冻结回退档从 `2560×1440` 降级；回退档必须使用独立 `render_profile_id`，不得覆盖生产节点。
3. 只有用户再次批准时，时长才可由 `5 s → 3 s → 2 s`，保持 `30 fps`。
4. 延长服务器生产窗口；本轮不再删减 640 节点、每 Look 的 5 个动作、Happy 表情或四台相机。

任何性能调整都必须保留：两个兼容域、8 个身份、同性各 4 套服装、当前 10 个生产动作、Happy 表情、四台相机、原子边、两类链策略和精确链配额。表情不作为编辑轴。

## 10. 停止条件

- 角色、服装、Skeleton 或 Morph 与已验证参考不一致。
- 相机遮挡人物、角色穿地/墙或明显服装穿模。
- 任一边同时改变两个及以上编辑轴。
- 节点 ID 与媒体/sidecar 哈希不一致，或链出现悬空引用。
- 服务器 UE 版本、插件、Vulkan/NVIDIA、大小写路径或 shader 无法在 Day 5 前通过 10 节点基准。
- 实测 ETA 即使完成第 9 节降级仍超过截止时间。

## 11. 本轮不宣称完成的长期能力

第一批成功只证明这套受限配置图可以生成和封装数据，不代表：

- 十体型、全部服装、全部动画或 Headshot 身份池已经生产化。
- UE 通用模块化换装、三发型、道具和年龄编辑已经完成。
- `WF-08`、`WF-09` 对所有未来场景和数据类型均已生产批准。

本 Sprint 完成后把事实写入 Milestone；本文件转入历史，不继续承载下一轮计划。
