# WF-06 UE 模块化角色运行时

> 文档角色：`workflow_runbook`
> 状态：`validated_pilot`
> 适用阶段：`WF-06`
> 权威范围：从完整参考建立模块网格、统一 Blueprint、Leader Pose 和 Morph 广播
> 上级入口：[`README.md`](./README.md)
> 上游：[`WF-05-UE-IMPORT-REFERENCE.md`](./WF-05-UE-IMPORT-REFERENCE.md)
> 下游：[`WF-07-ANIMATION-AND-PROPS.md`](./WF-07-ANIMATION-AND-PROPS.md)
> 最近核验：2026-08-06

## 1. 目的与使用时机

在完整参考通过后建立项目自有的模块化角色入口，使身体、服装、头发和部分面部组件能按语义槽位管理，同时保持一个 Skeleton、Leader Pose 和面部曲线传播。

## 2. 当前范围与非目标

当前实现只适用于硬编码的 `M02_Average` Pilot：20 个组件、19 个 follower、v002 Blueprint。没有十体型通用构建器；不得把下列脚本直接用于其他角色。

## 3. 进入条件

- `GATE-05 UE_REFERENCE_ACCEPTED` 通过。
- 完整参考路径和 Skeleton 与 M02 基准一致。
- UE Remote Execution 可发现唯一 `datatry_02` 节点。
- 目标版本不存在，或已明确只做验证；构建脚本不得覆盖已验证资产。

## 4. 输入与输出

输入为 FullReference 和其原始 Bundle。输出为 Vendor 下拆分模块、统一 Skeleton、材质恢复报告，以及 DataMake 下 `BP_DM_M02_ModularPilot_v002`。

## 5. 执行环境

构建脚本在 UE 内运行，外层由系统 Python Remote wrapper 提交：

```powershell
$ueRemote = "$ueScriptRoot\ue_remote_exec.py"
```

## 6. 执行步骤

仅在重建 M02 Pilot 或创建等价新版本时按顺序执行：

```powershell
python $ueRemote --project $ueProject --script "$ueScriptRoot\ue_interchange_split_pilot.py"
python $ueRemote --project $ueProject --script "$ueScriptRoot\ue_validate_split_pilot.py"
python $ueRemote --project $ueProject --script "$ueScriptRoot\ue_apply_split_pilot_materials.py"
python $ueRemote --project $ueProject --script "$ueScriptRoot\ue_build_m02_modular_pilot_blueprint.py"
python $ueRemote --project $ueProject --script "$ueScriptRoot\ue_build_m02_face_morph_broadcaster.py"
```

随后编译 Blueprint。`Body` 是唯一 Leader，另外 19 个组件设置 Leader Pose；`Body.propagate_curves_to_followers=true`。Vendor 保存导入/拆分源，DataMake 只保存自有 Blueprint 和控制入口。

已有 M02 资产不需要重复执行构建脚本，直接运行退出门禁。

## 7. 退出门禁

执行 [`GATE-06 RUNTIME_ACCEPTED`](../validation/README.md)。当前要求 `VAL-UE-01` 通过，并完成 `VIS-UE-01`：20/19 组件关系正确、13 个面部广播组件匹配、非面部隔离、材质和中性/Blink/Smile/Jaw Open 正常。

## 8. 失败与恢复

Blueprint 已存在、编译失败、Skeleton 不兼容、follower 缺 Leader、材质丢失或恢复包来源不明时停止。不要删除已验证资产；创建新版本并按 `REC-UE-01` 恢复。

## 9. 技术依据与下一阶段

组件契约、Morph 支持集合和变体边界由 [`MODULAR_CHARACTER_RUNTIME.md`](../ue_details/MODULAR_CHARACTER_RUNTIME.md) 定义。通过后进入 [`WF-07`](./WF-07-ANIMATION-AND-PROPS.md)。

