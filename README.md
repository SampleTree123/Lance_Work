# DataMake —— 多轮视频编辑数据集构建工作区

> 新会话先读 [`HANDOFF.md`](./HANDOFF.md)，再读 [`AGENTS.md`](./AGENTS.md)。

## 1. 项目定位

DataMake 用于**多轮视频编辑模型的数据集构建**，不负责模型训练。目标样本形态是：

```text
video_in + instruction -> video_out
video_0 -> video_1 -> video_2 -> ...
```

当前主攻来源是 **Unreal Engine 合成视频数据**。真实视频和大模型生成来源保留为后续规划；Lance/BAGEL 等外部模型验证用于判断现有能力和反推数据需求。

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

详细设计见 [`20_planning/data_design/`](./20_planning/data_design/README.md)。

## 3. 当前目录结构

```text
DataMake/
├── README.md
├── HANDOFF.md
├── AGENTS.md
├── .gitignore
├── 00_engine/                  # 引擎合成：UE、资产、脚本、工程、输出、缓存
│   ├── README.md
│   ├── unreal/
│   ├── assets/
│   ├── scripts/
│   ├── projects/
│   ├── outputs/
│   └── cache/
├── 10_research/                # 论文、外部项目、工具调研、模型能力验证
│   ├── README.md
│   ├── papers/
│   ├── tool_surveys/
│   └── model_experiments/
└── 20_planning/                # 数据设计、实施计划、合规、讨论记录
    ├── README.md
    ├── data_design/
    ├── implementation/
    ├── compliance/
    └── discussions/
```

## 4. 当前主线

1. **UE MVP**：在 [`00_engine/scripts/`](./00_engine/scripts/README.md) 打通一对前后编辑配对：`render(C) -> edit -> render(C') -> GT -> sidecar`。
2. **Lance 验证**：视频分支权重、`xks_lance` 环境和 `video_edit` 脚本已可用；batch8 公开视频三轮链式测试已跑完，记录见 [`10_research/model_experiments/lance/reports/video_edit_batch8_report.md`](./10_research/model_experiments/lance/reports/video_edit_batch8_report.md)。
3. **schema 收敛**：MVP 后把样本 schema v0 迁到 [`20_planning/data_design/schema/`](./20_planning/data_design/schema/README.md)。
4. **采样策略**：把三轮编辑链、回退/成环一致性写入 [`20_planning/data_design/sampling/`](./20_planning/data_design/sampling/README.md)。

## 5. 目录规则

- 顶层只保留三类长期工作：`00_engine/`、`10_research/`、`20_planning/`。
- 每个长期目录必须有 `README.md`；越往子目录越具体。
- 文档正文默认中文，文件名默认英文。
- 外部事实要带日期；UE 版本、许可证、模型权重、服务器环境执行前重新核实。
- 大文件、模型权重、UE 安装、缓存和输出不进 Git。路径约定见 [`20_planning/implementation/storage.md`](./20_planning/implementation/storage.md)。
- 讨论放在 [`20_planning/discussions/`](./20_planning/discussions/README.md)，稳定结论必须回写正式文档和本文件决策日志。

## 6. 决策日志

| 日期 | 决策 | 理由 |
|------|------|------|
| 2026-07-03 | **Lance batch8 测试跑完**：已下载视频分支权重，建立 `xks_lance`，跑通 `video_edit` smoke test，并完成 batch8 中 8 个领域的三轮链式编辑；2 个损坏源视频已用 clean 版补跑 | Lance 用于外部能力基线和失败模式收集，不替代 UE 数据管线；实测结果将反推 UE 编辑类型优先级 |
| 2026-07-03 | **HF cache 采用现有 scratch 全局路径**：继续使用 `/scratch/prj0000000275/jcy/.cache/huggingface`，Lance 可运行权重目录放在项目 `lance/models/Lance/` | 避免重复下载已有 HF cache；模型引用仍保持项目内稳定路径 |
| 2026-07-01 | **UE agent/MCP 采用边界**：UE 5.8 官方 MCP 插件可作为 Codex/Claude/Cursor 等 MCP-capable agent 的编辑器辅助入口；生产数据流水线仍以 UE Python + Automation Test Framework + MRQ/MRG 自建薄 harness 为核心 | UE 5.8 的 MCP 插件是官方 Experimental agent 控制层，但配置图、确定性渲染、端点复用和 sidecar 必须由可审计脚本保证 |
| 2026-07-01 | **目录收敛为三大主分支**：`00_engine/`、`10_research/`、`20_planning/` | 后续主要工作围绕引擎合成、外部资料/模型验证、讨论与实施计划三类展开；更贴合当前协作方式 |
| 2026-06-29 | **建立长期文档工作区** | 将零散规划整理为可接手、可 review、可持续更新的项目文档 |
| 2026-06-28 | **建立本地 Git 基线**：当前目录是本地 Git 仓库，分支 `main`；文档、规划和规则进入版本控制，大文件由 `.gitignore` 排除 | 后续会持续改文档、脚本和实验计划，需要可回滚、可 diff、可 review |
| 2026-06-28 | **UE harness 采用策略**：生产流水线不依赖第三方 MCP/agent 工具；使用 UE 官方 Python + Automation Test Framework + MRQ/MRG 自建薄 harness | 配置图、确定性渲染、端点复用和 sidecar 必须由可审计脚本保证 |
| 2026-06-28 | **存储改为单目录工作区**：管理员确认不能使用 `/local`；UE、DDC、模型验证权重/cache 和少量输出都放在当前 DataMake 下 | 当前 `/scratch` 空间足够 MVP 和单模型验证；网络盘小文件 I/O 较慢但可接受 |
| 2026-06-28 | **Codex 接手文档治理**：新增 `AGENTS.md`，用 `HANDOFF.md` 承载可移植上下文 | 后续主要由 Codex 协助，需要稳定项目规则 |
| 2026-06-19 | **数据组织为配置图**：确定性渲染节点 + 原子编辑边 + 端点复用 + 随机游走 | 让多轮链成为训练侧路径采样，避免重复渲染完整链 |
| 2026-06-19 | **E1-E11 全部在范围**，动作拆为 E3 肢体动作与 E11 面部表情 | 编辑 taxonomy 要覆盖目标能力；表情机制不同且容易对齐 |
| 2026-06-19 | **当前主攻 UE 5.8 引擎合成**，真实视频和大模型生成后续展开 | 引擎合成能提供其他来源拿不到的精确配对监督 |

## Agent 备忘

- 当前执行入口：[`HANDOFF.md`](./HANDOFF.md)。
- 当前 MVP 入口：[`00_engine/scripts/README.md`](./00_engine/scripts/README.md)。
- Lance 视频分支权重已下载，`xks_lance` 可用；后续继续用 `10_research/model_experiments/lance/scripts/run_video_edit.sh` 做真实视频基线验证。
- 提交前先看 `git status --short`，不要把 UE 安装、缓存、输出、模型权重或大型资产加入版本控制。
