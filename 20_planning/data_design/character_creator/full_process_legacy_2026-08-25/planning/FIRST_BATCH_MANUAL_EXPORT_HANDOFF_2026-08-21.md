# 第一批 CC 手动导出交接清单

> 文档角色：`active_sprint_handoff`  
> 状态：`completed_reference`  
> 适用阶段：`WF-04..WF-07`  
> 权威范围：第一批数据 Day 2 的 CC Motion 人工导出事实、文件清单和 UE 交接边界  
> 上级入口：[`README.md`](./README.md)  
> 上游：[`FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md`](./FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md) 与 v4 动作注册表  
> 下游：[`../workflow/WF-05-UE-IMPORT-REFERENCE.md`](../workflow/WF-05-UE-IMPORT-REFERENCE.md)、[`../workflow/WF-07-ANIMATION-AND-PROPS.md`](../workflow/WF-07-ANIMATION-AND-PROPS.md)  
> 最近核验：2026-08-22  
> 权威机器清单：`00_engine/scripts/dataset/first_batch_required_exports_20260822_v2.json`

## 1. 临时执行策略

为了优先在一周内跑通第一批数据，CC 导出和 Reallusion Auto Setup 导入允许由用户在图形界面中完成。Agent 继续负责固定清单、文件命名、哈希、UE 资产组织、5 秒窗口、门禁、数据 JSON 和渲染编排。

本策略不改变生产配置，只把无法稳定无人值守的 UI 操作转为人工执行。自动化导出属于后续优化，不再阻塞第一批数据。

## 2. 已完成且禁止重复导出的内容

以下 `32` 个 FullReference Look 已包含 `.ccProject`、`.fbx`、同名 Auto Setup `.json` 和 `.fbm/`，CC 合并审计为 `32/32`：

```text
D:\UE\exports\character_creator\first_data_batch_20260820_v1\full_reference
```

除非权威清单的哈希校验失败，否则不要重新导出人物或服装。第一批换装通过切换完整 Look 实现，不拆分模块化服装。

## 3. 已完成的 CC 手动导出

需要导出 `12` 个完整时长的 Motion-only FBX。女性动作使用女性 UE5 骨架载体，男性动作使用男性 UE5 骨架载体。优先使用 CC5 官方支持的 `Motion -> Custom -> Save One Motion Per File` 批量方式，不需要把动作放入项目时间线。

推荐载体：

```text
Female: D:\CharacterCreator_sucai\Reallusion Custom\Project\CC Project\F02_Average.ccProject
Male:   D:\CharacterCreator_sucai\Reallusion Custom\Project\CC Project\M02_Average.ccProject
```

批量导出从 `Custom` 文件列表读取源动作，因此载体项目已有的预览时间线不会作为导出输入。不要保存覆盖源 `.ccProject`。

### 3.1 每个性别执行一次批量导出

1. 加载对应性别的载体。
2. 执行 `File -> Export -> FBX -> Clothed Character`。
3. `Target Tool Preset` 选择 `UE 5 (Skeleton)`，`FBX Options` 选择 `Motion`。
4. 在 `Include Motion` 中选择 `Custom`，通过文件按钮一次加入该性别的 6 个 `.rlMotion` / `.iMotion`。
5. 启用 `Save One Motion Per File`，不启用网格或纹理导出。
6. 高级设置保持 UE5 Skeleton 和 Hand/Foot IK；关闭 `Add Reference Pose`、`Use T-Pose As Bind Pose`、`Zero Motion Root`、`Mouth Open as Morph` 和 `Convert Skinned Expressions to Morphs`。
7. 导出完整动作范围，不在 CC 中手工裁剪 5 秒窗口。
8. 允许 CC 使用源动作名称输出 6 个文件；Agent 验证后统一重命名为下表规范名称。

已签字的 5 秒窗口由 UE Sequence 使用 Start Offset 实现。源动作不足 5 秒时，按 Sprint 规则进行轻微 Idle 补齐，不拉伸速度。

### 3.2 女性动作

目标目录：

```text
D:\UE\exports\character_creator\first_data_batch_20260820_v1\motions\female
```

| 状态 | 动作 ID | CC 源文件 | 生产窗口 | FBX 文件名 |
| --- | --- | --- | --- | --- |
| [x] | `ACT_F01_SEXY_DANCE` | `01_act_f01_sexy_dance.rlMotion` | `1.6..6.6 s` | `A_F01_SEXY_DANCE.fbx` |
| [x] | `ACT_F02_CATCH_BREATH` | `02_act_f02_catch_breath.iMotion` | `0.0..5.0 s` | `A_F02_CATCH_BREATH.fbx` |
| [x] | `ACT_F03_AUDIENCE_01` | `03_act_f03_audience_01.rlMotion` | `0.0..4.516667 s` | `A_F03_AUDIENCE_01.fbx` |
| [x] | `ACT_F04_AUDIENCE_09` | `04_act_f04_audience_09.rlMotion` | `0.0..4.9 s` | `A_F04_AUDIENCE_09.fbx` |
| [x] | `ACT_F05_TIE_SHOES` | `05_act_f05_tie_shoes.iMotion` | `2.4..7.4 s` | `A_F05_TIE_SHOES.fbx` |
| [x] | `ACT_F06_ELEVATOR_GREETING` | `06_act_f06_elevator_greeting.rlMotion` | `1.0..6.0 s` | `A_F06_ELEVATOR_GREETING.fbx` |

源目录：

```text
D:\UE\Lance_Work\00_engine\scripts\character_creator\runtime_assets\first_batch_actions_20260821_v4\motions
```

### 3.3 男性动作

目标目录：

```text
D:\UE\exports\character_creator\first_data_batch_20260820_v1\motions\male
```

| 状态 | 动作 ID | CC 源文件 | 生产窗口 | FBX 文件名 |
| --- | --- | --- | --- | --- |
| [x] | `ACT_M01_BATTLE_DANCE` | `07_act_m01_battle_dance.rlMotion` | `0.0..5.0 s` | `A_M01_BATTLE_DANCE.fbx` |
| [x] | `ACT_M02_AUDIENCE_01` | `08_act_m02_audience_01.rlMotion` | `0.0..3.4 s` | `A_M02_AUDIENCE_01.fbx` |
| [x] | `ACT_M03_AUDIENCE_12` | `09_act_m03_audience_12.rlMotion` | `0.0..3.8 s` | `A_M03_AUDIENCE_12.fbx` |
| [x] | `ACT_M04_LIVING_ROOM_SWING` | `10_act_m04_living_room_swing.rlMotion` | `0.0..5.0 s` | `A_M04_LIVING_ROOM_SWING.fbx` |
| [x] | `ACT_M05_ELEVATOR_GREETING` | `11_act_m05_elevator_greeting.rlMotion` | `1.0..6.0 s` | `A_M05_ELEVATOR_GREETING.fbx` |
| [x] | `ACT_M06_CHEER_HANDS_STEP_DANCE` | `12_act_m06_cheer_hands_step_dance.rlMotion` | `3.0..8.0 s` | `A_M06_CHEER_HANDS_STEP_DANCE.fbx` |

截至 2026-08-21，12/12 Motion FBX 已存在并规范命名。三条替换动作通过 CC 动态门禁 3/3，最终 12 个五秒窗口已全部签署并冻结。机器清单状态为 `frozen_sources_ready_for_unreal_import`；不再需要重复操作 CC。

## 4. 动作导出后的交接

动作导出与窗口冻结已经完成。Agent 随后执行：

1. `[完成]` 验证 `12/12` 文件存在、非空且名称唯一。
2. `[完成]` 记录字节数和 SHA-256，并更新机器清单状态。
3. `[完成]` 导入 UE，共用对应 FullReference Skeleton，不创建 12 套重复骨架。
4. `[完成]` 验证时长、Root Motion、骨架绑定和衣服变形的受限技术门禁。
5. `[下一阶段]` 在 Sequence 中应用冻结的 5 秒窗口及必要的 Idle 补齐。

## 5. UE FullReference Look 手动导入

完整矩阵最终把 `32` 个 Look 分别导入到：

```text
/Game/Vendor/Reallusion/CC5/FirstDataBatch/Looks/<LOOK_ID>
```

使用 Reallusion Auto Setup 的 High Quality 流程，并保留同名 `.json` 与 `.fbm/` 在 FBX 旁。当前自动入口、三项小批次限制、同权限窗口守卫和崩溃恢复以 [`WF-05`](../workflow/WF-05-UE-IMPORT-REFERENCE.md) 为准；本节只保留手工回退。最终机器门禁为 32/32，不再需要重复导入。

## 6. 停止条件

- CC 显示内容许可、缺失资产或导出失败时，不生成空文件冒充成功。
- FBX 中包含多个动作、错误性别骨架或意外网格时停止该条并重导。
- UE Auto Setup 没有生成预期高质量材质时，不把该 Look 标记为已导入。
- 任一源文件路径或哈希与权威机器清单不一致时，先交由 Agent 重新核对。
