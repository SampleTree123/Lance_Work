# schema —— 统一样本格式

> ↑ 父层：[`../README.md`](../README.md)（数据设计）。

## 📂 内容说明

本目录沉淀跨来源统一样本 schema。当前第一批 Unreal 数据先使用：

- [`CONFIG_GRAPH_SCHEMA_V1.md`](./CONFIG_GRAPH_SCHEMA_V1.md)：第一批 asset、兼容域、node、原子 edge、chain、render job、媒体与哈希字段契约；当前冻结为四相机、Happy-only、640 节点。
- [`MULTI_ROUND_VIDEO_EDIT_TEXT_SCHEMA_V1.md`](./MULTI_ROUND_VIDEO_EDIT_TEXT_SCHEMA_V1.md)：把合法配置链转换为双语 `video_in + prompt + video_out` 回合和完整多轮对话；明确训练文本、历史回退与身份 grounding 边界。

当前执行位置与实现命令分别见 [`WF-70`](../character_creator/full_process/workflow/WF-70-GRAPH-CHAIN-PROMPT-JOBS.md)、[配置图技术文档](../character_creator/full_process/technical/dataset/CONFIG_GRAPH_AND_CHAINS.md)和 [Prompt 技术文档](../character_creator/full_process/technical/dataset/PROMPT_LAYER.md)。

旧 schema v0 仍在 [`../../../00_engine/scripts/README.md`](../../../00_engine/scripts/README.md) 中作为兼容参考；第一批 MVP 验收后再决定如何合并为跨三来源的正式 schema。

## Agent 备忘

- 最终 schema 必须覆盖三来源：真实视频、大模型生成、Unreal 合成；V1 当前只承诺第一批 Unreal 配置图。
- `video_in`、`instruction`、`video_out`、配置、资产、来源/许可元数据、GT passes、兼容域和端点复用信息都是一等字段。
