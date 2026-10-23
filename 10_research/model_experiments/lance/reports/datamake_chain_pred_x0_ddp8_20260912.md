# 整链顺序 pred_x0 复用：实现与验证（2026-09-12）

用户要求暂停旧 pred_x0 实验，并把同一条链集中处理，让当前监督 forward 同时提供下一轮历史。新版本已实现，单 H200 和双进程 Gloo 检查通过；尚未提交新正式八卡训练。本文由 [训练接入](../training_integration.md) 拥有。下述数字只描述本次实验范围。

## 暂停与恢复边界

旧 pred_x0 作业 **133605** 通过 `SAVE_AND_STOP` 在 optimizer 边界保存完整 **0000077**，2026-09-12 10:06:52 以 `COMPLETED/0:0` 退出。原 v1 启动器的 `latest` 恢复 dry-run 通过，`next_step=77`，原合同继续有效。GT 对照 **133604** 未修改，10:36 左右仍为 RUNNING。旧配置和源码保留，下面的 v2 使用独立 run/W&B 身份。

新 v2 默认从同一官方 Lance 基座、新 LoRA/optimizer 开始。整链改变采样次序、梯度归约分组和数据游标，**不能把 v1 的77步直接作为 v2 的完整状态恢复点**。v2 自身后续恢复使用 optimizer-window 游标。没有迁移或删除旧检查点，没有自动提交新训练。

## 实现与数据

- [新启动器](../scripts/run_datamake_chain_pred_x0_ddp_training.py) 复用原启动锁、检查点验证和八卡连续3步对比2步＋恢复1步的 Gate；新合同绑定28个源码文件与确定性调度 SHA。
- [训练器](../lance/train/datamake_chain_pred_x0_ddp_train.py)、[整链调度](../lance/train/datamake_chain_window_schedule.py)、[CPU媒体缓存与打包](../lance/train/datamake_chain_window_data.py) 通过 [0025补丁](../patches/legacy/0025-whole-chain-pred-x0-ddp.patch) 持久保存；原 GT/v1 实现不改。
- 一条链依次执行 R1→R2→…；每轮带梯度 forward 计算当前 GT 目标的官方 flow MSE，同时取出 pred_x0，在 no_grad 下 detach/VAE decode，成为下一轮所有相应 ViT 历史及最新 VAE source。当前轮 backward 后再解码，避免保留整链计算图。下一轮只训练自身，**不跨轮反传**。
- 每条链在同一次 optimizer 更新内完成，链内权重不变；历史只在当前链内缓存，不跨更新复用。CoinVE 单轮继续原共同绝对时间窗口采样，无历史生成；原视频仍按索引引用，没有复制视频数据。
- 7201条链、18276个加权训练目标不变：UE 14675、CoinVE 3601。五轮链仍做 `[R1,R2,R3,R4,R5,R5,R5]`，R5三次使用同一份前四轮历史、分别采样训练噪声；不是把一份loss乘3。
- 每次更新全局仍是32个目标；整链分配到8个rank，每rank数量可不同。配置里的累计4表示平均32/8，并非每rank固定4条链。按计算量分配链，只有最后一个本地目标同步DDP梯度，其余使用no_sync。每个数据epoch完整保留每个sampling instance；窗口可以跨epoch边界，无丢弃。
- **归约明确变化**：旧实现对每个8-rank microstep的token均值再平均4次；新实现按整个32目标window的全局目标token数归一化，防止rank拿到不同数量目标时被等权误加权。底层逐token官方MSE不变，但不能声称两种分组的数值梯度完全相同。

## 权重判断

本版额外轮次权重均为1，保留已有R5×3。后段损失增权可能让模型更重视从受损条件恢复当前输出，但不会通过已detach的历史直接约束前一轮生成；共享参数更新可能间接改善以后所有轮次。更大的权重也可能放大条件与GT不一致的监督噪声，不能保证更好的编辑。

pred_x0来自当前GT加噪后的单步预测，后轮质量并非必然随轮数单调降低，也不等价于30步真实自回填。先记录分轮MSE/目标数量，并用held-out真实多步自回填评估判断是否需要增权；不同轮次原始loss还受噪声时刻和内容难度影响。若后续另做消融，可尝试按链内相对位置缓慢增至末轮1.25–1.5，并归一化控制整体尺度和UE/CoinVE比例；这是待验证建议，本版没有启用。

相关背景仅作问题类比：训练与自身输出分布偏移见 [Ross等，2011](https://www.cs.cmu.edu/afs/.cs.cmu.edu/Web/People/sross1/publications/Ross-AIStats11-NoRegret.pdf)；这些结果不证明Lance后轮加权或pred_x0与多步采样等价。

## 验证与性能边界

[机器摘要](./datamake_chain_pred_x0_ddp8_20260912.json) 与 [诊断目录](../outputs/optimization_diagnostics/chain_pred_x0_ddp8_20260912/) 保存证据。

- Lance **153项**单元测试通过，涵盖3000个窗口的固定32目标、8rank非空、完整epoch覆盖、确定性恢复切片、R5独立曝光、detach及原源码合同保留。
- 真实媒体CPU检查：CoinVE单轮及UE三/四/五轮，当前GT tensor与原预处理逐元素一致，token计数分别为13728、38610、51480、90090；五轮7目标只需4份历史，R5训练时刻各不相同。
- 双进程CPU/Gloo：每rank分别7与1个目标，3次更新，对应detached-history全局token均值参考的梯度最大差 **0.0**。这验证不等长本地循环的同步与缩放，不等于八卡NCCL实测。
- 现有交互allocation **133654** 单H200，原生训练入口2次更新，4轮与5轮链共 **11次监督forward、11个训练目标、7次历史解码、0次额外历史model forward**；历史detach、VAE decode no_grad、双分支真实更新、冻结基座哈希不变、当前GT预处理一致全部通过。
- 单卡峰值 allocated **117.9474 GiB**；第一步4目标188.218秒（含首次编译/审计），第二步7目标117.854秒；全进程409.599秒，退出0，测试后显存0MiB。这些步骤目标不同且含诊断开销，**不作为八卡速度对比或epoch耗时估计**。没有声称所有长链组合均已GPU覆盖。
- 一个完整数据pass从旧版额外24213次历史模型forward减至0；18276次监督forward保留。历史解码次数由24213降至9883。该计数解释预期收益，但无法线性换算总用时，解码/ViT与VAE重编码、DDP负载不均仍存在。
- 最终配置fresh dry-run通过：next_step=0、gate_required=true；Slurm shell语法检查、补丁重放通过。核心文档/数据/Unreal共132项测试通过，目录/输出清单重建后文档独立及跨层审计通过（114文档、686链接、零错误/警告）。这些是工程与文档证据，不替代GPU恢复或质量验收。
- 完整八卡NCCL和真实模型连续/恢复Gate尚待用户提交后执行；当前短测未写新正式checkpoint，也未验收长期收敛或视频质量，L06/L08保持未关闭。

## 启动

[配置](../configs/datamake_coinve_mixed_ddp8_lora64_both_chain_pred_x0_no_region_v2.json) 与 [Slurm入口](../jobs/datamake_coinve_mixed_ddp8_lora64_both_chain_pred_x0_no_region_v2.sbatch) 保持8H200、双分支r64、global32、3000步、相同学习率、off10/retain/minimal padding、关闭区域loss加权、每50步保存最近4份。正式训练先执行完整八卡Gate。

在 DataMake 根目录运行：

```bash
RESUME_FROM=none DDP_MODE=train sbatch \
  10_research/model_experiments/lance/jobs/datamake_coinve_mixed_ddp8_lora64_both_chain_pred_x0_no_region_v2.sbatch
```

## 生命周期与输出所有权

新launcher、训练器与数据/调度helper是本下游实验的active代码，Technical owner为training_integration.md。新测试为validation用途；诊断目录内run.py/probe.py/cpu_pack_probe.py为本次已完成的有限测试，不是生产入口。该目录及未来v2 training_runs均沿用现有Lance输出类别；当前诊断保留用于复核，无自动清理授权。补丁已在空目录重放并逐文件字节一致校验。
