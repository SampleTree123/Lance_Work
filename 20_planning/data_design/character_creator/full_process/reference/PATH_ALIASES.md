# 路径别名与外部目录

> 文档 ID：`REFERENCE-PATHS`
> 文档类型：`reference`
> 生命周期：`current`
> 权威范围：本机路径别名、目录职责和迁移边界
> 最近核验：2026-10-23服务器路径；Windows路径沿用历史记录，待本地确认

## 1. Windows历史绑定与共同逻辑别名

| 别名 | 当前路径 | 主要内容 |
| --- | --- | --- |
| `%WORKSPACE_ROOT%` | `D:\UE` | 共享工作区 |
| `%LANCE_ROOT%` | `D:\UE\Lance_Work` | Git 管理的代码、配置、文档和轻量清单 |
| `%ENGINE_ROOT%` | `%LANCE_ROOT%\00_engine` | 运行代码、Bridge、Portal 与输出根目录 |
| `%DOC_ROOT%` | `%LANCE_ROOT%\20_planning\data_design\character_creator\full_process` | 当前文档体系 |
| `%WORKFLOW_ROOT%` | `%DOC_ROOT%\workflow` | 长期阶段契约 |
| `%TECHNICAL_ROOT%` | `%DOC_ROOT%\technical` | 可复现实现权威 |
| `%PROJECT_MANAGEMENT_ROOT%` | `%DOC_ROOT%\project_management` | 当前状态、计划、历史和决定 |
| `%DOC_SKILL_SOURCE%` | `%LANCE_ROOT%\.codex\skills\character-factory-doc-maintenance` | Git 管理的文档维护 Skill 权威源 |
| `%DOC_SKILL_ROOT%` | `%WORKSPACE_ROOT%\.codex\skills\character-factory-doc-maintenance` | 当前工作区的已安装 Skill 副本 |
| `%OUTPUT_ROOT%` | `%LANCE_ROOT%\00_engine\outputs` | 运行产物和证据 |
| `%CC_SCRIPT_ROOT%` | `%LANCE_ROOT%\00_engine\scripts\character_creator` | CC 生成器/Registry |
| `%UE_SCRIPT_ROOT%` | `%LANCE_ROOT%\00_engine\scripts\unreal` | UE 外层入口和 Payload |
| `%DATASET_SCRIPT_ROOT%` | `%LANCE_ROOT%\00_engine\scripts\dataset` | 图、链、Prompt 与作业生成器 |
| `%CC_BRIDGE_ROOT%` | `%LANCE_ROOT%\00_engine\character_creator_bridge` | Bridge 插件、协议和 CLI |
| `%VISUAL_PORTAL_ROOT%` | `%LANCE_ROOT%\00_engine\visualization_portal` | 本地审查门户 |
| `%CC_INSTALL_ROOT%` | `D:\CharacterCreator` | CC 程序环境 |
| `%CC_ASSET_ROOT%` | `D:\CharacterCreator_sucai` | CC 模板和 Custom 资产 |
| `%CC_EXPORT_ROOT%` | `D:\UE\exports\character_creator` | CC→UE Bundle |
| `%UE_PROJECT_ROOT%` | `D:\UE\projects\datatry_02` | UE 5.8 主项目 |
| `%CLOTHING_ROOT%` | `D:\BaiduNetdiskDownload\人物和服装_newest50pct_sorted` | 当前人工整理服装库 |
| `%ANIMATION_ROOT%` | `D:\BaiduNetdiskDownload\iclone动作` | 动画来源库 |

UE 路径解析规则：`/Game/<relative_path>` 表示 Content Browser Object Path，其当前本机物理目录根为 `%UE_PROJECT_ROOT%\Content\<relative_path>`。例如 `/Game/Vendor/Reallusion/...` 对应 `%UE_PROJECT_ROOT%\Content\Vendor\Reallusion\...`；带 `.AssetName` 的完整对象引用不是文件系统文件名，不能直接拼接为磁盘路径。

## 1.1 服务器绑定

服务器根为`/scratch/prj0000000275/jcy/xks/DataMake`。下表路径于2026-10-23只读核对；不代表当前会话通过UE Gate。

| 逻辑项 | 服务器绑定 | 边界 |
| --- | --- | --- |
| `%LANCE_ROOT%` / repo root | `/scratch/prj0000000275/jcy/xks/DataMake` | shell物理路径可显示`/home/users/astar/cfar/stuchengyou/jcy/xks/DataMake`；不是另一份待同步工作区 |
| `%ENGINE_ROOT%` | `<repo>/00_engine` | 数据生产目录，不是UE二进制安装根 |
| `%UE_PROJECT_ROOT%` | `<repo>/00_engine/projects/datatry_02` | Windows工程需经输入闭包同步；只同步文档不会更新Content |
| Installed Build | `<repo>/00_engine/unreal/UE_5.8` | 当前存在；不是已证明可替代旧生产构建 |
| 历史生产兼容构建 | `/scratch/prj0000000275/jcy/sx/UnrealEngine` | 发布profile保留此路径，但可执行文件当前不存在；不可作为有效命令默认值 |
| `%OUTPUT_ROOT%` | `<repo>/00_engine/outputs` | 服务器媒体/证据；目录快照不能覆盖本地输出事实 |
| Lance HF cache | `/scratch/prj0000000275/jcy/.cache/huggingface` | 保留服务器绑定，不同步到Windows文档暂存区 |

本轮同步范围见[文档同步](../technical/rendering_release/DOCUMENT_SYNC.md)。Windows表中的外部资产根不能据服务器内容自动修改；服务器运行快照见[同步状态](../project_management/status/SERVER_SYNC_STATUS.md)。

## 2. 所有权

- 程序、素材库、下载源和 UE 二进制工程不因出现在文档中而进入 Git。
- `%LANCE_ROOT%` 中的代码、配置、清单和活跃文档受 Git 管理；大体积运行输出仍按 Output Contract 和保留规则治理。
- `%CC_ASSET_ROOT%`、服装和动画来源默认只读；整理结果通过 Registry/Manifest 引用。
- `%UE_PROJECT_ROOT%` 的 Vendor 保留外部导入路径，DataMake 保存自有派生资产。
- `%OUTPUT_ROOT%` 不是永久仓库；产生它的 Technical 文档声明逻辑输出，Output 子系统声明保留、盘点和清理规则。
- 别名只描述位置和职责，不证明目录内资产已通过验证。当前接受状态必须查 Workflow/Batch Status。

## 3. 跨机器引用

版本化清单使用 `repo://`、`bundle://`、`workspace://`、数据集相对 URI 或 UE `/Game/...` 路径。Windows 盘符只可出现在明确标记为本机绑定的配置/锁文件，不能进入可迁移 `source_ref`。

| 表达 | 用途 |
| --- | --- |
| `repo://...` | `%LANCE_ROOT%` 下由 Git 管理的文件 |
| `bundle://...` | 冻结 Transfer Bundle 内的相对对象 |
| `workspace://...` | 仅在共享工作区可解析、尚未打包进 Bundle 的对象 |
| `/Game/...` | UE Content Browser Object Path；按第 1 节规则可定位 Content 目录，但不是可直接传给普通文件 API 的 Windows 路径 |
| 数据集相对路径 | 相对 Delivery Root 的媒体、Sidecar、Prompt 或 Manifest |

## 4. 快照

重构前完整文档快照位于：

```text
20_planning/data_design/character_creator/rebuild_reference_2026-08-25/
```

该目录只用于审计，不是当前执行入口，也不随活跃文档一起修改。
