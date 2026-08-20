# ADR-0013：Headshot 身份使用项目几何原型包

> 文档角色：`architecture_decision`
> 状态：`Accepted`
> 适用阶段：`RM-05B..RM-06,WF-01..WF-03`
> 权威范围：Headshot 身份的规范存储载体与生产接入顺序
> 上级入口：[`README.md`](./README.md)
> 上游：2026-08-08 Headshot Profile 升级与存储探针
> 下游：[`../cc_details/HEADSHOT_PIPELINE.md`](../cc_details/HEADSHOT_PIPELINE.md)
> 最近核验：2026-08-08

## 1. 背景

最初两个 Headshot 来源项目加载后均能枚举 `2837` 个 shaping Morph，但全部权重为零。新增的两个来源项目得到相同结果。四个人物身份均清晰存在，说明 Headshot 结果已经烘焙到项目网格，而不是由一组可重放的滑块权重表达。

只保存 Facial Profile 能保留动态表情配置，不能保存身份几何。实验性 `AvatarPresetAll` 虽写出约 `73.8 MB` 文件，但 CC 明确弹出“未创建 Morph Slider，角色形状不会保留”的警告；保存 API 直到用户关闭弹窗后才在约 `2 小时 46 分` 返回。它不具备身份完整性或无人值守稳定性。

## 2. 决定

每个 Headshot 原型采用版本化目录，并至少保存：

```text
identity_cc5_hd.ccProject
facial_profile_cc5_hd.ccFacialProfile
source_cc4_extended.ccFacialProfile
source_reference.jpg
evidence\
prototype.json
```

- `.ccProject` 是身份几何的唯一规范载体。
- `.ccFacialProfile` 是 CC5 动态配置载体，不单独声明身份。
- `prototype.json` 固化来源、大小、SHA-256、验证状态、证据和装配契约。
- 中央注册表只登记 `prototype_id`、性别、状态和 manifest 哈希。
- 原始 Headshot 项目保持冻结；规范项目始终由派生副本产生。

正式接入采用 `headshot_project_seed_then_bodyfit_v1`：先加载身份项目，再应用同性交付 Body/Junction、恢复规范 Profile、应用安全局部 Morph，最后应用 BodyFit Head Scale/Neck Height 和外观。

## 3. 后果

- 每个原型约占 100 MB，但可以忠实保留不可由滑块复建的身份。
- 原型可以独立哈希、回退、审计和人工验收。
- 现有 Face V3 的“BodyFit 起步再加载 Head seed”流程不能直接复用；必须实现项目起步的新分支。
- 在项目起步装配和用户视觉门禁通过前，Headshot 候选保持 `enabled_for_production=false`。

## 4. 未采用方案

| 方案 | 原因 |
| --- | --- |
| 保存完整 shaping Morph 向量 | 当前四例非零项均为 0，无法复建身份 |
| 只保存 `.ccFacialProfile` | 只承载动态配置，不承载身份几何 |
| 只保存 Facial Profile AvatarPreset | 与独立 Profile 一样，不是身份载体 |
| 当前即采用 `AvatarPresetAll` | 需要人工关闭警告、约 2 小时 46 分才返回，且 CC 明确提示形状不会保留；不满足身份与稳定性门禁 |

## 5. 复审条件

只有在新 CC/RLPy 版本证明某种更轻量格式能同时满足身份一致、Profile 一致、重载稳定、可哈希和十体型装配门禁时，才新增 ADR 取代本决定。
