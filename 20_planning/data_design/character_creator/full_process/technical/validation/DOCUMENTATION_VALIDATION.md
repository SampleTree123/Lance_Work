# 文档体系审计

> 文档 ID：`TECH-VALIDATION-04`
> 文档类型：`technical`
> 生命周期：`current`
> 适用阶段：全部 Workflow
> 实现所有权：文档结构、可达性、语义新鲜度、计划/状态同步和代码归属
> 验证所有权：`VAL-DOC-01`
> 输出契约：`OUT-GLOBAL-DOC-AUDIT`
> 最近核验：2026-10-13（计划基数与冻结后独立审计合同核对）

## 1. 触发条件

Workflow、代码入口、Registry、Schema、输出目录、计划、状态、Gate 或重要决定发生变化后运行。仅修正文案且不改变事实时仍执行链接/元数据检查。

## 2. 检查范围

- Master 可到达全部活跃索引；Workflow 可到达 Technical、Validation 和 Status；
- Workflow、Validation、Output、Technical、Status/Plan/History、Reference/Registry 与 Governance/Templates 分别通过自己的契约检查；
- 每个 Workflow 的 `VAL-*` 和 `OUT-*` 均在对应目录定义，并在实现 Technical 与 Status 中闭合；
- 每份活跃文档具备类型所需元数据；
- 获授权执行中恰好一个 `current` 主计划，且 `PROJECT_STATE.json` 与人类状态一致；仅在明确 `idle_after_completed_plan` 且 `current_plan_id=null` 的结项空闲状态允许零个 current，不自动启动 queued；
- `00_engine/` 与 `20_planning/implementation/` 内所有 Character Factory 脚本有生命周期和 Technical 所有者，且每个 `production` 入口被其 owner 文档直接点名并解释；
- Script Catalog 的路径、大小和 SHA-256 与工作树一致；
- Output Inventory 覆盖输出根全部直接作用域和精确保留路径，每个作用域有 Technical owner；ownership/retention 规则由 owner 文档直接说明；
- 当前批次数字只由状态/机器清单维护，入口文档不复制过期值；
- 活跃文档不链接原始重构快照作为执行入口；
- 根 README、HANDOFF 和代码 README 不与当前状态冲突。

各区先独立检查，只有独立契约通过后才检查跨层关系。不得通过增加一个总索引来掩盖某区缺少输入、输出、实现、证据或状态所有者。

## 3. 自动入口

检查器位于：

```text
00_engine/scripts/documentation/check_character_factory_docs.py
```

先更新机器目录，再审计：

```powershell
python 00_engine/scripts/documentation/build_script_lifecycle_catalog.py
python 00_engine/scripts/documentation/build_output_inventory.py
python 00_engine/scripts/documentation/check_character_factory_docs.py --json
```

文档测试：

```powershell
python -m pytest `
  00_engine/scripts/documentation/tests `
  00_engine/scripts/dataset/tests `
  00_engine/scripts/unreal/tests -q
```

检查器当前支持本目录结构和 `WF-00/10/.../90` 编号，并验证执行中唯一当前计划／显式结项空闲的计划基数、`PROJECT_STATE.json`、Script Catalog 和 Output Inventory。JSON 输出保留顶层 `errors/warnings/stats/success`，并新增：

- `subsystems`：DocumentIO、Metadata、Navigation、Master、Workflow、Validation、Output、Technical、Status、Plan、History、Decisions、Reference、Registry、Governance 和 Templates 的独立结果；
- `cross_layer`：只包含 `WF -> VAL -> Technical -> OUT -> Status`、Plan Requirement 回链、机器状态 ID 等明确跨层契约。

任何 `subsystems.<name>.success=false` 都使总结果失败；`cross_layer.success=true` 不能抵消独立子系统失败。旧的逐行 Link Trace 不再是人工必读产物。

Workflow 子系统还强制检查每个阶段是否具备可执行层契约：编号步骤必须指向精确脚本、配置或明确标注的人工/待实现边界；输出段必须解释输出组成、用途、主要下游和当前 Status owner。Output 子系统要求每个 `OUT-*` 有独立定义，Status 子系统要求当前输出表解释每项产物在当前批次中的实际角色。这样可以防止 Workflow 只有流程概述，却无法定位代码、产物含义或当前落点。

检查器回归测试：

```text
00_engine/scripts/documentation/tests/test_check_character_factory_docs.py
00_engine/scripts/documentation/tests/test_build_output_inventory.py
```

前者构造最小完整文档树并覆盖 16 个独立检查域，回归测试包括未定义验证、Status 漏输出、错误 Plan 生命周期、Technical 元数据缺失、Workflow 缺少精确实现导航、输出缺少用途/下游、Output 缺少独立定义和 Status 缺少当前角色；后者覆盖 Script Catalog 与 Output Inventory 的扫描、owner、哈希和保留规则。

## 4. 输出与保留

`VAL-DOC-01` 的正式证据写入唯一 Run Root：

```text
%OUTPUT_ROOT%/documentation_audit/<run_id>/
  manifest.json
  audit.json
  pytest.txt
  result.json
```

其中 `audit.json` 保存检查器的机器结果，`pytest.txt` 保存本页定义的测试结果，`result.json` 汇总自动检查与人工抽查结论，`manifest.json` 绑定实现/Git 版本、输入哈希、输出清单和保留状态。上一版接受运行是：

```text
%OUTPUT_ROOT%/documentation_audit/documentation_rebuild_20260825_v1/
```

已被以下接受运行取代：

```text
%OUTPUT_ROOT%/documentation_audit/documentation_rebuild_20260825_v2/
```

`v2` 绑定 `OUT-GLOBAL-DOC-AUDIT`，并覆盖精确实现导航、输出语义/下游与 Status 当前角色契约；它曾作为该阶段的接受结果，现与 `v1` 一样按 `superseded` 保留且不得原地覆盖。新一轮因文档、检查器、目录生成器或所有权变化而通过后，必须创建新 `run_id` 并显式填写 `supersedes`。

正式 Render Job 执行器、本地 Gate、`WF-80` 状态和输出保留规则完成收口后，当前接受运行升级为：

```text
%OUTPUT_ROOT%/documentation_audit/documentation_rebuild_20260825_v3/
```

`v3` 绑定正式执行器实现与本地证据、计划 `R07` 完成、当时的服务器下一步以及更新后的 Script Catalog/Output Inventory；它取代 `v2`，并按 `retained_evidence` 保留。2026-08-28 的服务器阻塞状态和 Script Catalog 更新已使其不再代表当前文档版本。服务器副本缺少 Windows 本地历史输出，不能在该副本上伪造 Output Inventory 通过；必须回到完整本地输出盘重建 Inventory、运行全审计并创建新 `run_id`。前述 `v1/v2/v3` 段落只用于版本演进说明。

2026-08-30 模块化服装 Pilot 收口后的历史接受运行是：

```text
%OUTPUT_ROOT%/documentation_audit/documentation_modular_outfit_pilot_20260830_v3/
```

以下两个失败 Run 均按 `disposable` 保留到本轮收口完成，不能作为 `VAL-DOC-01` 证据：

```text
%OUTPUT_ROOT%/documentation_audit/documentation_modular_outfit_pilot_20260830_v1/
%OUTPUT_ROOT%/documentation_audit/documentation_modular_outfit_pilot_20260830_v2/
```

`v1` 在创建 Run Root 后、重建 Output Inventory 前执行，因 Inventory 缺少新直接作用域而正确失败。`v2` 已重建 Inventory，随后因 owner 文档没有直接写出 `v1` 的完整物理前缀而正确失败；两次运行的测试均通过，但不能替代审计结论。`v3` 在完整登记三个作用域和 owner 说明后重新执行 16 个独立子系统、跨层契约和完整测试，且不得覆盖前两个 Run。

2026-09-30 全库衣柜/发型状态与网格视觉结论同步后的新审计 Run Root 为：

```text
%OUTPUT_ROOT%/documentation_audit/documentation_full_sync_20260930_v1/
```

精确保留前缀为 `documentation_audit/documentation_full_sync_20260930_v1`，按 `retained_evidence` 保存；是否通过只以该目录 `result.json` 为准。该 Run 在全部独立检查和完整测试通过后取代 `documentation_audit/documentation_modular_outfit_pilot_20260830_v3`；旧运行按 `superseded` 保留，本次不删除或覆盖它。2026-08-25 的 v3 仍保留为当时实现接受证据，不代表当前文档版本。

除正式四项产物，本次保存 `before_manifest.json` / `before/active_tree/`（更新前快照）、`manual_subsystem_review.json`（逐区人工检查）、`asset_evidence_check.json`（索引/落盘/保留哈希复查）、`inputs.lock.json`（最终工作树输入）、`git_before.txt` 、`maintenance.py` / `complete_checks.py`（本次一次性同步和审计实现）。这些文件只属于该运行的审计证据，快照不作为日常执行入口；不能从本轮文档测试通过推导 CC、UE、服务器、动态或打包的新增运行时 Gate。

## 5. 人工审计

自动通过后仍抽查：从 Master 能否自然找到当前下一步、任一 Workflow 的真实命令、代码输入/输出、恢复方式和状态；随机选择生产脚本与输出目录做正反向追溯。发现只能依靠对话历史理解的内容即判定文档缺口。

## 6. 维护 Skill

版本化权威源和当前工作区安装位置分别为：

```text
%DOC_SKILL_SOURCE%/SKILL.md
%DOC_SKILL_ROOT%/SKILL.md
```

新机器或仓库更新后，从 `%LANCE_ROOT%` 同步安装副本：

```powershell
$Source = '.\.codex\skills\character-factory-doc-maintenance\SKILL.md'
$InstallRoot = '..\.codex\skills\character-factory-doc-maintenance'
New-Item -ItemType Directory -Force $InstallRoot | Out-Null
Copy-Item -LiteralPath $Source -Destination "$InstallRoot\SKILL.md" -Force
```

同步后比较两个文件的 SHA-256，并分别运行 Skill Validator。阶段完成、计划切换、实现/输出变化或交接前调用 `character-factory-doc-maintenance`。Skill 要求先分别关闭受影响子系统，再校验显式跨层契约、重建机器目录并执行本页检查器；它不替代自动检查器，也不允许跳过运行证据。

## 7. 冻结后独立闭合检查单

执行任务仍在写代码或产物时，审计只描述该次检查点。最终接受必须绑定最后代码、输入配置、输出、当前文档和机器清单；早于后续修改的 pytest／审计只保留其原检查范围。先逐项关闭以下16个独立子系统，再接受显式跨层合同：

| 独立子系统 | 最终最低检查 |
| --- | --- |
| DocumentIO | 活跃文档可按UTF-8读取，机器JSON合法，读取错误为零 |
| Metadata | 文档类型、ID、生命周期、角色所需字段完整且唯一 |
| Navigation | 所有活跃文档可达，直接子文档有索引，文件与anchor引用存在 |
| Master | 顺向入口指到当前Status和长期Workflow，不重复动态数字 |
| Workflow | 阶段、前后序、精确实现入口、输入、输出组成／下游、VAL／OUT及失败恢复完整 |
| Validation | 稳定VAL有触发、证据、通过／失效条件、实现和状态落点，历史失败不改写 |
| Output | OUT契约与当前作用域owner明确，真实Inventory无缺项／不存在项，既有保留规则与owner说明一致 |
| Technical | 生产／辅助／测试有准确owner与生命周期，输入输出／命令／恢复完整，Catalog路径、规范化字节和SHA匹配最终文件 |
| Status | 人类／机器状态、Workflow／Batch事实与有效证据一致，未通过Gate显式pending，唯一下一步可执行 |
| Plan | 执行中唯一current，需求有验收／证据并与真实状态一致；未完父计划和用户暂停边界保留 |
| History | 只记录当时关闭事实，旧失败／回退／接受及旧代码pin保持原范围，不伪装当前事实 |
| Decisions | ADR状态、继承／替代关系和影响定义闭合，无未授权语义改变 |
| Reference | 路径别名、术语和状态词一致，不保存动态状态或机器输入真值 |
| Registry | 每个现用机器权威能反查到准确Technical owner与消费Workflow，路径／适用范围真实 |
| Governance | owner、冲突、同步、状态／计划基数和独立审计规则无矛盾 |
| Templates | 新建各类文档会满足当前元数据、状态／计划生命周期与独立合同 |

显式跨层复核包括 `WF -> VAL -> Technical -> OUT -> Status`、`Plan Requirement -> Workflow Status/Evidence`、`ADR -> 影响定义`、`Master -> 子系统入口`、Registry／机器状态ID与最终有效路径。只有16项各自通过且cross_layer通过，才能接受本轮总结果；局部范围与未检查的运行时／视觉Gate仍单独说明。
