# Output 技术索引

> 文档 ID：`TECH-OUTPUT-INDEX`
> 文档类型：`technical_index`
> 生命周期：`current`
> 权威范围：逻辑输出 ID、存储类别、Run Root、Manifest、保留、盘点和清理前置条件
> 最近核验：2026-08-26

| 文档 | 何时使用 |
| --- | --- |
| [输出契约目录](./OUTPUT_CONTRACTS.md) | 从 Workflow 的 `OUT-*` 确认产物内容、存储类别、生产所有者和状态落点 |
| [输出盘点与保留](./INVENTORY_AND_RETENTION.md) | 登记新输出、重建 Inventory、决定保留等级或准备清理时 |

Output 区只定义全局输出语义和机器盘点规则。某项输出如何生成、字段怎样计算、失败如何恢复，仍由表中指向的领域 Technical 文档负责；当前采用哪个版本由 Workflow/Batch Status 负责。

## 查询某一批次的实际输出

Output Contract 不保存不断变化的批次路径。已知批次时使用以下顺序：

```text
Master / Project Status
  -> Batch Status 的“权威机器产物”（当前物理路径与完成状态）
  -> 对应 OUT-*（稳定逻辑组成和保留语义）
  -> 生产 Technical（目录格式、字段、命令和恢复）
```

当前活动批次入口见 [BATCH-001 权威机器产物](../../project_management/status/batches/BATCH-001-FIRST-DATA.md#权威机器产物)。若只知道磁盘路径而不知道批次或所有者，则改从 [输出盘点与保留](./INVENTORY_AND_RETENTION.md) 反查。
