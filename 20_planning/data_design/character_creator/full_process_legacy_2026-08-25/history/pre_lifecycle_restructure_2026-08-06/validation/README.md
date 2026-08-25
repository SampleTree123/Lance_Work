# 验证与恢复文档

> 文档角色：`subsystem_index`
> 上级入口：[`../CHARACTER_FACTORY_MASTER_SPEC.md`](../CHARACTER_FACTORY_MASTER_SPEC.md)
> 最近核验：2026-08-06

## 1. 当前文档

| 文档 | 状态 | 职责 |
| --- | --- | --- |
| [`VALIDATION_AND_RECOVERY.md`](./VALIDATION_AND_RECOVERY.md) | `current` | CC、Bridge、CC→UE、UE 的可执行验证入口、输入输出、通过条件、停止条件和恢复树 |

## 2. 如何阅读下面的矩阵

“现有执行入口”只列当前仓库中真实存在并已核对调用方式的代码或人工步骤：

- `SYSTEM_PYTHON`：可在 PowerShell 中直接运行。
- `BRIDGE_CLI`：系统 Python 只提交受控请求；实际 `RLPy` 代码由 CC Bridge 加载。
- `UE_REMOTE`：系统 Python 通过 UE Python Remote Execution 把脚本送入已运行的编辑器；不等同于 Unreal MCP。
- `UE_UI`：当前只有经验证的人工操作，没有通用自动化执行器。
- `PLANNED`：尚无实现代码；文件名只表示未来开始实施后的落点。

代码存在不等于能力已经达到 `production`。状态仍由自动报告、人工视觉审查和当前扩展范围共同决定。

## 3. 当前能力与真实入口

| 能力 | 状态 | 现有执行入口 | 当前输出或限制 |
| --- | --- | --- | --- |
| Bridge heartbeat、lease、`ping` 与场景访问 | `validated_pilot` | `BRIDGE_CLI`：[`BRIDGE_OPERATIONS.md` 第 3 节](../bridge_details/BRIDGE_OPERATIONS.md#3-bridge-02健康检查)，代码为 [`cc_bridge_client.py`](../../../../../00_engine/character_creator_bridge/cc_bridge_client.py) | `health` JSON、Bridge result；必须由已启动 CC worker 消费 |
| Bridge 精确 Undo 警告守卫 | `validated_pilot` | `BRIDGE_CLI`：[`BRIDGE_OPERATIONS.md` 第 7 节](../bridge_details/BRIDGE_OPERATIONS.md#7-undo-警告守卫)，代码为 [`cc_undo_dialog_guard.ps1`](../../../../../00_engine/character_creator_bridge/cc_undo_dialog_guard.ps1) | 只匹配已知 Undo 文本；不处理 Replace/Material 或未知弹窗 |
| CC BodyFit 重建与结构门禁 | `validated_pilot` | `BRIDGE_CLI`：[`VALIDATION_AND_RECOVERY.md` 的 `VAL-CC-01`](./VALIDATION_AND_RECOVERY.md#val-cc-01-bodyfit-reconstruction-smoke)；内部执行器 [`cc_validate_body_reconstruction.py`](../../../../../00_engine/scripts/character_creator/cc_validate_body_reconstruction.py) | 每个 preset 的 `result.json`、批次 `validation_result.json` 和截图 |
| CC 完整角色静态、动态、Morph 隔离 QA | `validated_pilot` | `BRIDGE_CLI + SYSTEM_PYTHON`：[`VALIDATION_AND_RECOVERY.md` 的 `VAL-CC-02`](./VALIDATION_AND_RECOVERY.md#val-cc-02-complete-character-validation-and-contact-sheets) | 只对兼容 manifest 和已登记资产有效；仍需人工逐图判定 |
| CC→UE 单个 M02 完整参考导入 | `validated_pilot` | `CC_UI + UE_UI`：[`EXPORT_IMPORT_RUNBOOK.md`](../cc_ue_transfer/EXPORT_IMPORT_RUNBOOK.md) | 当前没有通用无人值守导入验收器；先验证完整参考再拆分 |
| M02 v002 面部 Morph 广播 | `validated_pilot` | `UE_REMOTE`：[`VALIDATION_AND_RECOVERY.md` 的 `VAL-UE-01`](./VALIDATION_AND_RECOVERY.md#val-ue-01-m02-v002-face-morph-broadcaster)；代码为 [`ue_validate_m02_face_morph_broadcaster.py`](../../../../../00_engine/scripts/unreal/ue_validate_m02_face_morph_broadcaster.py) | 验证 20 个组件、13 个面部广播组件和非面部隔离 |
| M02 v003 身体/面部混合动画矩阵 | `validated_pilot` | `SYSTEM_PYTHON + UE_REMOTE`：[`VAL-UE-02`](./VALIDATION_AND_RECOVERY.md#val-ue-02-m02-v003-hybrid-face-matrix)，外层入口 [`run_m02_face_hybrid_pie_review_v003.py`](../../../../../00_engine/scripts/unreal/run_m02_face_hybrid_pie_review_v003.py) | `2 body × 5 face state = 10`；输出 `pie_review.json` 与 10 张截图 |
| M02 Elder Morph 与表情共存 | `validated_pilot` | `SYSTEM_PYTHON + UE_REMOTE`：[`VAL-UE-03`](./VALIDATION_AND_RECOVERY.md#val-ue-03-m02-elder-morph-matrix)，外层入口 [`run_m02_elder_morph_pie_review.py`](../../../../../00_engine/scripts/unreal/run_m02_elder_morph_pie_review.py) | 6 案例；只适用于 M02 同身份、同拓扑快照 |
| M02 v002 模块结构间接覆盖 | `validated_pilot` | v003 矩阵会检查 20 组件、19 follower 和 Leader Pose；旧 [`ue_validate_m02_modular_blueprint.py`](../../../../../00_engine/scripts/unreal/ue_validate_m02_modular_blueprint.py) 仍硬编码 v001 | 覆盖仅来自组合矩阵；尚无独立、参数化的 v002 结构验证器，不得把旧脚本当作当前直接证据 |

## 4. 已预留但尚无代码的验收能力

| 能力 | 状态 | 当前可执行入口 | 开始实施后的文档位置 |
| --- | --- | --- | --- |
| 十体型 UE 导入回归 | `planned` | 无 | `UE_TEN_BODYFIT_ACCEPTANCE.md` |
| M02 v002 独立模块结构回归 | `planned` | 无；现有 v003 矩阵只提供间接覆盖 | 参数化并替代 `ue_validate_m02_modular_blueprint.py` 的 v001 硬编码 |
| 服装动作穿模矩阵 | `planned` | 无 | `OUTFIT_MOTION_ACCEPTANCE.md` |
| 发型/胡须动态门禁 | `planned` | 无 | `HAIR_ACCEPTANCE.md` |
| 场景、角色、相机碰撞与遮挡 | `planned` | 无 | `SCENE_CAMERA_ACCEPTANCE.md` |
| 视频、GT、sidecar 一致性 | `planned` | 无 | `DATASET_ACCEPTANCE.md` |
| 性能、显存、内存和批量时长回归 | `planned` | 无 | `PERFORMANCE_ACCEPTANCE.md` |

这些文件只在对应阶段真正开始时创建；当前表格不是实现承诺。

## 5. 证据边界

验证证据继续保存在 `D:\UE\Lance_Work\00_engine\outputs`，不复制到文档目录。文档记录复现入口、通过标准和稳定结论；一次运行是否成功必须回到该次报告和截图判断。
