# ADR-0017：交付视频使用顺序编号

> 文档 ID：`ADR-0017`
> 文档类型：`decision`
> 生命周期：`current`
> 状态：`accepted`
> 决定日期：2026-08-29
> 影响范围：`WF-80/WF-90`、节点媒体、Prompt 媒体 URI 与发布 Manifest
> 最近核验：2026-08-29

## 背景

内部 `node_id` 由规范化 Node Config 的 SHA-256 前 16 位稳定派生。它适合作为渲染、断点续跑、冲突检测和链端点复用主键，但 `n_<hash>` 不适合作为最终数据接收方直接浏览的视频文件名。

第一批文本层和 Render Job 均通过 `node_id` 引用唯一媒体。直接把内部文件改名为数字会破坏已有输入锁、Sidecar、恢复状态和媒体 URI；在发布层额外建立编号映射可以同时满足可读交付与内部可追溯性。

## 决定

1. 渲染层继续使用 `media/nodes/<node_id>/video.mp4`，`node_id` 的生成和语义不变。
2. 交付层把本次发布涉及的唯一节点按 `node_id` 字典序确定性排序，映射为从 `1` 开始的正整数文件名：`videos/1.mp4`、`videos/2.mp4`、依此类推。
3. `manifest.json` 必须保存 `视频编号/路径 -> node_id -> config_sha256 -> media_sha256` 的完整双向可恢复信息；数字本身不承载语义。
4. `chains.json` 使用顺序编号视频路径，但同时保留 Chain/Turn/Node/Edge ID、配置、双语 Prompt、独立 Prompt 和 Grounding，供训练与审计分别消费。
5. 每个发布版本独立冻结编号映射。改变链选择、媒体内容或映射规则必须生成新的发布目录，禁止原地覆盖。

目标接收方结构为：

```text
dataset_v1/
  videos/
    1.mp4
    2.mp4
    ...
  chains.json
  manifest.json
```

## 影响与后果

- 数据接收方只需读取三个顶层对象；GT、媒体规格、哈希、源 Sidecar 追溯和编号映射进入 `manifest.json`。
- 相同节点在多条链中只保存一份视频，`chains.json` 的多个位置复用同一编号路径。
- 局部样例包和完整发布包可能对同一 `node_id` 分配不同数字；比较数据时必须先读取各自 Manifest，不能跨包假设编号稳定。
- 发布封装器必须先验证 accepted Sidecar、图配置和媒体 SHA-256，再物化编号视频。

## 复审条件

只有接收方明确要求分片、WebDataset/Parquet、全局跨版本数字 ID，或单个 `manifest.json` 超出消费工具可接受大小时，才复审目录布局；复审不得移除内部 `node_id` 和哈希追溯。
