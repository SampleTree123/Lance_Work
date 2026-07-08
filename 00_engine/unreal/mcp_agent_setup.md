# UE MCP / Codex Linux 配置记录

> 状态：2026-07-07 已在 `MVPProject` 启用 UE 5.8 官方 MCP、Terminal、EditorToolset，并生成 Codex/Cursor/Claude/VSCode/Gemini client config。

## 1. Windows 步骤在 Linux 的对应关系

用户本地 Windows 步骤：

```text
enable plugins: Unreal MCP, Terminal, EditorToolset
Project Settings -> Model Context Protocol -> Auto start server
Terminal startup commands:
  set TERM=xterm-256color
  cd /d "C:\UnrealProjects\MCPCodex"
  Codex
ModelContextProtocol.GenerateClientConfig All
```

Linux 服务器对应结果：

```text
Unreal MCP plugin name: ModelContextProtocol
Terminal plugin name: Terminal
EditorToolset plugin name: EditorToolset
MCP server: http://127.0.0.1:8000/mcp
Codex client config: .codex/config.toml
```

Terminal startup commands 已写入 `MVPProject` 的 editor per-project settings：

```text
export TERM=xterm-256color
cd "/scratch/prj0000000275/jcy/xks/DataMake"
codex
```

这里进入 DataMake 根目录，是为了让 Codex 在整个工作区级别读取 `.codex/config.toml`。以后即使新增多个 UE project，只要它们使用同一个 UE MCP server 端口，Codex 从 DataMake 根目录启动即可连接当前运行中的 UE editor/server。

UE Installed Build 的 `GenerateClientConfig` 仍会把自动生成的 Codex TOML 写到 `00_engine/projects/MVPProject/.codex/config.toml`。这份文件保留为 UE 生成产物；DataMake 根目录 `.codex/config.toml` 是我们手工维护的项目级 canonical 配置。

## 2. 已写入的项目文件

- `00_engine/projects/MVPProject/MVPProject.uproject`：启用 `ModelContextProtocol`、`Terminal`、`EditorToolset`。
- `00_engine/projects/MVPProject/Config/DefaultEditorPerProjectUserSettings.ini`：设置 `bAutoStartServer=True`、`ServerPortNumber=8000`、`ServerUrlPath=/mcp` 和 Terminal startup commands。
- `00_engine/projects/MVPProject/Scripts/generate_mcp_client_config.py`：调用 UE 控制台命令生成 client config。Codex TOML 是 write-once；已有时脚本保留该文件，只刷新 JSON 客户端配置。
- `00_engine/scripts/run_mcp_generate_client_config.sh`：短生命周期生成脚本；运行时临时覆盖 `bAutoStartServer=False`，避免只生成配置时启动 HTTP listener。
- `.codex/config.toml`：DataMake 根目录的 Codex MCP 配置，当前指向 `http://127.0.0.1:8000/mcp`。

已生成的 client config：

```text
00_engine/projects/MVPProject/.mcp.json
00_engine/projects/MVPProject/.cursor/mcp.json
00_engine/projects/MVPProject/.vscode/mcp.json
00_engine/projects/MVPProject/.gemini/settings.json
00_engine/projects/MVPProject/.codex/config.toml
```

Codex 配置内容：

```toml
[mcp_servers.unreal-mcp]
url = "http://127.0.0.1:8000/mcp"
enabled = true
default_tools_approval_mode = "prompt"
tool_timeout_sec = 120
```

## 3. 验证结果

已执行：

```bash
00_engine/scripts/run_mcp_generate_client_config.sh
```

结果：`status=0`，UE 日志显示插件加载成功，并刷新 `.mcp.json`、Cursor、VSCode、Gemini 配置；Codex TOML 已存在时被保留。

也做了非沙箱 auto-start 验证：

```bash
00_engine/scripts/run_ue_cmd.sh \
  /scratch/prj0000000275/jcy/xks/DataMake/00_engine/projects/MVPProject/MVPProject.uproject \
  -run=pythonscript \
  -script=/scratch/prj0000000275/jcy/xks/DataMake/00_engine/projects/MVPProject/Scripts/generate_mcp_client_config.py \
  -NullRHI -unattended -nop4 -nosplash -stdout -FullStdOutLogOutput
```

结果：`status=0`；日志显示 `HttpListener stopping listening on Port 8000`，说明 MCP server auto-start 可以在普通执行环境中绑定 8000 端口。此前在 Codex 沙箱内出现的 `HttpListener - Unable to allocate stream socket` 是沙箱网络限制，不是 UE 配置失败。

## 4. 使用方式

生成/刷新 client config：

```bash
cd /scratch/prj0000000275/jcy/xks/DataMake
00_engine/scripts/run_mcp_generate_client_config.sh
```

实际使用 MCP 时，需要让 UE editor/server 进程保持运行，并让 Codex 从 DataMake 根目录启动：

```bash
cd /scratch/prj0000000275/jcy/xks/DataMake
codex
```

在 Codex 里用 `/mcp` 查看 `unreal-mcp` 是否在线。DataMake 项目必须被 Codex 标记为 trusted，否则根目录 `.codex/config.toml` 不会加载。

无头服务器上，Terminal 插件的 startup commands 只是和 Windows 编辑器 UI 配置保持一致；可靠工作流是外部 Codex 进程连接 UE MCP server。Terminal 面板本身需要 UE 编辑器 UI 创建，不作为批量生产依赖。

## 5. 边界

- UE MCP/EditorToolset 是 Experimental。用于检查、探索、原型脚本辅助可以；生产数据流水线仍必须固化为可审计的 UE Python/MRQ/MRG 脚本和 sidecar。
- UE 日志会提示：经该插件传给 LLM 的数据属于 UE EULA Licensed Technology，需要确保 LLM provider 不把数据用于训练。本项目后续接入任何外部模型/agent 时都要单独审查该约束。
- 当前只启用 `EditorToolset`，没有启用 `AllToolsets`，避免额外加载一整组实验工具集。
