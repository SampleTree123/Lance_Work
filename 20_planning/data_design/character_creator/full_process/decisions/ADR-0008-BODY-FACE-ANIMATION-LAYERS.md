# ADR-0008：身体与面部动画按通道和复用政策分层

> 状态：Accepted
> 文档角色：`architecture_decision`
> 适用阶段：`WF-07`
> 权威范围：身体/面部动画通道和复用政策决定
> 上级入口：[`README.md`](./README.md)
> 上游：M02 动画分层 Pilot
> 下游：动画与 Morph 规范和 Workflow
> 最近核验：2026-08-06
> 日期：2026-08-04

## 背景

CC 动画可能同时包含身体、头颈、面部骨骼和 Morph/Rig Logic 曲线。简单覆盖面部会丢失颈部动作；同时驱动眼骨和 eyeLook 曲线会冲突。

## 决定

动画登记 `facial_channels=none/curves/bones/hybrid` 和 `reuse_policy=replaceable/paired/locked`。可重组身体动画先生成 Body-only 派生版本；面部层从 `cc_base_facialbone` 叠加，排除 head/neck。眼球最终姿态由 Rig Logic 曲线负责。

## 影响

- 身体动作可与安全面部 clip 重组。
- 完整表演可以登记为 locked，保留原始配对。
- Jaw Open 需要曲线加下颌、牙齿和舌头支撑骨骼。
- 新动画必须先审计轨道，再进入组合矩阵。
