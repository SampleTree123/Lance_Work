# Character Creator 角色工厂总规范

> 文档角色：`current_authoritative_master`
> 首次建立：2026-08-05
> 体系重组：2026-08-06
> 适用范围：CC5 成人角色工厂、CC Bridge、CC→UE 5.8、UE 模块化角色与动画 Pilot
> 当前阶段：阶段 5A 已完成；下一步为阶段 5B Headshot 离线 4 人 smoke

本文件是角色工厂唯一人类可读总入口，也是高级使用手册。它说明当前系统能做什么、完整目标链如何组织、执行某类任务时应进入哪份技术文档，以及哪些步骤仍是 Pilot 或计划。精确命令、配置字段和故障恢复由子 Runbook 负责，精确 ID、哈希和参数由机器 JSON 负责。

## 目录

1. [阅读与权威规则](#1-阅读与权威规则)
2. [项目目标与当前边界](#2-项目目标与当前边界)
3. [文档体系与阅读路线](#3-文档体系与阅读路线)
4. [环境、路径和外部目录](#4-环境路径和外部目录)
5. [系统架构与完整目标链](#5-系统架构与完整目标链)
6. [BodyFit 身体系统](#6-bodyfit-身体系统)
7. [面部身份与年龄](#7-面部身份与年龄)
8. [外观、毛发与材质](#8-外观毛发与材质)
9. [当前 CC 角色生成流程](#9-当前-cc-角色生成流程)
10. [CC Bridge](#10-cc-bridge)
11. [CC 到 UE 传输](#11-cc-到-ue-传输)
12. [UE 模块化角色与动画](#12-ue-模块化角色与动画)
13. [质量门禁与运行安全](#13-质量门禁与运行安全)
14. [计划、决定和历史](#14-计划决定和历史)
15. [新对话恢复清单](#15-新对话恢复清单)
16. [维护协议](#16-维护协议)

## 1. 阅读与权威规则

### 1.1 状态标签

| 状态 | 可以如何使用 |
| --- | --- |
| `production` | 可作为当前默认流程 |
| `validated_pilot` | 只能在已验证边界内使用，不能直接扩展到十体型或批量生产 |
| `manual_verified` | 可以人工复现，但不能承诺无人值守 |
| `planned` | 只表示预留方向，不是当前能力 |
| `historical` | 只用于审计，禁止从旧文件恢复为当前入口 |

### 1.2 冲突处理

代码定义实际行为，机器 JSON 定义精确数据，本文件定义被接受的跨系统流程，技术 Runbook 定义复现方法，artifacts 定义一次运行证据。任意两层冲突时停止执行并登记同步债务，不得选择看起来方便的一层继续。

完整规则见 [`DOCUMENTATION_RULES.md`](./DOCUMENTATION_RULES.md)。

### 1.3 当前状态与历史

- 当前能力和版本：[`CURRENT_STATUS.md`](./CURRENT_STATUS.md)
- 当前未完成阶段：[`planning/ROADMAP.md`](./planning/ROADMAP.md)
- 尚未承诺的想法：[`planning/BACKLOG.md`](./planning/BACKLOG.md)
- 已接受决定及理由：[`decisions/README.md`](./decisions/README.md)
- 已发生事件和旧文档：[`history/README.md`](./history/README.md)

## 2. 项目目标与当前边界

角色工厂要为合成视频数据提供可追溯、可复现和可编辑的成人角色。角色身份由有限但高质量的身体、面部和资产库组合；编辑 pair 只改变明确登记的单一因素，其余身份、动画、相机和场景保持一致。

当前已经具备：

- 10 个固定成人 BodyFit。
- 20 个面部 seed、17 个生产主原型、当前 200 条配方实际使用的 28 个安全局部 Morph。
- 经过限定验证的皮肤、眼球、眉毛、睫毛、牙齿、胡须和头发池。
- CC 中的完整角色装配、保存、截图和质量验证执行器。
- 离线文件队列 Bridge 与受控命令。
- M02 的 CC→UE 导入、20 网格模块化拆分、身体/面部动画分层和年龄 Morph Pilot。

当前尚不具备：

- 十体型批量 CC→UE 生产导出。
- 每个角色三套正式可切换发型。
- 服装 Look 的十体型完整适配与动作穿模矩阵。
- 自动道具绑定、完整场景布置和大规模 MRQ 渲染。
- 语义明确的 Bridge 完整角色装配命令。
- Headshot 高质量身份原型生产池。

## 3. 文档体系与阅读路线

### 3.1 按任务选择文档

| 要做的事 | 第一份技术文档 | 关联文档 |
| --- | --- | --- |
| 验证或修改体型 | [`cc_details/BODYFIT_PIPELINE.md`](./cc_details/BODYFIT_PIPELINE.md) | [`validation/VALIDATION_AND_RECOVERY.md`](./validation/VALIDATION_AND_RECOVERY.md)、[`ADR-0001`](./decisions/ADR-0001-BODYFIT-SOURCE-PROJECTS.md) |
| 生成或修改人脸与年龄 | [`cc_details/FACE_IDENTITY_AND_AGE.md`](./cc_details/FACE_IDENTITY_AND_AGE.md) | [`cc_details/APPEARANCE_PIPELINE.md`](./cc_details/APPEARANCE_PIPELINE.md)、[`validation/VALIDATION_AND_RECOVERY.md`](./validation/VALIDATION_AND_RECOVERY.md) |
| 修改皮肤、眼睛或毛发池 | [`cc_details/APPEARANCE_PIPELINE.md`](./cc_details/APPEARANCE_PIPELINE.md) | [`reference/IMPLEMENTATION_INDEX.md`](./reference/IMPLEMENTATION_INDEX.md)、[`ADR-0004`](./decisions/ADR-0004-APPEARANCE-POOLS.md)、[`ADR-0005`](./decisions/ADR-0005-HAIR-PIGMENTATION-AND-VARIANTS.md) |
| 组装一个完整 CC 角色 | [`cc_details/CHARACTER_ASSEMBLY_RUNBOOK.md`](./cc_details/CHARACTER_ASSEMBLY_RUNBOOK.md) | [`bridge_details/BRIDGE_OPERATIONS.md`](./bridge_details/BRIDGE_OPERATIONS.md)、[`validation/VALIDATION_AND_RECOVERY.md`](./validation/VALIDATION_AND_RECOVERY.md) |
| 检查 CC 通信和弹窗 | [`bridge_details/BRIDGE_OPERATIONS.md`](./bridge_details/BRIDGE_OPERATIONS.md) | [`00_engine/character_creator_bridge/protocol_v1.md`](../../../../00_engine/character_creator_bridge/protocol_v1.md)、[`validation/VALIDATION_AND_RECOVERY.md`](./validation/VALIDATION_AND_RECOVERY.md) |
| 从 CC 导入 UE | [`cc_ue_transfer/EXPORT_IMPORT_RUNBOOK.md`](./cc_ue_transfer/EXPORT_IMPORT_RUNBOOK.md) | [`cc_ue_transfer/ASSET_TRACEABILITY.md`](./cc_ue_transfer/ASSET_TRACEABILITY.md) |
| 使用模块化角色 | [`ue_details/MODULAR_CHARACTER_RUNTIME.md`](./ue_details/MODULAR_CHARACTER_RUNTIME.md) | [`ue_details/ANIMATION_AND_MORPH_PIPELINE.md`](./ue_details/ANIMATION_AND_MORPH_PIPELINE.md) |
| 使用身体与面部动画 | [`ue_details/ANIMATION_AND_MORPH_PIPELINE.md`](./ue_details/ANIMATION_AND_MORPH_PIPELINE.md) | [`validation/VALIDATION_AND_RECOVERY.md`](./validation/VALIDATION_AND_RECOVERY.md) |
| 查找某一步实际使用的代码/JSON | [`reference/IMPLEMENTATION_INDEX.md`](./reference/IMPLEMENTATION_INDEX.md) | 对应技术规范或 Runbook |
| 查看本地目录和外部工程边界 | [`reference/EXTERNAL_DIRECTORIES.md`](./reference/EXTERNAL_DIRECTORIES.md) | [`reference/README.md`](./reference/README.md) |
| 诊断失败并恢复 | [`validation/VALIDATION_AND_RECOVERY.md`](./validation/VALIDATION_AND_RECOVERY.md) | 对应子系统 Runbook |
| 查看下一阶段或历史决策 | [`planning/ROADMAP.md`](./planning/ROADMAP.md) | [`decisions/README.md`](./decisions/README.md)、[`history/README.md`](./history/README.md) |

### 3.2 各层职责

`full_process` 保存当前文档；`00_engine/scripts/character_creator` 保存代码和机器配置；`00_engine/character_creator_bridge` 保存通信实现；`00_engine/outputs` 保存验证证据；`D:\UE\projects\datatry_02` 保存 UE 工程。目录不能因为文档重组而搬动。

文档按职责分层：Master 给出总流程和能力边界；技术规范解释数据模型和长期规则；Runbook 给出可执行步骤；Reference 负责路径、术语和实现文件定位；Validation 定义跨系统验收与恢复；Planning、ADR 和 History 分别保存未来、决定和过去。完整目录边界见 [`reference/EXTERNAL_DIRECTORIES.md`](./reference/EXTERNAL_DIRECTORIES.md)，代码级入口见 [`reference/IMPLEMENTATION_INDEX.md`](./reference/IMPLEMENTATION_INDEX.md)。

### 3.3 按目录划分的完整文档索引

本节索引 `full_process` 中的全部 Markdown。表中的“作用”是导航摘要，不代替文件正文；`history/legacy_2026-08-06` 下的文件只可审计，不可作为当前操作依据。

#### 3.3.1 根目录

| 文档 | 作用 |
| --- | --- |
| [`README.md`](./README.md) | `full_process` 的简短导航页、建议阅读路线和目录职责 |
| [`CHARACTER_FACTORY_MASTER_SPEC.md`](./CHARACTER_FACTORY_MASTER_SPEC.md) | 唯一人类可读总入口；定义当前被接受的跨系统流程和能力边界 |
| [`CURRENT_STATUS.md`](./CURRENT_STATUS.md) | 当前版本、已验证能力、已知不一致、在线依赖和下一步 |
| [`DOCUMENTATION_RULES.md`](./DOCUMENTATION_RULES.md) | 文档权威层级、状态、执行模式、Runbook 格式和同步规则 |

#### 3.3.2 `cc_details/`

| 文档 | 作用 |
| --- | --- |
| [`cc_details/README.md`](./cc_details/README.md) | CC 子系统索引、当前能力和未来文档预留 |
| [`cc_details/BODYFIT_PIPELINE.md`](./cc_details/BODYFIT_PIPELINE.md) | 十个 BodyFit 源项目、哈希、比例参数、身高和重建门禁 |
| [`cc_details/FACE_IDENTITY_AND_AGE.md`](./cc_details/FACE_IDENTITY_AND_AGE.md) | Face V3 身份结构、Facial Profile、局部 Morph、年龄与 Headshot 边界 |
| [`cc_details/APPEARANCE_PIPELINE.md`](./cc_details/APPEARANCE_PIPELINE.md) | 皮肤、眼睛、牙齿、眉睫、胡须、头发、色素和材质质量规则 |
| [`cc_details/CHARACTER_ASSEMBLY_RUNBOOK.md`](./cc_details/CHARACTER_ASSEMBLY_RUNBOOK.md) | 从请求、manifest 编译到 CC 装配、QA、汇总和联系表的可执行流程 |

#### 3.3.3 `bridge_details/`

| 文档 | 作用 |
| --- | --- |
| [`bridge_details/README.md`](./bridge_details/README.md) | Bridge 文档索引和当前命令能力矩阵 |
| [`bridge_details/BRIDGE_OPERATIONS.md`](./bridge_details/BRIDGE_OPERATIONS.md) | Bridge 安装、健康检查、队列、allowlist、命令、弹窗守卫和恢复 |

#### 3.3.4 `cc_ue_transfer/`

| 文档 | 作用 |
| --- | --- |
| [`cc_ue_transfer/README.md`](./cc_ue_transfer/README.md) | CC→UE 子系统索引和批量传输能力预留 |
| [`cc_ue_transfer/EXPORT_IMPORT_RUNBOOK.md`](./cc_ue_transfer/EXPORT_IMPORT_RUNBOOK.md) | CC5 FBX/JSON 导出、UE 5.8 导入、Auto Setup 与基础检查步骤 |
| [`cc_ue_transfer/ASSET_TRACEABILITY.md`](./cc_ue_transfer/ASSET_TRACEABILITY.md) | CC 源项目、导出 bundle、`/Game/Vendor` 与 `/Game/DataMake` 的身份映射 |

#### 3.3.5 `ue_details/`

| 文档 | 作用 |
| --- | --- |
| [`ue_details/README.md`](./ue_details/README.md) | UE 子系统索引、当前 Pilot 和未来运行时能力预留 |
| [`ue_details/MODULAR_CHARACTER_RUNTIME.md`](./ue_details/MODULAR_CHARACTER_RUNTIME.md) | M02 20 组件角色、Leader Pose、Morph 广播和模块变体边界 |
| [`ue_details/ANIMATION_AND_MORPH_PIPELINE.md`](./ue_details/ANIMATION_AND_MORPH_PIPELINE.md) | 身体/面部动画分层、通道登记、混合面部片段和 Elder Morph Pilot |

#### 3.3.6 `validation/`

| 文档 | 作用 |
| --- | --- |
| [`validation/README.md`](./validation/README.md) | 验证子系统索引；逐项区分已有执行代码与尚未实现的验收能力 |
| [`validation/VALIDATION_AND_RECOVERY.md`](./validation/VALIDATION_AND_RECOVERY.md) | CC、Bridge、CC→UE、UE 的具体命令、输入输出、通过条件、人工门禁和恢复树 |

#### 3.3.7 `planning/`

| 文档 | 作用 |
| --- | --- |
| [`planning/README.md`](./planning/README.md) | Roadmap、Backlog 的边界和更新规则 |
| [`planning/ROADMAP.md`](./planning/ROADMAP.md) | 已接受、已排序并有验收条件的未来阶段 |
| [`planning/BACKLOG.md`](./planning/BACKLOG.md) | 尚未排期的候选改进、研究问题和技术债务 |

#### 3.3.8 `decisions/`

| 文档 | 作用 |
| --- | --- |
| [`decisions/README.md`](./decisions/README.md) | ADR 索引、状态和决定摘要 |
| [`decisions/ADR-0001-BODYFIT-SOURCE-PROJECTS.md`](./decisions/ADR-0001-BODYFIT-SOURCE-PROJECTS.md) | BodyFit 使用 hash 锁定源 `.ccProject` |
| [`decisions/ADR-0002-FACE-IDENTITY-V3.md`](./decisions/ADR-0002-FACE-IDENTITY-V3.md) | 完整 seed + Facial Profile + 安全局部 Morph |
| [`decisions/ADR-0003-AGE-VARIANTS.md`](./decisions/ADR-0003-AGE-VARIANTS.md) | 年龄作为可选变体，身体老化延后 |
| [`decisions/ADR-0004-APPEARANCE-POOLS.md`](./decisions/ADR-0004-APPEARANCE-POOLS.md) | 外观只从审核池选择，眼球只换材质 |
| [`decisions/ADR-0005-HAIR-PIGMENTATION-AND-VARIANTS.md`](./decisions/ADR-0005-HAIR-PIGMENTATION-AND-VARIANTS.md) | 共享毛发色素抽样和每角色三发型目标 |
| [`decisions/ADR-0006-OUTFITS-PER-BODYFIT-LOOK.md`](./decisions/ADR-0006-OUTFITS-PER-BODYFIT-LOOK.md) | 服装按 BodyFit × Look 管理 |
| [`decisions/ADR-0007-UE-VENDOR-DATAMAKE-MODULARITY.md`](./decisions/ADR-0007-UE-VENDOR-DATAMAKE-MODULARITY.md) | Vendor 不移动，DataMake 作为统一派生入口 |
| [`decisions/ADR-0008-BODY-FACE-ANIMATION-LAYERS.md`](./decisions/ADR-0008-BODY-FACE-ANIMATION-LAYERS.md) | 身体与面部动画按通道和复用政策分层 |
| [`decisions/ADR-0009-RESTRICTED-OFFLINE-BRIDGE.md`](./decisions/ADR-0009-RESTRICTED-OFFLINE-BRIDGE.md) | Bridge 使用受控离线文件队列，不执行任意代码 |
| [`decisions/ADR-0010-DOCUMENT-AUTHORITY-AND-HISTORY.md`](./decisions/ADR-0010-DOCUMENT-AUTHORITY-AND-HISTORY.md) | 单一当前入口、技术子文档和不可变历史归档 |

#### 3.3.9 `reference/`

| 文档 | 作用 |
| --- | --- |
| [`reference/README.md`](./reference/README.md) | Reference 子目录索引及权威边界 |
| [`reference/EXTERNAL_DIRECTORIES.md`](./reference/EXTERNAL_DIRECTORIES.md) | CC 安装、素材、脚本、Bridge、输出、导出和 UE 工程的物理目录 |
| [`reference/IMPLEMENTATION_INDEX.md`](./reference/IMPLEMENTATION_INDEX.md) | 流程步骤与当前 Python、JSON、UE 资产和证据的映射 |
| [`reference/GLOSSARY.md`](./reference/GLOSSARY.md) | BodyFit、Facial Profile、Look、Leader Pose 等术语定义 |

#### 3.3.10 `history/`

| 文档 | 作用 |
| --- | --- |
| [`history/README.md`](./history/README.md) | 历史目录边界和使用规则 |
| [`history/MILESTONE_LOG.md`](./history/MILESTONE_LOG.md) | 重组后的只追加完成事件与证据索引 |
| [`history/legacy_2026-08-06/ARCHIVE_MANIFEST.md`](./history/legacy_2026-08-06/ARCHIVE_MANIFEST.md) | 六份重组前原文的来源、哈希和归档说明 |
| [`history/legacy_2026-08-06/README.md`](./history/legacy_2026-08-06/README.md) | 重组前根 README 的不可变快照 |
| [`history/legacy_2026-08-06/STATUS.md`](./history/legacy_2026-08-06/STATUS.md) | 重组前状态文档的不可变快照 |
| [`history/legacy_2026-08-06/CHARACTER_FACTORY_MASTER_SPEC.md`](./history/legacy_2026-08-06/CHARACTER_FACTORY_MASTER_SPEC.md) | 重组前 Master 的不可变快照 |
| [`history/legacy_2026-08-06/FACIAL_GENERATION.md`](./history/legacy_2026-08-06/FACIAL_GENERATION.md) | 旧面部生成规范的不可变快照 |
| [`history/legacy_2026-08-06/FACIAL_GENERATION_NEXT_ITERATION_PLAN_2026-07-31.md`](./history/legacy_2026-08-06/FACIAL_GENERATION_NEXT_ITERATION_PLAN_2026-07-31.md) | 旧面部迭代计划的不可变快照 |
| [`history/legacy_2026-08-06/CHARACTER_REALISM_IMPROVEMENT_BACKLOG_2026-08-05.md`](./history/legacy_2026-08-06/CHARACTER_REALISM_IMPROVEMENT_BACKLOG_2026-08-05.md) | 旧真实度改进清单的不可变快照 |

## 4. 环境、路径和外部目录

技术文档使用以下逻辑变量：

```text
LANCE_ROOT       = D:\UE\Lance_Work
CC_INSTALL_ROOT  = D:\CharacterCreator
CC_ASSET_ROOT    = D:\CharacterCreator_sucai
UE_PROJECT_ROOT  = D:\UE\projects\datatry_02
CC_EXPORT_ROOT   = D:\UE\exports\character_creator
```

CC 使用学校离线许可证。Agent 不自动重启 CC；需要重启时由用户在满足离线条件后执行。UE MCP 只有在编辑器和本地服务实际监听时才算在线。

完整目录结构、队列和输出规则见 [`reference/EXTERNAL_DIRECTORIES.md`](./reference/EXTERNAL_DIRECTORIES.md)。

## 5. 系统架构与完整目标链

```text
资产与身份配置
  -> manifest 编译
  -> CC 角色装配
  -> 静态/动态/隔离质量门禁
  -> 规范化 .ccProject
  -> FBX + JSON + textures 导出
  -> UE Auto Setup 导入
  -> 模块化角色与运行时控制
  -> 场景、相机、动画、渲染 manifest
  -> 视频、GT 和 sidecar
```

| 阶段 | 当前状态 | 当前入口 |
| --- | --- | --- |
| 身体、脸和外观配置 | `production` | `cc_details` 与机器 JSON |
| 角色 manifest 编译 | `production` | `cc_compile_character_manifest.py` |
| CC 完整角色执行 | `validated_pilot` | Bridge `validate-bodies` 执行兼容 manifest |
| CC 完整视觉门禁 | `validated_pilot` | `cc_validate_body_reconstruction.py` 与 artifacts |
| CC 保存项目 | `validated_pilot` | manifest `save_character_projects=true` |
| 单角色 CC→UE | `validated_pilot` | M02 FBX/JSON Pilot |
| UE 模块化角色 | `validated_pilot` | `/Game/DataMake/Characters/M02_Average/BP_DM_M02_ModularPilot_v002` |
| UE 身体/面部动画 | `validated_pilot` | v003 AnimBP 与 registry |
| 十体型导出、服装和发型 | `planned` | Roadmap 阶段 7–8 |
| 场景与批量渲染 | `planned` | UE 子目录能力矩阵 |

完整目标链用于规划；当前 Runbook 只给真实存在的入口。

## 6. BodyFit 身体系统

当前身体池固定为 10 个 `.ccProject`：男女各 Lean、Average、Athletic、Heavy 和 Short Average。运行时先加载 hash 锁定项目，不从 Neutral Base 用少量宏 Morph 猜测重建。

每个 BodyFit 同时拥有：

- 源项目路径、大小和 SHA-256。
- Body/Junction Morph 指纹。
- 固定 Head Scale。
- 必要时固定 Neck Height。
- 当前测量身高和视觉证据。

身体项目自带的面部只是加载载体，后续由同性交付的主面部和配方替换。面部步骤不得改变 Body/Junction 指纹。精确数值、验证命令和十体型表见 [`cc_details/BODYFIT_PIPELINE.md`](./cc_details/BODYFIT_PIPELINE.md)。

## 7. 面部身份与年龄

Face V3 的身份结构为：

```text
一个完整同性交付主面部 seed
  + 该 seed 对应的 Facial Profile
  + 配方列出的少量安全局部 Morph
  + BodyFit 固定 Head Scale / Neck Height
```

禁止把未列出的面部参数全部清零。眼部和口部支撑不参与自由随机；眼睛几何、眼骨、牙齿和口腔支撑必须保持成对一致。

当前年龄只有 `young=0.0`、`middle=0.5`、`older=1.0` 三档 Full Face Elder。年龄是可选变体，不是精确生理年龄。当前 CC 生产只改变面部；身体老化仍是计划项。

完整算法、seed 状态、Facial Profile、年龄和 Headshot 扩展见 [`cc_details/FACE_IDENTITY_AND_AGE.md`](./cc_details/FACE_IDENTITY_AND_AGE.md)。

## 8. 外观、毛发与材质

当前登记池：

| 组件 | 数量 | 核心规则 |
| --- | ---: | --- |
| 青年 2K `.ccSkin` | 21 | 整体应用头和身体；年龄 Morph 另行处理 |
| 眼球材质 | 12 | 只选 `Material Only`，禁止替换眼球对象 |
| 眉毛 | 13 | 按性别池和兼容登记选择 |
| 睫毛 | 9 | 当前成人双性候选池，仍执行眼睑动态门禁 |
| 牙齿 | 2 | 完整 `Replace`，需要张嘴和微笑检查 |
| 男性胡须 | 5 | 女性禁用；UE 目标支持有/无胡须 |
| 头发 | 58 | 按性别呈现分数和风险等级选择 |

同一角色的头发、眉毛和胡须共享一次色素抽样。自然常见、自然罕见和染发模式权重为 `0.92/0.06/0.02`；肤色资产只绑定色素档案，不直接推断种族身份。

最终皮肤和眼球应用后必须执行 `cc_face_material_quality_v1`：左右角膜各 3 项，头部皮肤 4 项，共回读 10 项实际写入。后续换肤或换眼必须重新应用。

资产路径、顺序、质量参数和扩展流程见 [`cc_details/APPEARANCE_PIPELINE.md`](./cc_details/APPEARANCE_PIPELINE.md)。

## 9. 当前 CC 角色生成流程

日常流程使用现有资源池，不重新生成 BodyFit、seed 或资产目录：

1. 验证 CC 离线启动、Bridge 心跳、内存和空闲状态。
2. 创建带唯一 `character_id`、`bodyfit_id` 和可选 `face_recipe_id` 的请求 JSON。
3. 使用系统 Python 编译确定性角色 manifest。
4. 检查 manifest 只引用白名单、已通过兼容登记和匹配性别的资产。
5. 通过 Bridge `validate-bodies` 提交该 manifest；当前命令名是技术债务。
6. CC 依固定顺序加载身体、面部、比例、皮肤、年龄、皱纹、五官资产、毛发和材质质量档案。
7. 执行静态、动态、Morph 隔离、眼球完整性和弹窗门禁。
8. 保存规范化 `.ccProject`、结果 JSON、截图和 manifest。
9. 汇总结果并生成人工联系表。
10. 只有自动门禁和人工视觉审核都通过，角色才可进入导出。

准确命令、输入模板、输出和恢复方式见 [`cc_details/CHARACTER_ASSEMBLY_RUNBOOK.md`](./cc_details/CHARACTER_ASSEMBLY_RUNBOOK.md)。

## 10. CC Bridge

Bridge 是 Agent 与离线 CC 的受控文件队列边界，不接受任意 Python。当前允许：

```text
ping
scene_summary
apply_face_recipe_preview
validate_bodyfit_library
```

客户端显示为 `health`、`ping`、`scene-summary`、`apply-face`、`validate-bodies`、`wait` 和 `result`。`health` 只读心跳，不产生队列作业。

安装、健康判定、原子请求、输出目录、超时、弹窗守卫和恢复见 [`bridge_details/BRIDGE_OPERATIONS.md`](./bridge_details/BRIDGE_OPERATIONS.md)。线协议仍由 `00_engine/character_creator_bridge/protocol_v1.md` 定义。

## 11. CC 到 UE 传输

已验证的 M02 导出包含 FBX、同名 JSON、`.fbm` 和纹理。CC 使用 Unreal 目标、Z 轴、UE5 Skeleton、Epic Hand/Foot IK、Auto Skin Rigid Mesh、JSON 材质 sidecar 和 Morph 导出。不同 CC 版本 UI 选项可能不同，Runbook 只列本机实际可见且已验证的设置。

UE 端使用项目级 Reallusion Auto Setup 2.03。Vendor 导入资产保留原路径，DataMake 只保存自己的蓝图、派生动画、配置和统一入口。

导出/导入步骤见 [`cc_ue_transfer/EXPORT_IMPORT_RUNBOOK.md`](./cc_ue_transfer/EXPORT_IMPORT_RUNBOOK.md)，资产身份和源→目标映射见 [`cc_ue_transfer/ASSET_TRACEABILITY.md`](./cc_ue_transfer/ASSET_TRACEABILITY.md)。

## 12. UE 模块化角色与动画

M02 Pilot 将完整导入网格拆成 20 个 Skeletal Mesh Component；Body 是 Leader，其余 19 个 follower 使用 Leader Pose。Morph 通过广播组件同步到相关网格。

动画策略：

- 身体动画保持身体、root、hip、脊柱和颈部运动。
- 可复用面部片段包含面部骨骼和 Morph 曲线，不覆盖身体层。
- 原始动画如果包含完整面部表演，应登记为 `full_performance`，不再叠加随机面部层。
- v003 已验证两条身体动作与五个面部状态 `10/10`。
- UE Elder Morph 仍是 Pilot，批量化前需要拓扑、Vertex ID 和视觉门禁。

组件接口见 [`ue_details/MODULAR_CHARACTER_RUNTIME.md`](./ue_details/MODULAR_CHARACTER_RUNTIME.md)，动画和 Morph 见 [`ue_details/ANIMATION_AND_MORPH_PIPELINE.md`](./ue_details/ANIMATION_AND_MORPH_PIPELINE.md)。

服装切换、三发型、毛发物理、道具、场景和渲染在 `ue_details/README.md` 中预留，但当前不得写成已实现能力。

## 13. 质量门禁与运行安全

每个正式 CC 角色至少检查：

- 正面、3/4、侧面、后脑和全身。
- 双眼闭合、单眼闭合、左右上下视线、眯眼、睁大、眉毛、微笑和张嘴。
- 眼球对象、眼骨、LookAt、`Eyeball Move` 和中性恢复。
- 牙齿、舌头、嘴唇、眼睑、睫毛、眉毛、胡须和头发穿模。
- Body/Junction 指纹、Head Scale、Neck Height 和材质参数回读。

自动 API 成功不能替代视觉验收。输出目录必须唯一，不得覆盖旧证据。CC 达到 24 GB private memory、未知阻塞弹窗、Bridge 心跳过期或 UE MCP 离线时停止对应自动步骤。

完整门禁和恢复树见 [`validation/VALIDATION_AND_RECOVERY.md`](./validation/VALIDATION_AND_RECOVERY.md)。

## 14. 计划、决定和历史

当前执行顺序：Headshot smoke → 10/20 原型比较 → 新面部与年龄 → 三发型/胡须 → 服装 Look 十体型 → 道具 → UE 统一接口 → 端到端样本。只有阶段验收后才能晋级当前能力。

- 活动计划：[`planning/ROADMAP.md`](./planning/ROADMAP.md)
- 候选改进：[`planning/BACKLOG.md`](./planning/BACKLOG.md)
- 决策理由：[`decisions/README.md`](./decisions/README.md)
- 完成事件：[`history/MILESTONE_LOG.md`](./history/MILESTONE_LOG.md)
- 旧原文：[`history/legacy_2026-08-06/`](./history/legacy_2026-08-06/)

## 15. 新对话恢复清单

1. 阅读本文件。
2. 阅读 [`CURRENT_STATUS.md`](./CURRENT_STATUS.md) 的同步债务和下一步。
3. 阅读 Roadmap 中当前阶段，不从历史文件推断下一步。
4. 根据任务打开对应技术 Runbook。
5. 从 [`reference/IMPLEMENTATION_INDEX.md`](./reference/IMPLEMENTATION_INDEX.md) 核对当前脚本和 JSON。
6. 运行 Bridge `health`；需要 UE 时再实时验证 UE MCP。
7. 检查 CC private memory、弹窗和当前场景是否可替换。
8. 为新运行创建唯一输出目录。
9. 运行后同步 Current Status、Milestone Log、Roadmap 和必要 ADR。

## 16. 维护协议

接受以下变化时必须同步本文件：

- BodyFit、面部、年龄或资产池数量变化。
- 默认装配顺序、质量门禁或停止条件变化。
- Bridge、CC 导出、UE 导入或运行时接口变化。
- 当前阶段、主要风险或能力成熟度变化。

只改变精确参数时更新机器 JSON 和对应技术文档，本文件保留摘要。原始 artifacts 不搬入文档目录；稳定结论必须回写 Current Status 或 Milestone Log。未来新增能力应进入既有子目录，不因增加一类功能重新设计顶层结构。
