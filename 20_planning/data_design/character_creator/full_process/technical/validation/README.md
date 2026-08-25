# 验证与恢复索引

> 文档 ID：`TECH-VALIDATION-INDEX`
> 文档类型：`technical_index`
> 生命周期：`current`
> 适用阶段：全部 Workflow
> 权威范围：验证控制面、视觉审查、恢复和文档审计
> 最近核验：2026-08-25

| 文档 | 何时使用 |
| --- | --- |
| [验证契约目录](./VALIDATION_CATALOG.md) | 按稳定 `VAL-*` 确定触发条件、实现所有者、最小证据、通过/失效语义和状态落点 |
| [视觉审查](./VISUAL_REVIEW.md) | 角色、服装、动作、镜头和媒体需要人工判断时 |
| [恢复手册](./RECOVERY.md) | CC/UE/Bridge/渲染/图构建失败或崩溃后 |
| [文档审计](./DOCUMENTATION_VALIDATION.md) | 文档、代码、状态、计划或输出发生变更后 |

验证区不创建第二套业务流程，也不复制领域命令。何时触发由 Workflow 的“必需验证”决定，准确命令由目录指向的领域 Technical 文档负责，当前结果由 Workflow/Batch Status 负责。

顺向使用：`Workflow -> VAL-* -> 实现 Technical -> Status/Evidence`。反向调查某份证据时：`Output Manifest -> OUT-* -> VAL-* -> Workflow Status`。
