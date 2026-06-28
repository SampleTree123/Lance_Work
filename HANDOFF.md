# HANDOFF —— 项目接续上下文（读我第一）

> 本文件是 DataMake 的可移植项目上下文，不是逐字聊天记录。
> 新会话或换环境时，先读这里，再按链接深入具体文档。

## 如何接续

1. 读本文件，确认当前状态、核心模型、风险和下一步。
2. 读 [`AGENTS.md`](./AGENTS.md)，确认 Codex 在本项目里的长期工作约定。
3. 读 [`README.md`](./README.md)，查看目录树和全局决策日志。
4. 按任务深入 `00_planning/`、`30_engine_synth/`、`discussions/`、`90_meta/`。
5. 每次形成稳定结论时，同步更新相关正式文档和顶层决策日志。

---

## 一句话项目

为**多轮视频编辑专家模型**造配套数据集（仅数据构建，不含训练）。三来源：真实视频数据集 / 大模型生成 / **引擎合成（Unreal Engine，当前主攻）**。文本指令后续可由已知编辑因子自动生成，当前主攻是视频数据。外部论文和模型验证服务于基线能力判断与数据需求反推，不把本目录扩展成训练仓库。

## 当前阶段与状态

**Codex 接手时间：2026-06-28。**

- 当前目录主要是前期规划文档，还没有 UE 工程、自动化渲染脚本、资产台账或样本数据。
- 前期可行性分析已完成，结论是“绿灯，但必须先跑 MVP 验证”。见 [`00_planning/feasibility_and_risks.md`](./00_planning/feasibility_and_risks.md)。
- 工作目标从“继续调研”转为“整理基线 → 准备 UE/MVP 落地 → 外部模型基线验证”。
- 当前工作区已初始化为本地 Git 仓库，分支 `main`。文档基线已提交；后续改动先看 `git status --short`，不要把大文件或缓存加入版本控制。
- Unreal 目标版本在 2026-06-19 文档中已转向 **UE 5.8**，但所有“最新版本 / hotfix / 发布状态 / 许可证”类外部事实在安装或引用前必须重新核实。
- `30_engine_synth/pipeline_research_memo.md` 保留了大量 UE 5.6 调研结论；它是历史技术备忘，不应覆盖后来关于 UE 5.8 的部署决策。
- **存储最新决定（2026-06-28）**：管理员确认不能使用 `/local`；当前阶段所有 UE 安装、DDC、MVP 工程、外部模型验证权重/cache 和少量输出都放在本目录 `/scratch/prj0000000275/jcy/xks/DataMake` 下。清理后 `/scratch` 当前约 `897G` 可用，足够 MVP 和 Lance 这类单模型验证。
- **研究/模型验证最新状态（2026-06-28）**：已新增 `05_research/` 与 `40_model_validation/`。Lance 已读 GitHub + 论文 + HF 文件清单，建议先验证 `video_edit` 与多轮一致性；BAGEL 只登记来源，暂未深读。Lance 权重尚未下载。
- **UE harness 最新结论（2026-06-28）**：没有直接可用的成熟 dataset harness。生产流水线用 UE 官方 Python + Automation Test Framework + MRQ/MRG 自建薄 harness；Unreal MCP/agent 工具只作为编辑器辅助。

## 最近的下一步

1. 用户确认后，按 [`40_model_validation/lance_validation_plan.md`](./40_model_validation/lance_validation_plan.md) 决定是否下载 Lance 视频分支权重并建立 `xks_lance`。
2. 按 [`00_planning/filesystem_usage.md`](./00_planning/filesystem_usage.md) 在 DataMake 下创建 `external/`、`.ue_cache/`、`ue_projects/`、`outputs/`。
3. 现场重新确认 UE 5.8 Linux 包、驱动/Vulkan、`ldd UnrealEditor-Cmd` 依赖、SLURM 分区/时限。
4. 在 `30_engine_synth/33_render/` 下先写最小脚本/伪代码骨架，而不是先扩目录。
5. MVP 首选 E8 光照、E5 道具可见性、E6 配饰可见性或 E11 表情；E2 服装和 E1 身份较难，放在闭环跑通之后。

## 核心数据模型（设计基石）
- 镜头 = 因子配置 `C { 身份 / 服装 / E3肢体动作 / E11表情 / 场景 / 道具 / 配饰 / 相机 / 光照 / 天气 / 风格 }`；`渲染(C)` = 一段视频。
- 编辑 = 配置图里**只改一个因子**的"边" `C→C'`；训练样本 = `(video_in, 指令, video_out)`。
- **端点复用**（一条边的输出视频 = 下条边的输入**文件**）→ 多轮链 = **训练侧路径采样**，链长/比例数据侧不固定；沿**随机游走**渲染最省。**端点复用是后期补不回来的硬约束。**
- 编辑类型 **E1–E11**（详见 `00_planning/README.md` taxonomy）；E3 肢体动作与 E11 面部表情已拆分。

## 风格域框架（让"多风格"可行）
- 角色按 humanoid **风格域**分区：**写实**(MetaHuman/UE5骨架) / **动漫**(VRM·VRoid) / **卡通**(RPM/Quaternius)。
- 铁律：**编辑只在同一风格域内发生**。渲染/GT/配置图这套"机器"与风格无关、**写一次通用**；每域只单独做"资产前处理"。
- 刻意排除：非人形角色；**引擎内跨风格变换**（写实↔动漫，交给大模型生成来源）。

## 服务器 / 环境
- **历史记录（2026-06-19）**：HPC 集群疑似 ACRC/Bright/WekaFS，用户 `stuchengyou`，主机 `GDS9B74`，1×NVIDIA H200(144G)，Ubuntu 22.04，glibc 2.35，内核 5.15，2TB RAM。
- **历史 Vulkan 检查（2026-06-19）**：`vulkaninfo` 曾列出 H200、Vulkan 1.3.289；SM6/Nanite 扩展齐全；ICD 在 `/etc/vulkan/icd.d/nvidia_icd.json`，库在 `/cm/local/apps/cuda/libs/`。安装 UE 或跑渲染前必须重新检查，不能只依赖旧记录。
- **无需 root / Docker**；Apptainer 1.3.4 + enroot 可作可选兜底。
- **存储（2026-06-28 最新决定）**：
  - 管理员确认不能使用 `/local`。
  - 当前 DataMake 实际路径：`/scratch/prj0000000275/jcy/xks/DataMake`。
  - 当前 `/scratch` 文件系统清理后约 `897G` 可用，足够 UE5.8 安装、DDC 和 MVP 小规模输出。
  - 统一布局：`external/UE_5.8/` 放引擎，`external/repos/` 放外部项目代码，`external/models/` 放模型权重，`external/hf_cache/` 放 HF cache，`.ue_cache/ddc/` 放 DDC，`.ue_cache/tmp/` 放临时文件，`ue_projects/` 放 MVP 工程，`outputs/mvp/` 和 `outputs/model_validation/` 放少量验证输出。
  - 风险：这是 WekaFS/网络盘，小文件 I/O 可能慢；先接受该限制，控制并发和输出规模。正式大规模数据生产或多模型大规模评测另行规划。
- **约束**：SLURM 单任务**最多 18h 占卡** → 大批量渲染拆 **job-array + 断点续跑**（MVP 不受影响）。**conda 环境名必须加 `xks_` 前缀**。
- **引擎获取**：用户**有 Epic 账号** → 连 GitHub 下 UE5.8 官方 Linux 编辑器包、**解压即用、无 root**。
- **本机创作端**：Windows **笔记本 RTX 4080(12G) + 32G RAM**，够 UE 场景创作/迭代/小测渲。**分工倾向：本机创作（GUI 顺、无 18h 限）+ 集群 H200 无头批渲**，服务器 Editor Streaming 仅作远程调试后备。
- ⚠️ 不要假设当前 Codex 会话一定运行在创作机或服务器上。每次执行现场命令前先确认 `pwd`、`hostname`、`nvidia-smi`、`vulkaninfo`。

## 待用户拍板
- 创作端最终定（倾向：本机创作 + 集群渲）。
- 风格域具体构成（先做哪几个域、"100 角色"在各域配比）。
- edit taxonomy 是否还要增减；各域"20 动作"具体清单。

## 关键已定决策（全量见 `README.md` 第 7 节决策日志）
- 仅做数据集，不含训练；当前主攻引擎合成视频。
- 数据 = **配置图 + 端点复用 + 沿游走渲染**；多轮链=训练侧采样。
- **E1–E11 全做**，渐进推进；"动作"拆 E3 肢体 / E11 表情。
- **风格域分区**（域内合成、域间大模型）。
- **公开发布 + 安全资产**为最终目标，但**版权暂缓**：原型临时资产可用于内部管线验证，但必须标 `prototype-only`，不得进入发布/训练集；发布前收口（见 `90_meta/`）。
- 引擎 **UE 5.8**（原型 5.8.0；大批量等首个 5.8.x hotfix；5.7 回退）；MetaHuman 创作在 Windows、Linux 无头批渲。

## 文件地图
| 路径 | 内容 |
|------|------|
| `AGENTS.md` | Codex 自动读取的项目规则 |
| `README.md` | Level 0 总览 / 文档约定 / 实时文件树 / **决策日志全量** |
| `HANDOFF.md` | 本文件 —— 接续入口（可移植记忆） |
| `00_planning/README.md` | 任务定义 / 核心数据模型 / **edit taxonomy E1–E11** / 多样性矩阵 |
| `00_planning/environment_infra.md` | UE版本/服务器/远程UI/配套软件/同步（调研稿） |
| `00_planning/feasibility_and_risks.md` | **可行性与风险 / go 判定 / 风险登记**（含服务器自检结论） |
| `00_planning/filesystem_usage.md` | **当前单目录存储布局**（不能用 `/local` 后的 DataMake 工作区方案） |
| `05_research/README.md` | 论文、外部项目、UE harness/MCP 调研索引 |
| `05_research/lance.md` | Lance 项目和论文阅读笔记 |
| `05_research/bagel.md` | BAGEL 来源登记（暂未深读） |
| `05_research/unreal_harness_survey.md` | UE automation / MCP / harness 调研与采用建议 |
| `30_engine_synth/README.md` | 引擎合成主攻分支总览 + 服装适配后账 |
| `30_engine_synth/pipeline_research_memo.md` | UE5.6 起步的合成管线技术备忘（历史调研稿，需结合 UE5.8 决策阅读） |
| `30_engine_synth/33_render/README.md` | **渲染/自动化 / MVP 最小闭环方案 / 样本 schema v0** |
| `30_engine_synth/33_render/cluster_deploy_and_mvp.md` | **集群部署 + MVP 启动计划**（命令级：装 UE5.8 / 无头渲染 / SLURM / 同步） |
| `40_model_validation/README.md` | 外部模型能力验证规则与索引 |
| `40_model_validation/lance_validation_plan.md` | Lance 下载、环境、视频编辑/多轮一致性验证计划 |
| `90_meta/licensing_compliance.md` | 许可证合规（暂缓，发布前收口清单） |
| `discussions/01_*` | 人物与服装：来源与适配（含风格域解法、资产生态） |
| `discussions/02_*` | 面部表情（E11，已细化） |
| `discussions/03_*` | 肢体动作（E3，已细化） |

## Agent 备忘

- 历史大调研结果已落入对应文档并标来源/可信度（pipeline_research_memo、environment_infra、discussions 02/03、feasibility）。
- **诚实优先**：服务器 Vulkan 最初**误判为"纯计算驱动"**（按 AI 集群先入为主 + 只查了 `/usr/share/vulkan` 标准路径）→ 教训：**别假设标准路径，broad 查 `ldconfig` + `/etc/vulkan/icd.d`**。已纠正。
- **风险①（确定性/对齐）是数据范式命门**，MVP 必须最先验（关 AA + 空间采样 + 锁种子/时间轴/相机 + warm-up；压不住则退"近似对齐+光流监督"并回写数据模型）。
- Lance 权重未下载；下载前不要整 HF 仓库拉 demo assets，只下 `Lance_3B_Video`、`Qwen2.5-VL-ViT`、`Wan2.2_VAE.pth` 和必要配置。HF cache 指向 `external/hf_cache/`。
- BAGEL 只登记来源，后续深读前不要引用它的论文细节作为已确认结论。
- 本文件随项目目录可移植。换环境时以本文件和 `AGENTS.md` 为准，不依赖任何私有聊天记忆。
