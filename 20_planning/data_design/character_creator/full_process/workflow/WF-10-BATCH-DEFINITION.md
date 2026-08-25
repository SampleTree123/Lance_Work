# WF-10 批次定义

> 文档 ID：`WF-10`
> 文档类型：`workflow`
> 生命周期：`current`
> 前序：`WF-00`
> 后序：`WF-20`
> Exit Gate：`GATE-10 BATCH_SPEC_ACCEPTED`
> 最近核验：2026-08-25

## 1. 目的与使用时机

在动用资产和编辑器前，定义本批数据解决什么问题、允许编辑哪些轴、目标规模、媒体规格、交付内容和降级边界。

## 2. 前后序与进入条件

- 前序：`WF-00`；后序：`WF-20`。
`GATE-00` 通过，当前计划已经建立或明确更新。

## 3. 输入

研究目标、数据任务定义、现有系统能力、预算、截止条件和风险边界。

## 4. 正常流程

| 步骤 | 操作 | 精确实现或机器入口 | 本步输出 |
| --- | --- | --- | --- |
| 1. 建立批次与计划映射 | 分配唯一 `batch_id`，把需求映射到当前 `PLAN-*` | [计划索引](../project_management/plans/PLAN_INDEX.md)、[批次状态索引](../project_management/status/batches/README.md)；当前机器状态为 [`PROJECT_STATE.json`](../project_management/status/PROJECT_STATE.json) | Batch/Plan 身份与责任边界 |
| 2. 定义数据语义 | 定义节点因素、可编辑轴、兼容域和链策略 | [配置图 Schema](../../../schema/CONFIG_GRAPH_SCHEMA_V1.md)、[链采样规范](../../../sampling/MULTI_ROUND_CHAIN_SAMPLING_V1.md) | 可被 `WF-70` 编译的语义契约 |
| 3. 定义媒体与交付 | 定义时长、帧率、分辨率、GT、Sidecar、文本和交付布局 | [文本 Schema](../../../schema/MULTI_ROUND_VIDEO_EDIT_TEXT_SCHEMA_V1.md) 与 [批次规格 Technical](../technical/dataset/BATCH_SPECIFICATION.md#3-必填规格) | 媒体/文本/发布规格 |
| 4. 定义规模与降级 | 冻结规模、验收指标、重试、停止条件和版本化降级 | [当前计划索引](../project_management/plans/PLAN_INDEX.md)、[Batch Status](../project_management/status/batches/README.md) 和 [`PROJECT_STATE.json`](../project_management/status/PROJECT_STATE.json) 共同负责；没有单独 Batch Spec Builder | 冻结规模与风险边界 |
| 5. 执行一致性检查 | 检查计划、状态、机器字段和 Schema 是否一致 | [`check_character_factory_docs.py`](../../../../../00_engine/scripts/documentation/check_character_factory_docs.py) 与 `00_engine/scripts/dataset/tests/`；命令见 [批次规格](../technical/dataset/BATCH_SPECIFICATION.md#4-执行步骤) | `VAL-SPEC-01` 证据 |

本阶段当前是“版本化文档 + 机器状态 + Schema”的受控组合，不存在通用一键 Batch Spec Builder；这属于明确实现边界，不得以手写脚本名代替。

## 5. 输出契约

| 输出 ID | 逻辑产物 | 存储类别 | 生产所有者 |
| --- | --- | --- | --- |
| `OUT-WF10-BATCH-SPEC` | 活动批次状态、机器可读规格和被接受的计划需求 | `versioned_registry`，Git 管理 | [批次规格](../technical/dataset/BATCH_SPECIFICATION.md) |

### 输出组成、用途与下游

| 组成 | 实际内容 | 为什么需要 | 下游消费者 |
| --- | --- | --- | --- |
| 计划需求 | 目标、完成条件、风险和允许降级 | 说明本批为何存在以及什么算完成 | 全部 Workflow Status 与 `WF-90` |
| Batch Status | 人类可读冻结规格、执行进度和例外 | 把长期流程落实到一个具体批次 | `WF-20` 资产冻结和发布审计 |
| 机器关键字段 | `batch_id`、活动 Workflow、媒体参数、规模和当前输出指针 | 给自动检查和编排器提供单一当前状态 | `WF-20/WF-70/WF-80` |
| Schema/采样版本 | 节点、链、文本、媒体字段及采样语义 | 防止不同生成器对同一批次作不同解释 | 图、Prompt、渲染和封装实现 |
| 规格验证证据 | 跨文件一致性检查和受影响测试结果 | 证明上述部分共同组成一个无冲突规格 | `VAL-SPEC-01` 与 `GATE-10` |

当前接受组合由 [WF-10 状态](../project_management/status/workflows/WF-10.md#当前输出与证据) 指定；稳定组成与保留语义见 [输出契约目录](../technical/output/OUTPUT_CONTRACTS.md#32-out-wf10-batch-spec)。

## 6. 必需验证

| 验证 ID | 角色 | 何时需要 |
| --- | --- | --- |
| `VAL-SPEC-01` | `required` | 新批次或批次语义、媒体规格、规模、停止条件变化后 |

定义、证据和通过条件见 [验证目录](../technical/validation/VALIDATION_CATALOG.md)。

## 7. Exit Gate

`GATE-10 BATCH_SPEC_ACCEPTED` 要求目标、轴、规模、输出、停止条件和不包含项均无歧义，且计划与批次状态一致。

## 8. 技术与状态

- [批次规格](../technical/dataset/BATCH_SPECIFICATION.md)
- [数据契约索引](../technical/dataset/README.md)
- [计划索引](../project_management/plans/PLAN_INDEX.md)
- [当前 WF-10 状态](../project_management/status/workflows/WF-10.md)

## 9. 失败与恢复

定义冲突时不进入资产筛选。先在计划中解决目标和成本取舍，再生成新版本批次规格。
