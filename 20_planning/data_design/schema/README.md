# schema —— 统一样本格式

> ↑ 父层：[`../README.md`](../README.md)（数据设计）。

## 📂 内容说明

本目录沉淀跨来源统一样本 schema。当前第一批 Unreal 数据先使用：

- [`CONFIG_GRAPH_SCHEMA_V1.md`](./CONFIG_GRAPH_SCHEMA_V1.md)：asset、node、edge、chain、render job、媒体与哈希契约。

旧 schema v0 仍在 [`../../../00_engine/scripts/README.md`](../../../00_engine/scripts/README.md) 中作为兼容参考；第一批 MVP 验收后再决定如何合并为跨三来源的正式 schema。

## Agent 备忘

- 最终 schema 必须覆盖三来源：真实视频、大模型生成、Unreal 合成；V1 当前只承诺第一批 Unreal 配置图。
- `video_in`、`instruction`、`video_out`、配置、资产、许可证、GT passes 和端点复用信息都是一等字段。
