# Slurm任务入口

最近核验：2026-10-22。当前源码已迁移，见[迁移验证](../reports/datamake_source_migration_20261022.md)。本轮未提交正式作业。

## 当前入口

| 作业 | 用途 |
| --- | --- |
| [GT八卡](datamake_coinve_mixed_ddp8_lora64_both_no_region_v1.sbatch) | GT历史，PEFT/DDP，双分支r64，每50步保存/keep4 |
| [整链八卡](datamake_coinve_mixed_ddp8_lora64_both_chain_pred_x0_no_region_v2.sbatch) | 整链pred_x0复用，detached历史，固定32目标窗口 |
| [CFG四卡](datamake_cfg4_gt1650.sbatch) | 现有CFG推理消融入口，运行前核对具体快照与输出身份 |

两种训练默认 `DDP_MODE=validate`，正式训练需要 `DDP_MODE=train`，并先完成对应实现合同的多卡连续/恢复Gate。新源码的单卡/CPU验证不代替该Gate。既有run已经有训练记录，不应使用 `RESUME_FROM=none` 向同一目录开始新实验；旧checkpoint严格合同不兼容时不能直接改哈希跳过检查。

## 兼容与历史

旧前缀pred_x0八卡、四卡PEFT基线/性能模板保留作配方或消融参考，默认使用上述两个训练主入口。Stage2全参、Stage5与Stage6 FSDP作业属于退役历史，其Python入口已明确拒绝启动，不能照旧命令提交。

历史资源请求与作业状态只描述当时实验；实际提交前核对当前allocation和配置。模型、数据及输出路径未因源码迁移移动。
