# CC 面部身份与年龄技术流程

> 文档角色：`technical_spec_and_runbook`
> 状态：`production`；Headshot 扩展为 `planned`
> 上级入口：[`../CHARACTER_FACTORY_MASTER_SPEC.md`](../CHARACTER_FACTORY_MASTER_SPEC.md)
> 最近核验：2026-08-06

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

## 6. Headshot 预留

Headshot 阶段当前为 `planned`。第一步只做 4 人离线 smoke，验证图片输入、生成、保存、重载、Facial Profile、后脑、弹窗和脚本可达性。通过后先建立 10 个候选，再比较是否扩到 20。

开始实施时创建 `HEADSHOT_PIPELINE.md`。在此之前不得把互联网图片、Headshot 输出或估算年龄写入当前生产池。

## 7. 验证

每个新主原型和完整角色必须覆盖正面、3/4、侧面、后脑、双/单眼闭合、四向视线、眯眼、睁大、眉毛、微笑、张嘴和中性恢复。自动门禁与人工检查见 [`../validation/VALIDATION_AND_RECOVERY.md`](../validation/VALIDATION_AND_RECOVERY.md)。
