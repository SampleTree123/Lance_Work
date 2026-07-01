# cache —— UE 缓存与临时目录

> 父层：[`../README.md`](../README.md)。

本目录用于放 UE DDC、shader cache 和临时文件。实际缓存内容由 `.gitignore` 排除。

推荐路径：

```bash
export UE_LocalDataCachePath="$DATAMAKE_ROOT/00_engine/cache/ddc"
export TMPDIR="$DATAMAKE_ROOT/00_engine/cache/tmp"
```

不要频繁删除 `ddc/`，否则网络盘上的 shader/DDC 重建会很慢。
