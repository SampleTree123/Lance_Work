# 10_research —— 相关资料、调研与外部模型验证

> 父层：[`../README.md`](../README.md)。

本目录放会影响数据方案和实验选择的外部资料：学习笔记、论文阅读、开源模型、Unreal 自动化 harness、agent/MCP 工具，以及 Lance/BAGEL 等外部模型能力验证。

## 内容说明

| 文件/目录 | 内容 | 状态 |
|-----------|------|------|
| `README.md` | 本层索引和维护规则 | 当前 |
| `study/` | 学习计划、论文阅读、模型架构概念、代码走读和后续讨论沉淀 | 当前 |
| `tool_surveys/unreal_harness_survey.md` | UE automation / MCP / harness 调研与采用建议 | 2026-07-01 已复核 UE5.8 MCP |
| `model_experiments/` | Lance、BAGEL、后续开放模型的验证计划、协议、训练适配和结果摘要 | Lance 两阶段全参完成；单步 `pred_x0` 历史 LoRA 四卡 Gate 已通过 |

## 维护规则

- 外部事实必须带日期和来源链接；模型版本、权重大小、许可证、硬件需求等执行前要复核。
- 研究笔记只记录对本项目有决策价值的信息，不做论文全文翻译。
- 一旦研究结论改变项目计划，要回写顶层决策日志、`HANDOFF.md` 和对应执行文档。
- 模型权重、论文 PDF、下载缓存和实验输出不直接提交；按 [`../20_planning/implementation/storage.md`](../20_planning/implementation/storage.md) 放入忽略路径。

## Agent 备忘

- Lance 是当前第一个外部模型验证对象；权重、环境和 `video_edit` 测试脚本已可用，详见 [`model_experiments/lance/validation_plan.md`](./model_experiments/lance/validation_plan.md) 和 `model_experiments/lance/reports/video_edit_batch8_report.md`（历史文件已于2026-09-11清理）。
- DataMake 多轮链到 Lance 的训练适配、两阶段全参结果、Stage 4 一行一链 full-rollout r64 LoRA 和 Stage 5 单步 `pred_x0` 快速历史方案见 [`model_experiments/lance/training_integration.md`](./model_experiments/lance/training_integration.md)；Stage 5 连续/恢复四卡 Gate 已通过并测得 1.91× 提速，正式授权状态以项目 Status 为准。
- BAGEL 先只登记，不要假设已经读完论文。
- UE harness 的当前结论：生产流水线优先用 UE 官方 Python + Automation Framework + MRQ/MRG 自建薄 harness；UE5.8 官方 MCP 和第三方 MCP/agent 工具只作为编辑器辅助、资产/关卡检查或原型探索，不进入确定性批渲核心链路。
