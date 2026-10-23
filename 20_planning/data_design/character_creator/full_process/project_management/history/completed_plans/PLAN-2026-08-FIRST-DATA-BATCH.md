# PLAN-2026-08 第一批多轮视频编辑数据

> 文档 ID：`PLAN-2026-08-FIRST-DATA-BATCH`
> 文档类型：`completed_plan`
> 生命周期：`completed`
> 影响阶段：`WF-10..WF-90`
> 完成日期：2026-08-31
> 最近核验：2026-08-31

## 结果

第一批数据完成 CC、UE、配置图、双语文本、H200 正式渲染、QA、封装与独立机器发布验证。最终 `dataset_v1` 保留 640 个顺序编号视频、4,000 条完整链、4,000 条简化链和 15,000 个 Turn；`VAL-RELEASE-01` 在 `JDS9B74/job118880` 上通过候选态与发布态两次全包验证，`GATE-90 DATASET_RELEASED` 于 2026-08-31 关闭。

## 最终需求状态

| ID | 需求 | 影响阶段 | 状态 | 接受证据 |
| --- | --- | --- | --- | --- |
| `R01` | 冻结编辑轴、媒体和交付规格 | `WF-10` | `completed` | [批次状态](../../status/batches/BATCH-001-FIRST-DATA.md) |
| `R02` | 冻结完整 Look、动作、相机和表情策略 | `WF-20` | `completed` | [WF-20 状态](../../status/workflows/WF-20.md) |
| `R03` | 完成 CC Look、Bundle 和 UE FullReference | `WF-30/WF-40` | `completed` | [WF-40 状态](../../status/workflows/WF-40.md) |
| `R04` | 验证动作、表情、材质和防 T-pose | `WF-50` | `completed` | [WF-50 状态](../../status/workflows/WF-50.md) |
| `R05` | 固定场景、四相机和五秒 Sequence | `WF-60` | `completed` | [WF-60 状态](../../status/workflows/WF-60.md) |
| `R06` | 生成并验证图、链、Prompt 和 Render Jobs | `WF-70` | `completed` | [WF-70 状态](../../status/workflows/WF-70.md) |
| `R07` | 实现正式节点执行器、GT、Sidecar、Manifest 和重试 | `WF-80` | `completed` | [WF-80 状态](../../status/workflows/WF-80.md) |
| `R08` | 服务器预检、项目 Smoke 和 10 节点基准 | `WF-00/WF-80` | `completed` | H200/580.126.20 正式 Tokyo MRQ、逐帧确定性、基准、恢复与 50 节点资源边界通过；Vulkan Validation 作为已记录 bounded risk 保留 |
| `R09` | 完整渲染、QA、文本媒体解析和发布包 | `WF-80/WF-90` | `completed` | [WF-90 状态](../../status/workflows/WF-90.md)；`release_evidence/release_qa/release_decision_20260831.json` |

## 发布接受证据

- 发布包：`%OUTPUT_ROOT%/delivery/first_batch_candidate_20260830_v002/dataset_v1/`，Manifest 状态为 `released`。
- 候选态独立验证：`release_evidence/release_qa/package_verification_independent_jds9b74_20260831.json`，SHA-256 `b268012a005cd4c42c33f28a906de782d67cce12de8364e7aa5769d8fe74d4e1`。
- 发布态独立复验：`release_evidence/release_qa/package_verification_released_independent_jds9b74_20260831.json`，SHA-256 `8fb9328f262329d555dcf35be8e97795c9e8dee497a1091cd91ddb5019595a73`。
- 发布决定：`release_evidence/release_qa/release_decision_20260831.json`。
- 不可变内容哈希：`chains.json=f28b0872...0c2d`、`chains_simple.json=afd07d31...ec2d`、有序视频哈希表 `68bec5d6...f51e`。

## 未纳入范围

通用 UE 模块化换装、Headshot 全面替换 Face V3、年龄编辑、道具、多场景、完整表情轴和全部动画资产不属于本计划完成条件。Lance 正式训练属于后续独立计划。
