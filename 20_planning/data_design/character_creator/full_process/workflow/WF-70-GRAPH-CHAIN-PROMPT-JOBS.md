# WF-70 配置图、编辑链、Prompt 与 Render Job

> 文档 ID：`WF-70`
> 文档类型：`workflow`
> 生命周期：`current`
> 前序：`WF-60`
> 后序：`WF-80`
> Exit Gate：`GATE-70 JOB_GRAPH_ACCEPTED`
> 最近核验：2026-08-25

## 1. 目的与使用时机

把冻结资产和 UE 运行时引用编译为唯一节点、原子边、多轮链、模型文本和一次性渲染作业，避免从笛卡尔积中盲目渲染。

## 2. 前后序与进入条件

- 前序：`WF-60`；后序：`WF-80`。
`GATE-60` 通过；资产、相机、动作和表达式均有稳定 ID 与 UE Object Path。

## 3. 输入

批次规格、资产矩阵、兼容域、Sequence/相机注册表、Schema、采样规则和 Prompt Catalog。

## 4. 正常流程

| 步骤 | 操作 | 精确实现或机器入口 | 本步输出 |
| --- | --- | --- | --- |
| 1. 编译图源 | 把 Required Exports、Look/Action/Expression/Scene/Camera Registry 合并为冻结 source manifest | [`build_first_batch_graph_source_v1.py`](../../../../../00_engine/scripts/dataset/build_first_batch_graph_source_v1.py)；输入顺序见 [配置图 Technical](../technical/dataset/CONFIG_GRAPH_AND_CHAINS.md#3-输入与编译顺序) | `source_manifest.json` 与版本化图源 |
| 2. 编译节点、边、链和作业 | 构建兼容域内唯一节点、原子边、配额链和去重 Render Jobs | [`build_first_batch_config_graph_v1.py`](../../../../../00_engine/scripts/dataset/build_first_batch_config_graph_v1.py) | `assets/domains/nodes/edges/chains/render_jobs` 与构建报告 |
| 3. 生成代表审查包 | 从权威图确定性抽取代表链用于人工/媒体 Smoke | [`build_first_batch_chain_review_v1.py`](../../../../../00_engine/scripts/dataset/build_first_batch_chain_review_v1.py) | `review_10/` 审查包 |
| 4. 生成 Prompt 层 | 从现有原子边生成 Turn/Dialog、身份描述和媒体 URI 引用 | [`build_first_batch_prompt_layer_v1.py`](../../../../../00_engine/scripts/dataset/build_first_batch_prompt_layer_v1.py) 与 [`prompt_catalog_first_batch_v1.json`](../../../../../00_engine/scripts/dataset/prompt_catalog_first_batch_v1.json) | Prompt Manifest、Turns、Dialogs 和文本报告 |
| 5. 执行图/文本 Gate | 重算连通性、单轴变化、配额、事实标签、悬空引用和文本泄漏 | Builder 自带报告、`00_engine/scripts/dataset/tests/` 与 [验证目录](../technical/validation/VALIDATION_CATALOG.md) | `VAL-GRAPH-01/VAL-TEXT-01` 证据 |

配置图是语义权威；Prompt 和媒体 URI 从图派生。不得先写文本或渲染随机笛卡尔积，再反推节点与链。

## 5. 输出契约

| 输出 ID | 逻辑产物 | 存储类别 | 生产所有者 |
| --- | --- | --- | --- |
| `OUT-WF70-JOB-GRAPH` | Assets、Domains、Nodes、Edges、Chains、Render Jobs、Prompt Layer 和构建报告 | `versioned_registry` + `authoritative` 数据根 | [配置图与链](../technical/dataset/CONFIG_GRAPH_AND_CHAINS.md) |

### 输出组成、用途与下游

| 组成 | 实际内容 | 为什么需要 | 下游消费者 |
| --- | --- | --- | --- |
| Source Manifest 与 Assets | 输入版本、哈希、资产和 Object Path 快照 | 锁定图构建所依据的全部上游事实 | 重建、审计和 `WF-80` 输入锁 |
| Domains/Nodes/Edges | 兼容域、唯一视频状态和单轴编辑关系 | 定义可渲染状态空间和可监督编辑 | Render Jobs、Chains、GT 与研究数据 |
| Chains 与事实标签 | 多轮路径、策略类别和五个可重算布尔标签 | 形成多轮编辑样本且保留路径语义 | Prompt 层和最终数据集 |
| Render Jobs | 按 `node_id` 去重后的唯一渲染任务与状态初值 | 避免同一节点被多条链重复渲染 | `WF-80` 正式执行器 |
| Prompt 层 | Prompt Manifest、Turn/Dialog、身份描述和媒体 URI | 把图上的单轴变化转成训练文本 | `WF-90` 发布和模型训练 |
| 构建/审查报告 | 数量、连通性、配额、引用、文本和代表链证据 | 证明结构正确但不冒充媒体完成 | `VAL-GRAPH-01/VAL-TEXT-01` |

当前接受图根和文本版本由 [WF-70 状态](../project_management/status/workflows/WF-70.md#当前输出与证据) 指定；稳定组成与保留语义见 [输出契约目录](../technical/output/OUTPUT_CONTRACTS.md#38-out-wf70-job-graph)。

## 6. 必需验证

| 验证 ID | 角色 | 何时需要 |
| --- | --- | --- |
| `VAL-GRAPH-01` | `required` | 图源、编辑轴、兼容域、采样配额或 Builder 变化后 |
| `VAL-TEXT-01` | `required` | Prompt Catalog、语言模板、身份描述或媒体引用规则变化后 |

定义、证据和通过条件见 [验证目录](../technical/validation/VALIDATION_CATALOG.md)。

## 7. Exit Gate

`GATE-70 JOB_GRAPH_ACCEPTED` 要求数量与批次规格一致、域内规则正确、每条边只改变一个轴、链标签可重算、全部媒体引用可解析且重复生成字节稳定。

## 8. 技术与状态

- [配置图与链](../technical/dataset/CONFIG_GRAPH_AND_CHAINS.md)
- [Prompt 层](../technical/dataset/PROMPT_LAYER.md)
- [当前 WF-70 状态](../project_management/status/workflows/WF-70.md)

## 9. 失败与恢复

生成失败不修改已冻结资产。修复源清单、Schema 或生成器后创建新版本输出，不能原地拼接不同契约的节点和链。
