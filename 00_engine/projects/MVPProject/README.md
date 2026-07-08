# MVPProject

Minimal UE 5.8 project for DataMake automation smoke tests and the first MVP render pair.

Current tracked files are intentionally small:

- `MVPProject.uproject`: enables Python, Editor Scripting, Movie Render Pipeline, UE MCP, Terminal, and EditorToolset.
- `Config/DefaultEngine.ini`: minimal startup settings.
- `Config/DefaultEditorPerProjectUserSettings.ini`: MCP auto-start and Terminal startup commands.
- `Scripts/smoke_python.py`: short lifecycle Python smoke test.
- `Scripts/generate_mcp_client_config.py`: generates MCP client configs through UE's `ModelContextProtocol.GenerateClientConfig` command.

Generated folders such as `Saved/`, `Intermediate/`, `DerivedDataCache/`, and `Binaries/` are ignored by Git.
