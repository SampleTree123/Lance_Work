# CC FullReference 到 UE

> 文档 ID：`TECH-TRANSFER-01`
> 文档类型：`technical`
> 生命周期：`current`
> 适用阶段：`WF-40`
> 实现所有权：CC Unreal FBX Bundle 与 UE FullReference Look 导入
> 验证所有权：`VAL-TRANSFER-01`
> 输出契约：`OUT-WF40-TRANSFER-BUNDLE`
> 运行环境：CC UI、系统 Python、UE Editor Python、Reallusion Auto Setup 2.03
> 最近核验：2026-08-25

## 1. 能力边界

当前生产路径把每个 Look 烘焙为一个完整 Skeletal Mesh。身体、皮肤、头发、胡须和服装随 Look 一起导出；第一批不依赖 UE 内任意换装。M02 模块化角色仍是技术 Pilot，不是 32-Look 的生产前提。

## 2. 权威输入

| 输入 | 位置 | 保留级别 |
| --- | --- | --- |
| 32-Look CC Registry | `%CC_SCRIPT_ROOT%/cc_first_batch_full_reference_looks_20260822_v3.json` | `authoritative` |
| 必需导出清单 | `%LANCE_ROOT%/00_engine/scripts/dataset/first_batch_required_exports_20260824_v3.json` | `authoritative` |
| CC 导出 Bundle | `%CC_EXPORT_ROOT%/<export_batch_id>/full_reference/<LOOK_ID>/`；当前批次为 `first_data_batch_20260820_v1` | `authoritative_binary` |
| UE 项目 | `%UE_PROJECT_ROOT%` | `authoritative_binary` |

每个 Bundle 至少包含同基名 `.fbx`、`.json` 和纹理目录；Manifest 中的文件大小和 SHA-256 必须匹配。

## 3. 输出组成与下游用途

`OUT-WF40-TRANSFER-BUNDLE` 跨越外部 Bundle、UE Content 和运行证据，不是把同一份文件复制三次：

| 组成 | 当前路径模式 | 内容 | 作用与下游 |
| --- | --- | --- | --- |
| CC Bundle | `%CC_EXPORT_ROOT%/first_data_batch_20260820_v1/full_reference/<LOOK_ID>/` | `<basename>.fbx`、同基名 JSON、`.fbm`/纹理 | 唯一可审计导入源；供本流程导入、按 Look 重试和未来迁移，不直接被 UE Sequence 播放 |
| UE FullReference | `/Game/Vendor/Reallusion/CC5/FirstDataBatch/Looks/<LOOK_ID>` | Skeletal Mesh、规范同性 Skeleton、材质、纹理、Morph、Blueprint 等 | `WF-50` 动画/表情验收、`WF-60` Sequence 和 `WF-80` 渲染真正消费的资产 |
| 来源映射 | `first_batch_required_exports_20260824_v3.json` 与每 Look 导入报告 | Look ID、FBX/JSON/纹理哈希、目标 Object Path、Skeleton 与导入结果 | 支撑源→UE 与 UE→源追溯、失败隔离和发布引用 |
| Gate 证据 | `%OUTPUT_ROOT%/unreal_character_import/<run_id>/` | 每 Look 验证 JSON、聚合报告、错误分类 | 支撑 `VAL-TRANSFER-01` 与 WF-40 Status；不能被“目录存在”替代 |

当前接受的三个物理位置只由 [WF-40 Status](../../project_management/status/workflows/WF-40.md#当前输出与证据) 指定。Output 子系统定义组成和保留语义，本文只负责如何生产这些内容。

## 4. 精确实现文件

| 阶段 | 文件 | 责任与边界 |
| --- | --- | --- |
| 32-Look 工单编译 | [`cc_build_first_batch_full_reference_looks_v3.py`](../../../../../../00_engine/scripts/character_creator/cc_build_first_batch_full_reference_looks_v3.py) | 生成完整 32-Look 配置、missing-16 增量配置和矩阵；不直接运行 CC |
| 首批增量 CC 执行 | [`run_first_batch_missing_looks_export.ps1`](../../../../../../00_engine/scripts/character_creator/run_first_batch_missing_looks_export.ps1) | 仅执行当前历史批次的 missing-16 扩展；不是通用全量重建器 |
| Bridge 提交 | [`cc_bridge_client.py`](../../../../../../00_engine/character_creator_bridge/cc_bridge_client.py) | 提交 `validate-bodies` 作业、租约和结果等待 |
| CC/RLPy Payload | [`cc_validate_body_reconstruction.py`](../../../../../../00_engine/scripts/character_creator/cc_validate_body_reconstruction.py) | 在 CC 内加载、装配、保存并调用 `RFileIO.ExportFbxFile` 原子导出 |
| 32-Look 聚合审计 | [`cc_audit_first_batch_full_reference_matrix_v1.py`](../../../../../../00_engine/scripts/character_creator/cc_audit_first_batch_full_reference_matrix_v1.py) | 合并冻结 16 与扩展 16 的结果，验证 32/32 文件和哈希 |
| 必需导出锁 | [`build_first_batch_required_exports_v1.py`](../../../../../../00_engine/scripts/dataset/build_first_batch_required_exports_v1.py) | 把已通过 CC 审计的来源编译为 UE 导入清单 |
| UE 系统入口 | [`run_first_batch_full_reference_import.py`](../../../../../../00_engine/scripts/unreal/run_first_batch_full_reference_import.py) | 预检、逐 Look 导入/验证、恢复和聚合 |
| UE Editor Payload | [`ue_import_first_batch_full_reference_looks.py`](../../../../../../00_engine/scripts/unreal/ue_import_first_batch_full_reference_looks.py) | 在 UE 中执行导入、Auto Setup、Object Path/Skeleton/Morph/材质验证和报告写入 |
| UE 远程执行 | [`ue_remote_exec.py`](../../../../../../00_engine/scripts/unreal/ue_remote_exec.py) | 发现当前 UE 实例并提交 Editor Python |
| 已知弹窗守卫 | [`ue_reallusion_dialog_watcher.py`](../../../../../../00_engine/scripts/unreal/ue_reallusion_dialog_watcher.py) | 只处理已登记的 Auto Setup/FBX 窗口；未知窗口停止 |

共享 CC 文件的生命周期所有者仍是 CC Assembly/Bridge Technical；本文拥有它们在 `WF-40` 中的调用顺序、Transfer 参数和输出解释。脚本反向归属见 Script Catalog。

## 5. CC 导出设置

选择 Unreal/UE5 Skeleton，关键值为：

| 选项 | 值 |
| --- | --- |
| Axis | `Z` |
| Auto Skin Rigid Mesh | 开 |
| Rename Duplicate Bone Name | 开 |
| Reset Self Illumination | 开 |
| Bone Name lower-case | 开 |
| Export JSON for Auto Material Setup | 开 |
| Reset Bone Scale | 开 |
| Epic Skeleton / UE5 Skeleton | 开 / UE5 |
| Epic Skeleton Hand and Foot IK | 开 |
| Mouth Open as Morph | 关 |
| Convert Skinned Expressions to Morphs | 关 |
| Use T-Pose As Bind Pose | 关 |

界面没有出现的旧版本选项不推测补选。导出前必须恢复中性临时状态，并禁止覆盖已验证 Bundle。

## 6. CC 导出执行与当前边界

编译当前 32-Look 工单和回归测试：

```powershell
$CCRoot = 'D:\UE\Lance_Work\00_engine\scripts\character_creator'
python "$CCRoot\cc_build_first_batch_full_reference_looks_v3.py"
python -m pytest "$CCRoot\tests\test_cc_build_first_batch_full_reference_looks_v3.py" -q
```

当前批次曾按“冻结 16 + 补齐 16”完成。只有在 missing-16 目标尚未生成、CC 已启动、UE 已关闭且 Bridge 健康时，增量入口才是：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File `
  "$CCRoot\run_first_batch_missing_looks_export.ps1" `
  -RunId '<new_unique_run_id>' `
  -TimeoutSeconds 18000
```

该脚本拒绝覆盖已有 Run Root 和已有 Export Root。它不是从空目录重建全新 32 Look 的入口；完整全量重建目前需要新 `export_batch_id`、重新编译的 full manifest 和新的受控包装器。这个包装器尚未实现，因此当前能力必须标记为“首批特化的分阶段自动化”，不能写成通用一键导出。

当前聚合审计入口：

```powershell
python "$CCRoot\cc_audit_first_batch_full_reference_matrix_v1.py"
python .\00_engine\scripts\dataset\build_first_batch_required_exports_v1.py
```

前者同样绑定当前历史 16+16 结构；新批次不得直接复用其默认路径。

## 7. UE 导入

目标目录固定为：

```text
/Game/Vendor/Reallusion/CC5/FirstDataBatch/Looks/<LOOK_ID>
```

外部资产保留在 `Vendor`；派生 Blueprint、动画、Sequence 和配置进入 `/Game/DataMake`。核心 FBX 选项：骨骼网格体和导入网格体开启，内容为 Geometry and Skinning Weights，基准 Look 首次创建 Skeleton，其余同性交给已冻结的同性 Skeleton，导入 Morph Target，角色基准导入时不导入动画。

## 8. 自动导入入口

UE 已启动且 Remote Python 可用时：

```powershell
python .\00_engine\scripts\unreal\run_first_batch_full_reference_import.py `
  --project datatry_02 `
  --required-exports .\00_engine\scripts\dataset\first_batch_required_exports_20260824_v3.json `
  --report-root .\00_engine\outputs\unreal_character_import\<new_unique_run_id> `
  --interactive --automated-task --auto-dialogs
```

批量任务可用 `--look-id F_ID01_O01` 重跑单个 Look。未知弹窗、许可提示和未精确匹配的对话框必须停下交给用户；自动对话守卫只处理已知 Auto Setup/FBX 模态窗口。

内部实现：

- 系统入口：`00_engine/scripts/unreal/run_first_batch_full_reference_import.py`
- UE Payload：`00_engine/scripts/unreal/ue_import_first_batch_full_reference_looks.py`
- 远程执行：`00_engine/scripts/unreal/ue_remote_exec.py`
- 弹窗守卫：`00_engine/scripts/unreal/ue_reallusion_dialog_watcher.py`

## 9. 导入输出与验证 Gate

每个 Look 必须验证：

1. 目标 Vendor 路径与清单一致；
2. 同性 Skeleton 一致，异性 Skeleton 不混用；
3. 身体比例、头身、皮肤、眼睛、牙齿、毛发和服装完整；
4. Morph Target 和 Facial Bone 存在；
5. Auto Setup 材质完成且没有白块、蓝白眼罩或明显接缝；
6. 动作下无 T-pose，代表动作下服装风险已记录；
7. 汇总报告明确 32/32 通过后，才允许进入 `WF-50`。

导入报告属于 `retained_evidence`。临时弹窗日志和无异常轮询属于 `disposable`。

当前接受的 32-Look 扩展证据为 `%OUTPUT_ROOT%/unreal_character_import/first_batch_full_reference_expansion_20260822_v2/`，其策略前缀是 `unreal_character_import/first_batch_full_reference_expansion_20260822_v2`。

## 10. 恢复

- 失败后保留源 Bundle，不覆盖重导出；修复后新建版本或重跑单个 Look。
- UE 崩溃后先跳过不确定的自动恢复包，核对 Content 和报告，再继续。
- 同名资产已经存在但哈希或 Skeleton 不一致时硬失败，不自动覆盖。
- 材质问题先区分源纹理、Auto Setup、Post Process、动画曲线竞争，再决定是否重导入。
