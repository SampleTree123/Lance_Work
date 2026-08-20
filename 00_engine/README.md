# 00_engine：生产实现与运行产物

本目录承载 Character Creator、Unreal Engine、配置图和可视化检查的实际实现。项目状态与执行顺序仍以根目录 [`HANDOFF.md`](../HANDOFF.md) 和角色工厂 [`CURRENT_STATUS.md`](../20_planning/data_design/character_creator/full_process/CURRENT_STATUS.md) 为准。

## 目录职责

| 路径 | 用途 | 当前状态 |
| --- | --- | --- |
| [`scripts/`](./scripts/README.md) | CC/UE 自动化、配置图、文档校验和测试 | 活跃 |
| [`character_creator_bridge/`](./character_creator_bridge/README.md) | CC5 文件队列通信与作业执行 | Pilot 已验证 |
| [`visualization_portal/`](./visualization_portal/README.md) | 截图、动作、服装和实验结果审查页面 | 可用工具 |
| `projects/` | 轻量 UE 项目配置与服务器 smoke 工程 | 不包含正式大型 Content |
| `assets/` | 资产台账、许可状态、manifest 与哈希 | 持续维护 |
| `outputs/` | 小型、可复核的自动化证据 | 大型生成物不进 Git |
| `cache/` | DDC、临时文件和可再生成缓存 | 不进 Git |
| `runtime/` | Linux 用户态依赖等运行补丁 | 按需使用 |
| `unreal/` | UE 5.8 安装、MCP 和运行环境说明 | 本地/服务器入口 |

JSON 配置与其执行代码同目录保存：CC 配置位于 `scripts/character_creator/`，UE 配置位于 `scripts/unreal/`，数据图配置位于 `scripts/dataset/`，资产注册表位于 `assets/`。

## 第一批生产状态

- 8 个身份与 16 个 FullReference Look 已冻结和导出；
- 12 个动作的 5 秒窗口已冻结，Motion FBX/UE 门禁待完成；
- Happy、Angry、Sad 的 UE 轻动态表情已通过机器门禁，待动态人工签字；
- 配置图生成器可生成 384 个唯一节点与 4,000 条链；
- 正式场景、相机、Sequence、唯一节点渲染和 sidecar 管线尚待贯通；
- 服务器环境预检脚本已就绪，项目 smoke 与 10 节点基准需在资产包上传后执行。

## 当前入口

- 实现索引：[`IMPLEMENTATION_INDEX.md`](../20_planning/data_design/character_creator/full_process/reference/IMPLEMENTATION_INDEX.md)
- 当前 Sprint：[`FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md`](../20_planning/data_design/character_creator/full_process/planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md)
- 服务器 Runbook：[`FIRST_BATCH_SERVER_RUNBOOK.md`](../20_planning/implementation/FIRST_BATCH_SERVER_RUNBOOK.md)
- 服务器预检：[`FIRST_BATCH_SERVER_PREFLIGHT.sh`](../20_planning/implementation/FIRST_BATCH_SERVER_PREFLIGHT.sh)

## 存储边界

Git 中只保留代码、配置、manifest、哈希和小型证据。CC 二进制资产、正式 UE `Content/`、`.uasset`、`.umap`、DDC、视频和批量截图通过独立资产包管理，不能直接加入仓库。
