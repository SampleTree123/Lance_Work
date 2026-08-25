# 数据图与文本层技术索引

> 文档 ID：`TECH-DATASET-INDEX`
> 文档类型：`technical_index`
> 生命周期：`current`
> 适用阶段：`WF-10/WF-70/WF-90`
> 权威范围：配置图、编辑链、Prompt 和 Render Job 编译
> 最近核验：2026-08-25

| 文档 | 负责内容 |
| --- | --- |
| [批次规格](./BATCH_SPECIFICATION.md) | 批次目标、可编辑轴、兼容域、媒体规格与停止/降级条件 |
| [资产与生产矩阵冻结](./ASSET_MATRIX_FREEZE.md) | 生产资产 ID、来源、兼容关系、排除项和必需导出 |
| [配置图与编辑链](./CONFIG_GRAPH_AND_CHAINS.md) | 节点、原子边、兼容域、链策略、确定性生成和结构门禁 |
| [Prompt 层](./PROMPT_LAYER.md) | 身份描述、单轴指令、Turn/Dialog、文本门禁和媒体解析 |

跨批次 Schema 位于 `20_planning/data_design/schema/`，链采样规范位于 `20_planning/data_design/sampling/`。本目录负责说明实现如何消费这些规范，不复制第二份 Schema。
