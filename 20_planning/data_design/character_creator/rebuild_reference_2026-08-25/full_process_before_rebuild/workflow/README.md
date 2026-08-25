# 角色工厂生产 Workflow

> 文档角色：`workflow_index`
> 状态：`current`
> 适用阶段：`WF-00..WF-09`
> 权威范围：生产生命周期顺序、阶段边界和阶段间交付契约
> 上级入口：[`../CHARACTER_FACTORY_MASTER_SPEC.md`](../CHARACTER_FACTORY_MASTER_SPEC.md)
> 上游：[`../CURRENT_STATUS.md`](../CURRENT_STATUS.md)
> 下游：本目录十个阶段 Runbook
> 最近核验：2026-08-24

本目录回答“实际生产时下一步做什么”。领域规则由 `cc_details/`、`bridge_details/`、`cc_ue_transfer/` 和 `ue_details/` 解释；测试实现由 `validation/` 解释。不得从技术规范中拼接一条自创生产流程。

2026-08-19 至 2026-08-26 的受限实现范围由 [第一批数据 Sprint](../planning/FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md) 冻结。`WF-08/09` 已进入 `in_progress` 并有本地可验证路径，但对应 Gate 在完整机器与人工证据齐全前仍未通过。

## 1. 唯一执行顺序

| 阶段 | 入口 | 退出门禁 | 当前状态 |
| --- | --- | --- | --- |
| `WF-00` 会话预检 | [`WF-00-SESSION-PREFLIGHT.md`](./WF-00-SESSION-PREFLIGHT.md) | `GATE-00 SESSION_READY` | `validated_pilot` |
| `WF-01` 角色定义 | [`WF-01-CHARACTER-DEFINITION.md`](./WF-01-CHARACTER-DEFINITION.md) | `GATE-01 MANIFEST_READY` | `validated_pilot` |
| `WF-02` CC 装配 | [`WF-02-CC-ASSEMBLY.md`](./WF-02-CC-ASSEMBLY.md) | `GATE-02 ASSEMBLY_COMPLETE` | `validated_pilot` |
| `WF-03` CC 验收 | [`WF-03-CC-ACCEPTANCE.md`](./WF-03-CC-ACCEPTANCE.md) | `GATE-03 CC_ACCEPTED` | `validated_pilot` |
| `WF-04` CC 导出 | [`WF-04-CC-EXPORT-BUNDLE.md`](./WF-04-CC-EXPORT-BUNDLE.md) | `GATE-04 BUNDLE_READY` | `validated_pilot` |
| `WF-05` UE 参考导入 | [`WF-05-UE-IMPORT-REFERENCE.md`](./WF-05-UE-IMPORT-REFERENCE.md) | `GATE-05 UE_REFERENCE_ACCEPTED` | `first_batch_validated`，32/32 FullReference Look |
| `WF-06` UE 角色运行时 | [`WF-06-UE-CHARACTER-RUNTIME.md`](./WF-06-UE-CHARACTER-RUNTIME.md) | `GATE-06 RUNTIME_ACCEPTED` | `validated_pilot`，仅 M02 |
| `WF-07` 动画与道具 | [`WF-07-ANIMATION-AND-PROPS.md`](./WF-07-ANIMATION-AND-PROPS.md) | `GATE-07 PERFORMANCE_ACCEPTED` | `validated_pilot`，无道具 P0 Runtime 已通过；生产池未完成 |
| `WF-08` 场景与相机 | [`WF-08-SCENE-CAMERA-SEQUENCE.md`](./WF-08-SCENE-CAMERA-SEQUENCE.md) | `GATE-08 SCENE_READY` | `first_batch_local_matrix_validated`，30 个生产组合与 32-Look 四机位代表矩阵已通过 |
| `WF-09` 渲染数据包 | [`WF-09-RENDER-DATASET-PACKAGE.md`](./WF-09-RENDER-DATASET-PACKAGE.md) | `GATE-09 DATASET_ACCEPTED` | `in_progress`，图/链/15,000 回合文本层与代表链已通过；正式 640 节点媒体未验收 |

## 2. 执行规则

1. 从 `WF-00` 开始；已有上游证据时也要核对其 Gate，不按文件是否存在推断通过。
2. 每个阶段只接收上一个阶段定义的输出。
3. Workflow 中的普通命令是生产命令的唯一来源；Gate 的测试命令只在 [`../validation/VALIDATION_CATALOG.md`](../validation/VALIDATION_CATALOG.md) 定义。
4. 自动成功不代替 [`../validation/VISUAL_ACCEPTANCE.md`](../validation/VISUAL_ACCEPTANCE.md) 中要求的人工视觉判定。
5. `planned` 阶段只定义契约，不可执行，也不能用 M02 Pilot 结果替代。
6. 笔记本资源有限时按 CC 段和 UE 段分段运行，不要求同时打开 CC 与 UE。

## 3. 维护与扩展分支

日常生产只走 `WF-*`。新增 BodyFit、Face seed、皮肤、毛发、服装或动画库属于维护/扩展任务，应从相应领域技术文档进入，更新机器注册表并运行该领域回归后，再回到受影响的 Workflow。
