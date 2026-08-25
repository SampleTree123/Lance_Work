# Character Creator 离线 Bridge

> 文档 ID：`TECH-BRIDGE-01`
> 文档类型：`technical`
> 生命周期：`current`
> 适用阶段：`WF-00/WF-30`
> 实现所有权：`00_engine/character_creator_bridge/`、CC `OpenPlugin` 和 `cc_validate_body_reconstruction.py`
> 验证所有权：`VAL-BRIDGE-01`
> 输出契约：`OUT-WF00-SESSION`、`OUT-WF30-CC-ASSETS`
> 最近核验：2026-08-25

## 1. 能力与边界

Bridge 使用本地原子 JSON 文件队列，让外部编排器调用已安装在 CC5 中的受控 RLPy 命令。它不接受任意 Python 源码，不绕过 CC 模态窗口，也不授权 Agent 自行重启 CC。

## 2. 实现组成

| 文件 | 角色 | 生命周期 |
| --- | --- | --- |
| `bridge_config.json` | 路径、协议、轮询、Lease 和 allowlist | `production` |
| `protocol_v1.md` | Request/Result/Heartbeat 契约 | `production` |
| `plugin/main.py` | CC `OpenPlugin` 单消费者 | `validated_pilot` |
| `cc_bridge_client.py` | 系统 Python CLI | `validated_pilot` |
| `cc_undo_dialog_guard.ps1` | 精确匹配 Undo 警告的可选守卫 | `utility` |
| `install_bridge.ps1` | 受控插件安装 | `utility` |
| `cc_validate_body_reconstruction.py` | 多模式 RLPy 执行器 | `validated_pilot`，按模式限定 |

## 3. 验证与健康检查

```powershell
$Client = 'D:\UE\Lance_Work\00_engine\character_creator_bridge\cc_bridge_client.py'
python $Client health
python $Client ping
python $Client scene-summary
```

通过条件：Heartbeat 新鲜、进程 ID 与当前 CC 一致、`ping` 终态成功、`scene-summary` 能读取当前 Avatar。

## 4. 作业协议

```text
client -> atomic request JSON -> CC plugin -> allowlisted RLPy command
client <- terminal result JSON <- CC plugin
```

每个作业必须有唯一 ID、Lease、终态结果和版本。运行输入通常先编译到：

```text
%CC_SCRIPT_ROOT%/runtime_staging/<run_id>/
```

该目录是临时 Bridge 输入，不进入 Git。真正机器配置仍由版本化 Registry/Manifest 决定。

## 5. BodyFit 与完整角色入口

`validate-bodies` 名称保留了历史技术债务，但当前也可分发兼容的完整角色 Manifest：

```powershell
python $Client validate-bodies --help
```

执行前必须由对应 Technical 文档生成准确配置。不得仅因命令名相同就把实验模式用于生产。

## 6. 弹窗守卫

Undo 守卫只在以下全部匹配时点击 `OK`：CC 进程 ID、窗口标题、完整提示文本和按钮标签。每次处理写入：

```text
%OUTPUT_ROOT%/character_creator_bridge/dialog_guard/<job-id>.jsonl
```

资产替换、许可、保存、Apply Cloth Options 和未知窗口不允许通用自动确认。

## 7. 输出与保留

作业目录至少保留 Request、Result、运行配置、失败窗口和关键报告。生产角色/Look 作业为 `retained_evidence`；Heartbeat、临时 staging 和无异常轮询日志为 `disposable`。

## 8. 恢复

1. 先停止提交新作业。
2. 判断作业是否已有终态；不得为同一 ID 重复执行有副作用命令。
3. 未知窗口交由用户处理。
4. CC 重启后等待新 Heartbeat，再从阶段入口重跑。
5. 资源持续增长时按角色/Look 分批并在批间由用户重启 CC。

完整故障分类见 [恢复手册](../validation/RECOVERY.md)。
