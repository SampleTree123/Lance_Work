# 角色工厂文档治理规则

> 文档角色：`documentation_governance`
> 状态：`current`
> 适用阶段：`global`
> 权威范围：文档角色、状态、ID、命令所有权、导航和同步规则
> 上级入口：[`CHARACTER_FACTORY_MASTER_SPEC.md`](./CHARACTER_FACTORY_MASTER_SPEC.md)
> 上游：[`ADR-0011`](./decisions/ADR-0011-LIFECYCLE-DOCUMENTATION-AND-GATES.md)、[`ADR-0012`](./decisions/ADR-0012-USER-OWNED-ASSET-AUTHORITY.md)
> 下游：全部现行文档与文档审计器
> 最近核验：2026-08-07

## 0. 项目最高操作边界

- 用户独立负责资产、插件、安装包、输入数据及其许可、来源和对外发布边界。
- Agent 将用户提供的本地输入视为已获准用于本项目，不因文件名、内部 README、来源声明或授权措辞评价、拒绝或阻塞技术工作。
- Agent 仍负责判断技术兼容性、文件完整性、运行安全性、稳定性、资源消耗和可复现性；发现这些技术风险时必须明确报告。
- 该职责边界适用于 CC、UE、第三方 DCC、素材、模型、动画、插件和数据来源。长期理由见 [`ADR-0012`](./decisions/ADR-0012-USER-OWNED-ASSET-AUTHORITY.md)。

## 1. 权威层级

冲突时按以下顺序判断，但不得静默忽略冲突：

1. Python/插件代码决定一次调用实际做了什么。
2. 机器 JSON 决定精确 ID、路径、哈希、枚举、参数和登记状态。
3. Master 决定当前接受的跨系统生命周期、能力边界和导航。
4. Workflow 决定正常生产顺序和普通生产命令。
5. Validation Catalog 决定测试命令与通过/失败语义。
6. 领域规范解释长期规则、不变量和扩展方式。
7. Current Status、证据、Roadmap、ADR 和 History 分别记录当前快照、一次事实、未来、理由和过去。

代码、JSON、Workflow 或验证定义不一致时停止相关流程，登记同步债务后修复。

## 2. 文档角色

| 角色 | 职责 | 不得承担 |
| --- | --- | --- |
| `current_authoritative_master` | 总目标、完整生命周期、边界和全树导航 | 复制全部命令 |
| `workflow_index/runbook` | 阶段顺序、输入输出、生产命令、Gate 调用 | 定义领域不变量或复制测试命令 |
| `technical_specification/reference` | 数据契约、算法、资产规则和实现解释 | 另建日常主流程 |
| `validation_index/catalog` | Gate 组成及 `VAL-*` 准确测试定义 | 普通装配/导入命令 |
| `visual_acceptance_catalog` | `VIS-*` 人工判定 | 自动化成功判断 |
| `recovery_runbook` | `REC-*` 停止与恢复 | 新增正常生产路径 |
| `current_status_snapshot` | 当前能力、版本和债务 | 历史流水账 |
| `active_roadmap/uncommitted_backlog` | 已排期未来/未承诺候选 | 覆盖当前规则 |
| `adr_index/decision` | 已接受决定与理由 | 运行步骤 |
| `history_index/append_only/archived` | 已发生事件和不可变快照 | 当前执行入口 |
| `compatibility_redirect` | 保持旧路径可用 | 保存第二套正文 |

## 3. 状态

允许的当前状态值：`current`、`production`、`validated_pilot`、`manual_verified`、`planned`、`compatibility`、`archived`。

同一文档含不同成熟度时，页级状态使用最能描述主体的值，分项在能力矩阵中逐项标注。`planned` 不得包含可被误认为已验证入口的命令。

## 4. 生命周期与 ID

- `WF-00..WF-09`：一次生产运行的固定阶段。
- `GATE-00..GATE-09`：各阶段唯一退出门禁。
- `VAL-<DOMAIN>-NN`：机器、结构或文件验证。
- `VIS-<DOMAIN>-NN`：人工视觉验收。
- `REC-<DOMAIN>-NN`：失败恢复。
- `RM-*`：开发 Roadmap，不能与 `WF-*` 混为同一阶段。
- `ADR-NNNN`：架构决定。

ID 在全部现行文档中必须唯一；引用可以重复，定义标题只能有一个。

## 5. 必需元数据

除不可变旧快照外，每份现行 Markdown 顶部必须包含：

```text
文档角色
状态
适用阶段
权威范围
上级入口
上游
下游
最近核验
```

`上级入口` 必须形成从 Master 可达的有向导航。目录 README 负责索引该目录所有现行子文档。

## 6. Workflow 固定结构

每份 `WF-*` 必须按顺序包含：

1. `目的与使用时机`
2. `当前范围与非目标`
3. `进入条件`
4. `输入与输出`
5. `执行环境`
6. `执行步骤`
7. `退出门禁`
8. `失败与恢复`
9. `技术依据与下一阶段`

阶段文档必须指出前一阶段、下一阶段、当前状态和 Exit Gate。正常命令只在这里维护；验证命令通过 `VAL-*` 链接调用。

## 7. Validation 固定结构

每个 `VAL-*` 定义必须给出：生命周期阶段、触发频率、状态、执行模式、系统问题、输入、准确入口、输出、通过条件、成功证明、不证明以及失败去向。

每个 `VIS-*` 必须给出：阶段、视角/姿态、检查对象、接受标准和证据。每个 `REC-*` 必须使系统回到可从阶段开头重跑的状态。

## 8. 单一命令来源

- 普通生产命令：对应 `WF-*`。
- Gate/测试命令：`VALIDATION_CATALOG.md`。
- 失败恢复命令：`RECOVERY_RUNBOOK.md`。
- 领域维护命令：所属领域规范，且不得伪装成日常生产。
- `IMPLEMENTATION_INDEX.md` 只映射文件与所有者，不复制命令块。

兼容页和 Master 只链接权威来源。相同命令不得在多个当前文档中独立维护。

## 9. 当前、计划和历史

Current 只描述现在；Roadmap 只描述已接受未来；Backlog 只保存未承诺候选；History 只保存发生过的事实。计划功能开始实现时才加入真实命令，验证通过后才允许改变状态。

重构旧文档前，复制所有将改写原文到日期化 history 子目录，保留相对路径并生成 SHA-256 清单。既有不可变快照不得修改。

## 10. 导航与未来预留

Master 必须给出完整生命周期和按目录的文档地图。每份缩略信息必须链接到 Workflow、领域规范、验证、Reference 或规划文档。未来能力可以有正式阶段契约，但必须明确 `planned`、缺失实现和预期 Gate。

## 11. 变更同步矩阵

| 变化 | 至少同步 |
| --- | --- |
| 生产顺序/命令 | Workflow、Master 摘要、Implementation Index、相关验证 |
| JSON schema/资产 ID | 领域规范、Workflow 输入、Implementation Index、测试 |
| 新测试或 Gate | Validation README/Catalog、对应 Workflow、Master |
| 能力成熟度 | Current Status、Workflow、Master、Roadmap、Milestone |
| 架构决定 | 新 ADR、Master、受影响规范 |
| 路径/版本 | External Directories、Implementation Index、Current Status |

## 12. 自动审计

只读审计器：

```powershell
python D:\UE\Lance_Work\00_engine\scripts\documentation\check_character_factory_docs.py `
  --root D:\UE\Lance_Work\20_planning\data_design\character_creator\full_process
```

审计检查链接、锚点、Master 可达性、目录索引、元数据、Workflow 链、ID 定义/引用和历史哈希。退出码 0 才能完成文档变更；`--json` 输出机器可读报告。

行号级递归导航由 [`reference/DOCUMENT_LINK_TRACE.md`](./reference/DOCUMENT_LINK_TRACE.md) 保存。修改现行 Markdown 的链接或行数后，先重新生成，再执行上述审计：

```powershell
python D:\UE\Lance_Work\00_engine\scripts\documentation\generate_character_factory_link_trace.py `
  --root D:\UE\Lance_Work\20_planning\data_design\character_creator\full_process
```

## 13. 兼容入口

`character_creator/README.md` 是父目录唯一导航入口。已被 `full_process` 取代的旧 Master、Status、面部规范和日期化计划不再保留逐文件跳转页；需要审计旧原文时只进入 `history`。确有外部依赖的旧路径才允许建立短跳转，且必须登记删除条件。
