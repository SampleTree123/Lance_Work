# 20_planning —— 讨论与实施计划

> 父层：[`../README.md`](../README.md)。

本目录放稳定设计、实施约束、合规和讨论记录。它回答“为什么这样做、按什么规则做、有哪些风险”，不放大文件和运行产物。

## 目录说明

| 路径 | 内容 |
|------|------|
| `data_design/` | 配置图、edit taxonomy、schema、采样、多来源定位 |
| `implementation/` | 存储、服务器环境、部署前检查、风险登记 |
| `compliance/` | 许可证、资产台账规范、发布前检查 |
| `discussions/` | 讨论过程、会议记录、历史背景 |

## 维护规则

- 稳定决策要写入对应正式文档，并同步顶层 [`README.md`](../README.md) 的决策日志。
- 讨论文件只记录过程，不作为唯一执行入口。
- 外部事实必须带日期；执行前重新核实。

## Agent 备忘

- 数据设计的核心约束在 [`data_design/README.md`](./data_design/README.md)。
- 存储和路径权威约定在 [`implementation/storage.md`](./implementation/storage.md)。
- 合规台账模板在 [`compliance/licensing_compliance.md`](./compliance/licensing_compliance.md)。
