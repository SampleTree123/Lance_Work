# 仅保留 Stage5 B 训练结果的清理

> 日期：2026-09-11。状态：已完成。所有者：[训练接入](../training_integration.md)。用户明确要求：除 Stage5 B 外删除其他训练实验结果及 checkpoint，确认无 Stage5 B 依赖后删除 checkpoint_migrations，其他类别保留。

本次删除 `outputs/training_runs/` 中除 `datamake_dialogue_one_step_x0_lora_r64_4xh200_stage2base_v1` 外的八个既有运行目录，并删除整个 `outputs/checkpoint_migrations/`。移除 856 个文件，释放 61.266 GiB。逐文件清单、删除依据和执行结果见[机器记录](./lance_keep_stage5b_cleanup_20260911.json)。

**Stage5 A 和所有 Stage6 FSDP/DDP 恢复点均已删除，包括 800、900/825 和 987/893；历史报告中的恢复命令不再可用。** 本次明确取代[此前保留正式 checkpoint 的清理范围](./lance_storage_cleanup_20260911.md)。原通过的验证是历史事实，不代表已删除的原始状态仍可重新加载。

Stage5 B 整个训练目录保留，包括完整 200/250/300/350 checkpoint、训练配置和日志。四份 checkpoint 的必需文件大小及 optimizer 分片数量/非空检查通过；训练合同中的 Stage2 step3669 基座、chain manifest、dataset config 存在，Stage5 B JSON 无 checkpoint_migrations 引用。

`model_bases`、`training_data`、`optimization_diagnostics`、`multiturn_chat` 和 `slurm_logs` 全部保留，官方模型和训练代码/config 未改动。保留的推理页面及诊断报告可能引用历史已删除 checkpoint；这类引用仅作溯源，不是可用恢复入口。删除前后对比确认其余 958 个既有输出文件大小、mtime、inode 或符号链接目标均未改变。未启动、恢复或取消训练任务。
