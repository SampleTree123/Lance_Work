# HANDOFF：DataMake 当前接手说明

本文件只规定接手顺序和恢复边界，不复制会快速变化的批次数字。当前事实的唯一人类入口是 [`PROJECT_STATUS.md`](./20_planning/data_design/character_creator/full_process/project_management/status/PROJECT_STATUS.md)，机器入口是同目录的 `PROJECT_STATE.json`。

## 新会话阅读顺序

1. [`AGENTS.md`](./AGENTS.md)：协作与仓库规则。
2. [`full_process/README.md`](./20_planning/data_design/character_creator/full_process/README.md)：项目定义、文档树和端到端 Workflow。
3. [`PROJECT_STATUS.md`](./20_planning/data_design/character_creator/full_process/project_management/status/PROJECT_STATUS.md)：当前计划、活动批次、唯一下一步和阻塞。
4. 当前状态指向的 `WF-*` 文档：确认进入条件和 Exit Gate。
5. Workflow 指向的 Technical 文档：执行准确代码、配置、验证和恢复步骤。

最短路径：

```text
Master -> Current Status -> Active Workflow -> Technical -> Validation
```

## 当前工作定位

当前计划和 Workflow 不在本页硬编码。接手者必须读取 `PROJECT_STATE.json` 的：

```text
current_plan_id
active_batch_id
active_workflow_id
next_action
blocking_issues
```

随后核对对应 Plan Requirement、Workflow Status 和 Batch Status。若三者冲突，停止执行并按 [`GOVERNANCE.md`](./20_planning/data_design/character_creator/full_process/GOVERNANCE.md) 的权威顺序处理。

## 本地、Git 与服务器边界

- 本地 Windows：CC5、UE Editor、MCP/Bridge、资产导入、视觉验收和本地 Smoke。
- Git：代码、文档、Schema、Registry、Manifest、哈希与轻量证据。
- 独立资产层：CC/UE 二进制资产、正式 UE `Content/` 和大型媒体。
- 服务器：环境/项目预检、性能基准、可续跑批量渲染和交付构建。

路径别名和服务器工作根见 [`PATH_ALIASES.md`](./20_planning/data_design/character_creator/full_process/reference/PATH_ALIASES.md) 与 [`SERVER_EXECUTION.md`](./20_planning/data_design/character_creator/full_process/technical/rendering_release/SERVER_EXECUTION.md)。

## 恢复规则

应用崩溃、会话重启或上下文中断后：

1. 不恢复 UE/CC 自动保存包，除非对应 Technical 恢复步骤明确要求。
2. 重新执行 `WF-00` 会话预检。
3. 检查 Git 工作树，不回退无法确认来源的修改。
4. 从当前 Workflow 的最后一个已验证 Gate 继续，不从对话中的“应该完成”继续。
5. 将故障、已验证恢复动作和未解决风险写回对应 Technical/Status。

通用恢复入口见 [`RECOVERY.md`](./20_planning/data_design/character_creator/full_process/technical/validation/RECOVERY.md)。

## 服务器接手

仅拉取 Git 不代表服务器具备生产资产。按 [`SERVER_EXECUTION.md`](./20_planning/data_design/character_creator/full_process/technical/rendering_release/SERVER_EXECUTION.md) 依次执行环境预检、资产/项目 Smoke 和小规模基准。环境阶段可运行：

```bash
bash 20_planning/implementation/FIRST_BATCH_SERVER_PREFLIGHT.sh --environment-only
```

正式 Render Jobs 执行器、媒体 Sidecar/Manifest 和节点级重试是否已达到生产 Gate，以当前 `WF-80` 状态为准。

## 文档维护

完成阶段、改变计划、修改实现或新增长期输出后，调用项目级 `character-factory-doc-maintenance` Skill，再运行：

```powershell
python 00_engine/scripts/documentation/build_script_lifecycle_catalog.py
python 00_engine/scripts/documentation/build_output_inventory.py
python 00_engine/scripts/documentation/check_character_factory_docs.py --json
```

重构快照和旧文档只用于审计，不能作为当前执行入口。
