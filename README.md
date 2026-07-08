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
│   ├── runtime/
│   ├── assets/
│   ├── scripts/
│   ├── projects/
│   ├── outputs/
│   └── cache/
├── 10_research/                # 学习资料、外部项目、工具调研、模型能力验证
│   ├── README.md
│   ├── study/
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
2. **Lance 验证**：视频分支权重、`xks_lance` 环境和 `video_edit` 脚本已可用；batch8 公开视频连续单轮测试已跑完；contextual v2 真多轮原型已完成 current-only 三轮测试；full-conversation multi-turn chat A 方案已接入但尚未 GPU 验证，记录见 [`10_research/model_experiments/lance/reports/contextual_video_edit_smoke.md`](./10_research/model_experiments/lance/reports/contextual_video_edit_smoke.md)。
3. **schema 收敛**：MVP 后把样本 schema v0 迁到 [`20_planning/data_design/schema/`](./20_planning/data_design/schema/README.md)。
4. **采样策略**：把三轮编辑链、回退/成环一致性写入 [`20_planning/data_design/sampling/`](./20_planning/data_design/sampling/README.md)。
5. **资产存储与台账**：本地只保留预览子集，服务器保留当前批次工作副本，长期素材/冷存储层待正式规模生产前确认；台账 schema 见 [`00_engine/assets/asset_ledger_schema.md`](./00_engine/assets/asset_ledger_schema.md)。

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
| 2026-07-08 | **Lance full-conversation multi-turn chat A 方案已接入待测**：参考 `Jayce-Ping/Lance@8b002b5` 新增 conversation engine 入口；历史 prompt 保留为独立 user turns，不拼入最新 prompt；视觉侧仍采用 DataMake v2 的旧视觉 VIT-only、最新视觉唯一 VAE direct source 策略 | 可以测试真正多轮对话上下文，并允许相邻轮次是不同任务；但避免回到 all-source 多 VAE 条件造成的 source-target 对齐问题 |
| 2026-07-08 | **资产存储改为三层策略**：本地 Laptop 4080/约 400G 只作交互预览层；服务器 DataMake `/scratch` 只作生产工作层；完整资产包、历史版本和正式结果需要长期素材/冷存储层，位置待正式规模生产前确认；新增资产台账 schema | 100+ 角色、多动作、多场景会迅速超过本地和当前工作盘的舒适容量；Git 只保存台账、脚本、配置、hash 和许可证记录，不保存资产本体 |
| 2026-07-08 | **纯 Xvnc 已证明可连但不适合作为完整 UE Editor GUI**：Windows VNC Viewer 通过 reverse tunnel 连接到 GPU 节点 Xvnc 成功，只显示 xterm；UE Editor 可初始化 H200/Vulkan 和项目 map，但在编辑器 UI 后期 SIGSEGV | 远程图形链路本身成立，失败边界在纯用户态 Xvnc 缺少完整 NVIDIA GLX/桌面栈；服务器继续定位为脚本化 UE、MCP/offscreen/MRQ 生产环境，人工图形编辑主要放本地 |
| 2026-07-07 | **用户态 TurboVNC 远程桌面支线已最小跑通**：TurboVNC 3.3 解包到 `00_engine/remote_desktop/`，补齐 `libXfont2`、`xkbcomp`、`xsetroot`；登录节点和 GPU job `101190` / `8FS9B74` 上 `Xvnc + xterm` 可监听 localhost；UE Editor 已确认能进入 H200/Vulkan 初始化 | 在无法联系管理员、集群未暴露 DCV/VNC/xpra module 的情况下，先验证普通用户能否自建远程桌面；UE 5.8 对当前 NVIDIA driver `565.57` 会弹出 bad-driver warning，交互预览脚本用 `r.WarnOfBadDrivers=0` 临时跳过；后续人工 VNC 结论见 2026-07-08 记录，生产数据管线仍以无头脚本为准 |
| 2026-07-07 | **UE MCP/Codex Linux 环境已配置**：`MVPProject` 启用 `ModelContextProtocol`、`Terminal`、`EditorToolset`；`bAutoStartServer=True`；DataMake 根目录 `.codex/config.toml` 作为 Codex canonical MCP 配置；已生成 `.mcp.json`、Cursor、VSCode、Gemini、Codex client config；非沙箱验证确认 MCP listener 可绑定 `127.0.0.1:8000/mcp` | 对齐用户 Windows 下的 UE agent 配置；Codex 可作为编辑器辅助和原型探索入口，并可覆盖未来多个 UE project；生产数据流水线仍用可审计的 UE Python/MRQ/MRG 脚本 |
| 2026-07-07 | **UE GPU/Python smoke 通过**：在 Slurm job `99943` / node `8FS9B74` 上确认 H200 driver `565.57.01`；UE 日志确认 `rhiname="Vulkan"`、`gpu="NVIDIA H200"`；新增 `MVPProject` 和 `run_mvp_python_smoke.sh`，`nullrhi` / `renderoffscreen` Python commandlet 均 `status=0` | 证明 UE Installed Build、用户态补库、项目内 DDC/HOME、Python 插件和短生命周期自动化入口可用；后续真正像素渲染仍需 MRQ/MRG 或 map/game smoke |
| 2026-07-07 | **UE 5.8 用户态运行环境已补齐**：`libgbm.so.1` 通过项目内 `00_engine/runtime/ubuntu2204-libs/` 解决；UE 命令统一走 `00_engine/scripts/run_ue_cmd.sh`，设置项目内 `HOME`/DDC/tmp/runtime libs，并默认使用 `-ddc=NoZenLocalFallback` | 用户没有 sudo；集群登录节点不适合写真实 home，也不适合启动 UE 5.8 的 ZenLocal DDC 服务；包装脚本让后续 GPU smoke 和批渲入口稳定 |
| 2026-07-06 | **UE 5.8 Linux Installed Build 已下载并解压**：zip 38G，解压目录 73G，版本为 UE 5.8.0 changelist 55116800 | Installed Build 路线无需源码编译，适合当前 MVP |
| 2026-07-05 | **Lance contextual v2 改为 role-aware 结构并完成 GPU 验证**：历史视频只进 VIT，最新视频作为唯一 clean VAE source；完整 current-only 三轮重跑效果最好，turn3 小目标项圈仍不精确；prompt 默认改为 `current-only` | BAGEL 多图 interleave 启发了“历史作为 clean context”的方向，但 Lance 当前 `video_edit` 需要保持 `ref_source == noise` 的 VAE 对齐；v2 修复了 v1 all-source 的结构错误；长文本复述历史会干扰当前局部编辑 |
| 2026-07-03 | **Lance contextual v1 turn1/turn2 已重跑，视觉质量失败**：`contextual_smoke_v1_01` 证明真多轮 interleave 链路可执行，但抽帧显示 turn1 主体漂移、turn2 场景重绘严重 | Lance 可作为外部失败基线，不适合继续在当前公开视频上堆 turn3 |
| 2026-07-03 | **Lance contextual 多轮 config 采用轻量原型路线**：新增 `contextual_video_edit.py`，用 `text -> video -> history videos...` 的 interleave config 让 Lance 模板生成“视频在前、文本在后”的实际 prompt，目标视频由 Lance 数据层自动追加 | Lance 现有数据层能打包多个历史视频条件并只生成一个目标视频；后续需通过输入预处理控制真实帧数和尺寸 |
| 2026-07-03 | **Lance batch8 连续单轮测试跑完**：已下载视频分支权重，建立 `xks_lance`，跑通 `video_edit` smoke test，并完成 batch8 中 8 个领域的三次连续单轮调用；2 个损坏源视频已用 clean 版补跑。该结果不是 Lance 真多轮编辑结论 | Lance 当前只确认单轮/连续单轮运行路径；多轮结论需改用 contextual config 重新测试 |
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
