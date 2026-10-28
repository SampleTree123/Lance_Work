# `00_engine`：生产实现与运行工作层

2026-10-28新增[离线编辑链展示包](render_pipeline/showcase/chain_examples_20261028/README.md)，网页、视频副本、属性与编辑说明集中在同一目录；本包获用户特许入Git，源生产媒体未改动。详情见[展示归档](render_pipeline/docs/CHAIN_SHOWCASE_20261028.md)。

本目录承载 Character Creator、Unreal Engine、配置图和视觉审查的实际实现与输出。长期流程从 [Character Factory Master](../20_planning/data_design/character_creator/full_process/README.md) 进入；当前成熟度和下一步从 [项目状态](../20_planning/data_design/character_creator/full_process/project_management/status/PROJECT_STATUS.md) 获取。

## 目录职责

| 路径 | 用途 | 权威说明 |
| --- | --- | --- |
| [`scripts/`](./scripts/README.md) | CC/UE/Dataset 自动化、配置和测试 | [Technical 索引](../20_planning/data_design/character_creator/full_process/technical/README.md) |
| [`character_creator_bridge/`](./character_creator_bridge/README.md) | CC 文件队列、RLPy 作业与回执 | [Bridge 操作](../20_planning/data_design/character_creator/full_process/technical/bridge/CC_BRIDGE_OPERATIONS.md) |
| [`visualization_portal/`](./visualization_portal/README.md) | 截图、动作、服装和实验审查页面 | [视觉审查](../20_planning/data_design/character_creator/full_process/technical/validation/VISUAL_REVIEW.md) |
| `projects/` | 轻量 UE 配置与 Smoke 工程 | [服务器执行](../20_planning/data_design/character_creator/full_process/technical/rendering_release/SERVER_EXECUTION.md) |
| `assets/` | 资产台账、Manifest 和哈希 | [资产追溯](../20_planning/data_design/character_creator/full_process/technical/transfer/ASSET_TRACEABILITY.md) |
| `outputs/` | 本地运行产物、证据和当前数据构建 | [输出盘点与保留](../20_planning/data_design/character_creator/full_process/technical/output/INVENTORY_AND_RETENTION.md) |
| `cache/` | 可重建缓存和临时工作文件 | 不进入生产 Manifest |
| `runtime/` | Linux 用户态依赖和运行补丁 | [服务器执行](../20_planning/data_design/character_creator/full_process/technical/rendering_release/SERVER_EXECUTION.md) |
| `unreal/` | UE 安装、MCP 和运行环境说明 | [环境与会话](../20_planning/data_design/character_creator/full_process/technical/environment/ENVIRONMENT_AND_SESSION.md) |

## 代码与输出目录

脚本是否可用于生产不由本页判断。机器目录为：

```text
scripts/SCRIPT_CATALOG.json
outputs/RETENTION_POLICY.json
outputs/OUTPUT_INVENTORY.json
```

`outputs/` 中包含大量历史验证结果。只有保留策略明确标记为 `superseded` 或 `disposable` 的路径，经过替代证据核验后才可成为清理候选；`unclassified` 默认保护。

## Git 边界

Git 只保存代码、配置、Manifest、哈希和适合版本控制的证据。CC 二进制资产、正式 UE `Content/`、`.uasset/.umap`、DDC 与批量媒体不因位于工作区而自动进入 Git，但必须通过 Registry 和交付 Manifest 追溯。

## 校验

```powershell
python 00_engine/scripts/documentation/build_script_lifecycle_catalog.py
python 00_engine/scripts/documentation/build_output_inventory.py
python 00_engine/scripts/documentation/check_character_factory_docs.py --json
```
