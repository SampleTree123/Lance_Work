# Character Creator 角色工厂总规范

> 文档角色：`current_authoritative_master`
> 首次建立：2026-08-05
> 最近核验：2026-08-05
> 适用范围：Character Creator 5 成人角色工厂、CC 自动化、CC 到 Unreal Engine 5.8 导出、UE 模块化角色与动画 Pilot
> 当前阶段：阶段 5A 已完成；下一步为阶段 5B Headshot 离线 4 人 smoke
> 维护要求：任何被接受的生产决策、参数、入口、验证结论或下一步变化，都必须在任务结束前同步本文件

本文件是 Character Creator 角色工厂的唯一人类可读总入口。新对话应先读本文件，再按本文索引读取机器配置、状态日志或活动计划。

本文件不会复制全部 JSON 数组、Python 实现和截图。它完整记录当前系统如何工作、哪些内容已经验证、哪些仍是 Pilot、权威文件在哪里，以及发生冲突时如何处理。精确资产 ID、路径、哈希和运行时字段仍由机器可读文件负责。

## 目录

1. [阅读与维护规则](#1-阅读与维护规则)
2. [项目目标与当前结论](#2-项目目标与当前结论)
3. [权威层级与文档职责](#3-权威层级与文档职责)
4. [本地环境与关键路径](#4-本地环境与关键路径)
5. [系统架构](#5-系统架构)
6. [十个 BodyFit](#6-十个-bodyfit)
7. [面部身份生成](#7-面部身份生成)
8. [年龄、皮肤与动态皱纹](#8-年龄皮肤与动态皱纹)
9. [面部组件与毛发](#9-面部组件与毛发)
10. [面部材质质量后处理](#10-面部材质质量后处理)
11. [唯一 CC 角色组装顺序](#11-唯一-cc-角色组装顺序)
12. [服装、换发与运行时变体](#12-服装换发与运行时变体)
13. [身体动画、面部动画与道具](#13-身体动画面部动画与道具)
14. [CC 到 UE 导出与导入](#14-cc-到-ue-导出与导入)
15. [UE 项目、场景与模块化角色](#15-ue-项目场景与模块化角色)
16. [质量门禁与停止条件](#16-质量门禁与停止条件)
17. [已完成阶段与关键证据](#17-已完成阶段与关键证据)
18. [当前未完成事项与执行顺序](#18-当前未完成事项与执行顺序)
19. [机器可读权威文件索引](#19-机器可读权威文件索引)
20. [新对话恢复检查清单](#20-新对话恢复检查清单)
21. [文档维护协议](#21-文档维护协议)

## 1. 阅读与维护规则

### 1.1 状态标签

本文统一使用以下标签：

| 标签 | 含义 |
| --- | --- |
| `production_approved` | 已通过当前适用范围的自动与视觉门禁，可进入默认角色工厂 |
| `validated_pilot` | 在代表样本上验证成功，但尚未扩展到十体型或完整生产规模 |
| `planned` | 已确认方向，尚未实现或验收 |
| `historical` | 只保留研究、事故或旧批次证据，不是当前入口 |
| `rejected` | 已知不安全或不兼容，禁止生产抽样 |

### 1.2 冲突处理

不同来源发生冲突时不得静默选择一份继续运行：

1. 精确资产 ID、文件路径、哈希和枚举值以机器配置为执行级权威。
2. 当前设计决策、流程和适用边界以本文件为人类可读权威。
3. Python 代码决定实际执行行为；若代码与本文件不一致，必须停止并同步修复。
4. `artifacts` 中的报告和截图证明一次实际运行发生了什么。
5. `STATUS.md` 是按日期追加的事实日志，其中旧章节可以保留旧结论，不能覆盖本文件的当前状态。
6. 活动计划只描述尚未完成的工作，不得冒充已经实现。

### 1.3 不重复维护的内容

以下内容不复制进本文件：

- 数百条完整人脸配方。
- 每个资产的完整机器字段与 SHA-256。
- Python 函数实现。
- 全部截图和逐帧测量。
- UE 二进制 `.uasset` 内容。

本文件必须为这些内容提供权威路径、用途、数量、状态和关键边界。

## 2. 项目目标与当前结论

角色工厂服务于 Unreal Engine 合成视频数据。目标是把角色表示为可审计配置，并生成可复现的 CC 项目、FBX/JSON 导出、UE 模块和验证证据：

```text
BodyFit
+ Face identity
+ Age
+ Skin and facial parts
+ Hair pigmentation
+ Hair / beard
+ Outfit Look
+ Body motion
+ Face animation
-> validated CC character
-> FBX + JSON sidecar
-> UE modular character
-> deterministic render configuration
```

截至 2026-08-05 的当前结论：

- 10 个成人 BodyFit 使用 hash 锁定的 `.ccProject` 作为权威身体入口。
- 面部使用 Face V3：20 条源 seed 记录中，17 个进入生产抽样。
- 200 条确定性人脸配方只修改 28 个安全局部 Morph。
- Facial Profile、眼球、牙齿和口腔支撑必须与主面部成对保留。
- 21 套青年 2K 皮肤、12 套眼球材质、13 套眉毛、9 套睫毛、2 套牙齿、5 套男性胡须和 58 套头发已经登记在各自限定池中。
- 皮肤微表面与眼部材质质量档案已为 `production_approved`。
- 10 个 BodyFit 各生成过 1 个完整角色并通过用户视觉验收。
- M02 已完成 CC5 到 UE 5.8 整合参考、20 网格模块化拆分、两条身体动画、可组合面部动画、年龄 Morph fallback 与混合面部骨骼/曲线 Pilot。
- 尚未完成十体型批量 UE 导出、三发型正式变体、服装 Look 十体型适配和端到端批量渲染。
- Aaron/M02 对照表明，当前最大剩余质量差距来自身份原型与面部几何，下一步是 Headshot 高质量原型验证。

## 3. 权威层级与文档职责

### 3.1 当前文档

| 文件 | 文档角色 | 维护方式 |
| --- | --- | --- |
| `CHARACTER_FACTORY_MASTER_SPEC.md` | `current_authoritative_master` | 每次接受生产决策后同步更新 |
| `STATUS.md` | `status_log` | 只追加已发生事实、结果和证据路径 |
| `FACIAL_GENERATION.md` | `supporting_subsystem_spec` | 保留面部算法、资产与门禁细节；历史 8 BodyFit 批次必须明确标成历史 |
| `FACIAL_GENERATION_NEXT_ITERATION_PLAN_2026-07-31.md` | `active_plan` | 只维护未完成阶段及验收条件 |
| `CHARACTER_REALISM_IMPROVEMENT_BACKLOG_2026-08-05.md` | `supporting_backlog` | 记录真实度候选项；已完成项指回本文件和正式配置 |
| `README.md` | `navigation_overview` | 只做目录导航和概念概览 |

### 3.2 机器与证据层

| 层级 | 位置 | 职责 |
| --- | --- | --- |
| 源配置 | `00_engine/scripts/character_creator/*.json` | 精确 ID、路径、参数、状态和哈希 |
| 执行代码 | `00_engine/scripts/character_creator/*.py` | 编译、装配、验证、截图和报告 |
| CC Bridge | `00_engine/character_creator_bridge/` | Agent 与离线 CC5 的受控通信 |
| CC 证据 | `00_engine/outputs/character_creator_bridge/artifacts/` | 运行结果、截图、项目和报告 |
| UE 索引 | `D:\UE\projects\datatry_02\DataMake\dm_asset_index.json` | 当前 DataMake 派生资产索引；必须在 UE 在线核对后更新 |
| UE 证据 | `00_engine/outputs/unreal_character_import/` | UE 构建、PIE 矩阵和联系表 |

## 4. 本地环境与关键路径

| 用途 | 路径或版本 |
| --- | --- |
| 工作区 | `D:\UE\Lance_Work` |
| CC5 软件 | `D:\CharacterCreator` |
| CC5 资产库 | `D:\CharacterCreator_sucai` |
| CC 自定义项目 | `D:\CharacterCreator_sucai\Reallusion Custom\Project\CC Project` |
| UE 主项目 | `D:\UE\projects\datatry_02` |
| UE 版本 | 5.8 |
| CC 到 UE Pilot 导出 | `D:\UE\exports\character_creator\pilot_m02_ue58_v001` |
| Reallusion Auto Setup | 项目级 `Plugins\RLPlugin`，版本 2.03，EngineVersion 5.8.0 |
| Auto Setup 原始安装包 | `C:\Program Files\Reallusion\Shared Plugins\Auto Setup\Unreal\Auto Setup 2.03 For Unreal 5.8 (All-in-One)` |
| UE DataMake 内容根 | `/Game/DataMake` |
| UE Vendor 内容根 | `/Game/Vendor/Reallusion/CC5` |

CC 使用学校离线许可证。Agent 不自动重启 CC；需要重启时由用户在满足离线条件后执行。UE MCP 当前默认地址为本地监听端口，只有编辑器和 MCP 服务实际启动时才能视为在线，不能根据配置存在推断连接成功。

## 5. 系统架构

### 5.1 CC 自动化边界

```text
Agent / CLI
  -> 结构化 JSON 请求
  -> 文件队列 Bridge
  -> CC5 OpenPlugin worker
  -> RLPy 白名单操作
  -> result.json + artifacts
```

Bridge 不接受任意 Python 源码。所有角色选择都应使用已经登记的 `bodyfit_id`、`face_recipe_id` 和 `asset_id`，不允许生产请求临时传入任意资产路径。

健康检查：

```powershell
python D:\UE\Lance_Work\00_engine\character_creator_bridge\cc_bridge_client.py health
```

主要实现：

```text
00_engine/character_creator_bridge/
  bridge_config.json
  cc_bridge_client.py
  plugin/main.py
  cc_undo_dialog_guard.ps1
  protocol_v1.md
```

### 5.2 角色配置原则

- Agent 选择结构化目标，不直接生成任意 CC 操作代码。
- BodyFit、主面部、资产、颜色、年龄和 Look 都必须来自登记。
- 每次装配记录源哈希、Morph 指纹、对象变化、弹窗和输出路径。
- 用户视觉验收与自动数值门禁缺一不可。
- 大文件与 `.uasset` 不进入 Git；Markdown、脚本、配置和 manifest 可以版本管理。

## 6. 十个 BodyFit

### 6.1 当前权威表

高度使用 CC 世界空间 avatar bounds 的 `maximum_z - minimum_z`，单位为 cm。Head Scale 与 Neck Height 为 CC UI 值；RLPy 权重为 UI 值乘 `0.01`。

| BodyFit | 性别 | 类别 | 高度 cm | Head Scale | Neck Height | 源项目 |
| --- | --- | --- | ---: | ---: | ---: | --- |
| `M01_Lean` | male | lean | 173.42 | -10 | -20 | `M01_Lean.ccProject` |
| `M02_Average` | male | average | 181.28 | 0 | 0 | `M02_Average.ccProject` |
| `M03_Athletic` | male | athletic | 187.74 | +10 | -20 | `M03_Athletic.ccProject` |
| `M04_Heavy` | male | heavy | 187.93 | +30 | 0 | `M04_Heavy.ccProject` |
| `M05_Short_Average` | male | short_average | 159.89 | 0 | 0 | `M05_Short_Average.ccProject` |
| `F01_Lean` | female | lean | 158.38 | -20 | -40 | `F01_Lean.ccProject` |
| `F02_Average` | female | average | 172.71 | +10 | 0 | `F02_Average.ccProject` |
| `F03_Athletic` | female | athletic | 173.16 | +10 | 0 | `F03_Athletic.ccProject` |
| `F04_Heavy` | female | heavy | 174.85 | +30 | 0 | `F04_Heavy.ccProject` |
| `F05_Short_Average` | female | short_average | 152.53 | -10 | 0 | `F05_Short_Average.ccProject` |

全部源项目位于：

```text
D:\CharacterCreator_sucai\Reallusion Custom\Project\CC Project
```

### 6.2 强制规则

- 运行时先加载 hash 锁定的 `.ccProject`，不从 Neutral Base 用少量大 Morph 猜测重建身体。
- Morph 向量用于漂移检测、审计和未来参数化研究，不取代源项目。
- Head Scale 与 Neck Height 在最终脸型应用后写入，属于 BodyFit，不参与随机面部生成。
- 当前十体型的身体几何和头身 overlay 已通过；M05/F05 尚未完成完整服装和头发兼容矩阵。
- F05/M05 是正常成人矮身材，不是儿童体型。儿童必须建立独立骨架、比例和资产门禁。

### 6.3 历史批次边界

旧的 24 角色验收清单是原 8 BodyFit 乘 `young/middle/older` 的 Face V3 结构批次。它仍是有效历史证据，但不能证明新增 M05/F05 已完成三年龄、完整外观或 UE 导出。

当前十体型视觉样本位于 `character_showcase_10_20260803_01`，每个 BodyFit 1 个角色，已通过用户视觉验收。

## 7. 面部身份生成

### 7.1 当前唯一入口

Face V3 使用：

```text
一个完整同性主面部
+ 对应 Facial Profile
+ 主面部眼球/牙齿/口腔支撑
+ 28 个白名单局部 Morph 的小幅修改
```

禁止把多个完整整头 macro 混合，也禁止先把未主动修改的面部参数清零。

### 7.2 Seed 与配方

| 项目 | 当前数量或状态 |
| --- | --- |
| Seed 总记录 | 20，男性 10、女性 10 |
| 生产主原型 | 17 |
| 中性 seed | `M00_Neutral`、`F00_Neutral`，不进入生产身份抽样 |
| 动态拒绝 | `F09_Female_F`，满幅微笑时下排牙齿穿出下唇 |
| 确定性配方 | 200 |
| 安全局部 Morph | 28 |

冻结范围：

- 所有 `role=macro` 整头控制。
- 6 个口部随机 Morph。
- 7 个眼部随机 Morph。
- `Eyeball Move`、眼遮挡、泪线、牙齿、舌头和 corrective 支撑。
- 未登记插件 Morph 和 Headshot 命名空间。

### 7.3 Facial Profile

Facial Profile 是完整身份原子的一部分，不是动态皱纹的替代品。只加载 Head Preset 而不加载对应 Facial Profile 曾造成闭眼时眼球穿出，因此生产流程必须：

1. 加载主 Head Preset。
2. 收敛眼球、牙齿与口腔 Actor Parts。
3. 加载对应 `.ccFacialProfile`。
4. 验证 Body/Junction、静态 Face Morph 与眼球结构未被污染。
5. 再应用安全局部 Morph。

## 8. 年龄、皮肤与动态皱纹

### 8.1 当前年龄实现

当前生产 Morph：

```text
display = Full Face Elder
id      = 2025-07-04-15-29-03_pack_old_man_face
```

| 档位 | UI 值 | RLPy 权重 | 当前含义 |
| --- | ---: | ---: | --- |
| `young` | 0 | 0.0 | 青年几何 |
| `middle` | 50 | 0.5 | 中间视觉状态 |
| `older` | 100 | 1.0 | 老年面部几何 |

当前实现只改变面部，不改变身体。下一轮会把 seed 基础年龄、可选老化资格和身体老化作为独立研究项；在服装兼容完成前，身体老化不进入默认生产。

### 8.2 皮肤

- 当前生产池包含 21 套 `Age <= 23` 的 CC5 Human 2K 整体皮肤。
- 根目录：`D:\CharacterCreator_sucai\Reallusion Custom\Skin\Overall\CC5 Human 2K\ActorMIXER CORE Library`。
- 女性皮肤只用于女性完整源脸，男性同理。
- `.ccSkin` 使用严格的 `Apply Material` 对话策略并同步头身颜色。
- 不额外叠加雀斑、痘痘、泛红、疤痕或静态 Face Wrinkle SkinGen 层。
- 专门老年皮肤暂不进入默认池，避免与 Elder Morph 重复老化。

### 8.3 动态皱纹

```text
Female: ...\Actor\Expression Wrinkles\CC5 2K\HD Neutral F 2K.rlWrinkle
Male:   ...\Actor\Expression Wrinkles\CC5 2K\HD Neutral M 2K.rlWrinkle
strength = 1.0
```

动态皱纹只在表情驱动时出现。它不替代静态 Elder Morph，也不替代 Facial Profile。男女乘三年龄的 6 例基线已经登记通过。

## 9. 面部组件与毛发

### 9.1 当前生产池

| 域 | 数量 | 应用规则 |
| --- | ---: | --- |
| 牙齿 | 2 | 替换完整 Teeth ActorPart |
| 眼球 | 12 | 只选 `Material Only`，保留眼球对象与几何 |
| 眉毛 | 13 | 女性 6、男性 7；替换 Brow ActorPart |
| 睫毛 | 9 | HD Natural 成人男女共享；严格处理 Character Preset 弹窗 |
| 男性胡须 | 5 | 只用于男性；女性和儿童禁止抽样 |
| 头发 | 58 | 根据呈现分数、轮廓族和动态状态抽样 |

关键资产来源：

```text
Teeth:
  D:\CharacterCreator_sucai\Reallusion Templates\Actor\Teeth\1 Normal Teeth.ccTeeth
  D:\CharacterCreator_sucai\Reallusion Templates\Actor\Teeth\HD Teeth\_HD Teeth 2K.ccTeeth

Eyes:
  D:\CharacterCreator_sucai\Reallusion Templates\Actor\Eye\Eyes_01.ccEye
  ... through Eyes_12.ccEye

Eyebrows:
  ...\Hair\Group\Eyebrows\HD Brows_F
  ...\Hair\Group\Eyebrows\HD Brows_M

Eyelashes:
  ...\Avatar Preset\Eyelash\1.HD Natural

Beard:
  ...\Hair\Group\Beard

Scalp hair:
  ...\Reallusion Custom\Hair\Group\Hair\Hair Builder
  ...\Hair Builder 2 - eGirl
  ...\Hair Builder 3 - Edgy
```

### 9.2 眼球硬约束

- 12 套眼球用于颜色和材质多样性，不是新的眼球形状来源。
- 应用前完成最终 BodyFit 和面部身份。
- 必须保留眼球 AvatarPart、几何摘要、眼部支撑 Morph 和 `Eyeball Move = 0.0`。
- 禁止为了换眼睛把未修改的眼部参数清零。

### 9.3 毛发呈现与颜色

默认呈现使用 `presentation_score`：靠近 0 更偏男性，靠近 1 更偏女性，0.5 为中性。默认模式先按性别阈值过滤，再按非空轮廓族抽样；跨性别呈现必须显式使用 `cross_presentation`。

一个角色只抽取一次毛发色素档案，并同时写给：

```text
scalp_hair
eyebrows
facial_hair
```

颜色模式：

```text
natural_common = 0.92
natural_rare   = 0.06
dyed          = 0.02
```

自然发色由皮肤资产映射到高色素、广色素或中高色素档案。金色不会出现在非洲/亚洲高色素档案的自然常见池中，但可作为低概率罕见或显式染发。

## 10. 面部材质质量后处理

### 10.1 当前生产档案

```text
profile_id = cc_face_material_quality_v1
status     = production_approved
file       = cc_face_material_quality_profile_v1.json
```

逻辑参数：

```text
cornea:
  ScleraBrightness             0.65 -> 0.50
  Sclera Roughness             0.20 -> 0.32
  Specular Scale               0.80 -> 0.70

skin_head:
  MicroNormal Strength         0.50 -> 0.65
  Micro Roughness Scale        0.05 -> 0.08
  Original Roughness Strength  0.85 -> 1.00
  Cavity Strength              0.20 -> 0.24
```

3 个角膜参数分别写入左右眼，加上 4 个头部皮肤参数，因此每个角色执行 10 项实际写入。

### 10.2 结果与边界

- M02 Pilot 通过用户视觉确认。
- 浅色女性、深色女性、浅色男性、深色男性 `4/4` 通过。
- 共生成 `32/32` 张 baseline/recommended、双灯光、双视图对照。
- Morph 变化、Eye AvatarPart 变化、眼球几何失败、材质恢复差异和 Undo 点击均为 0。
- 完整 M02 生产路径冒烟 `1/1` 通过并保存规范化 `.ccProject`。
- 本地自动测试 `154/154` 通过。

该调整是保守的稳定增益，不会显著改变身份。它不修改肤色底色、纹理、虹膜颜色、眼球几何、SSS、wetline 或 tearline，也不能替代高质量身份原型。

## 11. 唯一 CC 角色组装顺序

机器 registry 的当前顺序：

```text
1. bodyfit_project
2. primary_head_preset
3. local_face_morphs
4. bodyfit_proportion_adjustment
5. skin
6. age_morph
7. dynamic_wrinkle_profile
8. teeth
9. eyebrows
10. eyelashes
11. eyes_material_only
12. facial_hair
13. scalp_hair
14. shared_hair_pigmentation
15. face_material_quality_profile
16. quality_assurance
```

实际执行要求：

1. 加载并校验 BodyFit 源项目哈希和身体指纹。
2. 清理源项目中不属于权威身体的外观和动画。
3. 加载一个同性交付的完整主面部与 Facial Profile 支撑。
4. 只应用配方列出的安全局部 Morph。
5. 应用 BodyFit 固定 Head Scale 与 Neck Height。
6. 应用年龄、皮肤、皱纹、牙齿、眉毛、睫毛和眼球材质。
7. 应用胡须、头发和统一毛发颜色。
8. 应用已经批准的服装 Look。
9. 在所有换肤和换眼操作之后应用材质质量档案，并逐项回读。
10. 执行静态、动态、Morph 隔离、眼球完整性和弹窗门禁。
11. 保存 `.ccProject`、manifest、截图和导出源。

后续如果再次换皮肤或眼球，必须重新应用材质质量档案。资产 API 返回成功不等于视觉兼容通过。

## 12. 服装、换发与运行时变体

### 12.1 当前状态

- 已有基础上装、裤子、鞋和男女代表 Look 的 CC 装配 Pilot。
- 旧 8 BodyFit 的外观兼容登记包含 259 条正向、1 条拒绝；47 个资产至少有正向证据。
- `M04_Heavy + M_CASUAL_02` 因下摆穿模被结构化拒绝。
- M05/F05 仍缺完整服装、头发和动态兼容矩阵。
- 用户已经购买更多服装和动画资产，但尚未全部进入统一目录、资产登记和 Look 验收。

### 12.2 服装原则

- 不允许从 shirts、coats、pants 等槽位无约束随机组合。
- 使用经过静态和动作验证的 `Look manifest`，明确互斥、叠穿和身体隐藏规则。
- 固定 10 个 BodyFit，因此每件需要换装的服装最多准备 10 个体型适配网格，不按每张脸重复。
- 需要 UE 换装时，基础身体不能被永久裁空；可以使用可逆 mask/section 隐藏减少穿模。
- shirts 和 coats 可以是两个独立 Skeletal Mesh 组件，但只有通过指定叠穿 Look 才能同时启用。
- 颜色变化优先使用 UE Material Instance，不复制几何。

### 12.3 发型和胡须

- 目标是每个正式角色准备 3 套针对最终头部验证过的发型。
- Hair Builder 发型可能由多个子网格组成，UE 运行时切换单位是完整 `HairStyleSet`。
- 首版不承诺每个角色能使用全部 58 套发型。
- 男性至少支持 `beard_none` 与一套已适配默认胡须之间切换。
- 胡须和贴头短发默认按最终角色适配，不能只按 BodyFit 推断所有脸通用。

以上三发型、胡须开关和正式 Look 系统当前为 `planned`，不是已经完成的生产接口。

## 13. 身体动画、面部动画与道具

### 13.1 已验证身体动画

```text
Audience F 01
  D:\BaiduNetdiskDownload\解压动作\Audience Motion Pack\Audience Motion Pack\Audience F 01.rlMotion

Walk Wander M
  D:\BaiduNetdiskDownload\解压动作\Studio Mocap - City Life\Motion\Studio Mocap - City Life\Walk\Walk_Wander_M.rlMotion
```

UE 中已建立两条 Body-only 派生动画，使身体动作可以与批准的面部 clip 重新组合。Walk 源动画包含面部支撑骨骼，生产重组必须使用 Body-only 派生版本。

### 13.2 UE 面部分层

当前生产 Pilot AnimBlueprint：

```text
/Game/DataMake/Animations/CC5/Pilot/ABP_DM_M02_BodyFaceLayer_v003
```

当前批准的面部状态包括：

- `neutral`
- `natural_blink`
- `blink_gaze`
- `subtle_smile`
- `hybrid_support`

Hybrid face clip 使用 8 条下颌、上下齿和舌头支撑骨骼轨道，以及 11 条眨眼、张嘴、嘴唇、嘴角和眼神曲线。`head` 与 `neck` 不进入面部分层，因此保留身体动画中的头颈运动。

M02 Post Process AnimBlueprint 的 Rig Logic 拥有最终眼球姿态。正式眼神通过 `CTRL_expressions_eyeLook*` 曲线驱动，禁止同时叠加直接左右眼骨骼轨道。

真实 PIE 验收：

```text
2 body motions x 5 face states = 10/10 passed
20 skeletal mesh components
19 followers
head/neck rotation difference = 0.000 degrees
```

### 13.3 含面部内容的 CC 动画

动画登记必须声明：

| reuse_policy | 含义 |
| --- | --- |
| `replaceable` | 身体动画无面部通道，可搭配批准面部 clip |
| `paired` | 身体和面部资产必须作为登记组合使用 |
| `locked` | 源动画的嵌入面部内容必须保留，不允许随意覆盖 |

不能把所有 CC 动画都假设为纯身体动画。

### 13.4 动作道具

咖啡杯、酒杯、箱子等通常不包含在 `.rlMotion` 本体。未来应建立动作道具池，记录道具 ID、握持手、socket、抓握偏移、出现区间和碰撞规则。第一阶段只做少量高频道具 Pilot，不从预览图自动猜测道具。

## 14. CC 到 UE 导出与导入

### 14.1 已验证 Pilot

```text
D:\UE\exports\character_creator\pilot_m02_ue58_v001\
  CC_M02_Average_Pilot_UE58.Fbx
  CC_M02_Average_Pilot_UE58.json
```

已验证的 CC 导出关键项：

- Unreal preset，Z 轴。
- `Auto Skin Rigid Mesh`。
- `Rename Duplicate Bone Name`。
- `Reset Self Illumination`。
- `Bone Name lower-case`。
- `Export JSON for Auto Material Setup`。
- `Reset Bone Scale`。
- `Epic Skeleton` + `UE5 Skeleton`。
- `Epic Skeleton Hand and Foot IK`。
- 保留需要的 Morph 和面部支撑；未经新 Pilot 不随意改变其他开关。

### 14.2 UE 导入边界

- FBX 从外部文件系统拖入 Content Browser 是复制导入，不会移动源 FBX。
- 首个完整参考角色导入时 Skeleton 选择 `None`，建立新的 CC5/UE5 Skeleton；后续兼容模块复用该 Skeleton。
- JSON sidecar 必须与 FBX 同名同目录，供 Auto Setup 生成材质。
- Reallusion Auto Setup 2.03 和 `Content/CC_Shaders` 已在 `datatry_02` 验证。
- Vendor 目录保存导入源，不移动外部包内部资产，不直接编辑 Vendor 源。
- DataMake 目录保存自己的蓝图、派生动画、配置和统一入口。

### 14.3 模块化原则

当前已验证的完整导出后 UE 拆分路径可以把身体、衣服、鞋、头发、胡须和面部组件变成独立 Skeletal Mesh。Body 是 leader，其余模块跟随同一 Skeleton。

`Set Leader Pose Component` 传播骨骼姿态，但不自动传播 Morph Target。面部 Morph/曲线必须显式广播到需要的组件。

## 15. UE 项目、场景与模块化角色

### 15.1 项目与插件

```text
Project: D:\UE\projects\datatry_02
Engine:  Unreal Engine 5.8
Auto Setup: Plugins\RLPlugin 2.03
DataMake index: D:\UE\projects\datatry_02\DataMake\dm_asset_index.json
```

项目启用了 Python、Sequencer、Movie Render Pipeline、ModelContextProtocol 等工作插件。插件存在不等于 MCP 已连接；必须以实际 tool call 或监听状态判断。

### 15.2 场景入口

Vendor 场景源保持原路径，DataMake 使用自己的关卡入口：

| 场景 | DataMake 入口 | Vendor 源 |
| --- | --- | --- |
| Dreamscape Village | `/Game/DataMake/Scenes/DreamscapeVillage/L_DM_DreamscapeVillage` | `/Game/DreamscapeSeries/DreamscapeFarmlands/Maps/Demo_Village_New` |
| Gothic Castle | `/Game/DataMake/Scenes/GothicCastle/L_DM_GothicCastle` | `/Game/Ft_Gothic_castle/Map/L_Map` |
| Tokyo Stylized | `/Game/DataMake/Scenes/TokyoStylized/L_DM_TokyoStylized` | `/Game/TokyoStylizedEnvironment/Maps/Tokyo` |

旧 Vendor 关卡不作为统一生产入口。

### 15.3 M02 模块化 Pilot

```text
Blueprint:
  /Game/DataMake/Characters/M02_Average/BP_DM_M02_ModularPilot_v002

Full reference:
  /Game/Vendor/Reallusion/CC5/Characters/M02_Average/FullReference/CC_M02_Average_Pilot_UE58

Modules:
  /Game/Vendor/Reallusion/CC5/Characters/M02_Average/Modules/_SplitPilot

Animation:
  /Game/DataMake/Animations/CC5/Pilot/ABP_DM_M02_BodyFaceLayer_v003
```

当前模块化角色有 20 个 Skeletal Mesh 组件，其中 Body 之外 19 个 follower。`BroadcastFaceMorph` 覆盖 13 个身体/面部组件，排除服装和头发。

磁盘上存在 v003 AnimBlueprint 与 HybridSupport 动画，并有 `10/10` PIE 证据。`dm_asset_index.json` 当前仍把 controller 记录为 v002；由于 2026-08-05 整理时 UE MCP 未监听，该索引差异标记为 `pending_live_ue_index_sync`，不得在未打开 UE 核对蓝图实例引用前直接改成 v003。

### 15.4 UE 年龄 Morph Pilot

CC 常规 Unreal FBX 没有直接暴露 `Full Face Elder`。当前 M02 fallback 是导出青年/老年几何快照，并在 UE 用 Geometry Script 构造 Morph。

```text
/Game/DataMake/Pilots/CC5/ElderMorph/M02_Average/v001/
  BP_DM_M02_ElderMorphPilot_v001
  Generated/SK_DM_M02_ElderMorph_Body_v001
```

它覆盖 11 个实际变化模块，`AgeAlpha=0/0.5/1.0` 与眨眼、微笑组合通过。该方案仍为 `validated_pilot`，批量化前需要拓扑和 Vertex ID 门禁。

## 16. 质量门禁与停止条件

### 16.1 每个完整 CC 角色

至少需要：

1. 全身中性正面。
2. 面部正面、三分之四和侧面。
3. 头发后侧三分之四和后面。
4. 双眼闭合与左右单眼闭合。
5. 视线向上、下、左、右。
6. 眯眼、睁大眼、抬眉和压眉。
7. 微笑。
8. 张嘴正面和三分之四。
9. Body/Junction/Face/Other Morph 隔离报告。
10. 眼球 AvatarPart、几何、支撑 Morph 与世界变换检查。

必须拒绝：

- 眼球或泪线穿出眼皮。
- 虹膜与可见眼区偏离。
- 牙齿、牙龈或舌头穿唇。
- 眉毛、睫毛、胡须或头发明显漂浮/穿模。
- 面部步骤改变 Body/Junction。
- 服装 Look 静态或动作穿模超过门限。
- 未知模态弹窗被自动确认。

### 16.2 CC 运行安全

- Agent 不自动重启离线许可证版 CC。
- CC Private Bytes 达到 `24 GiB` 时停止当前批次并由用户重启。
- 只允许精确匹配已知 Undo Manager 文本的守卫点击 `OK`。
- Apply Material、Replace、Character Preset 弹窗必须由指定任务的严格标题、控件和目标按钮策略处理。
- 未知弹窗、CC 无响应或异常关闭时停止，不猜测点击。
- 同一失败原因连续出现 3 次时停止该阶段并诊断。
- 每个任务使用新的输出目录；失败证据不覆盖、不静默删除。

### 16.3 UE 门禁

- 模块使用兼容 Skeleton。
- 20 组件中 19 个 follower 正常。
- Morph/曲线显式广播，不依赖 Leader Pose 自动传播。
- 面部层不得覆盖身体动作中的头颈。
- 眼神由 Rig Logic 曲线单一路径驱动。
- PIE 验证结束后退出 PIE、清理临时 Actor，不保存 `/Game/Main`。
- Vendor 源资产不得直接修改。
- UE MCP 离线时不能宣称完成编辑器内验证。

## 17. 已完成阶段与关键证据

| 阶段 | 状态 | 关键结果 |
| --- | --- | --- |
| 体型基线 | `production_approved` | 10 个 hash 锁定 BodyFit；高度和头颈比例 `10/10` |
| Face V3 | `production_approved` | 17 主原型、28 局部 Morph、200 确定性配方 |
| 面部资产域 | `production_approved` within adult CC5 HD scope | 2 teeth、12 eyes、13 brows、9 lashes、21 skins、5 beards、58 hairs |
| 十体型展示 | `accepted_visual_sample` | 10 个 BodyFit 各 1 个完整角色通过用户视觉检查 |
| UE 模块化 M02 | `validated_pilot` | 20 网格、19 follower、材质和 Morph 广播 |
| UE 动画阶段 1 | `validated_pilot` | 2 body x 4 face，`8/8` |
| UE Elder 阶段 2 | `validated_pilot` | `AgeAlpha=0/0.5/1.0`，11 个变化模块 |
| UE Hybrid Face 阶段 3 | `validated_pilot` | 2 body x 5 face，`10/10` |
| Aaron/M02 阶段 4 | `completed_diagnostic` | 14 张同条件图；身份几何为主要剩余差距 |
| 材质质量阶段 5A | `production_approved` | 四皮肤 `4/4`、32 图、生产冒烟 `1/1`、测试 `154/154` |

主要证据路径：

```text
00_engine/outputs/character_creator_bridge/artifacts/
  character_showcase_10_20260803_01/
  aaron_m02_quality_benchmark_20260805_01/
  m02_face_material_recommended_20260805_01/
  face_material_cross_skin_20260805_retry01/
  face_material_quality_integration_smoke_20260805_retry01/

00_engine/outputs/unreal_character_import/
  m02_layered_animation_matrix_v002.json
  m02_elder_morph_review_v001/
  m02_face_hybrid_review_v003/
```

## 18. 当前未完成事项与执行顺序

当前下一步按以下顺序执行：

1. **阶段 5B：Headshot 4 人 smoke**
   验证本机离线 Headshot 的生成、保存、重载、Facial Profile、弹窗和脚本可达性。
2. **Headshot 10/20 原型比较**
   先建立 10 个高质量候选，比较身份覆盖、重复率、失败率和人工成本，再决定是否扩到 20。
3. **阶段 6：新面部配方与年龄**
   标注 seed 基础年龄，只允许合适的青年/青中年原型生成老化变体；身体老化继续保持实验状态。
4. **阶段 7：完整 CC 外观组装**
   每个正式角色适配 3 套发型；男性建立有/无胡须；复核材质质量后处理。
5. **阶段 8：服装 Look 与十体型适配**
   建立购买资产目录、层级/互斥规则、10 BodyFit 网格和动作穿模门禁。
6. **阶段 9：动作道具 Pilot**
   为咖啡杯、酒杯、箱子等建立明确 prop binding。
7. **阶段 10：UE 统一角色接口**
   把发型、胡须、服装、颜色、身体动作、面部动画和年龄暴露为受控变量。
8. **阶段 11：端到端验收样本**
   生成可复现短视频并验证原子编辑 pair。
9. **阶段 12：生产切换与文档收口**。

当前不应提前做：

- 无约束服装随机搭配。
- 十体型尚未导出时宣称 UE 角色工厂完成。
- 任意人脸自由使用全部发型和胡须。
- 恢复眼部、口部或整头大幅随机 Morph。
- 把 Aaron 专属资产直接复制为所有角色默认值。

## 19. 机器可读权威文件索引

### 19.1 身体与比例

| 文件 | 作用 |
| --- | --- |
| `cc_body_preset_library_v2.json` | 10 BodyFit 源项目、哈希和身体 Morph 指纹 |
| `cc_head_bodyfit_scale_decisions_v1.json` | 10 BodyFit 的 Head Scale/Neck Height 决策 |
| `cc_bodyfit_height_matrix_v2_20260803.json` | 当前十体型高度测量请求 |
| `artifacts/bodyfit_height_matrix_current_20260803_01/bodyfit_height_matrix.json` | 十体型实际高度结果 |

### 19.2 面部与外观

| 文件 | 作用 |
| --- | --- |
| `cc_face_seed_library_v1.json` | 20 条完整面部 seed 记录 |
| `cc_face_identity_policy_v1.json` | 28 个安全局部 Morph 与冻结策略 |
| `cc_face_recipes_v3_200.json` | 200 条确定性 Face V3 配方 |
| `cc_facial_production_registry_v1.json` | 当前面部资产池、顺序、年龄、色素和质量档案总登记 |
| `cc_appearance_asset_catalog_v1.json` | 外观资产 ID 到本地路径映射 |
| `cc_appearance_compatibility_v1.json` | 已通过与拒绝的外观组合证据 |
| `cc_face_material_quality_profile_v1.json` | `production_approved` 皮肤/眼部质量参数 |

### 19.3 角色请求与编译

| 文件 | 作用 |
| --- | --- |
| `cc_character_integration_manifest_v1.json` | 原 8 BodyFit × 3 年龄的 24 角色 Face V3 结构基线 |
| `cc_character_showcase_10_20260803_v1.json` | 十体型完整角色展示请求 |
| `cc_character_showcase_10_static_20260803_v1.json` | 十体型静态展示请求 |
| `cc_compile_character_manifest.py` | 从白名单和兼容登记编译角色 manifest |
| `cc_validate_body_reconstruction.py` | CC 中的权威装配、验证、截图和保存执行器 |

### 19.4 动画与 UE

| 文件 | 作用 |
| --- | --- |
| `cc_unreal_animation_channel_registry_v1.json` | Body/Face 动画通道、复用政策和 v003 入口 |
| `D:\UE\projects\datatry_02\DataMake\dm_asset_index.json` | DataMake 场景、角色和动画索引；v003 controller 待在线同步 |
| `D:\UE\projects\datatry_02\datatry_02.uproject` | UE 5.8 项目与插件配置 |

### 19.5 自动化

| 文件 | 作用 |
| --- | --- |
| `00_engine/character_creator_bridge/bridge_config.json` | 队列、心跳、允许路径与协议配置 |
| `00_engine/character_creator_bridge/protocol_v1.md` | 请求、结果、心跳和恢复契约 |
| `00_engine/character_creator_bridge/cc_bridge_client.py` | 外部 CLI |
| `00_engine/character_creator_bridge/plugin/main.py` | CC5 OpenPlugin worker |

## 20. 新对话恢复检查清单

新对话只处理 Character Creator/UE 角色工厂时，按以下顺序恢复：

1. 阅读本文件顶部状态和第 18 节下一步。
2. 阅读 `STATUS.md` 最后一个日期章节，确认是否有比本文件更新的已完成工作。
3. 读取活动计划中当前阶段的验收条件。
4. 读取本阶段涉及的机器 JSON，不从聊天记忆重建参数。
5. 检查 CC 是否由用户在离线条件下启动。
6. 运行 Bridge `health`，确认 heartbeat 新鲜、`busy=false`。
7. 若需要 UE，实际调用 MCP；连接失败时停止 UE 编辑器操作，只做磁盘审计。
8. 为新运行建立新输出目录，不覆盖旧证据。
9. 执行后同时更新机器配置、`STATUS.md`、活动计划和本文件。
10. 最终汇报必须说明自动测试、视觉检查、未执行项和 CC/UE 最终状态。

## 21. 文档维护协议

### 21.1 每次任务结束前

只要发生以下任一变化，就必须更新本文件：

- BodyFit、Head Scale、Neck Height 或高度变化。
- 面部 seed、Morph 白名单、年龄或 Facial Profile 策略变化。
- 资产池数量、兼容范围或拒绝项变化。
- 唯一组装顺序变化。
- 材质参数或质量门禁变化。
- CC Bridge、弹窗或停止条件变化。
- CC 导出、UE 导入、蓝图或动画入口变化。
- 当前阶段完成或下一步改变。

### 21.2 同步规则

```text
接受决策
-> 更新源 JSON / Python
-> 运行自动测试和真实应用 smoke
-> 把结果追加到 STATUS.md
-> 更新活动计划状态
-> 更新本 Master Spec 当前结论和权威索引
```

不得只修改 Markdown 而不更新执行配置，也不得只修改代码而让本文件继续描述旧流程。

### 21.3 变更记录

| 日期 | 变更 |
| --- | --- |
| 2026-08-05 | 建立总规范；统一记录 10 BodyFit、Face V3、面部资产池、材质质量阶段 5A、CC Bridge、M02 UE v003 动画 Pilot、当前缺口和维护协议 |
