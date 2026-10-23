# 位置编码求和优化与单卡验证

> 日期：2026-09-10，Asia/Singapore；准备工作始于09-09，输出根沿用当日名称。Technical 所有者：[训练接入](../training_integration.md#peftddp-性能优化2026-09-09)。计划L10，四卡验收仍待执行。

## 修改

针对上游commit `9717d91` 的 [data/common.py::shift_position_ids](../lance/data/common.py)，把两个Python内置sum改成Tensor.sum。按原条件首次需要计数时计算一次并转成布尔值，此后在同次调用的split循环里复用；modality标签不随位置更新变化。保留原有位置赋值顺序、原地修改行为以及未启用分支的短路行为，没有移动位置编码更新或改变训练loss。

[patch0017](../patches/legacy/0017-vectorize-position-modality-counts.patch)可重放到上游。该公共函数被旧训练和推理调用者共同使用，因此这些调用路径也会采用优化后的计算；原FSDP trainer/checkpoint文件与所有profile未修改。[DDP launcher](../scripts/run_datamake_ddp_training.py)把data/common.py加入代码哈希合同：旧DDP验证/转换合同不能直接沿用，后续仍须从完整900/825源按当前合同转换并通过四卡Gate，不改写旧合同。本轮没有恢复训练或执行大checkpoint转换。

## 正确性

- [位置编码回归](../tests/test_datamake_position_ids.py)直接提取固定上游commit中的原函数作为参考。CPU和CUDA各147组对照，覆盖数量相等/不等、缺少modality、空输入、零值/求和抵消、重复片段、inactive分支和int32/int64，完整位置编码输出逐元素一致，原地返回与modality输入保持行为一致。
- 同一个真实R5样本的完整位置编码逐元素一致，形状/输出SHA见paired/summary.json。
- 同一已加载PEFT/DDP模型、固定噪声种子2081，原版/优化版真实forward+backward的1016个非空LoRA梯度张量逐元素一致；所有6轮loss均严格相等。
- 117项Lance CPU测试通过，包括新增函数等价与DDP合同覆盖测试。patch反向检查及在干净上游文件上重放并比对完整文件均通过。

## 速度短测

使用现有testqueue allocation126170、H64Y574单H200/14CPU，both_branches、全层非重入检查点、每卡batch1。固定此前算子诊断的真实R5样本 `dmmt_77da8eb0bbc91bcfae3b`，有效序列62617、padding2919。缓存视频与VAE latent；模型内部ViT、位置处理、attention/mask、forward、loss和backward仍执行。每轮loss除以8，但不执行8次累积或optimizer更新，不写训练checkpoint、不运行W&B。

同一进程/同一模型先各预热一次，然后按原版、优化版、原版、优化版交替计时，仅替换模型模块中的位置处理函数引用。位置函数计时末尾CUDA同步对两种实现一致。没有profiler，不包含模型启动/媒体解码/VAE编码/optimizer耗时；第0轮还额外验证真实位置编码，因此不纳入均值。

| 单个真实R5样本 | 原版Python sum | 优化版张量归约 |
| --- | --- | --- |
| 位置编码函数 | 4.159701秒 | 0.002725秒 |
| 模型forward | 8.190266秒 | 4.040652秒 |
| backward含重算 | 9.436001秒 | 9.456845秒 |
| forward+backward | 17.626267秒 | 13.497497秒 |


该样本forward+backward平均节省 **4.129秒（23.42%）**。这是一次真实长样本计算路径的单变量对照，不应直接把比例外推到全部对话轮次、101秒/完整update或四卡吞吐。后续正式后端选择仍需同样本四卡数值/恢复和完整update验证。

## 产物与状态

输出根 `outputs/optimization_diagnostics/position_sum_20260909/` 属于现有optimization_diagnostics审计范围，包括probe.py/run.py、原始stdout/stderr、paired/summary.json、comparison.json、status.json、validation.json。诊断脚本不作为正式训练入口，未改变正式run身份。

两种函数均正常完成，GPU计算进程已退出；原训练继续暂停在900/825。当前代码合同只新增公共helper并改变DDP launcher哈希，其余已绑定源文件及profile哈希一致。文档/核心回归与审计结果记录在输出根validation.json。该验证不构成新PEFT/DDP四卡恢复验收，也不证明所有训练样本都有相同加速比例。
