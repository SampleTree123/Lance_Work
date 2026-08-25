# Character Creator Bridge 操作手册

> 文档角色：`operational_runbook`
> 状态：`validated_pilot`
> 上级入口：[`../CHARACTER_FACTORY_MASTER_SPEC.md`](../CHARACTER_FACTORY_MASTER_SPEC.md)
> 最近核验：2026-08-06

## 1. 组件和配置

```text
LANCE_ROOT = D:\UE\Lance_Work
BRIDGE_ROOT = %LANCE_ROOT%\00_engine\character_creator_bridge
RUNTIME_ROOT = %LANCE_ROOT%\00_engine\outputs\character_creator_bridge
```

| 文件 | 职责 |
| --- | --- |
| `bridge_config.json` | 协议、轮询、lease、输入/输出 allowlist 和执行器路径 |
| `plugin/main.py` | CC5 OpenPlugin 单消费者 worker |
| `cc_bridge_client.py` | 系统 Python CLI |
| `protocol_v1.md` | 请求、结果、心跳和恢复契约 |
| `install_bridge.ps1` | 受控安装并核对哈希 |
| `cc_undo_dialog_guard.ps1` | 精确匹配 Undo Manager 警告 |

当前 `bridge_id=lance_cc_bridge`、插件版本 `0.2.0`、协议版本 1。轮询 500 ms、心跳 1 s、活动 lease 5 s、最大请求 1 MiB。

## 2. BRIDGE-01：安装或更新

- 模式：`POWERSHELL`
- 前置：关闭 CC；用户确认离线许可证启动条件。

```powershell
$LANCE_ROOT = 'D:\UE\Lance_Work'
& "$LANCE_ROOT\00_engine\character_creator_bridge\install_bridge.ps1" `
  -CharacterCreatorRoot 'D:\CharacterCreator\Character Creator 5'
```

安装目标：

```text
D:\CharacterCreator\Character Creator 5\Bin64\OpenPlugin\LanceCCBridge\main.py
```

通过条件：命令返回 `success=true`，源和安装文件 SHA-256 一致，并生成 `install_manifest.json`。安装后必须由用户重新启动 CC；Agent 不自动启动或重启 CC。

## 3. BRIDGE-02：健康检查

```powershell
$client = "$LANCE_ROOT\00_engine\character_creator_bridge\cc_bridge_client.py"
python $client health
python $client ping
python $client scene-summary
```

`health` 通过条件：

- `state/heartbeat.json` 可解析。
- 协议版本匹配。
- `state` 为 `idle` 或 `busy`。
- `updated_at` 不超过 5 秒 lease。

`ping` 证明 worker 能消费请求；`scene-summary` 证明 `RLPy` 可访问场景。只看到配置文件或 CC UI 不能视为 Bridge 已连接。

## 4. Runtime 目录

```text
character_creator_bridge/
  inbox/              原子提交的新请求
  processing/         当前 worker 已领取请求
  completed_requests/ 成功请求归档
  failed_requests/    失败或拒绝请求归档
  results/            终态结果 JSON
  state/heartbeat.json
  logs/
  artifacts/          命令输出的唯一允许根
  dialog_guard/       Undo 守卫审计 JSONL
```

每次只在 CC UI 线程执行一个作业。v1 不自动清理请求和结果。

## 5. 输入与输出 allowlist

当前允许输入根：

```text
D:\UE\Lance_Work\00_engine\scripts\character_creator
D:\UE\Lance_Work\00_engine\outputs\character_creator_face_recipes
D:\CharacterCreator_sucai\Reallusion Templates
D:\CharacterCreator_sucai\Reallusion Custom\Project\CC Project
```

唯一允许输出根：

```text
D:\UE\Lance_Work\00_engine\outputs\character_creator_bridge\artifacts
```

因此动态请求/manifest 必须先在允许输入根中暂存；运行完成后复制到 artifacts 保存证据。路径逃逸、超限或未知命令会被拒绝。

## 6. 命令

### BRIDGE-03：异步提交与结果

```powershell
$jobId = 'bodyfit_smoke_20260806_001'
$library = "$LANCE_ROOT\00_engine\scripts\character_creator\cc_body_preset_library_v2.json"
$output = "$LANCE_ROOT\00_engine\outputs\character_creator_bridge\artifacts\$jobId"

python $client validate-bodies `
  --library-file $library `
  --preset-id M02_Average `
  --output-dir $output `
  --confirm-scene-replace `
  --auto-dismiss-undo-warning `
  --job-id $jobId `
  --no-wait

python $client wait $jobId --timeout 3600
python $client result $jobId
```

job ID 必须匹配 `[A-Za-z0-9][A-Za-z0-9_.-]{7,127}`。终态结果存在时，同 ID 请求不会重复执行。

### BRIDGE-04：BodyFit 或完整兼容 manifest

```powershell
python $client validate-bodies `
  --library-file <allowed-input.json> `
  --preset-id <optional-preset-id> `
  --output-dir <new-artifact-directory> `
  --confirm-scene-replace `
  --auto-dismiss-undo-warning
```

虽然 CLI 名称是 `validate-bodies`，实际 RLPy 执行器可读取包含完整面部/外观字段的兼容 manifest。这是当前完整角色 Pilot 的真实入口，不代表已有正式 `assemble-character` API。

### BRIDGE-05：`apply-face`

该命令仍存在，但插件要求旧字段 `target_face_morphs`。当前 Face V3 使用 `primary_face_seed_id + local_morphs + Facial Profile`，因此不得把 `cc_face_recipes_v3_200.json` 提交给 `apply-face`。该命令只保留历史兼容和诊断用途。

## 7. Undo 警告守卫

`--auto-dismiss-undo-warning` 会启动外部 PowerShell 守卫。只有以下条件全部匹配才点击 `OK`：

- 目标 CC PID。
- Character Creator 对话框标题。
- `QMessageBox` 类名。
- 完整已知警告文本。
- 唯一 `OK` 按钮。

每次处理写入 `dialog_guard/<job-id>.jsonl`。Replace/Material、Character Preset 或任何未知弹窗不会自动处理。

## 8. 恢复

| 症状 | 处理 |
| --- | --- |
| `heartbeat_missing` | 确认插件已安装，用户重启 CC，再检查 Plugins 菜单 |
| `heartbeat_stale` | 不提交；确认 CC 是否关闭/崩溃，用户恢复后等待新 instance ID |
| `busy` 长时间不变 | 读取 heartbeat active job、日志和 processing；不要重复同 job ID |
| `rejected` | 检查命令、请求大小、确认标志和 allowlist，不改结果文件 |
| `failed` | 保存 traceback、job ID 和 artifacts；用新 job ID/新输出目录重跑 |
| CC 崩溃 | 重启后插件把 orphan processing 请求写成 failed，不手工伪造成功结果 |
| 未知弹窗 | 停止等待用户，不扩宽自动点击规则 |

恢复后先重新执行 `health → ping → scene-summary`。完整质量和内存停止条件见 [`../validation/VALIDATION_AND_RECOVERY.md`](../validation/VALIDATION_AND_RECOVERY.md)。

## 9. 计划中的接口

后续专用接口应至少覆盖完整角色装配、项目保存、任务状态、取消和批量分块。实现前只记录在 Roadmap；不得在请求协议中预留未实现命令并宣称可用。
