# 30_experiments —— 实验与能力验证（Level 1）

> ↑ 父层：[`../README.md`](../README.md)（项目总览）。
> 本层放会影响数据方案的实验协议和结果记录。这里不是训练代码仓库。

---

## 📂 内容说明

| 子目录 | 内容 | 状态 |
|--------|------|------|
| `external_models/` | Lance、BAGEL、后续开放模型的能力验证 | Lance 待执行 |

## 边界

- 本层记录验证计划、实验协议、结果摘要和失败模式。
- 模型代码、权重和缓存放 `external/`，输出放 `outputs/`，都不进 Git。
- 实验结论如果影响数据构造，要回写 `01_data_design/`、`10_sources/` 或顶层决策日志。

## Agent 备忘（30_experiments）

- 当前优先实验是 Lance 的 `video_edit` 和多轮一致性验证。
- 实验目的不是刷 benchmark，而是找现有模型失败点，反推 DataMake 需要补什么数据。
