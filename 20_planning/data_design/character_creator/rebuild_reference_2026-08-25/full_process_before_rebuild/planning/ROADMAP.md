# Character Factory 活动 Roadmap

> 文档角色：`active_roadmap`
> 状态：`current`
> 适用阶段：`global`
> 权威范围：当前 Sprint 之后仍需完成且已经接受的开发顺序
> 上级入口：[`README.md`](./README.md)
> 上游：[`../CURRENT_STATUS.md`](../CURRENT_STATUS.md) 与已接受 ADR
> 下游：活动 Sprint、Backlog 和受影响 Workflow
> 最近核验：2026-08-24

已完成工作不在本文件复述，统一见 [`MILESTONE_LOG.md`](../history/MILESTONE_LOG.md) 和日期化周报。被放弃的方法不保留在活动 Roadmap；仍有长期解释价值的约束才保留在 ADR 或技术规范中。

## 1. 当前最高优先级

[`FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md`](./FIRST_DATA_BATCH_SPRINT_2026-08-19_TO_2026-08-26.md)

本轮采用受限旁路：

```text
冻结 10 个生产动作（每性别 5 个）与 32 个 FullReference Look
  -> 固定单场景、单锚点、四相机和 Happy 表情
  -> 建立两个连通兼容域、原子边和精确 4,000 条双策略链
  -> 本地完整链 smoke
  -> 服务器 10 节点基准
  -> 渲染完整 640 唯一节点池
  -> 回填媒体并封装 4,000 条链
```

该旁路使用 F02/M02、Face V3、烘焙服装 Look 和直接 Morph 面部层。它不会等待 RM-06..RM-10 的全部长期能力。

## 2. Sprint 之后的顺序

```text
RM-08R 服装剩余兼容与十体型
  -> RM-09R 动画池扩展与道具
  -> RM-06 Headshot 身份迁移与年龄
  -> RM-07 三发型与完整外观变体
  -> RM-10 UE 统一角色接口
  -> RM-11 完整端到端验收
  -> RM-12 生产收口
```

编号沿用既有工作包，`R` 表示只保留尚未完成的 remainder。

## 3. RM-08R：服装剩余项

**目标**：在不破坏已接受的 41 family / 53 逻辑组规则前提下，补齐当前 Sprint 未覆盖的服装能力。

- 解决或登记头发与头巾、兜帽、高领冲突。
- 把获准 Look 扩展到所需十体型，而不是只依赖 F02/M02。
- 为 `BodyFit × Look` 建立稳定 UE 资产和兼容记录。
- 至少验证两套 Look 的 UE 切换；禁止未登记的任意 Shirts/Coats 组合。

**退出条件**：十体型目标集合、头部服装策略和 UE 资产映射均有机器与视觉证据。

## 4. RM-09R：动画池与道具

**目标**：从已审查 P0 候选建立正式动画池，并处理明确的道具依赖。

- 吸收本 Sprint 通过的 10 个生产动作（每性别 5 个）和三条渲染表情；表情暂不作为编辑轴。
- 完成 69 条剩余候选的用户决定导入，按需扩充 P0。
- 建立单手杯子和双手箱子两个最小道具档案。
- 登记 Root Motion、循环、face policy、Socket、Attach/Detach、手型和 IK。

**退出条件**：正式动画 ID 可由配置稳定调用；两个道具案例可复现且无抓空气。

## 5. RM-06：Headshot 身份与年龄

**启动条件**：第一批数据完成，且不再受本周交付约束。

- 完成 10 个 Headshot 候选的视觉状态和质量比较。
- 决定是否扩充原型，再用小规模确定性配方评估多样性。
- 只有通过 Blink、Look、Smile、Jaw Open 和装配门禁的完整身份才能进入生产。
- 年龄先作为身份允许的可选变体；身体老化另做服装影响研究。

**退出条件**：新方案明确优于 Face V3，或以证据决定继续使用 Face V3。不得默认混合两个池。

## 6. RM-07：三发型与完整外观

- 每个生产身份准备 3 套已适配发型。
- 男性至少支持 `beard none/fitted_default`。
- 头发、眉毛和胡须共享色素档案。
- 保存稳定 asset ID、规范 CC 项目和动态视觉证据。

**退出条件**：代表男女身份的三发型和胡须开关通过，外观可确定性重建。

## 7. RM-10：UE 统一角色接口

从当前 M02 Pilot 和第一批 FullReference 配置抽象稳定接口，至少覆盖身份、发型、色素、胡须、服装 Look、身体动作、面部 clip、年龄和道具。Vendor 资产保持不动，DataMake 只保存自有蓝图、Data Asset 和配置。

**退出条件**：代表男女角色可只靠配置 ID 重建，重开项目结果一致。

## 8. RM-11：完整端到端验收

在十体型、三发型、至少两套 Look、身体/面部动作和代表道具上建立小规模覆盖，不做全笛卡尔积；完成场景、相机、Sequence、渲染、GT、sidecar 和双向追溯。

**退出条件**：从空闲 CC 到 UE 数据包可以按现行 Workflow 干净复跑。

## 9. RM-12：生产收口

- 晋升通过的 manifest/compiler/runtime 为默认入口。
- 清理被正式结果替代的临时探针、重复输出和旧兼容入口。
- 同步 Master、Workflow、Validation、Current Status、Implementation Index 和必要 ADR。
- 完成一次生产级回归和恢复演练。

**退出条件**：新对话从 Master 和 Current Status 即可定位唯一活动工作，不需阅读历史计划。

## 10. 跨阶段停止条件

- 输入/输出/资产 ID、哈希或版本无法追溯。
- 眼球、眼睑、牙齿、口腔、Skeleton、拓扑或服装兼容发生漂移。
- 只有 API 成功，没有机器结构验证与人工视觉证据。
- CC 未知模态弹窗、资源超限或服务器无法稳定复现。
