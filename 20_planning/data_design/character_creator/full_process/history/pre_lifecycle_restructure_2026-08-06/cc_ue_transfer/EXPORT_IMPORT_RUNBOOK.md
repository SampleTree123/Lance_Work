# CC5 到 Unreal Engine 5.8 导出与导入 Runbook

> 文档角色：`operational_runbook`
> 状态：`validated_pilot`
> 已验证对象：`M02_Average`
> 上级入口：[`../CHARACTER_FACTORY_MASTER_SPEC.md`](../CHARACTER_FACTORY_MASTER_SPEC.md)
> 最近核验：2026-08-06

## 1. 当前基准

```text
CC_EXPORT_ROOT = D:\UE\exports\character_creator
UE_PROJECT_ROOT = D:\UE\projects\datatry_02
Pilot bundle = %CC_EXPORT_ROOT%\pilot_m02_ue58_v001
```

Bundle：

```text
CC_M02_Average_Pilot_UE58.Fbx
CC_M02_Average_Pilot_UE58.json
CC_M02_Average_Pilot_UE58.fbm\
textures\
```

UE 项目使用 Reallusion Auto Setup (All-in-One) 2.03，项目级插件目录为 `Plugins/RLPlugin`，材质内容位于 `/Game/CC_Shaders`。

## 2. TRANSFER-01：导出前门禁

- 模式：`CC_UI`
- 状态：`manual_verified`

1. 打开已经通过完整 CC 门禁并保存的规范化 `.ccProject`。
2. 确认没有用于检查的临时姿势、摄像机动作或表情残留。
3. 确认最终皮肤、眼球和面部材质质量档案已经应用并回读。
4. 记录 `bodyfit_id`、`face_recipe_id`、年龄、外观资产 ID、源项目 SHA-256 和导出版本。
5. 新建版本化 bundle 目录；禁止覆盖旧导出。

## 3. TRANSFER-02：CC FBX 导出设置

- 模式：`CC_UI`
- 目标：Unreal Engine / UE5 Skeleton。

已验证的关键设置：

| 组 | 选项 | 值 |
| --- | --- | --- |
| General | Axis | `Z` |
| General | Auto Skin Rigid Mesh | 开 |
| General | Rename Duplicate Bone Name | 开 |
| General | Reset Self Illumination | 开 |
| General | Bone Name lower-case | 开 |
| General | Export JSON for Auto Material Setup | 开 |
| General | Reset Bone Scale | 开 |
| Character | Epic Skeleton | 开 |
| Character | UE5 Skeleton | 选中 |
| Character | Epic Skeleton Hand and Foot IK | 开 |
| Character | Mouth Open as Morph | 关 |
| Character | Convert Skinned Expressions to Morphs | 关 |
| Character | Use T-Pose As Bind Pose | 关 |

本机 CC5 界面没有显示某些旧教程选项时，不推测补选。以 FBX、同名 JSON 和纹理实际生成作为第一层通过条件。

角色目前按完整导出生成一个 Skeletal Mesh；CC 导出窗口没有“自动按服装/头发拆成独立网格”的开关。模块化拆分在 UE Pilot 中完成。

## 4. TRANSFER-03：Bundle 检查

至少检查：

```powershell
$bundle = 'D:\UE\exports\character_creator\pilot_m02_ue58_v001'
Get-Item "$bundle\CC_M02_Average_Pilot_UE58.Fbx"
Get-Item "$bundle\CC_M02_Average_Pilot_UE58.json"
Get-ChildItem "$bundle\textures" -File
```

保存 FBX/JSON/关键纹理哈希，并把它们写入导出 manifest。JSON 与 FBX 基名必须一致。

## 5. TRANSFER-04：UE 导入目标

- 模式：`UE_UI`
- Vendor 目标：

```text
/Game/Vendor/Reallusion/CC5/Characters/M02_Average/FullReference
```

外部导入资产保持原路径；不要移动到 DataMake。DataMake 只保存自有 Blueprint、派生动画和配置。

## 6. TRANSFER-05：FBX 导入选项

关键设置：

| 中文 UI | 值 |
| --- | --- |
| 骨骼网格体 | 开 |
| 导入网格体 | 开 |
| 导入内容类型 | `Geometry and Skinning Weights` |
| 骨骼 | 首次导入选 `None`，创建新 Skeleton |
| 保留平滑分组 | 开 |
| 导入骨骼层级中的网格体 | 开 |
| 导入变形目标 | 开 |
| 导入动画 | 角色基准导入时关；动画单独导入 |

法线和切线选项以 pilot 已验证结果为基准；如果修改，必须重新比较皮肤、毛发高光和接缝。导入警告不能只凭弹窗文字忽略，应保存 Output Log 并做视觉/结构检查。

Auto Setup 会读取同名 JSON 和纹理构建 Reallusion 材质。若只拖入 FBX，源文件不会从导出目录移动；UE 会在 Content 下创建自己的 `.uasset`。

## 7. TRANSFER-06：导入后检查

1. 打开完整 Skeletal Mesh。
2. 验证身体比例、头身、皮肤、眼睛、牙齿、毛发和材质接缝。
3. 在 Morph Target 面板验证左右眨眼和代表表情。
4. 验证 Skeleton、Root、IK 和 Facial Bone 存在。
5. 验证 Auto Setup 的材质和 Post Process/Rig Logic 资产。
6. 记录导入对象路径、Skeleton 和警告。
7. 通过后才能建立 DataMake 派生模块。

M02 已验证左右眨眼、表情、全身比例和皮肤材质。该结论不能自动推广到其他九个 BodyFit。

## 8. 动画导入边界

CC `.rlMotion` 不是 UE 可直接读取格式。动画需在 CC 中应用到兼容角色并导出 FBX，再在 UE 中指定现有 M02 Skeleton 导入。身体动画和面部动画的清理、分层规则见 [`../ue_details/ANIMATION_AND_MORPH_PIPELINE.md`](../ue_details/ANIMATION_AND_MORPH_PIPELINE.md)。

## 9. 停止条件

- 同名 JSON 缺失或与 FBX 不匹配。
- Auto Setup 插件未启用或 Shader 内容缺失。
- Skeleton 意外复用错误角色。
- Morph Targets 缺失。
- 皮肤、眼睛或头身比例明显错误。
- UE 崩溃、资产恢复状态不清或 MCP 离线但步骤依赖 MCP。

发生失败时保留 bundle，不在原目录重复导出；建立新版本并在 Traceability 中记录替代关系。

