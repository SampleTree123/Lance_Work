# 架构决策记录

> 文档角色：`adr_index`
> 状态：`current`
> 适用阶段：`global`
> 权威范围：已接受架构决定的目录索引
> 上级入口：[`../CHARACTER_FACTORY_MASTER_SPEC.md`](../CHARACTER_FACTORY_MASTER_SPEC.md)
> 上游：当前技术决定与验证结果
> 下游：ADR-0001..ADR-0013
> 最近核验：2026-08-08

ADR 记录已经接受、会长期影响实现的选择。改变决定时新增 ADR 并标记旧 ADR 被替代，不静默重写理由。

| ADR | 状态 | 决定 |
| --- | --- | --- |
| [`ADR-0001-BODYFIT-SOURCE-PROJECTS.md`](./ADR-0001-BODYFIT-SOURCE-PROJECTS.md) | Accepted | BodyFit 使用 hash 锁定源项目 |
| [`ADR-0002-FACE-IDENTITY-V3.md`](./ADR-0002-FACE-IDENTITY-V3.md) | Accepted | 完整 seed + Facial Profile + 安全局部 Morph |
| [`ADR-0003-AGE-VARIANTS.md`](./ADR-0003-AGE-VARIANTS.md) | Accepted | 年龄是可选面部变体，身体老化延后 |
| [`ADR-0004-APPEARANCE-POOLS.md`](./ADR-0004-APPEARANCE-POOLS.md) | Accepted | 外观只从审核池选择，眼球只换材质 |
| [`ADR-0005-HAIR-PIGMENTATION-AND-VARIANTS.md`](./ADR-0005-HAIR-PIGMENTATION-AND-VARIANTS.md) | Accepted | 共享色素抽样，每角色三套已适配发型 |
| [`ADR-0006-OUTFITS-PER-BODYFIT-LOOK.md`](./ADR-0006-OUTFITS-PER-BODYFIT-LOOK.md) | Accepted | 服装按 BodyFit × Look 管理 |
| [`ADR-0007-UE-VENDOR-DATAMAKE-MODULARITY.md`](./ADR-0007-UE-VENDOR-DATAMAKE-MODULARITY.md) | Accepted | Vendor 不动，DataMake 统一入口，模块化组件运行 |
| [`ADR-0008-BODY-FACE-ANIMATION-LAYERS.md`](./ADR-0008-BODY-FACE-ANIMATION-LAYERS.md) | Accepted | 按通道和复用政策分层动画 |
| [`ADR-0009-RESTRICTED-OFFLINE-BRIDGE.md`](./ADR-0009-RESTRICTED-OFFLINE-BRIDGE.md) | Accepted | Bridge 是受控离线文件队列，不执行任意代码 |
| [`ADR-0010-DOCUMENT-AUTHORITY-AND-HISTORY.md`](./ADR-0010-DOCUMENT-AUTHORITY-AND-HISTORY.md) | Accepted | 单一当前入口、技术子文档、不可变历史归档 |
| [`ADR-0011-LIFECYCLE-DOCUMENTATION-AND-GATES.md`](./ADR-0011-LIFECYCLE-DOCUMENTATION-AND-GATES.md) | Accepted | 生产生命周期、Workflow、Gate 和单一命令来源 |
| [`ADR-0012-USER-OWNED-ASSET-AUTHORITY.md`](./ADR-0012-USER-OWNED-ASSET-AUTHORITY.md) | Accepted | 用户负责资产、安装包和许可/来源判断；Agent 只做技术评估 |
| [`ADR-0013-HEADSHOT-BAKED-PROTOTYPE-STORAGE.md`](./ADR-0013-HEADSHOT-BAKED-PROTOTYPE-STORAGE.md) | Accepted | Headshot 身份用项目几何原型包保存，并采用 project-seed 装配路线 |
