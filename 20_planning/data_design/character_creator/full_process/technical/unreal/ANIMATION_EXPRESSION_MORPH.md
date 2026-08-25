# 动作、表情与 Morph

> 文档 ID：`TECH-UE-02`
> 文档类型：`technical`
> 生命周期：`current`
> 适用阶段：`WF-50/WF-60`
> 实现所有权：动作窗口、身体/面部组合、Root Motion、表情曲线和 Morph
> 验证所有权：`VAL-UE-01`、`VAL-UE-03`
> 输出契约：`OUT-WF50-RUNTIME-ACCEPTANCE`
> 运行环境：UE Editor Python、Animation Blueprint、AnimSequence
> 最近核验：2026-08-25

## 1. 通道模型

身体动作与面部表现可独立选择，但组合前必须分类：`none`、`curves`、`bones` 或 `hybrid`。只有 `reuse_policy=replaceable` 的身体动作才能与批准 Face Clip/Composite 重组；`paired/locked` 保留原始表演。

颈部和头部属于身体表演，不应被“纯面部”层覆盖。面部层只接管批准的 facial bone subtree/曲线；眼骨、Rig Logic 和直接 Morph 不得同时竞争同一输出。

## 2. 第一批生产输入与策略

- 每个性别 5 个动作，固定 5 秒、30 FPS、150 帧。
- `ACT_F02_CATCH_BREATH` 使用 `A_DM_F02_CATCH_BREATH_InPlaceCandidate_v001`。
- 其余动作保留源 Root Motion；短动作按 Registry 的 padding 策略补齐。
- 正式节点固定 `expression_id=happy`，表情不是第一批编辑轴。
- 每个动作使用其 `*_Happy_Composite_v001`，而不是临时预览动画。

精确路径、窗口和策略只从 `first_batch_graph_source_20260824_v1.json` 读取。

## 3. 构建与验证入口

核心实现：

- `ue_build_first_batch_idle_padding.py` / `run_first_batch_idle_padding.py`
- `ue_build_first_batch_inplace_candidates.py`
- `ue_build_first_batch_action_expression_composites.py`
- `ue_build_first_batch_expression_library.py`
- `ue_build_first_batch_expression_composition.py`
- `run_first_batch_action_expression_composites.py`
- `run_first_batch_all_action_expression_composites.py`
- `ue_validate_first_batch_day2_runtime.py`

构建顺序为：导入 Body Motion → 应用窗口/InPlace/Padding → 建立表情片段 → 生成 Composite → 在同性生产 Skeleton 上验证 → 登记到图源。

## 4. 面部白块故障

已诊断的白块并非光照问题，而是表情曲线作用于错误/重复材质或 Post Process 求值路径。典型现象是中性帧正常，微笑幅度增大时额头和脸颊逐渐变白。

恢复原则：

1. 用已知正常的 `A_DM_M02_Face_SubtleSmile_Loop_v001` 和历史正确视频做对照；
2. 在角色 Blueprint 直接播放身体动作，确认材质本身正常；
3. 枚举异常 Face/Composite 的曲线，排除非几何材质参数曲线；
4. 使用已批准的直接 Morph/Composite 契约，避免 Auto Setup Post Process 与相同 CTRL 曲线重复求值；
5. 验证中性、微笑峰值和回落帧，再批量替换。

不得通过改变灯光或降低表情幅度掩盖该故障。

## 5. Morph 边界

`Full_Face_Elder` Pilot 证明同身份、同拓扑差值 Morph 可在 UE 组合 Blink/Smile/Jaw Open；它不能跨身份或跨 BodyFit复用。运行时身体 Morph 会要求服装和毛发拥有同拓扑支持，因此第一批不启用身体和年龄编辑。

## 6. Gate

每个动作/表情组合至少检查：无 T-pose、时间上有运动、头颈未冻结、眼睑/眼球/牙齿/嘴唇无明显穿模、肤色稳定、Root Motion 符合策略、五秒窗口准确。机器曲线检查与视觉检查必须同时通过。
