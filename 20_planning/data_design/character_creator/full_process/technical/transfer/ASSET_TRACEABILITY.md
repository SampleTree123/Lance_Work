# 资产追溯契约

> 文档 ID：`TECH-TRANSFER-03`
> 文档类型：`technical`
> 生命周期：`current`
> 适用阶段：`WF-20..WF-90`
> 实现所有权：源资产、CC 项目、导出 Bundle、UE 对象、图节点与媒体的稳定映射
> 验证所有权：`VAL-MATRIX-01`、`VAL-TRANSFER-01` 的追溯子项
> 输出契约：`OUT-WF20-ASSET-MATRIX`、`OUT-WF40-TRANSFER-BUNDLE`
> 最近核验：2026-08-25

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

- `/Game/Vendor/Reallusion/...`：外部导入资产，不移动、不就地重构。
- `/Game/DataMake/...`：自有 Blueprint、派生动画、Sequence、配置和验证资产。
- `%UE_PROJECT_ROOT%/DataMake/dm_asset_index.json`：早期/运行时资产索引，修改前必须在线核对 UE 对象；它不是首批配置图的替代品。

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
