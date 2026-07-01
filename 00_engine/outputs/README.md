# outputs —— 引擎验证输出

> 父层：[`../README.md`](../README.md)。

本目录用于放 UE smoke test、MVP 小规模渲染、GT passes、sidecar 和对齐检查结果。实际输出由 `.gitignore` 排除。

当前建议：

```text
00_engine/outputs/mvp/
```

输出只用于阶段验证；稳定结论、失败模式和关键指标要回写到对应文档，不依赖输出目录长期保存。
