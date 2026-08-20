# WF-09 渲染与数据集交付包

> 文档角色：`workflow_runbook`
> 状态：`planned`
> 适用阶段：`WF-09`
> 权威范围：短视频、配置图、编辑链、sidecar、哈希和证据包的最终交付契约；当前第一批受限范围
> 上级入口：[`README.md`](./README.md)
> 上游：[`WF-08-SCENE-CAMERA-SEQUENCE.md`](./WF-08-SCENE-CAMERA-SEQUENCE.md)
> 下游：无，生产主线终点
> 最近核验：2026-08-19

## 1. 目的与使用时机

把通过场景门禁的 Sequence 渲染为可训练、可复查、可追溯的数据包，并验证媒体、GT、配置和证据彼此一致。

## 2. 当前范围与非目标

本阶段尚未实现。第一批冻结目标为最多 384 个唯一节点和 3,000–4,000 条 3–5 轮链；节点只渲染一次，链只引用媒体。完整范围见 [Sprint](../planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md)，字段和采样分别见 [Config Graph Schema V1](../../../schema/CONFIG_GRAPH_SCHEMA_V1.md) 与 [Sampling V1](../../../sampling/MULTI_ROUND_CHAIN_SAMPLING_V1.md)。

## 3. 进入条件

- `GATE-08 SCENE_READY` 通过。
- Sequence、角色、场景、相机、动画、随机种子和资产版本全部冻结。
- 输出根和唯一 dataset/run ID 已确定，旧结果不会被覆盖。

## 4. 输入与输出

第一批输入：通过 Gate 的 Sequence 模板、`assets.json`、`nodes.jsonl`、`edges.jsonl`、`render_jobs.jsonl` 和 render profile。输出至少包括唯一节点视频、sidecar、媒体哈希、`chains.jsonl`、失败/重试记录、软件与资产版本和验收报告。

## 5. 执行环境

计划使用 UE 5.8 Editor 命令行离屏模式和经验证的 MRQ/等价入口。服务器必须先完成 10 节点基准；同步、预检、降级和重试边界见 [Server Runbook](../../../../implementation/FIRST_BATCH_SERVER_RUNBOOK.md)。

## 6. 执行步骤

计划顺序为：创建唯一运行目录 → 冻结资产和节点图 → 本地完整链 smoke → 服务器 10 节点基准 → 批量渲染唯一节点 → 生成 sidecar/哈希 → 生成 3–5 轮链 → 自动引用一致性检查 → 人工抽检 → 封装交付。当前不得把此顺序解释为已有自动命令。

## 7. 退出门禁

计划门禁为 [`GATE-09 DATASET_ACCEPTED`](../validation/README.md)。未来 `VAL-DATASET-01` 必须验证帧数、时间、媒体可读性、GT/sidecar 对齐、资产追溯和哈希；`VIS-DATASET-01` 检查画面、遮挡、穿模、曝光和角色表现。

## 8. 失败与恢复

未来必须按失败类型支持仅重渲染缺失帧或整个 run，并保留失败报告。配置、资产或 Sequence 发生变化时必须生成新版本，不能把不同来源的帧拼入同一已验收包。

## 9. 技术依据与下一阶段

外部输出职责见 [`EXTERNAL_DIRECTORIES.md`](../reference/EXTERNAL_DIRECTORIES.md)，当前实施顺序见 [Sprint](../planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md)。`GATE-09` 通过才代表一份数据集包完成；在此之前只能称为 Pilot 或中间产物。
