# CC 面部身份与年龄技术流程

> 文档角色：`technical_specification`
> 状态：`production`
> 适用阶段：`WF-01..WF-03,WF-07`
> 权威范围：Face V3 身份、Facial Profile、局部 Morph、年龄和 Headshot 边界
> 上级入口：[`README.md`](./README.md)
> 上游：Face seed/recipe/policy 机器 JSON
> 下游：角色定义、CC 装配和 UE 年龄 Morph
> 最近核验：2026-08-10

Headshot 扩展当前为 `validated_pilot`：`RM-05B` 已通过，但尚未改变 Face V3 生产默认值。

迁移方向已经确定，但执行已延期：十个 Headshot 候选完成视觉状态后先冻结暂存；第一批数据交付后，才由 `RM-06` 继续评估扩容和生产迁移。当前 Face V3 仍是唯一稳定生产默认值，不与 Headshot 候选混合抽样。

## 1. 当前 Face V3 模型

```text
完整同性交付主面部 seed
  + 与 seed 绑定的 Facial Profile
  + 配方列出的安全局部 Morph
  + BodyFit 固定 Head Scale / Neck Height
```

权威文件：

| 文件 | 当前值 |
| --- | --- |
| `cc_face_seed_library_v1.json` | 20 seed，10 male + 10 female |
| `cc_face_identity_policy_v1.json` | 审计 51 个控制：41 个 `local`、10 个 `macro` |
| `cc_face_recipes_v3_200.json` | schema 3，200 条确定性配方 |
| `cc_generate_face_recipes_v3_config.json` | 每性别 100、随机种子 `20260727` |

动态筛选排除眼部、口部和整头宏后，当前 200 条配方实际使用 28 个 Brow/Cheek/Ear/Forehead/Jaw/Nose 局部 Morph。20 个 seed 中，男女 Neutral 技术 seed 不进入生产身份抽样；`F09_Female_F` 因满幅微笑时下排牙齿穿出下唇而拒绝。当前 17 个生产主原型均在 200 配方中出现。

## 2. 为什么不能清零整张脸

主 Head Preset 不只包含可见 Morph，还携带眼睑、眼球、牙齿、口腔和 Facial Profile 支撑。将未使用 Morph 批量置零会拆开这些成对状态，历史上已经导致眼球错位和闭眼穿模。

强制顺序：

1. 加载 BodyFit 源项目。
2. 加载同性交付主 Head Preset。
3. 收敛 BodyFit 眼球/牙齿 Actor Parts 到主原型目标。
4. 通过角色内容加载接口应用该 seed 的 Facial Profile。
5. 验证 Facial Profile 未改变 Body/Junction、静态 Head Morph 或眼球对象。
6. 只修改该配方实际列出的局部 Morph。
7. 最后应用 BodyFit 的 Head Scale 和 Neck Height。

禁止：

- 叠加第二个整头身份宏。
- 随机修改眼部和口部 Morph。
- 把 Facial Profile 当作普通 `.rlWrinkle` 加载。
- 用一个性别的主面部或 Facial Profile 装配另一个性别。

## 3. 生成新的 Face V3 候选配方

这一步只在重建配方池时执行，不属于日常角色生成。

```powershell
$LANCE_ROOT = 'D:\UE\Lance_Work'
$scriptRoot = "$LANCE_ROOT\00_engine\scripts\character_creator"
python "$scriptRoot\cc_generate_face_recipes_v3.py" `
  --config "$scriptRoot\cc_generate_face_recipes_v3_config.json" `
  --count-per-sex 100 `
  --seed 20260727
```

脚本把候选写入配置指定的独立输出目录。不得直接覆盖 `cc_face_recipes_v3_200.json`。

晋级前必须：

- 核对配方数量、ID 唯一性和男女分布。
- 所有主原型均来自 seed library，且不含拒绝 seed。
- 局部 Morph 全部属于当前动态筛选后的 28 项生产采样子集。
- 眼部、口部和整头宏为零随机修改。
- 去重、覆盖和强度分布达到计划要求。
- 代表 BodyFit 上完成中性、眨眼、视线、微笑和张嘴验证。
- 人工批准后再以新版本文件晋级，不原地覆盖历史证据。

## 4. 年龄

年龄 Morph：

```text
display = Full Face Elder
id = 2025-07-04-15-29-03_pack_old_man_face
```

| 标签 | UI | 权重 | 当前解释 |
| --- | ---: | ---: | --- |
| `young` | 0 | 0.0 | 青年成人状态 |
| `middle` | 50 | 0.5 | 中年视觉状态 |
| `older` | 100 | 1.0 | 普通老年视觉状态 |

当前分布为 `0.45/0.35/0.20`。它是视觉档位，不是精确年龄。动态皱纹男女统一使用 HD Neutral 2K，固定强度 1.0。

当前 CC 生产年龄只改变面部。身体、颈部和服装不随年龄变化；身体老化仍是实验方向。老年皮肤不与 Elder Morph 无条件叠加，当前生产池优先使用青年皮肤，再由年龄 Morph 和动态皱纹提供年龄变化。

## 5. 日常选择规则

- 请求可显式给出 `face_recipe_id`。
- 未给出时，编译器使用顶层整数 `seed` 和 `character_id` 做确定性选择。
- 同一请求、同一机器配置和同一 seed 必须得到同一配方。
- 生成 pair 时身份不变，年龄可以作为单独变体轴。
- 只有基础年龄合适的未来 Headshot 原型才允许生成老化变体；该策略尚未接入当前 seed 库。

## 6. Headshot 扩展

`RM-05B` 已完成并关闭。十候选扩展当前登记 5 女 + 5 男共 10 个来源项目；全部冻结来源保持为 `CC4 Extended / 160`，10 个独立派生项目均加载同性交付 CC5 HD Profile，并在重载后保持为 `CC5 MetaHuman / 379`。静态 Morph、眼球结构、材质、来源哈希与中性恢复通过机器门禁，Blink、三级 Smile 和 Jaw Open 可驱动。

Headshot 身份不由 shaping slider 向量承载：当前候选采用“项目几何 + Facial Profile sidecar + manifest/hash/evidence”的原型包；不能把它转换成现有 Face V3 的普通 face slider 配方。

`F_HS_001/002`、`M_HS_001/002` 状态为 `candidate_cc5_hd_rm05b_visual_accepted`；`F_HS_003..005`、`M_HS_003..005` 为机器通过、原照片已映射、等待人工视觉验收的候选。`headshot_project_seed_then_bodyfit_v1` 已在 F02/M02 上取得机器与用户 Pilot 通过；本轮只完成十原型候选池闭环和暂存，不做 10/20 比较，也不进入当前生产 seed 池。扩容、`RM-06` 配方验证和正式集成延期到服装与动画验证完成后。原始项目冻结、升级命令、原型目录、哈希、证据与接入顺序见 [`HEADSHOT_PIPELINE.md`](./HEADSHOT_PIPELINE.md)；存储决定见 [`ADR-0013`](../decisions/ADR-0013-HEADSHOT-BAKED-PROTOTYPE-STORAGE.md)。当前 Face V3 的 20 seed、17 个生产主原型和 200 条配方保持不变。

## 7. 验证

每个新主原型和完整角色必须覆盖正面、3/4、侧面、后脑、双/单眼闭合、四向视线、眯眼、睁大、眉毛、微笑、张嘴和中性恢复。机器检查见 [`VALIDATION_CATALOG.md`](../validation/VALIDATION_CATALOG.md)，人工检查见 [`VISUAL_ACCEPTANCE.md`](../validation/VISUAL_ACCEPTANCE.md)。
