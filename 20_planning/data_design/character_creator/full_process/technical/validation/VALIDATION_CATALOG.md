# 验证契约目录

> 文档 ID：`TECH-VALIDATION-01`
> 文档类型：`technical`
> 生命周期：`current`
> 适用阶段：全部 Workflow
> 实现所有权：验证 ID、触发条件、证据契约、通过/失效语义和状态落点
> 验证所有权：`VAL-DOC-01`
> 输出契约：`OUT-GLOBAL-VALIDATION-EVIDENCE`
> 最近核验：2026-08-25

## 1. 本目录负责什么

本目录是验证控制面，只回答以下问题：某个 Gate 需要哪些验证、验证 ID 代表什么、由哪份 Technical 文档实现、至少保存什么证据、怎样才算通过、何时结果失效，以及当前结果写到哪里。准确命令、脚本参数和领域恢复步骤仍由实现该验证的 Technical 文档负责，不能在本页维护第二份命令真相。

验证定义与验证结果必须分离：本页长期稳定；当前 `passed/pending/failed` 只写入对应 Workflow Status 或 Batch Status。脚本退出 0、文件存在或单张截图正常都不足以自动通过含视觉判断的验证。

## 2. 状态与 Gate 语义

验证结果只允许以下状态：

| 状态 | 含义 |
| --- | --- |
| `passed` | 当前输入、实现和环境下满足全部机器与人工条件 |
| `passed_with_accepted_risk` | 仅在当前计划/批次明确接受例外时通过，必须列出范围和决定 |
| `pending` | 尚未执行或证据不完整 |
| `failed` | 已执行且至少一项硬条件失败 |
| `not_applicable` | 条件验证在本次不适用，必须记录原因 |
| `expired` | 输入哈希、实现、资产、应用会话或环境变化使旧结果失效 |

Exit Gate 关闭前，所有 `required` 验证必须为 `passed` 或经当前计划批准的 `passed_with_accepted_risk`；`conditional` 验证必须为适用时通过、不适用时明确写成 `not_applicable`。`pending`、`failed`、`expired` 都不能被描述为 Gate 已通过。

## 3. 验证索引

| ID | Workflow / Gate | 角色 | 实现所有者 | 证据输出 | 当前结果所有者 |
| --- | --- | --- | --- | --- | --- |
| `VAL-ENV-01` | `WF-00 / GATE-00` | required | [环境与会话](../environment/ENVIRONMENT_AND_SESSION.md) | `OUT-WF00-SESSION` | [WF-00 状态](../../project_management/status/workflows/WF-00.md) |
| `VAL-BRIDGE-01` | `WF-00/WF-30` | conditional | [CC Bridge](../bridge/CC_BRIDGE_OPERATIONS.md) | `OUT-WF00-SESSION` 或 `OUT-WF30-CC-ASSETS` | [WF-00](../../project_management/status/workflows/WF-00.md) / [WF-30](../../project_management/status/workflows/WF-30.md) |
| `VAL-SPEC-01` | `WF-10 / GATE-10` | required | [批次规格](../dataset/BATCH_SPECIFICATION.md) | `OUT-WF10-BATCH-SPEC` | [WF-10 状态](../../project_management/status/workflows/WF-10.md) |
| `VAL-MATRIX-01` | `WF-20 / GATE-20` | required | [资产矩阵冻结](../dataset/ASSET_MATRIX_FREEZE.md) | `OUT-WF20-ASSET-MATRIX` | [WF-20 状态](../../project_management/status/workflows/WF-20.md) |
| `VAL-CC-01` | `WF-30 / GATE-30` | required | [BodyFit/Identity/Age](../character_creator/BODYFIT_IDENTITY_AGE.md) | `OUT-WF30-CC-ASSETS` | [WF-30 状态](../../project_management/status/workflows/WF-30.md) |
| `VAL-CC-02` | `WF-30 / GATE-30` | required | [服装系统](../character_creator/OUTFIT_SYSTEM.md) | `OUT-WF30-CC-ASSETS` | [WF-30 状态](../../project_management/status/workflows/WF-30.md) |
| `VAL-TRANSFER-01` | `WF-40 / GATE-40` | required | [CC→UE FullReference](../transfer/CC_TO_UE_FULLREFERENCE.md) | `OUT-WF40-TRANSFER-BUNDLE` | [WF-40 状态](../../project_management/status/workflows/WF-40.md) |
| `VAL-UE-01` | `WF-50 / GATE-50` | required | [角色运行时](../unreal/CHARACTER_RUNTIME.md) | `OUT-WF50-RUNTIME-ACCEPTANCE` | [WF-50 状态](../../project_management/status/workflows/WF-50.md) |
| `VAL-UE-02` | `WF-50 / GATE-50` | conditional | [角色运行时](../unreal/CHARACTER_RUNTIME.md) | `OUT-WF50-RUNTIME-ACCEPTANCE` | [WF-50 状态](../../project_management/status/workflows/WF-50.md) |
| `VAL-UE-03` | `WF-50 / GATE-50` | conditional | [动画、表情与 Morph](../unreal/ANIMATION_EXPRESSION_MORPH.md) | `OUT-WF50-RUNTIME-ACCEPTANCE` | [WF-50 状态](../../project_management/status/workflows/WF-50.md) |
| `VAL-SCENE-01` | `WF-60 / GATE-60` | required | [场景、相机与 Sequence](../unreal/SCENE_CAMERA_SEQUENCE.md) | `OUT-WF60-SEQUENCE-TEMPLATE` | [WF-60 状态](../../project_management/status/workflows/WF-60.md) |
| `VAL-GRAPH-01` | `WF-70 / GATE-70` | required | [配置图与链](../dataset/CONFIG_GRAPH_AND_CHAINS.md) | `OUT-WF70-JOB-GRAPH` | [WF-70 状态](../../project_management/status/workflows/WF-70.md) |
| `VAL-TEXT-01` | `WF-70 / GATE-70` | required | [Prompt 层](../dataset/PROMPT_LAYER.md) | `OUT-WF70-JOB-GRAPH` | [WF-70 状态](../../project_management/status/workflows/WF-70.md) |
| `VAL-RENDER-01` | `WF-80 / GATE-80` | required | [渲染执行](../rendering_release/RENDER_EXECUTION.md) | `OUT-WF80-NODE-MEDIA` | [WF-80 状态](../../project_management/status/workflows/WF-80.md) |
| `VAL-SERVER-01` | `WF-80 / GATE-80` | conditional | [服务器执行](../rendering_release/SERVER_EXECUTION.md) | `OUT-WF80-NODE-MEDIA` | [WF-00](../../project_management/status/workflows/WF-00.md) / [WF-80](../../project_management/status/workflows/WF-80.md) |
| `VAL-RELEASE-01` | `WF-90 / GATE-90` | required | [数据集封装](../rendering_release/DATASET_PACKAGE.md) | `OUT-WF90-DATASET-RELEASE` | [WF-90 状态](../../project_management/status/workflows/WF-90.md) |
| `VAL-DOC-01` | 全部文档变更 | required-on-change | [文档体系审计](./DOCUMENTATION_VALIDATION.md) | `OUT-GLOBAL-DOC-AUDIT` | [项目状态](../../project_management/status/PROJECT_STATUS.md) |

## 4. 分项契约

### 4.1 `VAL-ENV-01` 环境与会话

- 触发：新会话、换机、应用重启、崩溃恢复、路径或插件变化。
- 最小证据：路径/版本/Python/Git/磁盘、本轮必需应用和通道状态；服务器运行还需 GPU/Vulkan/UE 项目检查。
- 通过：本轮所有必需通道可执行，非必需通道被明确排除。
- 失效：相关应用重启、机器切换、环境或项目版本改变。

### 4.2 `VAL-BRIDGE-01` CC Bridge

- 触发：本轮通过 Bridge 调用 CC 前，以及 CC 重启后。
- 最小证据：Heartbeat、Ping、Scene Summary、唯一 Job ID、Lease 和终态 Result。
- 通过：请求只执行一次、结果与当前会话匹配、无未处理模态窗口。
- 失效：CC/Runner 重启、队列路径或协议版本变化。

### 4.3 `VAL-SPEC-01` 批次规格

- 触发：创建批次，或修改编辑轴、兼容域、规模、媒体规格、交付结构、降级与停止条件。
- 最小证据：当前计划需求、Batch Status、`PROJECT_STATE.json` 与机器规格的字段对照报告。
- 通过：上述来源无冲突，所有必填项、ID、单位和不包含项明确。
- 失效：任一受控批次字段或计划需求改变。

### 4.4 `VAL-MATRIX-01` 资产与生产矩阵

- 触发：生产资产池、兼容规则、Look/Action/Expression/Scene/Camera ID 或规模变化。
- 最小证据：来源 Registry 哈希、兼容域、排除原因、完整矩阵和预期计数报告。
- 通过：所有生产 ID 可解析，域内组合闭合，矩阵数量与批次规格一致，无隐式默认值。
- 失效：任一来源资产、Registry、兼容规则或批次规格变化。

### 4.5 `VAL-CC-01` 身体与身份

- 触发：BodyFit、Identity、Head Profile、年龄、眼口或皮肤组装逻辑变化。
- 最小证据：源项目/配方哈希、重建指纹、中性/闭眼/微笑/张嘴/侧面和重载一致性证据。
- 通过：身份与身体可确定性恢复，眼球、眼皮、牙齿、口腔和接缝没有未接受错误。
- 失效：源项目、Morph 规则、CC 版本或身份配方变化。

### 4.6 `VAL-CC-02` 服装兼容

- 触发：Outfit Family、槽位规则、鞋池、体型或动作压力集合变化。
- 最小证据：Family Schema 报告、Inventory Signature、极端体型静态视角和动作压力视频/决定。
- 通过：必需槽位完整，互斥/可选规则正确，未接受穿模为零；已接受风险精确到 Look/Action。
- 失效：服装文件、Family JSON、BodyFit 或压力动作集合变化。

### 4.7 `VAL-TRANSFER-01` CC 到 UE

- 触发：Bundle、导出/导入设置、Auto Setup、Skeleton 或目标 Object Path 变化。
- 最小证据：Bundle Manifest/哈希、导入报告、Object Path 映射和聚合 Gate。
- 通过：全部预期 Look 导入，Skeleton/Morph/材质/皱纹正确，无静默失败。
- 失效：源 Bundle、插件/UE 版本、导入参数或 UE 资产变化。

### 4.8 `VAL-UE-01` 生产运行时

- 触发：Look、动作、表情、Composite、动画模式或材质修复变化。
- 最小证据：生产组合覆盖报告、首中末帧/视频、T-pose/材质/时间变化审计和人工决定。
- 通过：没有 T-pose、静止冒充动作、白块、错误 Skeleton、错误身份或未登记严重穿模。
- 失效：任一生产资产、Composite、动画模式、材质或运行时 Blueprint 变化。

### 4.9 `VAL-UE-02` 模块化运行时

- 触发：批次使用分离网格、Leader Pose、运行时服装/毛发切换时。
- 最小证据：组件拓扑、Leader Pose、Morph 广播、动画同步和切换矩阵报告。
- 通过：所有声明可切换组件在验证范围内同步且无新增严重穿模。
- 失效：组件、Skeleton、Leader Pose 或切换逻辑变化。

### 4.10 `VAL-UE-03` 可编辑 Morph

- 触发：批次把 Elder 或其他 Morph 作为 UE 运行时编辑轴时。
- 最小证据：Morph 名称/范围、身体与附属网格跟随、动画极值和材质检查。
- 通过：完整声明范围内几何、毛发、胡须、眉毛和材质协调，且节点语义可追溯。
- 失效：Morph 范围、网格、材质或运行时广播逻辑变化。

### 4.11 `VAL-SCENE-01` 场景、相机与 Sequence

- 触发：地图、锚点、相机、窗口、InPlace 例外、Sequence 或 MRQ Profile 变化。
- 最小证据：UE 对象审计、四机位构图、150 帧时间变化、绑定和安全范围报告。
- 通过：角色可见且居中、无场景穿模、机位语义正确、绑定稳定、动作窗口准确。
- 失效：任一上述资产或参数变化。

### 4.12 `VAL-GRAPH-01` 图与链

- 触发：图源、Schema、兼容域、编辑轴、采样配额或 Builder 变化。
- 最小证据：`source_manifest.json`、`build_report.json`、确定性重建结果和悬空引用检查。
- 通过：计数符合批次规格，每条边只变一个轴，链标签可重算，域规则与 ID 全部有效。
- 失效：输入哈希、Schema 或 Builder 变化。

### 4.13 `VAL-TEXT-01` Prompt 层

- 触发：Prompt Catalog、模板、身份描述、语言或媒体 URI 规则变化。
- 最小证据：Prompt Manifest/Report、Dialog/Turn 计数、边对齐、内部 ID 泄漏和引用检查。
- 通过：全部 Turn 与图一致，文本自然、目标明确、无禁止泄漏和悬空引用。
- 失效：图、Catalog、模板、身份参考或 URI 映射变化。

### 4.14 `VAL-RENDER-01` 节点媒体

- 触发：Render Job、UE 资产、Sequence、MRQ Profile、执行器或媒体规格变化。
- 最小证据：节点状态、输入哈希、视频规格、首中末帧、首帧到第二帧连续性、时间变化、媒体哈希、失败分类和人工抽检；同节点跨 Run Root 复验还需逐帧确定性报告。
- 通过：计划节点均有唯一有效媒体，无黑帧、T-pose、错误机位、静止假动作或冲突哈希；第一批首帧 MAD `<=12`。确定性默认要求 mean frame MAD `<=1.5`、p95 `<=2.0`、单帧 max MAD `<=3.0`、差值大于 5 的像素比例 `<=1%`，且两侧 Editor profile 完全相同。
- 失效：任一输入哈希、执行器或媒体契约变化。

### 4.15 `VAL-SERVER-01` 服务器环境

- 触发：首次在服务器/新机器生产，以及环境、项目或插件变化后。
- 最小证据：Linux/GPU/Vulkan/UE/项目/插件/磁盘检查、两次离屏启动、正式 Tokyo 样例、同节点确定性、10 节点基准及中断恢复报告。
- 通过：两次启动稳定，项目资产完整，10/10 基准可恢复，同一 Editor 连续处理已冻结多节点批次且性能方案可接受；未关闭的 Validation VUID 必须显式记为 bounded risk，不能静默视为不存在。
- 失效：机器镜像、驱动、UE、项目、插件或路径映射变化。

### 4.16 `VAL-RELEASE-01` 数据集发布

- 触发：每个发布候选。
- 最小证据：发布 Manifest、顺序视频编号映射、媒体/GT/Sidecar/图/完整链/简化链/正式 Prompt 零悬空检查、统计 QA、人工抽检和 Checksums。
- 通过：`videos/1.mp4...` 连续无缺口，`chains.json` 每轮含双语 Prompt 且输入/输出均解析到唯一 accepted 媒体；`chains_simple.json` 的 `chain_index` 从 1 连续编号且逐轮等于完整链投影；交付包可在另一台机器独立验证，所有必需 QA 通过且版本不可变。
- 失效：发布候选中任意内容或哈希变化。

### 4.17 `VAL-DOC-01` 文档体系

- 触发：Workflow、Technical、Validation、Output、Status/Plan/History、Reference、代码所有权或输出规则变化。
- 最小证据：目录重建结果、文档审计 JSON、相关 pytest 结果和人工顺向/反向抽查。
- 通过：所有子系统各自契约通过，跨层 ID 与链接闭合，无状态/计划/证据冲突。
- 失效：活跃文档、目录生成器、实现所有权或输出策略再次变化。

## 5. 通用证据契约

每次验证至少记录：`validation_id`、输入 ID/哈希、实现版本、环境、开始/结束时间、结果状态、失败分类、证据 URI、输出契约 ID 和审查人。视觉验证还必须记录覆盖样例、决定与例外。证据目录必须有 Manifest；散落截图、聊天结论和未绑定源文件的网页不能单独支撑 Gate。

验证结果变更时只更新对应 Status；验证定义变更时更新本目录、实现 Technical、受影响 Workflow、模板和检查器。恢复共性见 [恢复手册](./RECOVERY.md)，视觉共性见 [视觉审查](./VISUAL_REVIEW.md)。
