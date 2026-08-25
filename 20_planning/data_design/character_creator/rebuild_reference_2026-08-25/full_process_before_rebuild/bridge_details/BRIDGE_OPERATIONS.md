# Character Creator Bridge 技术与维护规范

> 文档角色：`technical_specification`
> 状态：`validated_pilot`
> 适用阶段：`WF-00,WF-02,WF-03`
> 权威范围：Bridge 组件、协议、队列、allowlist、弹窗守卫和安装维护
> 上级入口：[`README.md`](./README.md)
> 上游：[`ADR-0009`](../decisions/ADR-0009-RESTRICTED-OFFLINE-BRIDGE.md)、代码与 `bridge_config.json`
> 下游：[`WF-00`](../workflow/WF-00-SESSION-PREFLIGHT.md)、[`WF-02`](../workflow/WF-02-CC-ASSEMBLY.md)、[`RECOVERY_RUNBOOK.md`](../validation/RECOVERY_RUNBOOK.md)
> 最近核验：2026-08-06

## 1. 作用与边界

Bridge 是系统 Python 与 CC5/RLPy 之间的受控离线文件队列。它不执行任意 Python，不远程操纵未知弹窗，也不证明角色视觉正确。每日生产健康检查由 `WF-00` 调用，准确测试命令只在 `VAL-BRIDGE-01`。

## 2. 当前组件

```text
LANCE_ROOT = D:\UE\Lance_Work
BRIDGE_ROOT = %LANCE_ROOT%\00_engine\character_creator_bridge
RUNTIME_ROOT = %LANCE_ROOT%\00_engine\outputs\character_creator_bridge
```

| 文件 | 职责 |
| --- | --- |
| `bridge_config.json` | 协议、轮询、lease、大小限制和输入/输出 allowlist |
| `plugin/main.py` | CC OpenPlugin 单消费者 worker |
| `cc_bridge_client.py` | 系统 Python CLI |
| `protocol_v1.md` | request/result/heartbeat 线协议 |
| `install_bridge.ps1` | 受控安装并核对源/目标哈希 |
| `cc_undo_dialog_guard.ps1` | 只处理精确匹配的 Undo 警告 |

当前 `bridge_id=lance_cc_bridge`、插件 `0.2.0`、协议 1、轮询 500 ms、心跳 1 s、活动 lease 5 s、最大请求 1 MiB。

## 3. 安装或更新

这是 Bridge 维护命令，不属于每次生产。前置：关闭 CC，并由用户确认离线许可证启动条件。

```powershell
$LANCE_ROOT = 'D:\UE\Lance_Work'
& "$LANCE_ROOT\00_engine\character_creator_bridge\install_bridge.ps1" `
  -CharacterCreatorRoot 'D:\CharacterCreator\Character Creator 5'
```

安装目标为 `D:\CharacterCreator\Character Creator 5\Bin64\OpenPlugin\LanceCCBridge\main.py`。通过要求 `success=true`、源/安装 SHA-256 一致并产生 `install_manifest.json`。安装后由用户重启 CC，再从 `WF-00` 验证。

## 4. Runtime 状态机

```text
inbox/              原子提交的新请求
processing/         worker 已领取请求
completed_requests/ 成功请求归档
failed_requests/    失败或拒绝请求归档
results/            终态结果 JSON
state/heartbeat.json
logs/
artifacts/          唯一允许输出根
dialog_guard/       Undo 守卫审计 JSONL
```

CC UI 线程每次只执行一个作业。终态结果存在时，相同 job ID 不重复执行。v1 不自动清理历史请求或结果。

## 5. 安全边界

允许输入根由 `bridge_config.json` 决定，当前覆盖 CC 脚本、Face recipe 输出、Reallusion Templates 和 Custom CC Project。唯一输出根是 `outputs\character_creator_bridge\artifacts`。

动态请求/Manifest 暂存于 `scripts\character_creator\runtime_staging\<run_id>`，完成后复制到 artifacts 并核对哈希。路径逃逸、未知命令、超限请求或缺少破坏性确认会被拒绝。

## 6. 命令语义

| CLI | 当前语义 | 生产入口 |
| --- | --- | --- |
| `health/ping/scene-summary` | heartbeat、队列消费和 RLPy 场景访问 | `VAL-BRIDGE-01` |
| `validate-bodies` | BodyFit 或完整兼容 Manifest 执行 | `WF-02` |
| `wait/result` | 异步 job 终态读取 | 由调用 Workflow/Validation 使用 |
| `apply-face` | 旧 `target_face_morphs` schema | 仅历史诊断，不用于 Face V3 |

job ID 必须匹配 `[A-Za-z0-9][A-Za-z0-9_.-]{7,127}`。当前没有正式 `assemble-character`、通用项目保存、取消或批量分块 API；这些只能在 Roadmap 中描述。

## 7. Undo 守卫

`--auto-dismiss-undo-warning` 只在 PID、窗口标题、类名、完整文本和唯一 OK 按钮全部匹配时点击，并写入 `dialog_guard/<job-id>.jsonl`。Replace/Material、Character Preset、Save 或未知弹窗不会自动处理。

## 8. 故障语义

`heartbeat_missing/stale` 表示当前 worker 不在线；`busy` 必须结合 active job、lease 和日志解释；`rejected` 表示安全/schema 问题；`failed` 表示执行器终态失败。不得改结果文件或重复相同 job ID。

准确恢复步骤见 [`REC-BRIDGE-01`](../validation/RECOVERY_RUNBOOK.md) 和 [`REC-DIALOG-01`](../validation/RECOVERY_RUNBOOK.md)。恢复后必须重做 `GATE-00`。
