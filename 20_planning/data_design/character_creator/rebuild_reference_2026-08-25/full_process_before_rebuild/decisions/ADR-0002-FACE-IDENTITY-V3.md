# ADR-0002：面部身份使用完整 Seed、Facial Profile 与安全局部 Morph

> 状态：Accepted
> 文档角色：`architecture_decision`
> 适用阶段：`WF-01..WF-03`
> 权威范围：Face V3 身份原子与局部 Morph 决定
> 上级入口：[`README.md`](./README.md)
> 上游：面部动态验证证据
> 下游：面部规范与角色 Workflow
> 最近核验：2026-08-06
> 日期：2026-07-29

## 背景

仅混合若干面部 Morph 并把其他参数清零会丢失眼骨、眼球、口腔和 Facial Profile 支撑，导致闭眼穿模、眼球偏移和牙齿穿唇。

## 决定

每张脸先加载一个同性交付的完整主 seed 和其 Facial Profile，再只修改配方列出的安全局部 Morph；最后应用 BodyFit 的 Head Scale/Neck Height。未知参数保持 seed 原值。

## 影响

- 眼口支撑保持完整，动态稳定性提高。
- 多样性来自更多高质量 seed 和有限安全局部变化，不来自无限清零混合。
- 当前 20 seed 中 17 个可作生产主原型；F09 和中性技术 seed 不进入主池。
- Headshot 新原型必须保存完整身份原子，而不是只保存 Morph 数值。
