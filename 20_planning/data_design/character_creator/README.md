# Character Creator 角色生成与变体设计

> 日期：2026-07-27  
> 状态：CC 端固定体型、Face V3 动态闭环和首轮外观资产验证已完成；导出与 UE 导入待验证  
> 关联：`../../discussions/05_character-creator-automation.md`、`../README.md`

当前实现、产物、质量门槛与恢复顺序见 [`STATUS.md`](./STATUS.md)。成人面部的唯一装配流程、资产池、年龄/皮肤策略及动态质量门槛见 [`FACIAL_GENERATION.md`](./FACIAL_GENERATION.md)。

本文记录当前关于 Reallusion Character Creator 5（CC5）用于批量生成 UE 渲染角色的设计结论。目标不是让 agent 直接操作 CC UI，而是建立一个可复现、可审计、可扩展的角色资产生成流程。

## 1. 总体结论

Character Creator 可以作为本项目的角色创作器，但应采用“固定插件逻辑 + 结构化配置”的方式控制：

```text
Codex / Agent
  -> 生成 character_spec.json
  -> 不直接生成任意 Python 代码

CC5 Python 插件
  -> 读取 character_spec.json
  -> 根据白名单资产和 morph slider 执行修改
  -> 导出 FBX / JSON / textures / log

Codex / Agent
  -> 检查 result.json、导出文件、日志
  -> 可选导入 UE 做低分辨率预览验证
```

核心原则：

- Agent 只写“目标配置”，不写任意可执行脚本。
- CC 插件负责把配置映射到真实 RLPy API、morph slider、资产路径和导出选项。
- 所有可选资产、slider、材质槽先由插件扫描成 `cc_capabilities.json`，再允许 agent 选择。
- 对训练/发布敏感的资产，必须先进入资产台账并完成许可证状态标记。

## 2. 当前本机 CC5 能力线索

本机安装与素材路径：

```text
D:\CharacterCreator
D:\CharacterCreator\Character Creator 5
D:\CharacterCreator\Character Creator 5\Bin64\RLPy.py
D:\CharacterCreator_sucai\Reallusion Custom\ActorMIXER
```

从 `RLPy.py` 中已看到的关键能力：

```text
RFileIO.LoadFile(...)
RFileIO.LoadObject(...)
RFileIO.LoadFbxFile(...)
RFileIO.LoadClotheFromFbx(...)
RFileIO.ExportFbxFile(...)
RFileIO.CheckExportFbxHasLicense(...)

RIAvatar.GetAvatarShapingComponent()
RIAvatar.GetMorphComponent()
RIAvatar.GetMaterialComponent()
RIAvatar.GetClothes()
RIAvatar.GetHairs()
RIAvatar.LoadAccessoryWithTransferSkinWeight(...)

RIAvatarShapingComponent.GetShapingMorphCatergoryNames()
RIAvatarShapingComponent.GetShapingMorphIDs(category)
RIAvatarShapingComponent.GetShapingMorphMinMax(id)
RIAvatarShapingComponent.GetShapingMorphWeight(id)
RIAvatarShapingComponent.SetShapingMorphWeight(id, weight)

RIMaterialComponent.GetMaterialNames(mesh)
RIMaterialComponent.LoadImageToTexture(...)
RIMaterialComponent.SetAttributeValue(...)

RApplication.GetDefaultContentFolder(...)
RApplication.GetCustomContentFolder(...)
RApplication.GetContentFilesInFolder(...)
```

这说明脚本层面不仅能调 shaping slider，也能加载内容库资产、替换/读取材质、处理衣服和头发对象，并导出 Unreal preset FBX。

## 3. CC Agent Bridge 设计

第一版插件建议只实现保守功能：

```text
cc_agent/
  inbox/
    command.json
    character_spec.json
  outbox/
    cc_capabilities.json
    result.json
    export_manifest.json
    logs/
  exports/
    character_id/
      character.fbx
      character.json
      textures/
```

推荐命令类型：

```json
{
  "command": "build_character",
  "spec_path": "D:/UE/cc_agent/inbox/character_spec.json",
  "output_dir": "D:/UE/cc_agent/exports/anchor_m_001_bodyfit_heavy"
}
```

推荐角色配置结构：

```json
{
  "character_id": "anchor_m_001_bodyfit_heavy",
  "identity_id": "anchor_m_001",
  "pool": "edit_anchor",
  "base": "male",
  "body_fit": "M_Heavy",
  "head_fit": "HeadFit_02",
  "face_variant": "face_017",
  "assets": {
    "hair": "hair_short_03",
    "upper": "outfit_casual_jacket_01",
    "lower": "outfit_jeans_01",
    "shoes": "shoes_sneaker_01"
  },
  "materials": {
    "iris_color": [1.0, 0.82, 0.18],
    "skin_tone": "skin_tone_04",
    "hair_color": [0.08, 0.05, 0.03]
  },
  "export": {
    "target": "unreal",
    "texture_size": 2048,
    "export_json": true
  }
}
```

不建议让配置里出现任意本地路径。应使用资产 ID，由插件查白名单映射表得到真实路径。

## 4. 可配置属性分层

角色变化分为三类。

### 4.1 CC baked variants

这些变化最好在 CC 中完成并导出，因为它们影响几何、蒙皮、贴合或复杂贴图烘焙：

- 体型：胖瘦、肌肉、肩宽、腰臀比例、腿长、身高比例。
- 头颅外轮廓：头宽、颅顶高度、后脑深度、耳朵位置、脖子粗细。
- 脸型结构：眼睛形状、鼻梁、下颌、脸颊、嘴唇结构。
- 大幅年龄结构：年轻/成熟/老年。
- 复杂皮肤 preset、SkinGen 层、皱纹、毛孔、复杂妆容。
- 衣服贴合、鞋、手套、帽子、头发适配。
- 眼球/牙齿/睫毛等模型级替换。

### 4.2 UE runtime variants

这些变化适合在 UE 中做，成本低且适合构造数据 pair：

- 眼睛颜色、瞳孔材质、虹膜贴图。
- 皮肤色调、粗糙度、小范围贴图变化。
- 发色、服装颜色、材质粗糙度。
- 妆容、雀斑、疤痕、纹身 decal 或 mask。
- 动作、姿态、相机、光照、场景位置。
- 已导出的 morph target 小幅变化。

### 4.3 需要条件验证的中间项

- 眼睛大小：只有导出对应 morph target 或骨骼控制时才建议在 UE 改。
- 眼睛形状：通常涉及眼睑/眼窝/眼球位置，不建议 UE 临时强改。
- 身高：UE actor scale 可以小幅使用，但大幅缩放会影响脚底、动画和相机。
- 换皮肤 preset：同 UV 的贴图替换适合 UE；复杂 CC 皮肤系统建议在 CC 中 bake。

## 5. BodyFit 体型预设

不建议为每个角色随机生成连续体型。原因是不同体型下衣服导出后通常已经变成适配该体型的网格，如果每个 identity 都有很多体型，会产生资产爆炸。

正式策略：

```text
固定少量 BodyFit 体型
服装按 BodyFit 适配导出
普通角色只绑定一个 BodyFit
少量 edit anchor 角色才导出多体型版本
```

建议第一版正式体型库：

| ID | 性别 | 视觉目标 | 体型重点 |
| --- | --- | --- | --- |
| `M_Slim` | male | 偏瘦 | 体量低，四肢细，肩不过宽 |
| `M_Average` | male | 普通 | 中等身高体量，自然成年人 |
| `M_Muscular` | male | 强壮 | 肩宽、胸背厚、手臂腿部更明显 |
| `M_Heavy` | male | 偏胖/厚重 | 腰腹、胸背、臀腿整体更大 |
| `F_Slim` | female | 偏瘦 | 腰细、四肢细、肩窄 |
| `F_Average` | female | 普通 | 中等比例，自然成年人 |
| `F_Athletic` | female | 运动型 | 肩背、手臂、腿部更有力量 |
| `F_Heavy` | female | 偏胖/丰满 | 腰臀、腿部、上身整体更大 |

体型不需要精确拟合真实厘米值，但应参考真实人体分布，避免极端比例。参考数据源：

- CDC/NHANES anthropometry: https://stacks.cdc.gov/view/cdc/174595
- ANSUR II: https://www.openlab.psu.edu/ansur2/
- CAESAR: https://www.humanshape.org/CAESAR/

## 6. ActorMIXER / ccMixerPreset 使用方式

用户现有素材中存在大量 `.ccMixerPreset`，例如：

```text
D:\CharacterCreator_sucai\Reallusion Custom\ActorMIXER\Character\HD Human Anatomy Set\HA Male Bodybuilder_Character.ccMixerPreset
```

已检查该文件：

- 文件头为 `_RLZeus`。
- 文件大小约 4.6 MB。
- 内容是 Reallusion 封装的二进制资产，不是 JSON/XML。
- 不应直接解析文件内容。

正确路线是让 CC 自己加载：

```python
RLPy.RFileIO.LoadFile(r"D:\...\HA Male Bodybuilder_Character.ccMixerPreset")
```

然后扫描当前角色的 shaping/morph 权重，保存为我们自己的 body vector：

```text
加载 base male/female
-> 应用 .ccMixerPreset
-> 扫描所有 shaping morph weight
-> 保存 body_vector.json
-> 后续可用 SetShapingMorphWeight 复现或混合
```

混合策略：

```text
新 BodyFit =
  0.70 * Male Athletic
+ 0.20 * Male Bodybuilder
+ 0.10 * Body Ratio Tall
```

实际应用时必须 clamp 范围，且一次最多混合 2-4 个 preset，避免衣服穿模、身体比例异常或动画问题。

## 7. HeadFit 与面部多样性

头部也需要适配模板，但不应把所有面部变化都做成头部网格变体。建议分层：

```text
HeadFit：控制头颅外轮廓，变化小，服务头发/帽子/眼镜适配
FaceVariant：控制五官、肤色、年龄感、妆容，变化大
```

第一版建议先使用 4 个 `HeadFit`。如后续发现性别差异导致适配问题，再扩展为男女各 4 个。

`HeadFit` 控制项：

- head scale
- head width
- head height
- skull depth
- forehead depth
- ear position
- jaw width
- neck width

这些变化要小，因为它们影响头发、帽子、眼镜、耳饰适配。

`FaceVariant` 可放开的项：

- 眼距、眼睛形状微调、眉骨。
- 鼻梁、鼻头、鼻宽。
- 嘴唇厚度、嘴角、下巴长度。
- 脸颊丰满度、年龄感。
- 肤色、皮肤细节、皱纹、胡子、妆容、瞳色。

强贴合头部轮廓的资产需要按 `HeadFit` 适配：

```text
头发、帽子、头盔、面罩
```

中等贴合资产先测试能否通过 socket、骨骼或小偏移复用：

```text
眼镜、耳饰、胡子、眉毛
```

弱贴合或材质类资产通常不需要为每个 HeadFit 单独导出：

```text
眼睛颜色、瞳色、皮肤贴图、妆容
```

## 8. 资产库避免组合爆炸

不要导出：

```text
8 个 BodyFit x 4 个 HeadFit x 所有服装 x 所有头发
```

应分开管理适配库：

```text
BodyFit 库
  8 个身体体型
  每个体型有对应适配好的服装 / 鞋 / 手套

HeadFit 库
  4 个头部适配模板
  每个头型有对应适配好的头发 / 帽子 / 强贴合头部资产
```

角色组装时选择：

```text
body_fit = M_Average
outfit = BodyFit_M_Average 下的一套服装

head_fit = HeadFit_02
hair = HeadFit_02 下的一套发型

face_variant = face_017
skin = skin_04
eyes = eye_material_03
```

管理逻辑可以分开，但最终导出推荐仍然先使用完整角色：

```text
CC 内组装完整角色 -> 导出完整角色 FBX -> UE 渲染
```

不要在第一阶段就把 UE 运行时模块化换装系统作为核心依赖。

## 9. Base Pool 与 Edit Anchor Pool

角色库应拆成两层：

```text
Base Pool
  大量普通角色
  每个角色只导出一个稳定版本
  用于普通渲染、多场景、多动作、多相机数据

Edit Anchor Pool
  少量锚点角色
  每个锚点角色导出若干受控变体
  用于 pair / edit / counterfactual 数据
```

普通角色不需要每个 identity 都导出所有体型、脸型、皮肤和头部变体。只有 edit anchor 才做多版本。

示例：

```text
普通数据生成：
  100+ identities
  每个 identity 只绑定 1 个 BodyFit
  通过服装、发型、肤色、动作、场景、相机增加多样性

体型编辑 pair：
  5-10 个 anchor identities
  每个 anchor identity 导出 3-4 个体型版本
  用于 same identity, different body type
```

这种策略同样适用于其他必须在 CC 中 baked 的变化：

- 体型变化。
- 头颅外轮廓变化。
- 脸型结构变化。
- 眼睛形状变化。
- 年龄结构变化。
- 复杂皮肤 preset。
- 复杂妆容/胡子。
- 服装/头发/帽子适配版本。

## 10. UE 中适合构造的简单替换 pair

UE 侧适合做低成本、低穿模风险的编辑 pair。一次 pair 尽量只改变一个主变量。

| 编辑类型 | UE 适合程度 | 推荐实现 |
| --- | --- | --- |
| 服装颜色 | 高 | 材质实例参数 |
| 眼睛颜色 | 高 | iris 材质参数或贴图 |
| 皮肤色调 | 高 | skin material 参数、贴图、roughness |
| 妆容/雀斑/疤痕/纹身 | 高 | 材质层、mask、decal |
| 发色 | 高 | 材质参数或贴图 |
| 服装款式 | 中高 | 只在同一 BodyFit 下换已适配服装 |
| 头发/帽子/眼镜 | 中高 | 只在同一 HeadFit 下换已适配资产 |
| 动作/姿态 | 高 | animation sequence / montage |
| 体型替换 | 中 | 用 edit anchor 的完整角色替换 |
| 身高 | 中 | 小幅 actor scale，需脚底和相机检查 |
| 眼睛大小 | 低到中 | 必须有 morph target 或骨骼控制 |
| 眼睛形状 | 低 | 建议 CC baked |
| 脸型/头骨 | 低 | 建议 CC baked |

体型 pair 的推荐方式：

```text
Pair A:
  Character = anchor_m_001_M_Average
  same face / same hair / same outfit style / same animation / same camera

Pair B:
  Character = anchor_m_001_M_Heavy
  same face / same hair / same outfit style / same animation / same camera
```

本质是“整角色替换”，但通过 anchor identity 和保持其他变量不变，让 pair 的语义聚焦在体型变化上。

## 11. 元数据建议

普通角色：

```json
{
  "character_id": "char_m_087",
  "pool": "base",
  "identity_id": "char_m_087",
  "body_fit": "M_Average",
  "head_fit": "HeadFit_02",
  "face_variant": "face_087",
  "supports_pairs": ["outfit_color", "eye_color", "hair_color"]
}
```

锚点角色体型变体：

```json
{
  "character_id": "anchor_m_001_bodyfit_heavy",
  "pool": "edit_anchor",
  "identity_id": "anchor_m_001",
  "variant_axis": "bodyfit",
  "variant_value": "M_Heavy",
  "body_fit": "M_Heavy",
  "head_fit": "HeadFit_02",
  "outfit_fit": "M_Heavy",
  "supports_pairs": ["bodyfit_swap", "outfit_color", "skin_tone"]
}
```

UE 渲染样本中应记录：

```text
character_id
identity_id
pool
body_fit
head_fit
face_variant
outfit_id
hair_id
material_variant_id
animation_id
scene_id
camera_id
edit_axis
source_character_id
target_character_id
```

## 12. 合规注意

CC/Reallusion 资产的训练、深度学习、再分发、导出权利必须单独核验。当前只能确认技术路径，不代表许可证允许用于训练数据。

执行规则：

- 每个 CC 内容包、ActorMIXER preset、发型、服装、皮肤、妆容都要进入资产台账。
- 许可证未明确前标记为 `candidate` 或 `prototype-only`。
- 对 AI/ML training 权利必须单独字段记录，不能因为本地能导出就默认可训练。
- 对第三方购买资产同样执行 NoAI / training 权利核验。

参考入口：

- Reallusion Content License: https://www.reallusion.com/license/content.html
- CC/iC Auto Setup for Unreal: https://www.reallusion.com/auto-setup/unreal-engine/default.html
- RLPy RFileIO: https://wiki.reallusion.com/IC_Python_API%3ARLPy_RFileIO

## 13. 下一步验证

> 本节保留最初路线图。其第 1-7 步已经由当前 CC 角色工厂原型覆盖，实际进度以 [`STATUS.md`](./STATUS.md) 为准。

最小可行验证顺序：

1. 在 `D:\UE` 下建立 `cc_agent` 原型目录，不直接写入 CC 安装目录。
2. 写 CC 插件扫描脚本：读取当前 avatar 的 morph categories、slider IDs、材质槽、衣服、头发。
3. 在 CC 中打开 base male / base female。
4. 用 Python 加载一个 `.ccMixerPreset`。
5. 扫描应用前后的 shaping morph weight 差异。
6. 保存 `body_vector.json`。
7. 用 `SetShapingMorphWeight` 复现该体型。
8. 导出 Unreal preset FBX + JSON + textures。
9. 导入 UE 测试材质、骨骼、动画和预览渲染。
10. 再扩展到 BodyFit / HeadFit / Base Pool / Edit Anchor Pool。

第一轮成功标准：

- 插件能读出当前角色能力表。
- `.ccMixerPreset` 能通过 `RFileIO.LoadFile` 应用到角色。
- 应用结果能被扫描成 morph weights。
- 导出的 FBX 可以在 UE 中打开、播放动作、显示材质。
- metadata 能明确记录体型、头型、identity、变体轴和资产来源。

## 14. 2026-07-27 实现结论

- 8 个成人 BodyFit 固定使用 hash 锁定的 `.ccProject` 作为权威入口；morph 向量只用于漂移检测和审计。
- Face Generator V3 已成为唯一生产面部入口：200 条确定性结构配方使用 17 个完整主原型和 35 个非口部局部 Morph；全部 17 个主原型加 8 个 BodyFit 代表随机脸的最终动态矩阵 `25/25` 通过。旧 V2.1 只保留作静态历史证据，完整规则见 [`FACIAL_GENERATION.md`](./FACIAL_GENERATION.md)。
- 本地外观目录现有 941 个逻辑资产，配方只允许引用白名单 `asset_id`。
- 两套男女外观均已完成 Average pilot 和 6 个非 Average BodyFit 扩展；16 个外观 preset 中 15 个视觉通过、1 个男性 Heavy 组合因下摆穿模被拒绝。
- 兼容性登记现有 15 个资产的正向证据与 1 条结构化拒绝组合，其余 926 个资产仍未验证。
- 配方支持按精确场景对象名清理冲突基础内衣；女性 `Dress_A` 组合会在装配前删除 `Bra` 并验证删除结果。
- 兼容性驱动的角色 manifest 编译器已接入 Face V3，能稳定选择 BodyFit、完整主面部原型、白名单局部 Morph 和完整外观，同时排除未验证资产及拒绝组合。
- 8 角色 V3 编译 pilot 成功；历史 `F04_Heavy` 产物已直接提交 CC，作为外观与桥接端到端证据。V3 面部本身以 25 例、375 张动态检查图为正式证据。
- 项目仍未进入 FBX 批量导出和 Unreal 导入阶段。

## 15. 兼容性 Manifest 编译

入口：

```text
00_engine/scripts/character_creator/cc_compile_character_manifest.py
```

默认 pilot：

```text
cc_character_manifest_requests_pilot_v1.json
cc_character_manifest_pilot_v1.json
```

执行：

```powershell
python .\00_engine\scripts\character_creator\cc_compile_character_manifest.py `
  --requests .\00_engine\scripts\character_creator\cc_character_manifest_requests_pilot_v1.json `
  --output .\00_engine\scripts\character_creator\cc_character_manifest_pilot_v1.json
```

每个角色必须提供 `character_id` 和 `bodyfit_id`。`face_recipe_id` 可显式指定，也可由顶层整数 `seed` 和 `character_id` 确定性选择。`appearance` 可选字段包括：

```json
{
  "appearance_recipe_id": "F_DRESS_01",
  "validation_preset_id": "APPV2MAT_F04_HEAVY_0001",
  "require_complete": true
}
```

编译器只从兼容性登记中选择已视觉通过的完整组合，不允许未验证资产，也不允许 `rejected_combinations`。显式请求已拒绝组合时输出结构化 `appearance_recipe_rejected`，并将 `presets` 置空，避免部分结果被误提交 CC。

## 16. 外观域独立验证

除服装、鞋和完整发型外，当前目录还包含：

```text
159 overall skins
94 SkinGen skin presets
59 eye sets
18 teeth sets
20 eyebrow sets
13 facial-hair sets
75 makeup presets
20 accessories
```

这些资产不能全部沿用“场景对象数量发生变化”的成功条件。运行器现按域使用两种证据：

- `scene_inventory`：服装、毛发和配饰必须使 `GetClothes/GetHairs/GetAccessories` 清单发生变化。
- `material_fingerprint`：皮肤、SkinGen、妆容、眼睛和牙齿必须使 avatar 材质、shader 参数或纹理采样 digest 发生变化。

首轮清单：

```text
00_engine/scripts/character_creator/
  cc_appearance_domain_policy_v1.json
  cc_appearance_domain_pilot_v1_config.json
  cc_appearance_domain_pilot_v1.json
```

清单含 10 条 preset，每条只改变 1 个域。实际执行必须逐条提交：

```powershell
python .\00_engine\character_creator_bridge\cc_bridge_client.py validate-bodies `
  --library-file .\00_engine\scripts\character_creator\cc_appearance_domain_pilot_v1.json `
  --preset-id APDOM_F_SKIN_0001 `
  --output-dir <unique-output-directory> `
  --confirm-scene-replace
```

不得一次提交全部 10 条。每条执行后检查 CC private memory；达到 24 GB 时停止，不由 agent 自动重启 CC。数值成功仍不等于兼容性通过，必须完成该 preset 的 `appearance_validation_plan.required_views` 视觉审核。牙齿还需要张嘴表情视图，SkinGen 与妆容是否可叠加需另做层栈验证。
