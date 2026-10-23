# 面部纹理候选配方（2026-10-12）

> 文档 ID：`TECH-CC-FACIAL-DETAIL-RECIPE-20261012`
> 文档类型：`technical`
> 生命周期：`current`
> 实现所有权：仅记录候选配方，自动装配尚未实现
> 验证所有权：用户手动视觉试用；自动化及 UE 还原验证待实施
> 输出契约：本候选文档，不新增角色或导出资产
> 权威范围：用户手动试用后确定的 SkinGen 素材选择、图层不透明度与组合规则；不代表自动化已经实现
> 最近核验：2026-10-12（用户提供路径、图层及参数；截图与口头视觉反馈）
> 执行状态：2026-10-18已授权简化方案与40人更新；实现及代表验证进行中，以新增简化节为准。

## 2026-10-18 当前采用的简化方案

本节覆盖下文历史候选配方：不再添加Face Wrinkle、Secondary、额外Roughness、Freckle、Face Acne。2026-10-18后续用户明确将红晕直接从人物组成部分移除，因此也不加载Hemoglobin／Redness／Mature Redness；保留所选皮肤自带细节。红晕不是本轮待办、阻塞或验收条件，不使用替代效果；下文红晕路径及50/100规则仅保留为历史记录。

完整装配方向已获授权：皮肤按照片可见肤色和整套质量选取；眉毛改为Makeup，男性`D:/CharacterCreator_sucai/Reallusion Custom/Makeup/Eyebrow/Makeup & SFX/Male`、女性同目录`Trimmed`；现有睫毛和虹膜池保持。先修复接缝、睫毛及下巴，再男女代表验证，成功后40人重处理。原眉毛Smart Hair染色不可直接视为Makeup兼容。实际执行进度见[本轮计划](../../../../../../00_engine/outputs/character_refresh_20261018_v1/PLAN.md)，不能把授权写成已实现。

以下为2026-10-12历史方案及资产路径，不再按其全套图层执行。

## 1. 范围与证据边界

用户已在女性换皮实验项目中手动试用这些效果。本文记录最后明确的选择，覆盖此前“所有基础层都是100”“Hemoglobin暂用80”等试调建议。男性预设的图层和强度由用户明确给定，尚不等于本会话已实跑男性自动装配。

本配方不改变照片生成的面部形状、Average 身体与固定头皮策略，不替代现有正式角色创建流程。未实现这套 SkinGen 图层的自动装配，也未完成这套手动效果的 UE 还原验证。不得据本文批量修改40人。

数值均指 SkinGen **图层顶部 Opacity（0–100）**，不是图层内 Normal Strength、Roughness 或颜色参数。图层名按用户提供记录；真实接口可能使用空格或不同大小写，实施时读取并核对，不能仅凭模糊匹配修改已有同名层。

## 2. 固定基础纹理

每个角色都加载对应性别的以下两个预设。基础层不随后面的轻/强档改变。

| 预设 | 性别 | 生成图层与 Opacity |
| --- | --- | --- |
| Face Wrinkle F | female | `wrinkle_fine` / 界面 Wrinkle Fine：100 |
| Face Wrinkle M | male | `wrinkle_fine`：30；`wrinkle_broad`：100 |
| 1Secondary Normal F | female | `secondary` / 界面 Secondary：100 |
| 1Secondary Normal M | male | `secondary`：100 |

精确路径：

```text
female wrinkle:
D:\CharacterCreator_sucai\Reallusion Templates\Skin\Normal Effects\1_Facial Wrinkle\Face Wrinkle F.ccSkinGenPreset
male wrinkle:
D:\CharacterCreator_sucai\Reallusion Templates\Skin\Normal Effects\1_Facial Wrinkle\Face Wrinkle M.ccSkinGenPreset
female secondary:
D:\CharacterCreator_sucai\Reallusion Templates\Skin\Normal Effects\4_Levels\1_Face\1Secondary Normal F.ccSkinGenPreset
male secondary:
D:\CharacterCreator_sucai\Reallusion Templates\Skin\Normal Effects\4_Levels\1_Face\1Secondary Normal M.ccSkinGenPreset
```

**不添加额外 Roughness 图层**。这不意味着删除基础皮肤的粗糙度贴图或禁用其反光表现。

## 3. 红晕三选一

选择一种红晕类型，然后按角色性别加载对应预设；三种不叠加。

| 类型 | 对应层 | 强度 |
| --- | --- | --- |
| Hemoglobin | `Hemoglobin` | 轻档50，强档100 |
| 普通 Redness | `upper face`、`mid face`、`lower face` | 三层同时50或同时100 |
| Mature Redness | `upper face`、`mid face`、`lower face` | 三层同时50或同时100 |

精确路径：

```text
female hemoglobin:
D:\CharacterCreator_sucai\Reallusion Templates\Skin\Skin Details\3_Coloration\Hemoglobin F.ccSkinGenPreset
male hemoglobin:
D:\CharacterCreator_sucai\Reallusion Templates\Skin\Skin Details\3_Coloration\Hemoglobin M.ccSkinGenPreset
female redness:
D:\CharacterCreator_sucai\Reallusion Templates\Skin\Skin Details\3_Coloration\Redness\Female.ccSkinGenPreset
male redness:
D:\CharacterCreator_sucai\Reallusion Templates\Skin\Skin Details\3_Coloration\Redness\Male.ccSkinGenPreset
female mature redness:
D:\CharacterCreator_sucai\Reallusion Templates\Skin\Skin Details\3_Coloration\Redness\Mature Female.ccSkinGenPreset
male mature redness:
D:\CharacterCreator_sucai\Reallusion Templates\Skin\Skin Details\3_Coloration\Redness\Mature Male.ccSkinGenPreset
```

类型名称表示预设选择，不根据 Mature 名称擅自修改角色年龄或几何。不同预设的100不代表相同视觉强度。

## 4. 雀斑与痘痘二选一

男女使用相同资产；不添加“都不选”作为默认第三项（该建议未被用户采用）。

| 选择 | 图层 | 强度 |
| --- | --- | --- |
| Freckle 01 | `Freckle` | 轻档50，强档100 |
| Face Acne Few | `Face Acne` | 轻档50，强档100 |

```text
D:\CharacterCreator_sucai\Reallusion Templates\Skin\Blemish\1_Freckle\Freckle 01.ccSkinGenPreset
D:\CharacterCreator_sucai\Reallusion Templates\Skin\Blemish\3_Acne\Face Acne Few.ccSkinGenPreset
```

未选中的雀斑/痘痘不加载；若试验项目已存在该层，按用户约定设置 Opacity=0，使其不贡献效果。不允许在已有图层上反复追加预设造成隐性重复。

## 5. 两档联动与组合

每个角色选择一个档位，该档位同时作用于选中的红晕全部图层和选中的雀斑/痘痘图层：

- 轻档：全部50。
- 强档：全部100。
- 固定基础纹理按第2节独立赋值，尤其男性 Wrinkle Fine 始终30。

每个性别共有 `3种红晕 × 2种局部特征 × 2档 = 12种组合`。随机种子、抽样比例、与皮肤库的搭配策略尚未确定，不擅自假定均匀抽样或与族群绑定。后续记录角色的实际预设路径、图层、档位，保留可复现性即可，不新增繁琐的逐角色验收。

## 6. 手动预览时的附加设置

用户在当前女性样本确认的候选参数：

- Micro Normal Tiling：20。
- Micro Normal Strength：0.7。
- Keep Original Roughness：勾选；用户取消勾选后认为过亮。
- SkinGen Head 编辑面板截图显示 Texture=4096×4096。

这些是当前女性样本的手动设置，尚未明确推广为所有男女角色的固定参数；不可与已经明确全员使用的基础图层规则混淆。Hemoglobin Opacity80属于较早试调，最终组合规则已改为50/100。

## 7. 保存与后续恢复边界

用户选择直接修改的项目：

```text
D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts\skin_detail_optimization_20261012_v1\CFD40_AF_005\C_skin_v3\independent_C_skin_only.ccProject
```

该路径现在是用户手动试验工作文件。原实验报告中的哈希描述当时版本，不能继续视为该路径当前字节的证明；不得用旧哈希不匹配自动覆盖/恢复用户修改。实际保存内容、全部当前图层、是否加了头发，本次未通过CC接口重新读取。

此前网页8893的C仍是旧的标准贴图＋部分参数迁移版本，**不包含今天这些手动新增纹理**。旧网页不是当前CC项目的完整同条件还原；用户明确要求先解决这一显示差异，再考虑实施本配方。

后续如获授权恢复：沿用已有CC/UE实现，先确认最终细分等级及法线烘焙，再导入一个代表例子。不只凭导出成功或当前CC截图就认定UE细节一致。官方说明CC5 HD的SkinGen法线细节需要向目标低细分层烘焙，具体针对本项目的操作仍待核对：[官方说明](https://manual.reallusion.com/Character-Creator-5/Content/ENU/5.0/05-HD-Character/Baking-Skin-Gen-Normal-to-Lower-Level-Model.htm)。

本次仅保存配方，不启动CC/UE操作、脚本实现、纹理烘焙、角色导出或自动批量任务。
