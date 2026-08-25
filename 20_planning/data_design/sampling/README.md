# sampling —— 配置图采样与多轮链

> ↑ 父层：[`../README.md`](../README.md)（数据设计）。

## 📂 内容说明

本目录定义配置图采样、兼容域内随机游走、多轮链抽取和结构事实标注：

- [`MULTI_ROUND_CHAIN_SAMPLING_V1.md`](./MULTI_ROUND_CHAIN_SAMPLING_V1.md)：第一批 3–5 轮链的双策略、五个事实标签、精确 4,000 条配额、两域连通、覆盖与去重规则。
- 核心端点复用原则见 [`../README.md`](../README.md)。实际生成命令、输入和权威产物见 [配置图技术文档](../character_creator/full_process/technical/dataset/CONFIG_GRAPH_AND_CHAINS.md)。

## Agent 备忘

- 多轮链长和策略比例属于训练侧采样，但数据侧必须保证原子边、同域路径、端点复用和可重算标签。
- 当前规范已接受并完成第一批本地实现：640 节点、8,320 条有向原子边和 4,000 条链已通过结构门禁。媒体生产与发布状态必须继续从 [`WF-80`](../character_creator/full_process/workflow/WF-80-RENDER-EXECUTION.md) 和[活动批次状态](../character_creator/full_process/project_management/status/batches/BATCH-001-FIRST-DATA.md)判断。
