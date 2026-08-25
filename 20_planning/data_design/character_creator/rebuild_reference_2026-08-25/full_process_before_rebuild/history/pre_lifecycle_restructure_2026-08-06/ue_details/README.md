# Unreal Engine 子系统文档

> 文档角色：`subsystem_index`
> 上级入口：[`../CHARACTER_FACTORY_MASTER_SPEC.md`](../CHARACTER_FACTORY_MASTER_SPEC.md)
> 当前工程：`D:\UE\projects\datatry_02`
> 最近核验：2026-08-06

本目录只描述 Unreal Engine 内的角色资产、运行时控制和后续渲染能力。外部资产原包保留在 `/Game/Vendor`，项目自有入口、派生动画和配置放在 `/Game/DataMake`。

## 当前文档

| 文档 | 状态 | 职责 |
| --- | --- | --- |
| [`MODULAR_CHARACTER_RUNTIME.md`](./MODULAR_CHARACTER_RUNTIME.md) | `validated_pilot` | M02 的 20 组件模块化角色、Leader Pose、Morph 广播和变体边界 |
| [`ANIMATION_AND_MORPH_PIPELINE.md`](./ANIMATION_AND_MORPH_PIPELINE.md) | `validated_pilot` | 身体/面部动画分层、通道登记和 Elder Morph Pilot |

## 能力矩阵与未来扩展

| 能力 | 状态 | 当前技术/验证入口 | 尚未实现时的文档落点 |
| --- | --- | --- | --- |
| M02 模块化角色 | `validated_pilot` | [`MODULAR_CHARACTER_RUNTIME.md`](./MODULAR_CHARACTER_RUNTIME.md)；[`VAL-UE-01`](../validation/VALIDATION_AND_RECOVERY.md#val-ue-01-m02-v002-face-morph-broadcaster) | 独立 v002 结构验证器仍待参数化 |
| M02 身体动作与面部片段重组 | `validated_pilot` | [`ANIMATION_AND_MORPH_PIPELINE.md`](./ANIMATION_AND_MORPH_PIPELINE.md)；[`VAL-UE-02`](../validation/VALIDATION_AND_RECOVERY.md#val-ue-02-m02-v003-hybrid-face-matrix) | 不适用 |
| M02 Elder Morph | `validated_pilot` | [`ANIMATION_AND_MORPH_PIPELINE.md`](./ANIMATION_AND_MORPH_PIPELINE.md)；[`VAL-UE-03`](../validation/VALIDATION_AND_RECOVERY.md#val-ue-03-m02-elder-morph-matrix) | 仅限已验证同身份、同拓扑快照 |
| 十体型统一角色接口 | `planned` | 无 | 扩展 `MODULAR_CHARACTER_RUNTIME.md` |
| 每角色三套可切换发型 | `planned` | 无 | `HAIR_VARIANTS.md` |
| 有/无胡须切换 | `planned` | 无 | `HAIR_VARIANTS.md` |
| 服装 Look 与分层穿搭 | `planned` | 无 | `OUTFIT_RUNTIME.md` |
| 动作道具绑定 | `planned` | 无 | `PROP_BINDING.md` |
| 场景、相机、Sequence 与 MRQ | `planned` | 无 | `SCENE_AND_RENDER_PIPELINE.md` |
| 视频、GT 与 sidecar 输出 | `planned` | 无 | `DATASET_OUTPUTS.md` |

计划项只在真正开始实施时创建对应文件；本 README 的能力矩阵负责保留目录位置，不用空白文档冒充能力。

## UE 工作前置条件

1. `datatry_02` 已启动且当前关卡状态明确。
2. Reallusion Auto Setup 2.03 已在项目级启用，`/Game/CC_Shaders` 可见。
3. 需要自动操作时，实时检查 Unreal MCP，而不是引用旧会话状态。
4. 保存前确认脏包属于本轮工作；崩溃恢复时先审查恢复列表。
5. Pilot 资产只在其登记的 Skeleton、BodyFit 和 Blueprint 边界内复用。

故障与恢复统一见 [`../validation/VALIDATION_AND_RECOVERY.md`](../validation/VALIDATION_AND_RECOVERY.md)。
