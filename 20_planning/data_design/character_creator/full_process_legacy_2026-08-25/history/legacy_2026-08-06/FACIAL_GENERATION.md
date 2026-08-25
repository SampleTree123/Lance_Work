# Character Creator 成人面部生成规范

> 文档角色：`supporting_subsystem_spec`
> 当前总规范：[`CHARACTER_FACTORY_MASTER_SPEC.md`](./CHARACTER_FACTORY_MASTER_SPEC.md)。本文件保留面部子系统细节和历史验收过程；出现冲突时，当前 10 BodyFit 状态与跨系统流程以总规范和机器配置为准。
> 更新日期：2026-08-05
> 范围：Character Creator 5 本地成人角色工厂
> 当前状态：各资产域已收口；24 个完整角色通过自动结构门禁；阶段 5A 皮肤微表面与眼部材质档案已通过四皮肤交叉验证并接入生产；新动态证据已通过单个女性完整角色的 15 姿态回归，24 角色分块重跑待执行
> 关联文档：[`README.md`](./README.md)、[`STATUS.md`](./STATUS.md)

本文是成人角色面部生成、外观装配和质量验收的当前权威说明。机器可读白名单仍以 `00_engine/scripts/character_creator` 下的 JSON 登记为准；本文负责说明设计、顺序、验证边界和当前已知风险。

## 目录

1. [当前验收状态](#1-当前验收状态)
2. [唯一生产装配流程](#2-唯一生产装配流程)
3. [身份原型、Facial Profile 与局部 Morph](#3-身份原型facial-profile-与局部-morph)
4. [年龄、皮肤和皱纹](#4-年龄皮肤和皱纹)
5. [眼球、眉毛、睫毛和牙齿](#5-眼球眉毛睫毛和牙齿)
6. [胡须、头发和统一毛发颜色](#6-胡须头发和统一毛发颜色)
7. [首版明确排除项](#7-首版明确排除项)
8. [强制质量门槛](#8-强制质量门槛)
9. [配置与机器可读登记](#9-配置与机器可读登记)
10. [后续执行顺序](#10-后续执行顺序)

## 1. 当前验收状态

### 1.1 结论总览

| 面部域 | 当前决定 | 状态 |
| --- | --- | --- |
| 身体基础 | 固定使用 10 个权威 BodyFit `.ccProject` | 已验证；原 8 套之外新增 M05/F05 矮身材 |
| 头身比例 | 每个 BodyFit 固定一组 Head Scale/Neck Height，不参与随机 | 10 套已固化；高度和 overlay `10/10` 通过 |
| 身份基础 | 一个完整同性交付主原型，不混合多个整头宏 | 17 个生产主原型已进入完整验收 |
| Facial Profile | 必须作为主原型的组成部分加载 | 24/24 完整角色运行时验证通过 |
| 局部身份 Morph | 只使用 28 个非眼部、非口部、非宏控制 | 200 条确定性配方已生成 |
| 年龄 | 只用 `Full Face Elder` 改变面部 | `0/50/100` 三档已验证 |
| 皮肤 | 21 套 `Age <= 23` 的青年 2K 整体皮肤 | 已验证 |
| 面部材质质量后处理 | 固定皮肤微表面与巩膜/角膜 7 参数档案 | 四皮肤 `4/4` 与生产冒烟 `1/1` 通过；已接入默认流程 |
| 动态皱纹 | 男女各一套 HD Neutral 2K，固定强度 `1.0` | 6 个性别/年龄组合已登记批准 |
| 眼球 | 12 套只按 `Material Only` 应用 | 资产域已验证 |
| 眉毛 | 女性 6 套、男性 7 套 | 已验证 |
| 睫毛 | 9 套 HD Natural，成人男女共享 | 资产域及 36 例 V3 极端矩阵已验证 |
| 牙齿 | 2 套完整资产替换 | 已验证 |
| 胡须 | 5 套，只用于男性 | `45/45` 组合已验证 |
| 头发 | 58 套进入生产登记 | 52 套动态批准，6 套刚性短发批准 |
| 毛发颜色 | 头发、眉毛、胡须共享一次颜色抽样 | 策略和材质写入已完成 |
| 历史完整角色批次 | 原 8 BodyFit × 3 年龄，共 24 个确定性请求 | 24/24 自动结构通过；不能覆盖新增 M05/F05 |
| 当前十体型展示 | 10 BodyFit 各 1 个完整角色 | 已通过用户视觉验收；M05/F05 完整外观矩阵仍待扩展 |
| 儿童 | 不继承成人结论 | 待单独设计 |

### 1.2 2026-07-29 闭眼与中性眼位问题（已修复）

本次事故实际包含两个连续问题：

1. **闭眼穿模**：完整皮肤和白色眼球材质暴露出仅加载 Head Preset 时缺失表情支撑。修复是把主原型的 `.ccFacialProfile` 作为身份原子状态加载，并验证它不改变静态 Body、Junction、Face Morph 或眼球对象结构。
2. **姿态检查后单眼偏移**：15 姿态测试结束、角色恢复世界位置后，CC 偶尔保留一只眼骨的旧求解缓存。修复是在恢复角色变换后发送 Morph 更新通知并用强制 `SetTime` 重新求值，最多重试 4 次，再比较双眼局部变换、T-Pose、Morph、LookAt 和世界变换。

2026-07-29 批次证明了以下结构结果：

```text
角色                    24/24 success
每例姿态定义            15
旧动态文件              360（不得再作为视觉证据）
中性眼位恢复            24/24
姿态检查后最终眼位      24/24
Body/Junction 隔离      24/24
自动结构门禁            24/24
```

后续审计发现，旧实现把临时 expression clip 放在第 1 帧以后，但
`RLPy.RGlobal.RenderImage()` 实际输出项目第 0 帧。因此这 360 个文件大多是中性帧，
不能证明 15 个姿态的视觉结果。24/24 的装配、Morph 隔离、Facial Profile、clip
数量和眼位恢复结论继续有效；“动态视觉已经通过”这一结论撤回。

### 1.3 2026-07-30 动态证据采集修复

唯一允许的面部动态取证流程是：

1. 强制求值并记录中性眼球、眼骨和待测表情通道原始权重。
2. 保存一次临时 `.ccProject` 快照。
3. 保留原 Facial Profile clip，不新增、不删除现有 expression clip。
4. 在原 clip 第 0 帧只覆盖本轮待测表情通道；未涉及通道保持原值。
5. 快照保存后先渲染并删除一张预热图，消除 CC 首帧横向构图漂移。
6. 所有正式图规范化为 `512 x 512`，保持纵横比并用场景背景色补边。
7. 姿态完成后在同一场景恢复原始通道权重并渲染中性正面基准。
8. 每个正面姿态与中性基准的缩略图 RMSE 必须不小于 `0.35`。
9. 重载快照，再比较眼球 Morph、语义对象结构和眼骨 local/basis/world 变换。
10. 项目重载会重建运行时对象 ID，并可重算参考 T-Pose；ID 不参与跨重载比较，
    T-Pose 允许 `0.5` 的记录阈值，当前世界平移仍只允许 `0.02`。
11. 临时项目和预热图必须删除，原 expression clip 数量必须恢复。

2026-07-31 在干净重启后完成 `CCINT_F01_YOUNG` 的完整角色回归：

```text
00_engine/outputs/character_creator_bridge/artifacts/
  face_v1_acceptance_f01_20260731_04/
```

该角色 `15/15` 姿态完成，14 个正面姿态的 RMSE 范围为 `0.8827` 至 `8.0621`；
姿态后眼位、Body/Junction 隔离、外观配方、Facial Profile、快照删除和 clip 数量
守恒全部通过，图片均为 `512 x 512`，未知/Undo 弹窗为 `0`。人工抽查闭眼、四向
视线、微笑、张嘴、侧面和后脑图未发现眼球或牙齿穿模。

该回归同时修复了两项仅影响门禁采样的 CC 缓存问题：

1. 角色从后脑 `-90°` 转回正面 `+90°` 时，单次眼骨世界坐标可能仍保留上一朝向；
   现在必须取得两次连续一致的完整眼骨状态后才建立比较基线。
2. 快照恢复后必须先恢复角色初始 yaw 和位置，再与运行前相同坐标系的眼位比较；
   不再把角色根节点移动误判为眼球移动。

本地 Character Creator 测试为 `132/132`。24 角色新动态证据尚未分块重跑；
当前 CC Private Bytes 为 `14.53 GiB`，仍低于 `24 GiB` 停止阈值。当前状态不能
标记为完整 24 角色视觉验收完成。

## 2. 唯一生产装配流程

后续不再保留多套面部生成路径。候选生产流程固定为：

```text
加载权威 BodyFit .ccProject
  -> 选择一个同性交付的 primary_face_seed_id
  -> 加载该 seed 的完整 Head Preset
  -> 将 BodyFit 眼球/牙齿 Actor Parts 支撑收敛到主原型目标
  -> 通过选中角色的内容加载接口应用主 Facial Profile
  -> 验证 Facial Profile 没有修改静态 Body/Head Morph 或眼球对象
  -> 只写入该配方列出的 28 项安全局部 Morph 子集
  -> 按 BodyFit 依次写入固定 Head Scale、固定 Neck Height
  -> 设置 Full Face Elder 年龄
  -> 加载一套青年整体皮肤
  -> 替换牙齿
  -> 只替换眼球材质
  -> 替换眉毛
  -> 替换睫毛
  -> 男性按配方决定是否替换胡须
  -> 替换头发
  -> 应用男女对应的 HD Neutral 2K 动态皱纹和固定强度
  -> 给头发、眉毛和胡须写入同一次毛发颜色抽样
  -> 在最终皮肤和眼球资产之后应用 production_approved 面部材质质量档案
  -> 逐项回读 10 个实际材质写入，并复核眼球完整性
  -> 执行静态、闭眼、视线、表情、后脑和全身检查
  -> 通过快照式第 0 帧取证、RMSE 活性门禁和快照恢复门禁
```

强制规则：

1. 每个角色只有一个主面部原型。
2. BodyFit 只能由 10 个权威项目加载；精确 Morph 指纹用于漂移检测，面部步骤不得改变 Body/Junction。
3. 不得把配方未列出的面部参数全部清零。
4. 不得把不同人物的整组 Eyes、Eyeball、Eyelash、Teeth 或整头宏任意混合。
5. `Eyeball Move`、眼遮挡、泪线、眨眼、视线、表情、viseme、corrective、牙齿和舌头支撑不属于身份随机化。
6. Facial Profile 必须在局部随机化前确定；动态皱纹 `.rlWrinkle` 是另一套机制，不能替代 Facial Profile。
7. 资产加载成功只说明 API 执行成功，不代表视觉兼容。
8. 任一眼球、眼睑、牙齿、头颈或身体门禁失败，整条角色配方失败。
9. Head Scale/Neck Height 属于 BodyFit 比例配置，禁止从人脸配方随机抽样，也禁止被后续面部或外观步骤覆盖。
10. 面部材质质量档案必须在最终换肤、换眼及全部外观装配后应用；后续若再次更换皮肤或眼球，必须重新应用并回读，不能假定旧值仍保留。

### 2.1 BodyFit 固定头颈比例

两个生产 Morph：

```text
Head Scale
  Morph ID: cc embed morphs/embed_full_head9

Neck Height
  Morph ID: 2019-08-30-20-14-55_neck height
```

最终参数如下；表中数值为 CC UI 值，RLPy 权重为 UI 值乘 `0.01`：

| BodyFit | Head Scale | Neck Height |
| --- | ---: | ---: |
| `F01_Lean` | -20 | -40 |
| `F02_Average` | +10 | 0 |
| `F03_Athletic` | +10 | 0 |
| `F04_Heavy` | +30 | 0 |
| `M01_Lean` | -10 | -20 |
| `M02_Average` | 0 | 0 |
| `M03_Athletic` | +10 | -20 |
| `M04_Heavy` | +30 | 0 |
| `M05_Short_Average` | 0 | 0 |
| `F05_Short_Average` | -10 | 0 |

应用约束：

1. 加载 BodyFit 和完整主面部原型、Facial Profile、局部身份 Morph 后再应用。
2. 固定顺序只能是 `Head Scale -> Neck Height`。
3. 未缩短颈部的七个 BodyFit 也必须显式写入 `Neck Height = 0`，消除 Head Preset 可能带入的残留值。
4. 运行时仅允许这两个 Morph 发生变化；其他 Morph 指纹、Eye AvatarPart、眼骨身份、LookAt 和 `Eyeball Move` 必须保持有效。
5. 这两个值不进入 `local_face_morphs`，因此换脸不会改变体型比例，也不会减少 200 条随机脸配方的身份多样性。

权威决策文件：

```text
00_engine/scripts/character_creator/
  cc_head_bodyfit_scale_decisions_v1.json
```

2026-08-01 生产运行时交叉脸型验证覆盖 `F01_Lean`、`M01_Lean`、
`M03_Athletic`，每个 BodyFit 使用两个不同主面部原型，共 `6/6` 通过：

```text
00_engine/outputs/character_creator_bridge/artifacts/
  bodyfit_proportion_smoke_v1_20260801_02/
    validation_result.json
    review/
      overview_all_bodyfits.png
```

每例均证明目标值精确落地、其余 Morph 指纹不变、眼球部件/眼骨结构不变、
近景渲染后中性眼状态恢复；批次结束后原 CC 场景 Morph 指纹精确恢复。

### 2.2 Facial Profile 加载接口

`.ccFacialProfile` 是 CC 的 Actor/Facial Profile 内容资产。当前实现使用：

```text
RLPy.RScene.SelectObject(avatar)
RLPy.RFileIO.LoadFile(profile_path)
```

禁止把下面的调用用于 `.ccFacialProfile`：

```text
avatar.GetFacialProfileComponent().LoadProfile(profile_path)
```

本机诊断中，该实验 API 对 `HD Aaron.ccFacialProfile` 持续运行超过 45 分钟且不返回，阻塞了桥接线程。该方法仍可用于已经验证过的 `.rlWrinkle` 动态皱纹资产，但两类扩展名不得混用同一加载路径。

实现层已加入扩展名硬门禁：Facial Profile 内容加载只接受 `.ccFacialProfile`，facial-profile component 的 wrinkle probe 只接受 `.rlWrinkle`。历史诊断 JSON 即使被误提交，也会在进入错误 API 前失败。

未知弹窗必须取消当前角色，不允许坐标盲点。只有精确匹配以下 Undo 文本时可以自动点击：

```text
Failed to record undo/redo step. Undo manager will restart.
```

## 3. 身份原型、Facial Profile 与局部 Morph

### 3.1 技术 seed 与生产候选

技术 seed 共 20 项，男女各 10：

```text
Male:
  M00_Neutral
  M01_Aaron
  M02_Kevin
  M03_Caleb
  M04_Male_A
  M05_Male_B
  M06_Male_C
  M07_Male_D
  M08_Male_E
  M09_Male_F

Female:
  F00_Neutral
  F01_Ariana
  F02_Camila
  F03_Katherine
  F04_Female_A
  F05_Female_B
  F06_Female_C
  F07_Female_D
  F08_Female_E
  F09_Female_F
```

当前成人 V1 生产池为 9 男 + 8 女：

- `M00_Neutral`、`F00_Neutral` 只作技术基线。
- `F09_Female_F` 在满幅微笑时出现下排牙齿穿出下唇，禁止生产抽样。
- 其余 17 项均已进入 24 角色矩阵，并通过真实眼球材质、Facial Profile 和 15 姿态自动门禁。

权威 seed 库：

```text
00_engine/scripts/character_creator/cc_face_seed_library_v1.json
```

### 3.2 Facial Profile 绑定

当前明确绑定：

```text
M01_Aaron
  D:\CharacterCreator_sucai\Reallusion Templates\Actor\Facial Profile\
    Custom Profile\CC5 HD\HD Aaron.ccFacialProfile

F01_Ariana
  D:\CharacterCreator_sucai\Reallusion Templates\Actor\Facial Profile\
    Custom Profile\CC5 HD\HD Ariana.ccFacialProfile
```

其余旧代头型暂使用同性交付的 CC5 HD Neutral profile：

```text
Male:
  ...\Custom Profile\CC5 HD\HD Neutral M.ccFacialProfile

Female:
  ...\Custom Profile\CC5 HD\HD Neutral F.ccFacialProfile
```

该映射已覆盖当前 17 个生产主原型，并通过 24 角色成人 V1 自动矩阵。后续新增头型或 CC/Profile 版本变化若失败，应优先改为：

1. 使用该完整源角色内嵌的 Facial Profile；
2. 或为该主原型保存独立、验证过的 `.ccFacialProfile`；
3. 不允许用手工调 `Eyeball Move` 掩盖 profile 不匹配。

档案绑定已显式固化在每条人脸配方和每个已编译角色中，不再只由运行时隐式推导：

```text
source_facial_profile.application_mode
source_facial_profile.path
source_facial_profile.sha256
source_facial_profile.policy_binding
```

`policy_binding` 只能是 `seed_override` 或 `default_by_sex`。生成器、manifest 编译器和 CC 验证器会分别与 seed library 交叉核对路径、SHA-256、加载模式和绑定来源。当前 200 条配方中，Aaron/Ariana 专用绑定共 23 条，其余同性交付默认绑定共 177 条；24 个完整角色 manifest 均已透传且零不匹配，17 个生产主原型均至少出现一次。

### 3.3 200 条人脸配方

当前生产算法：

```text
pipeline = complete_primary_face_plus_local_morphs_v1
recipe_count = 200
male = 100
female = 100
random_seed = 20260727
```

主文件：

```text
00_engine/scripts/character_creator/cc_face_recipes_v3_200.json
```

每条配方包含一个完整主原型、与主原型策略一致的 Facial Profile，以及在该原型基线上的少量局部变化。200 个配方 ID 和局部 Morph 指纹均唯一。加入档案元数据后以同一随机种子重建，配方 ID、主原型选择、局部 Morph 指纹及全部局部 Morph 数值均保持不变。

### 3.4 28 个安全局部 Morph

身份审计原始候选为 51 项。当前生产只允许：

| 区域 | 数量 |
| --- | ---: |
| Brow | 5 |
| Cheek | 3 |
| Ear | 5 |
| Forehead | 2 |
| Jaw/Chin | 5 |
| Nose | 8 |
| **合计** | **28** |

明确冻结：

- 10 个 `role=macro` 或整头控制。
- 6 个口部局部 Morph。
- 7 个眼部局部 Morph：Eye Angle、Depth、Height、Scale、Width、Eyeball Height、Eyeball Width。
- `CC1_Base Female`、`CC1_Base Male` 等完整角色身份宏。
- Headshot 和第三方插件命名空间。

冻结眼部局部 Morph 是保守措施。它避免新的配方继续改变眼裂与眼球关系，但不能代替 Facial Profile 修复。

精确 ID、边界和拒绝证据：

```text
00_engine/scripts/character_creator/cc_face_identity_policy_v1.json
00_engine/scripts/character_creator/cc_generate_face_recipes_v3_config.json
```

采样上限：

```text
normal_local_delta = 0.32
strong_local_delta = 0.48
ordinary_absolute_limit = 0.90
extreme_absolute_limit = 1.00
maximum_regions_modified_normal = 5
maximum_regions_modified_extreme = 7
```

同名但 ID 不同的 Morph 不得同时应用。安装新插件、增加 slider 或升级 CC 后必须重扫能力表；新增 ID 默认 `unverified`。

## 4. 年龄、皮肤和皱纹

### 4.1 年龄只改变面部

唯一年龄控制：

```text
Display: Full Face Elder
Morph ID: 2025-07-04-15-29-03_pack_old_man_face
Path:
D:\CharacterCreator_sucai\Reallusion Custom\Actor\Avatar Control\
  HD Ultimate Morphs.ccCustomSlider\Full Face Elder..ccCustomSlider
```

本地文件名含连续两个句点，不得自行改名。

| 标签 | CC UI 值 | RLPy 权重 | 解释 |
| --- | ---: | ---: | --- |
| `young` | 0 | 0.0 | 青年成人 |
| `middle` | 50 | 0.5 | 中年视觉状态 |
| `older` | 100 | 1.0 | 普通老年视觉状态 |

这三档是视觉年龄，不是精确生理年龄。身体和颈部老化 Morph 不进入首版，避免破坏 10 个 BodyFit 与服装的稳定关系。

整体 `.ccSkin` 会同时应用头部和身体材质，并启用 `Apply Head Color to Body`。但是年龄 Morph 和动态皱纹只改变面部，所以 `older` 角色在裸露上身或近景侧光下可能呈现“老年脸、青年身体”的年龄观感差异；正面图通常没有硬材质接缝。该现象属于当前明确接受的面部年龄策略，不应误判为皮肤加载失败。需要裸露身体的老年角色时，应另建身体年龄方案，而不是在本流程中临时修改 BodyFit。

当前批次分布：

```text
young  = 0.45
middle = 0.35
older  = 0.20
```

### 4.2 青年整体皮肤池

候选根目录：

```text
D:\CharacterCreator_sucai\Reallusion Custom\Skin\Overall\
  CC5 Human 2K\ActorMIXER CORE Library
```

规则固定为从文件名解析 `AgeNN`，只保留 `Age <= 23`。43 套原始资产中保留 21 套：

| 供应方目录标签 | 原始 | 保留 |
| --- | ---: | ---: |
| Female African | 4 | 2 |
| Female Asian | 5 | 3 |
| Female Caucasian | 7 | 4 |
| Female Middle East | 5 | 3 |
| Male African | 5 | 3 |
| Male Asian | 5 | 3 |
| Male Caucasian | 7 | 1 |
| Male Middle East | 5 | 2 |
| **合计** | **43** | **21** |

冻结资产：

```text
Female African:
  Age20-AlexisRogers_2k.ccSkin
  Age23-LorenaBuchanan_2k.ccSkin

Female Asian:
  Age19-MollyOno_2k.ccSkin
  Age23-ElaineDjou_2k.ccSkin
  Age23-LisaKwan_2k.ccSkin

Female Caucasian:
  Age18-NancyStevens_2k.ccSkin
  Age20-AmandaMoore_2k.ccSkin
  Age21-LoraSharp_2k.ccSkin
  Age23-SusanDavis_2k.ccSkin

Female Middle East:
  Age19-AnitaGhosh_2k.ccSkin
  Age21-AliaRay_2k.ccSkin
  Age21-FloraRahaman_2k.ccSkin

Male African:
  Age18-ThomasReed_2k.ccSkin
  Age20-JasonBower_2k.ccSkin
  Age23-LandonRozen_2k.ccSkin

Male Asian:
  Age19-DavidSoo_2k.ccSkin
  Age19-JakeNoguchi_2k.ccSkin
  Age20-JeremyShoji_2k.ccSkin

Male Caucasian:
  Age19-SamuelWalters_2k.ccSkin

Male Middle East:
  Age22-RayanRohan_2k.ccSkin
  Age23-SamirFarsut_2k.ccSkin
```

验证结果：

- `21/21` 皮肤通过，女性 `12/12`、男性 `9/9`。
- `63/63` 年龄状态完成，共 189 张固定机位图。
- `21/21` 保持 Body、身份 Morph、Eye AvatarPart 和 `Eyeball Move`。
- 不额外叠加轻微泛红、雀斑、痘痘或毛细血管层，保留皮肤自带细节。
- 目录标签仅表示供应方分类，不是真实国籍、族裔或个体身份标签。

证据：

```text
00_engine/outputs/character_creator_bridge/artifacts/
  skin_age_matrix_final_20260726_01/
```

### 4.3 静态和动态皱纹

首版排除静态 SkinGen：

```text
...\Skin\Normal Effects\1_Facial Wrinkle\Face Wrinkle F.ccSkinGenPreset
...\Skin\Normal Effects\1_Facial Wrinkle\Face Wrinkle M.ccSkinGenPreset
```

动态皱纹使用男女各一套：

```text
Female:
  ...\Actor\Expression Wrinkles\CC5 2K\HD Neutral F 2K.rlWrinkle

Male:
  ...\Actor\Expression Wrinkles\CC5 2K\HD Neutral M 2K.rlWrinkle

fixed_strength = 1.0
```

已完成男/女乘 `young/middle/older` 的 6 例年龄矩阵。动态皱纹只在表情驱动时出现，不取代静态年龄 Morph，也不取代 `.ccFacialProfile`。

### 4.4 生产面部材质质量后处理

生产档案：

```text
00_engine/scripts/character_creator/
  cc_face_material_quality_profile_v1.json

profile_id = cc_face_material_quality_v1
status     = production_approved
```

该档案不改变皮肤底色、贴图、虹膜颜色、眼球位置或几何，只在最终皮肤和眼球资产加载后应用以下小幅调整：

```text
cornea:
  ScleraBrightness            0.65 -> 0.50
  Sclera Roughness            0.20 -> 0.32
  Specular Scale              0.80 -> 0.70

skin_head:
  MicroNormal Strength        0.50 -> 0.65
  Micro Roughness Scale       0.05 -> 0.08
  Original Roughness Strength 0.85 -> 1.00
  Cavity Strength             0.20 -> 0.24
```

3 个角膜参数分别写入左右眼，连同 4 个头部皮肤参数，共执行并回读 10 项实际写入。四类皮肤交叉验证为 `4/4` 成功、`32/32` 张图片完整；Morph、Eye AvatarPart、眼球几何、材质恢复和 Undo 守卫均无异常。完整 M02 生产路径冒烟为 `1/1` 成功并保存规范化项目。`Bright` 只作为偏暖高曝光压力灯，不作为肤色身份参考。

## 5. 眼球、眉毛、睫毛和牙齿

### 5.1 眼球

批准资产：

```text
D:\CharacterCreator_sucai\Reallusion Templates\Actor\Eye\
  Eyes_01.ccEye
  Eyes_02.ccEye
  Eyes_03.ccEye
  Eyes_04.ccEye
  Eyes_05.ccEye
  Eyes_06.ccEye
  Eyes_07.ccEye
  Eyes_08.ccEye
  Eyes_09.ccEye
  Eyes_10.ccEye
  Eyes_11.ccEye
  Eyes_12.ccEye
```

规则：

- 对话框只选择 `Material Only`。
- 禁止 `Replace` 眼球对象。
- 保持 Eye AvatarPart、几何摘要、眼部支撑和 `Eyeball Move = 0.0`。
- 12 套只提供虹膜和眼球材质多样性，不提供眼睛形状。

证据边界：

- 12 套各 1 男 + 1 女，`24/24` 材质探针通过。
- `Eyes_01` 在 32 张成人脸和原 8 个 BodyFit 的轮换矩阵 `32/32` 通过；该证据不自动覆盖后增的 `M05/F05`。
- 其余 11 套依据材质只换、几何不变继承兼容结论。
- 这些结果不证明错误 Facial Profile 下的闭眼安全；完整角色仍必须重新做真实材质闭眼回归。

### 5.2 眉毛

女性 6 套：

```text
...\Hair\Group\Eyebrows\HD Brows_F\
  Female_Dense.rlHair
  Female_Filled-in.rlHair
  Female_Flat.rlHair
  Female_Petite.rlHair
  Female_Tapered.rlHair
  Female_Untamed.rlHair
```

男性 7 套：

```text
...\Hair\Group\Eyebrows\HD Brows_M\
  Male_Bushy.rlHair
  Male_Coarse.rlHair
  Male_Faint Unibrow.rlHair
  Male_Layered.rlHair
  Male_Light.rlHair
  Male_Patchy.rlHair
  Male_Segmented.rlHair
```

眉毛按 Brow AvatarPart 替换，不按普通头发或纯材质处理。13 套共 79 个成人面部组合，`79/79` 通过。

### 5.3 睫毛

成人男女共享池：

```text
...\Avatar Preset\Eyelash\1.HD Natural\
  Curled.ccAvatarPreset
  Delicate.ccAvatarPreset
  Dense.ccAvatarPreset
  Dense_Extended.ccAvatarPreset
  Lush.ccAvatarPreset
  Lush_Extended.ccAvatarPreset
  Sparse and Short.ccAvatarPreset
  Straight.ccAvatarPreset
  Thin and Drooping.ccAvatarPreset
```

规则：

- 选择 `Replace`，不是 `Material Only`。
- `Apply Character Preset` 必须精确匹配三个复选框并全部启用。
- 在面部身份和局部 Morph 完成后应用。

验证：

- 完整男女源脸 `18/18` 通过。
- 4 个 V3 极端成人脸乘 9 套睫毛，`36/36` 结构和人工检查通过。
- 每例包括中性、双眼闭合、单眼闭合和睁大眼睛。
- 该结论批准睫毛资产本身；完整角色的眼球遮挡仍服从 Facial Profile 总门禁。

### 5.4 牙齿

批准资产：

```text
D:\CharacterCreator_sucai\Reallusion Templates\Actor\Teeth\
  1 Normal Teeth.ccTeeth

D:\CharacterCreator_sucai\Reallusion Templates\Actor\Teeth\HD Teeth\
  _HD Teeth 2K.ccTeeth
```

规则：

- 完整资产 `Replace`。
- 优先在加载前移除旧牙齿对象，避免对话框阻塞。
- 允许牙齿资产写入自身必要的口腔支撑，但不得修改 Body/Junction。

两套资产覆盖原 8 个成人 BodyFit 和旧 32 张成人脸；中性、微笑和张嘴共 `64/64` 通过。该证据不自动覆盖后增的 `M05/F05`。由于口部局部 Morph 已冻结，不需要为每个体型单独制作牙齿版本。

## 6. 胡须、头发和统一毛发颜色

### 6.1 胡须

男性候选：

```text
...\Hair\Group\Beard\
  Country Style.rlhair
  Stubble.rlHair
  The Cowboy.rlhair
  Thick Chin Curtain.rlHair
  Viking.rlhair
```

5 套乘 9 张男性主面部，`45/45` 通过。胡须在皮肤和最终面部几何完成后应用；女性、儿童和未验证头型不得抽样。

胡须概率：

```text
male_facial_hair_probability = 0.45
```

### 6.2 头发池

来源：

```text
D:\CharacterCreator_sucai\Reallusion Custom\Hair\Group\Hair\
  Hair Builder\
  Hair Builder 2 - eGirl\
  Hair Builder 3 - Edgy\
```

原始 60 套中，两套因悬空花饰/蝴蝶附件不进入默认生产：

```text
Bridal-Style Braid
Graceful half up
```

当前登记 58 套：

| 状态 | 数量 |
| --- | ---: |
| `dynamic_approved` | 52 |
| `rigid_short_approved` | 6 |
| **合计** | **58** |

呈现标签：

| 标签 | 数量 |
| --- | ---: |
| `female_primary` | 42 |
| `male_primary` | 4 |
| `unisex` | 12 |

默认模式不会直接对 58 套均匀随机：

```text
male:
  female_presentation_score <= 0.5

female:
  female_presentation_score >= 0.5

then:
  先抽 silhouette_family
  再在非空族内均匀抽资产
```

这能避免男性默认抽到明显女性优先发型，同时保证每个默认性别池非空。跨性别呈现必须显式设置：

```text
hair_presentation_mode = cross_presentation
```

不得把技术兼容性和默认审美抽样混为同一个字段。

### 6.3 动态和风险边界

58 套均完成动态或刚性短发分类；另有 64 个静态压力案例覆盖高风险头型/体型组合。12 套带有已记录风险标签，例如：

- 固定颜色发圈或附件。
- 头饰/附件数量较多。
- 长发与肩部接触。
- 辫发、马尾和多部件结构。

`dynamic_approved` 不表示所有动作都绝对不会穿模。正式动画库确定后，仍需按短发、长发、辫发、马尾、盘发、mullet/undercut 等轮廓族抽样回归。

### 6.4 统一毛发颜色

一个角色只抽一次毛发颜色，并共享给：

```text
scalp_hair
eyebrows
facial_hair
```

模式概率：

```text
natural_common = 0.92
natural_rare   = 0.06
dyed          = 0.02
```

皮肤资产映射到四个色素档案：

```text
african_high_pigment
asian_high_pigment
caucasian_broad_pigment
middle_east_medium_high_pigment
```

自然常见、自然罕见和染发模式分别从档案许可的颜色池抽样。非洲和亚洲高色素档案的常见池只包含黑色、柔黑和极深棕；金色只能作为低概率自然罕见或显式染发出现。

年龄灰发比例：

```text
young:  0.00 - 0.03
middle: triangular(0.00, 0.18, 0.40)
older:  triangular(0.35, 0.65, 0.95)
dyed:   visible_gray_fraction = 0.0
```

完整色板和材质参数以生产登记为准。

## 7. 首版明确排除项

以下内容不进入首版成人角色工厂：

- 独立疤痕层。
- 额外雀斑、痘痘、泛红、毛细血管或肤色噪声层。
- 静态 `Face Wrinkle F/M` SkinGen 层。
- 专门老年皮肤。
- 身体、颈部或高龄衰弱体态 Morph。
- 浓妆和 stylized eyelash。
- 多个完整面部原型混合。
- 口部和眼部局部 Morph 随机化。
- Headshot 与第三方插件 Morph 的自动混合。
- 儿童面部和儿童资产兼容结论。

单眼皮/双眼皮作为完整主原型的自然身份差异保留，不建立单独资产轴。

## 8. 强制质量门槛

### 8.1 每个完整角色必需视图

1. 全身中性正面。
2. 面部中性正面、三分之四和侧面。
3. 头发后侧三分之四和后面。
4. 双眼完整闭合。
5. 左右单眼闭合。
6. 视线向上、下、左、右。
7. 眯眼和睁大眼睛。
8. 抬眉和压眉。
9. 微笑。
10. 张嘴正面和三分之四。

闭眼图必须使用能区分皮肤、巩膜和虹膜的真实材质。灰色一体材质只能用于拓扑观察，不能用于眼球遮挡验收。

### 8.2 必须拒绝

- 眼球穿出眼皮或离开正常眼眶。
- 闭眼时眼球、泪线或眼遮挡几何明显外露。
- 虹膜与实际可见眼区错位。
- 睫毛漂浮、穿透眼皮或闭眼时断裂。
- 眉毛漂浮、嵌入皮肤或左右绑定错误。
- 牙齿穿出嘴唇、脱离牙龈或张嘴错位。
- 胡须穿入嘴唇、脸颊、下巴或颈部。
- 头发穿头、后脑断裂或不可接受的颈肩穿模。
- 面部步骤改变 Body/Junction。
- 年轻角色中性状态被动态皱纹显著老化。
- 未知模态弹窗被自动确认。

### 8.3 自动证据

每个角色至少记录：

```text
Body/Junction fingerprints
primary_face_seed_id
Head Preset path and SHA-256
Facial Profile path and SHA-256
Facial Profile application mode and policy binding
primary Actor Parts support target and delta
local Morph IDs, baselines, targets and bounds
BodyFit proportion decision set, ordered Morph IDs, targets and actual values
Eyeball Move
Eye AvatarPart, geometry and eye-bone signatures
appearance asset IDs and hashes
hair presentation mode
pigmentation profile and selected color
CC product/API version
random seed
all required image paths
capture strategy and render warm-up result
same-scene neutral reference
per-pose RMSE liveness result
snapshot save/restore and cleanup result
visual review status
```

CC private memory达到 `24 GiB` 时必须停止提交新角色。Agent 不自动关闭或重启 CC。

## 9. 配置与机器可读登记

### 9.1 生产登记

```text
00_engine/scripts/character_creator/
  cc_facial_production_registry_v1.json
  cc_appearance_asset_catalog_v1.json
  cc_appearance_compatibility_v1.json
  cc_face_seed_library_v1.json
  cc_face_identity_policy_v1.json
  cc_face_recipes_v3_200.json
  cc_head_bodyfit_scale_decisions_v1.json
  cc_face_material_quality_profile_v1.json
```

登记中的当前组件数量：

```text
skins       21
eyes        12
eyebrows    13
eyelashes    9
teeth         2
facial_hair   5
scalp_hair   58
```

### 9.2 24 角色验收清单

```text
00_engine/scripts/character_creator/
  cc_character_integration_requests_v1.json
  cc_character_integration_manifest_v1.json
```

清单覆盖：

- 男女各 4 个 BodyFit。
- 八套固定 Head Scale/Neck Height 组合。
- `young/middle/older`。
- 当前生产主原型。
- 21 套皮肤、12 套眼球、13 套眉毛、9 套睫毛和 2 套牙齿。
- 男性有胡须和无胡须。
- 默认发型呈现过滤、轮廓族和三种发色模式。

当前 manifest 已完成自动结构验收。2026-07-29 正式汇总：

```text
00_engine/scripts/character_creator/
  cc_character_integration_automation_summary_v1.json

00_engine/outputs/character_creator_bridge/artifacts/
  character_integration_24_fixed_20260729_01/
    character_integration_final_summary.json
```

汇总器通过重复 `--result` 显式选择 24 个最终 `result.json`，因此不会把早期失败、
修复探针或重复运行混入正式结果。该汇总目前只能作为结构基线：

```text
status                         automation-complete-visual-review-pending
completed_case_count           24
pending_case_count              0
structural_pass_visual_pending 24
```

其中记录的旧动态图采用已淘汰的非零帧临时 clip 取证方式，不得用于人工动态签核。
24 例结构结果不需要重做设计或重新编译 manifest；干净重启后应把同一 24 个请求
分块重跑，使每例产生 `capture_strategy =
facial_profile_start_frame_snapshot_restore_v1` 和
`evidence_liveness.status = passed` 的新结果，再生成新的正式汇总。

2026-07-30 已把上述字段固化为汇总器硬门禁。用当前汇总器重新读取旧 24 例时，
完成结果仍为 `24/24`，但姿态验收为 `0/24`、最终状态为 `failed: 24`；这是预期的
拒绝结果，证明旧动态图不会再被误判为有效证据。

### 9.3 配置示例

```json
{
  "face": {
    "pipeline": "complete_primary_face_plus_local_morphs_v1",
    "primary_face_seed_id": "F05_Female_B",
    "facial_profile_asset_id": "CCFACEPROFILE_NEUTRAL_F",
    "face_recipe_id": "FFACEV3_0032",
    "age": {
      "label": "middle",
      "morph_id": "2025-07-04-15-29-03_pack_old_man_face",
      "weight": 0.5
    },
    "skin_asset_id": "approved_skin_asset_id",
    "eye_asset_id": "approved_eye_asset_id",
    "eye_application": "material_only",
    "eyebrow_asset_id": "approved_eyebrow_asset_id",
    "eyelash_asset_id": "approved_eyelash_asset_id",
    "teeth_asset_id": "approved_teeth_asset_id",
    "facial_hair_asset_id": null,
    "scalp_hair_asset_id": "approved_scalp_hair_asset_id",
    "hair_presentation_mode": "default",
    "hair_color_mode": "natural_common",
    "dynamic_wrinkle_strength": 1.0
  },
  "bodyfit_proportion_adjustment": {
    "application_order": ["head_scale", "neck_height"],
    "decision_set_id": "adult_head_bodyfit_scale_v1"
  }
}
```

生产请求只接受登记中的 `asset_id`，不接受 agent 临时传入任意磁盘路径。

## 10. 后续执行顺序

1. **已完成**：各资产域、头发呈现过滤、色素档案、200 条人脸配方和 24 角色 manifest。
2. **已完成**：主 Facial Profile、28 项安全局部 Morph、真实皮肤/眼球材质和 15 个姿态定义接入唯一组装流程。
3. **已完成**：闭眼穿模、中性 clip 误删和姿态后眼位缓存问题修复；24/24 自动结构验收通过。
4. **已完成**：替换失效的非零帧截图方案；快照式第 0 帧取证、预热、`512 x 512` 规范化、RMSE 活性检查和快照恢复已通过女性完整 15 姿态回归。
5. **已完成**：皮肤微表面与眼部材质档案通过 M02、四类皮肤和完整生产路径门禁，并接入 registry、manifest 和 CC 重建器。
6. **当前下一阶段**：执行 Headshot 离线 4 人 smoke，再比较 10/20 个高质量身份原型的实际收益。
7. **保留门禁**：按 BodyFit/性别分块重跑 24 角色；Private Bytes 达到 `24 GiB` 时停止。
8. **随后执行**：用新结果生成正式汇总并完成人工逐图签核，把 `visual_review_status` 从 `pending` 改为明确结论。
9. **之后执行**：保存正式 CC 项目，设计批量导出 manifest 和 FBX 导出流程。
8. **后续阶段**：补充服装与动画资产策略，再进入 Unreal 表情、动画和渲染回归。
9. **独立扩展**：儿童、第三方 HeadFit、新插件 Morph 或新 CC 版本均建立新矩阵，不继承成人 V1 结论。

任何新资产、新插件 Morph、新 Facial Profile 或新 CC 版本都不能自动继承本文结论，必须重新登记和验证。
