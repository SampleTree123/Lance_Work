# DataMake Character Factory

> 文档 ID：`MASTER`
> 文档类型：`master`
> 生命周期：`current`
> 权威范围：角色工厂从批次定义到数据集发布的长期流程、文档导航和信息边界
> 最近核验：2026-10-05（执行中唯一计划与显式结项空闲规则）

## 目录

1. [项目定义](#1-项目定义)
2. [如何使用本文](#2-如何使用本文)
3. [核心边界与术语](#3-核心边界与术语)
4. [文档体系](#4-文档体系)
5. [端到端生产流程](#5-端到端生产流程)
6. [状态、计划、决定与历史](#6-状态计划决定与历史)
7. [从哪里开始](#7-从哪里开始)
8. [维护原则](#8-维护原则)

## 1. 项目定义

本项目使用 Character Creator、Unreal Engine 和确定性数据生成脚本，生产可追溯的短视频多轮编辑数据。角色身份、BodyFit、外观、服装、动作、表情、场景、相机、随机种子、媒体、编辑链和文本指令必须能够回溯到机器配置、源资产版本、验证结果和最终交付清单。

文档描述的是一套可重复运行的生产系统，而不是某一次实验记录。当前批次的数量、冻结资产、执行进度和唯一下一步统一从 [项目状态](./project_management/status/PROJECT_STATUS.md) 进入；长期流程只在本文和 [`workflow/`](./workflow/README.md) 中定义。

当前系统仍在建设中。已有能力和未完成边界必须按状态文档理解，不能由历史截图、旧计划或单次成功推断。

## 2. 如何使用本文

首次接手按以下顺序阅读：

1. 本文：理解项目、目录和完整流程。
2. [项目状态](./project_management/status/PROJECT_STATUS.md)：确认现在做到哪里、当前计划和下一步。
3. 对应的 [`WF-*`](./workflow/README.md)：确认该阶段何时执行、输入输出和 Gate。
4. Workflow 指向的 [`technical/`](./technical/README.md) 文档：获得脚本、配置、命令、输出和恢复细节。
5. 对应状态文档：确认该能力在当前机器、项目或批次中的真实成熟度。

最短导航规则是：

```text
Master -> Current Status -> Workflow
                           -> Technical（怎么实现）
                           -> Validation（怎样证明）
                           -> Output（产生什么）
                           -> Registry（机器真值在哪里）
                           -> Workflow / Batch Status（当前是否接受）
```

查找当前批次的数据输出时不需要逐个翻阅全部 Workflow，使用以下专用路由：

```text
Master
  -> Project Status（找到活动批次）
  -> Active Batch Status / 权威机器产物（找到当前物理路径与完成状态）
     -> Dataset Technical（图、链、Prompt 和 Render Job 格式）
     -> Render Technical（节点媒体、Sidecar 和 Run Root 格式）
     -> Package Technical（最终统一交付包格式）
     -> Output Contract（确认逻辑组成、所有者和保留语义）
```

当前活动批次可直接从 [项目状态的活动对象](./project_management/status/PROJECT_STATUS.md#活动对象) 进入；该批次的“权威机器产物”表是查找第一批数据当前位置的唯一人类入口。最终交付包在 `WF-90` 通过前可能尚不存在，不能把图根或本地 Smoke 误称为完整数据集。

发生冲突时，先停止受影响阶段，再按 [治理规则](./GOVERNANCE.md#2-冲突裁决) 判断事实维度：运行证据描述实际行为，机器配置决定精确输入，长期契约决定是否合规，Status 决定当前是否允许生产。任何一项不能替另一项掩盖差异。

## 3. 核心边界与术语

### 3.1 系统边界

| 区域 | 主要职责 | 详细入口 |
| --- | --- | --- |
| `%LANCE_ROOT%` | Git 管理的代码、配置、文档和轻量清单 | [路径别名](./reference/PATH_ALIASES.md) |
| `%CC_INSTALL_ROOT%` | Character Creator 程序环境 | [环境与会话](./technical/environment/ENVIRONMENT_AND_SESSION.md) |
| `%CC_ASSET_ROOT%` | CC 模板、Custom 资产和规范项目 | [CC 技术索引](./technical/character_creator/README.md) |
| `%UE_PROJECT_ROOT%` | UE 主项目、Vendor 资产和 DataMake 自有资产 | [UE 技术索引](./technical/unreal/README.md) |
| `%OUTPUT_ROOT%` | 本地运行产物和证据；不自动等于正式交付 | [Output 子系统](./technical/output/README.md) |
| 服务器工作层 | 正式批量渲染、重试和交付构建 | [渲染与发布](./technical/rendering_release/README.md) |

文档中使用路径别名，不在多个文件重复维护机器绝对路径。UE Object Path、资产 ID 和批次 ID 是数据契约的一部分，不等同于 Windows 文件路径。

### 3.2 三种不同状态

- **系统能力状态**：流水线是否具备某项能力，例如 CC 到 UE 导入是否可复现。
- **Workflow 状态**：某个长期阶段当前通过了什么 Gate、还有什么缺口。
- **批次状态**：某一批冻结了哪些资产、已经生成多少节点、媒体是否完成。

三者不得写在同一个大段落中互相替代。状态入口见第 6 节。

### 3.3 关键对象

- `BodyFit`：受控身体体型模板，不等同于角色身份。
- `Identity`：面部身份与其可追溯描述。
- `Look`：一个可直接渲染的角色外观组合，通常包含身份、体型、服装和外观。
- `Node`：所有可编辑因素均确定的唯一视频状态。
- `Atomic Edge`：只改变一个允许编辑轴的两个节点之间的边。
- `Chain`：连续原子边组成的多轮编辑样本。
- `Gate`：阶段退出条件；文件存在或脚本退出 0 不自动等于 Gate 通过。

完整定义见 [术语表](./reference/GLOSSARY.md)。

## 4. 文档体系

文档树按职责拆分，不按软件名称简单堆放。每个子系统先能独立回答自己的问题，再通过稳定 ID 与其他层连接。

### 4.1 [`workflow/`](./workflow/README.md)

定义 `WF-00` 到 `WF-90` 的唯一长期生产顺序。每份 Workflow 只回答何时进入、需要什么、执行哪些逻辑步骤、产生哪个 `OUT-*`、必须通过哪个 `VAL-*`、Exit Gate 是什么，以及失败后回到哪里。

### 4.2 [`technical/`](./technical/README.md)

保存可复现实现，包括环境、脚本生命周期、CC、Bridge、传输、UE、数据图、渲染和发布。这里拥有代码/配置组合、准确命令、领域输出结构、验证实现、恢复和限制；一个能力可以由多个脚本共同完成。

### 4.3 [Validation](./technical/validation/README.md)

Validation 是独立控制面，虽然物理上位于 `technical/validation/`。它拥有稳定 `VAL-*`、触发条件、最低证据、通过/失效语义和结果落点；领域 Technical 只拥有如何执行验证。遇到 Gate、视觉检查或恢复问题从这里进入。

### 4.4 [Output](./technical/output/README.md)

Output 是独立控制面，拥有稳定 `OUT-*`、存储类别、Run Root、Manifest、晋升、盘点和保留规则。领域 Technical 说明怎样产生输出，Status 指向当前接受版本；目录名 `artifacts` 本身不表示重要性或可删除性。

### 4.5 [`project_management/`](./project_management/README.md)

- [`status/`](./project_management/status/README.md)：当前项目、Workflow 和活动批次事实。
- [`plans/`](./project_management/plans/README.md)：未来需求及落实状态；执行中恰好一个 current 主计划，显式结项空闲状态没有 current。
- [`decisions/`](./project_management/decisions/README.md)：长期架构和语义 ADR。
- [`history/`](./project_management/history/README.md)：关闭计划、里程碑和报告，不决定当前行为。
- [`templates/`](./project_management/templates/README.md)：未来新文档的结构契约。

### 4.6 [`reference/`](./reference/README.md)

只解释稳定术语、状态词、路径别名和跨机器 URI。它不保存机器 Registry、当前进度或执行步骤。

### 4.7 [`registry/`](./registry/README.md)

按对象反向定位当前机器权威、适用范围、Technical 所有者和消费 Workflow。已知阶段时仍从 Workflow/Technical 顺向执行；只有已知文件或资产名、不知道归属时才从 Registry 开始。

### 4.8 Master、Governance 与活跃树之外

- 本文是人类顺向入口；[`GOVERNANCE.md`](./GOVERNANCE.md) 是全树维护、冲突和审计规则。
- `00_engine/scripts/` 保存代码、Schema 和机器 Registry；准确组合由 Technical 解释，反查入口是 Registry 与 Script Catalog。
- `00_engine/character_creator_bridge/`、`00_engine/visualization_portal/` 是实现组件，由相应 Technical 文档拥有。
- `00_engine/outputs/` 是运行产物根；物理盘点由 Output Inventory 管理，当前接受版本由 Status 指向。
- `20_planning/data_design/schema/` 和 `sampling/` 保存跨批次数据契约，主要由 `WF-10/WF-70` 消费。
- `%CC_ASSET_ROOT%`、`%CC_EXPORT_ROOT%` 和 `%UE_PROJECT_ROOT%` 保存 Git 外二进制资产，必须通过 Registry/Manifest/哈希追溯。
- 重构前原文和完整快照位于活跃树之外，只通过快照 Manifest 审计，不能作为当前入口。

这些外挂目录必须在使用它们的 Workflow 和 Technical 中再次说明输入、输出与所有权；本节只解释边界，不替代实现文档。

## 5. 端到端生产流程

完整流程使用十进制编号，为未来插入阶段保留空间：

| 阶段 | 目的 | 实现与主要机器区域 | 验证 / 输出 | 当前状态 |
| --- | --- | --- | --- | --- |
| [`WF-00`](./workflow/WF-00-ENVIRONMENT-PREFLIGHT.md) | 验证机器、应用、通信和路径 | [环境](./technical/environment/README.md)、[Bridge](./technical/bridge/README.md)；本机/服务器/CC/UE | `VAL-ENV-01`, `VAL-BRIDGE-01` / `OUT-WF00-SESSION` | [WF-00](./project_management/status/workflows/WF-00.md) |
| [`WF-10`](./workflow/WF-10-BATCH-DEFINITION.md) | 定义批次、编辑轴和交付规格 | [批次规格](./technical/dataset/BATCH_SPECIFICATION.md)；Plan、Batch Status、Schema | `VAL-SPEC-01` / `OUT-WF10-BATCH-SPEC` | [WF-10](./project_management/status/workflows/WF-10.md) |
| [`WF-20`](./workflow/WF-20-ASSET-MATRIX-FREEZE.md) | 冻结资产、兼容域和生产矩阵 | [资产矩阵](./technical/dataset/ASSET_MATRIX_FREEZE.md)、[Registry](./registry/README.md)；CC/服装/动作源与脚本 Registry | `VAL-MATRIX-01` / `OUT-WF20-ASSET-MATRIX` | [WF-20](./project_management/status/workflows/WF-20.md) |
| [`WF-30`](./workflow/WF-30-CC-BUILD-ACCEPT.md) | 在 CC 组装、验收并保存角色 | [CC](./technical/character_creator/README.md)、[Bridge](./technical/bridge/README.md)；`%CC_ASSET_ROOT%`, `%OUTPUT_ROOT%` | `VAL-CC-01`, `VAL-CC-02` / `OUT-WF30-CC-ASSETS` | [WF-30](./project_management/status/workflows/WF-30.md) |
| [`WF-40`](./workflow/WF-40-CC-UE-TRANSFER.md) | 导出 Bundle 并导入 UE | [Transfer](./technical/transfer/README.md)；`%CC_EXPORT_ROOT%`, `%UE_PROJECT_ROOT%` | `VAL-TRANSFER-01` / `OUT-WF40-TRANSFER-BUNDLE` | [WF-40](./project_management/status/workflows/WF-40.md) |
| [`WF-50`](./workflow/WF-50-UE-RUNTIME-PERFORMANCE.md) | 验证 UE 角色、动作、表情和可选模块化能力 | [UE Runtime](./technical/unreal/README.md)；UE Vendor/DataMake | `VAL-UE-01`, `VAL-UE-02`, `VAL-UE-03` / `OUT-WF50-RUNTIME-ACCEPTANCE` | [WF-50](./project_management/status/workflows/WF-50.md) |
| [`WF-60`](./workflow/WF-60-SCENE-CAMERA-SEQUENCE.md) | 固定场景、锚点、相机和 Sequence | [Scene/Sequence](./technical/unreal/SCENE_CAMERA_SEQUENCE.md)；UE DataMake 与审查输出 | `VAL-SCENE-01` / `OUT-WF60-SEQUENCE-TEMPLATE` | [WF-60](./project_management/status/workflows/WF-60.md) |
| [`WF-70`](./workflow/WF-70-GRAPH-CHAIN-PROMPT-JOBS.md) | 编译节点、边、链、Prompt 和作业 | [Dataset](./technical/dataset/README.md)；`%DATASET_SCRIPT_ROOT%`, `%OUTPUT_ROOT%` | `VAL-GRAPH-01`, `VAL-TEXT-01` / `OUT-WF70-JOB-GRAPH` | [WF-70](./project_management/status/workflows/WF-70.md) |
| [`WF-80`](./workflow/WF-80-RENDER-EXECUTION.md) | 本地 Smoke、服务器预检和可续跑渲染 | [Render/Server](./technical/rendering_release/README.md)；UE、服务器 Run Root | `VAL-RENDER-01`, `VAL-SERVER-01` / `OUT-WF80-NODE-MEDIA` | [WF-80](./project_management/status/workflows/WF-80.md) |
| [`WF-90`](./workflow/WF-90-QA-PACKAGE-RELEASE.md) | QA、GT、Sidecar、哈希和发布 | [Package/Release](./technical/rendering_release/DATASET_PACKAGE.md)；Delivery Root | `VAL-RELEASE-01` / `OUT-WF90-DATASET-RELEASE` | [WF-90](./project_management/status/workflows/WF-90.md) |

正常顺序为：

```text
WF-00 -> WF-10 -> WF-20 -> WF-30 -> WF-40
      -> WF-50 -> WF-60 -> WF-70 -> WF-80 -> WF-90
```

一个阶段可以在技术 Pilot 上通过而在某个批次上尚未完成。生产是否继续，必须同时检查 Workflow 能力状态和活动批次状态。

## 6. 状态、计划、决定与历史

### 6.1 当前状态

[项目状态](./project_management/status/PROJECT_STATUS.md) 是人类入口；[`PROJECT_STATE.json`](./project_management/status/PROJECT_STATE.json) 是关键状态字段的机器权威。Workflow 和批次状态从这里分流，不在 Master 中复制动态数字。

### 6.2 计划

[计划索引](./project_management/plans/PLAN_INDEX.md) 在执行中必须明确恰好一个 `current` 主计划。完成计划全部归档且尚无下一任务授权时，项目可处于显式 `idle_after_completed_plan`：机器状态 `current_plan_id=null`，零 current；排队计划继续 queued，不能为维持索引数量自动启动。规则见 [Governance 7.2](./GOVERNANCE.md#72-计划)。计划使用需求 ID，例如 `PLAN-.../R03`；受影响的 Workflow 状态必须说明需求已经完成、部分完成或尚未开始。

计划生命周期只使用：

```text
queued -> current -> completed -> history/completed_plans
           |-> paused -> current
           |-> cancelled -> history（保留取消原因）
```

尚未批准的想法属于 Backlog，不是 `proposed` 计划；`blocked` 是某项需求状态，不是计划生命周期。

完成计划移入 `history/completed_plans/`，不继续作为当前操作入口。

### 6.3 决定与历史

改变长期架构、数据语义或不可逆边界时创建 ADR。单次故障、某次批次结果和临时参数不创建 ADR，而进入技术恢复说明、批次状态或里程碑。历史只能证明发生过什么，不能覆盖当前规则。

## 7. 从哪里开始

- 新对话或应用重启：从 [`WF-00`](./workflow/WF-00-ENVIRONMENT-PREFLIGHT.md) 开始。
- 继续当前工作：先读 [项目状态](./project_management/status/PROJECT_STATUS.md) 的“唯一下一步”；当前下一阶段方案定义、已完成清理与暂停的第一批证据收口通过 [Plan 索引](./project_management/plans/PLAN_INDEX.md) 分流。
- 创建新数据批次：从 [`WF-10`](./workflow/WF-10-BATCH-DEFINITION.md) 开始。
- 查找当前批次的数据、媒体或交付包：从 [项目状态的当前或关联批次](./project_management/status/PROJECT_STATUS.md#活动对象) 进入其“权威机器产物”表，再按表中的格式文档定位字段和目录结构。
- 修改系统能力：先创建或更新计划，再进入对应 Technical 文档，不把开发实验直接写入生产 Workflow。
- 发生失败：从失败阶段链接到 [恢复索引](./technical/validation/RECOVERY.md)，恢复后从该阶段入口条件重新开始。
- 已知资产、配置或脚本名但不知道归属：从 [Registry](./registry/README.md) 反向定位；定位后回到对应 Technical/Workflow。
- 已知物理输出路径但不知道能否删除：从 [Output Inventory 与保留规则](./technical/output/INVENTORY_AND_RETENTION.md) 开始，不凭目录日期判断。

## 8. 维护原则

1. 一个事实只有一个主要所有者，其他位置只摘要并链接。
2. Master 和 Workflow 保持稳定；批次数字只进入状态、计划和机器配置。
3. 代码与命令由 Technical 解释；稳定验证语义由 Validation 拥有；稳定输出和保留语义由 Output 拥有；当前接受版本由 Status 指向。
4. 未验证能力不能因单次成功升级为通用生产能力。
5. 每次阶段完成后更新状态、计划需求、证据和里程碑，并运行 `character-factory-doc-maintenance` Skill。
6. 所有文档变更必须通过 [文档审计](./technical/validation/DOCUMENTATION_VALIDATION.md)。
7. 删除或归档前必须有可回溯快照、Manifest、明确保留等级和审查决定；`unclassified` 默认禁止删除。
8. 文档审计先逐个关闭独立子系统，再检查明确的跨层 ID、链接、所有权和状态关系。

详细规则、模板和同步矩阵见 [`GOVERNANCE.md`](./GOVERNANCE.md)。
