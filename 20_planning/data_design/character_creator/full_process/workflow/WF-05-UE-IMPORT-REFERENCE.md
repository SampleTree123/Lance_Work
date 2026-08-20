# WF-05 UE 完整参考导入

> 文档角色：`workflow_runbook`
> 状态：`validated_pilot`
> 适用阶段：`WF-05`
> 权威范围：在 UE 5.8 中导入并验收未经拆分的完整参考角色
> 上级入口：[`README.md`](./README.md)
> 上游：[`WF-04-CC-EXPORT-BUNDLE.md`](./WF-04-CC-EXPORT-BUNDLE.md)
> 下游：[`WF-06-UE-CHARACTER-RUNTIME.md`](./WF-06-UE-CHARACTER-RUNTIME.md)
> 最近核验：2026-08-06

## 1. 目的与使用时机

先证明 Bundle、Skeleton、Morph 和材质在 UE 中完整正确，再建立模块化角色。完整参考是后续拆分和排错基准，不可跳过。

## 2. 当前范围与非目标

当前仅 `M02_Average` 完整通过。该结果不能自动推广到其他九个 BodyFit，也不证明服装、发型和动画组合无穿模。

## 3. 进入条件

- `GATE-04 BUNDLE_READY` 通过。
- UE 打开 `D:\UE\projects\datatry_02`，不在 PIE/Simulate。
- Reallusion Auto Setup 2.03 项目插件已启用，`/Game/CC_Shaders` 存在。
- Bundle 完整，UE 目标目录为空或为明确的新版本。

## 4. 输入与输出

输入是一个版本化 CC Bundle。输出是 `/Game/Vendor/Reallusion/CC5/Characters/<BodyFit>/FullReference` 下的完整 Skeletal Mesh、Skeleton、材质、纹理、Rig Logic/Post Process 资产和导入记录。

## 5. 执行环境

首次导入使用 `UE_UI`。外部 FBX 被复制为 `.uasset`，拖入 Content Browser 不会移动源文件。

## 6. 执行步骤

1. 导入到 `/Game/Vendor/Reallusion/CC5/Characters/<BodyFit>/FullReference`；不要导入到 DataMake。
2. FBX 关键选项：

| 中文 UI | 值 |
| --- | --- |
| 骨骼网格体 | 开 |
| 导入网格体 | 开 |
| 导入内容类型 | `Geometry and Skinning Weights` |
| 骨骼 | 首次导入选 `None` |
| 保留平滑分组 | 开 |
| 导入骨骼层级中的网格体 | 开 |
| 导入变形目标 | 开 |
| 导入动画 | 关 |

3. 确认 Auto Setup 读取同名 JSON 和纹理。
4. 保存 Output Log 和所有导入警告；警告不能仅凭文字忽略。
5. 打开完整 Skeletal Mesh，检查比例、皮肤、眼睛、牙齿、毛发、接缝、Skeleton、Root、IK 和 Facial Bone。
6. 在 Morph Target 面板验证左右眨眼、Smile/Jaw Open 或代表表达。

## 7. 退出门禁

执行 [`GATE-05 UE_REFERENCE_ACCEPTED`](../validation/README.md)：`VAL-XFER-01` 与 `VIS-XFER-01` 均通过，导入路径、Skeleton、材质、警告和来源 Bundle 已记录。

## 8. 失败与恢复

Skeleton 误复用、Morph 缺失、灰材质、透明错误、比例异常或 UE 崩溃时停止。保留源 Bundle，不覆盖参考资产；按 `REC-XFER-01` 或 `REC-UE-01` 建立新版本导入。

## 9. 技术依据与下一阶段

Vendor/DataMake 与追溯规则见 [`ASSET_TRACEABILITY.md`](../cc_ue_transfer/ASSET_TRACEABILITY.md) 和 [`ADR-0007`](../decisions/ADR-0007-UE-VENDOR-DATAMAKE-MODULARITY.md)。通过后进入 [`WF-06`](./WF-06-UE-CHARACTER-RUNTIME.md)。

