# Unreal Engine Harness / Agent / MCP 调研

> 初查日期：2026-06-28；UE 5.8 agent/MCP 复核日期：2026-07-01。
> 目标：确认是否存在可复用的 UE automation harness、agent skill 或 MCP 工具，帮助我们搭建合成数据流水线。

## 来源

- UE 5.8 official release blog: https://www.unrealengine.com/news/unreal-engine-5-8-is-now-available
- UE Automation Test Framework: https://dev.epicgames.com/documentation/en-us/unreal-engine/automation-test-framework-in-unreal-engine
- UE Python scripting: https://dev.epicgames.com/documentation/en-us/unreal-engine/scripting-the-unreal-editor-using-python
- UE Movie Render Pipeline: https://dev.epicgames.com/documentation/en-us/unreal-engine/movie-render-pipeline-in-unreal-engine
- UE Remote Control API HTTP Reference: https://dev.epicgames.com/documentation/en-us/unreal-engine/remote-control-api-http-reference-for-unreal-engine
- OpenAI Codex MCP docs: https://developers.openai.com/codex/mcp
- ChiR24/Unreal_mcp: https://github.com/ChiR24/Unreal_mcp
- runreal/unreal-mcp: https://github.com/runreal/unreal-mcp
- remiphilippe/mcp-unreal: https://github.com/remiphilippe/mcp-unreal

## 结论

没有找到可以直接替代我们数据流水线的成熟 “UE dataset harness”。UE 5.8 新增的官方 MCP 插件让“agent 操作引擎”从第三方探索变成了官方支持方向，但它仍是 **Experimental agent 控制层**，不是确定性数据生产 harness。

可用内容分四类：

1. **UE 官方自动化栈**：Python Editor scripting、Automation Test Framework、Functional Testing、Movie Render Pipeline / MRQ / MRG。
2. **UE 5.8 官方 MCP 插件**：Epic 说明该 Experimental 插件允许任意 LLM 系统通过 MCP 连接并理解 engine 和 project，内置暴露 Blueprints、assets、levels、materials、meshes 等核心系统，并允许开发者扩展自定义功能。
3. **第三方 AI agent 控制层**：Unreal MCP server，通过 C++ 插件、UE Remote Control API 或 Python remote execution 让 agent 操作编辑器。
4. **项目内自建薄 harness**：在官方 API 上封装 `render_pair.py`、`factors.py`、`passes.py`、`sidecar.py`。

当前建议：**生产流水线走第 4 类，底层依赖第 1 类；第 2/3 类只作为编辑器辅助、资产/关卡检查、脚本原型和交互调试。**

对“Claude Code 支持 UE5.8 agent”的准确理解：**UE 5.8 支持的是 MCP 标准插件，不是 Claude Code 专属功能**。Claude Code、Codex、Cursor 等只要支持 MCP 客户端能力，理论上都可以接入。OpenAI Codex 当前支持 STDIO 和 Streamable HTTP MCP servers，可在 CLI 和 IDE extension 中通过 `config.toml` 或 `codex mcp` 配置，因此可以作为 UE MCP 的客户端候选。

## 官方 UE 自动化栈

UE 官方 Automation Test Framework 支持 unit、feature、smoke、content stress、screenshot comparison 等测试类型，也支持 Python / Blueprint / C++ 测试入口。它适合做：

- 项目健康检查；
- 资产加载/编译/关卡检查；
- 渲染前后的 sanity check；
- headless automation test。

UE Python scripting 支持从命令行执行脚本：

- `UnrealEditor-Cmd.exe Project.uproject -ExecutePythonScript=script.py`
- `UnrealEditor-Cmd.exe Project.uproject -run=pythonscript -script=script.py`

其中 commandlet 模式更轻，但不会自动加载 level，脚本需要显式 `load_level`。

Movie Render Pipeline 是我们渲染侧的核心接口。MRQ 用于排队和脚本化批渲；MRG 是更灵活的图式渲染配置。官方文档说明 MRQ 支持 batch jobs、可复用 preset、远程/单独进程渲染，这与我们的 SLURM job-array 思路兼容。

UE Remote Control API 提供 HTTP/WebSocket 端点，可对当前 Editor 内的 UObject 调用 BlueprintCallable 函数、读取/写入可暴露属性、搜索资产等。它适合交互式工具或 agent 辅助检查，不适合作为唯一生产 harness，因为它需要活跃 Editor 会话，且安全边界和状态管理要单独处理。

## UE 5.8 官方 MCP 插件

2026-07-01 复核：Epic 的 UE 5.8 official release blog 明确称 MCP 插件为 Experimental，定位是让 LLM 系统连接并理解 engine/project，帮助构建 assets/systems、扩展 engine functionality、执行 testing/optimization 等任务。官方描述还说插件内置暴露 Blueprints、assets、levels、materials、meshes 等核心系统，并可由开发者扩展。

采用判断：

- 它是 UE 生态内最值得优先验证的 agent 入口，因为它来自 Epic，且是标准 MCP，而不是某个模型厂商私有协议。
- 它解决的是“让 agent 看见和操作编辑器/项目”的问题，不解决我们最关键的“配置图、确定性渲染、端点复用、sidecar 审计”问题。
- 因此短期应在 Windows 创作端或单机 UE 编辑器会话中试用，任务限于资产/关卡/Sequencer 检查、生成 Python/Blueprint 原型、查询对象和运行 smoke tests。
- 集群无头批渲仍走 `UnrealEditor-Cmd` + UE Python + MRQ/MRG。只有当官方 MCP 能在 Linux headless/`UnrealEditor-Cmd` 下稳定暴露所需工具，并且我们能把每个 agent 操作固化成可审计脚本后，才考虑进入生产依赖。

Codex 接入方式：

```toml
# .codex/config.toml 或 ~/.codex/config.toml；实际 url/port 以 UE 5.8 插件设置为准
[mcp_servers.unreal_engine]
url = "http://127.0.0.1:<UE_MCP_PORT>/mcp"
default_tools_approval_mode = "prompt"
tool_timeout_sec = 120
enabled = true
```

如果官方 UE 插件只在 Editor UI 内开启 server，则 Codex CLI 需要和 Editor 在同一台机器或通过 SSH port-forward 访问。不要把 UE MCP server 直接暴露到共享网络；如必须跨机器访问，要求本机隧道、token/auth、工具 allowlist 和日志记录。

## MCP / agent 工具

初步看到的可参考项目：

| 项目 | 特点 | 风险 |
|------|------|------|
| UE 5.8 official MCP plugin | Epic 官方 Experimental 插件；标准 MCP；暴露 Blueprints、assets、levels、materials、meshes 等；可扩展 | 文档和实测仍需补齐；Experimental；不等于 headless production harness |
| `ChiR24/Unreal_mcp` | C++ Automation Bridge + MCP；覆盖资产、Actor、Sequencer、Blueprint、console、tests 等；README 称支持 UE 5.0-5.8，并提供 Native MCP HTTP 与 TypeScript bridge 两种路径 | 需要插件编译/版本匹配；agent 拥有较大编辑器权限；第三方实现与官方 UE MCP 可能重叠 |
| `runreal/unreal-mcp` | 不装新 C++ 插件，使用 UE Python Remote Execution；工具较轻 | 需要打开 remote execution；非官方；安全边界弱 |
| `remiphilippe/mcp-unreal` | Go + C++ 插件；强调 UE 5.7、headless builds/tests、Blueprint editing | 版本目标不是 UE 5.8；无 release；更适合参考测试组织方式 |

这些 MCP 工具对“让 AI 帮忙操作编辑器”有价值，但不应该直接成为确定性渲染数据生产的核心，因为：

- agent 行为本身不适合作为可复现生产逻辑；
- 插件和 UE minor version 绑定，维护成本不低；
- 编辑器远程控制权限较大，需要安全隔离；
- 我们的核心不变量是配置图、端点复用和 sidecar，必须由可审计脚本保证。

## 对本项目的采用建议

短期：

- 继续按 [`../../00_engine/scripts/README.md`](../../00_engine/scripts/README.md) 写自有薄 harness。
- 入口脚本使用 UE Python command line，优先验证 `-ExecutePythonScript`；需要更轻时再试 `-run=pythonscript`。
- 用 Automation Test Framework 写确定性/对齐 smoke tests，例如同配置双渲像素差、深度一致性、sidecar 完整性。
- MRQ 先跑通；MRG 作为更复杂输出图和多 pass 方案的升级路径。
- 安装 UE 5.8 后优先检查官方 MCP 插件是否随 Installed Build 提供、插件名/端口/transport、能否在 Linux editor 和 Windows editor 都启用。
- 如果官方 MCP 可用，先让 Codex 通过 Streamable HTTP 连接，只开放 inspection / list / test / read-only 或低风险工具；修改类工具维持人工 approval。

中期：

- 可以在 Windows 创作端优先试 UE 5.8 官方 MCP；若功能不足，再对比 `ChiR24/Unreal_mcp` 或 `runreal/unreal-mcp`，用于让 agent 快速检查资产、关卡、Sequencer 和脚本暴露 API。
- 不把 MCP 工具写进集群批渲依赖；集群侧仍用命令行脚本。

长期：

- 当我们的 `render_pair.py` / schema / checklist 稳定后，可以考虑做一个项目内 Codex skill 或插件，把“如何操作 DataMake UE 工程”固化成可复用工作流。
