# WF-50 UE 角色运行时与表演资产

> 文档 ID：`WF-50`
> 文档类型：`workflow`
> 生命周期：`current`
> 前序：`WF-40`
> 后序：`WF-60`
> Exit Gate：`GATE-50 PERFORMANCE_ACCEPTED`
> 最近核验：2026-08-25

## 1. 目的与使用时机

证明每个生产 Look 能在 UE 中正确播放身体动作、面部表情和允许的 Morph，并明确 FullReference、模块化组件、Root Motion 和道具策略。

## 2. 前后序与进入条件

- 前序：`WF-40`；后序：`WF-60`。
`GATE-40` 通过，动作与表情均有冻结 ID 和目标 Skeleton。

## 3. 输入

FullReference Look、身体动画、面部曲线/骨骼动画、Morph 配置、服装兼容限制和道具依赖。

## 4. 正常流程

| 步骤 | 操作 | 精确实现或机器入口 | 本步输出 |
| --- | --- | --- | --- |
| 1. 审计角色基线 | 验证 FullReference、同性 Skeleton、材质、Morph、Blueprint 和无 T-pose 基线 | UE Payload [`ue_validate_first_batch_day2_runtime.py`](../../../../../00_engine/scripts/unreal/ue_validate_first_batch_day2_runtime.py)；契约见 [角色运行时](../technical/unreal/CHARACTER_RUNTIME.md#2-第一批输入与-fullreference-契约) | 逐 Look 运行时检查 |
| 2. 准备身体动作 | 应用冻结窗口、Root Motion/InPlace 和 Padding 策略 | 动作导入入口见 [Motion Transfer](../technical/transfer/MOTION_TRANSFER.md)；派生入口 [`ue_build_first_batch_idle_padding.py`](../../../../../00_engine/scripts/unreal/ue_build_first_batch_idle_padding.py) 与 [`ue_build_first_batch_inplace_candidates.py`](../../../../../00_engine/scripts/unreal/ue_build_first_batch_inplace_candidates.py) | 规范 Body Motion 资产 |
| 3. 构建面部与 Composite | 建立批准表情片段，并把可替换身体动作与面部层组合 | [`ue_build_first_batch_expression_library.py`](../../../../../00_engine/scripts/unreal/ue_build_first_batch_expression_library.py)、[`ue_build_first_batch_expression_composition.py`](../../../../../00_engine/scripts/unreal/ue_build_first_batch_expression_composition.py)、[`ue_build_first_batch_action_expression_composites.py`](../../../../../00_engine/scripts/unreal/ue_build_first_batch_action_expression_composites.py) | Face Clip/Composite 资产 |
| 4. 修复受控材质异常 | 仅在审计确认动态皱纹纹理绑定错误时备份并修复 | [`ue_patch_first_batch_head_wrinkle_textures.py`](../../../../../00_engine/scripts/unreal/ue_patch_first_batch_head_wrinkle_textures.py)，默认只审计 | 可逆材质补丁报告 |
| 5. 聚合机器与视觉 Gate | 覆盖 Look × Action × Expression，检查动作、肤色、眼口、Root Motion 和五秒窗口 | 系统入口 [`run_first_batch_day2_final_gate.py`](../../../../../00_engine/scripts/unreal/run_first_batch_day2_final_gate.py)；视觉标准见 [视觉审查](../technical/validation/VISUAL_REVIEW.md) | `VAL-UE-01` 证据与接受风险 |
| 6. 条件能力 Gate | 仅在批次声明模块化组件或可编辑 Morph 时执行额外 Gate | 当前仅有 M02 模块化 Pilot；边界见 [角色运行时](../technical/unreal/CHARACTER_RUNTIME.md#3-模块化-pilot-边界) 与 [Morph 边界](../technical/unreal/ANIMATION_EXPRESSION_MORPH.md#5-morph-边界) | `VAL-UE-02/VAL-UE-03` 或 `not_applicable` |

模块化换装和运行时年龄 Morph 不是第一批依赖。Pilot 成功不能替代生产矩阵 Gate。

## 5. 输出契约

| 输出 ID | 逻辑产物 | 存储类别 | 生产所有者 |
| --- | --- | --- | --- |
| `OUT-WF50-RUNTIME-ACCEPTANCE` | 被接受的 Look/Action/Expression 组合、Root Motion 策略、兼容性警告和运行时报告 | `ue_asset` + `run_evidence` | [角色运行时](../technical/unreal/CHARACTER_RUNTIME.md) |

### 输出组成、用途与下游

| 组成 | 实际内容 | 为什么需要 | 下游消费者 |
| --- | --- | --- | --- |
| UE 表演资产 | 规范身体动作、Face Clip、Composite、必要的可逆材质补丁 | 给 Sequence 提供可直接绑定的稳定资产 | `WF-60/WF-80` |
| 接受组合矩阵 | Look × Action × Expression、Skeleton 和五秒窗口映射 | 防止渲染器选择未验证组合 | `WF-60` 与 `WF-70` 图源 |
| 运行时策略 | Root Motion/InPlace、Padding、曲线/骨骼分层和可选模块化边界 | 保证同一 ID 在不同脚本中语义一致 | Sequence、Render Job 和恢复流程 |
| 兼容警告与已接受风险 | 局部服装穿模、头发/兜帽、Morph 和 Pilot 限制 | 区分批次可接受问题与系统能力 | QA、计划和后续改进 |
| Gate 报告与视觉证据 | 机器检查、关键帧/视频和人工决定 | 证明 UE 资产存在之外的实际播放质量 | `VAL-UE-01..03` 与 `GATE-50` |

当前资产/证据位置由 [WF-50 状态](../project_management/status/workflows/WF-50.md#当前输出与证据) 指定；稳定组成与保留语义见 [输出契约目录](../technical/output/OUTPUT_CONTRACTS.md#36-out-wf50-runtime-acceptance)。

## 6. 必需验证

| 验证 ID | 角色 | 何时需要 |
| --- | --- | --- |
| `VAL-UE-01` | `required` | 每个生产动作/表情/Look 组合矩阵或运行时规则变化后 |
| `VAL-UE-02` | `conditional` | 批次使用模块化组件、Leader Pose 或运行时换装时 |
| `VAL-UE-03` | `conditional` | 批次使用 Elder/其他可编辑 Morph 时 |

定义、证据和通过条件见 [验证目录](../technical/validation/VALIDATION_CATALOG.md)。

## 7. Exit Gate

`GATE-50 PERFORMANCE_ACCEPTED` 要求生产组合没有 T-pose、错误 Skeleton、白块、静止冒充动画或未登记的严重穿模。

## 8. 技术与状态

- [角色运行时](../technical/unreal/CHARACTER_RUNTIME.md)
- [动画、表情与 Morph](../technical/unreal/ANIMATION_EXPRESSION_MORPH.md)
- [视觉验收](../technical/validation/VISUAL_REVIEW.md)
- [当前 WF-50 状态](../project_management/status/workflows/WF-50.md)

## 9. 失败与恢复

材质、动画模式和曲线问题必须先在单 Look 上复现并修复，再重验矩阵。不能通过删掉失败帧或降低表情幅度掩盖系统错误。
