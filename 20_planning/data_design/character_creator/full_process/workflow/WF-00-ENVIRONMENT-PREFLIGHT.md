# WF-00 环境与会话预检

> 文档 ID：`WF-00`
> 文档类型：`workflow`
> 生命周期：`current`
> 前序：无
> 后序：`WF-10`
> Exit Gate：`GATE-00 SESSION_READY`
> 最近核验：2026-08-25

## 1. 目的与使用时机

在新对话、机器切换、应用重启、崩溃恢复或通信方式变化后，证明本轮需要的文件系统、代码、CC、UE 和服务器通道真实可用。

## 2. 前后序与进入条件

- 前序：无。任何后续阶段都可以因新会话、应用重启、机器切换或崩溃恢复而重新进入本阶段。
- 后序：按当前计划进入 `WF-10`，或返回此前中断的阶段。
- 已知本轮需要哪些应用和执行环境。
- 不把“配置存在”当作“连接成功”。

## 3. 输入

本机路径映射、Git 工作区、Python 环境、应用状态和本轮所需通信通道。

## 4. 正常流程

| 步骤 | 操作 | 精确实现或机器入口 | 本步输出 |
| --- | --- | --- | --- |
| 1. 检查工作区 | 检查路径映射、磁盘、Git 改动和当前配置版本 | 命令与边界由 [环境与会话](../technical/environment/ENVIRONMENT_AND_SESSION.md#3-本地输入与预检) 维护；文档审计入口为 [`check_character_factory_docs.py`](../../../../../00_engine/scripts/documentation/check_character_factory_docs.py) | 工作区与代码基线结果 |
| 2. 验证 CC 通道 | 仅在本轮需要 CC 时检查新鲜 Heartbeat、`ping` 和 `scene-summary` | [`cc_bridge_client.py`](../../../../../00_engine/character_creator_bridge/cc_bridge_client.py) 与 CC 端 [`plugin/main.py`](../../../../../00_engine/character_creator_bridge/plugin/main.py)；准确命令见 [Bridge Technical](../technical/bridge/CC_BRIDGE_OPERATIONS.md#3-验证与健康检查) | 当前 CC 进程绑定的 Bridge 结果 |
| 3. 验证 UE 通道 | 仅在本轮需要 UE 时确认项目、插件、MCP/Remote Execution 和无阻塞窗口 | 系统入口 [`ue_remote_exec.py`](../../../../../00_engine/scripts/unreal/ue_remote_exec.py)；具体无副作用查询由 [环境与会话](../technical/environment/ENVIRONMENT_AND_SESSION.md#5-ue-会话) 规定 | 当前 UE 会话和目标项目结果 |
| 4. 验证服务器环境 | 仅在需要服务器时检查 Slurm、Linux、GPU、Vulkan、UE 和磁盘，不启动生产渲染 | [`FIRST_BATCH_SERVER_PREFLIGHT.sh`](../../../../../20_planning/implementation/FIRST_BATCH_SERVER_PREFLIGHT.sh) 的 `--environment-only` 模式；完整说明见 [服务器执行](../technical/rendering_release/SERVER_EXECUTION.md#2-预检入口) | 服务器环境预检报告 |
| 5. 汇总本轮范围 | 把必需/非必需通道、失败原因和允许进入阶段写入会话结果 | 当前没有跨本地、CC、UE、服务器的一键聚合器；按 [Output Run Root](../technical/output/OUTPUT_CONTRACTS.md#5-run-root-契约) 和 [WF-00 状态](../project_management/status/workflows/WF-00.md) 记录 | `OUT-WF00-SESSION` |

本阶段是按需预检，不要求同时启动 CC 与 UE。第 5 步尚为受控记录流程，不能把任一单独命令成功描述为完整 `GATE-00`。

## 5. 输出契约

| 输出 ID | 逻辑产物 | 存储类别 | 生产所有者 |
| --- | --- | --- | --- |
| `OUT-WF00-SESSION` | 本轮会话预检结果、失败通道和允许进入的下一阶段 | `run_evidence`；可在无长期价值时为 `disposable` | [环境与会话](../technical/environment/ENVIRONMENT_AND_SESSION.md) |

### 输出组成、用途与下游

| 组成 | 实际内容 | 为什么需要 | 下游消费者 |
| --- | --- | --- | --- |
| 会话范围 | 本轮机器、项目、应用、所需通道、版本和路径别名 | 防止把未使用或未验证的通道误写成通过 | 本轮恢复逻辑和所有后续 Workflow |
| 通道结果 | 本地测试、CC Bridge、UE MCP/Remote Execution、服务器环境的逐项状态 | 证明当前进程/机器真实可执行，而不只是配置存在 | 依赖对应应用的 `WF-10`–`WF-90` |
| 失败与停止信息 | 阻塞窗口、权限、路径漂移、版本冲突、日志和恢复入口 | 支撑安全恢复并避免重复有副作用作业 | [恢复手册](../technical/validation/RECOVERY.md) 与 `VAL-ENV-01/VAL-BRIDGE-01` |
| 允许进入阶段 | 当前可继续的唯一 Workflow 和不适用通道 | 把预检结论转换为明确执行边界 | [项目状态](../project_management/status/PROJECT_STATUS.md) |

当前活动会话位置由 [WF-00 状态](../project_management/status/workflows/WF-00.md#当前输出与证据) 指定；稳定内容、Manifest 和保留规则见 [输出契约目录](../technical/output/OUTPUT_CONTRACTS.md#31-out-wf00-session)。

## 6. 必需验证

| 验证 ID | 角色 | 何时需要 |
| --- | --- | --- |
| `VAL-ENV-01` | `required` | 每次进入本阶段都执行，范围只覆盖本轮实际需要的环境 |
| `VAL-BRIDGE-01` | `conditional` | 本轮需要 CC Bridge 时执行；应用重启后旧结果失效 |

定义、证据和通过条件见 [验证目录](../technical/validation/VALIDATION_CATALOG.md)。

## 7. Exit Gate

`GATE-00 SESSION_READY` 要求所有本轮必需通道均通过；非必需应用可以关闭。任一通道未知时不得在依赖它的阶段继续。

## 8. 技术与状态

- [环境与会话](../technical/environment/ENVIRONMENT_AND_SESSION.md)
- [CC Bridge](../technical/bridge/CC_BRIDGE_OPERATIONS.md)
- [文档验证](../technical/validation/DOCUMENTATION_VALIDATION.md)
- [当前 WF-00 状态](../project_management/status/workflows/WF-00.md)

## 9. 失败与恢复

按 [恢复手册](../technical/validation/RECOVERY.md) 处理。CC 不由 Agent 擅自重启；UE 恢复包、未知窗口和权限不一致必须显式确认。
