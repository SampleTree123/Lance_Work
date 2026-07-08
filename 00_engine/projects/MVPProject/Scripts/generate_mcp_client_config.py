from pathlib import Path

import unreal


project_dir = Path(unreal.Paths.project_dir())
codex_config = project_dir / ".codex" / "config.toml"

if codex_config.exists():
    unreal.log(
        f"Codex MCP config already exists, preserving write-once TOML: {codex_config}"
    )
    clients = ["ClaudeCode", "Cursor", "VSCode", "Gemini"]
else:
    clients = ["All"]

for client in clients:
    unreal.SystemLibrary.execute_console_command(
        None,
        f"ModelContextProtocol.GenerateClientConfig {client}",
    )

unreal.log("DATAMAKE_MCP_CLIENT_CONFIG_REQUESTED")
