# 00_engine/scripts：执行代码入口

本目录保存可复现的 CC、UE、配置图和文档校验代码。当前第一批执行顺序由 [`FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md`](../../20_planning/data_design/character_creator/full_process/planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md) 定义；本页只说明代码位于哪里及其成熟度。

## 子目录

| 路径 | 内容 | 当前用途 |
| --- | --- | --- |
| [`character_creator/`](./character_creator/README.md) | CC5 角色、服装、动作、导出与验证脚本 | 生成 8 身份、16 Look、12 动作冻结输入 |
| [`unreal/`](./unreal/README.md) | UE 资产导入、表情、动作分层和运行时验证 | 完成 Pilot；继续做动作/Look 门禁与场景模板 |
| [`dataset/`](./dataset/README.md) | 配置图与多轮链生成 | 已通过合成输入测试，真实 UE ID 待补 |
| [`documentation/`](./documentation/README.md) | 文档图、链接和结构检查 | 提交前必须运行 |

根目录 shell 脚本用于 Linux UE 环境：

- `ue_env.sh`：统一 UE 环境变量；
- `run_ue_cmd.sh`：用户态 UE 命令包装；
- `run_mvp_python_smoke.sh`：最小 Python commandlet smoke；
- `run_mcp_generate_client_config.sh`：生成 MCP 客户端配置。

## 第一批关键实现

### Character Creator

- `character_creator/cc_build_first_batch_identity_library_v1.py`：建立首批 8 身份冻结库；
- `character_creator/cc_build_first_batch_full_reference_looks_v2.py`：建立并审计 16 个 FullReference Look；
- `character_creator/cc_build_first_batch_action_gate_v3.py`：首批 12 动作的 CC 门禁；
- `character_creator/cc_ingest_first_batch_action_window_selection_v1.py`：接收人工选择的 5 秒窗口；
- `character_creator/cc_build_first_batch_action_ue_export_v1.py`：准备 Motion FBX 导出任务；
- `character_creator/cc_first_batch_action_registry_20260820_v3.json`：当前 12 动作权威注册表；
- `character_creator/cc_first_batch_full_reference_looks_20260820_v2.json`：当前 16 Look 权威配置。

### Unreal Engine

- `unreal/first_batch_expression_profile_20260820_v1.json`：Happy/Angry/Sad 表情配置；
- `unreal/ue_build_first_batch_expression_library.py`：创建 UE 表情曲线资产；
- `unreal/ue_build_first_batch_expression_composition.py`：构建身体动作与面部表情组合；
- `unreal/run_first_batch_expression_review.py`：运行首批表情审查；
- `unreal/ue_import_cc5_rlmotion_pilot.py`：CC 动作导入 Pilot；
- `unreal/ue_validate_p0_runtime_motions.py`：运行时动作门禁。

### 配置图

- `dataset/build_first_batch_config_graph_v1.py`：确定性生成节点、原子边、3–5 轮链和渲染作业；
- schema：[`CONFIG_GRAPH_SCHEMA_V1.md`](../../20_planning/data_design/schema/CONFIG_GRAPH_SCHEMA_V1.md)；
- 采样：[`MULTI_ROUND_CHAIN_SAMPLING_V1.md`](../../20_planning/data_design/sampling/MULTI_ROUND_CHAIN_SAMPLING_V1.md)。

完整的代码、JSON、证据和 UE 资产映射以 [`IMPLEMENTATION_INDEX.md`](../../20_planning/data_design/character_creator/full_process/reference/IMPLEMENTATION_INDEX.md) 为准。

## 尚未实现或未贯通

以下内容不能因为存在 Pilot 就视为生产完成：

1. 12 个 Motion FBX 的完整导出和 UE 批量门禁；
2. 16 个 FullReference Look 的正式 UE 批量导入；
3. 固定场景、角色锚点、两台相机、灯光和 Sequence；
4. 唯一节点的 MRQ/MRG 渲染执行器；
5. sidecar、SHA-256、重试、断点恢复和交付验证；
6. 本地完整链和服务器 10 节点基准。

不要恢复旧 README 中尚未实现的 `render_pair.py`、`factors.py`、`passes.py` 等占位接口；生产实现应以当前 schema、Sprint 和实际 UE 资产为准。

## 校验

```powershell
python 00_engine/scripts/documentation/check_character_factory_docs.py --json
python -m pytest 00_engine/scripts/documentation/tests 00_engine/visualization_portal/tests 00_engine/scripts/dataset/tests -q
```

CC 全测试包含少量只能在 CC 内置 Python/PySide2 环境收集的测试；普通系统 Python 中应按测试说明排除这些 UI 专用模块。
