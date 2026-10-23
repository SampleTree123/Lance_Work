# 服装 Family、槽位组与兼容性

> 文档 ID：`TECH-CC-03`
> 文档类型：`technical`
> 生命周期：`current`
> 适用阶段：`WF-20/WF-30`
> 实现所有权：Outfit Family JSON、共享鞋池、静态兼容门禁和动作压力门禁
> 验证所有权：`VAL-MATRIX-01`（服装兼容子项）、`VAL-CC-02`
> 输出契约：`OUT-WF20-ASSET-MATRIX`、`OUT-WF30-CC-ASSETS`
> 最近核验：2026-08-30

## 1. 能力与边界

服装以 Family 为兼容边界。除人工明确合并或 Registry 允许的组合外，不跨 Family 随意替换单件。第一批在 UE 中使用烘焙 FullReference Look，不依赖运行时单件换装。

## 2. 输入、规范目录和槽位

Family 内服装目录只使用：

```text
Coats/
Shirts/
Pants/
Skirts/
Full-body/
Shoes/
_Accessories-Pending/
outfit_family.json
```

`Full-body` 的单个资产可以是独立整套，也可以是由多个锁定组件构成的 Bundle；JSON 的组类型消除歧义。

平均体型衣柜的 Elise 有已批准的版本化例外：用户 2026-09-08 选择 `4.ccCloth` 而非 `2.ccCloth`，其余锁定组件及鞋池不变。当前规则从衣柜 v3 Registry 指向的 `family_contracts/female.elise.json` 读取，外部旧 `outfit_family.json` 仅保留原始来源，不再决定本次 Elise 组成；源资产未删除。准确配置、路径、生成命令和恢复规则见 [Transfer 第10.9节](../transfer/CC_TO_UE_MODULAR_OUTFIT_PILOT.md#109-用户批准的锁定套装修订)。

## 3. Family JSON 模型

- `slot_group`：定义必选/可选槽位及每个槽位的候选池；兼容项可自由组合。
- `locked_bundle`：一组资产必须整体应用，不能拆分。
- `local_accessories`：只适用于当前 Family 的配件，不进入全局 Both 池。
- 鞋：Family 有原配鞋时只使用自己的 `Shoes/`；没有原配鞋时通过共享 `shoe_ids` 解析到全局鞋 Registry；`barefoot_allowed` 不等于必须赤脚。

## 4. 机器入口

| 文件/工具 | 作用 |
| --- | --- |
| `outfit_family_v1.schema.json` | Family JSON Schema |
| `cc_validate_outfit_family_library_v1.py` | 全库结构与引用验证 |
| `cc_build_confirmed_outfit_family_json_v1.py` | 从已确认规则生成 Family JSON |
| `cc_merge_shared_shoe_assignments_into_outfit_rules_v1.py` | 合并鞋池分配 |
| `cc_organize_shared_shoes_v1.py` / `cc_finalize_curated_shoes_v1.py` | 鞋池去重、分类、重编号 |
| `cc_build_outfit_compatibility_gate_v1.py` | 三体型静态门禁计划 |
| `cc_build_outfit_motion_stress_gate_v1.py` | 重体型动作压力门禁计划 |
| `cc_validate_body_reconstruction.py` | CC 内实际装配、动作和截图 |

## 5. 当前验证边界

现有精选库包含 41 个 Family 和 53 个逻辑组。静态极端体型门禁为 159/159，动作压力门禁为 53/53，用户已抽查并接受；这不代表未来新增体型、动作或跨 Family 组合自动兼容。

## 6. 组装顺序与弹窗

1. 重载规范角色项目并清除源服装/源局部配件。
2. 按内到外顺序应用 Pants/Skirts、Shirts、Coats、Full-body、Shoes 和本地配件。
3. 对旧代服装的 Apply Cloth Options 只能使用 Family 已验证策略；未知情况停止。
4. 验证 Inventory Signature，防止资产被隐式替换或驱逐。

## 7. 验证

- 静态：前、后、左右和三分之四视角，覆盖 slim/heavy/short 极端体型。
- 动态：至少 Walk 与 Full Body Calibration 的归一化时间采样。
- 人工：腋下、腰腹、胯部、裙摆、鞋脚、头发/兜帽和多层服装。
- UE：导入后用生产 Skeleton 和动作再次检查，CC 通过不能替代 UE 验收。

### 7.1 发型与服装的组合排除

发型、胡须和服装分别通过资产级检查后，仍必须执行组合级视觉检查。重点覆盖长发/兜帽/头巾/高领、多层服装和代表动作；发现穿模、遮挡或明显材质冲突时，记录 `hair_id`、`outfit_id`、BodyFit、动作和证据路径，写入版本化兼容排除清单。排除的是具体组合，不删除或否定单独资产；后续 `WF-20` 矩阵冻结和 `WF-70` 图编译必须消费该清单。

当前已确认的发型×服装规则以 Family 默认和资产级覆盖表达：除明确禁用范围外，其他服装全部使用 `allow_all=true, deny_all=false`；女性 `Rugged & Trendy Collection`、男性 `redsoul`、男性 `Rugged & Trendy Collection` 整个 Family 使用 `deny_all`，`WarriorCloak_A/B/C` 和 `Windbreaker_A/B/C` 使用资产级 `deny_all` 覆盖。用户确认的视觉证据为 `%OUTPUT_ROOT%/unreal_character_import/hair_outfit_compatibility_20260926_v1/manual_review.json`，现有版本化排除记录为 `00_engine/assets/character_creator/outfit_compatibility_aliases/hair_outfit_compatibility_exclusion_registry_20260926_v1.json`。当前策略不再设置 `pending_review` 回退。

面向 UE 的单文件 Registry 设计稿为 `00_engine/assets/character_creator/wardrobe_registry_ue_v4_draft_example_v2.json`。它直接保存 UE 服装资产索引、原 Family 的 `assembly`/鞋池/约束、40 个 UE 发型索引，以及每个 Family 的默认 `hair_interface`；组合完成后，代码检查所选资产是否带有 `deny_all` 覆盖，任意一个命中即不加载并清除发型。该设计稿仍在逐字段删减，不是当前运行时权威文件。

用户已批准把现有哈希式 `asset_id` 与 UE Case Root 的可读命名迁移记录为后续工作，当前不改 JSON ID 或 UE 资产路径。实施时须先冻结 `<sex>.<family>.<slot>.<asset_name>` 一类确定性命名规范，生成完整旧新映射，再通过 UE AssetTools 移动/重命名资产并修复 Blueprint、Level、Manifest 和组合引用；锁定 Bundle 使用可读 Bundle Root。迁移完成后必须验证 ID 唯一、全部 `assembly` 引用可解析、UE 路径存在并通过代表性服装切换测试。

第二批数量不预先固定。用户先从每个身份约三套发型候选和胡须有/无变体开始筛选，最终启用数由视觉 Gate 决定。

## 8. 输出与保留

Family JSON、Schema、鞋 Registry 和最终审查索引为 `authoritative`。完整静态/动态 Gate 和用户决定为 `retained_evidence`。日期重组备份、旧恢复分片和被取代联系表在映射确认后可标为 `superseded`。

## 9. 模块化服装 Pilot 的 CC 输入

M02/F02 平均体型模块化 Pilot 从已确认 Family JSON 中冻结 14 个 Case，覆盖 2 个无服装基础身体和 12 个服装 Case。它不重新解释全库规则，只允许 Manifest 明确列出的模块和 Runtime Variant：

```text
00_engine/scripts/character_creator/cc_modular_outfit_pilot_source_v1.json
00_engine/scripts/character_creator/cc_modular_outfit_pilot_20260829_v1.json
```

编译与收口文件为 `cc_build_modular_outfit_pilot_v1.py`、`run_modular_outfit_pilot_export.ps1` 和 `cc_finalize_modular_outfit_pilot_v1.py`；CC 实际装配仍由 `cc_validate_body_reconstruction.py` 的受控命令完成。精确执行顺序、双形态 Bundle 和当前证据见 [CC 到 UE 模块化服装 Pilot](../transfer/CC_TO_UE_MODULAR_OUTFIT_PILOT.md)。

当前 Pilot 只证明选定模块可在平均体型上转移和组装。未来新增 BodyFit、修改 Family JSON、鞋池、`cloth_options_policy` 或 Runtime Variant 时，必须重新触发 `VAL-MATRIX-01`、`VAL-CC-02`、`VAL-TRANSFER-01` 和适用的 `VAL-UE-02`，不能沿用旧视觉结论。
