# UE 模块化角色运行时

> 文档角色：`technical_specification`
> 状态：`validated_pilot`
> 适用阶段：`WF-06,WF-07`
> 权威范围：模块组件、Leader Pose、Morph 广播与运行时变体契约
> 已验证对象：`M02_Average`
> 上级入口：[`README.md`](./README.md)
> 上游：M02 FullReference、拆分模块和 UE 构建脚本
> 下游：模块角色 Workflow、动画与未来变体接口
> 最近核验：2026-08-06

## 1. 资产边界

```text
UE_PROJECT_ROOT = D:\UE\projects\datatry_02

完整参考网格：
/Game/Vendor/Reallusion/CC5/Characters/M02_Average/FullReference/CC_M02_Average_Pilot_UE58

模块根目录：
/Game/Vendor/Reallusion/CC5/Characters/M02_Average/Modules/_SplitPilot

统一 Skeleton：
/Game/Vendor/Reallusion/CC5/Characters/M02_Average/FullReference/CC_M02_Average_Pilot_UE58_Skeleton

DataMake 入口 Blueprint：
/Game/DataMake/Characters/M02_Average/BP_DM_M02_ModularPilot_v002
```

`Vendor` 保存导入或拆分所得源资产，不为了目录整齐而移动。`DataMake` 保存项目自有 Blueprint、运行时控制和稳定入口。

### 1.1 当前实现与复跑入口

| 层级 | 当前代码 | 说明 |
| --- | --- | --- |
| v001 基础构建 | [`ue_build_m02_modular_pilot_blueprint.py`](../../../../../00_engine/scripts/unreal/ue_build_m02_modular_pilot_blueprint.py) | 从拆分网格建立 20 组件基础 Blueprint |
| v001 基础验证 | [`ue_validate_m02_modular_blueprint.py`](../../../../../00_engine/scripts/unreal/ue_validate_m02_modular_blueprint.py) | 仍硬编码 v001，只用于旧基础回归 |
| v002 当前构建 | [`ue_build_m02_face_morph_broadcaster.py`](../../../../../00_engine/scripts/unreal/ue_build_m02_face_morph_broadcaster.py) | 从 v001 派生 v002，并加入 `BroadcastFaceMorph` |
| v002 当前验证 | [`ue_validate_m02_face_morph_broadcaster.py`](../../../../../00_engine/scripts/unreal/ue_validate_m02_face_morph_broadcaster.py) | 验证 20 组件、13 个面部广播组件和非面部隔离 |
| 当前复跑命令 | [`VAL-UE-01`](../validation/VALIDATION_CATALOG.md) | 给出 UE Remote Execution 命令、输出报告和通过字段 |
| 组合结构覆盖 | [`VAL-UE-02`](../validation/VALIDATION_CATALOG.md) | 在 2×5 PIE 矩阵中再次检查 20/19/Leader Pose |

当前没有参数化的十体型 Blueprint 构建器，也没有独立的 v002 通用结构验证器。实现文件的完整定位见 [`../reference/IMPLEMENTATION_INDEX.md`](../reference/IMPLEMENTATION_INDEX.md)。

## 2. 组件契约

M02 Pilot 有 20 个 `SkeletalMeshComponent`。`Body` 是唯一 Leader，另外 19 个组件必须将 `leader_pose_component` 指向 `Body`。

| 分组 | 组件 |
| --- | --- |
| 主体 | `Body` |
| 面部毛发 | `Face_BeardChin`、`Face_BeardNeck`、`Face_Mustache` |
| 眉睫与眼部 | `Face_Brows`、`Face_Eyes`、`Face_EyeOcclusion`、`Face_LashesUpper`、`Face_LashesLower`、`Face_TearDucts`、`Face_Tearline` |
| 口腔 | `Face_Teeth`、`Face_Tongue` |
| 头发 | `Hair_BackLeft`、`Hair_BackRight`、`Hair_Bangs`、`Hair_Mullet` |
| 服装 | `Outfit_Top`、`Outfit_Bottom`、`Outfit_Shoes` |

这些名称是 Pilot 的实现接口，不代表以后所有发型都必须拆成四个部件。新角色应通过统一语义槽位映射资产，而不是让业务逻辑依赖某款头发的内部块名。

## 3. 初始化不变量

角色 Blueprint 或生成代码完成后必须满足：

1. `Body` 使用目标角色 Skeleton，并负责 Anim Blueprint。
2. 19 个 follower 使用兼容 Skeleton 和 Leader Pose。
3. `Body.propagate_curves_to_followers=true`。
4. `Body` 允许动画曲线求值并启用动画。
5. 所有模块共享相同角色坐标、比例和 LOD 语义。
6. Post Process Anim Blueprint 保留 Reallusion Rig Logic；不得为单个 follower 重复运行一套冲突的面部逻辑。

检查证据：

```text
D:\UE\Lance_Work\00_engine\outputs\unreal_character_import\m02_body_face_demo_stage.json
```

当前证据为 `component_count=20`、`follower_count=19`、`followers_without_body_leader=[]`。

## 4. Morph 广播

一个 Morph 可能只存在于部分拆分网格。运行时不能假设只写 `Body` 就会改变所有模块，也不能向不存在该 Morph 的组件写值并把成功调用当作视觉成功。

当前 Blueprint 暴露 `BroadcastFaceMorph`，资产索引登记的覆盖组件数为 13。调用策略为：

1. 对 Body 和所有相关 follower 查询目标 Morph 是否存在。
2. 只对支持组件设置同名权重。
3. 记录实际支持组件集合。
4. 重置时对同一集合写回 `0.0`。
5. 对眼睑、牙齿、胡须、眉毛和头发执行动态视觉检查。

此广播适合已验证的面部 Morph。身体大幅 Morph 会改变服装网格，不得把它当成 UE 中任意体型切换方案。

## 5. 变体策略

### 5.1 当前可以做

- 关闭胡须组件实现有/无胡须 Pilot。
- 在材质兼容时修改发色、眉色和胡须色。
- 用已针对该身份导出的模块替换同一语义槽位。
- 通过 Blueprint 变量选择登记的身体动作和面部片段。

### 5.2 当前不能承诺

- 任意头发适配任意随机头型。
- 一套服装网格适配十个 BodyFit。
- Shirts 与 Coats 任意叠加且无穿模。
- 在 UE 内用身体 Morph 从一个 BodyFit 生成另一个 BodyFit。
- 未导出的牙齿、睫毛、眉毛或胡须在 UE 中自动重贴合。

生产目标是每个角色提前验证三套发型；胡须至少支持开/关。服装按 `BodyFit × Look` 导出，Look 定义层级和互斥关系。

## 6. 新模块接入步骤

1. 在 CC 中用目标 BodyFit 和目标身份装配并完成动态门禁。
2. 按 [`WF-04`](../workflow/WF-04-CC-EXPORT-BUNDLE.md) 导出同 Skeleton 资产，并用 [`WF-05`](../workflow/WF-05-UE-IMPORT-REFERENCE.md) 建立完整参考。
3. 导入 `/Game/Vendor/Reallusion/...`，不覆盖已通过的参考资产。
4. 验证 Skeleton、bind pose、材质、Morph 名和 LOD。
5. 创建或登记语义槽位，不直接替换当前 Pilot 后丢失来源。
6. 设置 Leader Pose，开启曲线传播。
7. 在 Neutral、Blink、Look、Smile、Jaw Open 和两条身体动作上检查。
8. 记录来源 bundle、UE 路径、BodyFit、face identity 和 QA 证据。
9. 通过后才加入运行时候选池。

## 7. 停止条件

发现以下任一情况时停止晋级：

- follower 没有 Body Leader。
- Skeleton 不兼容或 bind pose 偏移。
- 头、眼、牙齿、毛发或服装在中性姿态已穿模。
- 动画曲线没有传播到支持组件。
- Morph 支持组件集合与基准不一致且没有解释。
- Vendor 源资产被原地改写而没有可追溯副本。
- Blueprint 编译失败、编辑器崩溃或恢复包来源不明确。

## 8. 当前同步债务

`D:\UE\projects\datatry_02\DataMake\dm_asset_index.json` 已于 2026-08-19 在线核对并升级为 version 4；它同时保留本模块化 M02 入口与 FullReference F02/M02 P0 入口。模块 Hybrid 和 FullReference direct-Morph 是两套独立契约，不能因为索引统一而混用组件或 Post Process 策略。

`ue_validate_m02_modular_blueprint.py` 的 Blueprint 路径仍是 v001。当前 v002 只由面部广播脚本和 v003 组合矩阵覆盖；这项限制已登记到 [`../planning/BACKLOG.md`](../planning/BACKLOG.md)。
