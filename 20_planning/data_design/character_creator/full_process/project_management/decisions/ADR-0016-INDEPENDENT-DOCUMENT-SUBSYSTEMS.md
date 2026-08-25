# ADR-0016：文档子系统独立闭合与显式跨层契约

> 文档 ID：`ADR-0016`
> 文档类型：`adr`
> 生命周期：`current`
> 状态：`accepted`
> 适用阶段：`global`
> 日期：2026-08-25
> 权威范围：Workflow、Validation、Output、Technical、Status、Plan、History、Decisions、Reference、Registry、Governance、Templates 与 Master 的责任边界
> 取代：[`ADR-0015`](./ADR-0015-DOCUMENTATION-OPERATING-MODEL.md)
> 最近核验：2026-08-25

## 背景

V2 首次重建已经建立主线，但仍把 Validation、Output 和部分实现责任混在 Technical 中，并依赖跨文档链接掩盖各目录自身缺少定义、状态或索引的问题。结果是某个 Workflow 可以链接到验证文档，却无法说明验证 ID；某个状态页可以说“已通过”，却没有当前输出版本。只做全局链接检查不能证明每个子系统本身可维护。

## 决定

1. 每个文档子系统先独立定义自己的职责、内部结构、必填字段、状态语义、索引和独立审计，再建立跨层关系。
2. Workflow 只拥有长期顺序、进入条件、逻辑输入/输出、必需 `VAL-*` 和 Exit Gate；不复制命令和当前结果。
3. Validation 独立拥有 `VAL-*`、触发、证据、通过、失效和结果状态语义；领域 Technical 只拥有验证实现与命令。
4. Output 独立拥有 `OUT-*`、存储类别、Manifest、晋升、版本和保留/盘点语义；领域 Technical 只拥有具体生产方法。
5. Technical 独立拥有代码、配置、环境、输入、执行、领域输出字段、验证实现、恢复和已知限制；Script Catalog 反向指向其 owner。
6. Status、Plan、History 和 Decisions 各自独立：Status 只保存当前事实，Plan 保存未来要求和需求状态，History 保存关闭快照，ADR 保存长期规则。
7. Reference 与 Registry 分离：Reference 解释稳定术语、路径和导航方法；Registry 索引只列机器权威、所有者和反向查询，不复制 Registry 内容。
8. Governance 拥有全树维护规则；Templates 把各子系统独立契约固化为新文档结构；Master 只做人类入口和全生命周期导航。
9. 跨层关系只通过明确契约建立，例如 `WF-* -> VAL-* -> Technical -> OUT-* -> Status`、`Plan Requirement -> Workflow Status/Evidence`。不存在明确关系的部分不得为了“统一”而强行合并。
10. 审计顺序固定为：各子系统独立检查全部通过，再检查跨层 ID、链接、所有权和状态一致性。全局通过不能抵消任一子系统失败。

## 后果

- 文档数量可能略增，但每份文档的责任可单独判断，局部修改不要求重写全部体系。
- Validation/Output 不再作为 Technical 的附属段落；Technical 仍实现它们，但不拥有全局语义。
- Status 必须明确验证作用域和当前输出版本，避免“Pilot 通过”被误写为“正式批次完成”。
- 检查器需要同时支持子系统独立规则和跨层规则，并分别报告失败类别。
- ADR-0015 作为首次 V2 架构记录保留，但不再是现行操作权威。

## 未采用方案

- 不采用一个巨型文档统一保存 Workflow、命令、验证、输出和状态，因为会重新制造多处动态事实与难以局部维护的问题。
- 不采用只检查链接可达性的方案，因为链接存在不能证明定义完整、代码可执行或当前证据有效。
- 不采用只独立修复 Validation/Output、其余合并处理的方案，因为任何子系统内部缺口都会继续由跨层链接掩盖。

## 复审条件

只有项目不再需要可复现的多阶段生产，或实践证明某个子系统没有独立状态/规则且长期只产生重复信息时才复审。新增 Workflow、验证、输出、代码、计划或批次只扩展现有子系统，不触发顶层重构。
