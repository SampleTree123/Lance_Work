# 资产追溯契约

> 文档 ID：`TECH-TRANSFER-03`
> 文档类型：`technical`
> 生命周期：`current`
> 适用阶段：`WF-20..WF-90`
> 实现所有权：源资产、CC 项目、导出 Bundle、UE 对象、图节点与媒体的稳定映射
> 验证所有权：`VAL-MATRIX-01`、`VAL-TRANSFER-01` 的追溯子项
> 输出契约：`OUT-WF20-ASSET-MATRIX`、`OUT-WF40-TRANSFER-BUNDLE`
> 最近核验：2026-10-01（精确清理总验收、现用审查重载与重新导入源保留链）

## 1. 输入、输出与追溯链

```text
source asset + BodyFit + identity recipe + outfit rule
  -> canonical CC project / Look manifest
  -> versioned FBX + JSON + textures bundle
  -> UE Vendor FullReference + canonical Skeleton
  -> DataMake Blueprint / animation / Sequence
  -> graph asset -> node -> render_job
  -> media + sidecar + QA + delivery manifest
```

每层必须保存上一层的稳定 ID、版本和哈希，不能通过截图或显示名反推来源。

## 2. ID 与 URI

| 对象 | 主键/引用 |
| --- | --- |
| BodyFit、Identity、Outfit、Action、Camera | Registry 中的稳定 ID |
| Look | `look_id`，如 `F_ID02_O04` |
| CC/动作文件 | Manifest 中相对 URI、字节数、SHA-256 |
| UE 资产 | `/Game/...` Soft Object Path |
| Node | 规范化语义配置的稳定哈希 ID |
| Edge/Chain | 规范化端点或有序路径哈希 ID |
| Media | `node_id` + 权威相对 URI + SHA-256 |

禁止在可迁移清单的 `source_ref` 中保存盘符绝对路径。机器绝对路径只属于 [路径别名](../../reference/PATH_ALIASES.md) 或运行时锁文件。

## 3. UE 目录边界

- `/Game/Vendor/Reallusion/...`：外部导入来源。第一批 Look 与规范 BASE/Skeleton 保留；经审计的衣柜/发型运行资产已通过 UE API 复制到正式目录并重映射，禁止用磁盘移动 uasset 替代迁移。
- `/Game/DataMake/...`：自有 Blueprint、派生动画、Sequence、配置和验证资产。
- `%UE_PROJECT_ROOT%/DataMake/dm_asset_index.json`：早期/运行时资产索引，修改前必须在线核对 UE 对象；它不是首批配置图的替代品。

### 3.1 当前 UE 衣柜、发型与审查真值

`repo://00_engine/assets/character_creator/wardrobe_registry_ue_v4_full_20260929.json` 是当前衣柜/共享鞋/发型的精确 UE 对象与合法搭配索引；现用资产位于 `/Game/DataMake/CharacterFactory/{Wardrobe,Hair}/`，由 `/Game/DataMake/Characters/CharacterFactoryRuntime/.../v003` 读取。旧导入报告里的 Vendor/Case 路径是来源见证，不是当前查询地址。详细字段与迁移映射由 [Transfer 第 11 节](./CC_TO_UE_MODULAR_OUTFIT_PILOT.md#11-ue-衣柜与发型资产去冗余试点2026-09-28)拥有。

现用服装 Coverage 和发型×服装审查计划为 `%OUTPUT_ROOT%/unreal_character_import/current_reviews_20261001_v1/{wardrobe_coverage,hair_outfit_compatibility}/review_plan.json`。Compatibility 另读同目录 `bodyfit_metadata.json`；HairFit 使用 `%OUTPUT_ROOT%/unreal_character_import/hair_sex_fit_review_20260929_v1/review_plan.json`。命令和关卡由 [角色运行时 3.8](../unreal/CHARACTER_RUNTIME.md#38-现用入口与-2026-10-01-清理边界)拥有。当前 Plan 晋升不改历史 accepted Plan 或用户决定。

### 3.2 CC 清单与导入配置晋升

发型现用清单为 `%CC_EXPORT_ROOT%/scalp_hair_batch_20260924_v1/manifests/cc_export.json`，与原 staging 输入字节相同、preset 及产出路径相同；`ue_scalp_hair_batch_import_v1.py` 已消费此正式位置。共享 Pipeline 是 `/Game/DataMake/Config/Import/DM_Interchange_Split_Pipeline_v1`，已实测与旧配置一致，BASE Skeleton 不变。历史 `batch_import_report.json` 的旧路径不改写；晋升证据在 `%OUTPUT_ROOT%/asset_cleanup/cleanup_20261001_v1/cc_audit/hair_manifest_migration_result.json` 与 `import_pipeline_migration.json`，实施所有权见 [Transfer 11.5](./CC_TO_UE_MODULAR_OUTFIT_PILOT.md#115-发型现用-cc-清单与共享导入-pipeline2026-10-01)。

## 4. 最小 Bundle Manifest

```json
{
  "bundle_id": "...",
  "look_id": "F_ID02_O04",
  "bodyfit_id": "F02_Average",
  "identity_id": "F_ID02",
  "outfit_id": "O04",
  "source_project": {"uri": "bundle://...", "sha256": "..."},
  "fbx": {"uri": "bundle://...", "sha256": "...", "bytes": 0},
  "json": {"uri": "bundle://...", "sha256": "...", "bytes": 0},
  "target": {"engine": "UE 5.8", "auto_setup": "2.03"}
}
```

真实值由 Registry/Manifest 生成，不从本文示例复制。

## 5. 变更规则

- 像素相关配置、源文件、Skeleton、材质或动作窗口改变时生成新版本。
- 旧 Bundle 和旧节点不原地改写；通过替代关系标记 `superseded`。
- 相同 `node_id` 不得对应两个配置哈希或两个不同权威媒体。
- 追溯断裂是硬失败；不得以“视觉看起来一样”跳过。

## 6. 审计入口

反向查询从 [Registry 索引](../../registry/README.md) 开始；顺向执行从对应 Workflow/Technical 文档开始。正式发布时必须同时验证资产引用、文件哈希、UE 对象路径、节点配置哈希、媒体哈希和 Sidecar 哈希。

## 7. 失败与恢复

任一层引用、版本或哈希断裂时停止依赖它的下游阶段，从最近一个仍可验证的上游 Manifest 重建映射。不得通过重命名文件、手改 `node_id` 或忽略哈希来恢复。若源资产确实变化，创建新 Bundle/UE 资产/图版本并登记取代关系；旧链保持可审计。

## 8. 2026-10-01 清理追溯与执行边界

本轮可清理物必须由精确文件/包清单、来源哈希、替代物、引用闭包、人工决定保留规则和执行回执共同说明。报告与冻结 Manifest 中的旧路径可继续作为 historical evidence，不能因为历史路径没有当前文件就改写旧记录或恢复旧执行资产。需要重放时先查规范输入、保留小型工单和迁移映射；无法验证来源时停止。

旧 14-Case、P0、ScalpHairPilot、v001/v002 独立执行入口退出当前使用；有效报告作为 `retained_evidence` 保留。两个 v2 UE 模块的 shared helpers、同性 Average BASE Skeleton/Body、第一批生产 Look/动画/Sequence 和当前发型依赖的 M02 共享纹理/Rig 支持仍保留，旧目录名不能成为整树删除依据。

本轮入口迁移和清理后的独立重载已通过 Coverage 173 套 API 装配/第 1 页保存重载、Compatibility 第 1 项及正/侧/背视角和 Pipeline 等价验证；没有新增逐款人工视觉或完整动态适配结论。精确名单中的 2,396 个 UE 包、4,594,625,010 字节已清理，正式 777 个包哈希完全不变，保存图没有新增缺失 Game 引用，保留 Rig 的只读补验通过且未改资产。cleanup 根的 `ue_cleanup_receipt.json` 记录 completed，最终运行时证据为 `post_cleanup_runtime_checks_completion.json`；原迁移报告、分项失败和回执继续保留，不覆盖成单一成功记录。

UE API 曾返回对象删除成功但遗留 World 文件，也曾触发保留网格的未保存内存变更；已停止并退出，不采信或保存这些内存变更。最终离线精确清理在 UE 关闭、新鲜保存图对删除集合外引用为零、保护闭包与清单无交集后完成；每个字面路径和哈希绑定审核清单，随后正式 777 个包字节、新进程 registry、173 套装配和现用关卡保存重载均已核验。API 删除和离线清理分别记录，不笼统宣称“全部 UE API 完成”。源码 guard 或计划入口调整也不能成为新增功能验收。输出盘点、保留决策和恢复指针由 [清理 Output 所有者](../output/INVENTORY_AND_RETENTION.md#9-2026-10-01-全面清理与目录重组)维护。

保留链还包括 UE ImportData 指向的重新导入来源。`retained_legacy_support_import_sources.json` 逐项记录 183 个仍保留的 M02 共享支持资产及其 `%CC_EXPORT_ROOT%/pilot_m02_ue58_v001/CC_M02_Average_Pilot_UE58.Fbx` 来源，文件实际存在；`cc_retired_export_cleanup_review.json` 据此将完整 M02 导出包的 271 个文件、501,042,951 字节列为保留。其他旧导出 821 个文件、3,517,715,394 字节已由 `cc_retired_export_cleanup_receipt.json` 记录删除。旧源目录和执行入口年代不能替代引用审计；本轮保留原 ImportData 与冻结记录，没有将来源路径改为当前名称或删除仍可重导的输入。