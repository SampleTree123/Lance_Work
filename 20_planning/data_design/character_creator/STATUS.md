# Character Creator 本地角色工厂实现状态

> 日期：2026-07-30  
> 范围：Character Creator 5 本地端  
> 结论：8 个 BodyFit、17 个生产主面部和各外观资产域继续有效；24 个完整角色通过自动结构门禁；动态截图修复已通过完整角色快速回归，24 角色新证据重跑、人工签核、导出与 Unreal 导入尚未完成。

本文只记录已经落地的实现和可复现产物。长期设计仍见 [`README.md`](./README.md)，成人面部生产规范见 [`FACIAL_GENERATION.md`](./FACIAL_GENERATION.md)。

> 2026-07-30 面部状态：Face V2.1 永久保留为静态历史原型。V3 已把主 Facial Profile、真实皮肤/眼球材质和姿态后眼位恢复纳入同一门禁；`24/24` 角色自动结构验证有效。旧 360 张动态文件因 `RenderImage` 固定输出第 0 帧而失效，现已改为快照式第 0 帧取证和 RMSE 活性检查。

## 1. 当前能力边界

已经实现：

- CC5 文件队列桥接，可由外部客户端提交任务并读取结构化结果。
- 8 个固定成人 `BodyFit` 的权威项目加载与隔离检查。
- Face Generator V2.1 的锚点均衡生成、参数复原和多视角预览。
- Face Generator V3 的 200 条确定性配方、完整主原型加载、28 项生产局部 Morph、显式 Facial Profile 绑定和 manifest 编译；200 条配方及 24 个角色均通过策略一致性审计。
- 17 个候选主原型加 8 个 BodyFit 代表随机脸的旧 25 例矩阵；其数值隔离结果保留，旧眼球遮挡视觉结论已由当前 24 角色真实材质矩阵取代。
- Template 与 Custom 外观资产的统一白名单目录。
- 通过 `asset_id` 装配上装、下装、鞋和完整发型组。
- 装配前后场景对象增删记录，以及 body / junction / face / other morph 隔离检查。
- 首套男女外观在全部 8 个成人 BodyFit 上的数值与视觉验证。
- 第二套男女外观在全部 8 个成人 BodyFit 上的数值验证，以及 7/8 的视觉验证。
- 配方级基础衣物清理，可按精确对象名删除冲突内衣并记录删除状态。
- 正向兼容与视觉拒绝组合的分离登记。
- 兼容性驱动的确定性角色 manifest 编译，禁止未验证资产与已拒绝组合。
- 编译产物直接提交 CC 的端到端验证。
- 材质型资产的轻量指纹框架，可比较 avatar 材质、shader 参数和纹理采样。
- 皮肤、SkinGen、眼睛、牙齿、眉毛、胡须、妆容和配饰的 10 条单域 pilot 清单。
- 两套牙齿在当前 8 个成人 BodyFit 和 32 张成人脸上的张嘴、微笑与中性兼容验证。
- 12 套眼球材质的男女代表样本验证，以及代表材质在当前 8 个成人 BodyFit 和 32 张成人脸上的完整矩阵验证。
- 指定女性 6 套、男性 7 套眉毛在当前成人 CC5 HD 面部上的 Brow AvatarPart 替换、静态贴合与眉部表情验证。
- 9 套 HD Natural 睫毛在完整男女源脸上的共享池验证、动态眼睑姿态检查，以及 `Apply Character Preset` 弹窗的严格自动处理。
- 9 套睫毛乘 4 个 V3 极端成人脸的 `36/36` 组件矩阵与人工检查。
- ActorMIXER CORE Library 中 21 套青年 2K 皮肤在完整男女源脸上的三年龄矩阵，以及 `Apply Material` 弹窗的严格自动处理。
- 5 套男性胡须在 9 张 V3 男性生产主面部上的 `45/45` 静态、微笑和张嘴兼容验证，以及 Beard AvatarPart 正确识别。
- 58 套头发的呈现过滤、动态/刚性分类、压力矩阵和统一毛发颜色策略。
- 男女 HD Neutral 2K 动态皱纹在三年龄档的 6 例矩阵。
- 主 Facial Profile 内容加载后的 17 个生产主原型、8 个 BodyFit 和 24 个完整角色结构回归。
- 24 个角色各 15 个姿态定义均执行完成；旧 360 张文件不能作为动态视觉证据，但中性眼位和姿态后最终眼位结构结果仍为 `24/24`。
- 快照式第 0 帧表情取证、首帧预热、`512 x 512` 规范化、同场景中性基准、RMSE 活性检查和快照恢复已在完整男性角色上通过。
- 明确选择最终 24 个 `result.json` 的去重汇总器，避免早期失败批次和修复探针污染正式结论。
- 当前汇总器已强制检查新捕获策略、快照恢复与清理、clip 数量守恒、同场景中性参考和逐姿态 RMSE；旧 24 例重汇总时姿态门禁为 `0/24`，不会误入新正式结果。

尚未实现或尚未验证：

- 干净重启 CC 后，用新取证路径重跑 24 个完整角色并逐张签核；当前状态是自动结构通过、动态新证据待生成。
- HeadFit 正式分组及儿童、第三方头型的独立兼容矩阵。
- SkinGen、妆容和配饰等首版排除域。
- 动画、表情、项目保存、批量 FBX 导出和 Unreal 导入。
- 任何资产的 AI/ML 训练许可确认。

## 2. 体型基线

固定使用以下 8 个成人体型：

| ID | 性别 | 类别 | 状态 |
| --- | --- | --- | --- |
| `M01_Lean` | male | lean | accepted |
| `M02_Average` | male | average | accepted |
| `M03_Athletic` | male | athletic | accepted |
| `M04_Heavy` | male | heavy | accepted |
| `F01_Lean` | female | lean | accepted |
| `F02_Average` | female | average | accepted |
| `F03_Athletic` | female | athletic | accepted |
| `F04_Heavy` | female | heavy | accepted |

正式清单：

```text
00_engine/scripts/character_creator/cc_body_preset_library_v1.json
00_engine/scripts/character_creator/cc_body_morph_catalog_v1.json
```

8 个 `.ccProject` 是只读的权威体型入口，总计约 281.79 MiB。每次角色装配先加载对应项目，再应用面部和外观；不会为每个生成角色复制一份项目。清单中的 morph 向量用于漂移检测和审计，不再承担从 Neutral Base 重建体型的运行时职责。

## 3. Face Generator

### 3.1 V3 生产候选

唯一生产流程：

```text
BodyFit .ccProject
  -> 一个同性交付的完整 Head Preset
  -> 收敛主原型眼球/牙齿 Actor Parts 支撑
  -> 加载该主原型的 Facial Profile
  -> 只修改生产白名单中的 28 个非眼部、非口部局部 Morph
  -> 使用真实皮肤和眼球材质执行 15 姿态动态门禁
```

稳定产物：

```text
00_engine/scripts/character_creator/
  cc_generate_face_recipes_v3.py
  cc_generate_face_recipes_v3_config.json
  cc_face_recipes_v3_200.json
  cc_build_face_quality_batch_v3.py
  cc_face_quality_batch_v3_validation.json
```

配方结果：

- 200 条，男女各 100，确定性指纹 `200/200` 唯一。
- 男性使用 9 个合格主原型；女性使用 8 个合格主原型。
- 原身份策略审计 51 个控制；生产只使用 28 个 Brow/Cheek/Ear/Forehead/Jaw/Nose 局部控制。
- 所有 `role=macro`、6 个口部 Morph 和 7 个眼部 Morph 冻结。
- 旧 `target_face_morphs` 整脸写入不再出现在新 manifest。
- 每条配方和角色 manifest 显式记录 Facial Profile 的加载模式、路径、SHA-256 与 policy binding；当前 `200/200` 配方、`24/24` 完整角色清单均无缺失或策略不匹配。
- 本地完整单元测试 `130/130` 通过；该结果验证代码和清单，不替代 CC 动态视觉签核。

历史动态矩阵（数值结果有效；眼球遮挡视觉结论已由当前矩阵取代）：

| 项目 | 结果 |
| --- | --- |
| 非 Neutral 主原型测试 | 18 |
| 生产主原型通过 | 17 |
| 动态拒绝 | `F09_Female_F`，满幅微笑时下排牙齿穿出 |
| BodyFit 代表随机脸 | 8/8 |
| 历史矩阵结构结果 | 25/25 |
| 每例动态姿态 | 15 |
| 动态检查图 | 375 |
| 最大 face absolute error | `6.842994071387665e-08` |
| Body/Junction 污染 | 0 |
| 未知弹窗 | 0 |

完整皮肤和白色眼球材质接入后，`CCINT_M01_YOUNG` 曾暴露闭眼时眼球穿出。根因边界与修复结果如下：

- Head Preset 不能替代 Facial Profile；后者现已作为主原型原子状态加载。
- 动态测试不再创建或删除临时 expression clip；它保存临时项目快照，并只在原 Facial Profile clip 第 0 帧覆盖本轮表情通道。
- 姿态完成后先恢复原通道权重并渲染同场景中性基准，再重载快照恢复完整项目状态。
- 每个正面姿态必须通过 RMSE 活性门禁；所有正式证据规范化为 `512 x 512`。
- 恢复角色变换后强制刷新 Morph/时间求值，并重新比较双眼局部、T-Pose、Morph、LookAt 和世界状态。
- 眼球世界平移允许 `0.2 mm` 求值噪声，旋转和局部状态仍保持严格。

当前完整矩阵：

| 项目 | 结果 |
| --- | ---: |
| 完整角色 | 24/24 |
| BodyFit | 8/8 |
| 生产主原型覆盖 | 17/17 |
| 每例姿态 | 15 |
| 旧动态文件 | 360，失效，不可用于视觉签核 |
| 中性 expression clip 保留 | 24/24 |
| 中性眼位恢复 | 24/24 |
| 姿态后最终眼位 | 24/24 |
| 自动结构门禁 | 24/24 |
| 新动态取证快速回归 | 1 个完整角色，4 个核心姿态通过 |
| 24 角色新动态证据 | pending clean restart |
| 完整人工逐图签核 | pending |

精确流程和视觉边界见 [`FACIAL_GENERATION.md`](./FACIAL_GENERATION.md)。

最终报告：

```text
00_engine/scripts/character_creator/
  cc_character_integration_automation_summary_v1.json

00_engine/outputs/character_creator_bridge/artifacts/
  character_integration_24_fixed_20260729_01/
    character_integration_final_summary.json
```

旧 `face_v3_dynamic_validation_final_20260727_01` 仍是历史 25 例证据，不是当前完整角色最终报告。人工审核曾发现并修正两类生成风险：整头角色/macro Morph 不能当局部身份项叠加；口部 Morph 在没有牙齿和口腔成对支撑时可能造成微笑穿模。失败批次继续保留作拒绝证据，但不会进入显式选择的最终 24 例。

### 3.2 V2.1 静态历史

V2.1 的目标是解决旧版女性 regional 配方过度集中到同一原型的问题。

已实现的约束：

- 每个性别使用 9 个可用 identity anchor，共 18 个。
- 32 条 pilot 配方，男女各 16 条。
- 每个 primary anchor 最多使用 2 次。
- 禁止 neutral identity parent。
- 禁止 Headshot 目标 morph。
- 只允许审核通过的 Actor/Head face morph 修改。
- 排除 Actor 与 Headshot 同语义命名冲突。

代表性 CC 验证：

| 项目 | 结果 |
| --- | --- |
| 代表样本数 | 8 |
| 每批角色数 | 2 |
| 成功数 | 8/8 |
| 最大 face absolute error | `5.98e-8` |
| body / junction 污染 | 0 |
| 视觉异常 | 未发现明显破面、颅骨塌陷或眼球脱位 |

报告：

```text
00_engine/outputs/character_creator_bridge/artifacts/
  face_quality_v2_1_targeted_consolidated_20260723/review/
```

V2.1 曾是成人面部静态原型的默认版本。旧 Face V2 与 V2.1 结果只保留作对照，后续默认入口固定为 V3。

## 4. 外观资产目录

目录构建器同时扫描：

```text
D:\CharacterCreator_sucai\Reallusion Templates
D:\CharacterCreator_sucai\Reallusion Custom
```

目录产物：

```text
00_engine/scripts/character_creator/cc_appearance_asset_catalog_v1.json
```

当前统计：

| 项目 | 数量 |
| --- | ---: |
| 物理文件 | 1119 |
| 合并后的逻辑资产 | 969 |
| Template + Custom 成对项 | 150 |
| 服装 | 235 |
| 头发相关 | 309 |
| 配饰 | 20 |
| 眼睛 + 牙齿 | 77 |
| 皮肤 + 妆容 | 328 |

毛发资产已经细分：

- `scalp_hair`：248，其中 71 个完整 group/style 可进入首轮装配池，177 个 element 只作为组件。
- `eyebrows`：20。
- `facial_hair`：13。

目录规则：

- 角色配方只引用稳定 `asset_id`，不接受任意磁盘路径。
- 同一逻辑资产同时存在 Template 与 Custom 时优先 Custom。
- `.rlHairElement` 标记为 `component-only`，不能作为完整发型直接随机选择。
- 无法可靠判断男女的资产标记为 `unknown`，不做猜测。
- 未验证资产默认 `prototype-only`、`compatibility=unverified`。

## 5. 外观装配结果

### 5.1 首套外观

已通过的女性配方：

```text
APPV1_F_AVERAGE_0001
BodyFit: F02_Average
Face: FFACEV21_0009
Appearance: F_CASUAL_01
Assets: Camisole + Denim shorts + Boots_F + Chic bun medium
```

已通过的男性配方：

```text
APPV1_M_AVERAGE_0001
BodyFit: M02_Average
Face: MFACEV21_0009
Appearance: M_CASUAL_01
Assets: Rolled sleeves shirt_A3 + Slim fit pants + Canvas Shoes + Classic short
```

同一套男女外观随后扩展到各自全部 4 个成人体型。除上述两个 Average preset 外，以下 6 个矩阵 preset 也已通过：

```text
APPMAT_M01_LEAN_0001
APPMAT_M03_ATHLETIC_0001
APPMAT_M04_HEAVY_0001
APPMAT_F01_LEAN_0001
APPMAT_F03_ATHLETIC_0001
APPMAT_F04_HEAVY_0001
```

全部 8 个 preset 均满足：

- BodyFit 精确复原。
- 历史 Face V2.1 精确复原；该项只证明当时外观装配未污染面部，不代表 V3 动态面部结论。
- 4 个外观资产逐项产生可记录的场景对象变化。
- 装配后 body / junction / face / other morph 全部不变。
- 全身、正面、四分之三和侧面预览可生成。
- 未观察到明显衣物穿出、鞋脚错位或发际线穿模。

男性卷袖衬衫技术上适配，但衣摆较短，只能作为一种风格候选，不能标为通用男性默认上装。

合并报告：

```text
00_engine/outputs/character_creator_bridge/artifacts/
  appearance_quality_v1_consolidated_20260723_02/review/
  appearance_bodyfit_matrix_v1_consolidated_20260723/review/
```

### 5.2 第二套外观

Average pilot：

```text
APPV2_F_AVERAGE_0001
BodyFit: F02_Average
Face: FFACEV21_0010
Appearance: F_DRESS_01
Assets: Dress_A + High Heels_A1 + Finger Wave Pixie

APPV2_M_AVERAGE_0001
BodyFit: M02_Average
Face: MFACEV21_0010
Appearance: M_CASUAL_02
Assets: Basic T-shirts + Jeans_Rivets + Canvas Shoes_A1 + Short blowback
```

其余 6 个 BodyFit：

```text
APPV2MAT_M01_LEAN_0001
APPV2MAT_M03_ATHLETIC_0001
APPV2MAT_M04_HEAVY_0001
APPV2MAT_F01_LEAN_0001
APPV2MAT_F03_ATHLETIC_0001
APPV2MAT_F04_HEAVY_0001
```

第二套 8 个 preset 均数值成功，BodyFit、Face、资产加载和 morph 隔离全部通过。视觉结果为 7/8：

- 女性连衣裙组合在 `F01` 至 `F04` 上通过，但必须先按配方精确移除基础 `Bra`；不执行该清理时领口和后背会露出黑色胸衣边缘。
- 男性组合在 `M01`、`M02`、`M03` 上通过。
- `APPV2MAT_M04_HEAVY_0001` 被拒绝：`Jeans_Rivets` 腰部带状细节从 `Basic T-shirts` 前下摆明显穿出。
- 两款新发型在所有已检查头部的正面、四分之三和侧面视图中均未发现明显发际线、耳侧或后脑穿模。

合并报告：

```text
00_engine/outputs/character_creator_bridge/artifacts/
  appearance_quality_v2_consolidated_20260723/review/
  appearance_bodyfit_matrix_v2_consolidated_20260723/review/
```

有限范围兼容性登记：

```text
00_engine/scripts/character_creator/cc_appearance_compatibility_v1.json
```

当前登记审核了 260 个 preset：259 个正向通过、1 个视觉拒绝。47 个资产至少有一条正向证据，其余 922 个资产仍未验证。首套男女资产覆盖各自全部 4 个 BodyFit；第二套女性资产覆盖 `F01` 至 `F04`，第二套男性资产只覆盖 `M01` 至 `M03`，不得用于 `M04_Heavy`。眼球、牙齿、眉毛和胡须各自保留独立的验证边界；本结果不能推断跨性别、儿童或跨 HeadFit 兼容性。

## 6. 质量门槛

每个角色至少检查：

1. BodyFit 目标值与 fingerprint 一致。
2. Face 目标值一致，记录最大绝对误差。
3. 应用 face 后 body / junction / other 不变。
4. 每个外观 asset 的 `RFileIO.LoadFile` 返回成功。
5. 每个 standalone asset 引起场景附属对象变化。
6. 应用外观后四组 morph 均不变。
7. 全身检查衣服、鞋和身体穿插。
8. 正面、四分之三、侧面检查发际线、耳朵、后脑和颈部。

一次成功只证明指定 `BodyFit + Face + Assets` 组合。不得自动推断该资产兼容其他体型或头型。

## 7. 内存停止条件

2026-07-23 的早期连续验证曾达到：

```text
CharacterCreator PID: 5808
Responding: true
Working set: about 16.6 GB
Private memory: about 29.6 GB
```

虽然每次只运行 1 个角色，CC 仍会累计资产缓存。后续 6 个非 Average preset 因此拆成两次 CC 会话执行：

```text
Male run, 3 jobs:   private memory 11.39 GB, working set 4.95 GB
Female run, 3 jobs: private memory 9.93 GB, working set 4.40 GB
Current PID 36112:  private memory 9.57 GB, working set 4.88 GB, responding
After V2 pilots/matrix: private memory 19.78 GB, working set 3.47 GB, responding
After compiled-manifest E2E: private memory 20.83 GB, working set 2.14 GB, responding
```

执行规则：

- CC 作业每次最多 1 个外观角色。
- 每个作业后检查 `Responding`、working set 和 private memory。
- private memory 达到或超过 24 GB 时不再提交新作业。
- 不允许 agent 自动重启 CC；离线许可证要求由用户确认无网络启动条件。
- 达到停止条件后可以继续离线生成 manifest、目录、报告和文档。

## 8. 下一阶段

兼容性驱动的角色 recipe 编译器已经实现：

```text
00_engine/scripts/character_creator/
  cc_compile_character_manifest.py
  cc_character_manifest_requests_pilot_v1.json
  cc_character_manifest_pilot_v1.json
```

8 角色 pilot 每个 BodyFit 各 1 人，编译结果满足：

- 固定 seed 与 `character_id` 决定未显式指定的 Face/Appearance，选择可复现。
- 只使用兼容性登记中的完整正向组合。
- `M04_Heavy` 自动选择 `M_CASUAL_01`，不会选到被拒绝的 `M_CASUAL_02`。
- 女性连衣裙组合自动携带 `remove_base_clothing_names=["Bra"]`。
- 显式请求 `M04_Heavy + M_CASUAL_02` 时返回 `appearance_recipe_rejected`，输出 `character_count=0`、`presets=[]`，不会产生部分 manifest。
- 当前 8 角色 manifest 已离线重编译到 Face V3，且不再包含旧 `target_face_morphs` / `target_face_fingerprint` 整脸写入字段。
- 历史 `CCFACTORY_F04_0001` 已直接提交 CC，并验证 BodyFit、清理规则、资产加载和 morph 隔离；它早于 V3，只作为外观与桥接端到端证据。V3 面部动态证据以第 3.1 节的 25 例矩阵为准。

端到端结果：

```text
00_engine/outputs/character_creator_bridge/artifacts/
  character_manifest_pilot_v1_f04_e2e_20260723/
```

当前不需要强迫第二套男性服装适配 `M04_Heavy`。角色工厂按兼容性登记选择组合，而不是假设每件衣物适配所有体型。

新外观域 pilot 已完成离线准备：

```text
00_engine/scripts/character_creator/
  cc_appearance_domain_policy_v1.json
  cc_appearance_domain_pilot_v1_config.json
  cc_appearance_domain_pilot_v1.json
  tests/test_cc_appearance_material_fingerprint.py
```

目录覆盖：

| 域 | 目录数量 | 首轮 pilot | 验证证据 |
| --- | ---: | ---: | --- |
| 整体皮肤 | 159 | 2 | material fingerprint |
| SkinGen 皮肤细节 | 94 | 1 | material fingerprint |
| 眼睛 | 59 | 1 | material fingerprint |
| 牙齿 | 18 | 1 | material fingerprint + 后续张嘴视图 |
| 眉毛 | 20 | 1 | scene inventory |
| 胡须 | 13 | 1 | scene inventory |
| 妆容 | 75 | 1 | material fingerprint |
| 头部/其他配饰 | 20 | 2 | scene inventory |

10 条 preset 每条只包含 1 个资产；构建时已通过白名单、路径、性别提示、slot 和验证模式检查。该文件是最初的单样本 pilot 快照，不能再作为各域当前状态：眼球、牙齿、眉毛、睫毛、皮肤和胡须已经分别扩展验证，其中胡须已写入正向兼容登记。其余域仍保持 `pilot_pending_cc_validation`。执行策略固定为每个 CC 作业只提交 1 条，private memory 达到 24 GB 即停止，agent 不自动重启 CC。

下一步顺序：

1. 根据最终汇总图片路径完成人工抽样或逐图签核，记录明确的视觉通过/拒绝状态。
2. 保存通过角色的正式 CC 项目，建立批量 FBX 导出和导出 manifest。
3. 补充服装与动画资产策略，再进入 Unreal 表情、动画和渲染回归。
4. HeadFit、儿童、第三方头型、新插件 Morph 或新 CC 版本建立独立矩阵。
5. SkinGen、妆容和配饰仍是首版排除域，只有需求明确后再进入验证。

## 9. 关键脚本

```text
cc_generate_face_recipes_v3.py
cc_generate_face_recipes_v3_config.json
cc_face_recipes_v3_200.json
cc_build_face_quality_batch_v3.py
cc_face_quality_batch_v3_validation.json
cc_select_character_quality_subset.py
cc_validate_body_reconstruction.py
cc_build_appearance_asset_catalog.py
cc_build_appearance_quality_batch.py
cc_build_appearance_compatibility_registry.py
cc_compile_character_manifest.py
cc_appearance_domain_policy_v1.json
cc_appearance_domain_pilot_v1.json
cc_merge_character_quality_runs.py
cc_make_character_quality_report.py
```

桥接客户端：

```text
00_engine/character_creator_bridge/cc_bridge_client.py
```

严格 undo 提示守卫：

```text
00_engine/character_creator_bridge/cc_undo_dialog_guard.ps1
```

该守卫通过 Win32 只枚举目标 CC PID 的原生顶层和子窗口，再对标题、`QMessageBox` 类名、完整警告文本以及唯一 `OK` 按钮做精确匹配。它必须作为可访问交互桌面的独立进程运行；桥接客户端在隔离环境中启动的子进程不能代替该条件。

## 10. 合规状态

本轮只验证技术可行性。目录中的所有外观资产仍默认：

```text
license_status = prototype-only
```

本地可加载、可保存或可导出不等于允许用于 AI/ML 训练。采购、导出和正式数据生产前仍需逐包核验 Reallusion 与第三方许可证。

## 11. 2026-07-24 BodyFit 冻结结果

运行时策略已经从 Neutral Base 上写入少量 Morph，切换为直接加载 8 个 hash 锁定的权威 `.ccProject`：

- 8 个项目合计 `295474408` bytes（约 `281.79 MiB`）。
- 构建器会重新计算并核对每个项目的 SHA-256 与大小；任一项目变化都会拒绝重建清单。
- `cc_body_preset_library_v1.json` 固定声明 `body_application_mode = source_project`。
- 角色 manifest 编译器必须继承该模式和 `expected_eyeball_move_weight`，否则拒绝编译。
- Morph 向量继续作为漂移检测与审计依据，不再作为运行时体型复原入口。

8 个体型分别在 CC5 中通过独立加载验证：

```text
00_engine/outputs/character_creator_bridge/artifacts/
  source_body_canonical_m01_20260724_01/
  source_body_canonical_m02_20260724_01/
  source_body_canonical_m03_20260724_01/
  source_body_canonical_m04_20260724_01/
  source_body_canonical_f01_20260724_01/
  source_body_canonical_f02_20260724_01/
  source_body_canonical_f03_20260724_01/
  source_body_canonical_f04_20260724_01/
```

共同结果：

- `8/8` Body/Junction fingerprint 与清单一致。
- `8/8` `Eyeball Move = 0.0`。
- `8/8` LookAt controller 有效。
- `8/8` 未检测到 Face 或 Other Morph 的意外变化。

完整装配回归：

```text
source_body_m04_full_20260724_01
source_body_f04_reboot_full_20260724_01
```

男女 Heavy 样本均通过 Head preset、Face identity 和外观装配；面部后 Body/Junction 不变，外观后所有 Morph 不变，identity 层未写入 `Eyeball Move`。预览中未发现明显的头颈断层、眼球脱离眼眶或肩部破面。当前默认 Lightroom 的灰白眼球材质只用于几何检查，不作为虹膜颜色审核依据。

## 12. 2026-07-25 眼球材质验证结果

批准以下 12 个 CC5 眼球资产：

```text
D:\CharacterCreator_sucai\Reallusion Templates\Actor\Eye\
  Eyes_01.ccEye
  Eyes_02.ccEye
  ...
  Eyes_12.ccEye
```

固定应用规则：

- 只选择 CC 弹窗中的 `Material Only`，禁止 `Replace` 整个眼球对象。
- 应用前先完成 BodyFit 和面部原型装配，不清零未主动修改的眼部 Morph。
- 每次应用必须保持原眼球对象、几何摘要、130 个眼部支撑 Morph 和 `Eyeball Move = 0.0`。
- 这 12 套资产用于虹膜/眼球材质多样性，不作为新的眼球几何或眼睛形状来源。

验证分为两层：

| 层级 | 覆盖 | 结果 |
| --- | --- | --- |
| 颜色变体探针 | 12 个资产各 1 男 + 1 女，共 24 个样本 | `24/24` 通过 |
| 代表几何矩阵 | `Eyes_01` × 32 张成人脸 × 8 个 BodyFit 轮换，共 32 个样本 | `32/32` 通过 |

所有 56 个样本均满足：

- `Material Only` 精确弹窗只点击一次。
- 只有 `CC_Base_Eye` 材质发生变化。
- 眼球对象、几何与支撑 Morph 不变。
- 正面、侧面、三分之四、向左、向右、向上和向下视图可生成。
- 未发现眼球穿出、虹膜离开可见眼区或左右眼运动不一致。

`Eyes_02` 至 `Eyes_12` 没有伪造为各自执行过 32 张脸。它们在兼容性登记中保留各自的男女代表实测；完整成人矩阵结论依据“只换材质且几何完全保留”从 `Eyes_01` 继承。该继承只适用于当前成人 CC5 HD 眼球几何族，不覆盖儿童、第三方眼球几何或未来不兼容代际。

视觉注意项：

- 个别源脸在极端向下视线中会露出较多上方巩膜；中性视线位置正常，且 12 套材质表现一致，因此记录为眼睑/姿态观察项，不判定为眼球资产故障。
- 当前 RLPy 纹理对象不能可靠暴露贴图路径，自动材质摘要无法权威区分 12 套颜色；颜色差异已通过实际预览和源文件哈希确认。
- 闭眼、眨眼和细致表情变形留到睫毛与面部动画阶段验证。

正式证据：

```text
00_engine/outputs/character_creator_bridge/artifacts/
  eye_equivalence_probe_v1_consolidated_20260725/
  eye_compatibility_matrix_v1_consolidated_20260725/

00_engine/scripts/character_creator/
  cc_eye_equivalence_probe_v1.json
  cc_eye_compatibility_batch_v1.json
  cc_eye_equivalence_visual_review_v1.json
  cc_eye_compatibility_matrix_visual_review_v1.json
  cc_appearance_compatibility_v1.json
  cc_appearance_domain_policy_v1.json
```

## 13. 2026-07-25 眉毛验证结果

批准用户指定目录中的 13 套 CC5 HD Brows 资产：

```text
D:\CharacterCreator_sucai\Reallusion Templates\Hair\Group\Eyebrows\
  HD Brows_F\  6 套
  HD Brows_M\  7 套
```

本轮批准范围不包含外观目录中另外 7 套未被用户选中的眉毛。

固定应用规则：

- 女性 6 套进入成人女性眉毛池，男性 7 套进入成人男性眉毛池。
- 作为眉毛 group 加载并替换现有 `Brow AvatarPart`，不按普通头发对象或仅材质变体处理。
- 眉毛验证以头部和面部为中心，身体保持 Average；眉毛不需要为 8 个 BodyFit 分别制作版本。
- 成人 CC5 HD 以外的儿童头型、第三方头型和跨性别混用需单独验证。

验证结果：

| 项目 | 覆盖 | 结果 |
| --- | --- | --- |
| 已完成组合 | 13 套眉毛，共 79 个成人面部组合 | `79/79` 通过 |
| 高风险女性资产 | `Female_Untamed` × 16 张女性面部 | `16/16` 通过 |
| 高风险男性资产 | `Male_Bushy` × 16 张男性面部 | `16/16` 通过 |
| 高风险男性资产 | `Male_Faint Unibrow` × 16 张男性面部 | `16/16` 通过 |

检查内容包括中性正面、侧面、三分之四、双侧抬眉、双侧压眉和单侧抬眉。未发现明显漂浮、皮肤穿透、眉毛卡片断裂或左右绑定错误。

正式证据：

```text
00_engine/outputs/character_creator_bridge/artifacts/
  eyebrow_compatibility_v1_consolidated_20260725/

00_engine/outputs/character_creator_bridge/
  eyebrow_review_20260725/

00_engine/scripts/character_creator/
  cc_eyebrow_compatibility_batch_v1.json
  cc_eyebrow_compatibility_visual_review_v1.json
  cc_appearance_compatibility_v1.json
```

## 14. 2026-07-26 睫毛验证与弹窗自动化

批准用户指定 `1.HD Natural` 目录中的 9 套睫毛：

```text
Curled
Delicate
Dense
Dense_Extended
Lush
Lush_Extended
Sparse and Short
Straight
Thin and Drooping
```

固定应用规则：

- 作为 `ccAvatarPreset` 加载，不再按旧的 `Replace / Material Only` 弹窗处理。
- 仅当 CC 窗口同时精确包含 `Apply Character Preset`、三个指定复选框和 `Apply / Cancel` 时自动执行。
- `Apply Morph`、`Apply Textures` 和 `Restore neutral lash strip before application.` 必须全部为勾选状态，然后只点击一次 `Apply`。
- 未知弹窗只取消当前加载并让任务失败，不允许猜测按钮或按屏幕坐标点击。
- 9 套资产进入成人男女共享的 HD Natural 睫毛池；HD Makeup、Stylized、儿童和第三方头型不在本轮批准范围。

验证结果：

| 项目 | 覆盖 | 结果 |
| --- | --- | --- |
| 男性源脸 | `M02_Average` × 9 套睫毛 | `9/9` 通过 |
| 女性源脸 | `F02_Average` × 9 套睫毛 | `9/9` 通过 |
| 自动弹窗 | 18 次角色预设加载 | `18/18` 精确匹配并自动确认 |
| 眼部隔离 | Eye AvatarPart 身份与 `Eyeball Move` | `18/18` 保持 |
| 图像证据 | 每组合 6 个视图，共 108 张 | 完整 |

检查内容包括中性正面、三分之四、侧面、双眼闭合、单眼闭合和双眼睁大。联系表未发现明显睫毛漂浮、眼皮穿透、左右绑定错误或闭眼变形断裂。

当前批准是成人共享候选池结论。睫毛资产本身已经通过完整男女源脸测试，但尚未与 V3 最终安全脸形成组合矩阵；接入正式 manifest 前仍需在 V3 生成脸上执行同样的眼睑动态回归。

正式证据：

```text
00_engine/outputs/character_creator_bridge/artifacts/
  eyelash_direct_matrix_m_20260726_01/
  eyelash_direct_matrix_f_20260726_01/

00_engine/scripts/character_creator/
  cc_eyelash_direct_matrix_v1.json
  cc_eyelash_compatibility_visual_review_v1.json
  cc_make_eyelash_contact_sheet.py
```

## 15. 2026-07-26 皮肤与三年龄验证

皮肤池只使用 ActorMIXER CORE Library 中名称年龄 `Age <= 23` 的 2K `.ccSkin`。共冻结 21 套：女性 12 套、男性 9 套。供应方目录标签只用于库存分组，不作为国籍或族裔真值。

固定应用规则：

- 女性皮肤应用到完整女性源脸，男性皮肤应用到完整男性源脸。
- 精确识别 `Apply Material` 弹窗；应用材质、Shader 纹理和参数，保留独立动态皱纹策略。
- 每套皮肤应用后依次设置 `Full Face Elder=0/50/100`，只改变面部年龄，不改变身体体型。
- 每个年龄状态渲染正面、三分之四和侧面。
- 加载后必须保持身份与身体 Morph、Eye AvatarPart、`Eyeball Move` 和年龄循环复位不变。

验证结果：

| 项目 | 覆盖 | 结果 |
| --- | --- | --- |
| 皮肤资产 | 女性 12 + 男性 9 | `21/21` 通过 |
| 年龄状态 | `young/middle/older` | `63/63` 通过 |
| 图像证据 | 每状态 3 个视图 | `189/189` 完整 |
| 参数隔离 | Morph、眼球和年龄复位 | `21/21` 保持 |
| 自动弹窗 | `Apply Material` | `21/21` 精确匹配并自动确认 |

RLPy 对 `Age21-AliaRay_2k` 没有暴露纹理样本，因此该套无法仅靠材质 API 指纹区分；固定机位渲染确认皮肤已变化，其余隔离检查均通过。同性别青年皮肤最接近的一对仍有 `24.17%` 像素发生明显变化；最弱的相邻年龄变化仍有 `5.90%` 像素发生明显变化。

正式证据：

```text
00_engine/scripts/character_creator/
  cc_skin_age_matrix_v1.json
  cc_summarize_skin_age_validation.py

00_engine/outputs/character_creator_bridge/artifacts/
  skin_age_matrix_final_20260726_01/
```

该结论批准 21 套皮肤进入首版成人候选池，但不自动扩展到儿童、第三方头型或未来极端 HeadFit。

## 16. 2026-07-27 男性胡须验证与 Undo 弹窗守卫

批准以下 5 套男性胡须：

```text
D:\CharacterCreator_sucai\Reallusion Templates\Hair\Group\Beard\
  Country Style.rlhair
  Stubble.rlHair
  The Cowboy.rlhair
  Thick Chin Curtain.rlHair
  Viking.rlhair
```

验证矩阵固定使用 `M02_Average` BodyFit，并覆盖全部 9 张 V3 男性生产主面部。每个胡须与每张脸都生成中性正面、三分之四、侧面、微笑、张嘴正面和张嘴三分之四视图。

| 项目 | 覆盖 | 结果 |
| --- | --- | --- |
| 胡须资产 | 5 套 | `5/5` 通过 |
| 男性面部组合 | 5 套 × 9 张 V3 主面部 | `45/45` 通过 |
| 图像证据 | 每组合 6 个视图 | `270/270` 完整 |
| Morph 隔离 | 面部配方、Body、Junction | `45/45` 保持 |
| 面部最大绝对误差 | 应用前后 | `0.0` |

CC 对胡须使用独立 `EAvatarPartType_Beard`。验证器此前只清点普通 Hair、Clothes 和 Accessories，导致四套成功加载的资产被误报为失败；现已显式登记 `facial_hair -> EAvatarPartType_Beard`。`Viking` 同时具有 4 个 Beard AvatarPart 和一个 `Viking Beard` 场景对象，因此验证器允许该域采用 AvatarPart 与场景对象双重表示。

人工联系表检查未发现明显漂浮，或胡须穿入嘴唇、脸颊、下巴和颈部。该结论只批准成人男性 V3 主面部；女性、儿童、第三方头型和未来极端 HeadFit 不自动继承。

本轮还修复了反复出现的精确警告：

```text
Failed to record undo/redo step. Undo manager will restart.
```

旧守卫对整棵桌面 UIA 树做后代搜索，可能因进程令牌访问失败而长时间阻塞。新守卫先通过 Win32 限定目标 CC PID，再仅检查该进程窗口。最终 40 个矩阵样本中自动处理 396 次该警告，自动化错误 0、未知弹窗 0，未再要求人工点击。守卫不能消除 CC 内部 Undo 警告的产生，但可以在严格匹配后可靠解除阻塞。

正式证据：

```text
00_engine/outputs/character_creator_bridge/artifacts/
  facial_hair_matrix_v2_merged_20260727_01/

00_engine/scripts/character_creator/
  cc_facial_hair_compatibility_batch_v1.json
  cc_facial_hair_compatibility_visual_review_v1.json
  cc_appearance_compatibility_v1.json

00_engine/character_creator_bridge/
  cc_undo_dialog_guard.ps1
```
