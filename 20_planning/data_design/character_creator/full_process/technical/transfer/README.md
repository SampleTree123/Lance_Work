# CC 到 UE 传输索引
> 文档 ID：`TECH-TRANSFER-INDEX`
> 文档类型：`technical_index`
> 生命周期：`current`
> 适用阶段：`WF-40`
> 权威范围：CC Bundle、动作 FBX、UE 导入与跨层资产追溯
> 最近核验：2026-10-18（新增CFD40候选转移实现所有权；未晋升生产Gate）

| 文档 | 负责内容 | 当前成熟度 |
| --- | --- | --- |
| [CC FullReference 到 UE](./CC_TO_UE_FULLREFERENCE.md) | 角色 Bundle 导出、32-Look 导入和导入后门禁 | `first_batch_validated` |
| [CC 到 UE 模块化服装](./CC_TO_UE_MODULAR_OUTFIT_PILOT.md) | 双形态 Bundle、分离网格与基础 Skeleton；第 10 节是平均体型全衣柜的编译、导出和导入入口 | 平均体型全库转移、UE 重组与正式索引映射已完成；运行时和视觉范围查 WF-50 |
| [动作传输](./MOTION_TRANSFER.md) | `.rlMotion` 到动作 FBX，再到统一 Skeleton 的导入 | `first_batch_validated` |
| [资产追溯](./ASSET_TRACEABILITY.md) | CC 源、Bundle、Vendor、DataMake、节点和媒体之间的 ID/哈希链 | `current_contract` |
| [CFD40新版候选转移](./CFD40_REFRESH_CANDIDATE_TRANSFER_20261018.md) | 本run完整导出准备、单人共享骨架导入、实测附属睫毛与离线批量恢复记录 | 私有离线实现；完整CC/FBX/UE及候选画面须真实验收，未发布 |

传输层只负责格式和身份边界。CC 中如何组装角色见 [CC 技术索引](../character_creator/README.md)，UE 中如何运行角色见 [UE 技术索引](../unreal/README.md)。
