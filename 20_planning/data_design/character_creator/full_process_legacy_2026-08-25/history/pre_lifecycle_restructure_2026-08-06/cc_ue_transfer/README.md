# CC 到 UE 传输文档

> 文档角色：`subsystem_index`
> 上级入口：[`../CHARACTER_FACTORY_MASTER_SPEC.md`](../CHARACTER_FACTORY_MASTER_SPEC.md)
> 最近核验：2026-08-06

## 当前文档

| 文档 | 状态 | 职责 |
| --- | --- | --- |
| [`EXPORT_IMPORT_RUNBOOK.md`](./EXPORT_IMPORT_RUNBOOK.md) | `validated_pilot` | CC5 FBX/JSON 导出和 UE 5.8 导入 |
| [`ASSET_TRACEABILITY.md`](./ASSET_TRACEABILITY.md) | `validated_pilot` | 源项目、bundle、Vendor 资产和 DataMake 派生资产追溯 |

## 能力矩阵与未来文档

| 能力 | 状态 | 当前执行入口 | 尚未实现时的文档落点 |
| --- | --- | --- | --- |
| 单个 M02 完整角色导入 | `validated_pilot` | [`EXPORT_IMPORT_RUNBOOK.md`](./EXPORT_IMPORT_RUNBOOK.md)；源/目标映射见 [`ASSET_TRACEABILITY.md`](./ASSET_TRACEABILITY.md) | 当前仍包含 CC UI 与 UE UI 人工步骤 |
| 十体型批量导出 | `planned` | 无 | `BATCH_EXPORT.md` |
| 三发型和胡须变体 bundle | `planned` | 无 | 扩展 `BATCH_EXPORT.md` 与 [`ASSET_TRACEABILITY.md`](./ASSET_TRACEABILITY.md) |
| 服装 Look 十体型 bundle | `planned` | 无 | `OUTFIT_TRANSFER.md` |
| LOD、贴图分辨率和体积优化 | `planned` | 无 | `OPTIMIZATION.md` |
| CC/Auto Setup/UE 版本升级 | `planned` | 无 | `VERSION_MIGRATION.md` |

本目录不定义 UE 运行时切换逻辑；导入后的组件和动画见 [`../ue_details/README.md`](../ue_details/README.md)。
