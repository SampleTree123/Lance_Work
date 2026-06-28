# HANDOFF —— 项目接续上下文

> 新会话先读本文件，再读 [`AGENTS.md`](./AGENTS.md) 和 [`README.md`](./README.md)。

## 一句话项目

DataMake 为**多轮视频编辑模型**构建训练/验证数据集。本仓库只做数据构建、研究记录和外部能力验证，不做模型训练。

当前主攻：**Unreal Engine 合成视频数据**，用配置图生成精确配对编辑样本。

## 当前状态

- 工作区路径：`/scratch/prj0000000275/jcy/xks/DataMake`。
- 本地 Git 已初始化，分支 `main`，已有 baseline commit。
- 尚无 UE 工程、渲染脚本、资产台账或样本数据。
- 管理员确认不能使用 `/local`，当前阶段所有工作都在 DataMake 目录下完成。
- Lance 已读 GitHub / 论文 / HF 文件清单，但权重尚未下载。
- BAGEL 只登记来源，暂未深读。

## 核心数据模型

- 配置：`C = {身份, 服装, 动作, 表情, 场景, 道具/配饰, 相机, 光照, 天气/特效, 风格}`。
- 节点：确定性渲染 `render(C)`。
- 边：原子编辑 `C -> C'`。
- 单轮样本：`(video_in, instruction, video_out)`。
- 多轮链：配置图路径 `C0 -> C1 -> C2 -> ...`。
- 硬约束：**端点复用**，上一轮 `video_out` 必须就是下一轮 `video_in` 文件。

详细设计见 [`01_data_design/`](./01_data_design/README.md)。

## 当前目录地图

| 路径 | 内容 |
|------|------|
| `00_project/` | 项目运行、存储、环境、风险 |
| `01_data_design/` | 数据模型、edit taxonomy、schema、采样 |
| `02_research/` | 论文、外部项目、UE harness/MCP 调研 |
| `10_sources/` | 三类数据来源：真实视频、大模型生成、UE 合成 |
| `10_sources/unreal_engine/render/` | 当前 UE MVP 主线 |
| `30_experiments/` | 外部模型能力验证 |
| `30_experiments/external_models/lance_validation_plan.md` | Lance 验证计划 |
| `90_compliance/` | 许可证、资产合规、发布约束 |
| `99_archive/discussions/` | 讨论归档 |

## 服务器与存储

- 当前目录在 `/scratch` 上；清理后曾有约 897G 可用，执行前重新 `df -h .`。
- 当前布局见 [`00_project/storage.md`](./00_project/storage.md)：
  - `external/UE_5.8/`：UE 引擎。
  - `external/repos/`：外部项目代码。
  - `external/models/`：模型权重。
  - `external/hf_cache/`：Hugging Face cache。
  - `.ue_cache/ddc/`：UE DDC。
  - `.ue_cache/tmp/`：临时目录。
  - `ue_projects/`：UE MVP 工程。
  - `outputs/mvp/` 和 `outputs/model_validation/`：少量验证输出。
- `external/`、`.ue_cache/`、`outputs/`、模型权重、UE 产物不进 Git。

历史服务器记录在 [`00_project/environment.md`](./00_project/environment.md) 和 [`00_project/risks.md`](./00_project/risks.md)。执行前必须重新检查 `nvidia-smi`、`vulkaninfo`、`ldd`、UE 版本和 SLURM 限制。

## 已定策略

- 当前主攻 UE 5.8 合成；UE5.6 调研只作历史参考。
- UE 生产流水线使用官方 Python + Automation Test Framework + MRQ/MRG 自建薄 harness。
- 第三方 Unreal MCP/agent 工具只作为编辑器辅助，不进入集群批渲核心链路。
- MVP 首选低风险编辑：E8 光照、E5 道具可见性、E6 配饰可见性或 E11 表情。
- E1 身份、E2 服装较难，放到基础闭环之后。
- 原型资产可 `prototype-only`，但不能进入发布或训练数据。

## 最近下一步

1. 确认是否下载 Lance 视频分支权重并建立 `xks_lance`。
2. 按 [`00_project/storage.md`](./00_project/storage.md) 创建实际工作目录。
3. 重新确认 UE 5.8 Linux 包、Vulkan、依赖和 SLURM。
4. 在 [`10_sources/unreal_engine/render/`](./10_sources/unreal_engine/render/README.md) 写 MVP 最小脚本/伪代码骨架。
5. MVP 通过后，把 schema v0 迁到 [`01_data_design/schema/`](./01_data_design/schema/README.md)，并把三轮链/环一致性写入 [`01_data_design/sampling/`](./01_data_design/sampling/README.md)。

## Agent 备忘

- 接手先跑 `git status --short`。
- 不要下载或提交大文件，除非用户明确确认。
- 旧讨论只作背景；稳定结论以正式分支文档为准。
- Lance 权重未下载；不要整 HF 仓库拉 demo assets，只下视频验证所需文件。
