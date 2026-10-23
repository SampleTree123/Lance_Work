# UE＋CoinVE 单H200训练正确性验证

> 日期：2026-09-11。所有者：[训练接入](../training_integration.md)。用户要求先复核八卡配置并在当前单卡完成简单训练测试，之后由用户使用八卡。本次单卡验证通过，未提交八卡作业。

## 配置与输入复核

[八卡主配置](../configs/datamake_coinve_mixed_ddp8_lora64_both_no_region_v1.json)和配方参考一致：8卡DDP、r64双分支、全基座冻结、区域loss加权关闭、batch1/累计4/global32、3000步、50步保存/最近4份。正式profile和native trainer源文件在本次测试中未修改；run/configs/profile.json与原profile逐字段一致。Stage5 B全部22份冻结实现哈希不变。

数据配置、split/sampling清单及全部Parquet哈希/行数复核通过；8640个媒体引用仍存在且非空。训练/验证/测试计数18276/949/967保持。测试严格使用八卡分片算法中rank0的前16条记录，实际trace逐项与预期sample_id相符：3条CoinVE、13条UE，覆盖合成R1～R5。CoinVE共同5秒裁剪、合成原采样、role-aware目标损失及最小padding均经正常入口执行。

运行时确认508个PEFT目标模块、1016个adapter张量、240146432个FP32可训练参数，其他模型参数排除在optimizer外。

## 执行结果

既有allocation129889/testqueue/JDS9B74，一张H200，14CPU/250GiB主存。通过native `datamake_ddp_train.main()`的`--single-gpu-probe --smoke --stop-after 4`执行；不替换forward、loss、数据集或optimizer实现，仅用外层hook采集梯度/更新/冻结权重证据。每次更新累计4条，单卡实际batch4，不冒充八卡global32实验。

| 更新 | loss | 裁剪前梯度范数 | 时间/秒 | 峰值allocated/GiB |
| --- | ---: | ---: | ---: | ---: |
| 1 | 0.198591 | 0.050538 | 192.41 | 95.13 |
| 2 | 0.072141 | 0.021465 | 47.61 | 118.01 |
| 3 | 0.074983 | 0.031930 | 32.45 | 94.32 |
| 4 | 0.083931 | 0.020776 | 54.96 | 116.87 |

4次更新、16次带梯度forward/backward全部成功，loss和梯度有限，无OOM、Python异常或编译缓存上限退化。第一步LR=0，属于原warmup：理解/生成的非零梯度张量分别247/256，但没有权重更新。第二步LR非零，两侧分别247/256个张量变化；第三、四步分别494/512个张量变化。末层部分理解adapter没有损失梯度属原计算路径，不等于双分支未训练。

所有被冻结的参数均无梯度，训练前后对完整冻结参数内容计算的SHA256一致。最高allocated约118.01GiB、reserved约120.08GiB。进程退出码0，结束后nvidia-smi显存占用0MiB。

第一步包含新61帧输入的编译和初始单CPU绑定开销。后三步平均约45.01秒/4条，但样本轮次不同，包含审计hook、I/O和编译因素，不作为稳定吞吐或八卡加速预测。这四批loss也不能用于判断收敛和泛化质量。

## 环境问题及处理

交互终端继承单核affinity，虽allocation分配14CPU，最初主进程与数据worker都绑定Linux CPU38。核对Slurm cgroup后，仅将本次诊断进程树调整到已有cpuset `38-42,45-46,102-106,109-110`；没有扩展allocation、改变其他进程或占用其他作业CPU。调整前后逐线程证据见原始输出的affinity_adjustment.json。

八卡sbatch明确申请112CPU/单task，不依赖该交互终端的单核绑定；本轮无需为此修改正式profile。

加载器唯一missing项`latent_pos_embed.pos_embed`为`PositionEmbedding3D`构造时确定性生成的冻结sin/cos位置表，1410项匹配、unexpected0；不是未初始化的可训练权重。mrope映射提示、Triton逻辑操作弃用提示和DDP unused检测提示未阻断训练；没有把提示直接当成训练正确性证明，以上结论来自真实梯度/更新/重载检查。

## checkpoint检查

4步后使用生产DDP-v6保存器额外保存一份约2.88GB的诊断checkpoint，再主动扰动一个adapter和optimizer LR，使用生产加载器恢复：

- 全部adapter逐tensor完全一致。
- Adam/optimizer的3048个状态张量全部完全一致，最大差0。
- scheduler完全一致，Python/NumPy/Torch CPU/CUDA RNG恢复检查通过。
- 游标completed_steps=next_step=4、next_microstep=16，optimizer_boundary=true。

本次没有跑到50步；50步间隔/keep4属于已复核的正式配置，本次额外保存只验证GPU状态序列化/加载。此诊断checkpoint world_size=1，带diagnostic_only标记，不能用作八卡正式恢复点；八卡新实验仍从官方基座新建LoRA。

## 证据与下一步

- [机器汇总](./datamake_coinve_single_gpu_validation_20260911.json)。
- [原始输出](../outputs/optimization_diagnostics/coinve_ddp8_single_gpu_20260911/)：config_audit、optimizer_audit、gpu_audit、stdout/stderr、run/metrics/trace、诊断checkpoint。
- 输出内probe.py/run.py为本次已完成诊断的复现证据，不是正式训练入口；run.py绑定本次allocation并拒绝复用已有run目录。生命周期为completed diagnostic，输出受保护，不作为默认清理候选。
- [八卡配置与启动命令](./datamake_coinve_ddp8_training_config_20260911.md)。

单卡训练与保存/重载链路通过，未发现阻塞八卡启动验证的配置问题。八rank GPU/NCCL、跨rank数据消费、连续3步对比2＋恢复1的GPU Gate尚未执行；按用户要求留给随后八卡作业。八卡配置的启动器会在Gate通过后才进入正式训练。L06/L08质量Gate与WF90 released边界不变。
