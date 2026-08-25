# 角色工厂文档治理规则

> 文档角色：`documentation_governance`
> 上级入口：[`CHARACTER_FACTORY_MASTER_SPEC.md`](./CHARACTER_FACTORY_MASTER_SPEC.md)
> 最近核验：2026-08-06

## 1. 权威层级

发生冲突时按以下规则处理，但不得静默忽略冲突：

1. Python 和插件代码决定一次调用实际执行了什么。
2. 机器 JSON 决定精确 ID、路径、哈希、枚举、参数和登记状态。
3. Master 决定当前被接受的跨系统流程、能力边界和阅读入口。
4. 技术文档解释如何复现代码与配置定义的行为。
5. `CURRENT_STATUS.md` 记录当前版本、已验证范围和已知同步债务。
6. artifacts、截图和报告证明一次实际运行发生了什么。
7. Roadmap、Backlog 和历史文件不得覆盖当前规则。

代码、JSON、Master 和技术文档不一致时停止该流程，先登记冲突，再同步修复。

## 2. 文档状态

| 状态 | 含义 |
| --- | --- |
| `production` | 当前默认入口，具备代码、配置、验证和恢复说明 |
| `validated_pilot` | 代表样本验证成功，但尚未扩展到目标规模 |
| `manual_verified` | 人工 UI 流程成功，但没有稳定自动入口 |
| `planned` | 只有需求、设计或预留位置，不可按生产能力引用 |
| `historical` | 只用于审计和理解过去，不再执行 |

## 3. 执行模式

技术步骤只能使用以下标签：

| 标签 | 含义 |
| --- | --- |
| `POWERSHELL` | 在本机 PowerShell 中执行安装、目录或守卫操作；不是 Python 运行环境 |
| `SYSTEM_PYTHON` | 在 PowerShell/系统 Python 中运行，不依赖 `RLPy` |
| `CC_RLPY` | 必须在 Character Creator 5 Python 环境中执行 |
| `CC_UI` | 必须由用户在 CC 图形界面中确认或操作 |
| `BRIDGE_CLI` | 外部客户端提交受控 Bridge 请求 |
| `UE_REMOTE` | 系统 Python 通过 UE Python Remote Execution 向已运行编辑器提交脚本；不依赖 Unreal MCP |
| `UE_MCP` | UE 编辑器在线且 MCP 服务监听时执行 |
| `UE_UI` | 在 UE 编辑器图形界面执行或确认 |
| `PLANNED` | 尚无有效入口，禁止当成命令执行 |

## 4. 技术步骤格式

每份 Runbook 必须提供：

```text
步骤 ID
成熟度与执行模式
前置条件和破坏性影响
入口文件或 UI 路径
完整输入
准确命令或操作
输出目录和关键文件
自动通过条件
人工视觉条件
失败恢复方式
当前证据
```

不得用“运行相关脚本”“正常导入”“按之前方式”等依赖对话记忆的表述。

技术规范可以解释算法、数据模型和约束，而不重复整段实现源码；但必须链接到当前代码和机器配置。Runbook 和验证文档则必须给出能够直接执行的命令或 UI 操作，并明确：

- 哪个外层入口可由系统 Python 调用。
- 哪个内部脚本只能由 CC/RLPy 或 UE 加载，禁止直接运行。
- 输入文件、输出报告、关键字段和自动通过条件。
- 当前没有实现代码时明确写 `PLANNED / 无可执行入口`，不得使用“当前 Runbook”“相关脚本”等占位表述。

## 5. 路径规则

命令使用 [`reference/EXTERNAL_DIRECTORIES.md`](./reference/EXTERNAL_DIRECTORIES.md) 定义的变量；同一文档首次出现时必须给出当前本机绝对值。机器 JSON 中保留真实绝对路径，不为文档可读性修改。

## 6. 当前、计划和历史的分离

- `CURRENT_STATUS.md` 可以覆盖更新，只描述现在。
- `planning/ROADMAP.md` 只保存已经排期的未完成工作。
- `planning/BACKLOG.md` 保存尚未承诺的候选。
- `decisions/` 保存已经接受的技术选择、理由和后果。
- `history/MILESTONE_LOG.md` 只追加完成事件和证据。
- `history/legacy_*` 中的原文永不修改。

## 7. 未来能力预留

未来能力先写入对应子目录 README 的能力矩阵并标记 `planned`。开始实施后才创建技术文件；禁止建立只有标题和 TODO 的空白文档。

## 8. 每次变更的同步矩阵

| 变化 | 必须更新 |
| --- | --- |
| 精确参数、路径或资产池 | 机器 JSON、对应技术文档、Current Status、Master 摘要 |
| 执行代码或命令 | 代码、Runbook、Implementation Index、测试证据 |
| 接受重大策略 | ADR、Master、相关技术文档 |
| 完成阶段 | Current Status、Milestone Log、Roadmap |
| 新候选想法 | Backlog；未接受前不得进入 Master 当前流程 |
| 废弃入口 | 替代 ADR、兼容跳转、历史记录、全仓链接更新 |

## 9. 兼容页与外部文档

`character_creator` 根目录中的旧文件名是兼容入口，不再保存当前技术正文。代码旁的 README 可以解释组件自身，但必须回链本体系；协议字段仍由代码目录中的协议文档负责。
