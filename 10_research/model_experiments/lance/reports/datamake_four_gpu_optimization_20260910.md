# 四卡检查点与 packed batch 优化验证

> 日期：2026-09-10，Asia/Singapore。Technical 所有者：[训练接入](../training_integration.md#peftddp-性能优化2026-09-09)。用户指定的三步短测已完成；不表示新后端完整恢复或正式训练质量验收通过，计划L10继续in_progress。

## 范围与结论

按用户顺序完成：修改sum后的四卡基线、关闭少量检查点、在全检查点基线上扩大每卡batch至2。基线、关闭2层、关闭4层、batch2四组均完成12次optimizer更新并退出0；前2次预热，后10次计时。全部无OOM，loss与梯度norm有限且梯度非零。

使用既有交互allocation126684，节点8GS9B74，四H200/56CPU；各runner实际CPU affinity均56。保持官方基座、fresh both_branches r64 LoRA、BF16计算、全局batch32、数据顺序、优化器及调度配方。每组每rank消费相同96个prefix，共384个目标样本；四rank逐步sample IDs与基线完全一致。无W&B上传或训练checkpoint写出，实际执行forward/backward/optimizer更新。

| 配置 | 平均秒/更新 | 相对基线耗时下降 | 跨卡最大allocated峰值 GiB | 目标样本/秒 |
| --- | ---: | ---: | ---: | ---: |
| batch1 / 累积8 / 全检查点 | 93.6838 | — | 41.0466 | 0.3416 |
| batch1 / 累积8 / 关闭34、35层检查点 | 92.9987 | 0.7313% | 50.4105 | 0.3441 |
| batch1 / 累积8 / 关闭32～35层检查点 | 93.1451 | 0.5751% | 67.3686 | 0.3436 |
| batch2 / 累积4 / 全检查点 | 92.6229 | 1.1324% | 63.0883 | 0.3455 |

这次短测未显示明显的端到端提速：关闭2/4层检查点分别增加约9.36/26.32GiB显存，耗时只下降0.73%/0.58%；batch2增加约22.04GiB，耗时只下降1.13%。短测、顺序执行和运行波动限制外推，不能把这些微小差异当作稳定加速保证。新DDP候选默认仍保留全检查点、每卡batch1；部分检查点和packed配置保留为实验选项。

显存表是跨rank最大单卡PyTorch allocated峰值，不是四卡总和。对应reserved峰值为43.1348/52.2656/69.3418/66.1289GiB。batch2逐rank allocated峰值为63.0883/60.7851/58.4134/62.1706GiB。基线快照没有记录逐rank峰值，相关字段为null。所有诊断GPU进程已退出并释放显存；用户交互allocation继续保留。

## 耗时观察与后续线索

以下是每步各阶段跨rank最大值的均值；各项最大值可能来自不同rank，不能相加作精确耗时分解。

| 配置 | 前向秒 | 反向含同步秒 | VAE与区域权重秒 |
| --- | ---: | ---: | ---: |
| batch1 / 累积8 / 全检查点 | 23.493 | 57.474 | 5.599 |
| batch1 / 累积8 / 关闭34、35层检查点 | 23.523 | 56.130 | 6.347 |
| batch1 / 累积8 / 关闭32～35层检查点 | 23.573 | 55.079 | 7.525 |
| batch2 / 累积4 / 全检查点 | 24.618 | 60.235 | 5.828 |

关闭少量层只省去相应层的重算：关闭2/4层的反向阶段确有缩短，但其他阶段也发生波动，最终收益很小。batch2没有减少原有样本的有效token及监督计算，前向和反向阶段均未缩短；减少调用次数并未转化为明显整体收益。本次没有进一步对CUDA kernel作耗时归因。

两个未纳入本轮修改的具体线索：

- 官方`common/val/utils.py::make_padded_latent`在每个微步调用`torch.cuda.empty_cache()`。分配/清理成本可能影响保留更多激活后的收益；没有对应allocator profile，尚不能认定因果。
- 官方`data/dataset_base_train.py::to_tensor`将尾部padding加入独立sample并设为causal。`modeling/lance/qwen2_navit.py`补零Q/K/V后仍计算该段attention，最后裁掉输出。两段padding长度p1/p2合并为p1+p2时，掩码允许的无效query/key对增加p1×p2；例如各32000时额外约10.24亿对。实际kernel成本取决于块稀疏调度，不能直接换算为秒。后续优先独立验证屏蔽padding attention或缩小padding预算，再讨论与batch组合；本轮未修改这些行为。

## packed实现与数值结果

新增`train/datamake_packed_batch.py`复用官方`PackedDataset.pack_sequence/to_tensor`，按原rank/index种子处理两个prefix；每样本上限65536不变，总容量131072。保留VAE/ViT媒体形状、索引和样本attention边界，DataLoader一次传一个完整packed对象。

原配方每个微步先跨rank按区域权重归一化。packed loss将两个slot分别跨rank归一化再平均，batch2/累积4保持batch1/累积8的样本目标权重；不对拼接后全部token简单统一平均。当前仅支持Stage6 MSE-only监督；consumed cursor仍按原prefix计数，每次更新每rank消费8个prefix。

真实四GPU固定相同latent、flow噪声、媒体和位置索引，对照两个独立样本与一个packed对象：

| 数值对照 | 梯度相对L2差 | 梯度cosine | 全局loss |
| --- | ---: | ---: | --- |
| 原BF16计算 | 35.2611% | 0.947486 | single 0.15002221；packed 0.14997114 |
| Transformer及输出投影FP32、禁用TF32 | 0.160935% | 0.999998706 | 两者均0.14985626936 |

原BF16对照超过事先设定的2%梯度阈值，仍记录为未通过；不因loss接近而忽略。重复single计算的loss和梯度逐位一致，排除了本次参照随机漂移。Transformer输入采样完全一致，BF16第一层出现约0.05%～0.19%差异并逐层放大。

FP32对照四rank一致，最大梯度绝对差5.17815e-7，最终预测采样相对差约7.77e-7～1.56e-6，达到原数值阈值。它使用同一批BF16舍入后的基座数值升为FP32，保留原BF16视觉/latent构造；耗时4663.61秒属于精度诊断，不代表训练速度。提高计算精度后差异显著下降，强烈支持BF16形状相关数值误差被深层计算放大的解释；没有定位到某个具体kernel，也没有证明所有输入或长期收敛等价。

因此，在高精度对照通过后完成了独立的BF16 batch2吞吐测量，但未将原BF16梯度等价Gate改为通过，未接受batch2为正式训练默认。PyTorch2.8在[官方数值精度说明](https://docs.pytorch.org/docs/2.8/notes/numerical_accuracy.html#batched-computations-or-slice-computations)中说明批量与逐片计算不保证逐位一致；此一般事实本身不构成本项目35%梯度差可接受的证明（核验日期2026-09-10）。

## 验证与可追溯证据

证据根：`outputs/optimization_diagnostics/four_gpu_optimization_20260910/`，属于既有下游诊断输出范围。保留配置、精确命令、源码合同、stdout/stderr、metrics及逐rank trace。

- `comparison.json`：四组12步结果、后10步统计、逐rank显存及相同样本顺序核对。
- `completion_audit.json`：每组退出0、optimizer_step连续1～12、全局目标曝光32～384、四rank各96个prefix、有限loss/非零有限grad_norm；记录三步实验完成，同时明确BF16等价Gate未通过、正式后端未接受。
- `comparison_contract_audit.json`、`final_source_audit.json`：基座、数据配置、recipe、运行库及PEFT版本一致，三个变体各19个源码哈希仍与运行合同一致。相对基线的既有源码差异仅为trainer和外层launcher，另新增packed helper。基线status的source_sha256记录原trainer；逆转诊断快照的路径前缀及禁止smoke保存两项变换，可恢复该原始哈希。
- 120项Lance CPU回归通过；`tests/packed_batch_distributed_check.py`的两进程Gloo/DDP、官方PEFT、非重入检查点及不等长区域加权梯度对照最大差3.469446951953614e-18。
- `real_packing_cpu.json`：四rank真实媒体拼接及边界检查。该CPU辅助检查使用默认占位token151655；真实GPU对照已使用训练token151656并重新逐tensor验证媒体、文本、位置和索引，不能混同两种范围。
- `packed_gpu_validation_attempt2/`保留BF16失败，`packed_gpu_diagnostic/`保留single-repeat及逐层定位，`packed_gpu_fp32_diagnostic/`和`fp32_result_summary.json`保留高精度结果。`batch2_benchmark_decision.json`保留精度检查到测速的明确边界。
- `patch_replay.json`：0016→0018在空Git中重放，四个DDP源码逐字节一致；patch0018纳入packed与选择性检查点支持，公共sum优化由0017维护。
- 诊断脚本早期的Tensor比较、分布式初始化、MagicMock和dtype衔接错误均保留在`*.attempt*`日志中；不算作训练实现已通过。高精度进程及两级等待监护最终均退出，真实returncode为0。

备用的`packed_gpu_full_reduce_check.py`/`run_packed_full_reduce_check.py`仅已准备并检查语法，未执行。它通过官方`allow_bf16_reduced_precision_reduction=False`重用原BF16检查；该开关未加入生产trainer。原控制器`sequence_status.json`保留其在BF16检查处停止的历史状态，最终实验状态以各组status及completion_audit为准。

## 当前边界

三步性能探索已完成，未启动完整训练或新一轮性能方向。原Job126188/126189再次经Slurm核实为COMPLETED、ExitCode0:0，完整恢复点仍900/825，未自动续训。新PEFT/DDP完整状态迁移及四卡原生恢复Gate仍待执行，旧转换候选不能手工改合同复用；本次fresh短测不替代这些Gate或视觉/收敛验收。

Technical、Plan L10、Status/机器状态和HANDOFF同步本次结论；L06/L08/L10仍in_progress，WF90 released不变。核心132项unittest通过（documentation22/dataset30/unreal80）；最终文档审计通过：114文档、673本地链接，各独立子系统与跨层检查全部通过，零错误/警告；证据为同一诊断根的`documentation_final_audit.json`。
