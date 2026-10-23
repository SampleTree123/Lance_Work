# 渲染与发布技术索引

> 文档 ID：`TECH-RELEASE-INDEX`
> 文档类型：`technical_index`
> 生命周期：`current`
> 适用阶段：`WF-80/WF-90`
> 权威范围：本地渲染、服务器执行、媒体 QA 和数据集封装
> 最近核验：2026-09-30

| 文档 | 负责内容 | 当前状态 |
| --- | --- | --- |
| [渲染执行](./RENDER_EXECUTION.md) | Render Job、MRQ、恢复和本地 Smoke | 正式执行器本地 2 节点真渲染/恢复已验证；服务器完成由用户确认，媒体证据待同步 |
| [服务器执行](./SERVER_EXECUTION.md) | Linux/NVIDIA 预检、10 节点基准和批量重试 | 旧精确环境失败保留历史；当前成功环境和预检/基准证据待同步 |
| [数据集封装](./DATASET_PACKAGE.md) | 媒体 Sidecar、GT、清单、哈希和发布 Gate | 交付契约已定义；用户确认发布/训练使用，独立发布证据待核验 |
