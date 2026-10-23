# LoRA 新旧实现的算子级短对照

> 日期：2026-09-09，Asia/Singapore。Technical 所有者：[训练接入](../training_integration.md#peftddp-性能优化2026-09-09)。属于 L10 诊断证据，不替代四卡恢复/数值/吞吐验收。

## 范围与复现

在既有 testqueue allocation126170、H64Y574 单 H200/14CPU 上，先旧 BranchLoRA/FSDP NO_SHARD，再新 PEFT/DDP。生产 trainer 的模型初始化、冻结精度、官方基座、全层非重入检查点和分布式包装按现行源码复用到独立诊断脚本。正式 trainer/profile/patch 不修改；两个原训练继续暂停在900/825。

固定原短测 rank0 的第一条真实样本 `dmmt_77da8eb0bbc91bcfae3b`，target_round=5，实际序列62617、padding2919，总长65536。缓存媒体和 VAE latent，仍执行模型内部 ViT、位置编码/attention mask、forward、区域加权 loss 和 backward。两次预热、两次普通计时，最后单独一次 CPU/CUDA profiler；每次固定噪声种子2081，loss除以8，清空梯度，不进行 optimizer.step、不保存训练checkpoint、不运行W&B。没有实际执行8次累积或四卡通信，不能直接替代上次32样本的完整update比较。

运行证据根：`outputs/optimization_diagnostics/operator_probe_20260909/`，包括 `probe.py`、`run.py`、`analyze.py`、两臂 `summary.json` / `events.json`、`comparison.json`、`status.json` 和独立 `sum_probe.py` / `sum_probe.json`。这些是现有 optimization_diagnostics 下游输出范围中的审计材料，不是正式训练入口或恢复点。

## 普通计时

| 每个固定样本 | 旧 FSDP | 新 PEFT/DDP |
| --- | --- | --- |
| forward（秒） | 8.170962 | 8.242229 |
| backward含重算（秒） | 9.691553 | 9.436727 |
| 峰值allocated（GiB） | 64.198652 | 37.441003 |
| forward+backward（秒） | 17.862515 | 17.678956 |

该样本前向加反向时间缩短1.03%；是单个R5样本的普通计时，不是上次完整update的3.30%。

最后一次带profiler的forward/backward分别为旧版12.313993/9.726497秒、新版12.009801/9.470411秒，仅供观察采集开销。

普通计时包含 forward 内部的CPU调度/同步等待。profiler开销单列，不能用其总时间替换普通计时，也不能把嵌套算子 inclusive 时间重复相加。此次峰值显存不含正式Adam状态/完整8次累积，与上次80.99/41.04GiB不是同一测量范围。

## 基座梯度修复是否生效

真实模型hook显示：旧版508/508个基座层前向weight.requires_grad=True，504个decoder内基座层重算时也为True；新版分别为508/508及504/504个False（另4个目标层位于decoder重算范围外）。

| 每次反向 | 旧 FSDP | 新 PEFT/DDP |
| --- | --- | --- |
| 基座权重梯度矩阵乘法数 | 508 | 0 |
| 这些GEMM的GPU执行时间合计 | 446.943毫秒 | 0.000毫秒 |

基座权重梯度GEMM在新版确实消失；旧版仅约0.447秒，而该样本普通前向+反向约17.863秒。两种计时口径不同，这只能说明量级，不能作为精确百分比的关键路径分解。

分类依据是 `aten::mm` 的输入/输出矩阵形状、MmBackward/AddmmBackward父事件、排除嵌套前向linear/matmul，然后匹配基座权重形状或其转置。反向在autograd线程执行，不能要求父事件一定包含主线程的DIAG_BACKWARD标签；分析器显式处理此边界。逐形状计数/耗时及508个基座模块的前向/重算hook记录保留在结果中。

权重梯度矩阵乘法时间不包含全部梯度缓冲分配、cast、flatten/reduce等开销；它证明核心额外GEMM数量和量级，不能视为整个FSDP问题的精确因果消融。两臂还同时改变了adapter实现、基座存储精度和wrapper。

## 共同保留的主要开销

FlexAttention生成kernel的CPU父事件归属及张量形状见comparison.json；36层前向、36层重算和36层反向的主要kernel分别汇总如下（只记对应kernel，不含全部周边attention操作）：

| 阶段 | 旧版GPU毫秒 | 新版GPU毫秒 |
| --- | --- | --- |
| attention前向 | 1639.273 | 1619.047 |
| attention重算 | 1623.340 | 1628.621 |
| attention反向 | 4685.565 | 4545.569 |


此外，真实profiler捕获约75万次整数加法kernel。代码 [data/common.py 的 shift_position_ids](../lance/data/common.py) 在split循环中使用：

```python
sum(i_sample_modality == 2) == sum(i_sample_modality == 1)
```

这里的Python内置sum逐个迭代CUDA张量，产生大量细碎GPU操作。位置处理在两种后端中都保留。算子统计结合源码支持其为明确的优化候选，但本轮没有给该函数加独立生产范围计时，也没有修改其语义。

隔离测试对同样长度62617的合成CUDA布尔向量做12次归约，每种执行两轮：Python sum平均3.916722秒，Tensor.sum平均0.000232秒，计数均20873。该证据仅说明求和实现的局部开销与计数等价，不代表完整位置编码函数或端到端训练已经验证替换后等价/提速，也不能把3.92秒直接扣到每个训练样本上。

## 结论与边界

冻结修复确实减少基座权重梯度计算，但该样本的额外权重梯度GEMM只占数百毫秒量级；attention、重算、输入反传及位置处理仍然执行，因此不能按冻结参数比例期待成倍加速。接下来优先验证位置处理的张量归约替换和整函数输出等价，再考虑attention/检查点策略；这是建议，尚未实施正式修改。

两臂均正常退出，样本ID/序列长度一致；未恢复原训练，未写训练checkpoint。生产代码合同与此前短测完全一致。132项核心CPU回归（22文档、30数据、80Unreal）通过；文档catalog/inventory与完整审计结果见诊断输出根中的validation.json。四卡NCCL/恢复Gate和收敛质量仍待验证。

## 后续实现

2026-09-10已按用户授权完成[位置求和优化与验证](./datamake_position_sum_optimization_20260910.md)。上文“尚未修改”描述诊断当时状态；实际修改、当前合同和效果以上述报告为准。
