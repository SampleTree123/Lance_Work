# Character Creator 角色工厂当前状态

> 文档角色：`current_status_snapshot`
> 状态：`current`
> 适用阶段：`global`
> 权威范围：当前可用能力、第一批数据基线、未完成项和唯一下一步
> 上级入口：[`CHARACTER_FACTORY_MASTER_SPEC.md`](./CHARACTER_FACTORY_MASTER_SPEC.md)
> 上游：机器配置、验证报告、人工验收与 [2026-08-19 周报](./history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md)
> 下游：[`FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md`](./planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md) 与各 Workflow
> 最近核验：2026-08-20
> 更新方式：覆盖更新；完成事件只追加到 [`MILESTONE_LOG.md`](./history/MILESTONE_LOG.md)

## 1. 当前结论

角色工厂已经有可用的 CC 角色基础、服装规则、首批 8 个冻结身份、16 个已保存并导出的 FullReference Look、F02/M02 UE 身体/面部组合 Pilot、首批 12 动作机器门禁，以及 Happy/Angry/Sad 的 UE 轻动态表情实现。配置图和 4,000 链生成器已通过合成输入测试，但动作 UE Bundle、16 Look 的 UE 导入、场景、Sequence、批量渲染和数据集封装尚未贯通。

当前唯一活动目标是 [第一批多轮编辑数据 Sprint](./planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md)：在 2026-08-26 前，用受限配置图渲染最多 384 个唯一节点，并生成目标 4,000、最低 3,000 条 3–5 轮编辑链。

本轮不等待十体型、全部动画、Headshot 身份迁移、三发型、道具或通用模块化换装完成。

## 2. 第一批冻结基线

| 维度 | 本轮值 | 当前状态 |
| --- | --- | --- |
| BodyFit | 女性 `F02_Average`、男性 `M02_Average` | 已有 CC/UE 参考证据 |
| 身份 | 每性别 4 个，共 8 个 | `F_ID01..04`、`M_ID01..04` 已冻结、保存并有哈希证据 |
| 服装 | 每性别 4 套，共 8 套；环形稀疏组合形成 16 个 Look | 16/16 CC 项目和 FullReference FBX/JSON 已通过最终审计；女性 O04 使用 `CasualJacket_C` |
| 身体动作 | 12 个物理文件：女性 6 条、男性 6 条；每个 Look 使用 6 条同性动作 | v3 源文件、CC 机器门禁和 5 秒窗口已完成用户签字并按 SHA-256 冻结；Motion FBX 导出及 UE 门禁待完成 |
| 表情 | Happy、Angry、Sad；F02/M02 各三条 3 秒可循环轻动态 Morph clip | UE 资产、6/6 运行时案例和 18/18 图已通过机器门禁；动态视觉签字待完成 |
| 场景 | 1 个场景、1 个安全锚点、固定灯光 | 待在 WF-08 固定 |
| 相机 | 中近景、全身景各 1 台 | 待在 WF-08 固定 |
| 节点 | `16 Looks × 6 sex-compatible Actions × 4 states = 384` | schema 与确定性生成器已实现并通过测试；身份/服装真实源已冻结，动作窗口与场景源待补齐 |
| 链 | 3–5 轮；目标 4,000，最低 3,000 | 4,000 链确定性生成、原子边、回退/闭环和覆盖检查已通过测试；真实冻结源待补齐 |
| 输出 | 节点媒体、sidecar、哈希、配置图、链和报告 | WF-09 待实现 |
| 服务器 | Git 代码/文档/配置已于 2026-08-20 同步；Linux/NVIDIA + UE 5.8 Editor 离屏运行 | 环境预检、二进制资产包、项目 smoke 与 10 节点基准待完成 |

完整冻结范围、日程和降级顺序只在 Sprint 文档维护。

## 3. 已验证且本轮可复用

| 能力 | 成熟度 | 可复用边界 |
| --- | --- | --- |
| 成人 BodyFit | `production` | 10 个源项目有 hash 锁；本轮只使用 F02/M02 |
| Face V3 | `production` | 20 seed、17 个生产主原型、200 条配方；本轮身份仍从该稳定池选择 |
| 面部外观池 | `production` | 21 皮肤、12 眼球材质、13 眉毛、9 睫毛、2 牙齿、5 胡须、58 发型 |
| CC Bridge | `validated_pilot` | 受控离线文件队列可工作；CC 必须由用户按离线许可方式启动 |
| 完整角色装配 | `first_batch_export_validated` | 8 身份、16 Look 已确定性装配、保存和 FullReference 导出；16/16 最终审计通过 |
| 服装规则 | `validated_pilot` | 41 family、53 逻辑组；极端体型静态 159/159、动作压力 53/53，用户已接受/抽查 |
| P0 动作 | `validated_pilot` | 16 条已完成 CC 动态检查和用户视觉接受；4 条代表动作完成 UE Pilot |
| 首批 12 动作 | `window_frozen_pending_motion_export_and_ue` | 女性 6、男性 6；v3 注册表、12/12 最终窗口签字及冻结产物完整；Motion FBX/UE 门禁待完成 |
| 首批三表情 | `machine_validated_pending_visual` | F02/M02 共 6 个 UE 曲线资产；身体动作叠加运行时 6/6、18/18 图、自动错误 0 |
| 第一批配置图生成器 | `implemented_partially_frozen_input` | 合成输入可确定性生成 384 节点、原子边、4,000 条 3–5 轮链与渲染作业；8 身份、16 Look 和动作窗口已冻结，场景精确 ID 待写入 |
| CC→UE FullReference | `validated_pilot_first_batch_ready` | F02/M02 Pilot 已通过 UE 5.8 + Auto Setup 2.03；首批 16 Look 的 CC Bundle 已通过 16/16 审计，等待 UE 批量导入 |
| UE 身体/面部分层 | `validated_pilot` | F02/M02 的 4 body × 4 direct-Morph face 为 16/16、24/24 图 |
| UE 模块化 M02 | `validated_pilot` | 20 组件、19 follower、Morph 广播可用，但不作为本轮通用换装前提 |
| UE Elder Morph | `validated_pilot` | M02 Pilot 可连续变化；本轮不使用年龄编辑 |
| 可视化门户 | `production_utility` | 可登记、筛选、放大和审查当前截图/结果分支 |

FullReference 直接 Morph 路线必须禁用角色组件的 Post Process Blueprint，否则会与 RL 求值重复并产生眼部伪影；当前 Pilot 不声明 eye-bone gaze。

## 4. 本轮尚未完成

1. 用户完成三种表情的动态视觉签字；完成已冻结 12 个动作的 Motion FBX 导出与 UE 门禁。
2. 将已审计的 16 个 FullReference Look 批量导入 UE，并验证 Skeleton、Morph、材质和 Auto Setup 输出。
3. 在单场景中固定安全角色锚点、两台相机、灯光和 Sequence 模板。
4. 用真实冻结资产填充配置图源，生成 384 节点、原子边、4,000 条链与渲染作业。
5. 实现唯一节点渲染、sidecar、哈希、失败重试和交付验证，并在本地跑通一条 3–5 轮完整链。
6. 服务器先完成不依赖资产包的环境预检；项目与二进制资产同步后，再完成插件/大小写路径项目 smoke 和 10 节点基准。
7. 按实测速度完成 384、288 或 192 节点档位，并交付至少 3,000 条有效链。

这些项目的顺序和退出条件见 [Sprint](./planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md)，不能从旧实验日志推断。

## 5. 当前已知限制

- 头发与头巾、兜帽、高领服装可能相交；本轮优先选择无此风险的 16 个 Look，不在本周建设通用兼容系统。
- 服装按烘焙 FullReference Look 导出，不支持 UE 内任意单件组合。
- Headshot 10 人候选保持冻结且 0 个生产启用；本轮继续使用 Face V3。
- 69 条 P0 剩余动作的离线人工决定仍可继续，但不阻塞本轮 12 个动作文件。
- 当前生产动画批准数为 0；本 Sprint 只能晋升用户视觉接受并完成 UE 门禁的 12 个动作文件及三条表情。
- 首批动作旧 v1 导出被软件自身的 `You must first purchase the content licenses in order to export FBX files.` 对话框阻断并已失败收口；16 个角色 FullReference 已另行成功导出，但这不等于 12 个 Motion FBX 已解除阻塞。
- CC 的额外 `textures\` 目录只在 Auto Setup JSON 引用布料权重图时生成；FBX、JSON 和 `.fbm\` 始终必需，不能把“无权重图所以无 `textures\`”误判为导出失败。
- `WF-08` 与 `WF-09` 目前仍是 `planned`，第一条本地完整链和服务器基准通过后才能提升成熟度。
- CC 未知弹窗、Undo 警告、private memory 达到 24 GB、UE 资产/哈希漂移均要求停止，不允许自动猜测。

## 6. 关键入口

| 需求 | 权威入口 |
| --- | --- |
| 本周做什么 | [第一批数据 Sprint](./planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md) |
| 配置图字段 | [Config Graph Schema V1](../../schema/CONFIG_GRAPH_SCHEMA_V1.md) |
| 3–5 轮链如何采样 | [Multi-round Sampling V1](../../sampling/MULTI_ROUND_CHAIN_SAMPLING_V1.md) |
| 服务器怎么预检和渲染 | [Server Runbook](../../../implementation/FIRST_BATCH_SERVER_RUNBOOK.md) / [Executable Preflight](../../../implementation/FIRST_BATCH_SERVER_PREFLIGHT.sh) |
| 当前代码/JSON/UE 资产 | [Implementation Index](./reference/IMPLEMENTATION_INDEX.md) |
| 后续而非本周工作 | [Roadmap](./planning/ROADMAP.md) / [Backlog](./planning/BACKLOG.md) |
| 已完成过程与证据 | [Milestone](./history/MILESTONE_LOG.md) / [周报](./history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md) |

## 7. 唯一下一步

先完成三种表情的动态视觉签字，并生成 `required_exports.json`。随后把已审计的 16 个 FullReference Look 导入 UE，完成已冻结 12 个动作的 Motion FBX 导出/导入门禁；通过后固定场景、角色锚点、两台相机与 Sequence。服务器可并行执行 `FIRST_BATCH_SERVER_PREFLIGHT.sh --environment-only`，但场景 ID、本地完整链和资产 manifest 未冻结前，不上传生产资产包或开始全量节点渲染。
