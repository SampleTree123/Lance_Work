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

`run_first_batch_render_matrix.py` 及其 Profile/Sequence/MRQ 子脚本是底层实现和诊断入口，不能单独替代正式 Render Job 状态。Sequence 构建会把目标相机隔离到完整工作区；每个节点统一从 section 0 的 `0..149` 输出，并请求帧 `-1` 完成 Sequencer binding 预滚。媒体 Gate 同时要求 `evaluation_preroll`、可见运动和首帧到第二帧连续性，避免上一 Camera Cut 或动画 section 边界状态进入交付首帧。

Linux/H200 单次 Editor invocation 使用 `run_first_batch_server_render_jobs.py`；多批次入口是 `run_first_batch_server_render_batches.py`。`run_first_batch_server_production.py` 固定先做单 UE 50 节点 Gate，再按 50 节点/Editor 完成 640、审计并调用发布封装器；`run_first_batch_server_production_slurm.sh` 是当前 Slurm job body，并强制通过 `DM_PRODUCTION_RUN_ROOT` 与 `DM_DELIVERY_ROOT` 指定新的版本化输出，避免覆盖已冻结候选。`v003` 证明资源边界可支持 50，但媒体后来因动画首帧视觉缺陷失效。修复后的 6 个高风险动作/机位先在同一 UE PID 内 6/6 accepted，正式 `v004` 随后以 13 个 Editor invocation 完成 640/640 accepted，全部 exit 0，并构建完整 `dataset_v1` 候选。失败 invocation 仍按 Sidecar/SHA-256 复用 accepted 节点，不允许每个视频重启一次 UE。`h200_vulkan_sm6_580_tokyo_v1` 固定 Tokyo staging map、H200/580 Vulkan SM6 参数和 `0.0.0.0`/TTL 1 Remote Execution；完整 640 节点执行仍需 `--confirm-full-run`。Vulkan 源码补丁已固化在 `patches/ue58_vulkan_compatibility/`，准确生产二进制和命令以候选包旁的 `release_evidence/render_run/profile.json` 为准。

跨独立 Run Root 的同节点逐帧确定性由 `validate_first_batch_node_determinism.py` 验证。它要求相同 GT、媒体规格与 Editor profile，并对 150 帧 mean/p95/max MAD 和 changed-pixel fraction 执行硬 Gate。

## 安全边界

运行前确认 UE 项目、MCP/Remote Execution、恢复弹窗和未保存资产状态。运行后同时检查机器报告和视觉结果；T-pose、Skeleton、Morph、材质、服装、构图或时间运动异常均不能静默通过。

完整脚本生命周期和 owner 由 `../SCRIPT_CATALOG.json` 提供。当前批次冻结动作、Look、相机和完成度只从 Batch Status 与 Registry 获取。
