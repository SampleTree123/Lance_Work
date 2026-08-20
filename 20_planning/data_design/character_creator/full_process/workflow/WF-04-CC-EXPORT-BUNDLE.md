# WF-04 CC 导出 Bundle

> 文档角色：`workflow_runbook`
> 状态：`validated_pilot`
> 适用阶段：`WF-04`
> 权威范围：从规范 `.ccProject` 生成版本化 Unreal FBX/JSON/纹理 Bundle
> 上级入口：[`README.md`](./README.md)
> 上游：[`WF-03-CC-ACCEPTANCE.md`](./WF-03-CC-ACCEPTANCE.md)
> 下游：[`WF-05-UE-IMPORT-REFERENCE.md`](./WF-05-UE-IMPORT-REFERENCE.md)
> 最近核验：2026-08-06

## 1. 目的与使用时机

只对通过 CC 验收的规范项目执行，生成可独立追溯、不可覆盖的 UE 导入 Bundle。本阶段仍在 CC 中，不操作 UE Content。

## 2. 当前范围与非目标

已完整验证对象为 `M02_Average`。CC 导出得到完整 Skeletal Mesh，不会自动按服装和头发拆分；模块拆分属于 `WF-06`。

## 3. 进入条件

- `GATE-03 CC_ACCEPTED` 通过。
- 项目处于中性姿态，无审核用临时动画、摄像机或表情。
- 最终材质质量档案已应用并回读。
- 新建版本化目录，禁止覆盖已有 Bundle。

## 4. 输入与输出

输入是规范 `.ccProject`、角色 Manifest 和验收记录。输出至少包含同基名 `.Fbx`、`.json`、`.fbm/`、`textures/` 和导出追溯信息。

当前基准：

```text
CC_EXPORT_ROOT = D:\UE\exports\character_creator
Pilot bundle = D:\UE\exports\character_creator\pilot_m02_ue58_v001
```

## 5. 执行环境

使用 `CC_UI` 的 Unreal FBX 导出界面。导出前记录 `character_id`、BodyFit、face recipe、年龄、外观 ID、源项目哈希和目标版本。

## 6. 执行步骤

1. 选择 Unreal Engine、UE5 Skeleton。
2. 使用以下已验证设置：

| 选项 | 值 |
| --- | --- |
| Axis | `Z` |
| Auto Skin Rigid Mesh | 开 |
| Rename Duplicate Bone Name | 开 |
| Reset Self Illumination | 开 |
| Bone Name lower-case | 开 |
| Export JSON for Auto Material Setup | 开 |
| Reset Bone Scale | 开 |
| Epic Skeleton / UE5 Skeleton | 开 / 选中 |
| Epic Skeleton Hand and Foot IK | 开 |
| Mouth Open as Morph | 关 |
| Convert Skinned Expressions to Morphs | 关 |
| Use T-Pose As Bind Pose | 关 |

3. 本机界面缺少旧教程选项时不推测补选，以实际 FBX、同名 JSON 和纹理为准。
4. 导出完成后执行 `VAL-BUNDLE-01`；保存 FBX、JSON 和关键纹理哈希。

## 7. 退出门禁

[`GATE-04 BUNDLE_READY`](../validation/README.md) 要求 `VAL-BUNDLE-01` 通过：FBX/JSON 同基名且来自本次导出，纹理存在，源项目与 Manifest 可追溯，目标版本和 Auto Setup 版本已记录。

## 8. 失败与恢复

缺 JSON、纹理不完整、导出中断或版本路径错误时保留失败目录并新建版本重导，不在原目录补拼文件。按 `REC-XFER-01` 处理。

## 9. 技术依据与下一阶段

追溯 schema 见 [`ASSET_TRACEABILITY.md`](../cc_ue_transfer/ASSET_TRACEABILITY.md)，外部目录职责见 [`EXTERNAL_DIRECTORIES.md`](../reference/EXTERNAL_DIRECTORIES.md)。通过后关闭或保留 CC 由资源情况决定，并进入 [`WF-05`](./WF-05-UE-IMPORT-REFERENCE.md)。

