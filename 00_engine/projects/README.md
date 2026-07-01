# projects —— UE 工程入口

> 父层：[`../README.md`](../README.md)。

本目录用于放 MVP 和后续 UE 工程。当前计划的第一个工程位置：

```text
00_engine/projects/MVPProject/
```

## Git 策略

- `Saved/`、`Intermediate/`、`DerivedDataCache/`、`Binaries/`、`.sln` 等生成内容不进 Git。
- 稳定后只提交必要源码、配置、Python 脚本、少量文本资产清单和说明。
- 大型 `.uasset` / `.umap` 是否进 Git 需要另行决定；正式 UE 工程更适合 Perforce 或专门的大文件方案。
