# ADR-0015：可持续文档运行模型

> 文档 ID：`ADR-0015`
> 文档类型：`adr`
> 生命周期：`superseded`
> 状态：`superseded_by_ADR-0016`
> 适用阶段：`global`
> 日期：2026-08-25
> 权威范围：Master、Workflow、Technical、项目管理、Reference 和输出治理
> 最近核验：2026-08-25
> 取代者：[`ADR-0016`](./ADR-0016-INDEPENDENT-DOCUMENT-SUBSYSTEMS.md)

## 背景

旧体系虽然保存了大量事实，但主题文档、逐行链接追踪、当前状态、计划和历史互相交叉。读者能搜索到文件，却难以从项目目的自然走到当前下一步和可执行代码；状态数字多处复制，输出缺少统一保留等级，脚本与产物也没有稳定所有者。

## 决定

> 历史说明：本节是首次 V2 切换时的决定。其“Technical 包含输出和验证”的责任边界已由 ADR-0016 细化并取代，当前应遵循 ADR-0016。

1. `README.md` 是唯一 Master，从项目定义进入长期 Workflow、当前状态和技术实现。
2. 长期流程使用 `WF-00/10/.../90`，为未来插入阶段保留编号空间。
3. Workflow 只定义何时做、输入输出和 Gate；Technical 独占脚本、配置、命令、输出、验证和恢复细节。
4. Project Management 分为当前状态、活跃/排队/暂停计划、ADR 和整理后的历史；恰好一个主计划为 `current`。
5. `PROJECT_STATE.json` 保存关键机器状态，`PROJECT_STATUS.md` 是人类入口；Workflow 能力状态与批次执行状态分离。
6. 代码首先由使用它的 Technical 文档解释，输出首先由产生它的 Technical 文档解释；Reference 只做路径、术语和 Registry 反向查询。
7. 输出统一标记为 `authoritative`、`retained_evidence`、`superseded` 或 `disposable`，重要运行使用统一 Run Root。
8. 原始旧文档保存在活跃树之外的哈希快照；巨型逐行 Link Trace 和重复实现索引不再作为人工入口。
9. 每次阶段性工作结束后运行项目文档维护 Skill，更新状态、计划需求、技术实现、证据和里程碑，并执行语义审计。

## 后果

活跃文档数量更少但责任更明确；新增 UE 或数据阶段不需要再次更改顶层结构。动态数字集中到状态/机器清单，历史仍可审计但不决定当前行为。迁移后 ADR-0010 和 ADR-0011 保留为历史决定并标记 superseded。

## 复审条件

只有项目边界不再是角色工厂到视频编辑数据发布、或现有层级无法容纳新的长期生产阶段时，才新增 ADR 修改顶层架构。单纯新增代码、资产、验证或批次不触发目录重构。
