# WF-00 会话与运行环境预检

> 文档角色：`workflow_runbook`
> 状态：`validated_pilot`
> 适用阶段：`WF-00`
> 权威范围：每次生产会话的启动顺序与在线状态确认
> 上级入口：[`README.md`](./README.md)
> 上游：无，生产主线入口
> 下游：[`WF-01-CHARACTER-DEFINITION.md`](./WF-01-CHARACTER-DEFINITION.md)
> 最近核验：2026-08-06

## 1. 目的与使用时机

每个新会话、CC/UE 重启、崩溃恢复、网络切换或 Bridge/MCP 配置变化后执行。本阶段只确认环境真实可用，不创建角色、不导入资产。

## 2. 当前范围与非目标

当前可以确认系统 Python、CC Bridge、CC/RLPy、UE 5.8 工程和 UE Remote/MCP 各自状态。配置文件存在不等于服务在线；`/mcp` 中出现工具也不等于编辑器端调用已成功。

## 3. 进入条件

- 用户已保存需要保留的 CC/UE 工作。
- CC 必须由用户在学校离线许可证条件下启动；Agent 不自动启动或重启 CC。
- 当前无未知模态弹窗。
- CC private memory 低于 24 GB。

## 4. 输入与输出

输入是当前机器会话和目标工作段。输出是一次 `GATE-00` 判定，至少记录时间、CC instance ID、Bridge 协议/插件版本、目标 UE 工程和实际可用通道。

## 5. 执行环境

```powershell
$LANCE_ROOT = 'D:\UE\Lance_Work'
$ccScriptRoot = "$LANCE_ROOT\00_engine\scripts\character_creator"
$bridgeRoot = "$LANCE_ROOT\00_engine\character_creator_bridge"
$bridgeClient = "$bridgeRoot\cc_bridge_client.py"
$ueScriptRoot = "$LANCE_ROOT\00_engine\scripts\unreal"
$outputRoot = "$LANCE_ROOT\00_engine\outputs"
$ueProject = 'datatry_02'
```

CC 段使用 `SYSTEM_PYTHON + BRIDGE_CLI`。UE 段使用 `UE_UI`、`UE_REMOTE` 或 `UE_MCP`；三者不能互相代替。

## 6. 执行步骤

1. 确认本轮是 CC 段还是 UE 段，仅启动必要的重型应用。
2. 若本轮修改过 Python、Bridge 或机器 JSON，先执行 `VAL-CODE-01`。
3. 任何 CC 作业前执行 `VAL-BRIDGE-01`，必须同时通过 heartbeat、ping 和 RLPy scene summary。
4. UE 段确认工程为 `D:\UE\projects\datatry_02`，不处于 PIE/Simulate，脏包状态已知。
5. 需要 UE Remote 时单独确认 Python Remote Execution；需要 MCP 时单独做一次无副作用工具调用。
6. 检查未知弹窗、待恢复包和未解释的活动 job；存在任一项则停止。

准确测试命令及其证明边界见 [`VALIDATION_CATALOG.md`](../validation/VALIDATION_CATALOG.md)。

## 7. 退出门禁

执行 [`GATE-00 SESSION_READY`](../validation/README.md)。CC 生产至少要求 `VAL-BRIDGE-01`；`VAL-CODE-01` 仅在代码或机器配置变化后强制执行。未使用的 UE 通道可以记为 `not_required`，不能记为通过。

## 8. 失败与恢复

heartbeat 过期、CC 崩溃、未知弹窗、UE 恢复包或 Remote/MCP 离线时，按 [`RECOVERY_RUNBOOK.md`](../validation/RECOVERY_RUNBOOK.md) 对应 `REC-*` 处理。恢复后重新执行整个 `WF-00`。

## 9. 技术依据与下一阶段

Bridge 组件、安全边界和安装方法见 [`BRIDGE_OPERATIONS.md`](../bridge_details/BRIDGE_OPERATIONS.md)，外部路径见 [`EXTERNAL_DIRECTORIES.md`](../reference/EXTERNAL_DIRECTORIES.md)。通过后进入 [`WF-01`](./WF-01-CHARACTER-DEFINITION.md)。

