# Output 技术索引

> 文档 ID：`TECH-OUTPUT-INDEX`
> 文档类型：`technical_index`
> 生命周期：`current`
> 权威范围：逻辑输出 ID、存储类别、Run Root、Manifest、保留、盘点和清理前置条件
> 最近核验：2026-08-25

| 文档 | 何时使用 |
| --- | --- |
| [输出契约目录](./OUTPUT_CONTRACTS.md) | 从 Workflow 的 `OUT-*` 确认产物内容、存储类别、生产所有者和状态落点 |
| [输出盘点与保留](./INVENTORY_AND_RETENTION.md) | 登记新输出、重建 Inventory、决定保留等级或准备清理时 |

Output 区只定义全局输出语义和机器盘点规则。某项输出如何生成、字段怎样计算、失败如何恢复，仍由表中指向的领域 Technical 文档负责；当前采用哪个版本由 Workflow/Batch Status 负责。
