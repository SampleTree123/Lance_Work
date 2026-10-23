# WF-90 QA、封装与发布

> 文档 ID：`WF-90`
> 文档类型：`workflow`
> 生命周期：`current`
> 前序：`WF-80`
> 后序：无
> Exit Gate：`GATE-90 DATASET_RELEASED`
> 最近核验：2026-08-31

## 1. 目的与使用时机

把媒体、图、链、Prompt、GT、Sidecar、哈希和验收证据汇聚成一个可交付、可验证、可恢复的数据包。

## 2. 前后序与进入条件

- 前序：`WF-80`；后序：无，发布完成后回到 `WF-10` 定义新批次。
`GATE-80` 通过，所有正式节点媒体已经完成且版本唯一。

## 3. 输入

配置图、链、Prompt、媒体清单、GT、Sidecar、软件/资产版本、运行报告和人工抽检决定。

## 4. 正常流程

| 步骤 | 操作 | 精确实现或机器入口 | 当前实现状态 | 本步输出 |
| --- | --- | --- | --- | --- |
| 1. 解析媒体引用 | 将 Nodes、Chains、Turns/Dialogs 的相对 URI 解析到 accepted Node Media | `build_first_batch_delivery_v1.py`；字段和布局由 [数据集封装](../technical/rendering_release/DATASET_PACKAGE.md) 与 [Prompt Technical](../technical/dataset/PROMPT_LAYER.md) 定义 | 4,000 链、15,000 Turn 与 640 accepted 媒体零悬空引用检查通过 | 零悬空引用报告 |
| 2. 验证 GT/Sidecar/哈希 | 比对 Node 配置、UE 实际绑定、媒体规格、SHA-256 和 attempt 状态 | [发布封装器](../../../../../00_engine/scripts/dataset/build_first_batch_delivery_v1.py) 在物化每个编号视频前执行硬检查 | 640/640 通过；视频 SHA-256 和源硬链接已独立复核为零差异 | 节点完整性报告 |
| 3. 执行 QA | 运行结构、统计、媒体和分层人工抽样检查 | 本机/异机 package-only 入口为 [`verify_first_batch_delivery_v1.py`](../../../../../00_engine/scripts/dataset/verify_first_batch_delivery_v1.py)；稳定 Gate 见 [Validation Catalog](../technical/validation/VALIDATION_CATALOG.md)，领域标准见 [视觉审查](../technical/validation/VISUAL_REVIEW.md) | 本机全量机器 QA、完整/简化链 package-only 验证、13 视频分层视觉抽样、用户签字及 `JDS9B74/job118880` 独立全包验证通过 | QA 报告与人工决定 |
| 4. 构建交付包 | 生成 `videos/<编号>.mp4`、完整 `chains.json`、训练 `chains_simple.json` 和追溯 `manifest.json` | `build_first_batch_delivery_v1.py`；目标结构见 [数据集封装](../technical/rendering_release/DATASET_PACKAGE.md#1-交付结构) | `%OUTPUT_ROOT%/delivery/first_batch_candidate_20260830_v002/dataset_v1/` 已构建并晋升为 `released` | 不可变 Release |
| 5. 冻结发布 | 分配 `release_id`，验证另一机器可复核并更新 Batch/Plan/里程碑 | 当前版本所有者为 [WF-90 状态](../project_management/status/workflows/WF-90.md) 和 [Batch Status](../project_management/status/batches/README.md) | `completed`；发布决定见 `release_evidence/release_qa/release_decision_20260831.json` | `OUT-WF90-DATASET-RELEASE` |

本阶段已完成。2026-08-31，候选在独立节点通过全包验证，Manifest 仅将状态晋升为 `released`；随后发布态再次通过相同全包验证。链、简化链和全部视频内容未因晋升改变，`VAL-RELEASE-01` 与 `GATE-90` 已关闭。

## 5. 输出契约

| 输出 ID | 逻辑产物 | 存储类别 | 生产所有者 |
| --- | --- | --- | --- |
| `OUT-WF90-DATASET-RELEASE` | 版本化交付包、QA 报告、发布 Manifest、Checksums 和保留/清理清单 | `delivery`，不可原地覆盖 | [数据集封装](../technical/rendering_release/DATASET_PACKAGE.md) |

### 输出组成、用途与下游

| 组成 | 实际内容 | 为什么需要 | 下游消费者 |
| --- | --- | --- | --- |
| `manifest.json` | Batch/Release、输入版本、Node 配置、编号映射、媒体/Sidecar 哈希和 QA 状态 | 提供交付包单一追溯入口 | 用户、训练系统和独立审计 |
| `chains.json` | 链事实、Node 配置、正式双语 Prompt、独立 Prompt、Grounding 和输入/输出视频路径 | 保存多轮编辑监督语义 | 数据加载器和模型训练 |
| `chains_simple.json` | 从 1 连续编号的链、Hash 追溯 ID 和每轮输入视频/双语指令/输出视频 | 提供精简训练输入，不携带验证元数据 | 数据加载器和模型训练 |
| `videos/<编号>.mp4` | 每个内部 `node_id` 的唯一 accepted 媒体 | 让多条链复用节点，同时提供简短文件名 | Turn 媒体解析 |

当前正式发布位于 `%OUTPUT_ROOT%/delivery/first_batch_candidate_20260830_v002/dataset_v1/`；为保持候选身份和所有既有引用，物理目录名未改，权威 Manifest 状态为 `released`。准确状态和 QA 证据由 [WF-90 状态](../project_management/status/workflows/WF-90.md#当前输出与证据) 指定。稳定组成、不可变性和保留语义见 [输出契约目录](../technical/output/OUTPUT_CONTRACTS.md#310-out-wf90-dataset-release)。

## 6. 必需验证

| 验证 ID | 角色 | 何时需要 |
| --- | --- | --- |
| `VAL-RELEASE-01` | `required` | 每个发布候选都必须独立执行，不能继承旧发布结果 |

定义、证据和通过条件见 [验证目录](../technical/validation/VALIDATION_CATALOG.md)。

## 7. Exit Gate

`GATE-90 DATASET_RELEASED` 要求媒体、链、文本和元数据零悬空引用，哈希一致，全部必需 QA 通过，人工抽检已签字，发布包可在另一台机器独立验证。

当前批次已于 2026-08-31 满足上述全部条件，Gate 结果为 `passed`。

## 8. 技术与状态

- [数据集封装](../technical/rendering_release/DATASET_PACKAGE.md)
- [验证索引](../technical/validation/README.md)
- [当前 WF-90 状态](../project_management/status/workflows/WF-90.md)

## 9. 失败与恢复

发布前失败返回对应生产阶段修复并生成新版本。发布后发现错误不得覆盖既有版本，必须撤回并发布带新 ID 的修正版。
