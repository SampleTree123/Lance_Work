# Character Creator 离线 Bridge

> 文档 ID：`TECH-BRIDGE-01`
> 文档类型：`technical`
> 生命周期：`current`
> 适用阶段：`WF-00/WF-30`
> 实现所有权：`00_engine/character_creator_bridge/`、CC `OpenPlugin` 和 `cc_validate_body_reconstruction.py`
> 验证所有权：`VAL-BRIDGE-01`
> 输出契约：`OUT-WF00-SESSION`、`OUT-WF30-CC-ASSETS`
> 最近核验：2026-10-02（弹窗处理实现静态核对；不扩大运行验收范围）

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

`validate-bodies --auto-dismiss-undo-warning` 启动 `cc_undo_dialog_guard.ps1`，通过 Windows 控件 `InvokePattern` 执行精确匹配按钮；该守卫不调用前台激活或模拟鼠标输入。CC 内部另有 `ExactUndoWarningGuard` 的 Qt 定时器以及 `load_file_with_known_cc_dialogs` 的素材专用处理，直接调用已识别控件。内部定时器能否处理同步原生调用期间的弹窗取决于事件循环，不能代替所有外部恢复。当前外部守卫还精确识别导出许可不足提示，记录 `fatal_dialog.json` 后关闭该提示；这不购买许可、不解锁内容、不使失败导出通过。未知窗口只记录。

2026-10-02 Headshot diagnostic 模式在 `run_library` 中提前分发，跳过上述通用运行期守卫，故本轮曾改用 Computer Use。用户于 2026-10-03 先停止、随后重新允许必要时使用 Computer Use，用完停止；当前优先接口和后台专用处理，不长期占用前台。已核对旧代码与历史日志；本次静态核对不等于守卫已在当前 Headshot 会话重新启用。触发 Undo 的眼部 SDK 查询已在实验模式避开，但面部配置升级仍曾触发同类提示，不能宣称全流程无弹窗。

2026-10-03 路线验证器的眼睛/牙齿支持加载重新接入既有 Qt `load_file_with_material_only_dialog`，仅允许 `.ccEye/.ccTeeth` 并校验来源 SHA。`headshot_route_compare_20261002_v1/r1_male_02_texture_validation_v1/route_validation_report.json` 已记录两次精确匹配、各点击一次 Material Only，未占用 Computer Use。整套 `.ccSkin` 预处理另复用已识别的皮肤设置弹窗处理。该小范围实测不等于 Headshot 的所有弹窗均能自动处理，未知弹窗仍须观察。

同轮材质诊断新增 `load_file_with_known_cc_dialogs` 的显式 `preserve_head_textures=True`，仅在已要求皮肤材质策略时允许使用：局部复制开关集合，把 Ignore Head Diffuse Texture 与 Ignore Head Normal Texture 设为 true，不修改默认策略。`r1_male_02_preserve_head_skin_v1` 记录一次精确匹配和一次 Apply；头部照片保留，但严格 SHA 检查失败且头身色差未解决。隐藏的 Apply Head Color to Body 控件不算可见操作或功能生效证据。此模式是诊断支持，不是已接受的肤色修复，结果 owner 为 [BodyFit Technical 10.1](../character_creator/BODYFIT_IDENTITY_AGE.md#101-颈部异常的输入溯源与修复试验)。

## 7. 输出与保留

作业目录至少保留 Request、Result、运行配置、失败窗口和关键报告。生产角色/Look 作业为 `retained_evidence`；Heartbeat、临时 staging 和无异常轮询日志为 `disposable`。

## 8. 恢复

1. 先停止提交新作业。
2. 判断作业是否已有终态；不得为同一 ID 重复执行有副作用命令。
3. 未知窗口交由用户处理。
4. CC 重启后等待新 Heartbeat，再从阶段入口重跑。
5. 资源持续增长时按角色/Look 分批并在批间由用户重启 CC。

完整故障分类见 [恢复手册](../validation/RECOVERY.md)。

2026-10-04 人工照片后处理已在原离线 CC 实例验证两种无需前台激活的内部 Qt 调用：眼/牙 Material Only 沿用精确弹窗处理；最终阶段 Bake Slider 精确匹配唯一启用的 `qtBakeToolButton`、文字/tooltip 及 AvatarCreatorShaping 祖先，直接 click，不改变禁用状态，不移动鼠标。隐藏标签中的已启用控件也被记录为内部调用，不能写作可见菜单点击。该烘焙必须位于独立角色完成几何补偿之后；立即局部网格不变及随后细分/重载结果由 [BodyFit Technical 10.6](../character_creator/BODYFIT_IDENTITY_AGE.md#106-人工照片角色的独立副本后处理2026-10-04) 拥有。未知控件仍不自动确认，单例成功不扩大为通用 UI/早期烘焙支持。
