# DataMake Lance 训练文件清理（2026-09-04）

> 状态：`completed`  
> 范围：`10_research/model_experiments/lance/` 中被现行 v3/v5 正式路径取代的重型测试产物、失败入口和可重建缓存  
> 结论边界：只清理 Lance 下游研究区；未修改 released 数据、官方 Lance 基座、当前 v3 正式 Run、轻量审计证据或仍需执行的消融实现。

本报告仅记录2026-09-04当日状态。tiny/Stage1轻量日志、报告与视觉结果的保留决定已被[2026-09-06清理](./datamake_lance_storage_cleanup_20260906.md)替代；下文“当前”均指原执行日，不作为现存文件索引。

## 1. 清理结果

清理前 Lance `outputs/` 约 163 GiB，清理后约 31 GiB。按删除前逐目录字节数和第二阶段 optimizer 文件尺寸计算，释放至少 142,534,685,259 bytes（约 132.7 GiB），另清除了 216 个 `.pyc` 与对应 `__pycache__`。

当前 `training_runs/` 只保留三类运行外壳：

- 当前 Stage 5 正式 v3 Run，包含正在按最近四份策略滚动的 adapter-only checkpoint；
- 第二阶段 Job `120425` 的轻量配置、launch manifest 和 W&B 缓冲；
- 第一阶段 Job `119261` 的轻量配置、launch manifest 和 W&B 缓冲。

## 2. 已删除的重型输出

以下输出已被正式 v3 checkpoint、checkpoint-v5 audit JSON 和 Slurm 日志取代，不再保留二进制 smoke checkpoint/W&B Run Root：

- 失败的 Stage 4 v1 正式 Run `datamake_dialogue_online_rollout_lora_r64_4xh200_v1/`；
- 旧 v1 smoke `datamake_dialogue_online_rollout_lora_r64_4xh200_v1_smoke/`；
- v2 checkpoint 调试与恢复迭代：`smoke_continuous3`、`smoke_resume3`、`smoke_dcpcontinuous3`、`smoke_dcpresume3`、`smoke_emptyshardresume3`、`smoke_keepfieldcontinuous3/resume3`、`smoke_optmapcontinuous3/resume3`；
- v3 连续/恢复 smoke Run：`datamake_dialogue_one_step_x0_lora_r64_4xh200_v3_smoke_continuous3/` 与 `..._smoke_resume3/`；
- Stage 2 单卡 2-step smoke Run；
- 已被报告和六个轻量视觉结果取代的 tiny-overfit 训练 Run；
- 第一阶段全参 Run 的 `checkpoints/`。第一阶段训练日志、报告、W&B 缓冲、launch manifest 和既有视觉结果仍保留，但其 step3371 权重不再可从本地恢复。

Stage 4/5 smoke 的机器可读逐 tensor 结论继续由 `datamake_stage4_lora_resume_smoke_audit_20260904.json` 与 `datamake_stage5_one_step_x0_resume_smoke_audit_20260904.json` 保存；其中的源 checkpoint 路径现在是历史路径，不再表示文件仍在线。

## 3. 第二阶段基座整理

第二阶段 `0003669` 的四个 AdamW shard 合计 44,440,911,348 bytes；当前消融 `ABL-LORA-BASE-01/B` 只需冻结模型参数，不需要恢复旧 optimizer/scheduler。因而原完整 checkpoint 已降级为独立 base-only artifact：

```text
outputs/model_bases/datamake_dialogue_stage2_step3669/
  model.safetensors
  generation_config.json
  llm_config.json
  tokenizer*.json
  merges.txt
  vocab.json
  base_model_manifest.json
```

`model.safetensors` 为 28,422,373,304 bytes，SHA-256 为 `ae9c4aba917af7564403972976bc706a4c6455c169128f2794c12e3bef99075e`。该目录可以作为 fresh LoRA 的冻结基座，但不是可恢复第二阶段全参训练的 checkpoint。

## 4. 代码整理

删除了已知会启动无效 checkpoint-v4 路径的三个 v1 文件：

- `configs/datamake_dialogue_online_rollout_lora_r64_v1.json`
- `jobs/datamake_dialogue_online_rollout_lora_r64_v1.sbatch`
- `jobs/datamake_dialogue_online_rollout_lora_r64_v1_smoke.sbatch`

保留：

- 当前 v3 profile、正式/Smoke Slurm 入口、launcher、训练主循环和 checkpoint-v5；
- v2 full-rollout profile/Slurm，作为 `ABL-HISTORY-FAST-01/A` 的必要消融基线；
- Stage 3 teacher-forced/offline history 实现，因为 teacher-forced 仍是已登记的后续对照；
- Stage 1/2 profile、patch、报告和脚本，用于历史可追溯；
- 全部 17 个 Lance 回归测试。测试源码总计不到 0.5 MiB，仍覆盖现行数据、LoRA、FSDP checkpoint、profile 和日志契约，不属于可删除产物。

## 5. 运行安全检查

清理没有触碰 `datamake_dialogue_one_step_x0_lora_r64_4xh200_v3/`。清理后该 Run 保有 `0000050` 与 `0000100` 两个完整 checkpoint，日志继续越过 step110，因此当前四卡训练未受影响。

被删除的二进制文件未进入回收站，不能原地恢复；smoke 可由保留的 profile、代码和 Slurm 入口重跑。第一阶段权重及第二阶段 optimizer 状态只保留历史结论，不能再恢复训练；第二阶段模型权重仍以 base-only artifact 保留。

## 6. 清理后验证

- Lance：74/74 项 unittest 通过。两项历史 Stage 2 profile 测试改为使用临时占位模型目录检查冻结配方，不再错误要求已清理的 Stage 1 权重在线；这不会把历史 profile 重新标记为可执行。
- Character Factory：documentation 22/22、dataset 30/30、Unreal 80/80，共 132/132 项 unittest 通过。
- 文档：114/114 个文档可达、5 个输出范围、404 个脚本、661 个本地链接，零错误、零警告。
- 结构：`PROJECT_STATE.json`、Stage 3 review profile 与 base-only manifest 均通过 JSON 解析；脚本目录和输出清单已重建。
