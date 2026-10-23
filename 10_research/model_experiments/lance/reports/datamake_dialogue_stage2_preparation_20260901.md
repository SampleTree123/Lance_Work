# DataMake dialogue 第二阶段训练准备与 smoke

> 日期：2026-09-01  
> 状态：`local_smoke_passed_formal_job_queued`  
> 范围：第一批 released `dialogue` 的第二阶段全参数续训准备；不包含视觉质量通过结论

这是2026-09-01的历史准备记录，不是当前排队状态。训练已完成，结果见[Stage2报告](./datamake_dialogue_stage2_results_20260903.md)。原Stage1初始化权重与smoke Run已退役；当前仅保留Stage2 base-only模型供新LoRA使用。

## 决策

用户因时间限制决定跳过 100～300 step A/B 短训。第二阶段先执行 2-step 技术 smoke；若 forward、weighted MSE、backward、optimizer、梯度和日志均正常，则使用同一配置直接训练一个完整 Epoch。该路径只能评价“R5 增采样＋条件 dropout 关闭＋区域加权”的组合效果，不能把最终收益单独归因到其中一个改动。

## 数据

- 来源 split 保持 seed `2026` 的 3,600/200/200 chains，validation/test 不变。
- train 原有 13,483 个唯一前缀全部保留。
- Round 1～4 各出现 1 次；Round 5 的 596 条各出现 3 次，共 1,788 个训练实例。
- 有效 train 为 14,675 行；global batch 4 时一个 Epoch 为 3,669 steps，仅同步补齐 1 条。
- 新 train 使用 8 个 Parquet shard，`data_seed=2081` 给 4 ranks × 2 workers 分配 `[3669, 3668, 3669, 3669]` 行，不遗漏有效实例。
- 媒体继续引用 released 包，没有复制 MP4。第二次在 `/tmp` 独立重建后，8 个 Parquet 的逐文件 SHA-256 与正式输出完全一致。

冻结入口：

- `outputs/training_data/datamake_dialogue_first_batch_v002_stage2_r5x3_seed2041_sharded8_20260901/sampling_manifest.json`
- `configs/datamake_dialogue_stage2_r5x3_region_v1.json`

## 区域加权

patch `0009` 给 DataMake 唯一 direct-source VAE latent 和 target VAE latent 标记明确角色。训练时以冻结 VAE 的绝对 latent 差异构造 soft importance：50%/90% 分位数映射到 `[0,1]`，原始 token 权重为 `1 + importance`，即相对范围约为 1～2；最终 MSE 除以四卡全局权重总和，保持整体 loss 尺度稳定。完全相同的 latent 自动退化为普通均匀 MSE。

该分支由 `edit_region_weighting` 显式控制，只改变训练损失。推理没有 target 视频，也不执行权重构造。W&B/本地日志新增 `mse_unweighted`、`edit_region_weight_mean` 和 `edit_region_weight_max`，原 `mse` 表示实际参与反向传播的加权 MSE。

## 第二阶段配置

- 起点：正式第一阶段 `checkpoints/0003371`，新 optimizer/scheduler horizon。
- Lance core 全参数；embed、ViT、VAE 冻结；无 LoRA、无 EMA。
- LR `1e-5`，101-step warmup，半周期 cosine 单向降到 `1e-6`。
- text/ViT/VAE condition dropout 均为 0。
- 每 600 completed steps 保存，只保留第二阶段最近 1 个完整 checkpoint，正常结束额外保存 step3669。
- W&B online Run ID：`datamake-dialogue-stage2-r5x3-region-v1`。

## 存储清理

准备阶段曾保留Stage1最终权重作为初始化；该权重及tiny/Stage1结果现已删除。当前保留范围见[2026-09-06清理记录](./datamake_lance_storage_cleanup_20260906.md)，不能使用本历史配方直接恢复全参训练。

## 验证状态

- 完整 44 项 Lance unittest 已通过，覆盖 R5 重采样、source/target role、soft region weights、全局权重归一化、正式/smoke profile、断点恢复和 W&B 契约。
- Round-5 真实媒体 CPU pack 为 62,496 tokens，包含 5 个 ViT history condition、1 个 clean VAE source 和 1 个 VAE target，低于 65,536 上限且 source-target 对齐。
- stage2 正式/2-step smoke profile dry-run、Shell 语法、Python compile 和 patch `0004..0009` 重放后文件哈希一致性通过。
- 文档维护重建后为 114 份可达文档、5 个 Output Scope、404 个脚本和 651 条本地链接，独立子系统与跨层检查零错误/零警告；138 项核心 pytest 通过。
- `sbatch --test-only` 接受 4×H200 smoke 资源请求；真实 Job `120397` 未启动即由用户取消。

## 本地单 H200 smoke

用户随后批准使用现有交互 allocation `120417` 的单张 H200 快速执行同一 2-step Gate，并同步把正式任务加入队列。独立入口 `scripts/run_datamake_stage2_local_smoke.py` 先完整校验冻结四卡 profile，再只把技术 smoke 的 world size/FSDP mesh 改为 1；数据、step3371 权重、可训练参数、optimizer、dropout、区域 loss 与 token 上限不变。W&B 使用 offline，`save_every=0` 且不保存最终 checkpoint。

| Step | weighted MSE | unweighted MSE | region mean/max | total norm | step time |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0.0567 | 0.0386 | 1.1769 / 2.0000 | 0.07524 | 277.49 s |
| 2 | 0.0988 | 0.0947 | 1.2694 / 2.0000 | 0.12319 | 11.10 s |

step1 包含单卡 TorchInductor 首次编译和视频预取，step2 才接近本次 smoke 的稳态计算时间。两步均完成 forward、weighted loss、backward、梯度裁剪和 AdamW update；进程正常 return code 0，无 OOM、NaN、Traceback 或数据错误。W&B offline summary 的最终 allocated/cached 显存约为 119,799/128,982 MiB。单卡将 `HYBRID_SHARD` 自动退化为 `NO_SHARD` 是 PyTorch 的预期行为；四卡全局权重归一化另由 unittest 覆盖，且第一阶段已验证四卡 FSDP 路径。

证据：

- `outputs/slurm_logs/dm_lance_s2_local_smoke_120417.out`
- `outputs/slurm_logs/dm_lance_s2_local_smoke_120417.err`
- `outputs/training_runs/datamake_dialogue_stage2_r5x3_region_fullparam_4xh200_v1_local1xh200_smoke2_job120417/`

技术 smoke 结论为 `passed`，只证明新训练路径可执行，不证明区域加权或 R5 增采样会改善最终视觉质量。正式 4×H200 Job `120425` 已提交到 `testqueue`，当前等待资源；启动后继续以 W&B online、四卡首步和 steady-state 指标作为运行 Gate。
