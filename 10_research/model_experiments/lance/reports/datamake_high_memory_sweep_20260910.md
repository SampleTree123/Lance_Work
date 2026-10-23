# H200更高显存配置短测

> 日期：2026-09-10，Asia/Singapore。状态：实验完成，batch4编译边界保留。Technical所有者：[训练接入](../training_integration.md#peftddp-性能优化2026-09-09)，计划L10。

后续实现已完成：[VAE缓存策略与高显存配置接入](./datamake_vae_cache_integration_20260910.md)记录正常入口、两臂最终候选与验证；下文保留本阶段隔离实验的原始范围。

## 结论与最终复测

用户要求继续利用H200剩余显存。本轮在原allocation126684、8GS9B74四张H200（各143771MiB，约140.4GiB）完成更高显存探索。最有希望的候选是**每卡batch1/累积8，关闭26～35共10层检查点，保留VAE分配器缓存**。

| 12更新对照（前2预热、后10计时） | 平均秒/更新 | 峰值allocated / reserved GiB |
| --- | ---: | ---: |
| 前轮基线：batch1，全检查点，原清缓存行为 | 93.68 | 41.05 / 43.13 |
| 本轮最终候选：关闭10层、保留缓存 | 85.83 | 118.24 / 121.29 |

最终候选耗时缩短**8.38%**，吞吐由0.3416升至0.3728个目标视频/秒。全局batch32，双方每rank同序96个prefix、总384个目标曝光；12步全局和各rank loss、全局梯度范数逐步完全一致，均为有限值且梯度范数非零。无OOM。计时段每步范围78.83～91.50秒，样本标准差4.10秒；这是短测结果，不推断长训练收敛或所有数据上的OOM边界。

基线来自[前轮12更新实验](./datamake_four_gpu_optimization_20260910.md)，本轮另跑相同前4步基线，测量段与前轮对应两步仅差0.174%，loss一致。不会把4步初筛均值与12步复测均值直接计算加速比。

## 初筛与缓存对照

每组初筛4次完整optimizer更新，前2次预热，后2次用于筛选。相同global batch32、每rank32个prefix、fresh both_branches r64 LoRA、相同数据/模型/优化器和56CPU affinity；全部串行执行。

| 初筛配置 | 秒/更新 | 峰值allocated / reserved GiB | 相对本轮基线耗时缩短 |
| --- | ---: | ---: | ---: |
| 基线：batch1，全检查点 | 99.78 | 41.04 / 43.13 | +0.00% |
| batch1，关闭8层 | 100.66 | 101.25 / 103.40 | -0.88% |
| batch1，关闭12层 | 99.51 | 135.16 / 138.07 | +0.27% |
| batch2，关闭4层 | 96.18 | 115.25 / 118.34 | +3.61% |
| batch1，全检查点，保留缓存 | 97.24 | 41.04 / 43.19 | +2.55% |
| batch1，关闭8层，保留缓存 | 92.48 | 101.25 / 103.87 | +7.32% |

关闭12层已经达到135GiB实际张量峰值，但几乎没有加速。关闭8层时，保留缓存使同配置耗时从100.66降至92.48秒；VAE/区域权重阶段从10.72降至3.98秒。该隔离对照支持每微步清缓存造成了显著开销、抵消部分检查点重计算节省的判断。各阶段指标分别取跨rank最大值，不可严格相加归因；未进一步分解具体cudaFree/cudaMalloc开销。

官方`common/val/utils.py::make_padded_latent()`每微步调用一次`torch.cuda.empty_cache()`。按[PyTorch2.8文档](https://docs.pytorch.org/docs/2.8/generated/torch.cuda.memory.empty_cache.html)，它释放分配器未占用缓存，不会直接增加PyTorch可用显存；某些情况下可能改善碎片。查阅日期2026-09-10，适用本地Torch2.8.0+cu126。本轮测试保留缓存的收益，不把关闭清缓存等同于释放活跃计算图。

最终off10候选由off8约101GiB和off12约135GiB的实测边界自适应选择，用更多激活减少重计算，同时保留容量余量；不是穷举所有层组合的最优解。

## batch4的明确边界

`screen_b4_all`首步失败，**不是OOM**，也没有有效吞吐/优化器更新结果。错误路径为`modeling/lance/lance.py:270 → torch.nn.attention.flex_attention.create_block_mask(_compile=True)`；当前Inductor/Triton生成262144²=68719476736元素的布尔mask中间kernel，报`XBLOCK=8192`超过4096。结论来自本地错误栈与生成kernel，不能推广为所有PyTorch版本或所有batch4实现都失败。官方实现参考[PyTorch2.8 create_block_mask源码](https://github.com/pytorch/pytorch/blob/v2.8.0/torch/nn/attention/flex_attention.py)，查阅日期2026-09-10。

原初筛controller按非OOM错误停止，失败状态和日志原样保留；定位后独立完成b2_off4，随后完成缓存对照和最终候选。未临时重写mask或更改环境规避编译器限制，未继续盲测batch8。batch4/8配置通道仅供诊断，CPU检查通过不代表GPU训练已可用。

## 实现、正确性与适用范围

- `IndexedPackedPrefixDataset`、外层profile校验和variant生成器放开batch1/2/4/8；仍使用官方packer与已有slot归一化loss，每卡batch×累积=8。patch0019记录clone的限制扩展，默认profile仍为batch1/全检查点。
- 120项Lance CPU回归通过。两进程Gloo/DDP、官方PEFT和非重入检查点下，batch2/4/8与8个独立微步的梯度最大绝对差均3.469446951953614e-18。
- 四rank真实batch4（训练token151656）媒体/文本/位置/索引逐tensor一致；mask的各段边界及代表位置与独立样本一致，样本间attention隔离。0016→0018→0019在空Git重放后四个DDP源码逐字节一致。
- 缓存优化本轮仅由隔离`cache_probe_train.py`实施：AST把官方VAE函数唯一一次清缓存调用改为pass，其余函数计算保留。四rank保存原函数、替换AST和wrapper哈希；没有修改官方VAE生产源码，也未切换默认或正式训练配置。
- 所有成功运行的19个生产源码哈希、数据/模型/优化配方和四rank样本trace核对通过。全部batch1配置的逐步loss和梯度范数与基线完全一致。这不是逐参数梯度全量或正式恢复Gate。
- 扩大batch保留[前轮BF16限制](./datamake_four_gpu_optimization_20260910.md)：batch2固定噪声梯度相对L2差35.26%，FP32 Transformer对照降至0.160935%。本轮吞吐探索不接受BF16 packed等价或收敛；最终候选保持batch1。没有重复77分钟FP32诊断。

建议下一项实现工作是将保留VAE缓存行为收敛为可配置DDP选项，再配合选择性检查点做正式迁移/恢复验证。当前结果不自动恢复正式训练、不晋升后端。原Stage6两臂仍暂停900/825，L10保持in_progress，WF90发布状态不变。

## 复现与证据所有权

证据根：`outputs/optimization_diagnostics/memory_sweep_20260910/`，属于训练接入已有optimization_diagnostics范围，不创建新生产或清理类别。

- `run_probe.py`、`run_initial_sweep.py`：初筛精确命令、配置/源码合同、56CPU affinity、四rank trace、metrics和错误；`screen_b4_all.err`、`batch4_generated_mask_kernel.py`和`batch4_compiler_evidence.json`保留编译边界，生成kernel仅为证据，不作为可执行训练脚本。
- `cache_probe_train.py`、`run_cache_probe.py`、`run_cache_sweep.py`：隔离缓存诊断和串行控制；最终运行目录`final_b1_off10_keepcache/`。
- `real_packing_cpu_check.py`、`real_packing_cpu.json`、CPU日志和`patch_replay.json`：输入、mask、梯度数学和补丁证据。
- `analyze_sweep.py`、`comparison.json`、`audit_completion.py`、`completion_audit.json`：公平比较和完成检查；`live_summary.py`仅为执行中观察，`write_final_report.py`由已完成记录生成本报告。
- `core_tests.json`：文档22、数据集30、Unreal80，共132项unittest通过；默认解释器无pytest，已用等价unittest发现执行现有测试。`documentation_final_audit.json`记录独立子系统与跨层审计：114文档、675本地链接，零错误/警告。`final_runtime_audit.json`记录四卡显存/进程清空、原两臂仍暂停及交互allocation保留。

复测命令（仅在已有四卡allocation和空闲GPU上执行，label必须使用新的输出名）：

```bash
srun --jobid=126684 --overlap --ntasks=1 --cpus-per-task=56 --cpu-bind=none --time=00:42:00 \
  /scratch/prj0000000275/jcy/.conda/envs/xks_lance/bin/python \
  10_research/model_experiments/lance/outputs/optimization_diagnostics/memory_sweep_20260910/run_cache_probe.py \
  b1_off10 --updates 12 --label YOUR_NEW_LABEL
```

allocation编号为本轮历史记录，不是未来可直接复用的资源授权。`--benchmark-only`隔离W&B且不保存正式checkpoint；复现脚本拒绝覆盖已有run目录。
