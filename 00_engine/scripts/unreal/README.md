# Unreal Engine 自动化脚本

本目录保存 UE 5.8 的资产导入、动画分层、Morph、运行时审查和截图取证脚本。

## 调用约定

- `run_*.py`：在系统 Python 中运行的编排器，通过 `ue_remote_exec.py` 调用已经打开并连接的 UE Editor。
- `ue_*.py`：在 UE Python 环境中执行的具体任务，不应直接用普通 Python 启动。
- `*.json`：与脚本同版本的输入配置；修改资产路径或 UE Object Path 后必须重新门禁。

## 当前第一批入口

- `first_batch_expression_profile_20260820_v1.json`：Happy、Angry、Sad 的冻结定义；
- `ue_build_first_batch_expression_library.py`：创建表情资产；
- `ue_build_first_batch_expression_composition.py`：组合身体动画与面部表达；
- `run_first_batch_expression_review.py`：执行 6 个运行时案例并生成审查图；
- `ue_import_cc5_rlmotion_pilot.py`：CC 动作导入 Pilot；
- `ue_validate_p0_runtime_motions.py`：动作运行时门禁。

当前机器门禁已经覆盖 F02/M02 三表情，但 12 个冻结 Motion FBX、16 个 Look、正式场景和批量渲染仍待完成。执行顺序见 [`CURRENT_STATUS.md`](../../../20_planning/data_design/character_creator/full_process/CURRENT_STATUS.md)。

## 安全边界

执行前确认：

1. 当前 UE 项目是 `datatry_02`，MCP/Remote Execution 已连接；
2. 没有恢复包、导入选项或未保存资产弹窗；
3. 脚本中的绝对路径和 UE Object Path 与当前项目一致；
4. 用户未要求暂停，且 CC/UE 不在崩溃恢复状态。

脚本运行后必须检查生成报告中的 `success`、样本数量、错误数组，并完成人工视觉审查。存在资产、Skeleton、Morph、材质或构图异常时不得继续批量阶段。
