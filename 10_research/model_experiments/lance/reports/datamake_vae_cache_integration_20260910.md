# VAE缓存策略与高显存训练配置接入

> 日期：2026-09-10，Asia/Singapore。状态：实现与正常入口四卡验证完成。Technical所有者：[训练接入](../training_integration.md#peftddp-性能优化2026-09-09)，计划L10（整体正式迁移/恢复事项仍in_progress）。

## 已落实的结果

用户要求继续“更加充分利用显存”。已把[高显存实验](./datamake_high_memory_sweep_20260910.md)中的缓存策略接入正常DDP训练，并分别验证两臂候选；均为batch1/累积8、global batch32、保留VAE缓存，仍保留部分梯度检查点。

| 候选 | 关闭检查点层（从0编号） | 峰值allocated / reserved GiB | 验证范围 |
| --- | --- | ---: | --- |
| 理解＋生成（历史文件已于2026-09-11清理） | 26～35，共10层 | 118.24 / 121.29 | 12更新，前2预热后10计时 |
| 仅生成（历史文件已于2026-09-11清理） | 22～35，共14层 | 126.82 / 128.79 | 4更新，前2预热后2粗筛 |

硬件为原allocation126684、8GS9B74四张H200，每卡143771MiB（约140.4GiB），每次通过srun取得56CPU，全部串行。所有实测配置均无OOM。峰值为四卡最大值；不将短测无OOM推断为所有未来数据/更长训练都不会OOM。

**理解＋生成的同12步对照**：基线93.68380秒/更新，接入后的正常入口**85.77096秒，耗时缩短8.45%**。每rank同序96个prefix，合计384个目标曝光；12步全局及各rank loss、全局梯度范数与基线和先前隔离缓存实验逐步完全一致。与隔离实验85.83083秒仅差0.070%，说明性能收益已由正常代码路径复现。基线同条件复核和历史源码范围见高显存报告，不混用不同步数均值。

**仅生成分支的同4步对照**：off10初测仅用99.44GiB，因此自适应测试off14。保留off10对照配置（历史文件已于2026-09-11清理）；两组后2步均值由86.74733降至**84.48253秒，短测缩短2.61%**，峰值提高至126.82GiB。4步全局和各rank loss、全局梯度范数逐步完全一致。此比较仅是该分支内部的两步粗筛，不与理解＋生成的十步均值做跨分支加速比较，也不宣称层数已经全局最优。

## 实现与使用

官方`common/val/utils.py::make_padded_latent`增加keyword-only参数`empty_cache=True`。在线/离线/混合VAE计算保留，只使函数最后一次清缓存可选；未重写VAE、loss或attention。DDP读取`ddp.vae_cache_policy`：

- `release`：调用清缓存，未设置该字段时沿用此行为。
- `retain`：复用分配器缓存，正常trainer传`empty_cache=False`，每步metrics记录实际配置策略。

variant生成器支持`--vae-cache-policy release|retain`，生成独立run/W&B identity。原默认profile和原正式FSDP恢复点均未覆盖。新候选通过正常launcher读取，不再使用AST替换或训练猴子补丁。

正常入口只读检查命令（本轮两臂均执行dry-run；去掉dry-run才会按validate运行GPU启动验证，恢复验证还需明确传入已转换checkpoint）：

```bash
/scratch/prj0000000275/jcy/.conda/envs/xks_lance/bin/python \
  10_research/model_experiments/lance/scripts/run_datamake_ddp_training.py \
  --profile 10_research/model_experiments/lance/configs/datamake_stage6_mem_b1_off10_retain_20260910.json \
  --mode validate --dry-run
```

仅生成使用上表对应off14配置。精确短测命令在各`*_status.json`，核心训练入口均为`train/datamake_ddp_train.py`；`run_probe.py`使用`--smoke --benchmark-only --stop-after`执行真实优化器更新，隔离W&B且不保存正式checkpoint。

## 正确性与完成核验

- 122项Lance CPU回归通过。新测试直接执行真实VAE函数，覆盖在线/离线/混合输入，检查缓存策略不改变tensor值、对象/梯度属性、默认清缓存与retain跳过行为；profile策略校验通过。
- patch0020在官方9717d91 VAE文件及0016→0018→0019 DDP补丁之上重放，五个源码逐字节匹配当前实现。
- 三个正常入口run退出0；实际策略、检查点层数、四卡、global batch、四rank同样本顺序、有限loss与非零有限梯度范数全部核对。日志确认理解＋生成508个目标/240146432个参数，仅生成256个目标/120412160个参数，原冻结语义保持。
- 每个run的20个实现文件哈希与当前源码一致，包含新增`common/val/utils.py`。旧19文件合同作为历史证据保留，旧转换/恢复Gate不可直接复用；完整profile哈希区分缓存/检查点策略。
- 文档/数据集/Unreal共132项现有unittest回归通过（默认环境无pytest，使用unittest发现执行）；独立子系统与跨层文档审计结果见`documentation_final_audit.json`。
- GPU进程退出、四卡显存释放，用户交互allocation保留，原Stage6两臂仍暂停900/825；`final_runtime_audit.json`保存运行态核验。

本次“更充分使用显存”的实验及代码接入目标已具备正常入口的实现、复现和验证证据。原训练继续暂停；正式迁移/恢复Gate与长期质量验收仍属于L10后续事项，本次不接受正式续训或收敛。此前batch4的原生mask编译边界、packed BF16数值限制继续保留；本轮最终方案使用batch1，不推荐batch4/8为已可用训练选项。

## 证据与所有权

`outputs/optimization_diagnostics/cache_integration_20260910/`属于训练接入已有下游诊断范围，默认保护，不新建生产输出或清理类别：

- `run_probe.py`、`run_validation.py`、各run配置/合同、metrics与四rank trace：正常入口复现；追加off14以独立srun执行，未改写最初两组controller记录。
- `cpu_tests.out`、`core_tests.json`、`patch_replay.json`：回归与补丁证据。
- `audit_results.py`、`results.json`：逐要求完成核验和公平比较；`live_summary.py`仅供执行中观察。
- `documentation_final_audit.json`、`final_runtime_audit.json`、`goal_completion_audit.json`：文档、运行边界及目标最终审核。

patch0020、tests/test_datamake_vae_cache.py、三份新增retain配置，以及outer launcher/variant生成器由同一Technical所有者维护。本报告是该实现的当前结果入口；前一阶段实验报告保留当时的诊断实现与测量记录。
