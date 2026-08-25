# 角色工厂历史与快照

> 文档角色：`history_index`
> 状态：`current`
> 适用阶段：`global`
> 权威范围：完成事件和不可变旧文档快照导航
> 上级入口：[`../CHARACTER_FACTORY_MASTER_SPEC.md`](../CHARACTER_FACTORY_MASTER_SPEC.md)
> 上游：已完成工作和被替代文档
> 下游：Milestone、日期化汇报与三个不可变快照目录
> 最近核验：2026-08-24

| 内容 | 作用 |
| --- | --- |
| [`MILESTONE_LOG.md`](./MILESTONE_LOG.md) | 只追加的完成事件、范围和证据入口 |
| [`reports/README.md`](./reports/README.md) | 日期化周报和阶段汇报索引；只作汇报快照，不定义当前流程 |
| [`legacy_2026-08-06/ARCHIVE_MANIFEST.md`](./legacy_2026-08-06/ARCHIVE_MANIFEST.md) | 第一次文档重组前六份旧文档的哈希清单 |
| [`pre_lifecycle_restructure_2026-08-06/ARCHIVE_MANIFEST.md`](./pre_lifecycle_restructure_2026-08-06/ARCHIVE_MANIFEST.md) | 本次生命周期重构前 37 份现行文档的路径、字节数和哈希 |
| [`pre_chain_contract_rewrite_2026-08-24/ARCHIVE_MANIFEST.md`](./pre_chain_contract_rewrite_2026-08-24/ARCHIVE_MANIFEST.md) | 配置图兼容域与双策略链契约重写前的 Schema/Sampling 原文哈希 |

历史用于追溯，不定义当前行为。快照文件逐字节不可变；需要纠错时在当前文档或 Milestone 中追加说明，不修改旧原文。
