# CC 外观、毛发与材质技术流程

> 文档角色：`technical_spec_and_runbook`
> 状态：`production`；服装 Look 扩展为 `planned`
> 上级入口：[`../CHARACTER_FACTORY_MASTER_SPEC.md`](../CHARACTER_FACTORY_MASTER_SPEC.md)
> 最近核验：2026-08-06

## 1. 权威文件和候选池

```text
LANCE_ROOT = D:\UE\Lance_Work
CC_ASSET_ROOT = D:\CharacterCreator_sucai
SCRIPT_ROOT = %LANCE_ROOT%\00_engine\scripts\character_creator
```

| 文件 | 职责 |
| --- | --- |
| `cc_appearance_asset_catalog_v1.json` | 969 个逻辑资产的稳定 ID、物理路径和域 |
| `cc_appearance_compatibility_v1.json` | 已通过资产、完整 Look 和拒绝组合 |
| `cc_facial_production_registry_v1.json` | 当前面部池、年龄、毛发、色素和应用顺序 |
| `cc_facial_production_registry_config.json` | Registry 构建输入 |
| `cc_face_material_quality_profile_v1.json` | 生产面部材质质量参数 |

当前生产池：

| 域 | 数量 | 加载方式 |
| --- | ---: | --- |
| Skin | 21 | 完整 `.ccSkin`，头和身体一起应用 |
| Eyes | 12 | `Material Only`，保留眼球对象 |
| Eyebrows | 13 | 替换当前眉毛资产 |
| Eyelashes | 9 | 应用 HD Natural Avatar Preset |
| Teeth | 2 | 完整 `Replace` |
| Facial hair | 5 | 仅男性，完整替换或不加载 |
| Scalp hair | 58 | 按性别呈现、轮廓和风险登记选择 |

## 2. 当前唯一应用顺序

Registry 中的顺序为：

```text
bodyfit_project
primary_head_preset
local_face_morphs
bodyfit_proportion_adjustment
skin
age_morph
dynamic_wrinkle_profile
teeth
eyebrows
eyelashes
eyes_material_only
facial_hair
scalp_hair
shared_hair_pigmentation
face_material_quality_profile
quality_assurance
```

后加载皮肤或眼球会覆盖材质质量参数，因此质量档案必须靠后；质量档案之后只能做验证、保存或导出。

## 3. 各域硬约束

### 3.1 Skin

- 当前只使用 `CC5 Human 2K/ActorMIXER CORE Library` 中年龄标注不高于 23 的青年皮肤。
- `.ccSkin` 同时改变头部和身体材质，并启用头身颜色协调。
- 年龄 Morph 和动态皱纹不由皮肤年龄替代。
- 皮肤组绑定一个色素档案，不把皮肤文件名直接当成人种标签。

### 3.2 Eyes

- 对话框必须选择 `Material Only`。
- 禁止 `Replace` 眼球对象。
- Eye AvatarPart、眼骨、LookAt、眼球几何和 `Eyeball Move=0.0` 必须保持。
- 12 套资产只提供材质/虹膜差异，不提供眼形差异。

### 3.3 Teeth

当前两套：

```text
%CC_ASSET_ROOT%\Reallusion Templates\Actor\Teeth\1 Normal Teeth.ccTeeth
%CC_ASSET_ROOT%\Reallusion Templates\Actor\Teeth\HD Teeth\_HD Teeth 2K.ccTeeth
```

完整 `Replace`。优先在加载前移除旧牙齿对象，减少选择弹窗。必须检查中性、微笑、张嘴和 3/4 张嘴。

### 3.4 Eyebrows 与 Eyelashes

眉毛按男女登记池选择。九套 HD Natural 睫毛当前允许用于成人双性角色，但每个完整脸仍需眨眼、眯眼和睁大门禁；资产加载成功不代表眼睑兼容。

### 3.5 Hair 与 Beard

- 默认呈现模式使用 `female_presentation_score`：男性 `<=0.5`，女性 `>=0.5`，0.5 可双性使用。
- `cross_presentation` 只在显式请求时放开，不作为默认随机模式。
- 发型可由多个网格组成，后续 UE 切换单位是完整 `HairStyleSet`。
- 胡须概率当前为男性 0.45；女性始终不加载。
- 被拒绝或高穿模风险发型不能通过文件存在自动晋级。

## 4. 统一毛发颜色

同一角色只抽样一次，应用到头发、眉毛和胡须。模式权重：

```text
natural_common = 0.92
natural_rare   = 0.06
dyed           = 0.02
```

当前色素档案：

```text
african_high_pigment
asian_high_pigment
caucasian_broad_pigment
middle_east_medium_high_pigment
```

年龄灰度在颜色之后计算；染发模式的可见灰度固定为 0。完整调色板和权重只由 Registry JSON 定义，本文不复制全部颜色值。

## 5. 面部材质质量档案

`cc_face_material_quality_v1` 状态为 `production_approved`。

| 域 | 参数 | 值 | 实际写入次数 |
| --- | --- | ---: | ---: |
| 左右 Cornea | `ScleraBrightness` | 0.50 | 2 |
| 左右 Cornea | `Sclera Roughness` | 0.32 | 2 |
| 左右 Cornea | `Specular Scale` | 0.70 | 2 |
| Head Skin | `MicroNormal Strength` | 0.65 | 1 |
| Head Skin | `Micro Roughness Scale` | 0.08 | 1 |
| Head Skin | `Original Roughness Strength` | 1.00 | 1 |
| Head Skin | `Cavity Strength` | 0.24 | 1 |

总计 10 项实际写入并逐项回读。档案只修改头部皮肤和角膜，不改身份 Morph、Body、眼球对象或皮肤贴图。

## 6. 新增资产流程

### APP-01：重建候选目录

- 执行模式：`SYSTEM_PYTHON`
- 只在本地资产根变化后执行。

```powershell
$LANCE_ROOT = 'D:\UE\Lance_Work'
$scriptRoot = "$LANCE_ROOT\00_engine\scripts\character_creator"
python "$scriptRoot\cc_build_appearance_asset_catalog.py" `
  --template-root "D:\CharacterCreator_sucai\Reallusion Templates" `
  --custom-root "D:\CharacterCreator_sucai\Reallusion Custom" `
  --audit <content-audit.json> `
  --output <candidate-catalog.json>
```

先生成候选文件，不直接覆盖当前 catalog。

### APP-02：域验证

1. 为一个资产建立只改变单一域的验证 preset。
2. 使用 Bridge `validate-bodies` 单条提交，不能把未知弹窗风险的多个资产一次提交。
3. 材质域使用 material fingerprint；服装和毛发使用 scene inventory。
4. 生成必需视图并人工审查。
5. 记录通过、风险、拒绝原因和适用性别/BodyFit。

### APP-03：重建兼容登记

```powershell
python "$scriptRoot\cc_build_appearance_compatibility_registry.py" `
  --catalog <reviewed-catalog.json> `
  --batch <reviewed-batch.json> `
  --validation <validation-result.json> `
  --review <visual-review.json> `
  --output <candidate-compatibility.json>
```

`--batch`、`--validation` 和 `--review` 可重复。晋级前必须确认拒绝组合没有丢失。

### APP-04：重建面部生产 Registry

```powershell
python "$scriptRoot\cc_build_facial_production_registry.py" `
  --config "$scriptRoot\cc_facial_production_registry_config.json" `
  --output <candidate-registry.json>
```

检查池数量、路径、SHA-256、性别、加载模式、顺序、色素和材质档案引用后再晋级。

## 7. 服装边界

服装不等同于面部外观池。当前只保留已验证历史 Look 作为 Pilot，尚未完成采购资产目录、层级互斥、十体型网格、动作穿模和 UE 切换。开始阶段 8 时创建 `OUTFIT_PIPELINE.md`，不得在本文件扩写成无约束随机换装。

共用验证与弹窗恢复见 [`../validation/VALIDATION_AND_RECOVERY.md`](../validation/VALIDATION_AND_RECOVERY.md)。

