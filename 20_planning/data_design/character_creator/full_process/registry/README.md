# Registry：机器权威反向索引

> 文档 ID：`REGISTRY-INDEX`
> 文档类型：`registry_index`
> 生命周期：`current`
> 权威范围：机器可读权威、适用范围、Technical 所有者和反向查询入口
> 最近核验：2026-08-25

## 1. 子系统职责

Registry 子系统用于“已知对象名或文件类型，但不知道机器真值和实现归属”时反向查询。它只登记：

1. 机器权威的准确路径或定位规则；
2. 该权威当前用于哪个范围；
3. 解释、生成和维护它的唯一 Technical 所有者；
4. 主要消费 Workflow。

本页不复制 Registry 的字段和值，不保存当前验证结果，也不替代 Workflow 的执行顺序。当前接受版本和证据必须查 Status；字段/生成命令必须查 Technical；词义和路径别名必须查 [Reference](../reference/README.md)。

## 2. CC 与资产权威

| 对象 | 当前机器权威 | 当前范围 | Technical 所有者 | 主要 Workflow |
| --- | --- | --- | --- | --- |
| BodyFit | `repo://00_engine/scripts/character_creator/cc_body_preset_library_v2.json` | 10 个冻结 BodyFit | [BodyFit / Identity / Age](../technical/character_creator/BODYFIT_IDENTITY_AGE.md) | `WF-20`, `WF-30` |
| Face V3 | `repo://00_engine/scripts/character_creator/cc_face_seed_library_v1.json`、`repo://00_engine/scripts/character_creator/cc_face_recipes_v3_200.json` | 当前旧生产身份原型与配方 | [BodyFit / Identity / Age](../technical/character_creator/BODYFIT_IDENTITY_AGE.md) | `WF-20`, `WF-30` |
| Headshot 原型与头型 | `repo://00_engine/scripts/character_creator/cc_headshot_face_prototype_registry_v1.json`、`repo://00_engine/scripts/character_creator/cc_headshot_skull_profile_library_v1.json` | 已验证候选；是否进入批次由 Asset Matrix 决定 | [BodyFit / Identity / Age](../technical/character_creator/BODYFIT_IDENTITY_AGE.md) | `WF-20`, `WF-30` |
| 第一批 Identity | `repo://00_engine/scripts/character_creator/cc_first_batch_identity_library_20260820_v1.json` | `BATCH-001-FIRST-DATA` | [BodyFit / Identity / Age](../technical/character_creator/BODYFIT_IDENTITY_AGE.md) | `WF-20`, `WF-30` |
| 外观资产 | `repo://00_engine/scripts/character_creator/cc_appearance_asset_catalog_v1.json`、`repo://00_engine/scripts/character_creator/cc_facial_hair_asset_catalog_v1.json`、`repo://00_engine/scripts/character_creator/cc_scalp_hair_asset_catalog_v1.json` | 皮肤、眼球、眉毛、睫毛、牙齿、胡须和头发候选 | [外观资产](../technical/character_creator/APPEARANCE_ASSETS.md) | `WF-20`, `WF-30` |
| Outfit Family | `%CLOTHING_ROOT%/<sex>/<family>/outfit_family.json` 与 `repo://00_engine/scripts/character_creator/outfit_family_v1.schema.json` | 人工批准的 Family 内组合 | [服装系统](../technical/character_creator/OUTFIT_SYSTEM.md) | `WF-20`, `WF-30` |
| 第一批 32 Look | `repo://00_engine/scripts/character_creator/cc_first_batch_full_reference_looks_20260822_v3.json` | `BATCH-001-FIRST-DATA` | [组装与验收](../technical/character_creator/ASSEMBLY_AND_ACCEPTANCE.md) | `WF-20`–`WF-50` |
| 第一批动作池 | `repo://00_engine/scripts/character_creator/cc_first_batch_action_pool_20260824_v1.json` | 女性 5、男性 5 的当前生产动作 | [动作传输](../technical/transfer/MOTION_TRANSFER.md) | `WF-20`, `WF-40`, `WF-50` |

没有出现在“当前机器权威”列中的旧 Probe、旧版本 JSON 或人工截图，不能因为文件仍存在就被视为生产 Registry。是否保留由 Output/History 规则决定。

## 3. Transfer、UE 与数据集权威

| 对象 | 当前机器权威 | 当前范围 | Technical 所有者 | 主要 Workflow |
| --- | --- | --- | --- | --- |
| 必需 CC 导出 | `repo://00_engine/scripts/dataset/first_batch_required_exports_20260824_v3.json` | 第一批 Transfer 输入闭包 | [资产追溯](../technical/transfer/ASSET_TRACEABILITY.md) | `WF-40` |
| 本地 Look/Action/Camera 矩阵 | `repo://00_engine/scripts/unreal/first_batch_local_render_matrix_20260824_v1.json` | 第一批本地与图源矩阵 | [场景、相机与 Sequence](../technical/unreal/SCENE_CAMERA_SEQUENCE.md) | `WF-20`, `WF-60`, `WF-80` |
| 第一批 Expression | `repo://00_engine/scripts/unreal/first_batch_expression_profile_20260820_v1.json` | 第一批表情配置来源 | [动画、表情与 Morph](../technical/unreal/ANIMATION_EXPRESSION_MORPH.md) | `WF-50`, `WF-70` |
| 第一批图源 | `repo://00_engine/scripts/dataset/first_batch_graph_source_20260824_v1.json` | 节点、边、链和 Render Job 的唯一源输入 | [配置图与链](../technical/dataset/CONFIG_GRAPH_AND_CHAINS.md) | `WF-70`, `WF-80` |
| Prompt Catalog | `repo://00_engine/scripts/dataset/prompt_catalog_first_batch_v1.json` | 第一批模板与身份描述 | [Prompt 层](../technical/dataset/PROMPT_LAYER.md) | `WF-70`, `WF-90` |
| UE 早期对象索引 | `%UE_PROJECT_ROOT%/DataMake/dm_asset_index.json` | 早期场景/角色引用辅助；不是第一批图源替代品 | [角色运行时](../technical/unreal/CHARACTER_RUNTIME.md) | `WF-50`, `WF-60` |

## 4. 跨阶段控制目录

| 对象 | 机器/文档权威 | 查询用途 | 所有者 |
| --- | --- | --- | --- |
| 脚本生命周期与归属 | `repo://00_engine/scripts/SCRIPT_CATALOG.json` | 由脚本路径反查生命周期、哈希和 Technical 所有者 | [脚本生命周期](../technical/implementation/SCRIPT_LIFECYCLE.md) |
| 验证契约 | [Validation Catalog](../technical/validation/VALIDATION_CATALOG.md) | 由 `VAL-*` 反查触发条件、证据、实现与状态落点 | [Validation 子系统](../technical/validation/README.md) |
| 输出契约 | [Output Contracts](../technical/output/OUTPUT_CONTRACTS.md) | 由 `OUT-*` 反查生产者、存储类别和状态所有者 | [Output 子系统](../technical/output/README.md) |
| 输出保留规则 | `repo://00_engine/outputs/RETENTION_POLICY.json` | 由物理输出路径反查保留等级、所有者和输出契约 | [盘点与保留](../technical/output/INVENTORY_AND_RETENTION.md) |
| 输出当前盘点 | `repo://00_engine/outputs/OUTPUT_INVENTORY.json` | 查看已扫描路径的当前分类，不直接授权删除 | [盘点与保留](../technical/output/INVENTORY_AND_RETENTION.md) |
| 当前项目状态 | [PROJECT_STATE.json](../project_management/status/PROJECT_STATE.json) | 机器读取 active Workflow/Plan/Batch、验证和当前输出指针 | [Status 子系统](../project_management/status/README.md) |

本轮文档交接清单：[server_documentation_sync_20261023.json](../../../../implementation/server_documentation_sync_20261023.json)，由[DOCUMENT_SYNC](../technical/rendering_release/DOCUMENT_SYNC.md)拥有，仅用于该次服务器文档快照，不是发布媒体Manifest或持续同步权威。

## 5. 查询规则

### 5.1 反向查询

```text
对象名或物理文件
  -> 本索引定位机器权威
  -> Technical 确认字段、生成命令和限制
  -> Workflow 确认何时消费
  -> Workflow/Batch Status 确认当前接受版本与证据
```

### 5.2 顺向执行

```text
Master / 当前 Status
  -> Workflow
  -> Technical
  -> 机器 Registry / Manifest
  -> VAL-* / OUT-*
```

顺向工作不要从本页猜测执行步骤。

## 6. 独立维护契约

- 每条当前 Registry 必须有准确定位、适用范围、Technical 所有者和主要 Workflow。
- 同一对象存在多个版本时，只把当前权威放入主表；旧版本通过 History、Git 或产生它的 Technical 追溯。
- Registry 内容、动态计数和当前通过状态不得复制到本页。
- 新增机器权威时，先由 Technical 定义，再更新本页；若改变长期语义，同时提交 ADR。
- 路径不存在、所有者缺失、多个文件同时自称当前权威或 Status 指向不同版本时，停止使用并执行 `VAL-DOC-01`。
