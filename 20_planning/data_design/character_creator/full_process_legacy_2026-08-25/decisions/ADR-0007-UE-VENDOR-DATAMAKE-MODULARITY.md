# ADR-0007：UE 使用 Vendor/DataMake 分层与模块化角色

> 状态：Accepted
> 文档角色：`architecture_decision`
> 适用阶段：`WF-05,WF-06,WF-08`
> 权威范围：UE Vendor/DataMake 分层和模块角色决定
> 上级入口：[`README.md`](./README.md)
> 上游：M02 导入与模块 Pilot
> 下游：传输、UE 运行时和场景 Workflow
> 最近核验：2026-08-06
> 日期：2026-08-04

## 背景

外部 `.uasset` 内部引用依赖原路径，随意移动会破坏资产。项目又需要统一角色入口和可切换服装/毛发。

## 决定

外部资产保留在 `/Game/Vendor` 或原包路径，不原地编辑和移动；`/Game/DataMake` 保存关卡引用、角色 Blueprint、派生动画、配置和统一接口。模块化角色以 Body 为 Leader，其余 Skeletal Mesh Component 使用 Leader Pose 和曲线传播。

## 影响

- 导入资产与项目逻辑边界清晰。
- M02 Pilot 为 20 个组件、19 个 follower。
- DataMake 可以重建入口而不改 Vendor 源资产。
- 未来十体型应复用语义槽位，不依赖某个 Pilot 的具体网格块名。
