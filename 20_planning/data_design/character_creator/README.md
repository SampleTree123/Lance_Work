# Character Factory 文档入口

当前生产文档统一位于 [`full_process/`](./full_process/README.md)。本页只作为父目录导航，不维护第二套状态或文件清单。

## 阅读顺序

1. [`full_process/README.md`](./full_process/README.md)：项目定义、文档结构和端到端十阶段流程。
2. [`PROJECT_STATUS.md`](./full_process/project_management/status/PROJECT_STATUS.md)：当前计划、活动批次、能力边界和唯一下一步。
3. [`workflow/README.md`](./full_process/workflow/README.md)：`WF-00/10/.../90` 的阶段契约。
4. [`technical/README.md`](./full_process/technical/README.md)：代码、配置、命令、输出、验证和恢复。
5. [`project_management/README.md`](./full_process/project_management/README.md)：状态、计划、ADR 与历史。

路径、术语和机器 Registry 反向查询见 [`reference/README.md`](./full_process/reference/README.md)。

## 非活动目录

- `full_process_legacy_2026-08-25/`：切换前旧活跃树，保留审计，不用于执行。
- `rebuild_reference_2026-08-25/`：重构前哈希快照。

脚本、输出、CC 资产、导出 Bundle 和 UE 项目位于文档树之外，其所有权通过 Workflow、Technical、`SCRIPT_CATALOG.json` 和 `OUTPUT_INVENTORY.json` 追溯。
