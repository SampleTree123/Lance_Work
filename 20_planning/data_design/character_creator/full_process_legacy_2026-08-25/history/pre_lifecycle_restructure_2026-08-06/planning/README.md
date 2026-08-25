# 规划文档

> 文档角色：`planning_index`
> 上级入口：[`../CHARACTER_FACTORY_MASTER_SPEC.md`](../CHARACTER_FACTORY_MASTER_SPEC.md)
> 最近核验：2026-08-06

## 文件职责

| 文件 | 包含 | 不包含 |
| --- | --- | --- |
| [`ROADMAP.md`](./ROADMAP.md) | 已接受、按阶段排序、具有完成标准的未来工作 | 已完成历史、未经承诺的想法 |
| [`BACKLOG.md`](./BACKLOG.md) | 候选改进、研究问题和未排期技术债务 | 当前阶段执行命令、已完成记录 |

当前能力看 [`../CURRENT_STATUS.md`](../CURRENT_STATUS.md)，历史事件看 [`../history/MILESTONE_LOG.md`](../history/MILESTONE_LOG.md)，已接受且长期有效的规则看 [`../decisions/README.md`](../decisions/README.md)。

## 变更规则

1. 阶段必须有目标、输入、输出、验收和停止条件。
2. 阶段完成后从 Roadmap 移除，结论追加到 Milestone Log，并更新 Current Status。
3. Backlog 项目进入承诺范围时移到 Roadmap，并补齐依赖和验收标准。
4. 不用 `TODO` 数量代替能力状态；状态必须来自实际验证。
