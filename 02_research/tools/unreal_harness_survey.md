# Unreal Engine Harness / Skill / MCP 调研

> 查询日期：2026-06-28。
> 目标：确认是否存在可复用的 UE automation harness、agent skill 或 MCP 工具，帮助我们搭建合成数据流水线。

## 来源

- UE Automation Test Framework: https://dev.epicgames.com/documentation/en-us/unreal-engine/automation-test-framework-in-unreal-engine
- UE Python scripting: https://dev.epicgames.com/documentation/en-us/unreal-engine/scripting-the-unreal-editor-using-python
- UE Movie Render Pipeline: https://dev.epicgames.com/documentation/en-us/unreal-engine/movie-render-pipeline-in-unreal-engine
- ChiR24/Unreal_mcp: https://github.com/ChiR24/Unreal_mcp
- runreal/unreal-mcp: https://github.com/runreal/unreal-mcp
- remiphilippe/mcp-unreal: https://github.com/remiphilippe/mcp-unreal

## 结论

没有找到可以直接替代我们数据流水线的成熟 “UE dataset harness”。可用内容分三类：

1. **UE 官方自动化栈**：Python Editor scripting、Automation Test Framework、Functional Testing、Movie Render Pipeline / MRQ / MRG。
2. **AI agent 控制层**：Unreal MCP server，通过 C++ 插件或 Python remote execution 让 agent 操作编辑器。
3. **项目内自建薄 harness**：在官方 API 上封装 `render_pair.py`、`factors.py`、`passes.py`、`sidecar.py`。

当前建议：**生产流水线走第 3 类，底层依赖第 1 类；第 2 类只作为编辑器辅助和原型探索。**

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

## MCP / agent 工具

初步看到的可参考项目：

| 项目 | 特点 | 风险 |
|------|------|------|
| `ChiR24/Unreal_mcp` | C++ Automation Bridge + MCP；覆盖资产、Actor、Sequencer、Blueprint、console、tests 等；README 称支持 UE 5.0-5.8 | 需要插件编译/版本匹配；agent 拥有较大编辑器权限 |
| `runreal/unreal-mcp` | 不装新 C++ 插件，使用 UE Python Remote Execution；工具较轻 | 需要打开 remote execution；非官方；安全边界弱 |
| `remiphilippe/mcp-unreal` | Go + C++ 插件；强调 UE 5.7、headless builds/tests、Blueprint editing | 版本目标不是 UE 5.8；无 release；更适合参考测试组织方式 |

这些 MCP 工具对“让 AI 帮忙操作编辑器”有价值，但不应该直接成为确定性渲染数据生产的核心，因为：

- agent 行为本身不适合作为可复现生产逻辑；
- 插件和 UE minor version 绑定，维护成本不低；
- 编辑器远程控制权限较大，需要安全隔离；
- 我们的核心不变量是配置图、端点复用和 sidecar，必须由可审计脚本保证。

## 对本项目的采用建议

短期：

- 继续按 [`../../10_sources/unreal_engine/render/README.md`](../../10_sources/unreal_engine/render/README.md) 写自有薄 harness。
- 入口脚本使用 UE Python command line，优先验证 `-ExecutePythonScript`；需要更轻时再试 `-run=pythonscript`。
- 用 Automation Test Framework 写确定性/对齐 smoke tests，例如同配置双渲像素差、深度一致性、sidecar 完整性。
- MRQ 先跑通；MRG 作为更复杂输出图和多 pass 方案的升级路径。

中期：

- 可以在 Windows 创作端试 `ChiR24/Unreal_mcp` 或 `runreal/unreal-mcp`，用于让 agent 快速检查资产、关卡、Sequencer 和脚本暴露 API。
- 不把 MCP 工具写进集群批渲依赖；集群侧仍用命令行脚本。

长期：

- 当我们的 `render_pair.py` / schema / checklist 稳定后，可以考虑做一个项目内 Codex skill 或插件，把“如何操作 DataMake UE 工程”固化成可复用工作流。
