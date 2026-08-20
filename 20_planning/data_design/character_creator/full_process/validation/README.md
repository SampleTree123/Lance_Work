# 生命周期门禁与验证索引

> 文档角色：`validation_index`
> 状态：`current`
> 适用阶段：`WF-00..WF-09`
> 权威范围：Gate 组成、验证类型和阶段晋级规则
> 上级入口：[`../CHARACTER_FACTORY_MASTER_SPEC.md`](../CHARACTER_FACTORY_MASTER_SPEC.md)
> 上游：[`../workflow/README.md`](../workflow/README.md)
> 下游：[`VALIDATION_CATALOG.md`](./VALIDATION_CATALOG.md)、[`VISUAL_ACCEPTANCE.md`](./VISUAL_ACCEPTANCE.md)、[`VISUAL_REVIEW_PORTAL.md`](./VISUAL_REVIEW_PORTAL.md)、[`RECOVERY_RUNBOOK.md`](./RECOVERY_RUNBOOK.md)
> 最近核验：2026-08-17

## 1. 四个概念

| 概念 | 回答的问题 | 权威位置 |
| --- | --- | --- |
| Workflow Stage `WF-*` | 生产流程现在做什么 | `workflow/` |
| Exit Gate `GATE-*` | 什么条件满足后才能进入下一阶段 | 本文 |
| Validation `VAL-*` / Visual `VIS-*` | 如何证明机器结构或人工视觉正确 | Validation Catalog / Visual Acceptance |
| Recovery `REC-*` | 失败后怎样回到可重跑状态 | Recovery Runbook |

Gate 不是脚本，Runbook 也不是测试。一个 Gate 会组合零到多个 `VAL-*`、`VIS-*`；成功只在其适用范围内成立。

## 2. 生命周期 Gate

| Gate | 所属阶段 | 必需验证 | 当前状态 | 成功含义 |
| --- | --- | --- | --- | --- |
| `GATE-00 SESSION_READY` | `WF-00` | 每次 CC 会话 `VAL-BRIDGE-01`；代码/JSON 改动时另加 `VAL-CODE-01` | `validated_pilot` | 本轮所需执行通道在线且无已知阻塞 |
| `GATE-01 MANIFEST_READY` | `WF-01` | `VAL-MANIFEST-01` | `production` | 请求已确定性编译且只引用审核资产 |
| `GATE-02 ASSEMBLY_COMPLETE` | `WF-02` | `VAL-CC-02` 机器部分；BodyFit 变更时另加 `VAL-CC-01` | `validated_pilot` | CC 作业及结构报告完成，不代表视觉通过 |
| `GATE-03 CC_ACCEPTED` | `WF-03` | `VAL-CC-02` + `VIS-CC-01/02/03`；新 Headshot 身份原子另加 `VAL-CC-03/04/05` + `VIS-CC-04`；有新 Look 时先执行 `VAL-CC-07`，再执行 `VIS-CC-05` | `validated_pilot` | 角色在 CC 中通过机器和人工验收并有规范项目 |
| `GATE-04 BUNDLE_READY` | `WF-04` | `VAL-BUNDLE-01` | `validated_pilot` | FBX/JSON/纹理和来源形成可追溯 Bundle |
| `GATE-05 UE_REFERENCE_ACCEPTED` | `WF-05` | `VAL-XFER-01` + `VIS-XFER-01` | `validated_pilot`，仅 M02 | 完整参考角色在 UE 中正确 |
| `GATE-06 RUNTIME_ACCEPTED` | `WF-06` | `VAL-UE-01` + `VIS-UE-01` | `validated_pilot`，仅 M02 | 模块、Leader Pose、Morph 和材质运行正确 |
| `GATE-07 PERFORMANCE_ACCEPTED` | `WF-07` | 适用的 `VAL-UE-02/03/04` + `VIS-UE-02`；毛发/道具测试尚缺 | `validated_pilot`，能力分项 | 模块 Hybrid、Elder 与 FullReference direct-Morph Pilot 分别通过，不能覆盖未实现分项 |
| `GATE-08 SCENE_READY` | `WF-08` | `VAL-SCENE-01` + `VIS-SCENE-01` | `planned` | 未来场景、角色、道具、相机和 Sequence 可渲染 |
| `GATE-09 DATASET_ACCEPTED` | `WF-09` | `VAL-DATASET-01` + `VIS-DATASET-01` | `planned` | 未来媒体、GT、sidecar、配置和证据一致 |

## 3. 何时运行哪些验证

- 每个新 CC 会话：`VAL-BRIDGE-01`。
- Python、Bridge 或机器 JSON 变化后：`VAL-CODE-01`。
- 每次角色请求编译后：`VAL-MANIFEST-01`。
- BodyFit 源或比例配置变化后：`VAL-CC-01`；普通角色不重复全十体型烟测。
- 每个完整角色装配后：`VAL-CC-02` 和全部 `VIS-CC-*`。
- 每个新 Headshot 原始项目保存或 Profile 升级后：`VAL-CC-03` 与 `VIS-CC-04`；创建/复制/修改原型包后另运行 `VAL-CC-04`；首次接到 BodyFit 或修改 project-seed 顺序后运行 `VAL-CC-05`；生产晋级时还必须执行完整 `VIS-CC-02`。
- 服装来源新增、删除或替换后：`VAL-CC-06`；family/鞋规则、代表抽样、BodyFit、装配器或加载兼容注册表变化后，以及每个恢复分片执行时：`VAL-CC-07`。静态机器与人工审查接受后运行 `VAL-CC-08` 动作压力门禁，再完成 `VIS-CC-05` 的动态结论。源包预览只用于候选筛选；当前动态结论是用户抽查接受，不替代未来十体型和生产动画范围的完整验收。
- 从 2026-08-09 起，任何产生截图或联系表的新视觉审查：机器完整性检查后、请求用户审查前，按 [`VISUAL_REVIEW_PORTAL.md`](./VISUAL_REVIEW_PORTAL.md) 登记独立结果分支；人工结论写回 run 后才能汇总对应 `VIS-*`。
- 每个导出 Bundle：`VAL-BUNDLE-01`。
- 每个首次 UE 完整参考导入：`VAL-XFER-01` 与 `VIS-XFER-01`。
- 模块 Blueprint 或 Morph 广播变化后：`VAL-UE-01` 与 `VIS-UE-01`。
- 模块 Hybrid 动画分层变化后：`VAL-UE-02`；Elder Morph 变化后：`VAL-UE-03`；FullReference P0 Motion、Face clip、Wrapper 或 Post Process 策略变化后：`VAL-UE-04`。

## 4. 晋级规则

状态晋级必须同时满足可复现输入、适用自动验证、人工审核、恢复路径、文档同步和机器注册表一致。`not_required` 必须说明原因；`planned`、`skipped` 或缺证据不能当作通过。

## 5. 兼容入口
