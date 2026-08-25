# 文档与项目知识治理规则

> 文档 ID：`GOV-001`
> 文档类型：`governance`
> 生命周期：`current`
> 权威范围：文档角色、事实所有权、生命周期、输出保留和审计规则
> 最近核验：2026-08-25

## 1. 目标

本规则保证项目规模扩大后仍能回答五个问题：现在做到哪里、下一步是什么、如何复现、输出在哪里、为什么采用当前方案。目录整齐不是目标；事实唯一、流程可执行和证据可追溯才是目标。

## 2. 冲突裁决

项目没有一条可以覆盖所有问题的线性“最高权威”。先判断冲突属于哪个事实维度，再回到该维度的所有者：

| 问题 | 权威 | 回答 |
| --- | --- | --- |
| 程序实际做了什么 | 运行证据、日志、媒体和当前代码 | 描述已发生行为，不自动证明行为合规 |
| 本次精确输入是什么 | Registry、Manifest、Schema、配置和哈希 | 决定 ID、版本、路径、参数和输入闭包 |
| 长期允许怎样工作 | Governance、当前 ADR、Workflow、Validation/Output 契约 | 决定规范、阶段边界、Gate 和稳定语义 |
| 应当怎样复现实现 | Technical 与其拥有的代码/配置/测试 | 决定命令、组合关系、恢复和实现限制 |
| 当前是否允许生产使用 | Workflow/Batch Status 及仍有效的 Gate 证据 | 决定当前接受范围，不改变长期定义 |
| 准备实现什么 | 当前 Plan | 决定未来要求，不证明已经实现 |
| 过去发生过什么 | History、关闭计划、报告和快照 | 支撑追溯，不覆盖当前事实 |

两个维度不一致时不能任选一个覆盖另一个。例如代码成功执行但违反 Workflow/Validation 契约，真实结论是“代码已执行、Gate 失败”，不是代码自动成为新规范。冲突不能由现有 ADR/规则解释时，停止受影响阶段、登记状态与证据，必要时新建 ADR；不得只修改文档使检查变绿。

## 3. 信息所有权

| 信息 | 唯一主要所有者 | 其他文档允许内容 |
| --- | --- | --- |
| 项目目的和长期流程 | Master | 简短链接 |
| 阶段顺序、输入输出、Gate | Workflow | Technical/Status 回链 |
| 验证 ID、状态词、触发、证据和失效语义 | Validation | Workflow/Technical/Status 引用 |
| 输出 ID、存储类别、Run Root、Manifest、晋升和保留语义 | Output | Workflow/Technical/Status 引用 |
| 脚本、配置、命令、领域输出结构、验证实现和恢复 | Technical | Workflow 摘要 |
| 当前能力和唯一下一步 | Status | Master 一行入口 |
| 当前批次冻结值和进度 | Batch Status / 机器配置 | Plan 的目标值、Technical 的示例 |
| 未来需求和验收条件 | Plan | Status 的需求落实结果 |
| 长期架构决定 | ADR | Master/Technical 的决定链接 |
| 已完成事实 | Milestone / Completed Plan | Status 的极简近期摘要 |
| 术语与路径别名 | Reference | 上下文中的简短解释 |
| 机器权威、适用范围和 Technical 所有者反查 | Registry Index | Technical/Workflow 的顺向链接 |
| 全树维护、冲突和审计规则 | Governance | 各子系统的局部契约 |
| 新文档结构 | Templates | 当前文档不受模板滚动覆盖 |

同一动态数字不得在根 README、Master、代码 README、Workflow 和状态中分别人工维护。

## 4. 文档类型与元数据

所有活跃 Markdown 至少包含：

```text
文档 ID
文档类型
生命周期
最近核验
```

Master、Workflow、Technical、Index 和 Governance 还必须提供 `权威范围` 或等价的 `实现所有权`。Plan、Status、ADR 和 History 使用各自的影响阶段、状态来源、决定范围或证据字段表达边界，不为了形式重复同一信息。

不同类型增加自己的字段，不再要求每份文档填写相同的八项元数据：

- Workflow：阶段 ID、前序、后序、Gate。
- Technical：拥有的实现范围、适用 Workflow、运行环境。
- Validation：稳定验证 ID、角色、实现所有者、证据输出和结果所有者。
- Output：稳定输出 ID、生产者、存储类别、Manifest 和状态所有者。
- Status：状态来源、当前计划、更新时间。
- Plan：计划状态、需求 ID、影响阶段、完成条件。
- ADR：状态、日期、上下文、决定、后果。
- History：事件日期、来源计划、证据。
- Reference：稳定术语或路径范围。
- Registry：机器权威、当前范围、Technical 所有者和消费 Workflow。
- Template：目标文档类型及其必填结构。

生命周期只允许：`current`、`queued`、`paused`、`completed`、`superseded`、`compatibility`、`archived`。

## 5. Workflow 契约

每份 `WF-*` 按以下顺序组织：

1. 目的与使用时机
2. 前后序与进入条件
3. 输入
4. 正常流程
5. 输出契约（稳定 `OUT-*`）
6. 必需验证（稳定 `VAL-*`）
7. Exit Gate
8. Technical 与当前 Status 导航
9. 失败与恢复

Workflow 不保存某个批次的完整资产列表，不保存长命令块，不记录逐日实验过程。动态状态由对应 `status/workflows/WF-*.md` 管理。

“正常流程”不能只写抽象动词。每一步至少给出：操作目的、精确 Technical 所有者、实际入口文件/机器配置和本步产物；完整可复制命令仍只保存在 Technical，Workflow 不复制参数真相。若实现仅覆盖 Pilot、增量批次或人工触发路径，必须在 Workflow 中直接写明，不能用“自动化”概括为通用能力。

“输出契约”不能只列 `OUT-*` 名称。每个逻辑输出至少解释：组成部分、实际内容、存在理由、下游消费者、当前位置所有者和验证证据。一个 `OUT-*` 跨越 Bundle、UE Asset 与 Run Evidence 时，必须明确它们为何不可互相替代。

## 6. Technical 契约

每份主要 Technical 文档至少说明：

1. 能力与边界
2. 何时由哪些 Workflow 调用
3. 实现所有权，包括全部入口、辅助脚本、配置和测试
4. 环境和前置条件
5. 输入契约
6. 可复现步骤和准确命令
7. 领域输出结构，并声明其稳定 `OUT-*`
8. 机器/人工验证实现，并声明其稳定 `VAL-*`
9. 失败恢复与停止条件
10. 当前限制和版本迁移条件

文档头还必须声明 `验证所有权` 与 `输出契约`；无产物或无需验证时写明确的 `not_applicable` 理由。一个能力可以由多个脚本共同工作，不强制指定虚假的“唯一主脚本”。未被任何 Technical 文档拥有的活跃脚本必须分类为实验、废弃或待登记。

## 7. 状态与计划生命周期

### 7.1 状态

- `PROJECT_STATUS.md`：当前能力概况、当前计划、活动批次和唯一下一步。
- `PROJECT_STATE.json`：关键状态的机器可读权威。
- `status/workflows/WF-*.md`：每个阶段当前能力、证据、计划需求、缺口和下一 Gate。
- `status/batches/*.md`：某批次冻结值、完成率、阻塞和交付状态。

状态覆盖更新，不保存完整旧版本。完成事实追加到历史。

### 7.2 计划

恰好允许一个 `current` 主计划。其他未完成计划只能是 `queued` 或 `paused`；`blocked` 是需求状态，不是计划生命周期。每项计划需求使用稳定 ID，并列出：目标、影响 Workflow、验收条件、当前落实状态和证据位置。

计划完成必须同时满足：

1. 所有必需需求进入终态。
2. 受影响 Workflow 状态已经同步。
3. 验证证据存在。
4. 长期决定已经写入 ADR（若适用）。
5. 里程碑已经追加。
6. 计划移入 `history/completed_plans/`，索引状态改为 `completed`。

### 7.3 历史

历史只保存经过整理的完成计划、里程碑、报告和事故结论。重构前整树原文属于原始快照，放在活跃树之外并附 SHA-256 Manifest，不纳入日常导航。

### 7.4 决定

ADR 只保存会长期改变架构、数据语义、生产边界或治理方式的决定。`accepted` ADR 必须有背景、决定、后果和复审条件；`superseded` ADR 必须指向后继。普通参数选择、单次运行结果和当前阻塞不写成 ADR。

## 8. 输出与保留契约

稳定 `OUT-*`、存储类别、Run Root、Manifest 和晋升语义由 [Output 子系统](./technical/output/README.md) 独立维护。本节只规定全树必须遵守的安全边界。

### 8.1 每次运行

新的生产或验证运行应使用唯一 `run_id`，并尽量包含：

```text
<run_root>/
  manifest.json
  status.json
  inputs.lock.json
  result.json
  logs/
  evidence/
  media/
```

`manifest.json` 至少记录生产者、Git revision、Workflow、计划/批次 ID、输入哈希、输出列表、验证状态、保留等级和被谁取代。

### 8.2 保留等级

| 等级 | 含义 | 删除规则 |
| --- | --- | --- |
| `authoritative` | 当前生产输入、正式数据或不可替代清单 | 未迁移并验收前禁止删除 |
| `retained_evidence` | 支撑 Gate、事故结论或人工签字 | 由替代证据和保留策略决定 |
| `superseded` | 已被新版本完整取代且有映射 | 验证替代物和 Manifest 后可清理 |
| `disposable` | 可重建缓存、临时截图、失败中间帧 | 不影响追溯时可清理 |
| `unclassified` | 尚未完成所有权或保留审查 | 默认保护，禁止删除 |

`artifacts` 只是输出目录名，不构成特殊文档类别。每个输出必须有 `OUT-*`、产生它的 Technical 所有者和当前 Status 指针；保留等级由 Output Policy 决定，领域 Technical 不可自行授权删除。

### 8.3 正式数据包

正式批次不得把文本、视频、图和报告散落为互不关联的权威根。交付包至少按以下逻辑组织：

```text
delivery/<batch_id>/
  manifest/
  graph/
  text/
  media/
  metadata/
  qa/
  checksums/
```

本地工作输出可以分散，但发布时必须由 Batch Manifest 汇聚为一个数据包。

## 9. 路径与跨机器规则

1. 文档使用 `%LANCE_ROOT%`、`%UE_PROJECT_ROOT%`、`%OUTPUT_ROOT%` 等别名。
2. 绝对路径只在 [PATH_ALIASES.md](./reference/PATH_ALIASES.md) 或确需复制执行的机器命令中出现。
3. 本地、服务器路径映射分别维护；机器私有配置不进入 Git。
4. UE `Content/`、`.uasset`、`.umap`、DDC、缓存和媒体不因未进入 Git 而失去所有权，必须由资产/交付 Manifest 追溯。

## 10. 代码生命周期

活跃实现分为：

- `production`：当前默认生产实现。
- `validated_pilot`：只在登记范围内验证。
- `utility`：辅助生成、审计或可视化工具。
- `experimental`：不能作为生产入口。
- `deprecated`：已被替代，等待归档或删除。
- `archived`：只为复现历史结果保留。

代码目录 README 只做本地开发导航，不复制项目当前状态。Technical 文档负责解释当前入口、组合关系和输出。

## 11. 子系统独立闭环

每个子系统必须先独立满足自己的契约，不能依靠其他目录中的解释掩盖缺口：

| 子系统 | 独立闭环最低条件 |
| --- | --- |
| Workflow | 阶段集合、顺序、输入、`OUT-*`、`VAL-*`、Gate 和恢复完整 |
| Validation | 每个 `VAL-*` 有触发、证据、通过、失效、实现和状态落点 |
| Output | 每个 `OUT-*` 有生产者、存储类别、Manifest、晋升、保留和状态落点 |
| Technical | 所有当前文档被索引，代码/配置/命令/验证实现/输出产生/恢复可复现 |
| Status | 只描述当前事实，并为每个阶段列能力、计划、验证、输出、风险和下一 Gate |
| Plan | 生命周期和需求状态合法，恰好一个 current，需求有验收与证据入口 |
| History | 只保存关闭事实、最终证据与当时范围，不伪装当前入口 |
| Decisions | accepted/superseded 关系闭合，当前规则有复审条件 |
| Reference | 术语、路径别名和 URI 边界完整，不保存动态状态 |
| Registry | 当前机器权威、范围、Technical 所有者和消费 Workflow 可反查 |
| Governance | 事实所有权、冲突、同步、删除和审计规则无内部矛盾 |
| Templates | 新建文档会自然满足对应子系统最低契约 |
| Master | 人类可顺向理解全生命周期，并能到达所有活跃子系统入口 |

只有全部独立检查通过后，才检查明确跨层关系：`WF-* -> VAL-* -> Technical -> OUT-* -> Status`、`Plan Requirement -> Workflow Status/Evidence`、`ADR -> 受影响定义`、`Master -> 子系统入口`。没有明确契约的内容不为形式统一而合并。

## 12. 变更同步矩阵

| 变化 | 必须同步 |
| --- | --- |
| 长期生产顺序或 Gate 语义 | Workflow、ADR、Master 导航、Workflow Status |
| 新增/修改验证契约 | Validation、实现 Technical、受影响 Workflow、模板、检查器 |
| 新增/修改输出契约 | Output、生产 Technical、受影响 Workflow/Status、Retention/Inventory |
| 技术实现或命令 | Technical、Script Catalog、测试；当前能力改变时再更新 Status |
| 批次冻结值 | Batch Status、机器配置、相关 Plan Requirement 状态 |
| 能力通过 Gate | Workflow Status、Batch/Project Status、验证证据、Milestone |
| 当前计划变化 | PROJECT_STATE、PROJECT_STATUS、PLAN_INDEX、相关 Workflow Status |
| 计划需求完成 | Plan、相关 Workflow Status 和证据；全计划完成后迁入 History |
| 机器权威变化 | Registry Index、拥有它的 Technical、消费 Workflow/Status |
| 路径变量 | Reference PATH_ALIASES、相关 Technical、环境预检 |
| 新文档类型或必填结构 | Governance、对应 Template、检查器；必要时 ADR |

## 13. 审计顺序

### 13.1 独立检查

文档审计先按第 11 节逐个子系统报告结果。任一子系统失败时，全树不能标记为 `VAL-DOC-01 passed`，即使链接总数或跨层关系看起来正确。

### 13.2 跨层检查

独立检查全部通过后，至少检查：

- Master 对所有活跃文档可达。
- 目录 README 索引直接子文档。
- 类型化元数据和链接有效。
- Workflow 的 `VAL-*`、`OUT-*`、Technical 和 Status 全部可解析且职责一致。
- 恰好一个 current 计划，且与 `PROJECT_STATE.json` 一致。
- Plan Requirement 与 Workflow Status/Evidence 一致。
- Registry 当前权威与 Technical/Status 当前指针一致。
- accepted/superseded ADR 与受影响定义一致。
- 根入口和代码 README 不复制受控批次数字。
- 活跃文档不把历史或快照当作当前权威。
- 非路径参考文档不存在未登记的 Windows 绝对路径。

准确命令见 [文档验证](./technical/validation/DOCUMENTATION_VALIDATION.md)。巨型逐行链接追踪只按需生成到临时审计输出，不进入活跃文档树。
