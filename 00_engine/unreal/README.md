# unreal —— Unreal Engine 目标环境

> 父层：[`../README.md`](../README.md) → [`../../README.md`](../../README.md)。

本目录记录 Unreal Engine 版本、部署、历史技术调研和集群 MVP 计划。当前执行目标是 **UE 5.8 Linux Installed Build + 无头渲染**。

## 内容说明

| 文件 | 内容 | 状态 |
|------|------|------|
| `README.md` | 本层索引和当前策略 | 当前 |
| `pipeline_research_memo.md` | UE 环境、渲染能力、软件清单、历史调研 | 历史调研稿，执行前复核 |
| `cluster_deploy_and_mvp.md` | 当前 DataMake 单目录方案下的 UE 安装、无头 smoke test、SLURM MVP 计划 | 当前执行计划 |
| `mcp_agent_setup.md` | UE 5.8 官方 MCP + Codex/Terminal Linux 配置 | 当前 |

实际引擎目录使用：

```text
00_engine/unreal/UE_5.8/
```

下载包临时放：

```text
00_engine/unreal/downloads/
```

用户态运行库补丁放：

```text
00_engine/runtime/
```

## 当前策略

- 引擎目标：UE 5.8。UE5.6 相关备忘录只作历史调研。
- 部署路线：优先使用 Linux Installed Build zip；源码编译、容器、Apptainer 只在 Installed Build 失败时再讨论。2026-07-06 复核：Installed Build 入口需要 Epic account 登录，不需要 GitHub；源码路线才需要 Epic account 绑定 GitHub。
- 命令入口：统一通过 [`../scripts/run_ue_cmd.sh`](../scripts/run_ue_cmd.sh) 调用 `UnrealEditor-Cmd`，补齐项目内 `HOME`、本地 `libgbm`、DDC/tmp 和 `-ddc=NoZenLocalFallback`。
- Smoke 入口：[`../scripts/run_mvp_python_smoke.sh`](../scripts/run_mvp_python_smoke.sh) 已在 H200 节点验证 `nullrhi` / `renderoffscreen` 两个分支可短生命周期退出。
- 无头渲染：`run_ue_cmd.sh` + `-RenderOffscreen` + Vulkan；2026-07-07 UE 日志已确认 `rhiname="Vulkan"`、`gpu="NVIDIA H200"`。
- 渲染系统：MRQ 先跑通，MRG 作为多 pass / 图式输出升级路径。
- 数据 harness：生产侧自建薄脚本，底层用 UE Python + Automation Test Framework + MRQ/MRG。
- Agent/MCP：UE 5.8 官方 MCP 插件已在 `MVPProject` 启用，Codex canonical MCP 配置放在 DataMake 根目录 `.codex/config.toml`；Codex 可通过 MCP 连接 UE server 做编辑器辅助、资产/关卡检查和原型探索，但不作为集群批渲核心依赖。配置见 [`mcp_agent_setup.md`](./mcp_agent_setup.md)。
- 远程桌面：用户态 TurboVNC 最小链路已在登录节点和 H200 GPU job 节点验证，入口见 [`../remote_desktop/README.md`](../remote_desktop/README.md)；UE Editor 可进入 H200/Vulkan 初始化，但 viewport 交互体验尚未人工目视确认。

## 关键技术结论

- **前后对齐**：固定帧率、时间轴、相机、随机种子和 console vars；AA=None + 空间采样；必要时 warm-up 让 Lumen 收敛。
- **端点复用**：脚本输出的 `video_out` 必须可作为下一条边的 `video_in` 原文件使用。
- **GT passes**：优先 World Depth、Motion Vectors、Object IDs/Cryptomatte 或 Stencil Layers，并由 sidecar 记录相机、actor 标签和改动因子。
- **增删类编辑**：优先 visibility toggle，而不是 spawn/destroy，降低时间轴和确定性风险。
- **原型资产**：可用于内部管线验证，但必须标 `prototype-only`；训练/发布前必须换成合规资产或取得明确授权。

## 相关入口

- MVP 渲染管线：[`../scripts/README.md`](../scripts/README.md)。
- UE harness 调研：[`../../10_research/tool_surveys/unreal_harness_survey.md`](../../10_research/tool_surveys/unreal_harness_survey.md)。
- UE MCP/Codex 配置：[`mcp_agent_setup.md`](./mcp_agent_setup.md)。
- 存储路径：[`../../20_planning/implementation/storage.md`](../../20_planning/implementation/storage.md)。
- 许可证约束：[`../../20_planning/compliance/licensing_compliance.md`](../../20_planning/compliance/licensing_compliance.md)。

## Agent 备忘

- 执行前重新核实 UE 5.8 实际下载来源、hotfix 状态、Linux 依赖和 SLURM 限制。
- UE Linux Installed Build 页面是 `https://www.unrealengine.com/en-US/linux`；如果需要源码，再走 `EpicGames/UnrealEngine` GitHub 绑定流程。
- 不把引擎、下载包、DDC、工程生成目录或渲染输出提交进 Git。
- 第一个 MVP 不追求资产规模，先验证确定性渲染、GT、sidecar 和端点复用。
- 试用 UE MCP 时优先限制为 inspection/read-only/test 类操作；任何修改类工具保持人工 approval。
