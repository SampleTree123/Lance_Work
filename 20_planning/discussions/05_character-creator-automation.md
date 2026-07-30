# 话题 05：Character Creator 自动化与角色变体策略

> 关联正式文档：[`../data_design/character_creator/README.md`](../data_design/character_creator/README.md)  
> 状态：已形成第一版方案，等待 CC 插件原型验证  
> 日期：2026-07-18

## 背景问题

项目希望使用 Character Creator 作为批量角色创作器，通过脚本控制角色体型、头脸、服装、头发、皮肤等变化，并导出到 Unreal Engine 用于合成视频渲染。

关键疑问包括：

- CC 是否可以由 Python 脚本控制。
- agent 是否应该直接生成 Python 指令。
- 体型、头部、服装、头发如何避免组合爆炸。
- 哪些变化应该在 CC 中 baked，哪些可以在 UE 中 runtime 替换。
- 如何构造 same identity 的编辑 pair。

## 已确认的技术方向

不让 agent 直接生成任意 Python 代码，而是生成结构化配置：

```text
Agent -> character_spec.json
CC 插件 -> 固定 RLPy 逻辑读取配置并执行
CC 插件 -> 导出 FBX / JSON / textures / log
Agent -> 检查 result.json 和导出文件
```

CC 插件还需要先扫描能力表：

```text
cc_capabilities.json
  -> 可用 morph slider
  -> 可用 hair / clothing / skin / eye assets
  -> 当前角色材质槽
  -> 可用导出设置
```

## 本机 CC5 发现

已在本机看到 `D:\CharacterCreator\Character Creator 5\Bin64\RLPy.py` 暴露了多项可用接口：

```text
RFileIO.LoadFile
RFileIO.LoadObject
RFileIO.LoadClotheFromFbx
RFileIO.ExportFbxFile
RIAvatar.GetAvatarShapingComponent
RIAvatar.GetClothes
RIAvatar.GetHairs
RIMaterialComponent.LoadImageToTexture
RApplication.GetContentFilesInFolder
```

这说明 CC 自动化技术上可行，但需要实际插件验证。

## ActorMIXER 结论

用户现有的 `.ccMixerPreset` 文件是 Reallusion 二进制资产，文件头为 `_RLZeus`，不应直接解析。

正确策略：

```text
用 RFileIO.LoadFile 加载 .ccMixerPreset
-> 让 CC 应用 preset
-> 扫描当前角色 morph weights
-> 保存为 body_vector.json
-> 后续用 SetShapingMorphWeight 复现或混合
```

这可以把 ActorMIXER preset 转换为可组合的体型向量，但混合必须限制范围，避免极端形变和穿模。

## 角色库策略

不要让每个 identity 都导出所有体型和所有头型。采用两层角色池：

```text
Base Pool
  大量普通角色
  每个角色只导出一个稳定版本

Edit Anchor Pool
  少量锚点角色
  每个锚点角色导出若干受控变体
  用于 pair / edit / counterfactual 数据
```

这个策略同样适用于体型、头部外轮廓、脸型结构、眼睛形状、年龄结构、复杂皮肤、复杂妆容、服装适配和头发适配。

## BodyFit / HeadFit 结论

体型使用固定预设，避免连续随机：

```text
M_Slim
M_Average
M_Muscular
M_Heavy
F_Slim
F_Average
F_Athletic
F_Heavy
```

头部适配先按 4 个 `HeadFit` 管理。头颅外轮廓变化小，五官、肤色、年龄感、妆容和发型变化承担主要面部多样性。

身体适配资产和头部适配资产分开管理：

```text
BodyFit -> 服装 / 鞋 / 手套
HeadFit -> 头发 / 帽子 / 强贴合头部资产
```

但第一阶段最终仍推荐在 CC 中组装完整角色，再导出完整 FBX 到 UE。

## UE 侧编辑 pair

UE 中适合做低成本 pair：

- 服装颜色。
- 眼睛颜色。
- 皮肤色调。
- 妆容、雀斑、疤痕、纹身。
- 发色。
- 同一 BodyFit 下服装款式替换。
- 同一 HeadFit 下头发/帽子替换。
- 动作、姿态、相机、光照。

不建议 UE 临时大改：

- 大幅体型。
- 头骨/脸型。
- 眼睛形状。
- 未导出 morph target 的眼睛大小。

体型编辑 pair 使用整角色替换，但保持 identity、脸、头发、服装风格、动作、相机尽量一致。

## 待验证

- `RFileIO.LoadFile` 是否能稳定应用 `.ccMixerPreset` 到当前 avatar。
- 应用 preset 后，morph weight 是否能完整扫描并复现。
- CC 导出的 Unreal preset FBX 是否满足 UE 中材质、骨骼、动画和渲染需求。
- Reallusion 与第三方 CC 内容的训练/AI 使用权利。

详细执行方案见正式文档：[`../data_design/character_creator/README.md`](../data_design/character_creator/README.md)。
