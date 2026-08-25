# 输出盘点与保留

> 文档 ID：`TECH-OUTPUT-02`
> 文档类型：`technical`
> 生命周期：`current`
> 适用阶段：全部 Workflow
> 实现所有权：输出所有权规则、保留策略、Inventory Builder 和非破坏性清理前置条件
> 验证所有权：`VAL-DOC-01`
> 输出契约：`OUT-GLOBAL-OUTPUT-INVENTORY`
> 最近核验：2026-08-25

## 1. 能力与边界

本能力回答：某个 `%OUTPUT_ROOT%` 路径由谁生产、属于哪个 Workflow/`OUT-*`、当前保留级别是什么、是否允许进入清理候选。它不生成业务产物、不自动删除文件，也不替代生产它的领域 Technical 文档。

机器权威：

```text
00_engine/outputs/README.md
00_engine/outputs/RETENTION_POLICY.json
00_engine/outputs/OUTPUT_INVENTORY.json
```

## 2. 实现组成与环境

| 文件 | 生命周期 | 作用 |
| --- | --- | --- |
| `00_engine/scripts/documentation/build_output_inventory.py` | `utility` | 非破坏性扫描输出作用域并应用最长前缀规则 |
| `00_engine/scripts/documentation/check_character_factory_docs.py` | `utility` | 检查 owner、保留规则、输出契约和物理路径一致性 |
| `00_engine/outputs/RETENTION_POLICY.json` | `authoritative` | 人工审查的所有权与保留规则 |
| `00_engine/outputs/OUTPUT_INVENTORY.json` | `authoritative` | 当前盘点生成物 |

在 `%LANCE_ROOT%` 的系统 Python 环境执行，不需要 CC/UE：

```powershell
python 00_engine/scripts/documentation/build_output_inventory.py
python 00_engine/scripts/documentation/check_character_factory_docs.py --json
```

## 3. Policy 契约

`ownership_rules` 只决定领域 owner 和 Workflow；`rules` 决定经过人工审查的保留级别，并可用更长路径覆盖 owner。二者与 `output_contract_id` 共同形成反向查询，但所有权和保留必须保持独立：一个输出有 owner 不代表它值得长期保留，一个输出未分类也不代表可以删除。

保留级别：

| 级别 | 含义 | 清理资格 |
| --- | --- | --- |
| `authoritative` | 当前生产输入、正式媒体/数据或不可替代 Manifest | 未迁移验收前禁止 |
| `retained_evidence` | 支撑 Gate、事故结论或人工接受 | 替代证据通过后再审查 |
| `superseded` | 已由映射后的新版本完整取代 | 可进入人工清理候选 |
| `disposable` | 可重建缓存、临时日志或失败中间帧 | 不影响追溯时可清理 |
| `unclassified` | 尚未完成保留审查 | 默认禁止 |

## 4. Inventory 契约

盘点记录至少包含：相对路径、作用域级别、文件数、字节数、最后修改时间、`retention`、`workflow`、`owner_document`、`output_contract_id`、匹配规则和原因。默认枚举每个输出根的直接子作用域；Retention Policy 点名的深层路径额外单列，避免递归展开巨大历史树。

Inventory 是可重建元数据，不替代正式发布媒体哈希。`WF-90` 的 Delivery Manifest/Checksums 才负责交付内容完整性。

## 5. 新输出登记

1. 在生产它的领域 Technical 文档中写清 `OUT-*`、路径模式、目录结构、验证和建议保留级别。
2. 若为新逻辑产物，在 [输出契约目录](./OUTPUT_CONTRACTS.md) 登记稳定 ID。
3. 在 `ownership_rules` 增加大类 owner；需要长期保留时再在 `rules` 增加精确路径、`output_contract_id` 和理由。
4. 重建 `OUTPUT_INVENTORY.json`，确认物理路径、owner、Workflow、契约和保留级别。
5. 执行 `VAL-DOC-01`，并在对应 Workflow/Batch Status 登记当前接受版本。

## 6. 清理前置条件

只有 `superseded` 或 `disposable` 可以成为清理候选。清理前逐项确认：目标绝对路径位于预期输出根、替代物存在且已验收、Manifest/哈希可追溯、当前 Status/Plan 未引用、Git 与 UE/CC 外部资产不依赖该路径。`unclassified` 不能因旧、占空间大或目录名含 `test` 被删除。

本流程只生成候选清单；递归删除仍是独立、显式审批的文件系统操作。

## 7. 验证与恢复

通过条件：所有输出作用域有存在的 Technical owner；每条保留规则目标存在、在 Inventory 中一致，并直接被 owner 文档说明；每条长期证据绑定有效 `OUT-*`。Builder 失败时保留旧 Inventory，修复策略或权限后原子重建，不手改生成统计。

路径漂移、误删或规则过期时先停止依赖该证据的 Gate。根据 Manifest 恢复路径，或创建新版本并更新 Status/替代映射；不得通过删除规则来让审计静默通过。

## 8. 当前限制

大部分历史作用域仍为 `unclassified`，在逐项确认替代关系前均受保护。Inventory 只盘点 `%OUTPUT_ROOT%`；`%CC_ASSET_ROOT%`、`%CC_EXPORT_ROOT%`、UE `/Game` 和服务器 Delivery 由其领域 Manifest/Registry 追踪，不因未出现在本文件中而失去所有权。
