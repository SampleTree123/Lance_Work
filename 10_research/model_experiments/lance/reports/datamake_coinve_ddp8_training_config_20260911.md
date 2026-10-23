# UE＋CoinVE 八卡双分支 LoRA 配置

后续验证：[单H200混合短测](./datamake_coinve_single_gpu_validation_20260911.md)已通过，八卡GPU启动Gate尚未执行。下文未执行GPU指配置准备当时，不覆盖后续单卡结果。

> 日期：2026-09-11。所有者：[训练接入](../training_integration.md)。用户要求：8卡、LoRA、理解和生成双分支、每50步保存、关闭区域加强；随后确认仅保留最近4份。本次生成配置和验证，不提交作业。

## 可执行入口

- 主配置：[datamake_coinve_mixed_ddp8_lora64_both_no_region_v1.json](../configs/datamake_coinve_mixed_ddp8_lora64_both_no_region_v1.json)。
- 作业：[datamake_coinve_mixed_ddp8_lora64_both_no_region_v1.sbatch](../jobs/datamake_coinve_mixed_ddp8_lora64_both_no_region_v1.sbatch)。
- 配方合同参考：[recipe](../configs/datamake_coinve_mixed_ddp8_lora64_both_no_region_v1_recipe.json)。只供DDP语义比较，不可用旧FSDP入口提交。
- 数据：[混合数据组织与成对窗口](./datamake_coinve_mixed_dataset_20260911.md)。原Parquet、视频与裁剪窗口保持不变，增加八卡调度清单`sampling_ddp8_worker1.json`。

| 项目 | 本次配置 |
| --- | --- |
| 硬件/后端 | 单节点8×H200，官方PEFT0.15.2＋DDP |
| 初始化 | 官方Lance_3B_Video基座；新LoRA、新optimizer，不续用Stage5 B或已删Stage6 |
| LoRA | r64/alpha64，理解＋生成分支；基座、ViT、VAE、embedding冻结 |
| 区域加强 | `edit_region_weighting=false`，关闭差异区域loss加权；FlexAttention正常保留 |
| batch | 每卡1，梯度累计4，global batch32；不使用未验收batch>1路径 |
| 训练预算 | 沿用3000个optimizer step，即约96000条采样记录，约5.25次混合训练集大小 |
| 学习率 | 沿用3e-4峰值→3e-5最低，warmup101，cosine；未因卡数翻倍扩大LR |
| checkpoint | 每50次optimizer更新保存，最近4份完整状态，结束保存 |
| 计算优化 | BF16基座/FP32 adapter，末10层关闭检查点、其余保留；VAE缓存retain；末尾padding128对齐 |
| 数据 | 18276条训练记录；合成R5×3＋CoinVE一次，保持约80.3%/19.7%；CoinVE共同5秒窗口 |
| 数据读取 | 8个既有Parquet，8rank×1worker，每rank一个文件；prefetch2，seed2220 |
| 作业资源 | testqueue、18小时、112CPU、1024GiB主存；不使用/local |
| 日志身份 | 独立run和W&B ID，原配置未覆盖；不上传媒体或模型 |

“区域加强”在当前代码中对应`build_edit_region_mse_weights`生成的loss权重，不是单独的区域attention模块。配置关闭该计算，正常模型注意力与flow-matching损失保持。

硬件通过当日只读`sinfo -p testqueue -N`核验：分区存在单节点8张H200、128CPU的节点；当时为mix/alloc状态，不能据此承诺立即获得整机。

## 八卡运行适配

外层[DDP launcher](../scripts/run_datamake_ddp_training.py)现在按profile传递torchrun进程数、完整checkpoint world_size、各rank RNG文件名和连续/恢复trace检查范围。global batch合同检查为`GPU数×每卡batch×累计次数`，不再强制每rank累计8条。

`IndexedPrefixDataset`按实际worker数检查每rank分片数量，继续使用原索引/恢复算法。八卡首次各读取2285条，全局覆盖18276个不同sampling_instance，另有4条短分片循环重复（约0.022%）。没有复制原视频或重写训练Parquet。当前配置每rank一个CPU worker，整机仍为8个数据worker；后续若出现解码瓶颈可另行评估16分片/每rank两worker。

上游改动由[patch0023](../patches/legacy/0023-configure-ddp-world-and-worker-count.patch)保存；outer launcher由DataMake直接追踪。四卡模板继续使用2worker/rank、累计8/global32。Stage5 B的22份冻结实现文件保持一致。

## 启动命令

只执行GPU启动验证（job默认行为）：

```bash
sbatch 10_research/model_experiments/lance/jobs/datamake_coinve_mixed_ddp8_lora64_both_no_region_v1.sbatch
```

执行验证，通过后自动进入正式训练：

```bash
DDP_MODE=train sbatch 10_research/model_experiments/lance/jobs/datamake_coinve_mixed_ddp8_lora64_both_no_region_v1.sbatch
```

从本次新实验最近完整checkpoint恢复：

```bash
RESUME_FROM=latest DDP_MODE=train sbatch 10_research/model_experiments/lance/jobs/datamake_coinve_mixed_ddp8_lora64_both_no_region_v1.sbatch
```

新训练默认为`RESUME_FROM=none`。GPU Gate执行八rank连续3步与2步＋恢复1步，对比adapter、Adam、scheduler、RNG、游标与trace；未通过时不进入正式训练。八卡不能直接沿用四卡的checkpoint RNG/游标和验收结果。

## 验证边界

当前133项Lance CPU回归通过，包含实际八rank分片覆盖、解析后区域加权开关为false、八进程torchrun参数、rank7 RNG/trace纳入Gate且能检出rank7差异。启动器真实dry-run和job Bash语法检查通过；Stage5 B22份冻结哈希一致。额外八进程CPU/Gloo实测3次更新、累计4、区域加权关闭，与显式全局参考的最大梯度差2.98e-8，模型更新及基座冻结检查通过。该结果记录在[验证证据](./datamake_coinve_ddp8_validation_20260911.json)。

这些检查不代替八卡GPU loss/backward、显存或NCCL启动/恢复验证。未提交作业，未产生新训练checkpoint，未给出八卡实际速度结论。L06/L08质量验收及WF90 released边界保持原状。
