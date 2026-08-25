# ADR-0001：BodyFit 使用 Hash 锁定源项目

> 状态：Accepted
> 文档角色：`architecture_decision`
> 适用阶段：`WF-01..WF-03`
> 权威范围：BodyFit 源项目与哈希决定
> 上级入口：[`README.md`](./README.md)
> 上游：BodyFit 验证证据
> 下游：CC BodyFit 规范与角色 Workflow
> 最近核验：2026-08-06
> 日期：2026-07-24

## 背景

少量宏 Morph 可以近似身材，但不能保证胸腔、腹部、肩部、四肢和 Junction 的全部细节与人工确认结果一致。插件变化还会增加 Morph 槽位。

## 决定

10 个成人 BodyFit 以 `.ccProject` 为身份源，登记绝对路径、文件大小、SHA-256、Body/Junction 指纹、Head Scale 和 Neck Height。运行时先加载源项目，再替换面部和外观。

## 影响

- 可以精确复原人工验收体型。
- 项目文件较大，但数量固定且可管理。
- Morph 指纹用于漂移审计，不作为默认重建方式。
- 修改 BodyFit 必须产生新哈希并重新验证服装和高度。
