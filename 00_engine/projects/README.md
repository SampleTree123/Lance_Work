# projects —— UE 工程入口

> 父层：[`../README.md`](../README.md)。

本目录用于放 MVP 和后续 UE 工程。当前第一个工程位置：

```text
00_engine/projects/MVPProject/
```

## 当前工程

`MVPProject/` 已创建为最小 UE 5.8 工程，用于 smoke test 和后续 MVP 渲染闭环：

- `MVPProject.uproject`：启用 Python、Editor Scripting、Movie Render Pipeline。
- `Scripts/smoke_python.py`：短生命周期 Python commandlet smoke。
- `Scripts/generate_mcp_client_config.py`：调用 UE MCP 控制台命令生成 client config。
- `Config/DefaultEngine.ini`：最小工程配置。
- `Config/DefaultEditorPerProjectUserSettings.ini`：UE MCP auto-start 和 Terminal startup commands。

已验证：2026-07-07 在 H200 节点 `8FS9B74` 上，通过 `00_engine/scripts/run_mvp_python_smoke.sh nullrhi` 和 `renderoffscreen`，均 `status=0`。

UE MCP/Codex 配置已验证：`ModelContextProtocol`、`Terminal`、`EditorToolset` 已启用，DataMake 根目录 `.codex/config.toml` 作为 Codex canonical 配置；`00_engine/scripts/run_mcp_generate_client_config.sh` 可生成/刷新 UE 自动 client config；非沙箱运行确认 MCP listener 可绑定 `127.0.0.1:8000/mcp`。详情见 [`../unreal/mcp_agent_setup.md`](../unreal/mcp_agent_setup.md)。

## Git 策略

- `Saved/`、`Intermediate/`、`DerivedDataCache/`、`Binaries/`、`.sln` 等生成内容不进 Git。
- 稳定后只提交必要源码、配置、Python 脚本、少量文本资产清单和说明。
- 大型 `.uasset` / `.umap` 是否进 Git 需要另行决定；正式 UE 工程更适合 Perforce 或专门的大文件方案。
