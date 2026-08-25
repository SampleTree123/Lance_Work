# Unreal Engine 实现目录

本目录保存 UE 5.8 的资产导入、运行时验证、动画/表情组合、场景/Sequence、MRQ 与本地编排脚本。业务流程从 [UE 技术索引](../../../20_planning/data_design/character_creator/full_process/technical/unreal/README.md) 进入。

## 调用约定

- `run_*.py`：系统 Python 编排器，通常通过 `ue_remote_exec.py` 调用已打开的 UE Editor。
- `ue_*.py`：UE Python Payload，不应直接由普通 Python 启动。
- `*.json`：与实现配套的 Registry/Profile/Matrix；修改 UE Object Path 后必须重跑对应 Gate。
- `tests/`：不替代 UE 运行时和人工视觉验证。

## 技术入口

- CC Bundle 与 Motion 导入：[transfer/README.md](../../../20_planning/data_design/character_creator/full_process/technical/transfer/README.md)
- 角色 Blueprint、FullReference 与模块化 Pilot：[CHARACTER_RUNTIME.md](../../../20_planning/data_design/character_creator/full_process/technical/unreal/CHARACTER_RUNTIME.md)
- Body/Face 动画、Morph 与材质故障：[ANIMATION_EXPRESSION_MORPH.md](../../../20_planning/data_design/character_creator/full_process/technical/unreal/ANIMATION_EXPRESSION_MORPH.md)
- 场景、角色锚点、相机与 Sequence：[SCENE_CAMERA_SEQUENCE.md](../../../20_planning/data_design/character_creator/full_process/technical/unreal/SCENE_CAMERA_SEQUENCE.md)
- MRQ、本地矩阵与服务器执行：[rendering_release/README.md](../../../20_planning/data_design/character_creator/full_process/technical/rendering_release/README.md)

## 当前正式渲染入口

`run_first_batch_render_jobs.py` 是第一批数据唯一拥有正式节点状态的执行入口。它读取冻结 `render_jobs.jsonl`，生成 Run Root、输入锁、Lease、attempt、GT/Sidecar、媒体 Manifest，并按媒体 SHA-256 断点复用。准确命令、目录结构和本地验收证据见 [RENDER_EXECUTION.md](../../../20_planning/data_design/character_creator/full_process/technical/rendering_release/RENDER_EXECUTION.md)。

`run_first_batch_render_matrix.py` 及其 Profile/Sequence/MRQ 子脚本是底层实现和诊断入口，不能单独替代正式 Render Job 状态。

## 安全边界

运行前确认 UE 项目、MCP/Remote Execution、恢复弹窗和未保存资产状态。运行后同时检查机器报告和视觉结果；T-pose、Skeleton、Morph、材质、服装、构图或时间运动异常均不能静默通过。

完整脚本生命周期和 owner 由 `../SCRIPT_CATALOG.json` 提供。当前批次冻结动作、Look、相机和完成度只从 Batch Status 与 Registry 获取。
