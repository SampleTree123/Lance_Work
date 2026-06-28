# DataMake —— 多轮视频编辑数据集构建工作区

> 本文件是项目总览。换会话先读 [`HANDOFF.md`](./HANDOFF.md)，再读 [`AGENTS.md`](./AGENTS.md)。

## 1. 项目定位

DataMake 只负责**多轮视频编辑模型的数据集构建**，不负责模型训练。目标数据形态是：

```text
video_in + instruction -> video_out
video_0 -> video_1 -> video_2 -> ...
```

当前主攻来源是 **Unreal Engine 合成视频数据**。真实视频和大模型生成数据保留为后续来源；Lance/BAGEL 等外部模型验证用于判断现有能力和反推数据需求。

## 2. 核心数据模型

把一个镜头建模为配置：

```text
C = {角色, 服装, 动作, 表情, 场景, 道具/配饰, 相机, 光照, 天气/特效, 风格}
render(C) -> video
```

- 节点：确定性渲染的视频。
- 边：一次原子编辑 `C -> C'`，通常只改一个因子。
- 单轮样本：`(render(C), instruction, render(C'))`。
- 多轮样本：配置图上的路径 `C0 -> C1 -> C2 -> ...`。
- 硬约束：**端点复用**。一条边的 `video_out` 必须就是下一条边的 `video_in` 文件。

详细设计见 [`01_data_design/`](./01_data_design/README.md)。

## 3. 当前目录结构

```text
DataMake/
├── README.md
├── HANDOFF.md
├── AGENTS.md
├── .gitignore
├── 00_project/                 # 项目运行：存储、环境、风险
│   ├── README.md
│   ├── storage.md
│   ├── environment.md
│   └── risks.md
├── 01_data_design/             # 数据设计：配置图、taxonomy、schema、sampling
│   ├── README.md
│   ├── schema/README.md
│   └── sampling/README.md
├── 02_research/                # 论文、外部项目、工具调研
│   ├── README.md
│   ├── papers/
│   │   ├── lance.md
│   │   └── bagel.md
│   └── tools/
│       └── unreal_harness_survey.md
├── 10_sources/                 # 数据来源
│   ├── README.md
│   ├── real_video/README.md
│   ├── model_generated/README.md
│   └── unreal_engine/
│       ├── README.md
│       ├── pipeline_research_memo.md
│       └── render/
│           ├── README.md
│           └── cluster_deploy_and_mvp.md
├── 30_experiments/             # 实验与能力验证
│   ├── README.md
│   └── external_models/
│       ├── README.md
│       └── lance_validation_plan.md
├── 90_compliance/              # 许可证、资产和发布约束
│   ├── README.md
│   └── licensing_compliance.md
└── 99_archive/                 # 讨论和历史归档
    ├── README.md
    └── discussions/
        ├── README.md
        ├── 01_character-and-outfit-sources.md
        ├── 02_facial-expressions.md
        ├── 03_body-action.md
        └── 04_2026-06-27-meeting.md
```

## 4. 当前主线

1. **UE MVP**：在 [`10_sources/unreal_engine/render/`](./10_sources/unreal_engine/render/README.md) 打通一对前后编辑配对：`render(C) -> edit -> render(C') -> GT -> sidecar`。
2. **Lance 验证**：按 [`30_experiments/external_models/lance_validation_plan.md`](./30_experiments/external_models/lance_validation_plan.md) 决定是否下载视频分支权重并测试 `video_edit` / 多轮一致性。
3. **schema 收敛**：MVP 后把样本 schema v0 迁到 [`01_data_design/schema/`](./01_data_design/schema/README.md)。
4. **采样策略**：把三轮编辑链、回退/成环一致性写入 [`01_data_design/sampling/`](./01_data_design/sampling/README.md)。

## 5. 目录规则

- 顶层按职责分区，不按临时任务堆文件。
- 每个长期目录必须有 `README.md`。
- 文档正文默认中文，文件名默认英文。
- 外部事实要带日期；UE 版本、许可证、模型权重、服务器环境执行前重新核实。
- 大文件、模型权重、UE 安装、缓存和输出不进 Git。路径约定见 [`00_project/storage.md`](./00_project/storage.md)。
- 讨论放在 [`99_archive/discussions/`](./99_archive/discussions/README.md)，稳定结论必须回写正式文档。

## 6. 决策日志

| 日期 | 决策 | 理由 |
|------|------|------|
| 2026-06-29 | **目录结构重组为长期工作区**：确立 `00_project/`、`01_data_design/`、`02_research/`、`10_sources/`、`30_experiments/`、`90_compliance/`、`99_archive/` 七个主分支 | 后续工作不只有 UE；需要把项目运行、数据设计、研究、数据来源、实验、合规和讨论归档分开 |
| 2026-06-28 | **建立本地 Git 基线**：当前目录是本地 Git 仓库，分支 `main`；文档、规划和规则进入版本控制，大文件由 `.gitignore` 排除 | 后续会持续改文档、脚本和实验计划，需要可回滚、可 diff、可 review |
| 2026-06-28 | **UE harness 采用策略**：生产流水线不依赖第三方 MCP/agent 工具；使用 UE 官方 Python + Automation Test Framework + MRQ/MRG 自建薄 harness | 配置图、确定性渲染、端点复用和 sidecar 必须由可审计脚本保证 |
| 2026-06-28 | **存储改为单目录工作区**：管理员确认不能使用 `/local`；UE、DDC、模型验证权重/cache 和少量输出都放在当前 DataMake 下 | 当前 `/scratch` 空间足够 MVP 和单模型验证；网络盘小文件 I/O 较慢但可接受 |
| 2026-06-28 | **Codex 接手文档治理**：新增 `AGENTS.md`，用 `HANDOFF.md` 承载可移植上下文 | 后续主要由 Codex 协助，需要稳定项目规则 |
| 2026-06-19 | **数据组织为配置图**：确定性渲染节点 + 原子编辑边 + 端点复用 + 随机游走 | 让多轮链成为训练侧路径采样，避免重复渲染完整链 |
| 2026-06-19 | **E1-E11 全部在范围**，动作拆为 E3 肢体动作与 E11 面部表情 | 编辑 taxonomy 要覆盖目标能力；表情机制不同且容易对齐 |
| 2026-06-19 | **当前主攻 UE 5.8 引擎合成**，真实视频和大模型生成后续展开 | 引擎合成能提供其他来源拿不到的精确配对监督 |

## Agent 备忘

- 当前执行入口：[`HANDOFF.md`](./HANDOFF.md)。
- 当前 MVP 入口：[`10_sources/unreal_engine/render/README.md`](./10_sources/unreal_engine/render/README.md)。
- Lance 权重未下载；下载前先确认只下视频分支和 `xks_lance` 环境。
- 提交前先看 `git status --short`，不要把 `external/`、`.ue_cache/`、`outputs/`、模型权重或 UE 产物加入版本控制。
