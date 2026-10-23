# 渲染与发布技术索引

> 文档 ID：`TECH-RELEASE-INDEX`
> 文档类型：`technical_index`
> 生命周期：`current`
> 适用阶段：`WF-80/WF-90`
> 权威范围：本地渲染、服务器执行、媒体 QA 和数据集封装
> 最近核验：2026-10-23

| 文档 | 负责内容 | 当前状态 |
| --- | --- | --- |
| [渲染执行](./RENDER_EXECUTION.md) | Render Job、MRQ、恢复和本地 Smoke | 第一批已完成；能力证据见WF-80 Status，新批次需另行验收 |
| [服务器执行](./SERVER_EXECUTION.md) | Linux/NVIDIA 预检、10 节点基准和批量重试 | 历史兼容构建生产通过；当前引擎路径需重新确认，见服务器同步状态 |
| [数据集封装](./DATASET_PACKAGE.md) | 媒体 Sidecar、GT、清单、哈希和发布 Gate | 第一批已发布并完成独立验证，见WF-90 Status |
| [文档同步](./DOCUMENT_SYNC.md) | 两端文档范围、清单与冲突合并 | 服务器整理完成后由用户同步；不代表资产/引擎同步 |
