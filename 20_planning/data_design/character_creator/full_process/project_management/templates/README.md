# Templates：新文档结构契约

> 文档 ID：`TEMPLATE-INDEX`
> 文档类型：`template_index`
> 生命周期：`current`
> 权威范围：各可扩展文档子系统的新文档必填结构
> 最近核验：2026-08-25

## 1. 模板索引

| 模板 | 用于新建 | 独立契约重点 |
| --- | --- | --- |
| [Workflow](./WORKFLOW_TEMPLATE.md) | `WF-*` | 顺序、输入、`OUT-*`、`VAL-*`、Gate、恢复 |
| [Technical](./TECHNICAL_TEMPLATE.md) | 实现文档 | 代码/配置/命令、验证实现、输出产生、恢复 |
| [Status](./STATUS_TEMPLATE.md) | Workflow/Batch Status | 当前能力、计划、验证、输出、风险、下一 Gate |
| [Plan](./PLAN_TEMPLATE.md) | current/queued/paused Plan | 稳定需求 ID、状态、验收和证据入口 |
| [Validation](./VALIDATION_TEMPLATE.md) | 新 `VAL-*` | 触发、证据、通过、失效、实现和结果所有者 |
| [Output](./OUTPUT_TEMPLATE.md) | 新 `OUT-*` | 生产者、存储、Manifest、晋升、保留、状态所有者 |
| [ADR](./ADR_TEMPLATE.md) | 长期决定 | 背景、决定、后果、复审和替代关系 |
| [History](./HISTORY_TEMPLATE.md) | 关闭计划/报告 | 当时范围、最终事实、证据和未纳入项 |
| [Reference](./REFERENCE_TEMPLATE.md) | 新稳定参考 | 稳定定义或路径；禁止当前状态 |
| [Registry](./REGISTRY_TEMPLATE.md) | 新机器权威索引 | 路径、范围、Technical 所有者和消费 Workflow |

## 2. 使用规则

1. 先确认要新增的事实确实属于该子系统；不要为了写文档创造重复权威。
2. 复制后把 `文档类型` 改为目标类型，替换全部方括号/`XX`/`YYYY` 占位符。
3. 把新文件加入其直接父目录 README，再运行该子系统独立检查。
4. 独立检查通过后，才补显式跨层关系并运行 `VAL-DOC-01`。
5. 模板更新不滚动覆盖已存在文档；现有文档通过审计单独迁移。

Master 和 Governance 是单例权威，不通过模板复制创建。
