# Lance_Work / DataMake

用于构建 **Unreal Engine 多轮视频编辑数据集** 的工作仓库。项目当前不训练模型，重点是把 Character Creator 角色资产、Unreal Engine 场景与确定性配置图连接成可审计的数据生产流水线。

> 新会话先读 [`HANDOFF.md`](./HANDOFF.md)，项目规则见 [`AGENTS.md`](./AGENTS.md)。Character Creator 与 UE 主流程从 [`CHARACTER_FACTORY_MASTER_SPEC.md`](./20_planning/data_design/character_creator/full_process/CHARACTER_FACTORY_MASTER_SPEC.md) 进入。

## 数据模型

一个视频节点由确定性配置 `C` 生成：

```text
C = {identity, body_fit, outfit, action, expression, scene, camera, lighting}
render(C) -> video
```

一次原子编辑只改变一个主要因素：

```text
video_0 -> video_1 -> video_2 -> ...
```

每条边形成 `(video_in, instruction, video_out)`；上一轮的 `video_out` 必须直接复用为下一轮的 `video_in`，不能重复渲染替代。

## 当前状态

状态日期：**2026-08-20**。当前唯一活动目标是在 **2026-08-26** 前完成第一批可交付样例。

| 项目 | 当前状态 |
| --- | --- |
| 目标规模 | 目标 4,000 条、最低 3,000 条多轮链；每条 3–5 次原子编辑 |
| 配置图 | `16 Looks × 6 同性动作 × 4 相机/表情状态 = 384` 个唯一节点 |
| 身份与体型 | `F02_Average`、`M02_Average`；每性别 4 个身份，共 8 个 |
| 服装 | 每性别 4 套；16 个 FullReference Look 已保存、导出并通过 `16/16` 审计 |
| 动作 | 女性 6 条、男性 6 条；12 个 5 秒窗口已由用户确认并冻结 |
| 表情 | Happy、Angry、Sad；UE 机器门禁 `6/6` 案例、`18/18` 图通过，动态人工签字待完成 |
| 配置生成 | 已能确定性生成 384 节点和 4,000 条 3–5 轮链；真实场景与 UE 资产 ID 尚待补齐 |
| UE | CC→UE FullReference、身体/面部分层和 Elder Morph 已通过 Pilot |
| 服务器 | 代码、配置和文档已同步 GitHub；二进制资产包、项目 smoke、10 节点基准待完成 |

女性 O04 已冻结为 `YogaPants_B + CasualJacket_C + Pump Heel_B`。本批不等待十体型、Headshot 身份迁移、通用模块化换装、三发型、道具池或全部动画完成。

权威状态以 [`CURRENT_STATUS.md`](./20_planning/data_design/character_creator/full_process/CURRENT_STATUS.md) 为准；本周冻结范围和退出条件以 [`FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md`](./20_planning/data_design/character_creator/full_process/planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md) 为准。

## 当前执行顺序

1. 完成三种表情的动态视觉签字。
2. 导出并在 UE 中门禁 12 个 Motion FBX。
3. 将 16 个 FullReference Look 批量导入正式 UE 项目。
4. 固定单场景、安全角色锚点、两台相机、灯光和 Sequence。
5. 用真实资产生成配置图、节点作业和 4,000 条编辑链。
6. 跑通本地一条完整 3–5 轮链，包括 sidecar、哈希和失败恢复。
7. 同步二进制资产到服务器，执行环境/项目预检和 10 节点基准，再决定 384、288 或 192 节点档位。

## 文档入口

| 想了解什么 | 入口 |
| --- | --- |
| 当前可用能力与唯一下一步 | [`CURRENT_STATUS.md`](./20_planning/data_design/character_creator/full_process/CURRENT_STATUS.md) |
| 本周目标、冻结项和降级规则 | [`FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md`](./20_planning/data_design/character_creator/full_process/planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md) |
| CC 角色工厂完整主流程 | [`CHARACTER_FACTORY_MASTER_SPEC.md`](./20_planning/data_design/character_creator/full_process/CHARACTER_FACTORY_MASTER_SPEC.md) |
| 代码、配置、JSON 和 UE 资产索引 | [`IMPLEMENTATION_INDEX.md`](./20_planning/data_design/character_creator/full_process/reference/IMPLEMENTATION_INDEX.md) |
| 配置图字段 | [`CONFIG_GRAPH_SCHEMA_V1.md`](./20_planning/data_design/schema/CONFIG_GRAPH_SCHEMA_V1.md) |
| 3–5 轮链采样规则 | [`MULTI_ROUND_CHAIN_SAMPLING_V1.md`](./20_planning/data_design/sampling/MULTI_ROUND_CHAIN_SAMPLING_V1.md) |
| 服务器执行说明 | [`FIRST_BATCH_SERVER_RUNBOOK.md`](./20_planning/implementation/FIRST_BATCH_SERVER_RUNBOOK.md) |
| 服务器自动预检 | [`FIRST_BATCH_SERVER_PREFLIGHT.sh`](./20_planning/implementation/FIRST_BATCH_SERVER_PREFLIGHT.sh) |
| 引擎、脚本和产物目录 | [`00_engine/README.md`](./00_engine/README.md) |
| 历史里程碑与证据 | [`MILESTONE_LOG.md`](./20_planning/data_design/character_creator/full_process/history/MILESTONE_LOG.md) |

## 仓库结构

```text
Lance_Work/
├── 00_engine/      # CC/UE 自动化、项目配置、轻量输出和验证工具
├── 10_research/    # 外部模型与工具研究；Lance 实验属于此分支
├── 20_planning/    # 数据设计、当前 Sprint、运行手册、合规与历史决策
├── README.md       # GitHub 总入口
├── HANDOFF.md      # 新会话和服务器接手入口
└── AGENTS.md       # 协作与维护规则
```

## Git 与资产边界

Git 保存代码、Markdown、JSON 配置、manifest、哈希和小型验证证据。以下内容不进入仓库：

- Character Creator 二进制资产与项目，如 `.ccProject`、`.ccAvatar`、`.ccCloth`、`.rlHair`、`.rlMotion`；
- Unreal Engine 的大型 `Content/`、`.uasset`、`.umap`、DDC、缓存和渲染输出；
- 原始人物照片、模型权重和可再生成的大型可视化产物。

这些资产通过独立资产包同步，并按 manifest/hash 与 Git 配置关联。详细约束见 [`storage.md`](./20_planning/implementation/storage.md) 和 [`local_asset_workflow.md`](./20_planning/implementation/local_asset_workflow.md)。

## 快速校验

```powershell
python 00_engine/scripts/documentation/check_character_factory_docs.py --json
python -m pytest 00_engine/scripts/documentation/tests 00_engine/visualization_portal/tests 00_engine/scripts/dataset/tests -q
git status --short
```

服务器预检：

```bash
bash 20_planning/implementation/FIRST_BATCH_SERVER_PREFLIGHT.sh --environment-only
```

Lance/BAGEL 等模型能力验证仍保留在 [`10_research/model_experiments/`](./10_research/model_experiments/README.md)，但不阻塞当前第一批 UE 数据生产。
