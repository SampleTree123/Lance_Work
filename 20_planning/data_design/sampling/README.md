# sampling —— 配置图采样与多轮链

> ↑ 父层：[`../README.md`](../README.md)（数据设计）。

## 📂 内容说明

本目录定义配置图采样、随机游走、多轮链抽取和环一致性：

- [`MULTI_ROUND_CHAIN_SAMPLING_V1.md`](./MULTI_ROUND_CHAIN_SAMPLING_V1.md)：第一批 3–5 轮链的原子边、回退、闭环、覆盖与去重规则。
- 核心端点复用原则见 [`../README.md`](../README.md)。

## Agent 备忘

- 多轮链长和比例属于训练侧采样，但数据侧必须保证端点复用。
- 第一批实现通过后，再把实际采样器、验证报告和跨来源扩展登记到本目录。
