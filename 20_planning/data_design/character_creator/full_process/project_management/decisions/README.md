# 架构决定索引

> 文档 ID：`ADR-INDEX`
> 文档类型：`decision_index`
> 生命周期：`current`
> 权威范围：改变长期技术、数据或文档契约的已接受决定
> 最近核验：2026-10-05（显式结项空闲规则）

| ADR | 主题 | 状态 | 主要影响 |
| --- | --- | --- | --- |
| [0001](./ADR-0001-BODYFIT-SOURCE-PROJECTS.md) | BodyFit 使用哈希锁定源项目 | accepted | `WF-20/WF-30` |
| [0002](./ADR-0002-FACE-IDENTITY-V3.md) | Face Identity V3 | accepted | `WF-20/WF-30` |
| [0003](./ADR-0003-AGE-VARIANTS.md) | 年龄变体 | accepted | 后续 CC/UE 年龄能力 |
| [0004](./ADR-0004-APPEARANCE-POOLS.md) | 外观资产池 | accepted | `WF-20/WF-30` |
| [0005](./ADR-0005-HAIR-PIGMENTATION-AND-VARIANTS.md) | 毛发色素与变体 | accepted | `WF-20/WF-30` |
| [0006](./ADR-0006-OUTFITS-PER-BODYFIT-LOOK.md) | 服装按 BodyFit/Look 处理 | accepted | `WF-20..WF-50` |
| [0007](./ADR-0007-UE-VENDOR-DATAMAKE-MODULARITY.md) | UE Vendor/DataMake 边界 | accepted | `WF-40..WF-60` |
| [0008](./ADR-0008-BODY-FACE-ANIMATION-LAYERS.md) | 身体/面部动画分层 | accepted | `WF-50` |
| [0009](./ADR-0009-RESTRICTED-OFFLINE-BRIDGE.md) | 受控离线 Bridge | accepted | `WF-00/WF-30` |
| [0010](./ADR-0010-DOCUMENT-AUTHORITY-AND-HISTORY.md) | 第一代单入口文档 | superseded | 由 ADR-0015 取代 |
| [0011](./ADR-0011-LIFECYCLE-DOCUMENTATION-AND-GATES.md) | 第一代 Workflow/Gate 文档 | superseded | 由 ADR-0015 取代 |
| [0012](./ADR-0012-USER-OWNED-ASSET-AUTHORITY.md) | 用户拥有的资产决定权 | accepted | 资产池与人工验收 |
| [0013](./ADR-0013-HEADSHOT-BAKED-PROTOTYPE-STORAGE.md) | Headshot 烘焙原型存储 | accepted | `WF-20/WF-30` |
| [0014](./ADR-0014-COMPATIBILITY-DOMAINS-AND-CHAIN-POLICIES.md) | 兼容域与双链策略 | accepted | `WF-70..WF-90` |
| [0015](./ADR-0015-DOCUMENTATION-OPERATING-MODEL.md) | 可持续文档运行模型初版 | superseded | 由 ADR-0016 取代 |
| [0016](./ADR-0016-INDEPENDENT-DOCUMENT-SUBSYSTEMS.md) | 文档子系统独立闭合与显式跨层契约 | accepted | 全局 |
| [0017](./ADR-0017-COMPLETED-PLAN-IDLE-STATE.md) | 计划完成归档后等待用户下一任务的显式空闲状态 | accepted | Plan/Status/Governance |

| [0018](./ADR-0018-ACTION-DEPENDENT-STABLE-CAMERA.md) | 动作替换保镜头配方、允许派生平滑轨迹不同 | accepted | WF-60/70/80实验范围 |

只有改变长期规则的决定进入 ADR。一次故障、单批结果和临时参数分别进入 Technical Recovery、Batch Status 或 Plan。

accepted ADR 至少包含背景、决定、影响/后果和复审条件。`superseded` ADR 保留原文及明确取代者，不再作为当前操作规则。
