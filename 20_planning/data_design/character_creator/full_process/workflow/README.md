# 生产 Workflow 索引

> 文档 ID：`WF-INDEX`
> 文档类型：`workflow_index`
> 生命周期：`current`
> 权威范围：长期生产阶段、顺序和 Gate 导航
> 最近核验：2026-08-25

## 唯一主线

```text
WF-00 Environment Preflight
  -> WF-10 Batch Definition
  -> WF-20 Asset Matrix Freeze
  -> WF-30 CC Build and Accept
  -> WF-40 CC to UE Transfer
  -> WF-50 UE Runtime and Performance
  -> WF-60 Scene, Camera and Sequence
  -> WF-70 Graph, Chain, Prompt and Jobs
  -> WF-80 Render Execution
  -> WF-90 QA, Package and Release
```

| ID | 阶段 | Gate |
| --- | --- | --- |
| [`WF-00`](./WF-00-ENVIRONMENT-PREFLIGHT.md) | 环境与会话预检 | `GATE-00 SESSION_READY` |
| [`WF-10`](./WF-10-BATCH-DEFINITION.md) | 批次定义 | `GATE-10 BATCH_SPEC_ACCEPTED` |
| [`WF-20`](./WF-20-ASSET-MATRIX-FREEZE.md) | 资产与矩阵冻结 | `GATE-20 MATRIX_FROZEN` |
| [`WF-30`](./WF-30-CC-BUILD-ACCEPT.md) | CC 组装与验收 | `GATE-30 CC_ASSETS_ACCEPTED` |
| [`WF-40`](./WF-40-CC-UE-TRANSFER.md) | CC→UE 传输 | `GATE-40 UE_REFERENCE_ACCEPTED` |
| [`WF-50`](./WF-50-UE-RUNTIME-PERFORMANCE.md) | UE 运行时与表演 | `GATE-50 PERFORMANCE_ACCEPTED` |
| [`WF-60`](./WF-60-SCENE-CAMERA-SEQUENCE.md) | 场景、相机与 Sequence | `GATE-60 SEQUENCE_ACCEPTED` |
| [`WF-70`](./WF-70-GRAPH-CHAIN-PROMPT-JOBS.md) | 图、链、文本与作业 | `GATE-70 JOB_GRAPH_ACCEPTED` |
| [`WF-80`](./WF-80-RENDER-EXECUTION.md) | 渲染执行 | `GATE-80 MEDIA_COMPLETE` |
| [`WF-90`](./WF-90-QA-PACKAGE-RELEASE.md) | QA、封装与发布 | `GATE-90 DATASET_RELEASED` |

## 使用规则

1. 新会话始终先执行 `WF-00`。
2. 新批次从 `WF-10` 开始；已冻结批次可以从其状态记录的未完成阶段继续。
3. Workflow 说明生产顺序，不代替 Technical 实现。
4. 每个 Gate 同时要求机器检查和适用的人工验收。
5. 修改系统能力时先更新计划和 Technical，验证通过后才能升级 Workflow 状态。
6. 当前阶段和唯一下一步只看 [项目状态](../project_management/status/PROJECT_STATUS.md)。
