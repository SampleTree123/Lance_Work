# UE 角色运行时

> 文档 ID：`TECH-UE-01`
> 文档类型：`technical`
> 生命周期：`current`
> 适用阶段：`WF-40/WF-50`
> 实现所有权：UE 角色资产边界、Skeleton、Blueprint 和运行时能力
> 验证所有权：`VAL-UE-01`、`VAL-UE-02`
> 输出契约：`OUT-WF50-RUNTIME-ACCEPTANCE`
> 运行环境：Unreal Engine 5.8 Editor
> 最近核验：2026-08-25

## 1. 目录与所有权

```text
/Game/Vendor/Reallusion/CC5/FirstDataBatch/Looks/<LOOK_ID>  # 外部导入
/Game/DataMake/Characters/...                               # 自有 Wrapper/Blueprint
/Game/DataMake/Animations/CC5/FirstDataBatch/...            # 派生动作/表情
/Game/DataMake/Sequences/FirstBatch/...                     # 生产 Sequence
```

Vendor 资产不移动。DataMake 资产可以版本化重建，但不得覆盖仍被权威节点引用的版本。

## 2. 第一批输入与 FullReference 契约

- 32 个 Look：女性 16、男性 16；每个 Look 已烘焙身份、平均 BodyFit、服装和外观。
- 同性 Look 共享已冻结的同性 Skeleton；男女 Skeleton 不混用。
- 第一批不提供 UE 内单件服装自由替换；身份和服装编辑通过切换完整 Look 实现。
- 每个生产 Look 必须能播放同性 5 个动作和 Happy Composite。

角色资产真值由 `first_batch_required_exports_20260824_v3.json` 与 `first_batch_graph_source_20260824_v1.json` 共同冻结。

正式运行时审计入口：

| 入口 | 作用 |
| --- | --- |
| `run_first_batch_day2_final_gate.py` | 编排表情库、Composite、动态预览和角色运行时总 Gate |
| `ue_validate_first_batch_day2_runtime.py` | 在 UE 内检查 Look、Skeleton、动作、表情、材质和 T-pose |
| `ue_patch_first_batch_head_wrinkle_textures.py` | 审计/备份/修复/恢复头部动态皱纹纹理绑定；默认只审计 |

## 3. 模块化 Pilot 边界

`/Game/DataMake/Characters/M02_Average/BP_DM_M02_ModularPilot_v002` 验证了多 SkeletalMeshComponent、Leader Pose、面部 Morph 广播和身体/面部分层。它证明模块化方向可行，但只覆盖 M02 Pilot，不是第一批 32-Look 的运行时依赖。

后续通用换装必须为每个 BodyFit 导出裸体/基础体与对应服装模块，验证共同 Skeleton、Leader Pose、Morph 支持、隐藏身体面和碰撞；不得把 Pilot 状态写成正式能力。

## 4. 运行时检查

对每个生产 Look 至少检查：

1. Skeletal Mesh、Skeleton 和 Physics/Facial 支持可加载；
2. 材质槽不丢失，脸/身体接缝和肤色一致；
3. 眼睛、牙齿、睫毛、眉毛、头发、胡须可见且位置正确；
4. 动作播放时不进入 T-pose；
5. 面部曲线不与 Auto Setup Post Process 重复求值；
6. Wrapper/Sequence 引用的是当前批准 Look，而不是历史 Pilot。

## 5. 已知限制

- 烘焙服装可能在特定动作下出现局部穿模；第一批按已记录风险接受，不等同于通用兼容。
- 头发与兜帽/头部服装相交尚未建立自动禁配系统。
- 身体 Morph 在 UE 运行时变化会破坏烘焙服装适配，因此第一批不启用体型编辑。
- Headshot、年龄和可替换发型尚未进入第一批生产 Look。

## 6. 输出与恢复

构建/验证报告进入 `%OUTPUT_ROOT%/unreal_character_import/`，其中聚合 Gate 和人工决定为 `retained_evidence`，一次性舞台 Actor、临时关卡和诊断资产为 `disposable`。崩溃后先审计脏包、临时 Actor 和资产路径，再继续；不要直接保存未知自动恢复内容。

当前保留的 Day-2 运行时证据为 `%OUTPUT_ROOT%/unreal_character_import/first_batch_day2_20260822_v1/`，其策略前缀是 `unreal_character_import/first_batch_day2_20260822_v1`。
