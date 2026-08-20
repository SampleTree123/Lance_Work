# Character Creator 角色工厂 Master

> 文档角色：`current_authoritative_master`
> 状态：`current`
> 适用阶段：`WF-00..WF-09`
> 权威范围：跨 CC、Bridge、CC→UE、UE 运行时和最终数据交付的当前流程、边界与导航
> 上级入口：[`README.md`](./README.md)
> 上游：机器代码、JSON 注册表和已验证证据
> 下游：[`workflow/README.md`](./workflow/README.md) 及所有领域、验证和规划文档
> 最近核验：2026-08-19

## 目录

1. [如何使用本文](#1-如何使用本文)
2. [目标与当前边界](#2-目标与当前边界)
3. [从零到数据集的完整主线](#3-从零到数据集的完整主线)
4. [十个生产阶段](#4-十个生产阶段)
5. [验证在流程中的位置](#5-验证在流程中的位置)
6. [日常生产与系统扩展](#6-日常生产与系统扩展)
7. [完整文档树](#7-完整文档树)
8. [环境与外部目录](#8-环境与外部目录)
9. [状态、计划、决定与历史](#9-状态计划决定与历史)
10. [恢复一个新对话](#10-恢复一个新对话)
11. [维护规则](#11-维护规则)

## 1. 如何使用本文

本文是唯一的人类可读总入口。第一次阅读先看第 2 至第 5 节；实际生产从 [`WF-00`](./workflow/WF-00-SESSION-PREFLIGHT.md) 开始，并只按 `WF-00 → ... → WF-09` 前进。

Master 说明“为什么、何时、到哪里”；Workflow 给出正常执行顺序和生产命令；领域文档解释数据模型与硬约束；Validation 定义测试、人工验收和恢复；Reference 定位代码、JSON、路径和术语。

发生冲突时遵循 [`DOCUMENTATION_RULES.md`](./DOCUMENTATION_RULES.md)：代码决定实际执行，机器 JSON 决定精确 ID/路径/参数，Master 决定被接受的跨系统流程。冲突未解释前停止生产。

**项目级最高操作边界之一**：用户独立负责资产、插件、安装包、输入数据及其许可、来源和对外发布边界。Agent 将用户提供的本地输入视为已获准用于本项目，不依据文件名、README、来源声明或授权措辞评价、拒绝或阻塞技术任务；只判断兼容性、完整性、稳定性、安全性、资源消耗和可复现性。详细决定见 [`ADR-0012`](./decisions/ADR-0012-USER-OWNED-ASSET-AUTHORITY.md)。

状态含义：

| 状态 | 含义 |
| --- | --- |
| `production` | 当前默认能力，具有实现、配置、验证和恢复说明 |
| `validated_pilot` | 在明确对象/规模上验证成功，不能扩展推断 |
| `manual_verified` | 人工 UI 流程成功，但没有稳定自动入口 |
| `planned` | 只有契约和验收目标，当前不可执行 |
| `compatibility` | 仅维护旧链接，不定义当前行为 |
| `archived` | 历史证据，不覆盖当前规则 |

## 2. 目标与当前边界

最终目标是生成可追溯的短视频/图像数据包：角色身份、BodyFit、年龄、外观、服装、动画、道具、场景、相机、随机种子和软件版本可回溯，并同时交付可用 GT、sidecar、配置、哈希和验收证据。

当前真实边界：

- 10 个成人 BodyFit、Face V3、面部外观池、41 个服装族/53 个逻辑组和 P0 动作候选已有机器与人工证据。
- F02/M02 穿衣 FullReference、四条代表动作及 `4 body × 4 direct-Morph face = 16/16` UE Runtime Pilot 已通过；它只证明受限技术组合，不等于完整生产批准。
- Headshot 10 人候选、三发型、十体型 UE 扩展、头部服装冲突和道具仍是后续工作，不阻塞第一批受限数据。
- `WF-08/09` 尚无已验证的统一执行器，因此完整数据生产仍未打通。

当前唯一活动计划是 [第一批多轮编辑数据 Sprint](./planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md)：使用 F02/M02、8 个身份、8 套服装、16 个烘焙 Look、6 条动作、3 种表情、1 个场景和 2 台相机构建最多 384 个唯一节点，并生成目标 4,000、最低 3,000 条 3–5 轮编辑链。精确当前状态见 [`CURRENT_STATUS.md`](./CURRENT_STATUS.md)；已完成过程只查 [`MILESTONE_LOG.md`](./history/MILESTONE_LOG.md)。

## 3. 从零到数据集的完整主线

```text
启动本轮所需应用并验证真实通信
  -> 定义角色请求并编译确定性 Manifest
  -> CC 装配身体、脸、年龄和外观
  -> CC 机器检查 + 人工动态/静态验收 + 保存项目
  -> 导出版本化 FBX/JSON/纹理 Bundle
  -> UE 完整参考导入与验收
  -> UE 模块化角色、Leader Pose、Morph 与变体
  -> 身体/面部动画、年龄、服装、毛发和道具
  -> 场景、角色位置、相机和 Level Sequence
  -> 渲染媒体/GT并封装可追溯数据集
```

每个箭头都是阶段边界。文件存在、脚本退出 0、界面看似正常或前一次成功，都不能替代当前阶段的 Exit Gate。

| 阶段 | 核心输入 | 核心输出 | Gate | 状态 |
| --- | --- | --- | --- | --- |
| `WF-00` | 当前机器会话 | 已验证执行通道 | `GATE-00` | `validated_pilot` |
| `WF-01` | 角色意图与注册表 | request + Manifest | `GATE-01` | `validated_pilot` |
| `WF-02` | Manifest | CC 装配结果与机器报告 | `GATE-02` | `validated_pilot` |
| `WF-03` | CC artifacts | accepted `.ccProject` 与证据 | `GATE-03` | `validated_pilot` |
| `WF-04` | accepted `.ccProject` | FBX/JSON/纹理 Bundle | `GATE-04` | `validated_pilot` |
| `WF-05` | Bundle | UE FullReference | `GATE-05` | `validated_pilot`，F02/M02 参考角色 |
| `WF-06` | FullReference | 模块化 Blueprint | `GATE-06` | `validated_pilot`，M02 |
| `WF-07` | 模块角色与表演资产 | 可验证表演配置 | `GATE-07` | 分项 Pilot |
| `WF-08` | 表演配置与场景意图 | Scene/Camera/Sequence | `GATE-08` | `planned` |
| `WF-09` | 已通过 Sequence | 数据集交付包 | `GATE-09` | `planned` |

完整阶段导航见 [`workflow/README.md`](./workflow/README.md)。

## 4. 十个生产阶段

### 4.1 WF-00 会话预检

何时：每个新会话、CC/UE 重启、崩溃恢复或通道变化后。目的：证明本轮需要的系统真实在线，而不是只看到配置。CC 必须由用户离线启动；代码变化时运行 `VAL-CODE-01`，任何 CC 作业前运行 `VAL-BRIDGE-01`。输出 `GATE-00 SESSION_READY`。

执行：[`WF-00-SESSION-PREFLIGHT.md`](./workflow/WF-00-SESSION-PREFLIGHT.md)。Bridge 机制：[`BRIDGE_OPERATIONS.md`](./bridge_details/BRIDGE_OPERATIONS.md)。失败：[`RECOVERY_RUNBOOK.md`](./validation/RECOVERY_RUNBOOK.md)。

### 4.2 WF-01 角色定义

何时：环境就绪、尚未改动 CC 场景时。目的：把 BodyFit、脸、年龄和外观选择固化为确定性 Manifest，禁止直接填本地资产路径。输出 request、Manifest 和 `GATE-01 MANIFEST_READY`。

执行：[`WF-01-CHARACTER-DEFINITION.md`](./workflow/WF-01-CHARACTER-DEFINITION.md)。规则：[`BODYFIT_PIPELINE.md`](./cc_details/BODYFIT_PIPELINE.md)、[`FACE_IDENTITY_AND_AGE.md`](./cc_details/FACE_IDENTITY_AND_AGE.md)、[`APPEARANCE_PIPELINE.md`](./cc_details/APPEARANCE_PIPELINE.md)。

### 4.3 WF-02 CC 装配

何时：Manifest 已通过。目的：在 CC/RLPy 中按 BodyFit → 面部 → 年龄 → 外观 → 材质质量顺序装配，并生成机器报告。它会替换当前 CC 场景。输出结构完整的角色 artifacts 和 `GATE-02 ASSEMBLY_COMPLETE`；此 Gate 不代表视觉通过。

执行：[`WF-02-CC-ASSEMBLY.md`](./workflow/WF-02-CC-ASSEMBLY.md)。Bridge 安全边界：[`BRIDGE_OPERATIONS.md`](./bridge_details/BRIDGE_OPERATIONS.md)。

### 4.4 WF-03 CC 验收

何时：装配作业成功后。目的：生成 summary/contact sheets，执行静态、动态、眼口、材质和追溯审核，恢复中性并保存规范项目。输出 accepted `.ccProject`、完整证据和 `GATE-03 CC_ACCEPTED`。

执行：[`WF-03-CC-ACCEPTANCE.md`](./workflow/WF-03-CC-ACCEPTANCE.md)。人工判定：[`VISUAL_ACCEPTANCE.md`](./validation/VISUAL_ACCEPTANCE.md)。

### 4.5 WF-04 CC 导出 Bundle

何时：CC 项目已人工接受。目的：使用已验证 Unreal/UE5 设置导出同基名 FBX、JSON、`.fbm` 和纹理，并固化来源哈希。输出版本化 Bundle 和 `GATE-04 BUNDLE_READY`。

执行：[`WF-04-CC-EXPORT-BUNDLE.md`](./workflow/WF-04-CC-EXPORT-BUNDLE.md)。追溯规则：[`ASSET_TRACEABILITY.md`](./cc_ue_transfer/ASSET_TRACEABILITY.md)。

### 4.6 WF-05 UE 完整参考导入

何时：Bundle 完整且 UE/Auto Setup 就绪。目的：先在 Vendor 目录验证完整 Skeletal Mesh、Skeleton、材质、Morph 和 Rig Logic，再允许拆分。输出 FullReference 和 `GATE-05 UE_REFERENCE_ACCEPTED`。当前 F02/M02 穿衣参考角色均有完整导入证据；模块化运行时仍只覆盖 M02。

执行：[`WF-05-UE-IMPORT-REFERENCE.md`](./workflow/WF-05-UE-IMPORT-REFERENCE.md)。

### 4.7 WF-06 UE 模块化运行时

何时：FullReference 通过。目的：建立模块网格、统一 Skeleton、20/19 Leader Pose、曲线传播和面部 Morph 广播，DataMake 暴露稳定 Blueprint。输出运行时角色和 `GATE-06 RUNTIME_ACCEPTED`。当前构建器硬编码 M02。

执行：[`WF-06-UE-CHARACTER-RUNTIME.md`](./workflow/WF-06-UE-CHARACTER-RUNTIME.md)。组件契约：[`MODULAR_CHARACTER_RUNTIME.md`](./ue_details/MODULAR_CHARACTER_RUNTIME.md)。

### 4.8 WF-07 动画与道具

何时：模块角色或明确登记的 FullReference Pilot 通过。目的：按 `none/curves/bones/hybrid` 和 `replaceable/paired/locked` 分类组合身体、面部与年龄，并登记道具依赖。M02 的两身体动作、五面部状态和 Elder Pilot 已验证；P0 的 16 条候选已完成 CC 动态机器门禁和用户视觉自然度验收。F02/M02 穿衣参考角色、四条代表动作及 FullReference 直接 Morph 的 `16/16` 运行时矩阵也已通过。生产动画池、其余 P0 决定、三发型和道具仍未收口。

执行：[`WF-07-ANIMATION-AND-PROPS.md`](./workflow/WF-07-ANIMATION-AND-PROPS.md)。技术规则：[`ANIMATION_AND_MORPH_PIPELINE.md`](./ue_details/ANIMATION_AND_MORPH_PIPELINE.md)。

### 4.9 WF-08 场景与相机

状态：`planned`。第一批 Sprint 只实现 1 个场景、1 个安全锚点、固定灯光、1 个中近景、1 个全身景和确定性 Level Sequence；当前仍没有统一执行器或验证代码。

阶段契约：[`WF-08-SCENE-CAMERA-SEQUENCE.md`](./workflow/WF-08-SCENE-CAMERA-SEQUENCE.md)。当前范围：[`FIRST_DATA_BATCH_SPRINT`](./planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md)。

### 4.10 WF-09 渲染与数据集

状态：`planned`。第一批 Sprint 将实现唯一节点渲染、sidecar、哈希、原子边、3–5 轮链和交付检查；当前早期渲染结果不构成数据集能力。

阶段契约：[`WF-09-RENDER-DATASET-PACKAGE.md`](./workflow/WF-09-RENDER-DATASET-PACKAGE.md)。数据契约：[`CONFIG_GRAPH_SCHEMA_V1.md`](../../schema/CONFIG_GRAPH_SCHEMA_V1.md) 与 [`MULTI_ROUND_CHAIN_SAMPLING_V1.md`](../../sampling/MULTI_ROUND_CHAIN_SAMPLING_V1.md)。

## 5. 验证在流程中的位置

验证不是最后统一补做，而是每个阶段的退出条件：

```text
Workflow 执行完成
  -> VAL-* 检查机器、结构或报告
  -> VIS-* 检查必须由人判断的视觉结果
  -> Gate 汇总适用项
  -> 通过才进入下一 WF；失败进入 REC-*
```

Gate 的组成与运行时机见 [`validation/README.md`](./validation/README.md)；准确测试命令和“成功能/不能证明什么”见 [`VALIDATION_CATALOG.md`](./validation/VALIDATION_CATALOG.md)；视觉姿态与标准见 [`VISUAL_ACCEPTANCE.md`](./validation/VISUAL_ACCEPTANCE.md)；每次视觉结果的网页登记、历史分支和 A/B 审查见 [`VISUAL_REVIEW_PORTAL.md`](./validation/VISUAL_REVIEW_PORTAL.md)；恢复步骤见 [`RECOVERY_RUNBOOK.md`](./validation/RECOVERY_RUNBOOK.md)。

## 6. 日常生产与系统扩展

日常生产沿 `WF-*` 前进。以下工作不是主线步骤，而是修改生产系统本身：

| 扩展任务 | 首读文档 | 回归影响 |
| --- | --- | --- |
| 新增/修改 BodyFit | [`BODYFIT_PIPELINE.md`](./cc_details/BODYFIT_PIPELINE.md) | `VAL-CODE-01`、`VAL-CC-01`，随后重验受影响角色 |
| 新增 Face seed/recipe/年龄 | [`FACE_IDENTITY_AND_AGE.md`](./cc_details/FACE_IDENTITY_AND_AGE.md) | Face/眼口动态验证与 `WF-01..03` |
| 新增 Headshot 原型 | [`HEADSHOT_PIPELINE.md`](./cc_details/HEADSHOT_PIPELINE.md) | `VAL-CC-03/04/05`、`VIS-CC-04`；接入前验证 project-seed 装配 |
| 新增皮肤、眼睛、毛发 | [`APPEARANCE_PIPELINE.md`](./cc_details/APPEARANCE_PIPELINE.md) | 域兼容矩阵和 `VIS-CC-*` |
| 新增服装来源或 Look | [`OUTFIT_PIPELINE.md`](./cc_details/OUTFIT_PIPELINE.md) | `VAL-CC-06` 源盘点，随后平均体型静态/动态和十体型兼容验证 |
| 修改 Bridge/API | [`BRIDGE_OPERATIONS.md`](./bridge_details/BRIDGE_OPERATIONS.md) | `VAL-CODE-01`、`VAL-BRIDGE-01` |
| 新增模块槽位/变体 | [`MODULAR_CHARACTER_RUNTIME.md`](./ue_details/MODULAR_CHARACTER_RUNTIME.md) | `VAL-UE-01`、`VIS-UE-01` |
| 新增动画/年龄 Morph | [`ANIMATION_AND_MORPH_PIPELINE.md`](./ue_details/ANIMATION_AND_MORPH_PIPELINE.md) | `VAL-UE-02/03`、`VIS-UE-02` |

开发阶段使用 `RM-*`，生产生命周期使用 `WF-*`；两者不得混用。当前开发顺序见 [`ROADMAP.md`](./planning/ROADMAP.md)。

## 7. 完整文档树

### 7.1 根目录

| 文档 | 作用 |
| --- | --- |
| [`README.md`](./README.md) | `full_process` 的短导航和 Master 跳转 |
| [`CHARACTER_FACTORY_MASTER_SPEC.md`](./CHARACTER_FACTORY_MASTER_SPEC.md) | 唯一跨系统总入口和完整生命周期 |
| [`CURRENT_STATUS.md`](./CURRENT_STATUS.md) | 当前能力、版本、限制和同步债务 |
| [`DOCUMENTATION_RULES.md`](./DOCUMENTATION_RULES.md) | 文档角色、状态、ID、命令所有权和维护规则 |

### 7.2 `workflow/`

[`workflow/README.md`](./workflow/README.md) 解释唯一执行顺序；`WF-00` 至 `WF-09` 分别对应第 4 节十个阶段。生产命令和阶段交付只在这些 Runbook 中维护。

### 7.3 `cc_details/`

| 文档 | 作用 |
| --- | --- |
| [`README.md`](./cc_details/README.md) | CC 领域索引及进入时机 |
| [`BODYFIT_PIPELINE.md`](./cc_details/BODYFIT_PIPELINE.md) | 十个 BodyFit、哈希、比例和身体不变量 |
| [`FACE_IDENTITY_AND_AGE.md`](./cc_details/FACE_IDENTITY_AND_AGE.md) | Face V3、Facial Profile、局部 Morph、年龄和 Headshot 边界 |
| [`HEADSHOT_PIPELINE.md`](./cc_details/HEADSHOT_PIPELINE.md) | Headshot 输入、原始项目冻结、CC5 Profile 晋级、原型包与 project-seed 接入契约 |
| [`APPEARANCE_PIPELINE.md`](./cc_details/APPEARANCE_PIPELINE.md) | 皮肤、眼睛、牙齿、眉睫、胡须、头发、色素和材质规则 |
| [`OUTFIT_PIPELINE.md`](./cc_details/OUTFIT_PIPELINE.md) | 服装源包、Look、替换组、层级互斥、十体型兼容和 UE 切换规则 |

### 7.4 `bridge_details/`

[`README.md`](./bridge_details/README.md) 是 Bridge 索引；[`BRIDGE_OPERATIONS.md`](./bridge_details/BRIDGE_OPERATIONS.md) 解释安装、协议、队列、allowlist、Undo 守卫和内部恢复边界。每日健康检查由 `WF-00` 调用。

### 7.5 `cc_ue_transfer/`

[`README.md`](./cc_ue_transfer/README.md) 是传输索引；[`ASSET_TRACEABILITY.md`](./cc_ue_transfer/ASSET_TRACEABILITY.md) 定义来源映射；实际导出和导入分别由 `WF-04/05` 维护。

### 7.6 `ue_details/`

[`README.md`](./ue_details/README.md) 是 UE 领域索引；[`MODULAR_CHARACTER_RUNTIME.md`](./ue_details/MODULAR_CHARACTER_RUNTIME.md) 定义组件/Leader/Morph/变体契约；[`ANIMATION_AND_MORPH_PIPELINE.md`](./ue_details/ANIMATION_AND_MORPH_PIPELINE.md) 定义动画通道、复用政策和 Elder 边界。

### 7.7 `validation/`

[`README.md`](./validation/README.md) 定义 Gate；[`VALIDATION_CATALOG.md`](./validation/VALIDATION_CATALOG.md) 定义 `VAL-*`；[`VISUAL_ACCEPTANCE.md`](./validation/VISUAL_ACCEPTANCE.md) 定义 `VIS-*`；[`VISUAL_REVIEW_PORTAL.md`](./validation/VISUAL_REVIEW_PORTAL.md) 定义视觉产物如何登记为可检索结果分支并进行 A/B 审查；[`RECOVERY_RUNBOOK.md`](./validation/RECOVERY_RUNBOOK.md) 定义 `REC-*`。

### 7.8 `planning/`

[`README.md`](./planning/README.md) 解释规划边界；[`FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md`](./planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md) 是当前唯一活动计划；[`ROADMAP.md`](./planning/ROADMAP.md) 只保存 Sprint 之后未完成的 `RM-*`；[`BACKLOG.md`](./planning/BACKLOG.md) 保存未承诺候选项。

### 7.9 `decisions/`

[`README.md`](./decisions/README.md) 索引所有 ADR。ADR-0001 至 0010 分别记录 BodyFit、Face V3、年龄、外观池、毛发、服装、UE 分层、动画分层、离线 Bridge 和旧文档治理；[`ADR-0011`](./decisions/ADR-0011-LIFECYCLE-DOCUMENTATION-AND-GATES.md) 记录生命周期/Gate 架构；[`ADR-0012`](./decisions/ADR-0012-USER-OWNED-ASSET-AUTHORITY.md) 记录用户对资产、安装包和许可/来源判断的独立权威边界；[`ADR-0013`](./decisions/ADR-0013-HEADSHOT-BAKED-PROTOTYPE-STORAGE.md) 记录 Headshot 烘焙身份的规范原型包和 project-seed 装配路线。

### 7.10 `reference/`

[`README.md`](./reference/README.md) 是参考索引；[`IMPLEMENTATION_INDEX.md`](./reference/IMPLEMENTATION_INDEX.md) 按 `WF-*` 定位代码/JSON/UE 资产；[`EXTERNAL_DIRECTORIES.md`](./reference/EXTERNAL_DIRECTORIES.md) 定义本机路径和所有权；[`GLOSSARY.md`](./reference/GLOSSARY.md) 定义术语与 ID；[`DOCUMENT_LINK_TRACE.md`](./reference/DOCUMENT_LINK_TRACE.md) 逐文件列出从 Master 出发的行号级提及链与回链。

### 7.11 `history/`

[`README.md`](./history/README.md) 解释历史边界；[`MILESTONE_LOG.md`](./history/MILESTONE_LOG.md) 只追加完成事件；[`reports/README.md`](./history/reports/README.md) 索引日期化周报与阶段汇报。`legacy_2026-08-06/` 保存第一次重组前旧文档；`pre_lifecycle_restructure_2026-08-06/` 保存本次重构前 37 份原文及 SHA-256。

### 7.12 跨目录数据与服务器规范

- [`data_design/schema/CONFIG_GRAPH_SCHEMA_V1.md`](../../schema/CONFIG_GRAPH_SCHEMA_V1.md)：第一批 asset、node、edge、chain、render job 和媒体契约。
- [`data_design/sampling/MULTI_ROUND_CHAIN_SAMPLING_V1.md`](../../sampling/MULTI_ROUND_CHAIN_SAMPLING_V1.md)：3–5 轮链、回退、闭环、覆盖和去重。
- [`implementation/FIRST_BATCH_SERVER_RUNBOOK.md`](../../../implementation/FIRST_BATCH_SERVER_RUNBOOK.md)：Linux/UE 5.8 项目同步、预检、10 节点基准、批量渲染和重试边界。

## 8. 环境与外部目录

核心路径：

```text
LANCE_ROOT      = D:\UE\Lance_Work
CC_INSTALL_ROOT = D:\CharacterCreator
CC_ASSET_ROOT   = D:\CharacterCreator_sucai
CLOTHING_SOURCE_ROOT = D:\BaiduNetdiskDownload\人物和服装
CC_EXPORT_ROOT  = D:\UE\exports\character_creator
UE_PROJECT_ROOT = D:\UE\projects\datatry_02
VISUAL_PORTAL    = D:\UE\Lance_Work\00_engine\visualization_portal
```

代码、机器 JSON 和 artifacts 不存入 `full_process`。完整职责、Bridge 队列、Vendor/DataMake 和输出规则见 [`EXTERNAL_DIRECTORIES.md`](./reference/EXTERNAL_DIRECTORIES.md)。

## 9. 状态、计划、决定与历史

- 当前能做什么：[`CURRENT_STATUS.md`](./CURRENT_STATUS.md)。
- 当前一周做什么：[`FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md`](./planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md)。
- Sprint 之后开发什么：[`ROADMAP.md`](./planning/ROADMAP.md)。
- 尚未承诺什么：[`BACKLOG.md`](./planning/BACKLOG.md)。
- 为什么采用当前规则：[`decisions/README.md`](./decisions/README.md)。
- 已经发生过什么：[`MILESTONE_LOG.md`](./history/MILESTONE_LOG.md)。

Roadmap 不覆盖当前能力，History 不定义当前流程，输出证据不等于机器配置。

## 10. 恢复一个新对话

1. 阅读本 Master 第 2、3、4 节。
2. 阅读 [`CURRENT_STATUS.md`](./CURRENT_STATUS.md)，确认当前已验证边界和未完成项。
3. 若 Sprint 仍活动，先读 [`FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md`](./planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md)，只执行其中当前日门禁。
4. 根据任务定位当前 `WF-*`；检查上一个 Gate 的真实证据。
5. 阅读该 Workflow 链接的领域规范和验证定义。
6. 用 [`IMPLEMENTATION_INDEX.md`](./reference/IMPLEMENTATION_INDEX.md) 核对准确脚本、JSON、UE 资产和证据路径。
7. 编辑器工作前重新执行 `WF-00`，不继承旧会话在线状态。

## 11. 维护规则

任何实现、注册表或能力变化后，至少同步：受影响 Workflow、领域规范、Validation、Implementation Index、Current Status，以及需要时的 Roadmap/ADR/Milestone。所有文档必须从 Master 可达，链接、元数据、阶段链、ID 唯一性和历史哈希由只读文档审计脚本检查。

旧入口只能跳转，不能保留第二套当前命令；计划页不得出现看似可运行的伪命令。详细规则见 [`DOCUMENTATION_RULES.md`](./DOCUMENTATION_RULES.md)。
