# 02_research —— 论文 / 外部项目 / 方法调研（Level 1）

> ↑ 父层：[`../README.md`](../README.md)（项目总览）。
> 本层放会影响数据方案和实验选择的外部资料：论文、开源模型、Unreal 自动化 harness、agent/MCP 工具等。

---

## 📂 内容说明

| 文件 | 内容 | 状态 |
|------|------|------|
| `README.md` | 本层索引和维护规则 | ✅ |
| `papers/lance.md` | Lance 项目与论文阅读笔记；已形成模型验证建议 | ✅ 初读 |
| `papers/bagel.md` | BAGEL 项目、论文、模型入口登记；暂未深读 | ✅ 已登记 |
| `tools/unreal_harness_survey.md` | UE automation / MCP / harness 调研与采用建议 | ✅ 初查 |

## 维护规则

- 外部事实必须带日期和来源链接；模型版本、权重大小、许可证、硬件需求等执行前要复核。
- 研究笔记只记录对本项目有决策价值的信息，不做论文全文翻译。
- 一旦研究结论改变项目计划，要回写 `README.md` 决策日志、`HANDOFF.md` 和对应执行文档。
- 模型权重、论文 PDF、下载缓存和实验输出不放在本目录；按 [`../00_project/storage.md`](../00_project/storage.md) 放入忽略路径。

## Agent 备忘（02_research）

- Lance 是当前第一个外部模型验证对象，详见 [`../30_experiments/external_models/lance_validation_plan.md`](../30_experiments/external_models/lance_validation_plan.md)。
- BAGEL 先只登记，不要假设已经读完论文。
- UE harness 的当前结论：生产流水线优先用 UE 官方 Python + Automation Framework + MRQ/MRG 自建薄 harness；MCP/agent 工具只作为编辑器辅助或原型探索，不进入确定性批渲核心链路。
