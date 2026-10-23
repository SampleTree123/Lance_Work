# 环境与会话预检实现

> 文档 ID：`TECH-ENV-01`
> 文档类型：`technical`
> 生命周期：`current`
> 适用阶段：`WF-00`
> 实现所有权：Git/Python 检查、CC Bridge 健康检查、UE MCP/Remote Execution 和服务器预检
> 验证所有权：`VAL-ENV-01`
> 输出契约：`OUT-WF00-SESSION`
> 最近核验：2026-10-01

## 1. 能力与边界

本能力验证本轮所需环境是否真实可执行。它不启动生产任务，不把已安装插件等同于已连接通道，也不自动恢复未知弹窗。

## 2. 三种 Python 环境

| 环境 | 可运行内容 | 禁止内容 |
| --- | --- | --- |
| 系统 Python | 生成器、编排器、JSON/媒体/文档测试 | 直接 `import RLPy` 或 `unreal` |
| CC 内 Python/RLPy | `cc_validate_body_reconstruction.py` 等 CC 执行逻辑 | 由普通 Conda/Python 直接启动 |
| UE Python | `ue_*.py` 任务 | 由系统 Python直接导入 `unreal` |

系统编排器通常通过 CC Bridge 或 `ue_remote_exec.py` 进入应用内环境。

## 3. 本地输入与预检

```powershell
$LanceRoot = 'D:\UE\Lance_Work'
git -C $LanceRoot status --short
python "$LanceRoot\00_engine\scripts\documentation\check_character_factory_docs.py" --json
python -m pytest `
  "$LanceRoot\00_engine\scripts\documentation\tests" `
  "$LanceRoot\00_engine\scripts\dataset\tests" `
  "$LanceRoot\00_engine\scripts\unreal\tests" `
  "$LanceRoot\00_engine\visualization_portal\tests" -q
```

工作区允许存在用户改动，但任何自动格式化、移动和删除都不得覆盖未识别改动。

## 4. CC 会话

1. CC 由用户按离线环境要求启动。
2. 运行 Bridge `health`、`ping` 和 `scene-summary`。
3. 心跳必须是本次启动的新鲜记录。
4. 未知弹窗、Undo Manager 警告或长期无响应按 Bridge/恢复文档处理。

准确命令见 [CC Bridge](../bridge/CC_BRIDGE_OPERATIONS.md)。Agent 不擅自联网启动或重启 CC。

## 5. UE 会话

1. 确认项目为 `%UE_PROJECT_ROOT%`，目标版本与项目插件一致。
2. 确认没有恢复包、FBX 导入窗口、Auto Setup 或未保存提示。
3. 从 MCP 工具列表或 Remote Execution 执行无副作用查询。
4. 需要交互窗口守卫时，守卫与 UE 必须使用相同 Windows 权限级别。

UE Editor 可见并不证明 Remote Execution 正常；每次崩溃或重启后重新验证。

## 6. 服务器环境

服务器预检入口为：

```bash
bash 20_planning/implementation/FIRST_BATCH_SERVER_PREFLIGHT.sh --environment-only
```

该入口必须在实际服务器版本再次验证。完整边界见 [服务器执行](../rendering_release/SERVER_EXECUTION.md)。

## 7. 输出与保留

预检输出保存环境版本、路径、插件、GPU、通道和失败原因。当前批次首次服务器预检属于 `retained_evidence`；重复无变化的本地健康检查可以是 `disposable`。

## 8. 验证与停止条件

- 当前自动测试全部通过才允许声明代码基线健康。
- 任一必需通信通道失败时停止依赖它的阶段。
- 未知模态窗口、权限不一致、路径漂移和项目版本不符均为硬停止条件。

## 9. 清理后的本地环境入口

2026-10-01 清理后，项目编辑器启动关卡为 `/Game/DataMake/Validation/ScalpHairFit/L_DM_ScalpHairFit_Review_v001`；原早期 `/Game/Main` 与旧对照/P0 关卡已审查退役。第一批渲染仍由锁定配置显式指定场景/Sequence，不依赖编辑器启动地图。当前审查入口及加载条件见 [角色运行时](../unreal/CHARACTER_RUNTIME.md)。

独立 UE Python 命令行进程可以在没有可见编辑器窗口时执行包查询、组装、保存与重载；这仍启动了真正的 UE 进程，并非系统 Python 自行读取或渲染 uasset。可见编辑器、命令行进程和 Remote Execution 属于不同会话，不能仅凭是否有窗口推断任务正在运行。核验以对应日志、实际输出、保存态重载和退出结果为准。

旧隔离测试的运行时 profile、Zen 与 shader 工作缓存已按精确清单清除；工程编译依赖、引擎安装、当前素材、未知用途的历史输入仍保留。CC 在本轮保持关闭，原生 Custom 内容只移除六份逐字节相同且有保留替代的 staging 项目；没有重新启动 CC 或将未运行的 CC 会话检查写成通过。详情见 `%OUTPUT_ROOT%/asset_cleanup/cleanup_20261001_v1/README.md`。
