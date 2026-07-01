# schema —— 统一样本格式

> ↑ 父层：[`../README.md`](../README.md)（数据设计）。

## 📂 内容说明

本目录用于沉淀统一样本 schema。当前样本 schema v0 暂在 [`../../../00_engine/scripts/README.md`](../../../00_engine/scripts/README.md) 中，等 MVP 跑通后再迁移成正式 schema。

## Agent 备忘

- schema 必须覆盖三来源：真实视频、大模型生成、Unreal 合成。
- `video_in`、`instruction`、`video_out`、配置、资产、许可证、GT passes 和端点复用信息都是一等字段。
