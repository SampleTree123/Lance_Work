# Stage6 暂停与新 LoRA 单卡速度短测

> 日期：2026-09-09，Asia/Singapore。Technical 所有者：[训练接入](../training_integration.md)。计划 L10；不替代四卡正确性、完整迁移恢复或视觉质量验收。
> 当前状态：两个原训练已保存退出；同卡速度短测完成，结果仅适用于本次单卡短样本。

## 原训练暂停结果

用户明确要求暂停 Job126188、126189。20:29:44 在两臂各自 Run Root 写入 SAVE_AND_STOP，训练器完成当前 optimizer update、保存 adapter/Adam/scheduler/四rank RNG/consumed cursor 后退出。Slurm 两个作业均为 COMPLETED，ExitCode=0:0；不是强制取消或保留显存的 Slurm suspend。

| Job | 分支 | 最终完整步数 | next_microstep | 恢复目录 |
| --- | --- | --- | --- | --- |
| 126188 | 理解+生成 LoRA | 900 | 7200 | `outputs/training_runs/datamake_dialogue_stage2_recipe_lora_r64_both_branches_v1_4xh200_restart1/checkpoints/0000900` |
| 126189 | 仅生成 LoRA | 825 | 6600 | `outputs/training_runs/datamake_dialogue_stage2_recipe_lora_r64_freeze_und_v1_4xh200_restart1/checkpoints/0000825` |

两份新 checkpoint 的完成标记、必需文件/大小、四rank状态和 optimizer 边界游标通过现有 v5 validator；SAVE_AND_STOP 请求均已由训练器消费。此前文档中的“真实四卡请求保存退出未验证”在此次900/825实际退出范围内得到验证；这不构成新PEFT/DDP四卡验证。

本轮不自动恢复这两个作业。旧800仍是历史对照点，后续恢复应选择与任务相符的实际完整源。

## 短测范围

- 使用用户既有 allocation126170，H64Y574 单H200；启动前GPU仅1MiB、利用率0，无计算进程。
- 显式请求14个CPU；实际 affinity=14，step CPU cfs quota=-1（period100000）。此前单卡探针只有1CPU，本轮结果不能与其总时间直接归因比较。
- 固定both_branches配置、官方基座、全层非重入激活检查点、FP32 adapter/BF16基座计算、累计8、每卡batch1；每臂4个optimizer更新，首步单列，后3步作短样本均值。
- 在同一trainer诊断入口依次使用 `--probe-backend ddp`（官方PEFT）和 `--probe-backend fsdp`（旧BranchLoRA、FSDP NO_SHARD）。两者 fresh adapter，使用四rank既定数据安排的rank0索引；完成后核对逐更新 sample_ids 完全一致。
- world=1，没有四卡通信；FSDP参照仅复用旧冻结/flatten/混合精度路径，并非原四卡HYBRID_SHARD正式作业的完整复现。短样本、顺序运行、编译/cache因素限制外推，不宣布稳定四卡加速倍数。
- `--single-gpu-probe --smoke --stop-after 4`，不生成训练checkpoint，关闭W&B；墙钟包含启动，step_time为训练循环内计时，分别记录。

## 结果

同卡两臂各4更新均退出0，逐更新sample_ids、step和MSE token数一致；每臂处理32个目标视频。去掉首步后：新代码平均101.247秒/更新，旧FSDP平均104.707秒/更新，时间缩短3.30%（吞吐比1.0342×）。峰值allocated由80.992降至41.040GiB，减少49.33%。这次短测的主要改善是显存；速度只小幅提升，不能外推四卡通信收益。

| 指标 | 旧BranchLoRA/FSDP NO_SHARD | 新PEFT/DDP |
| --- | --- | --- |
| 首步后3步平均 | 104.707 秒/更新 | 101.247 秒/更新 |
| 首步后3步中位数 | 106.821 秒/更新 | 103.393 秒/更新 |
| 峰值allocated（4步） | 80.992 GiB | 41.040 GiB |
| 峰值reserved（4步） | 96.244 GiB | 42.750 GiB |
| 总墙钟（含初始化/退出） | 531.437 秒 | 556.671 秒 |

每个更新累计8个目标视频；不是单视频耗时。完整逐步计时：

| 更新 | 旧FSDP（秒） | 新PEFT/DDP（秒） |
| --- | --- | --- |
| 1 | 133.555 | 131.060 |
| 2 | 106.821 | 103.393 |
| 3 | 96.684 | 92.937 |
| 4 | 110.615 | 107.412 |

去首步后的阶段均值（ViT包含在forward中，不能再相加）：

| 阶段 | 旧FSDP（秒） | 新PEFT/DDP（秒） |
| --- | --- | --- |
| 数据等待 | 0.0012 | 0.0013 |
| VAE/区域权重 | 5.6740 | 4.8426 |
| 模型forward | 40.8715 | 41.2511 |
| backward/sync | 57.8661 | 54.9177 |
| 其中ViT | 4.4160 | 4.3352 |

速度比例使用训练循环内的step_time，不包括模型初始化、日志和保存；本次不写checkpoint。总墙钟单独列出，顺序运行的文件/编译缓存及初始化差异会影响它，不能把首步后均值的改善等同于本次整个进程墙钟改善。实际训练数学路径仍包括绝大多数前向、激活反传、attention和检查点重算，所以冻结基座梯度开销减少后未出现成倍加速。显存差包括取消FP32基座常驻、FSDP临时权重/梯度等，不能全部归因于一种buffer。

本轮只测双分支LoRA、单H200、4更新；没有测试仅生成臂，也没有完成新后端四卡恢复/通信性能验收。测试结束已释放GPU计算进程，交互allocation126170继续保留，两个原训练保持暂停。


## 证据与所有权

- [暂停状态](../outputs/optimization_diagnostics/pause_and_speed_20260909/pause_status.json)
- [同卡诊断配置与结果](../outputs/optimization_diagnostics/pause_and_speed_20260909/paired_speed/status.json)
- `outputs/optimization_diagnostics/pause_and_speed_20260909/paired_speed/`：两臂stdout/stderr、metrics、sample trace、配置与来源代码合同；属于现有下游诊断输出范围，默认保留，不作为训练恢复点。
- `outputs/optimization_diagnostics/pause_and_speed_20260909/run_short_speed.py`：本次执行脚本副本；单次诊断证据，不是生产训练入口。

## 算子级追加诊断

随后同日完成[固定真实R5样本的算子对照](./datamake_lora_operator_profile_20260909.md)，解释基座梯度修复为何未带来大幅提速；该单样本计算诊断不替换上面的32样本完整update结果。
