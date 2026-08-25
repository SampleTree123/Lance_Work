# CC Bridge 领域规范

> 文档角色：`subsystem_index`
> 状态：`current`
> 适用阶段：`WF-00,WF-02,WF-03`
> 权威范围：Bridge 文档导航
> 上级入口：[`../CHARACTER_FACTORY_MASTER_SPEC.md`](../CHARACTER_FACTORY_MASTER_SPEC.md)
> 上游：Bridge 代码、协议与配置
> 下游：[`BRIDGE_OPERATIONS.md`](./BRIDGE_OPERATIONS.md)
> 最近核验：2026-08-06

[`BRIDGE_OPERATIONS.md`](./BRIDGE_OPERATIONS.md) 解释安装、协议、队列、allowlist、命令语义和 Undo 守卫。每次会话的实际健康检查从 [`WF-00`](../workflow/WF-00-SESSION-PREFLIGHT.md) 进入，准确命令由 [`VAL-BRIDGE-01`](../validation/VALIDATION_CATALOG.md) 定义，失败按 [`REC-BRIDGE-01`](../validation/RECOVERY_RUNBOOK.md) 恢复。

