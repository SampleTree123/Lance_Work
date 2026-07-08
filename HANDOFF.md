# HANDOFF —— 项目接续上下文

> 新会话先读本文件，再读 [`AGENTS.md`](./AGENTS.md) 和 [`README.md`](./README.md)。

## 一句话项目

DataMake 为**多轮视频编辑模型**构建训练/验证数据集。本仓库只做数据构建、研究记录和外部能力验证，不做模型训练。

当前主攻：**Unreal Engine 合成视频数据**，用配置图生成精确配对编辑样本。

## 当前状态

- 工作区路径：`/scratch/prj0000000275/jcy/xks/DataMake`。
- 本地 Git 已初始化，分支 `main`。
- 已有最小 UE 工程 `00_engine/projects/MVPProject/`、Python smoke 脚本和 UE MCP/Codex 配置；尚无正式渲染脚本、实际资产台账或样本数据。资产台账 schema 已新增在 `00_engine/assets/asset_ledger_schema.md`。
- 管理员确认不能使用 `/local`，当前阶段所有工作都在 DataMake 目录下完成。
- Lance 已完成 GitHub / 论文 / HF 文件清单初读；视频分支权重已下载，`xks_lance` 环境可运行。
- Lance `video_edit` smoke test 已跑通；真实公开视频 batch8 的 8 个领域均已完成三次连续单轮调用，其中 `6.mp4`、`7.mp4` 原始视频编码损坏，已用 clean 版补跑完成。这不是 Lance 真多轮编辑结论。
- Lance contextual 多轮 config 工具已新增：`10_research/model_experiments/lance/scripts/contextual_video_edit.py`。v1 已重跑 turn1/turn2 并抽帧检查；链路能跑通，但主体和场景保持失败。2026-07-05 复查后确认 v1 的 all-source 结构会打破 Lance edit 的 source-target VAE 对齐；现已实现并测试 v2 role-aware config：历史视频只进 VIT，最新视频作为唯一 clean VAE source。v2 turn2/turn3 已在 H200 上生成成功；完整 `contextual_role_v2_current_only_full_01` 三轮重跑效果最好：turn1 保住双人主体并改红外套，turn2 稳定加夕阳，turn3 保持红外套/夕阳并把蓝色加到前景狗附近，但项圈不精确。默认 prompt 改为 `current-only`：只写当前轮指令，必要时加入少量保持约束，不复述完整历史编辑。记录见 `10_research/model_experiments/lance/reports/contextual_video_edit_smoke.md`。
- Lance full-conversation multi-turn chat A 方案原型已接入：参考 `Jayce-Ping/Lance@8b002b5`，本地 Lance 增加 `multiturn/`、`multiturn_chat.py`，DataMake 增加 `scripts/run_multiturn_chat.sh` 和 `scripts/build_multiturn_conversation.py`。它保留历史 user/assistant turns，不把历史 prompt 拼进最新 prompt；视觉条件仍按 DataMake v2 原则处理：旧视觉 VIT-only，最新视觉为唯一 clean VAE direct source。已通过语法检查和 conversation JSON 生成测试，尚未跑 GPU 视觉结果。
- BAGEL 已做针对性代码/论文查阅：其 interleaved image generation 训练支持多张历史图像作为 clean VAE/VIT context；这启发 Lance v2 采用历史 VIT-only、最新 source VAE-only 的保守映射。
- 当前顶层结构已收敛为 `00_engine/`、`10_research/`、`20_planning/` 三大块。

## 核心数据模型

- 配置：`C = {身份, 服装, 动作, 表情, 场景, 道具/配饰, 相机, 光照, 天气/特效, 风格}`。
- 节点：确定性渲染 `render(C)`。
- 边：原子编辑 `C -> C'`。
- 单轮样本：`(video_in, instruction, video_out)`。
- 多轮链：配置图路径 `C0 -> C1 -> C2 -> ...`。
- 硬约束：**端点复用**，上一轮 `video_out` 必须就是下一轮 `video_in` 文件。

详细设计见 [`20_planning/data_design/`](./20_planning/data_design/README.md)。

## 当前目录地图

| 路径 | 内容 |
|------|------|
| `00_engine/` | 引擎合成总入口：UE、资产、脚本、工程、输出、缓存 |
| `00_engine/unreal/` | UE 安装/部署说明、历史技术调研、集群 MVP 计划 |
| `00_engine/scripts/` | 当前 UE MVP 渲染管线和后续脚本入口 |
| `00_engine/assets/` | 资产来源、许可证、台账和 prototype-only 约束 |
| `10_research/` | 论文、外部项目、UE harness/MCP 调研 |
| `10_research/model_experiments/` | 外部模型能力验证，当前重点是 Lance |
| `20_planning/data_design/` | 数据模型、edit taxonomy、schema、采样 |
| `20_planning/implementation/` | 存储、服务器环境、风险和实施前检查 |
| `20_planning/compliance/` | 许可证、资产合规、发布约束 |
| `20_planning/discussions/` | 讨论过程和会议记录 |

## 服务器与存储

- 当前目录在 `/scratch` 上；2026-07-08 本地 `df -h .` 显示约 2.8T 总量、2.0T 已用、826G 可用、71% 使用率。
- 资产存储已改为三层策略：本地 Windows/Laptop 4080 只作交互预览层；服务器 DataMake 只作生产工作层；完整资产包、历史版本和正式结果需要长期素材/冷存储层，位置尚未确定。实际引入资产前先按 `00_engine/assets/asset_ledger_schema.md` 建台账。
- 当前布局见 [`20_planning/implementation/storage.md`](./20_planning/implementation/storage.md)：
  - `00_engine/unreal/UE_5.8/`：UE 引擎。
  - `00_engine/unreal/downloads/`：UE zip / 临时下载包。
  - `00_engine/cache/ddc/`：UE DDC / shader cache。
  - `00_engine/cache/tmp/`：UE 临时目录。
  - `00_engine/projects/`：UE MVP 工程。
  - `00_engine/outputs/`：少量 UE 验证输出。
  - `10_research/model_experiments/lance/lance/`：Lance 上游代码仓库。
  - `10_research/model_experiments/lance/models/`：Lance 权重。
  - `10_research/model_experiments/lance/inputs/`：Lance 自测输入和 prompt。
  - `10_research/model_experiments/lance/outputs/`：Lance 验证输出。
  - `10_research/model_experiments/lance/logs/`：Lance 运行日志和自动生成 config。
- UE 5.8 Linux Installed Build zip 已下载并通过 `unzip -tq` 校验，也已解压：
  - `00_engine/unreal/downloads/Linux_Unreal_Engine_5.8.0.zip`
  - 大小约 38G
  - 解压目录 `00_engine/unreal/UE_5.8/`，约 73G
  - build：UE 5.8.0，changelist 55116800，branch `++UE5+Release-5.8`
  - `libgbm.so.1` 已用无 sudo 方式补齐：`libgbm1_22.0.1-1ubuntu2_amd64.deb` 解包到 `00_engine/runtime/ubuntu2204-libs/`，`ldd` 已无 `not found`。
  - UE 命令已统一封装为 `00_engine/scripts/run_ue_cmd.sh`，会设置项目内 `HOME`、`LD_LIBRARY_PATH`、DDC/tmp，并默认追加 `-ddc=NoZenLocalFallback`。
  - GPU 节点 smoke 已完成：2026-07-07 job `99943` / node `8FS9B74` / H200 / driver `565.57.01`。`vulkaninfo` 未安装，但 UE 日志确认 `rhiname="Vulkan"`、`gpu="NVIDIA H200"`。
  - 裸 `-version` 可初始化 Vulkan 但不是可靠短生命周期 smoke；不要加 `-NoShaderCompile`，会触发 `AllowShaderCompiling()` 断言。
  - `00_engine/scripts/run_mvp_python_smoke.sh` 已验证：`nullrhi` 和 `renderoffscreen` 两个分支均 `status=0`，打印 `DATAMAKE_UE_PYTHON_SMOKE_OK`。注意 Python commandlet 通常选择 Null RHI，不能替代真正像素渲染 smoke。
  - UE MCP agent 环境已配置：`ModelContextProtocol`、`Terminal`、`EditorToolset` 已在 `MVPProject` 启用，`bAutoStartServer=True`；DataMake 根目录 `.codex/config.toml` 是 Codex canonical MCP 配置，UE 自动生成的 client config 仍保留在 `MVPProject` 下。`run_mcp_generate_client_config.sh` 可复跑；非沙箱验证确认 listener 可绑定 8000。详情见 `00_engine/unreal/mcp_agent_setup.md`。
  - 用户态远程桌面支线已验证到边界：TurboVNC 3.3 已在 `00_engine/remote_desktop/` 解包，补齐 `libXfont2`、`xkbcomp`、`xsetroot`；Windows VNC Viewer 已通过 reverse tunnel 连到 GPU 节点 `Xvnc + xterm`。UE Editor 可初始化 H200/Vulkan 并加载项目 map，但在纯 Xvnc 的编辑器 UI 后期 SIGSEGV；CrashReportClient 随后因 Xvnc 无 GLX 二次失败。结论：该方案可作远程终端/VNC smoke，不适合作为稳定完整 UE Editor GUI；服务器继续定位为脚本化 UE、MCP/offscreen/MRQ 生产环境。详情见 `00_engine/remote_desktop/README.md`。
  - zip 已满足删除条件；删除前先向用户确认。
- Lance 当前实际使用用户已配置的 HF cache：`/scratch/prj0000000275/jcy/.cache/huggingface`；可运行权重目录仍在 `10_research/model_experiments/lance/models/Lance/`。
- 上述大文件、缓存、输出和模型权重不进 Git。

历史服务器记录在 [`20_planning/implementation/environment.md`](./20_planning/implementation/environment.md) 和 [`20_planning/implementation/risks.md`](./20_planning/implementation/risks.md)。执行前必须重新检查 `nvidia-smi`、`vulkaninfo`、`ldd`、UE 版本和 SLURM 限制。

## 已定策略

- 当前主攻 UE 5.8 合成；UE5.6 调研只作历史参考。
- UE 生产流水线使用官方 Python + Automation Test Framework + MRQ/MRG 自建薄 harness。
- UE 5.8 官方 MCP 插件已配置给 `MVPProject`，只作为编辑器辅助、资产/关卡检查和原型探索；Codex 通过 DataMake 根目录 `.codex/config.toml` 接入当前运行中的 UE MCP server，但不进入集群批渲核心链路。
- 服务器图形桌面只是预览支线；TurboVNC 已确认可连接 xterm，但完整 UE Editor GUI 在纯 Xvnc 下不稳定。生产渲染仍固化为 UE Python/MRQ/MRG 脚本，人工图形化编辑主要放本地。
- MVP 首选低风险编辑：E8 光照、E5 道具可见性、E6 配饰可见性或 E11 表情。
- E1 身份、E2 服装较难，放到基础闭环之后。
- 原型资产可 `prototype-only`，但不能进入发布或训练数据。
- 本地 400G 不作为完整素材库；只放少量交互预览子集。服务器只放当前批次工作副本；长期冷存储层需在正式规模生产前确认。

## 最近下一步

1. 向用户确认是否删除 `00_engine/unreal/downloads/Linux_Unreal_Engine_5.8.0.zip` 释放约 38G。
2. 在 [`00_engine/scripts/`](./00_engine/scripts/README.md) 写 MVP 最小渲染脚本骨架：创建/加载最小场景、固定相机、跑 MRQ/MRG 或可替代的首帧/短视频 smoke。
3. 真正像素渲染 smoke 通过后，再实现 `render_pair.py` / `factors.py` / `passes.py` / `sidecar.py`。
4. Lance 后续若继续测多轮，先用 `run_multiturn_chat.sh` 测 full-conversation A 方案，并与 `contextual_role_v2_current_only_full_01` 做同视频/同 prompt 对照；不要回到 v1 all-source 作为默认方案。

## Agent 备忘

- 接手先跑 `git status --short`。
- 不要下载或提交大文件，除非用户明确确认。
- 旧讨论只作背景；稳定结论以正式分支文档为准。
- Lance 视频权重已下载；没有下载 `Lance_3B/` 图片分支和 HF demo assets。
- Lance 输出、日志、真实视频输入、clean 输入副本和自测 prompt 默认不进 Git；稳定结论写入正式文档。
