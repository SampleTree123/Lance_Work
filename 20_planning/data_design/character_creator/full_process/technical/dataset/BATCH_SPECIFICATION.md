# 批次规格

> 文档 ID：`TECH-DATASET-03`
> 文档类型：`technical`
> 生命周期：`current`
> 适用阶段：`WF-10`
> 实现所有权：Batch ID、编辑轴、兼容域、媒体/交付规格、规模、停止与降级条件的一致性契约
> 验证所有权：`VAL-SPEC-01`
> 输出契约：`OUT-WF10-BATCH-SPEC`
> 运行环境：文档维护与系统 Python
> 最近核验：2026-08-25

## 1. 能力与边界

本能力把研究目标转换为可被资产冻结、图构建、渲染和发布共同读取的批次规格。它不选择具体资产、不生成节点，也不把计划目标自动视为已实现能力。

当前实现是“计划需求 + Batch Status + `PROJECT_STATE.json` + Schema”的受控组合，尚无单独的通用 Batch Spec Builder。该限制必须保留，不能假装已有一键生成器。

## 2. 权威输入

| 输入 | 作用 |
| --- | --- |
| 当前 `PLAN-*` | 目标、需求、完成条件、风险和允许降级 |
| `project_management/status/batches/<batch_id>.md` | 人类可读冻结规格与执行状态 |
| `project_management/status/PROJECT_STATE.json` | 当前批次关键机器字段 |
| `20_planning/data_design/schema/` | 节点、图、文本和媒体字段契约 |
| `20_planning/data_design/sampling/` | 链采样语义与标签 |

计划拥有“准备实现什么”，状态拥有“当前冻结了什么”，Schema 拥有“字段如何表达”。三者冲突时 `VAL-SPEC-01` 失败，不能任选一个继续。

## 3. 必填规格

每批至少定义：`batch_id`、任务目的、兼容域、节点因素、可编辑轴、链策略、目标规模、时长/fps/分辨率、GT/Sidecar、文本语言、输出布局、重试、停止条件、允许的版本化降级和明确不包含项。动态数值只保存在 Batch Status/机器配置，不复制到 Workflow/Master。

## 4. 执行步骤

1. 创建唯一 Batch Status 和计划需求映射。
2. 将可机器读取的关键字段写入 `PROJECT_STATE.json` 或版本化批次配置。
3. 对照 Schema/采样规范检查单位、枚举、ID 和依赖关系。
4. 运行文档审计与受影响的 Schema/Builder 测试。
5. 把 `VAL-SPEC-01` 结果和当前输出版本写入 `STATUS-WF-10`。

当前首批核验入口：

```powershell
python 00_engine/scripts/documentation/check_character_factory_docs.py --json
python -m pytest 00_engine/scripts/dataset/tests -q
```

## 5. 输出与保留

`OUT-WF10-BATCH-SPEC` 由当前计划、Batch Status、`PROJECT_STATE.json` 和适用 Schema/采样版本共同组成，全部为 Git `versioned_registry`。运行审计报告按 `OUT-GLOBAL-DOC-AUDIT` 保留；不为同一批次创建未关联的第二份数字清单。

## 6. 验证、恢复与限制

`VAL-SPEC-01` 检查必填字段、计划/状态/机器配置一致性、ID 唯一性、单位和不包含项。冲突时停止 `WF-20`，先明确哪个来源是正确事实，再版本化更新所有受影响所有者；禁止只改一份文档使检查通过。

新增通用 Batch Spec Builder 属于后续能力；实现前，跨文件一致性依赖文档检查器和领域测试，当前不宣称任意批次自动编译。
