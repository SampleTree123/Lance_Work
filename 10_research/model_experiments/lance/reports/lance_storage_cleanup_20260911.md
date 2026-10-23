# Lance 历史验证与迁移产物清理

> 日期：2026-09-11。范围：用户明确要求释放 Lance 目录磁盘空间；不修改训练代码、配置、数据集或当前训练状态。输出所有者：[训练接入](../training_integration.md)。

已删除 72 个大文件，释放 44.507 GiB。逐文件路径、大小、删除前 inode/mtime、分类、替代依据和完成结果见[清理清单](./lance_storage_cleanup_20260911.json)。

- 四组旧 Stage6 FSDP 启动验证：仅移除 adapter 和分布式 optimizer 大文件，保留 passed Gate、日志、trace、配置及小型状态文件。这些旧验证均已通过，现有 DDP 的完整验证产物仍保留。
- padding 迁移中间版本：仅移除 `checkpoint_migrations/padding_20260910`、`padding_ddp_20260910` 以及诊断目录 `padding_20260910/migrated_both`、`migrated_gen` 下的大型 adapter/optimizer。最终 `padding_final_20260910` 替代关系已由[原优化报告](./datamake_padding_optimization_20260910.md)明确记录。

清理目录增加 `CLEANUP_20260911.json` 标记。其中旧 checkpoint manifest 仅作为历史证据保留，目录已不是可加载的完整 checkpoint；重新做这些旧验证的逐张量比较需要重跑。历史 passed 记录不等于原始张量仍在磁盘。

保留全部正式训练 checkpoint，包括原 FSDP 900/825 与优化后 DDP 987/893；保留最新两组 DDP 启动验证全部原始产物、最终迁移 900/825、官方模型与 Stage2 基座、所有训练数据和实验日志。未删除 profiler 原始事件。

删除前对 987/893 和最终迁移 900/825 的所有 manifest artifact 校验大小与 SHA256，通过；原 FSDP 900/825 校验所需文件大小和 optimizer 分片数量，通过。删除后确认其余 1,765 个既有输出文件大小、mtime 与 inode 均未改变。没有启动或恢复训练。
