# Technical 实现索引

> 文档 ID：`TECH-INDEX`
> 文档类型：`technical_index`
> 生命周期：`current`
> 权威范围：可复现实现、代码所有权、输出和验证导航
> 最近核验：2026-08-25

| 目录 | 能力 | 主要 Workflow |
| --- | --- | --- |
| [`environment/`](./environment/README.md) | 机器、会话、路径和测试环境 | `WF-00` |
| [`implementation/`](./implementation/README.md) | 脚本生命周期、代码所有权和 Script Catalog | 全部阶段 |
| [`character_creator/`](./character_creator/README.md) | BodyFit、身份、外观、服装、组装与验收 | `WF-20/WF-30` |
| [`bridge/`](./bridge/README.md) | CC 离线文件队列、RLPy 和弹窗守卫 | `WF-00/WF-30` |
| [`transfer/`](./transfer/README.md) | CC Bundle、UE FullReference 和追溯 | `WF-40` |
| [`unreal/`](./unreal/README.md) | 角色运行时、动画、表情、场景和 Sequence | `WF-50/WF-60` |
| [`dataset/`](./dataset/README.md) | 配置图、链、Prompt 和 Render Jobs | `WF-10/WF-70` |
| [`rendering_release/`](./rendering_release/README.md) | 本地/服务器渲染、封装和发布 | `WF-80/WF-90` |
| [`validation/`](./validation/README.md) | 机器门禁、视觉审查、恢复和文档审计 | 全部阶段 |
| [`output/`](./output/README.md) | 稳定输出 ID、Run Root、Manifest、盘点和保留 | 全部阶段 |

Technical 文档只声明经过验证的边界。某脚本存在不等于它是生产入口；当前能力成熟度必须同时查看对应 Workflow Status。

## 机器目录

- `00_engine/scripts/SCRIPT_CATALOG.json`：全部脚本的生命周期、SHA-256 和 Technical 所有者。
- `00_engine/outputs/RETENTION_POLICY.json`：人工批准的输出保留规则。
- `00_engine/outputs/OUTPUT_INVENTORY.json`：当前输出体积、文件数和分类盘点。

脚本目录的生成与审计见 [脚本生命周期与所有权](./implementation/SCRIPT_LIFECYCLE.md)；输出契约和盘点见 [Output 技术索引](./output/README.md)。机器目录用于反向查询；正常执行仍先从 Workflow 进入对应领域 Technical 文档。
