# Lance 当前源码补丁

2026-10-22：当前基线为官方 `4baeee086648996f6ab12e673cbe461b0b149997`。

## 当前唯一安装来源

- [current/source_lock.json](current/source_lock.json)：官方提交和源码哈希。
- [current/datamake.patch](current/datamake.patch)：必要DataMake改动的一份完整补丁。
- [重建/校验工具](../scripts/rebuild_lance_checkout.py)：默认拒绝覆盖已有目录，支持 `--verify-only` 与 `--official-only`。
- [迁移说明与验证](../reports/datamake_source_migration_20261022.md)：保留/退役清单、GPU对照、归档和恢复边界。

从DataMake根目录核验当前目录：

```bash
python 10_research/model_experiments/lance/scripts/rebuild_lance_checkout.py --verify-only
```

重建到尚不存在的临时目录用于比对：

```bash
python 10_research/model_experiments/lance/scripts/rebuild_lance_checkout.py --destination /tmp/lance_rebuild_example
```

临时目录只用于源码校验，不自动改变现有训练入口；完整DataMake训练仍使用外层工作区下的 `lance/` 与配套scripts/configs。

## 历史补丁

[legacy/](legacy/)保存0001–0026的原始阶段补丁，只用于追溯。不要依次应用它们来构建当前代码，也不要在当前补丁之后追加历史补丁。原阶段重放证据按其日期与基线解释。

以后修改忽略目录中的实现时，需要同步当前补丁/源码锁并验证干净重建。模型权重、媒体、checkpoint不得进入补丁或外层Git。
