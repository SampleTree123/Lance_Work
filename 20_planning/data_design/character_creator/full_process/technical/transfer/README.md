# CC 到 UE 传输索引
> 文档 ID：`TECH-TRANSFER-INDEX`
> 文档类型：`technical_index`
> 生命周期：`current`
> 适用阶段：`WF-40`
> 权威范围：CC Bundle、动作 FBX、UE 导入与跨层资产追溯
> 最近核验：2026-08-25

| 文档 | 负责内容 | 当前成熟度 |
| --- | --- | --- |
| [CC FullReference 到 UE](./CC_TO_UE_FULLREFERENCE.md) | 角色 Bundle 导出、32-Look 导入和导入后门禁 | `first_batch_validated` |
| [动作传输](./MOTION_TRANSFER.md) | `.rlMotion` 到动作 FBX，再到统一 Skeleton 的导入 | `first_batch_validated` |
| [资产追溯](./ASSET_TRACEABILITY.md) | CC 源、Bundle、Vendor、DataMake、节点和媒体之间的 ID/哈希链 | `current_contract` |

传输层只负责格式和身份边界。CC 中如何组装角色见 [CC 技术索引](../character_creator/README.md)，UE 中如何运行角色见 [UE 技术索引](../unreal/README.md)。
