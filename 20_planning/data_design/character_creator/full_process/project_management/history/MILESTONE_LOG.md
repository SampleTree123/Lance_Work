# 项目里程碑

> 文档 ID：`HISTORY-MILESTONES`
> 文档类型：`history`
> 生命周期：`current`
> 权威范围：已完成的重要能力与批次事件摘要
> 最近核验：2026-08-25

## 2026-07：CC 自动化基础

- 建立受控 RLPy/Bridge 探针，确认可加载项目、应用 Morph/资产、保存项目和采集验证图。
- 冻结 10 个成人 BodyFit，形成哈希、Body/Junction 指纹与头颈修正规则。
- Face V3、外观池和 Headshot Pilot 逐步形成；Headshot 暂未进入第一批生产。

## 2026-08-01 至 08-17：外观与服装系统

- 眼球、牙齿、眉毛、睫毛、胡须、头发和青年皮肤候选完成受控验证。
- 服装整理为 41 个 Family、53 个逻辑组；静态极端体型 159/159、动作压力 53/53 通过。
- 记录头发与兜帽/头部服装冲突为已知风险，第一批不阻塞。

## 2026-08-18 至 08-22：CC→UE 与第一批资产

- M02 模块化 Pilot 证明 Leader Pose、Morph 广播和身体/面部分层可行。
- FullReference F02/M02 Pilot、动作导入和直接 Morph 契约通过。
- 第一批扩展为 8 个身份 × 4 套服装 = 32 Look，32/32 CC 导出与 UE 导入通过。
- 动作收敛为男女各 5 个；Catch Breath 使用唯一 InPlace Override。

## 2026-08-23 至 08-24：场景、媒体、图和文本

- TokyoStylized、统一锚点、四相机、五秒/30 FPS/1440p 渲染配置通过。
- 32-Look 本地代表矩阵通过；修复动作 T-pose 与面部白块问题。
- 正式图生成 640 节点、8,320 边、4,000 链和 640 Render Job，结构门禁通过。
- 代表链媒体视觉通过；Prompt V2 生成 4,000 Dialog、15,000 Turn 并通过文本门禁。

## 2026-08-25：文档运行模型 V2

- 完成全量文档/代码/输出审计，建立 Master→Workflow→Technical/Status/Validation 主线。
- 引入 Workflow/Batch 双状态、唯一当前计划、输出保留等级和文档维护 Skill 契约。
- 旧活跃树保留哈希快照，ADR-0015 取代旧文档架构决定。

## 2026-08-25：文档子系统独立闭环

- 依据 ADR-0016，把 Workflow、Validation、Output、Technical、Status、Plan、History、Decisions、Reference、Registry、Governance、Templates 与 Master 改为可分别审计的子系统；任何跨层成功均不能抵消子系统自身缺口。
- Reference 与 Registry 完成职责分离；Master 提供面向人的完整阅读路径，各 Workflow 明确实现、验证、输出和状态入口。
- 文档检查器新增逐子系统结果与显式跨层契约结果，配套回归覆盖未定义验证、状态漏输出、错误计划生命周期、Technical 元数据缺失、Workflow 缺少精确实现导航、输出语义/下游缺失和 Status 当前角色缺失。
- `VAL-DOC-01` 通过，当时的正式证据保存在 `%OUTPUT_ROOT%/documentation_audit/documentation_rebuild_20260825_v2/`；原 `v1` 作为被取代证据保留。

## 2026-08-25：正式 Render Job 执行器本地验收

- 完成 `render_jobs.jsonl` 驱动的正式节点执行器，覆盖输入锁、Lease、attempt、GT/Sidecar、媒体 Manifest、原子晋升和按 `node_id` 恢复。
- 男女各 1 个真实节点首次渲染 2/2 accepted；同一 Run Root 第二次调用得到 `rendered=0`、`reused=2`，证明按配置与媒体 SHA-256 断点复用。
- 媒体均为 2560×1440、30 FPS、150 帧、5 秒；Pose Driver、时间变化和人工代表帧检查通过。
- 证据位于 `%OUTPUT_ROOT%/unreal_render/first_batch_formal_executor_smoke_20260825_v003/`。该里程碑关闭计划 `R07`，不关闭服务器预检、10 节点基准或完整 `GATE-80`。
- 文档、脚本目录、输出治理、状态与计划的闭环审计证据升级为 `%OUTPUT_ROOT%/documentation_audit/documentation_rebuild_20260825_v3/`。
