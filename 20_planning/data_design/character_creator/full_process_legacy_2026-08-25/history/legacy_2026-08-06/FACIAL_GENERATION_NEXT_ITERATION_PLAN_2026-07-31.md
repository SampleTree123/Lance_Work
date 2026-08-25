# Character Creator 下一轮角色质量、模块化资产与 UE 使用计划

> 文档角色：`active_plan`。本文件只描述尚未完成的阶段和验收条件；当前生产事实与唯一流程见 [`CHARACTER_FACTORY_MASTER_SPEC.md`](./CHARACTER_FACTORY_MASTER_SPEC.md)。
> 初版日期：2026-07-31
> 合并更新：2026-08-05
> 状态：阶段 5A“眼部/皮肤质量 Pilot”已通过四皮肤交叉验证并接入角色工厂；下一步进入阶段 5B Headshot smoke
> 适用范围：Character Creator 5 本地成人角色工厂、CC5 到 Unreal Engine 5.8 导入与运行时变体
> 当前生产规范：[`FACIAL_GENERATION.md`](./FACIAL_GENERATION.md)
> 当前实现状态：[`STATUS.md`](./STATUS.md)

本文件已经合并原“Headshot、年龄和面部多样性改进计划”与 2026-08-04 确认的完整角色、动画、道具、服装和 UE 模块化计划。它描述下一轮候选流程，不在验收前替换当前 Face V3 生产规则。

## 目录

1. [文档角色与版本边界](#1-文档角色与版本边界)
2. [已锁定基线](#2-已锁定基线)
3. [已确认的生产决策](#3-已确认的生产决策)
4. [目标、范围与非目标](#4-目标范围与非目标)
5. [Aaron 与 M02 质量基准](#5-aaron-与-m02-质量基准)
6. [Headshot 与高质量身份原型](#6-headshot-与高质量身份原型)
7. [面部配方与多样性](#7-面部配方与多样性)
8. [年龄系统](#8-年龄系统)
9. [唯一 CC 角色组装顺序](#9-唯一-cc-角色组装顺序)
10. [头发、发色与胡须](#10-头发发色与胡须)
11. [服装与固定 BodyFit](#11-服装与固定-bodyfit)
12. [身体动画与面部动画分层](#12-身体动画与面部动画分层)
13. [动作道具池](#13-动作道具池)
14. [CC 导出与 UE 导入](#14-cc-导出与-ue-导入)
15. [UE 模块化角色架构](#15-ue-模块化角色架构)
16. [验证与验收](#16-验证与验收)
17. [执行阶段](#17-执行阶段)
18. [机器可读产物](#18-机器可读产物)
19. [停止条件](#19-停止条件)
20. [最终文档收口](#20-最终文档收口)

## 1. 文档角色与版本边界

三个文件各自只承担一种职责：

| 文件 | 职责 |
| --- | --- |
| `STATUS.md` | 已经实现并有证据支持的事实 |
| `FACIAL_GENERATION.md` | 当前可执行的 Face V3 权威生产规范 |
| 本文件 | 下一轮完整角色工厂候选方案与执行顺序 |

执行期间不得把本计划中的未验证结论写成当前能力。每一阶段只有在结构门禁、视觉审查和可复现产物同时通过后，才能进入下一阶段或合并到权威规范。

版本隔离规则：

- 当前 `cc_face_seed_library_v1.json`、`cc_face_identity_policy_v1.json`、`cc_face_recipes_v3_200.json` 和现有 BodyFit 文件继续保留。
- 下一轮身份、年龄、毛发、服装、动作和道具登记使用新版本文件，不原地覆盖旧文件。
- Vendor 源资产保持只读；派生动画、蓝图、配置和验证资产进入 `DataMake`。
- 失败 pilot 不得改变默认角色生成入口。
- 下一轮全部验收前，不重写 `FACIAL_GENERATION.md` 的生产结论。

## 2. 已锁定基线

### 2.1 十个成人 BodyFit

当前固定体型为：

```text
M01_Lean
M02_Average
M03_Athletic
M04_Heavy
M05_Short_Average
F01_Lean
F02_Average
F03_Athletic
F04_Heavy
F05_Short_Average
```

权威清单：

```text
00_engine/scripts/character_creator/cc_body_preset_library_v2.json
```

这些 BodyFit 的源项目、Morph 指纹、身高和固定 Head Scale/Neck Height 已验收。下一轮不得重新随机体型，也不得让面部、年龄或外观步骤污染 Body/Junction。现有比例 overlay 继续由当前决策文件控制；需要变更时必须另开专项视觉实验。

### 2.2 当前面部与外观基线

当前有效基础包括：

- 17 个 Face V3 生产主原型。
- 200 条确定性人脸配方。
- 28 个非眼部、非口部安全局部 Morph。
- 完整主原型、Facial Profile、眼球/牙齿支撑的成对加载规则。
- 2 套牙齿、12 套眼球材质、13 套眉毛、9 套睫毛。
- 21 套青年 2K 整体皮肤、5 套男性胡须、58 套已登记头发。
- 当前动态皱纹、毛发色素档案和弹窗守卫。

这些资产池继续作为下一轮的稳定对照，不因质量升级计划而失效。

### 2.3 当前 UE 技术基线

`M02_Average` 已经完成：

- CC5 到 UE 5.8 整合参考导入。
- 20 个独立 Skeletal Mesh 的模块化拆分。
- Body 作为 leader，另外 19 个组件跟随。
- 服装、鞋、头发、胡须和面部组件的材质复用。
- 两条 `.rlMotion` 身体动画导入。
- Audience 与 Walk 两条 Body-only 派生动画。
- `neutral / natural_blink / blink_gaze / subtle_smile` 四条可复用面部曲线 clip。
- `ABP_DM_M02_BodyFaceLayer_v002` 已完成 `2 body x 4 face` PIE 矩阵。
- `BP_DM_M02_ModularPilot_v002` 面部 Morph 广播与曲线传播验证。

当前 UE pilot 是架构证明，不是十个 BodyFit 的批量生产结果。

### 2.4 不回退边界

- 不重新开放任意整头、眼部、口部或未知插件 Morph 随机化。
- 不假设 `Leader Pose` 会自动完成 Morph 广播、毛发贴合或服装 Conform。
- 不移动 Vendor 已导入资产；`DataMake` 只保存本项目的引用、派生资产、蓝图和配置。
- 不覆盖或保存 `/Game/Main` 的临时预览修改。
- 不把机器检查成功等同于视觉验收成功。

## 3. 已确认的生产决策

| 领域 | 已确认决策 |
| --- | --- |
| 身体 | 固定使用 10 个 BodyFit，不按角色继续随机体型 |
| 面部 | 身份首先来自完整高质量主原型，再叠加小幅安全局部 Morph |
| 原型数量 | 不预先冻结为 40；先比较 10 个与 20 个原型的实际收益 |
| 年龄 | 年龄是可选变体，不是每个角色必有；只允许合适的青年或青中年基线生成老化变体 |
| 身体老化 | 纳入研究，但在服装兼容性验证前不进入默认生产 |
| 头发 | 每个正式角色准备 3 套针对最终头部验证过的可替换发型 |
| 发色 | 与眉毛、胡须共享角色级毛发色素档案；UE 中优先用材质切换 |
| 胡须 | 男性角色至少支持 `none` 与一套已适配胡须之间切换 |
| 眉毛/睫毛 | 随最终面部适配；首版不声明跨任意角色自由更换 |
| 服装 | 每件服装最多按 10 个 BodyFit 生成适配网格，不按人脸重复 |
| 搭配 | 使用已验证 Look manifest，不做无约束层级随机组合 |
| 动画 | 身体动作与面部表情独立组合，不把每个组合烘焙成一条新源动画 |
| 道具 | 动作与道具分离管理；需要道具的动作禁止无道具渲染 |
| UE | 模块化角色通过数据资产和统一蓝图切换发型、胡须、服装、动作和表情 |

## 4. 目标、范围与非目标

### 4.1 本轮目标

1. 定位当前随机角色与官方 Aaron 角色的主要质量差距。
2. 验证 Headshot 是否能稳定提供更高质量的完整成人身份原型。
3. 用 10/20 原型对照决定下一版身份池规模，而不是按预设数量扩充。
4. 将年龄从单一 `Full Face Elder` 改为受控、可选、可审核的年龄档案。
5. 建立唯一且可复现的完整 CC 角色组装顺序。
6. 为每个角色建立 3 套发型和男性有/无胡须的 UE 变体能力。
7. 建立十个 BodyFit 的服装兼容、Look 搭配和动作穿模门禁。
8. 将身体动作、面部表情和交互道具拆成可组合的数据层。
9. 把已经验证的 CC 内容可靠导入 UE，并形成统一运行时角色接口。
10. 用小规模端到端角色集证明生成、导出、导入、换装、动画和短视频配置可复现。

### 4.2 本轮非目标

- 儿童和未成年人角色。
- 让任意角色自由使用全部头发或全部胡须资产。
- 无限制随机叠加 shirts、coats、dresses 和配饰。
- 在 UE 中实时重新执行 CC 的头发贴合或服装 Conform。
- 首轮引入 SkinGen 疤痕、复杂妆容或大量配饰。
- 在没有 pilot 的情况下承诺所有长发物理都能复用同一种运行时方案。
- 直接替换当前 Face V3，而不保留回退路径。

## 5. Aaron 与 M02 质量基准

### 5.1 对照对象

官方参考：

```text
D:\CharacterCreator_sucai\Reallusion Templates\Project\CC Project\1.HD Talking Aaron.ccProject
```

当前参考：已验收的 `M02_Average` 完整角色项目与 UE M02 modular pilot。

Aaron 项目体积约 705 MiB，当前 M02 展示项目约 196 MiB。文件体积不是质量指标，但说明二者包含的纹理、精修状态和项目内容不同，必须拆分比较，不能只通过增大随机 Morph 解决。

### 5.2 统一比较条件

两个角色必须使用相同的：

```text
CC 版本
场景与背景
相机焦距、距离与曝光
三点或统一 HDRI 灯光
中性姿态与相同测试动作
实时细分等级
截图分辨率
```

每个角色至少输出：

```text
front close-up
three-quarter close-up
profile close-up
full body
blink
smile
mouth open
```

### 5.3 分层诊断

建立四组对照：

1. **完整外观对照**：各自原生皮肤、眼睛和毛发，评估最终观感。
2. **几何对照**：去除头发/胡须并使用统一中性材质或标准皮肤，评估轮廓、眼睑、嘴唇和面部结构。
3. **材质对照**：保留各自原生皮肤，使用相同灯光近景检查色素、微法线、粗糙度、油脂和 SSS。
4. **动态对照**：使用同一眨眼、微笑和张嘴目标，评估 Facial Profile、corrective 和动态皱纹。

诊断字段：

```text
identity_geometry
skin_albedo
micro_normal
roughness_specular
subsurface_response
eye_and_tearline
facial_profile
dynamic_wrinkle
hair_and_beard
lighting_sensitivity
```

### 5.4 决策规则

- 如果统一材质后差距仍大，优先升级完整身份原型和局部雕塑质量。
- 如果几何接近但原生皮肤差距大，优先扩充高质量皮肤和材质配置。
- 如果静态接近但表情差距大，优先校准 Facial Profile、corrective 和动态皱纹。
- 如果只在原项目灯光下差距大，先统一渲染条件，不错误修改角色。
- 不以扩大随机 Morph 振幅作为第一修复手段。

### 5.5 2026-08-05 首轮执行结论

首轮决策级基准已完成。Aaron 与 M02 分别生成中性正面、四分之三、侧面、全身、双眼眨眼、微笑和张口 7 张 `1536 x 1536` 图片，共 14 张。两者使用相同相机、Lightroom、角色位置、截图模式和姿态目标；项目恢复、眼部状态恢复和临时快照清理均通过。

结构门禁通过：M02 未见头身比例错误、眼球偏离、闭眼穿模、牙齿穿模或表情通道失效。主要感知差距按优先级为：

1. `P0` 眼白、角膜高光、泪线与中性眼神融合。
2. `P1` 皮肤区域色素、微法线、粗糙度、高光和 SSS 响应。
3. `P1` 身份几何的次级结构、自然不对称和年龄痕迹。
4. `P2` Facial Profile 的变形幅度、眼周/面颊联动和动态皱纹。
5. `P2` 头发与胡须的根部、密度和材质融合。

本轮没有执行统一中性材质、皮肤互换、动态皱纹隔离和多灯光材质响应，因此这些项目不能被写成最终根因结论。它们转入阶段 5A 的小型质量 Pilot，不阻塞阶段 4 的优先级决策。

正式证据：

```text
00_engine/outputs/character_creator_bridge/artifacts/
  aaron_quality_benchmark_20260805_03/
  m02_quality_benchmark_20260805_03/
  aaron_m02_quality_benchmark_20260805_01/
    aaron_m02_quality_benchmark.json
    AARON_M02_QUALITY_GAP_REPORT.md
    aaron_m02_contact_sheet.png
    aaron_m02_geometry_sheet.png
    aaron_m02_expression_sheet.png
```

## 6. Headshot 与高质量身份原型

### 6.1 能力边界

Headshot 适合从清晰成人人像建立可编辑 CC 头部，但不预设达到扫描级复原。结果受图像朝向、焦距、遮挡、表情、光照和人工校正影响。第一轮先验证本机离线环境中的生成、保存、重载和脚本可达范围。

### 6.2 来源图片规范

首轮来源建议：

```text
成人，优先 18-29 岁青年基线
接近正面，头部无明显俯仰和旋转
中性表情，嘴部自然闭合
视线看向相机
人脸有效区域尽量不低于 1024 x 1024
均匀光照，无强侧光和硬阴影
无眼镜、口罩、手部遮挡和厚重刘海
无明显广角畸变、滤镜或几何修脸
```

为复现而记录：

```text
source_id
source_path
sha256
estimated_source_age_range
sex_presentation
appearance_group
headshot_mode
manual_adjustments
notes
```

### 6.3 数量采用递进比较

| 阶段 | 数量 | 目的 |
| --- | ---: | --- |
| Smoke | 4，男女各 2 | 验证生成、保存、重载、弹窗和自动化边界 |
| 第一批质量池 | 10，男女各 5 | 与当前 17 原型比较身份差异和合格率 |
| 第二批质量池 | 20，男女各 10 | 判断从 10 增至 20 的边际收益 |
| 后续扩展 | 待比较结果决定 | 不提前冻结为 40 或更大 |

只有当 20 原型相较 10 原型仍明显增加有效身份覆盖，且合格率、动态安全和人工成本可接受时，才继续扩充。

### 6.4 完整身份原子

一个生产主原型不是一组孤立 Morph，而是：

```text
完整 Head Preset
+ 对应 Facial Profile
+ 眼球/眼睑支撑状态
+ 牙齿/口腔支撑状态
+ Headshot 与必要人工修正记录
+ 静态和动态验证证据
```

每个角色仍只加载一个完整主原型，不把多个整头 macro 任意叠加。

### 6.5 单个原型流程

1. 加载同性别 `M02_Average` 或 `F02_Average` 干净 BodyFit。
2. 运行 Headshot 并记录模式和人工调整。
3. 保存完整 `.ccProject` 快照。
4. 保存可用的 Head Preset 与 Facial Profile。
5. 扫描 Head、Face、Body、Junction、Eye、Teeth 和表达支撑状态。
6. 去除头发、胡须和非必要配饰，生成标准化预览。
7. 使用标准皮肤和标准眼球检查纯几何。
8. 执行中性、眨眼、视线、微笑、张嘴、侧面和后脑门禁。
9. 计算文件 hash、Morph 指纹和对象结构摘要。
10. 人工标记 `accepted`、`repairable` 或 `rejected`。

### 6.6 拒绝条件

- 中性状态眼球或眼睑位置异常。
- 眨眼、视线或睁大眼时穿模。
- 微笑、张嘴时牙齿、舌头、嘴唇或下颌异常。
- 面部明显不对称且不是预期身份特征。
- 侧面颅骨、鼻梁、嘴凸或后脑轮廓明显失真。
- Head/Neck/Junction 污染固定 BodyFit。
- Facial Profile 无法稳定恢复。
- 标准皮肤替换后几何质量明显下降。
- 青年基线在无年龄 Morph 时仍明显表现为中老年。

## 7. 面部配方与多样性

### 7.1 多样性优先级

```text
更多合格完整主原型
  > 主原型均衡采样
  > 小幅安全局部 Morph
  > 可选年龄档案
```

不得为了快速增加差异重新开放眼部、口部、整头 macro、未知插件 Morph 或 Headshot 命名空间随机化。

### 7.2 局部 Morph

第一轮继续以当前 28 个安全局部 Morph 为候选：

```text
Brow      5
Cheek     3
Ear       5
Forehead  2
Jaw/Chin  5
Nose      8
```

新原型增加后重新校准当前局部 delta。优先降低或维持幅度，不直接增大。每条配方必须：

- 只引用一个完整主原型。
- 绑定该原型对应的 Facial Profile。
- 禁止同语义重复 Morph 并用。
- 限制普通配方修改区域数。
- 保持眼部、口部、牙齿、舌头、viseme 和 corrective 支撑不变。
- 在最终年龄与外观应用后重新进行视觉审核。

### 7.3 去重与覆盖

采用三层检查：

1. Morph 指纹和头部结构摘要。
2. 标准皮肤、无毛发状态下的正面、四分之三和侧面图像相似度。
3. 人工联系表检查同脸、近似脸、平均脸和异常脸。

相似度阈值由 10/20 原型 pilot 建立，不在没有本地数据时预设固定值。

### 7.4 质量与数量取舍

- 正式池宁可保留较少高质量原型，也不接收结构不稳定的身份。
- 当前 Face V3 继续作为对照和回退。
- 新原型质量达到 Aaron 的程度不是单一硬门槛，但必须明确比当前低质量平均脸改善了哪个维度。
- 每次扩池同时报告新增身份覆盖、近似重复率、动态失败率和人工修正时间。

## 8. 年龄系统

### 8.1 年龄是可选变体

不是所有角色都必须生成 `middle` 或 `older`。角色先完成身份与青年基线审核，再决定是否允许年龄变化。

建议字段：

```text
prototype_baseline_apparent_age
age_variant_eligible
target_age_profile
target_apparent_age_range
final_apparent_age_review
```

只有青年或青中年基线、且结构门禁通过的原型可以生成明显老化变体。原型本身已明显老年时，不再叠加完整老化层。

### 8.2 年龄档案

候选档案：

| 档案 | 视觉目标 | 使用规则 |
| --- | --- | --- |
| `young` | 18-29 | 身份基线；年龄 Morph 为 0 |
| `middle` | 35-55 | 可选，中等面部老化 |
| `older` | 60-80 | 可选，较强但受控的面部与身体老化 |

年龄档描述视觉目标，不声明精确生理年龄。

### 8.3 面部年龄 Morph 审计

重新扫描：

```text
age
elder
old
wrinkle
nasolabial
eye bag
cheek
jowl
lip
```

每项分类为：

```text
face_only
body_or_neck
eye_risk
mouth_risk
macro
plugin_namespace
unknown
```

只有不污染 Body/Junction、不破坏眼球/眼皮/牙齿/口腔支撑并通过动态姿态的项目才能进入白名单。

### 8.4 UE 面部 Elder Morph 导出 Pilot

在扩展年龄档案前，先只使用 `M02_Average` 和 `Full Face Elder` 验证 CC 到 UE 的可调年龄 Morph 链路。本阶段不修改十个 BodyFit，也不引入身体老化。

固定执行顺序：

1. 以青年状态作为基础网格，尝试将 `Full Face Elder` 作为 Morph Target 导出，而不是只烘焙老年结果。
2. 导入独立 UE Pilot 目录，不覆盖当前 M02 正式参考资产。
3. 验证 UE 中存在年龄 Morph，并检查 `0 / 0.5 / 1.0` 三档。
4. 同时检查眼球、眼皮、牙齿、嘴唇、颈部 Junction 和动态表情。
5. 检查眉毛、睫毛、胡须和发际线组件是否包含并正确响应同名 Elder Morph。

判定分支：

```text
all_components
  Body 与需要贴合的毛发组件都有 Elder Morph，可统一驱动

body_only
  只有 Body 有 Elder Morph；必须补充组件修正 Morph 或使用年龄适配变体

not_exportable
  CC 无法直接导出该滑块；导出青年/老年同拓扑网格后构造 Morph Target
```

`Leader Pose` 只传播骨骼姿态，不传播 Body 顶点形变。只有组件自身包含对应 Morph Target 时，`AgeAlpha` 广播才有意义。首轮只验证一名角色和一套眉毛、睫毛、胡须、头发组合，不批量扩展。

完成标准：明确 CC 是否能导出可调 Elder Morph、哪些模块可同步响应，以及 UE 年龄滑块是否能在眨眼、微笑和张嘴时保持眼口安全。

**2026-08-04 执行结果：阶段 2 已完成。**

最终判定为 `not_exportable -> fallback_all_components`：CC 的常规 UE FBX 导出没有把 `Full Face Elder` 暴露成可调 Morph Target，青年和老年快照中可直接识别的年龄 Morph 数量均为 `0`；随后使用青年/老年几何快照和 Geometry Script 构造了同名 Morph。该后备路线在所有实际受年龄几何影响的模块上形成了可统一广播的 `Full_Face_Elder`。

| 分类 | UE 组件 | 结论 |
| --- | --- | --- |
| 年龄驱动 | `Body`、眉毛、上下睫毛、下巴胡须、颈部胡茬、八字胡、4 个头发子组件 | `11/11` 含 `Full_Face_Elder` 并在 PIE 中同步响应 |
| 几何不变 | 眼球、Eye Occlusion、Tearline、牙齿、舌头 | 青年/老年顶点差为 `0`，不需要伪造年龄 Morph |
| 非面部排除 | T-shirt、牛仔裤、鞋 | 仅有导入浮点噪声或完全不变，不进入年龄广播 |

运行时 Pilot 为：

```text
/Game/DataMake/Pilots/CC5/ElderMorph/M02_Average/v001/
  BP_DM_M02_ElderMorphPilot_v001
  Generated/SK_DM_M02_ElderMorph_Body_v001
```

真实 PIE 中共存在 `20` 个骨骼网格组件，年龄支持集合在全部 6 个用例中保持一致。`AgeAlpha=0 / 0.5 / 1.0` 呈现连续的青年、中间和老年几何；`AgeAlpha=1` 时双眼眨眼与轻微微笑均正常，未见眼球、眼皮、嘴唇、胡须或发际线脱离。表达式动态验收必须在 PIE 中通过动画曲线完成；编辑器世界直接调用 `SetMorphTarget` 会受到 Post Process AnimBlueprint 曲线求值影响，不能作为动态表情是否生效的最终证据。

张嘴用例中 `CTRL_expressions_jawOpen=0.65` 已在运行时精确到达，当前截图未见穿模，但开口幅度很小。该曲线只能证明 Morph 通道可达，不能替代下颌、牙齿和舌头支撑骨骼，因此“完整张嘴安全”转为阶段 3 的硬门禁，不在本阶段误判为已经完成的混合面部动画。

已知边界：

- UE 导入后的 Body 青年/老年 Source Model 顶点数为 `59295 / 59297`；Geometry Script 写入成功且三档运行结果连续，但该 2 顶点漂移不能泛化为任意角色都可直接构造 Morph。批量化前必须增加拓扑、Vertex ID 和视觉门禁。
- CC 快照包含 `19` 个网格，没有单独导出当前模块化蓝图中的 TearDuct；Pilot 保留原蓝图的中性 TearDuct，因此运行时仍为 `20` 个组件。后续正式导出需要明确登记该组件来源。

正式证据：

```text
00_engine/outputs/unreal_character_import/
  m02_elder_morph_snapshot_import_v001.json
  m02_elder_body_morph_build_v001.json
  m02_elder_component_morph_build_v001.json
  m02_elder_morph_pilot_blueprint_v001.json
  m02_elder_morph_review_v001/pie_review.json
  m02_elder_morph_review_v001/m02_elder_morph_pie_contact_sheet.png
```

### 8.5 身体老化

身体老化纳入下一轮研究，但与面部老化分开登记：

```text
body_age_profile
posture_age_morphs
neck_age_morphs
hand_age_material_or_morph
clothing_refit_required
```

身体年龄 Morph 可能改变胸腔、肩、背、腹部、颈部和姿态，从而使现有服装失配。因此：

1. 先在裸体或标准紧身测试服上验证几何。
2. 检查是否改变固定 BodyFit 身份。
3. 检查站立、行走和抬臂姿态。
4. 对实际使用的老年角色单独生成服装适配版本。
5. 在服装影响未量化前，身体老化不得进入默认批量生产。

### 8.6 皮肤与动态皱纹

- 当前青年皮肤池继续作为第一轮标准皮肤来源。
- 皮肤本身明显老年时，不叠加完整静态老化层。
- 动态皱纹继续使用已验证配置作为基线，但强度是否按年龄变化由 pilot 决定。
- 最终年龄必须结合几何、皮肤、动态皱纹和身体状态共同审核。

## 9. 唯一 CC 角色组装顺序

下一轮候选流程只有以下一条，不保留多个并行组装算法：

```text
1. 加载 hash 锁定的 BodyFit .ccProject
2. 清理 BodyFit 源项目中的非权威外观和动画
3. 加载一个完整主面部原型
4. 绑定该原型的 Facial Profile 与眼口支撑
5. 应用受限的安全局部身份 Morph
6. 应用 BodyFit 固定 Head Scale -> Neck Height
7. 可选应用面部年龄档案
8. 可选应用已验收身体年龄档案
9. 应用整体皮肤并同步头身颜色
10. 应用动态皱纹
11. 应用眼球、牙齿、眉毛和睫毛
12. 抽取角色级毛发色素档案
13. 为最终头部适配并验证 3 套头发
14. 男性角色适配默认胡须，并建立 none 变体
15. 应用一个已批准 Look 服装组合
16. 在最终皮肤和眼球资产之后应用锁定的面部材质质量档案
17. 执行静态、动态、隔离和弹窗门禁
18. 保存规范化 .ccProject、manifest 和导出源
```

关键约束：

- Head Scale/Neck Height 必须在最终脸型后应用，并且不进入随机面部 Morph。
- 头发和胡须必须在最终头部几何后适配。
- 服装只服从 BodyFit 和可选身体年龄状态，不服从人脸身份。
- 面部材质质量档案必须在最终皮肤和眼球资产应用后执行，并在预览、保存和导出前逐项回读；后续换肤或换眼后必须重新应用。
- 动画不烘焙进权威静态角色源项目；动画与角色通过 manifest 组合。
- 每一步记录应用前后 Morph 指纹、对象变化和资产 hash。

## 10. 头发、发色与胡须

### 10.1 每个角色三套发型

每个正式角色必须具有：

```text
hair_style_0 = 默认发型
hair_style_1 = 已适配替换发型
hair_style_2 = 已适配替换发型
```

三套发型都在该角色最终脸型、Head Scale 和 Neck Height 完成后于 CC 中应用、贴合和验证。UE 不负责重新执行 CC 的 Conform。

### 10.2 发型是多网格集合

Hair Builder 发型可能由多个子网格组成，因此运行时单位是 `HairStyleSet`，不是单一 Skeletal Mesh：

```text
hair_style_id
source_asset_id
character_id
head_fit_id
mesh_parts[]
material_slots[]
physics_mode
color_profile_ids[]
validation_status
```

UE 切换时必须同时清空旧发型全部子组件，再装入新发型的全部子组件。

### 10.3 复用策略

- 离头皮较远、宽松的发型可以在通过交叉验证后共享。
- 贴头短发、刘海和紧贴发际线的发型默认按角色适配。
- `head_fit_id` 可在后续用于复用，但首版不以聚类代替逐角色三发型承诺。
- 不要求每个角色拥有全部 58 套发型。

### 10.4 发型门禁

每套发型至少检查：

```text
front / three-quarter / profile / back
brow raise
blink
smile
head yaw / pitch
walk
raised arms
```

检查发际线、额头、耳朵、后脑、颈部和肩部穿模。长发还需检查胸、背和服装碰撞。

### 10.5 毛发物理

- 无额外物理骨骼的发型可直接作为 Body follower。
- 含额外骨骼或物理的长发可能需要 `Copy Pose From Mesh` 后运行专用 AnimBP、AnimDynamics 或 Chaos。
- 第一版换发 pilot 优先选择不依赖复杂物理的 3 套发型。
- 复杂长发只有在专用物理路径通过后才能进入生产池。

### 10.6 发色

角色只抽取一次毛发色素档案，并用于头发、眉毛和胡须。发色优先在 UE 中通过 Material Instance 或参数化材质切换，避免为颜色复制几何。

保留模式：

```text
natural_common
natural_rare
dyed
```

默认数据使用 `natural_common`；罕见和染发模式必须显式请求。

### 10.7 胡须开关

男性角色至少支持：

```text
beard_mode = none
beard_mode = fitted_default
```

实现要求：

- CC 导出时不得把胡须和眉毛合并。
- 胡须可以由多个子网格组成，运行时作为一个 `BeardStyleSet` 开关。
- 关闭胡须时同时关闭可见性、碰撞和隐藏阴影。
- 皮肤不得带无法关闭的明显烘焙胡须；允许轻微自然胡茬，但必须登记。
- 默认无胡须但需要有胡须 pair 的角色，必须先在 CC 中适配一套胡须。
- 胡须颜色跟随角色毛发色素档案。

## 11. 服装与固定 BodyFit

### 11.1 数量边界

面部身份不改变 Body/Junction，因此服装变体维度是：

```text
garment_id x supported_bodyfit_ids
```

而不是：

```text
garment x BodyFit x face x skin
```

每件服装最多生成 10 个 BodyFit 适配网格，但只为实际支持的体型导出，不机械复制全部组合。

### 11.2 服装层级

统一槽位：

```text
base_underwear
top_inner
top_outer
bottom
dress_or_one_piece
legwear
shoes
gloves
accessory
```

互斥和依赖规则示例：

- `dress_or_one_piece` 与普通 `top_inner + bottom` 默认互斥。
- `top_outer` 只能与白名单 `top_inner` 组合。
- shirts 与 coats 不因槽位不同就自动兼容。
- 鞋、袜子和裤脚必须成组检查。
- 高领、围巾、帽子受 Head Scale/Neck Height 和头发影响，单独登记。

### 11.3 Look manifest

使用经过验证的整体 Look，而不是运行时无约束随机层叠：

```text
look_id
sex_presentation
supported_bodyfit_ids[]
garment_parts[]
layer_order
body_hide_mask
allowed_hair_styles[]
colorway_ids[]
motion_validation[]
known_risks[]
status
```

### 11.4 适配与验证

每个服装版本必须：

1. 在目标 BodyFit 上由 CC Conform。
2. 检查基础身体是否需要隐藏区域。
3. 保留用于换装的完整基础身体；不得不可逆删除未记录的身体网格。
4. 验证中性、行走、抬臂、肘部弯曲、躯干扭转和坐姿候选。
5. 检查内外层服装之间以及服装与身体之间的穿模。
6. 记录适配方式、碰撞设置和已知风险。

### 11.5 第一批服装 pilot

先在 `M02_Average` 和 `F02_Average` 建立：

```text
Look A：单层日常服装
Look B：第二套完整日常服装
Look C：inner + outer 分层压力测试
```

三套通过后再扩展到其他 BodyFit。最终每个角色需要多少 Look，由实际数据 pair 需求决定，不在本计划中提前冻结。

## 12. 身体动画与面部动画分层

### 12.1 当前 pilot 的边界

`A_CC_Audience_F_01_BodyFaceDemo_v001` 已证明身体动作和面部曲线可以同时播放，但它把表情直接写入一条派生动画，只适合验证，不适合规模化组合。

### 12.2 正式分层

```text
Body Motion Layer
  身体、Root Motion、手指、脖子和头部

Face Curve Layer
  blink / gaze / idle / smile / speech curves

Face Bone Layer
  eyes / jaw / teeth / tongue / facial support bones

Sequencer or Runtime Controller
  决定片段时间、混合权重和随机种子
```

身体源动画中的眼球、下颌、牙齿、舌头、面部 Morph 曲线必须审计；Body-only 派生资产保留脖子和头部动作，但移除可替换的面部支撑骨骼及面部曲线，不修改 Vendor 源动画。

### 12.3 第一轮验收矩阵

使用两条现有身体动作：

```text
Audience F 01
Walk_Wander_M
```

分别组合：

```text
neutral idle face
natural blink
blink + gaze
subtle smile
```

同一面部 clip 必须能与两条身体动作组合，而不复制成两套源动画。检查循环接缝、眨眼频率、视线、嘴角和模块化 follower。

### 12.4 面部内容策略

每条身体动画登记以下面部策略，不能只用“有/无表情”布尔值：

```text
replaceable
  不含面部内容，可自由搭配 Face clip

paired
  已拆成 Body-only + Face-only，默认成对使用但允许显式替换

locked
  完整表演不可拆或不应替换，禁止再叠加其他面部动画
```

同时登记：

```text
facial_channels = none | curves | bones | hybrid
paired_face_clip_id
```

### 12.5 面部骨骼与曲线混合层

阶段 1 的 `ABP_DM_M02_BodyFaceLayer_v002` 保留为曲线分层稳定基线。面部骨骼 pilot 新建 `v003`，不得原地覆盖 `v002`。

`v003` 使用 `Layered Blend per Bone` 覆盖眼球、下颌、牙齿、舌头和面部支撑骨骼，并明确排除 `neck` 与 `head`，随后合成面部 Morph 曲线。首个 Face-only hybrid clip 至少包含眼球转动、下颌张合、一项舌头或牙齿动作和一组嘴唇或脸颊曲线。

完成标准：同一 Face-only hybrid clip 可组合 Audience 与 Walk；Walk 的脖子扭动不被覆盖；眼球、下颌、牙齿、舌头、Morph 曲线和 19 个 follower 同时正常，无重复驱动或穿模。

### 12.6 目标实现

- AnimBlueprint 负责持续身体姿态、面部骨骼层和面部曲线层。
- Sequencer 负责短视频中的 clip 时间、相机和事件。
- 静态蓝图函数保留作检查和显式设置，不承担高频连续动画。
- 身体动作、面部动作和最终角色通过 ID 组合写入渲染 manifest。

## 13. 动作道具池

### 13.1 基本原则

普通 `.rlMotion` 按身体动作处理。预览中的杯子、手机、箱子等不视为动作文件自带网格。任何看起来在持物的动作都必须标记 `requires_prop`；没有兼容道具时禁止进入正式渲染。

### 13.2 第一版常用池

```text
单手：cup, bottle, phone, book
双手：box, tray
环境：chair, table
```

首个技术 pilot 只做：

```text
one_hand_cup
two_hand_box
```

### 13.3 交互档案

```text
interaction_id
motion_id
prop_category
compatible_prop_ids[]
primary_hand
primary_socket
relative_transform
hand_pose_id
secondary_hand_ik
attach_frame
detach_frame
collision_profile
scale_range
validation_status
```

### 13.4 UE 实现

- 单手物体附着到主手 Socket，并保存相对位姿。
- 双手物体由主手或独立轨迹驱动，副手通过 IK/Control Rig 保持接触。
- 拿起和放下由 Sequencer 事件或蓝图在指定帧 Attach/Detach。
- 椅子和桌子作为场景交互物，不挂在角色骨架上。
- 拒绝抓空气、手指悬空、手掌穿入道具、双手接触漂移和尺寸不合理。

## 14. CC 导出与 UE 导入

### 14.1 导出单位

每个正式角色保留一个默认完整导出源，同时将变体登记为独立集合：

```text
character_default
hair_style_0
hair_style_1
hair_style_2
beard_fitted_default
outfit_look_variants[]
```

实际导出可以采用完整角色后在 UE 拆分的已验证路径；无论使用哪种方式，必须以 JSON sidecar 记录源角色、当前 BodyFit、面部配方、资产 ID 和导出设置。

### 14.2 导出约束

- 使用 UE5 Skeleton、Epic hand/foot IK 和当前已验证的 Auto Material JSON 设置。
- 角色需要换装时不得删除被当前服装覆盖的基础身体。
- 不合并需要独立切换的服装、头发、胡须和眉毛。
- 不把胡须与眉毛合并。
- 保留所需 Morph Target 和 Facial Profile 支撑。
- 纹理和材质按资产 ID 复用，不为每个几何变体复制同一套贴图。
- Vendor 导出源和 DataMake 派生资产命名必须可追溯。

### 14.3 UE 内容边界

```text
/Game/Vendor/Reallusion/CC5/
  CC 导入源、整合参考、Skeletal Mesh、材质和纹理

/Game/DataMake/Characters/
  统一角色蓝图、数据资产、兼容 manifest 和派生配置

/Game/DataMake/Animations/
  Body-only、面部曲线和项目派生动画
```

Vendor 内容不移动；DataMake 通过引用组织。

### 14.4 导入验证

- 所有模块使用兼容 Skeleton。
- Body 保留 PhysicsAsset 和必要 Post Process Anim Blueprint。
- follower 不重复启用无意义碰撞。
- 材质槽按名称正确复用。
- Morph Target 数量和关键名称存在。
- 基础身体完整，隐藏全部服装后没有被永久裁空。
- 导入后中性、眨眼、微笑、张嘴和全身动画均正常。

## 15. UE 模块化角色架构

### 15.1 组件结构

```text
CharacterRoot
  Body                         # leader
  FaceSupportRoot
    Eyes
    Teeth
    Tongue
    Brows
    Eyelashes
    Tearline / Occlusion
  HairRoot
    HairPart_0..N
  BeardRoot
    BeardPart_0..N
  ClothingRoot
    TopInner
    TopOuter
    Bottom
    Dress
    Shoes
    Gloves
  PropRoot
```

发型和胡须都是多网格集合，不能假设每套资产只占一个组件。

### 15.2 统一运行时接口

```text
SetHairStyle(HairStyleId)
SetHairColor(HairColorId)
SetBeardEnabled(bool)
SetBeardStyle(BeardStyleId)
SetOutfitLook(LookId)
PlayBodyMotion(MotionId)
PlayFaceClip(FaceClipId)
EquipProp(InteractionId, PropId)
ClearProp()
```

首版 `SetBeardStyle` 只需支持默认适配胡须；核心要求是 `SetBeardEnabled` 的稳定二值切换。

### 15.3 数据资产

建议建立：

```text
DA_CharacterIdentity
DA_HairStyleSet
DA_BeardStyleSet
DA_OutfitLook
DA_BodyMotionProfile
DA_FaceClipProfile
DA_PropInteractionProfile
```

每个角色数据资产引用 3 个 HairStyleSet、可选 BeardStyleSet、允许的 Look、身体动作、面部动作和道具交互。

### 15.4 面部曲线

- Body 统一接收面部曲线。
- 通过已验证的曲线传播或显式广播同步到支持同名 Morph 的面部模块。
- 服装和普通头发不接收无关面部 Morph。
- 需要跟随表情的眉毛、睫毛、眼周和胡须必须在导入时验证实际响应。

### 15.5 毛发物理分支

- 简单发型继续使用 leader/follower 架构。
- 带额外毛发骨骼的发型使用专用组件和 AnimBP，不强行套用只适合普通 follower 的逻辑。
- 每个 HairStyleSet 明确 `physics_mode`，运行时不得猜测。

## 16. 验证与验收

### 16.1 结构门禁

- BodyFit 源 hash 与 Body/Junction 指纹一致。
- 只加载一个完整主面部原型。
- Facial Profile、眼球和牙齿支撑与原型一致。
- 非目标 Morph 未变化。
- 外观加载后 BodyFit 与面部配方保持不变。
- 保存、重载和导出前后结构摘要一致。

### 16.2 面部动态门禁

保留当前 15 姿态体系，并至少覆盖：

```text
neutral
blink left / right / bilateral
look left / right / up / down
eyes wide
squint
smile
mouth open
three-quarter mouth open
restore neutral
```

检查眼球、眼皮、牙齿、舌头、嘴唇、眉毛、睫毛、胡须和恢复后眼位。

### 16.3 毛发门禁

每个最终角色：

- `3/3` 发型完成四视图。
- `3/3` 发型完成表情与转头检查。
- 男性 `beard none/default` 两个状态均正确。
- 发色切换不改变几何和角色身份。
- 无遗留隐藏阴影、漏组件或错误材质。

### 16.4 服装门禁

- 每个 Look 的层级和互斥规则合法。
- 目标 BodyFit 上静态无明显穿模。
- 行走、抬臂、弯肘和扭转通过。
- 身体隐藏区域不会在其他 Look 中造成缺失。
- 材质颜色变体不改变网格适配状态。

### 16.5 动画与道具门禁

- 同一个面部 clip 能与至少两条身体动作组合。
- 面部骨骼层不得覆盖身体动画中的脖子和头部姿态。
- Hybrid Face clip 的骨骼轨道与 Morph 曲线必须同时生效且不重复驱动。
- 动画循环、Root Motion 和 follower 同步正常。
- 道具的手型、Socket、相对变换和 Attach/Detach 帧正确。
- 双手交互中副手不漂移。
- 不生成持物动作但没有道具的正式样本。

### 16.6 UE 门禁

- PIE 中实际播放资产与 manifest 一致。
- 组件数量、Skeleton、leader、曲线传播和可见性状态正确。
- 三套发型逐一切换并截图。
- 胡须开启/关闭逐一截图。
- 至少两个 Look 逐一切换并执行动作。
- 身体动作、面部表情和道具可同时运行。
- 临时 Actor 清理完成，`/Game/Main` 未被保存修改。

### 16.7 人工视觉验收

机器门禁不能替代以下判断：

- 身份是否自然、精细且不呈现明显平均脸。
- Aaron 对照中的主要质量差距是否缩小。
- 年龄是否单调递增并保持同一身份。
- 头身、颈部、发型和服装是否协调。
- 表情和持物动作是否自然，而不只是“没有报错”。

## 17. 执行阶段

### 阶段 0：文档与基线收口

- 删除临时 `CURRENT_HANDOFF` 文件。
- 将当前入口统一到 `STATUS.md` 和本计划。
- 保留现有 Face V3、10 BodyFit 和 M02 UE pilot 作为基线。

完成标准：不存在失效交接链接；下一轮只有本文件一个计划入口。

### 阶段 1：动画层正式分离

**状态：已完成（2026-08-04）。**

- 将 Audience 和 Walk 两条动作建立 Body-only 派生版本。
- 建立可复用 blink、gaze、idle 和 subtle smile 面部 clip。
- 在同一 M02 modular blueprint 上完成 `2 body x 4 face` 组合。
- 决定正式 AnimBlueprint 与 Sequencer 边界。

完成标准：同一面部 clip 不需复制即可组合两条身体动作。

实现入口为 `/Game/DataMake/Animations/CC5/Pilot/ABP_DM_M02_BodyFaceLayer_v002`。AnimBlueprint 负责持续身体动作选择、可复用面部循环选择和 Additive 合成；Sequencer 负责镜头时间、选择器切换、Actor 位移、相机与渲染编排。PIE `2 x 4` 矩阵 `8/8` 通过，正式证据为 `00_engine/outputs/unreal_character_import/m02_layered_animation_matrix_v002.json`。

### 阶段 2：UE Elder 年龄 Morph 导出 Pilot

状态：**已完成（2026-08-04）**。

- 使用 `M02_Average` 与 `Full Face Elder` 验证可调 Morph Target 导出。
- 在独立 UE Pilot 目录检查 `0 / 0.5 / 1.0` 三档。
- 验证 Body、眉毛、睫毛、胡须、头发的 Morph 覆盖情况。
- 在眨眼、微笑和张嘴状态检查眼球、牙齿、嘴唇和 Junction。
- 若不能直接导出，则验证青年/老年同拓扑网格构造 Morph 的后备路线。

完成结论：常规 CC 导出为 `not_exportable`，青年/老年快照后备路线达到 `fallback_all_components`。11 个实际受影响模块使用统一 `Full_Face_Elder` 广播，5 个严格不变模块保持中性。年龄 `0 / 0.5 / 1.0`、眨眼和微笑已通过真实 PIE；完整下颌支撑转入阶段 3。

### 阶段 3：面部骨骼与曲线混合分层

状态：**已完成（2026-08-04）**。阶段 2 已证明单独 `jawOpen` 曲线不足以代表完整张嘴；本阶段已补齐下颌、牙齿和舌头支撑骨骼，并完成曲线与骨骼的混合验收。

- 保留 `ABP_DM_M02_BodyFaceLayer_v002`，正式入口新增为 `/Game/DataMake/Animations/CC5/Pilot/ABP_DM_M02_BodyFaceLayer_v003`。
- Face-only hybrid clip 为 `/Game/DataMake/Animations/CC5/Pilot/Face/A_DM_M02_Face_HybridSupport_Loop_v001`，包含 8 条面部根、下颌、上下齿与舌头支撑骨骼轨道，以及 11 条眨眼、嘴唇、微笑、张嘴和眼神 Morph/Rig Logic 曲线。
- `Layered Blend per Bone` 从 `cc_base_facialbone` 分层，明确排除 `head` 与 `neck`。M02 的 Post Process Rig Logic 拥有最终眼球骨骼姿态，因此正式 clip 使用左右 `eyeLookRight` 曲线驱动眼神，不再叠加直接眼球骨骼轨道，避免双重驱动。
- 新建图结构和时序完全匹配的中性控制 `/Game/DataMake/Animations/CC5/Pilot/ABP_DM_M02_BodyFaceLayer_v003_ControlNeutral`，用于排除不同 AnimBP 图和启动时间造成的伪差异。
- Audience 与 Walk 共用同一 hybrid clip；真实 PIE `2 body x 5 face` 共 `10/10` 用例通过。20 个骨骼网格组件中 19 个 follower 正常，头颈相对中性控制的旋转差为 `0.000` 度，视觉检查未见眼球偏移、牙齿/舌头穿模或模块脱离。
- `00_engine/scripts/character_creator/cc_unreal_animation_channel_registry_v1.json` 已固化 `facial_channels` 与 `replaceable / paired / locked` 规则，并记录 Rig Logic 眼神驱动边界。

完成标准：身体头颈动作不变，面部骨骼与曲线同时生效，模块化 follower 正常，且没有双重驱动、眼球偏移或牙齿穿模。

正式证据：

```text
00_engine/outputs/unreal_character_import/
  m02_face_support_bone_audit_v001.json
  m02_face_hybrid_clip_v001_build.json
  m02_layered_anim_blueprint_v003_build.json
  m02_hybrid_neutral_control_v003_build.json
  m02_face_hybrid_review_v003/pie_review.json
  m02_face_hybrid_review_v003/m02_face_hybrid_pie_contact_sheet.png
```

阶段 3 的 `v004` 只用于证明直接眼球骨骼轨道会被 Post Process Rig Logic 覆盖，不属于生产资产；诊断资产、脚本和报告已清理。

### 阶段 4：Aaron/M02 质量基准

状态：**首轮决策级基准已完成（2026-08-05）**。

- 已建立统一 CC 相机、Lightroom、角色位置、分辨率和姿态矩阵。
- 已完成同条件完整外观、轮廓几何和动态比较，共 14 张正式图片。
- 已输出完整、几何和表情三张联系表，以及机器可读评估和中文差距报告。
- 已确认 M02 通过结构门禁；优先改进域为眼部/泪线、皮肤材质响应和身份次级结构。
- 统一中性材质、皮肤互换、动态皱纹隔离和多灯光响应未被伪装为已完成，转入阶段 5A。

完成标准已满足：能够明确说明主要差距与优先级，并区分已证实结论和待隔离变量。

### 阶段 5：眼部/皮肤质量 Pilot 与 Headshot 10/20 原型比较

状态：`5A` 已完成并进入生产；`5B` 未开始。

- `5A` 已在 M02 上完成眼白、角膜、虹膜、泪线和中性眼神的 4 配置、2 灯光矩阵，不扩充身份数量。
- `5A` 已使用 `Default_CC5` 与暖色宽正面 `Bright` 控制光完成 5 配置皮肤矩阵，隔离微法线、粗糙度、高光和 SSS 响应。
- 推荐档案只保留 7 个参数定义，实际写入左右角膜 6 个 slot/parameter 与头部皮肤 4 个 slot/parameter，共 10 项；虹膜/泪线、区域粗糙度和 SSS 变化暂缓全局采用。
- 推荐档案为 `00_engine/scripts/character_creator/cc_face_material_quality_profile_v1.json`，状态为 `production_approved`。
- 正式原始/推荐复核为 `2 profile x 2 light = 4` 张，材质恢复差异 `0`、眼部结构恢复通过、Undo 点击数 `0`。
- `female_light / female_dark / male_light / male_dark` 四套完整角色交叉验证为 `4/4` 成功，共 `32/32` 张图片；Morph、Eye AvatarPart、眼球几何和材质恢复全部通过。
- 生产 registry 已 hash 锁定该档案，manifest compiler 已传播引用；M02 完整生产路径冒烟为 `1/1` 成功，10 项参数回读一致并保存规范化 `.ccProject`。
- `5B` 使用 4 人 smoke 验证 Headshot 离线使用、保存、重载和弹窗。
- `5B` 建立首批 10 个候选原型；人工比较后再决定是否扩展到 20 个。
- 比较身份覆盖、重复率、失败率、人工成本，以及相对 Aaron/M02 基准的质量提升。

`5A` 技术证据位于 `m02_face_material_recommended_20260805_01`、`face_material_cross_skin_20260805_retry01` 和 `face_material_quality_integration_smoke_20260805_retry01`。阶段 5 的剩余完成标准是：完成 Headshot 4 人 smoke，并由用户根据 10/20 原型对照决定正式身份池规模。

### 阶段 6：新面部配方与年龄

- 冻结通过的完整身份原子。
- 用当前安全局部 Morph 生成新确定性配方 pilot。
- 审计面部年龄 Morph。
- 对合适原型建立可选 `young/middle/older`。
- 小规模验证身体老化及其服装影响。

完成标准：新脸比当前 V3 提升身份质量或多样性，并保持眼口动态安全。

### 阶段 7：完整 CC 外观组装

- 按唯一顺序组装代表角色。
- 每个角色选择并适配 3 套发型。
- 男性建立 `none/fitted_default` 胡须切换。
- 固化毛发色素档案。
- 保存项目、manifest 和视觉证据。

完成标准：代表男女角色的三发型与胡须二值状态全部通过。

### 阶段 8：服装 Look 与十体型适配

- 在 M02/F02 建立 Look A/B/C。
- 固化服装槽位、层级、互斥、Body hide mask 和动作门禁。
- 扩展到实际支持的其他 BodyFit。
- 只导出已批准的 BodyFit 版本。

完成标准：至少两套正式 Look 可在 UE 中切换，分层压力 Look 有明确通过或拒绝结论。

### 阶段 9：动作道具 pilot

- 建立小型道具目录和交互档案。
- 完成单手杯子与双手箱子。
- 验证 Socket、手型、IK 和 Attach/Detach。

完成标准：角色不抓空气，单手与双手交互均有可复现配置。

### 阶段 10：UE 统一角色接口

- 将 M02 blueprint 抽象为可复用架构。
- 接入角色、发型、胡须、Look、动作、面部和道具数据资产。
- 实现统一运行时函数。
- 在代表男女角色上验证。

完成标准：配置 ID 能确定性重建同一 UE 角色状态。

### 阶段 11：端到端验收样本

选择覆盖十个 BodyFit 的小规模角色集，但不展开全部笛卡尔积。每个角色至少验证：

```text
1 个默认身份与皮肤
3 套发型
男性有/无胡须
至少 2 个 Look
至少 2 条身体动作
至少 2 个面部 clip
代表角色的 1 个道具交互
```

完成标准：CC 项目、导出 manifest、UE 资产、运行时配置和截图/短视频可互相追溯。

### 阶段 12：生产切换与收口

- 新流程通过后切换默认 manifest 编译入口。
- 保留旧 V1/V3 文件作为历史回退。
- 清理失败探针和被最终结果取代的临时输出。
- 重构 `FACIAL_GENERATION.md` 为完整角色工厂规范。

## 18. 机器可读产物

建议的新版本文件：

```text
cc_character_factory_policy_vNext.json
cc_headshot_source_manifest_v1.json
cc_headshot_prototype_library_v1.json
cc_face_seed_library_v2.json
cc_face_age_morph_policy_v1.json
cc_face_age_profiles_v1.json
cc_face_age_morph_export_pilot_v1.json
cc_body_age_morph_policy_v1.json
cc_face_recipes_vNext.json
ue_face_animation_layer_policy_v1.json
ue_face_hybrid_clip_manifest_v1.json
cc_hair_style_compatibility_v1.json
cc_character_hair_variants_v1.json
cc_beard_toggle_policy_v1.json
cc_outfit_look_library_v1.json
cc_garment_bodyfit_compatibility_v1.json
cc_body_motion_library_v1.json
cc_face_clip_library_v1.json
cc_prop_library_v1.json
cc_prop_interaction_library_v1.json
cc_ue_character_manifest_v1.json
```

`vNext` 在实现时替换为明确版本号。每个文件至少记录：

```text
schema_version
generated_at
source_paths
source_hashes
asset_ids
compatibility_ids
validation_status
evidence_paths
rejection_reasons
```

建议报告：

```text
aaron_m02_quality_benchmark.json
headshot_capability_report.json
headshot_10_vs_20_comparison.json
age_profile_validation_summary.json
hair_three_variant_acceptance.json
beard_toggle_acceptance.json
outfit_bodyfit_matrix_summary.json
body_face_layering_validation.json
prop_interaction_validation.json
ue_character_factory_acceptance.json
```

## 19. 停止条件

- CC Private Bytes 达到或超过 `24 GiB` 时停止提交新任务。
- Agent 不自动重启离线许可证版 CC。
- CC 无响应、异常关闭或出现未知弹窗时停止当前批次。
- 已知 Undo/Replace 弹窗只能由严格匹配的守卫处理；不能猜测点击未知窗口。
- 同一失败原因连续出现 3 次时停止该阶段并诊断。
- 任一身份出现眼球、牙齿、Facial Profile 或 Body/Junction 问题时，不继续扩大其年龄、毛发和服装矩阵。
- Headshot 需要联网、重新授权或人工确认时停止并通知用户。
- UE 批处理不得保存 `/Game/Main`，不得修改 Vendor 源资产。
- 长时间 UE 导入、着色器编译或渲染可以等待；无法判断的交互窗口不得自行确认。
- 任一阶段未完成视觉验收，不得仅凭 JSON `success=true` 宣布生产可用。

## 20. 最终文档收口

下一阶段全部验收后，将 `FACIAL_GENERATION.md` 从“面部生成规范”重构为完整的 CC 角色工厂操作规范，至少包含：

1. 系统目标、版本和目录边界。
2. 资产登记、白名单与兼容性模型。
3. 10 个 BodyFit、面部身份、年龄和皮肤。
4. 眼睛、牙齿、眉毛、睫毛、头发、发色和胡须。
5. 服装 Look、BodyFit 适配和身体隐藏规则。
6. 唯一 CC 角色组装步骤。
7. 动画、面部 clip、道具与交互档案。
8. CC 保存、导出和 JSON sidecar。
9. UE 导入、Vendor/DataMake 目录和模块化蓝图。
10. UE 换发、胡须开关、换装、动画和道具 API。
11. 静态、动态、穿模、PIE 和短视频验收。
12. 弹窗、内存、恢复、失败处理和清理规则。
13. 角色配置示例和端到端复现步骤。

该文档先作为项目内权威流程规范。若后续需要成为可安装的 Codex skill，再从稳定规范提取 `SKILL.md` 和必要脚本，不在流程仍频繁变化时提前维护第二套说明。

本计划在全部稳定结论合并后标记为 `implemented`；若不再需要历史追踪，可以删除，避免与权威规范形成两个生产真值。
