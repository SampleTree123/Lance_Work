# 输出契约目录

> 文档 ID：`TECH-OUTPUT-01`
> 文档类型：`technical`
> 生命周期：`current`
> 适用阶段：全部 Workflow
> 实现所有权：稳定输出 ID、存储类别、Run Root、Manifest、晋升和失效语义
> 验证所有权：`VAL-DOC-01`
> 输出契约：`OUT-GLOBAL-OUTPUT-INVENTORY`
> 最近核验：2026-08-31

## 1. 目的与边界

`OUT-*` 表示逻辑产物契约，不等于单个文件夹。一个产物可以同时包含 Git Registry、外部二进制、UE Object Path 和运行证据，但必须由一个主要 Technical 能力解释，且由状态文档指出当前接受版本。

本目录不复制每个领域的完整文件列表，也不把 `%OUTPUT_ROOT%` 内所有历史目录自动晋升为生产产物。准确生成步骤和字段见“生产所有者”；当前证据见“状态所有者”；物理目录的保留分类见 [输出盘点与保留](./INVENTORY_AND_RETENTION.md)。

## 2. 存储类别

| 类别 | 含义 | 典型位置 |
| --- | --- | --- |
| `versioned_registry` | Git 管理的 Schema、Registry、配置和轻量 Manifest | `%LANCE_ROOT%/00_engine/scripts/`、`20_planning/` |
| `external_binary` | CC 项目、素材库等不进入 Git 的权威二进制 | `%CC_ASSET_ROOT%` |
| `cc_export_bundle` | CC 导出的 FBX/JSON/纹理 Bundle | `%CC_EXPORT_ROOT%` |
| `ue_asset` | `.uasset/.umap` 与 UE Object Path | `%UE_PROJECT_ROOT%/Content`、`/Game/...` |
| `run_evidence` | 运行报告、日志、截图、视频和人工决定 | `%OUTPUT_ROOT%/<producer>/<run_id>/` |
| `render_run` | 节点 attempt、媒体、GT、Sidecar、状态和哈希 | 本地 `%OUTPUT_ROOT%/unreal_render/` 或服务器 Run Root |
| `delivery` | 已发布、不可原地覆盖的统一数据包 | `delivery/<batch_id>/<release_id>/` |

目录名 `artifacts` 只表示某个生产者的输出分区，不是保留等级。`external_binary` 和 `ue_asset` 即使不在 Git/`%OUTPUT_ROOT%`，也必须由 Registry/Manifest、哈希和对象路径追溯。

## 3. Workflow 输出目录

| 输出 ID | Workflow | 最小逻辑内容 | 主要存储 | 生产所有者 | 当前状态所有者 |
| --- | --- | --- | --- | --- | --- |
| `OUT-WF00-SESSION` | `WF-00` | 环境范围、版本、通道结果、失败原因、允许进入阶段 | `run_evidence` | [环境与会话](../environment/ENVIRONMENT_AND_SESSION.md) | [WF-00 状态](../../project_management/status/workflows/WF-00.md) |
| `OUT-WF10-BATCH-SPEC` | `WF-10` | Batch ID、轴、兼容域、媒体/交付规格、规模、停止与降级条件 | `versioned_registry` | [批次规格](../dataset/BATCH_SPECIFICATION.md) | [WF-10 状态](../../project_management/status/workflows/WF-10.md) |
| `OUT-WF20-ASSET-MATRIX` | `WF-20` | 生产资产 ID、源哈希、兼容域、排除项、矩阵与完整性报告 | `versioned_registry` | [资产矩阵冻结](../dataset/ASSET_MATRIX_FREEZE.md) | [WF-20 状态](../../project_management/status/workflows/WF-20.md) |
| `OUT-WF30-CC-ASSETS` | `WF-30` | 规范 `.ccProject`、Look Manifest、CC Gate、视觉决定 | `external_binary` + `run_evidence` | [CC 组装与验收](../character_creator/ASSEMBLY_AND_ACCEPTANCE.md) | [WF-30 状态](../../project_management/status/workflows/WF-30.md) |
| `OUT-WF40-TRANSFER-BUNDLE` | `WF-40` | CC Bundle、UE FullReference、Object Path 映射和导入聚合报告 | `cc_export_bundle` + `ue_asset` + `run_evidence` | [CC→UE FullReference](../transfer/CC_TO_UE_FULLREFERENCE.md) | [WF-40 状态](../../project_management/status/workflows/WF-40.md) |
| `OUT-WF50-RUNTIME-ACCEPTANCE` | `WF-50` | 接受的 Look/Action/Expression、运行时资产、兼容警告和 Gate 报告 | `ue_asset` + `run_evidence` | [角色运行时](../unreal/CHARACTER_RUNTIME.md) | [WF-50 状态](../../project_management/status/workflows/WF-50.md) |
| `OUT-WF60-SEQUENCE-TEMPLATE` | `WF-60` | Scene/Camera/Anchor Registry、Sequence、MRQ Profile 和布局证据 | `versioned_registry` + `ue_asset` + `run_evidence` | [场景、相机与 Sequence](../unreal/SCENE_CAMERA_SEQUENCE.md) | [WF-60 状态](../../project_management/status/workflows/WF-60.md) |
| `OUT-WF70-JOB-GRAPH` | `WF-70` | Source Manifest、Assets/Domains/Nodes/Edges/Chains、Render Jobs、Prompt 和报告 | `versioned_registry` + `%OUTPUT_ROOT%` authoritative 根 | [配置图与链](../dataset/CONFIG_GRAPH_AND_CHAINS.md) | [WF-70 状态](../../project_management/status/workflows/WF-70.md) |
| `OUT-WF80-NODE-MEDIA` | `WF-80` | 节点 attempt、媒体、GT/Sidecar、状态、日志、哈希和完成清单 | `render_run` | [渲染执行](../rendering_release/RENDER_EXECUTION.md) | [WF-80 状态](../../project_management/status/workflows/WF-80.md) |
| `OUT-WF90-DATASET-RELEASE` | `WF-90` | 顺序编号视频、链/双语 Turn、追溯 Manifest、QA 和发布决定 | `delivery` | [数据集封装](../rendering_release/DATASET_PACKAGE.md) | [WF-90 状态](../../project_management/status/workflows/WF-90.md) |

### 3.1 `OUT-WF00-SESSION`

该 ID 表示一次具有明确范围的会话预检结论，不表示永久环境认证：

| 部分 | 最小内容 | 作用 | 当前位置所有者 |
| --- | --- | --- | --- |
| 会话范围 | 机器、项目、应用、版本、所需通道和路径映射 | 定义本次结论能覆盖什么，防止跨进程/机器继承 | [WF-00 Status](../../project_management/status/workflows/WF-00.md#当前输出与证据) |
| 通道结果 | 本地测试、CC Bridge、UE MCP/Remote Execution、服务器环境的适用状态 | 证明依赖通道当前可执行，而不只是配置存在 | [WF-00 Status](../../project_management/status/workflows/WF-00.md#验证状态) |
| 失败与恢复 | 阻塞窗口、权限、路径/版本冲突、日志和恢复入口 | 支撑安全恢复并避免重复有副作用任务 | [恢复手册](../validation/RECOVERY.md) |
| Gate 结论 | 允许进入的 Workflow、非必需通道和失效条件 | 把检测结果转换为执行边界 | 所有本轮下游 Workflow |

应用重启、机器切换或通道变化后结果失效。生产命令由 [环境 Technical](../environment/ENVIRONMENT_AND_SESSION.md) 负责；重复无变化的本地检查可为 `disposable`，首次服务器/关键故障证据按 Status 和 Retention Policy 保留。主要下游是本轮被允许继续的所有 Workflow。

### 3.2 `OUT-WF10-BATCH-SPEC`

该 ID 是多份权威共同构成的受控规格，不是某个孤立 JSON：

| 部分 | 最小内容 | 作用 | 当前位置所有者 |
| --- | --- | --- | --- |
| Plan Requirements | 目标、完成条件、风险和允许降级 | 说明批次为什么生产以及何时完成 | [Plan Index](../../project_management/plans/PLAN_INDEX.md) |
| Batch Status | 批次 ID、冻结规格、执行进度、例外和下一 Gate | 提供人类可读的当前批次事实 | [WF-10 Status](../../project_management/status/workflows/WF-10.md#当前输出与证据) |
| Machine State | 当前批次、阶段、媒体参数、规模和输出指针 | 给检查器和编排器提供当前机器字段 | [`PROJECT_STATE.json`](../../project_management/status/PROJECT_STATE.json) |
| Schema/Sampling versions | 节点、链、文本、媒体和采样语义 | 让 `WF-20/WF-70/WF-80/WF-90` 对同一规格作一致解释 | [批次规格 Technical](../dataset/BATCH_SPECIFICATION.md) |
| Spec evidence | 跨文件一致性、单位、枚举和不包含项检查 | 支撑 `VAL-SPEC-01`，不能由任一单文件替代 | [WF-10 Status](../../project_management/status/workflows/WF-10.md#验证状态) |

当前没有通用 Batch Spec Builder。生产/验证方式由 [批次规格 Technical](../dataset/BATCH_SPECIFICATION.md) 负责；上述组成全部一致后才能通过 `GATE-10`。主要下游是 `WF-20` 的资产冻结、`WF-70` 的图编译、`WF-80` 的媒体执行和 `WF-90` 的发布 Gate。

### 3.3 `OUT-WF20-ASSET-MATRIX`

该 ID 把候选资产收敛为允许生产的稳定状态空间：

| 部分 | 最小内容 | 作用 | 当前位置所有者 |
| --- | --- | --- | --- |
| Production Registries | Identity/Look/Action/Expression/Scene/Camera ID、来源和哈希 | 避免后续按文件名或目录猜测资产身份 | [WF-20 Status](../../project_management/status/workflows/WF-20.md#当前输出与证据) |
| Compatibility/Exclusions | 性别、BodyFit、服装、动作、道具等允许组合与排除原因 | 阻止不兼容组合进入组装和图构建 | [资产矩阵 Technical](../dataset/ASSET_MATRIX_FREEZE.md) |
| Required Exports/Work Matrices | 必需 CC/UE 二进制、Object Path 和覆盖工作单 | 形成 `WF-30/WF-40/WF-50` 的确定输入 | [WF-20 Status](../../project_management/status/workflows/WF-20.md#当前输出与证据) |
| Integrity evidence | 计数、缺失、哈希、重复 ID、闭包和隐式默认检查 | 支撑 `VAL-MATRIX-01` 与 `GATE-20` | [WF-20 Status](../../project_management/status/workflows/WF-20.md#验证状态) |

外部二进制不复制进本输出，只由路径别名、稳定 ID 和哈希引用。生成与审计入口由 [资产矩阵 Technical](../dataset/ASSET_MATRIX_FREEZE.md) 负责。主要下游是 `WF-30` 角色组装、`WF-40` 转移、`WF-50` 运行时和 `WF-70` 图源。

### 3.4 `OUT-WF30-CC-ASSETS`

该 ID 保存 CC 端可重载源状态和接受结论，不包含最终 UE 导出 Bundle：

| 部分 | 最小内容 | 作用 | 当前位置所有者 |
| --- | --- | --- | --- |
| Canonical CC projects | 每个被接受 Look 的规范 `.ccProject` | 保留可修改、可重导出的 CC 源状态 | [WF-30 Status](../../project_management/status/workflows/WF-30.md#当前输出与证据) |
| Look Manifest | Look ID、BodyFit、Identity、Appearance、Outfit、来源与哈希 | 证明项目与冻结矩阵一致并驱动 `WF-40` | [WF-30 Status](../../project_management/status/workflows/WF-30.md#当前输出与证据) |
| Machine reports | Inventory、可重载、路径、计数和哈希结果 | 捕获肉眼不可见的结构错误 | [CC 组装 Technical](../character_creator/ASSEMBLY_AND_ACCEPTANCE.md) |
| Visual decisions/failures | 眼口、材质、毛发、服装动态证据、接受风险和失败原因 | 支撑 `VAL-CC-01/02` 与按 Look 恢复 | [WF-30 Status](../../project_management/status/workflows/WF-30.md#验证状态) |

FBX/JSON/纹理属于 `OUT-WF40-TRANSFER-BUNDLE`，不得与本输出混淆。组装、验收和当前首批自动化边界由 [CC 组装 Technical](../character_creator/ASSEMBLY_AND_ACCEPTANCE.md) 负责。主要下游是 `WF-40` 的 Bundle 导出和故障重导出。

### 3.5 `OUT-WF40-TRANSFER-BUNDLE`

该 ID 表示一次可追溯的 CC→UE 转移结果，不表示单个目录。四部分必须共同解释，任何一部分都不能单独宣称 `GATE-40` 已通过：

| 部分 | 最小内容 | 作用 | 当前位置所有者 |
| --- | --- | --- | --- |
| `cc_export_bundle` | 每 Look FBX、JSON、纹理/`.fbm`、源哈希与 Bundle 标识 | 提供不可变导入源和确定性重导入依据 | [WF-40 Status](../../project_management/status/workflows/WF-40.md#当前输出与证据) |
| `ue_asset` | Vendor 根下的 FullReference 资产及规范同性 Skeleton | 提供 `WF-50`–`WF-80` 实际消费的 UE 角色 | [WF-40 Status](../../project_management/status/workflows/WF-40.md#当前输出与证据) |
| source/Object Path mapping | Look ID、Bundle 文件、UE Object Path、Skeleton 和导入版本映射 | 支撑正反向追溯、单 Look 重试和发布引用 | [资产追溯](../transfer/ASSET_TRACEABILITY.md) |
| `run_evidence` | 每 Look 导入验证、聚合报告、失败分类和 Gate 结论 | 支撑 `VAL-TRANSFER-01`，不能由资产存在性替代 | [WF-40 Status](../../project_management/status/workflows/WF-40.md#验证状态) |

生产命令和字段由 [FullReference Technical](../transfer/CC_TO_UE_FULLREFERENCE.md) 负责；当前接受版本由 WF-40 Status 负责；物理证据保留由 [输出盘点与保留](./INVENTORY_AND_RETENTION.md) 负责。主要下游是 `WF-50` 的运行时验收、`WF-60` 的 Sequence 绑定与 `WF-80` 的节点渲染；它们只消费已通过 Gate 的 UE FullReference 和追溯信息，不直接把 CC Bundle 当作运行时资产。

### 3.6 `OUT-WF50-RUNTIME-ACCEPTANCE`

该 ID 表示经过播放和视觉 Gate 的 UE 角色表演能力，不只是若干 `.uasset`：

| 部分 | 最小内容 | 作用 | 当前位置所有者 |
| --- | --- | --- | --- |
| Performance assets | 规范 Body Motion、Face Clip/Composite 和必要可逆材质补丁 | 给 Sequence/Render Job 提供可直接绑定资产 | [WF-50 Status](../../project_management/status/workflows/WF-50.md#当前输出与证据) |
| Accepted combination matrix | Look × Action × Expression、Skeleton 和窗口映射 | 阻止未验证组合进入渲染 | [角色运行时 Technical](../unreal/CHARACTER_RUNTIME.md) |
| Runtime policies | Root Motion/InPlace、Padding、曲线/骨骼分层和条件能力边界 | 保持运行时、图和渲染器解释一致 | [动作/表情 Technical](../unreal/ANIMATION_EXPRESSION_MORPH.md) |
| Warnings/Gate evidence | 已接受穿模风险、Pilot 限制、机器报告和视觉结论 | 支撑 `VAL-UE-01..03` 与 `GATE-50` | [WF-50 Status](../../project_management/status/workflows/WF-50.md#验证状态) |

模块化 Pilot 和可编辑 Morph 只有在对应条件验证通过时才进入本输出。当前第一批消费的是烘焙 FullReference 与批准 Composite。主要下游是 `WF-60` 的 Sequence/Camera 绑定、`WF-70` 的图源和 `WF-80` 的节点渲染。

### 3.7 `OUT-WF60-SEQUENCE-TEMPLATE`

该 ID 把场景空间、镜头语义和时序/渲染配置锁为可重建模板：

| 部分 | 最小内容 | 作用 | 当前位置所有者 |
| --- | --- | --- | --- |
| Scene/Anchor Registry | Map、角色锚点、朝向和安全范围 | 让所有 Look 使用同一空间语义 | [WF-60 Status](../../project_management/status/workflows/WF-60.md#当前输出与证据) |
| Camera Registry | Camera ID、变换、镜头和构图规则 | 把相机变成稳定节点轴 | [场景 Technical](../unreal/SCENE_CAMERA_SEQUENCE.md) |
| UE Sequence/Bindings | DataMake Sequence、Actor Binding、动作窗口和 Camera Cut | 给节点执行器提供可控 staging 模板 | [WF-60 Status](../../project_management/status/workflows/WF-60.md#当前输出与证据) |
| MRQ Profile | FPS、帧范围、分辨率和渲染参数 | 保持本地和服务器媒体契约一致 | [渲染 Technical](../rendering_release/RENDER_EXECUTION.md) |
| Layout evidence | Object Path 审计、截图/视频和人工结论 | 支撑 `VAL-SCENE-01`，不能由 Sequence 存在性替代 | [WF-60 Status](../../project_management/status/workflows/WF-60.md#验证状态) |

当前路径由 WF-60 Status 指定；构建、审计和恢复由 [场景 Technical](../unreal/SCENE_CAMERA_SEQUENCE.md) 负责。主要下游是 `WF-70` 的 Camera/Scene 节点字段和 `WF-80` 的 staging/MRQ 执行。

### 3.8 `OUT-WF70-JOB-GRAPH`

该 ID 是数据语义根，Prompt 与 Render Job 都从它派生：

| 部分 | 最小内容 | 作用 | 当前位置所有者 |
| --- | --- | --- | --- |
| Source/Assets/Domains | 输入版本与哈希、资产快照和兼容域 | 锁定图构建事实并支持确定性重建 | [WF-70 Status](../../project_management/status/workflows/WF-70.md#当前输出与证据) |
| Nodes/Edges | 唯一视频状态和单轴编辑关系 | 定义可渲染状态空间及监督关系 | [配置图 Technical](../dataset/CONFIG_GRAPH_AND_CHAINS.md) |
| Chains/labels | 多轮路径、策略和可重算事实标签 | 形成多轮样本并保留路径语义 | Prompt、QA 和最终交付 |
| Render Jobs | 按 `node_id` 去重的渲染任务与初始状态 | 避免同一节点因多条链重复渲染 | `WF-80` |
| Prompt Layer | Manifest、Turn/Dialog、身份描述和媒体 URI | 把原子边转换成训练文本 | `WF-90` 与训练加载器 |
| Build/review evidence | 计数、连通性、配额、引用、文本和代表链报告 | 支撑 `VAL-GRAPH-01/VAL-TEXT-01`，不代表媒体完成 | [WF-70 Status](../../project_management/status/workflows/WF-70.md#验证状态) |

当前接受图根与文本版本由 WF-70 Status 指定；精确生成器和文件结构由 [配置图](../dataset/CONFIG_GRAPH_AND_CHAINS.md) 与 [Prompt](../dataset/PROMPT_LAYER.md) Technical 负责。主要下游是 `WF-80` 的去重 Render Jobs 和 `WF-90` 的 Graph/Text 交付层。

### 3.9 `OUT-WF80-NODE-MEDIA`

该 ID 表示可续跑的节点级渲染结果；单个 MP4 不满足此契约：

| 部分 | 最小内容 | 作用 | 当前位置所有者 |
| --- | --- | --- | --- |
| Run/Attempt state | Manifest、输入锁、Lease、状态、日志、机器/版本、Editor invocation/supervisor 和错误分类 | 支撑断点续跑、同配置重试和单 UE 多节点批次恢复 | [WF-80 Status](../../project_management/status/workflows/WF-80.md#当前输出与证据) |
| Accepted node media | `media/nodes/<node_id>/` 下唯一视频/帧 | 让多条链复用同一语义节点 | `WF-90`、Turn/Dialog 和训练数据 |
| GT/Sidecar | 节点配置、UE 绑定、媒体规格、版本、attempt 和哈希 | 连接确定性配置与真实像素 | QA、发布和复现 |
| Media Manifest/status | Node 到 URI、字节数、SHA-256、接受/失败状态和完成清单 | 支撑零悬空引用和只重跑失败节点 | `WF-90` |
| Smoke/benchmark evidence | 本地代表链、服务器基准、首帧/确定性报告和视觉抽检 | 在全量运行前发现系统性错误 | `VAL-RENDER-01/VAL-SERVER-01` |

第一批原始 Run Root、Smoke 和 benchmark 输出已在最终包通过后清理。当前 640 个 accepted 媒体位于 `%OUTPUT_ROOT%/delivery/first_batch_candidate_20260830_v002/dataset_v1/videos/`；输入锁、冻结 profile、640 节点结果、媒体 Manifest 和生产 checkpoint 位于同一候选根的 `release_evidence/render_run/`。执行命令、历史 Run ID 和当前边界由 [渲染 Technical](../rendering_release/RENDER_EXECUTION.md) 负责，准确状态由 [WF-80 Status](../../project_management/status/workflows/WF-80.md) 负责。主要下游是 `WF-90` 发布验证以及 Lance 训练数据构建。

### 3.10 `OUT-WF90-DATASET-RELEASE`

该 ID 是一个不可原地覆盖的统一交付包，不是 `%OUTPUT_ROOT%` 中散布文件的集合：

| 部分 | 最小内容 | 作用 | 当前位置所有者 |
| --- | --- | --- | --- |
| `manifest.json` | Batch/Release、输入哈希、Node 配置、`编号 -> node_id`、媒体/Sidecar 哈希与 QA | 提供接收方单一顶层入口和追溯映射 | [WF-90 Status](../../project_management/status/workflows/WF-90.md#当前输出与证据) |
| `chains.json` | 链事实、Node 序列、正式双语 Prompt/Standalone Prompt、Grounding 与媒体路径 | 保存多轮编辑监督语义 | 数据加载器和训练系统 |
| `chains_simple.json` | `chain_index=1..N`、Hash `chain_id` 和每轮输入视频/双语指令/输出视频 | 提供不含验证元数据的直接训练视图，同时保留完整链追溯 | 训练数据加载器 |
| `videos/<编号>.mp4` | 从 1 连续编号、每个内部 `node_id` 唯一一份的 accepted 媒体 | 解析所有 Turn 输入/输出并复用端点 | 模型训练与评估 |

当前完整发布位于 `%OUTPUT_ROOT%/delivery/first_batch_candidate_20260830_v002/dataset_v1/`，Manifest 状态为 `released`；目录保留候选 ID 以维持身份与既有引用，发布决定和独立候选态/发布态报告位于相邻 `release_evidence/release_qa/`。旧未版本化候选和两链格式样例已删除。目标结构、Gate 和不可变性由 [数据集封装 Technical](../rendering_release/DATASET_PACKAGE.md) 负责，准确状态由 WF-90 Status 指定。主要下游是数据接收方、训练/评估加载器和独立复核流程。

## 4. 全局维护输出

| 输出 ID | 内容 | 生产所有者 | 默认保留 |
| --- | --- | --- | --- |
| `OUT-GLOBAL-VALIDATION-EVIDENCE` | 跨阶段人工审查 Run 与恢复证据 | [视觉审查](../validation/VISUAL_REVIEW.md) | 由其绑定的 Gate 决定 |
| `OUT-GLOBAL-DOC-AUDIT` | 文档检查 JSON、测试结果和人工审计摘要 | [文档体系审计](../validation/DOCUMENTATION_VALIDATION.md) | 最近一次通过结果为 `retained_evidence` |
| `OUT-GLOBAL-SCRIPT-CATALOG` | 脚本生命周期、哈希和 Technical 所有者目录 | [脚本生命周期](../implementation/SCRIPT_LIFECYCLE.md) | `authoritative` |
| `OUT-GLOBAL-OUTPUT-INVENTORY` | 输出保留策略和非破坏性盘点 | [输出盘点与保留](./INVENTORY_AND_RETENTION.md) | `authoritative` |

### 4.1 `OUT-GLOBAL-VALIDATION-EVIDENCE`

| 部分 | 最小内容 | 作用 | 当前位置所有者 |
| --- | --- | --- | --- |
| Validation Run | 绑定的 `VAL-*`、Workflow/Batch、输入哈希、运行结果和时间 | 证明某个稳定 Gate 在确定范围内执行过 | 对应 [Workflow Status](../../project_management/status/workflows/README.md) |
| Machine evidence | 报告、日志、结构检查和失败分类 | 支撑可重复判定与恢复 | [Validation Catalog](../validation/VALIDATION_CATALOG.md) |
| Visual/human decision | 审查媒体、抽样范围、结论、例外和签署者 | 覆盖机器检查无法判断的视觉质量 | [视觉审查](../validation/VISUAL_REVIEW.md) |

主要下游是对应 Workflow Exit Gate、批次状态、发布 QA 和故障恢复。证据是否保留由其绑定 Gate 的当前状态决定，不因位于 `artifacts` 自动删除或晋升。

### 4.2 `OUT-GLOBAL-DOC-AUDIT`

| 部分 | 最小内容 | 作用 | 当前位置所有者 |
| --- | --- | --- | --- |
| Audit Manifest | 文档根、实现/Git 版本、输入哈希、`supersedes` 和运行范围 | 标识一次不可混淆的文档审计 | [文档体系审计](../validation/DOCUMENTATION_VALIDATION.md) |
| Checker result | 独立子系统、跨层契约、错误、警告和统计 JSON | 证明结构、所有权和导航满足机器规则 | [`PROJECT_STATE.json`](../../project_management/status/PROJECT_STATE.json) 的 `VAL-DOC-01` |
| Test result | 文档、Dataset 和 UE 脚本测试摘要 | 防止只通过链接检查却破坏实现契约 | [项目状态](../../project_management/status/PROJECT_STATUS.md) |

主要下游是文档变更验收、维护 Skill、交接和下一次审计的替代链。最近一次通过且仍匹配工作树的 Run 为 `retained_evidence`。

### 4.3 `OUT-GLOBAL-SCRIPT-CATALOG`

| 部分 | 最小内容 | 作用 | 当前位置所有者 |
| --- | --- | --- | --- |
| Script entries | 路径、领域、生命周期、活动批次、Technical owner、字节数和 SHA-256 | 让每个脚本可反向定位到解释其组合方式的 Technical | [脚本生命周期](../implementation/SCRIPT_LIFECYCLE.md) |
| Coverage summary | 扫描根、排除项和生命周期计数 | 发现未登记、失效或误分类脚本 | [`SCRIPT_CATALOG.json`](../../../../../../00_engine/scripts/SCRIPT_CATALOG.json) |
| Builder provenance | Catalog Builder 版本和生成时间 | 证明目录与当前代码树匹配 | [脚本生命周期](../implementation/SCRIPT_LIFECYCLE.md) |

主要下游是 Technical 子系统审计、Workflow 实现导航、代码清理和交接。Catalog 是生成的 `authoritative` 索引，不能手工修正哈希。

### 4.4 `OUT-GLOBAL-OUTPUT-INVENTORY`

| 部分 | 最小内容 | 作用 | 当前位置所有者 |
| --- | --- | --- | --- |
| Retention Policy | 路径前缀、产物类型、Technical owner、输出契约和保留决定 | 定义输出类别和审查后的保留语义 | [`RETENTION_POLICY.json`](../../../../../../00_engine/outputs/RETENTION_POLICY.json) |
| Physical Inventory | 当前直接输出范围、大小、时间、匹配规则、owner 和状态 | 把磁盘目录映射回文档体系 | [`OUTPUT_INVENTORY.json`](../../../../../../00_engine/outputs/OUTPUT_INVENTORY.json) |
| Unclassified report | 未匹配、失效或冲突规则 | 阻止未知输出被自动删除 | [输出盘点与保留](./INVENTORY_AND_RETENTION.md) |

主要下游是非破坏性清理、存储规划、当前证据定位和发布保留清单。Inventory 是只读盘点；`unclassified` 始终受保护。

## 5. Run Root 契约

产生可重复运行产物的能力使用唯一 `run_id`，推荐结构：

```text
<run_root>/
  manifest.json
  inputs.lock.json
  status.json
  result.json
  logs/
  evidence/
  media/
  attempts/<attempt_id>/
```

`manifest.json` 至少包含：`output_contract_id`、`producer`、`workflow_id`、`validation_ids`、`plan_id`、`batch_id`、`run_id`、实现/Git 版本、输入哈希、输出清单、开始/结束时间、验证状态、保留建议和 `supersedes`。不适用字段写 `null` 并说明原因，不能静默省略追溯键。

## 6. 晋升、失效与不可变性

1. 新运行先写 attempt/临时目录；通过结构与适用 `VAL-*` 后才晋升为接受产物。
2. 产物存在不等于被接受；Status 必须指向当前版本和证据。
3. 输入、实现或契约变化时创建新版本；旧产物通过 `supersedes` 关联，不原地覆盖。
4. `authoritative`、`retained_evidence`、`superseded`、`disposable`、`unclassified` 是保留状态，不是质量状态。
5. `unclassified` 默认受保护。只有完成替代映射和证据审查后，才能进入清理候选。

## 7. 使用方法

- 顺向执行：`Workflow -> OUT-* -> 生产 Technical -> 物理产物 -> Workflow/Batch Status`。
- 反向调查：`物理路径 -> OUTPUT_INVENTORY.json -> owner/output_contract_id -> Technical/Workflow/Status`。
- 新增输出：先在生产 Technical 中定义，再登记本目录和 Retention Policy；最后重建 Inventory 并执行 `VAL-DOC-01`。
