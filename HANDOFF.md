# HANDOFF：当前项目接手说明

> 状态日期：2026-08-20。新会话先读本文件，再读 [`AGENTS.md`](./AGENTS.md) 和 [`README.md`](./README.md)。Character Creator/UE 的唯一总入口是 [`CHARACTER_FACTORY_MASTER_SPEC.md`](./20_planning/data_design/character_creator/full_process/CHARACTER_FACTORY_MASTER_SPEC.md)。

## 当前目标

在 2026-08-26 前完成第一批 UE 多轮视频编辑数据样例：

- 目标 4,000 条、最低 3,000 条编辑链；
- 每条链 3–5 次原子编辑；
- 384 个唯一渲染节点，节点媒体只渲染一次；
- 每条边必须复用真实端点文件，不能重复渲染伪造端点复用。

权威范围和降级规则见 [`FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md`](./20_planning/data_design/character_creator/full_process/planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md)。

## 已冻结输入

| 维度 | 冻结内容 |
| --- | --- |
| BodyFit | `F02_Average`、`M02_Average` |
| 身份 | 每性别 4 个，共 8 个：`F_ID01..04`、`M_ID01..04` |
| 服装 | 每性别 4 套，环形稀疏组合形成 16 个 FullReference Look |
| 女性 O04 | `YogaPants_B + CasualJacket_C + Pump Heel_B` |
| 身体动作 | 女性 6 条、男性 6 条，共 12 个物理动作文件 |
| 动作窗口 | 12/12 个 5 秒窗口已经用户确认并按 SHA-256 冻结 |
| 表情 | Happy、Angry、Sad；F02/M02 各 3 条轻动态 Morph clip |
| 图规模 | `16 Looks × 6 同性动作 × 4 states = 384` 节点 |

本批明确不等待十体型、Headshot 身份迁移、通用模块化换装、道具池、全部动作或三发型完成。

## 已完成能力

- CC 角色工厂已有稳定 Face V3、10 个 BodyFit、服装规则和受控 Bridge。
- 8 个身份、16 个 Look 已确定性组装、保存和导出，最终审计 `16/16` 通过。
- CC→UE FullReference Pilot、F02/M02 身体/面部分层、M02 模块化组件和 Elder Morph 已验证。
- 三表情 UE 机器门禁已通过：`6/6` 运行时案例、`18/18` 图、自动错误 0；动态人工签字仍待完成。
- 配置图生成器已用合成输入确定性生成 384 节点和 4,000 条 3–5 轮链。
- 代码、Markdown、JSON 配置和轻量证据已推送到 GitHub `main`。

完整成熟度以 [`CURRENT_STATUS.md`](./20_planning/data_design/character_creator/full_process/CURRENT_STATUS.md) 为准。

## 尚未完成

1. 完成 Happy/Angry/Sad 动态视觉签字。
2. 导出 12 个 Motion FBX，并在 UE 中完成 Skeleton、Root Motion、时长和抽帧门禁。
3. 将 16 个 FullReference Look 批量导入正式 UE 项目并验证材质、Morph 和 Auto Setup 输出。
4. 固定一个场景、安全角色锚点、固定灯光、两台相机和 Sequence 模板。
5. 把真实 UE 资产 ID 写入配置源，生成正式 384 节点和 4,000 链作业。
6. 实现唯一节点渲染、sidecar、哈希、失败重试和交付验证。
7. 本地跑通一条完整链；服务器完成项目 smoke、10 节点基准和第一批生产。

## 接手后的严格顺序

```text
expression visual signoff
  -> 12 Motion FBX export/import gate
  -> 16 Look UE import gate
  -> scene/camera/sequence freeze
  -> real config graph generation
  -> one local 3-5 turn chain
  -> asset bundle upload
  -> server preflight + 10-node benchmark
  -> batch render
```

场景 ID 未冻结前，不开始全量节点渲染。10 节点基准未通过前，不提交正式批量作业。

## 关键入口

| 工作 | 文档 |
| --- | --- |
| 当前状态与唯一下一步 | [`CURRENT_STATUS.md`](./20_planning/data_design/character_creator/full_process/CURRENT_STATUS.md) |
| 当前 Sprint | [`FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md`](./20_planning/data_design/character_creator/full_process/planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md) |
| 完整角色工厂流程 | [`CHARACTER_FACTORY_MASTER_SPEC.md`](./20_planning/data_design/character_creator/full_process/CHARACTER_FACTORY_MASTER_SPEC.md) |
| 当前代码与资产索引 | [`IMPLEMENTATION_INDEX.md`](./20_planning/data_design/character_creator/full_process/reference/IMPLEMENTATION_INDEX.md) |
| 配置图 schema | [`CONFIG_GRAPH_SCHEMA_V1.md`](./20_planning/data_design/schema/CONFIG_GRAPH_SCHEMA_V1.md) |
| 多轮链采样 | [`MULTI_ROUND_CHAIN_SAMPLING_V1.md`](./20_planning/data_design/sampling/MULTI_ROUND_CHAIN_SAMPLING_V1.md) |
| 服务器 Runbook | [`FIRST_BATCH_SERVER_RUNBOOK.md`](./20_planning/implementation/FIRST_BATCH_SERVER_RUNBOOK.md) |
| 自动预检脚本 | [`FIRST_BATCH_SERVER_PREFLIGHT.sh`](./20_planning/implementation/FIRST_BATCH_SERVER_PREFLIGHT.sh) |
| 一周工作汇报 | [`WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md`](./20_planning/data_design/character_creator/full_process/history/reports/WEEKLY_REPORT_2026-08-13_TO_2026-08-19.md) |

## 本地与服务器边界

- 本地 Windows：运行 CC5、UE Editor、资产导入、人工视觉检查和轻量自动化。
- 服务器 Linux：运行 UE 5.8 离屏 smoke、基准和批量渲染。
- Git：只同步代码、文档、JSON、manifest、哈希和轻量证据。
- 独立资产包：同步 CC/UE 二进制资产、正式 UE `Content/` 和项目工作副本。

服务器工作目录约定：

```text
/scratch/prj0000000275/jcy/xks/DataMake
```

Reallusion Auto Setup 2.03 的 `RLPlugin` 是 Win64 导入辅助；Linux 生产包通常不带该二进制插件，但保留导入后生成的 `Content/CC_Shaders` 和角色资产。任何例外必须先通过服务器项目 smoke。

## 服务器接手

仅更新 Git 内容：

```bash
cd /scratch/prj0000000275/jcy/xks/DataMake
git pull --ff-only origin main
```

资产包尚未上传时可以先跑环境预检：

```bash
bash 20_planning/implementation/FIRST_BATCH_SERVER_PREFLIGHT.sh --environment-only
```

项目和资产上传后，再按 [`FIRST_BATCH_SERVER_RUNBOOK.md`](./20_planning/implementation/FIRST_BATCH_SERVER_RUNBOOK.md) 执行项目 smoke 和 10 节点基准。

## 停止条件

- CC 未知弹窗或 Undo 错误；
- CC private memory 达到 24 GB；
- UE 崩溃、资产哈希漂移、Skeleton/Morph/材质门禁失败；
- 真实源与冻结 manifest 不一致；
- Vulkan/驱动/插件/大小写路径预检失败；
- 渲染出现角色穿模、构图错误、黑帧或端点不一致。

遇到停止条件应保存日志和证据，不得自动猜测或绕过门禁。
