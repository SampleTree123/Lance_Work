# 历史训练启动器

2026-10-22归档。旧全参、Stage5在线rollout与Stage6 FSDP启动代码仅供追溯，不支持在当前源码上执行；归档入口已显式拒绝启动。迁移前原文另保存在可校验源码归档中。

当前 GT/整链训练分别使用上一级的 `run_datamake_ddp_training.py` 和 `run_datamake_chain_pred_x0_ddp_training.py`。公共路径、环境和模型参数映射已经抽取到 `datamake_runtime.py`，现行入口不再导入历史训练器。

所有者：[训练接入](../../training_integration.md)；证据：[迁移报告](../../reports/datamake_source_migration_20261022.md)。
