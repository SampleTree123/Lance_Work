# 外部目录与所有权

> 文档角色：`path_reference`
> 上级入口：[`README.md`](./README.md)
> 最近核验：2026-08-06

## 1. 路径变量

```text
LANCE_ROOT       = D:\UE\Lance_Work
CC_INSTALL_ROOT  = D:\CharacterCreator
CC_ASSET_ROOT    = D:\CharacterCreator_sucai
UE_PROJECT_ROOT  = D:\UE\projects\datatry_02
CC_EXPORT_ROOT   = D:\UE\exports\character_creator
```

## 2. 目录职责

| 路径 | 所有权与内容 | 规则 |
| --- | --- | --- |
| `%CC_INSTALL_ROOT%` | Character Creator 5 程序和学校离线许可证环境 | 不把项目数据写入程序目录；Agent 不自动重启 |
| `%CC_ASSET_ROOT%` | Reallusion Templates、Custom、ActorMIXER、皮肤、毛发等本地资产库 | 只读为默认；资产迁移需独立任务和备份 |
| `%LANCE_ROOT%\00_engine\scripts\character_creator` | 系统 Python 生成器、RLPy 执行器和机器 JSON | 当前实现源；不把 artifacts 混入此处 |
| `%LANCE_ROOT%\00_engine\character_creator_bridge` | CC 插件、CLI、协议、配置和弹窗守卫 | Bridge 实现源；配置定义安全边界 |
| `%LANCE_ROOT%\00_engine\scripts\unreal` | UE Python 构建、检查、PIE 和截图脚本 | 只有导入 `unreal` 的脚本在 UE Python 内运行 |
| `%LANCE_ROOT%\00_engine\outputs` | 每次验证的 JSON、截图、联系表和日志 | 证据目录；使用唯一 run ID，不覆盖旧运行 |
| `%CC_EXPORT_ROOT%` | CC 到 UE 的 FBX/JSON/纹理 bundle | 每次导出独立版本目录；不作为长期文档入口 |
| `%UE_PROJECT_ROOT%` | Unreal Engine 5.8 主项目 | Vendor 保留外部资产，DataMake 保存项目自有入口 |
| `character_creator/full_process` | 当前人类可读文档体系 | 不保存脚本、机器配置或原始截图 |

## 3. Bridge 运行目录

配置文件：

```text
%LANCE_ROOT%\00_engine\character_creator_bridge\bridge_config.json
```

运行根：

```text
%LANCE_ROOT%\00_engine\outputs\character_creator_bridge
```

典型子目录由插件维护：

```text
inbox\
processing\
completed_requests\
failed_requests\
results\
state\heartbeat.json
logs\
artifacts\
dialog_guard\
```

`allowed_input_roots` 当前包括脚本目录、Face recipe 输出、Reallusion Templates 和 Custom CC Project。`artifacts` 是允许输出根，不自动成为输入根。

完整角色动态请求可暂存在：

```text
%LANCE_ROOT%\00_engine\scripts\character_creator\runtime_staging\<run_id>
```

该目录按需生成，目前可能不存在；不得提交 Git。作业完成后将 request/manifest 复制到对应 artifact，再在核对哈希后清理 staging。

## 4. CC 资产路径原则

- `Reallusion Templates` 是模板资产源，不为让 UI 显示而直接改名或移动。
- `Reallusion Custom` 保存用户可见、可编辑和迁移后的资产。
- 资产目录中同名文件不代表内容相同，registry 使用稳定 ID 和绝对路径。
- 自动应用前确认路径属于 Bridge allowlist。
- 新采购资产先离线落盘并人工在 CC 中可见，再进入 catalog。

## 5. UE 内容边界

```text
/Game/Vendor/...   外部包、Reallusion 导入和拆分源资产
/Game/DataMake/... 项目自有地图入口、角色 Blueprint、派生动画和配置
/Game/CC_Shaders   Reallusion Auto Setup 依赖内容
```

外部 `.uasset` 可能硬编码包引用。导入后不要用文件系统移动；如确需移动，只能在 Unreal Content Browser 内执行并修复 Redirector，且必须独立验证。当前约定是 Vendor/原包不移动。

## 6. 输出保留

- 原始失败输出保留到结论稳定，不用新运行覆盖。
- 成功运行至少保留 request、manifest、result、自动报告和视觉证据。
- 临时 probe 只有在被正式证据取代且不再参与审计时才清理。
- 文档引用目录或关键报告，不枚举每一张截图。
