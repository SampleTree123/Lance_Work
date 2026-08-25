# BodyFit、身份与年龄

> 文档 ID：`TECH-CC-01`
> 文档类型：`technical`
> 生命周期：`current`
> 适用阶段：`WF-20/WF-30`
> 实现所有权：BodyFit Library、Face V3 Registry、Headshot Registry 和年龄策略
> 验证所有权：`VAL-MATRIX-01`（BodyFit/Identity 子项）、`VAL-CC-01`
> 输出契约：`OUT-WF20-ASSET-MATRIX`、`OUT-WF30-CC-ASSETS`
> 最近核验：2026-08-25

## 1. 能力与边界

身体、面部身份和年龄是三个独立概念。BodyFit 从哈希锁定的规范 `.ccProject` 加载；其初始脸只作为加载状态，随后由身份流程替换。不能把几条大 Morph 权重视为完整项目的唯一可逆存储。

## 2. 当前机器入口

| 文件 | 作用 | 状态 |
| --- | --- | --- |
| `cc_body_preset_library_v2.json` | 10 个成人 BodyFit、源项目、Body/Junction 指纹和验证 | `production` |
| `cc_build_body_preset_library_v2.py` | 从已接受项目生成/迁移 Library | `utility` |
| `cc_face_seed_library_v1.json` | 原始 Face Seed | `validated_reference` |
| `cc_face_recipes_v3_200.json` | Face V3 配方池 | `production` |
| `cc_generate_face_recipes_v3.py` | Face V3 确定性生成器 | `utility` |
| `cc_build_first_batch_identity_library_v1.py` | 从集成 Manifest、BodyFit 和头身决定冻结第一批 8 个 Identity | `production` |
| `cc_headshot_face_prototype_registry_v1.json` | Headshot 烘焙原型候选 | `validated_pilot`，未进入第一批生产 |
| `cc_headshot_skull_profile_library_v1.json` | 四个已选头型 Profile | `validated_pilot` |

所有路径相对于 `%CC_SCRIPT_ROOT%`。

## 3. BodyFit 规则

- 当前成人库为女性/男性各五个，包括 lean、average、athletic、heavy 和 short-average。
- 规范源是 `.ccProject`，运行时先校验字节数、SHA-256 和 Body/Junction Fingerprint。
- Body/Junction 向量用于漂移检测和审计，不替代源项目加载。
- Head Scale、Neck 和短体型修正已被烘焙或登记在 Library；生产不重新猜测滑块。
- 新增体型必须通过静态比例、身高、头身、眼口、服装和动作兼容验证。

## 4. Face V3 规则

Face V3 使用已接受 Seed 和受控局部 Morph 生成身份变化：

1. 加载主原型的完整面部支持状态。
2. 只修改允许随机化的局部 Morph。
3. 不把未知眼口支持参数批量清零。
4. 口部 Macro、牙齿/口腔和极端眼形需要成对验证。
5. 配方保存 Seed、局部权重、随机种子和版本，不保存模糊的“长得像某人”描述。

## 5. Headshot 边界

Headshot 项目需要保留烘焙身份项目、CC5 HD Facial Profile、来源照片、头型 Profile、哈希和动态检查。当前已验证从 CC3+ 项目升级和 project-seed + BodyFit 路线，但生产启用数仍为 0；第一批继续使用 Face V3。

四个头型候选为 Base、Long Deep、Low Flat、Narrow Shallow。它们是低频头骨 Profile，不应覆盖身份局部 Morph。

## 6. 年龄

- 年龄是可选变体，不要求每个身份都生成老年版本。
- 静态年龄 Morph、皮肤年龄和动态皱纹是不同通道。
- 青年皮肤可通过受控面部年龄 Morph 生成中/老年变体；本身老年皮肤不再叠加强老化层。
- 正式年龄编辑还需身体年龄、毛发、服装和动态表情共同验收；第一批不启用。

## 7. 验证与输出

当前权威输入本身属于 `authoritative`；配方生成结果和动态门禁为 `retained_evidence`；轴扫描中未入选图为 `superseded/disposable`。新身份至少检查中性、闭眼、微笑、张嘴、左右侧和重载一致性。

历史及当前 BodyFit/Face 运行输出统一归本能力解释，当前盘点根为：

```text
%OUTPUT_ROOT%/character_creator_body_preset_validation/
%OUTPUT_ROOT%/character_creator_face_recipes/
%OUTPUT_ROOT%/character_creator_face_recipes_v2_1/
%OUTPUT_ROOT%/character_creator_face_recipes_v3/
%OUTPUT_ROOT%/character_creator_face_seed_validation/
```

这些根当前只完成 owner 登记；除 Retention Policy 精确列出的路径外，不得从目录名推断可删除性。

执行器由 [CC 组装与验收](./ASSEMBLY_AND_ACCEPTANCE.md) 调用，历史实验细节保存在重构快照中，不作为生产入口。

## 8. 失败与恢复

源项目哈希、Body/Junction 指纹或身份支持状态不一致时停止该角色，不自动重算“接近”的滑块值。先恢复被锁定的源项目或为调整结果创建新 BodyFit/Identity 版本，再从干净项目重建并重复动态门禁。Headshot、年龄或实验 Morph 失败不得回写当前 Face V3/BodyFit 生产 Registry。
