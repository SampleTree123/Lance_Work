# Stage6 LoRA：PEFT / DDP 优化实现与验证

> 日期：2026-09-09；Lance `9717d91`，PyTorch `2.8.0+cu126`，PEFT `0.15.2`。
> 状态：实现与CPU回归完成；保存/Gate修复后需重新转换候选（旧转换证据保留）；单卡全层重算通过、全关和隔层重算均 OOM；四卡 NCCL 恢复与吞吐 Gate 待执行。尚未切换正式训练。
> Technical 所有者：[训练接入](../training_integration.md)。计划：L10；不关闭 L06/L08 质量验证。

后续用户已暂停原126188/126189，完整恢复点900/825；新旧路径的同H200/14CPU短速度对照已完成，精确结果见[暂停与短测报告](./datamake_lora_short_speed_20260909.md)。下文初版单卡与800转换记录保留历史范围。

## 修改目的与依据

本次解决的是 LoRA 相对全参训练没有明显提速，不是解释两种 LoRA 范围间的小幅速度差。历史日志中，全参 Stage2 约 17.398 秒/更新（batch4）；Stage6 两臂 601～800 平均 135.651 / 134.929 秒/更新，但每次累计 8 个 microbatch，折算约 16.956 / 16.866 秒/microbatch。约 2.6% / 3.1% 的差异只是不同运行条件下的描述，不能视为严格加速实验。

现有 FSDP 在 decoder block 内同时包裹冻结基座和 LoRA。当前 `use_orig_params=True` 混合布局可让 forward 中的冻结基座 view 继承 flat parameter 的梯度需求。PyTorch 2.8 CPU 复现观察到额外基座 view 梯度；原 optimizer 仍只更新 adapter，CPU 对照中 adapter 梯度一致，因此这首先是计算与通信浪费，不能据此断言已训练权重错误。旧 checkpoint-v5 的恢复证据继续有效。

另外，旧实现所有 decoder layer 强制激活检查点重算；LoRA 减少可训练参数，却仍需大部分基座 forward、激活反传、完整历史 ViT、VAE 和媒体解码。关闭重算有望降低时间，但会提高峰值显存；本次提供独立配置，实测前不将关闭重算设为正式默认。

官方依据于本次实现核对，适用范围为当前固定版本：PyTorch [FSDP 的混合冻结参数限制](https://docs.pytorch.org/docs/2.8/fsdp.html)、[DDP 与 no_sync](https://docs.pytorch.org/docs/2.8/generated/torch.nn.parallel.DistributedDataParallel.html)、PEFT [低层 adapter 注入](https://huggingface.co/docs/peft/en/developer_guides/low_level_api)及 [LoraConfig](https://huggingface.co/docs/peft/package_reference/lora)。DDP 是当前单机四 H200 的实现选择；[ZeRO-2](https://www.deepspeed.ai/tutorials/zero/)留作显存不足时的后续方案，本次没有加入第二套未经验证的训练后端。

## 实现

- 使用官方 PEFT `inject_adapter_in_model`、`LoraConfig` 和 adapter state API；DataMake 只维护分支目标列表、旧命名转换及确定性初始化。
- 固定原本 508 / 256 个目标模块、r64/alpha64/dropout0、FP32 adapter 和 BF16 基座计算。严格冻结基座，DDP 在更新阶段只同步 adapter 梯度；前 7 个 microbatch 的 forward/backward 均在 `no_sync()` 中，第 8 次同步。
- 原 GT 历史、R5×3 数据、区域加权 loss、batch32、累计8、LR/scheduler 和 optimizer 超参不变。冻结理解参数时保留理解激活传导。
- 激活检查点支持 `all`、`alternate`（偶数 decoder 层）和 `none`。每个模式使用独立配置、Run/W&B 身份和恢复合同；不能直接用不同模式的原生 checkpoint 绕过合同检查。
- checkpoint-v6 保存标准 PEFT 权重、按名称映射的完整 Adam、scheduler、四 rank RNG 和已消费 microstep；原子完成、SHA256、世界大小和配置/实现/数据合同检查。每100更新保存，保留最新4份完整 checkpoint。
- v5 转换器使用官方 PyTorch DCP consolidation；逐 tensor 验证导出的 adapter 等于 optimizer 携带的 live 参数，保留 Adam step/一二阶矩，不以新 optimizer 冒充续训。源 checkpoint 只读。
- 性能日志包含数据等待、VAE/区域权重、model forward、ViT 子集、backward/sync、总更新时间与显存；launcher 另记包含初始化/日志/保存的 `launch_segments.jsonl` 墙钟时间。ViT 属于 forward，分 rank 最大值不可简单相加。
- 四卡启动验证对比连续3步与2步保存后恢复第3步，检查 adapter、Adam、scheduler、RNG、cursor、每 rank sample/loss、非零生成 LoRA-B，以及连续/恢复两臂相对 prefix 的实际 B 更新。默认 `--mode validate` 完成后退出；正式执行需显式 `--mode train` 且 Gate 合同一致。

## 当前证据与限制

113 项 Lance CPU 回归通过，其中新增8项真实 PEFT 等价、初始化 RNG、基座冻结、完整恢复、Adam 重排/迁移、checkpoint 包装名称及损坏拒绝测试。两进程 Gloo 的真实 DDP 测试通过：3更新、累计8、区域加权 loss 对照显式全局参考计算，最大梯度差 `4.470348358154297e-08`。这些检查不代替四 H200/NCCL 或真实模型跨后端数值对照。

两份 Stage6 step800 曾按初版代码完整转换。以下为修复前的历史候选，当前实现合同已失效，保留审计但不作为启动入口：

```text
outputs/checkpoint_migrations/stage6_ddp_peft_both_800_20260909_final/0000800
outputs/checkpoint_migrations/stage6_ddp_peft_gen_800_20260909_final/0000800
```

同目录不带 `_final` 的首次转换及 `_preflight_snapshot` 是实现校验完善前的暂存结果，其合同已被后续代码变化失效，不作为启动入口；保留审计，不自动清理。`migration.json` 记录源路径和 adapter/live 参数一致性，转换成功仅表示文件级映射通过，四卡 continuation 仍待验证。

单卡诊断使用用户已有且空闲的 `126170` allocation、H200，保留四 rank 数据安排中的 rank0 样本、累计8，但实际 world=1；禁止写训练 checkpoint。该 allocation 只有1个 CPU 配额，媒体准备/编译可能限制速度。结果目录为 `outputs/optimization_diagnostics/peft_ddp_20260909/`；速度和显存见下方单卡记录，不将单卡数据推断为四卡正式收益。

原 Stage5、Stage6 FSDP trainer/profile/checkpoint 与已提交作业不变。本次不提交新的正式训练、不中止旧任务、不改 released 数据、不增加 VAE/ViT 缓存。

## 可复查命令

从本 Lance 目录运行；Python 使用现有 `xks_lance` 环境。PEFT 安装在本项目忽略目录，不升级共享 PyTorch/Transformers：

```bash
python -m pip install --no-deps --target runtime/peft_0_15_2 -r configs/requirements_ddp_peft.txt
python scripts/convert_datamake_fsdp_to_peft.py --profile configs/datamake_stage6_ddp_peft_both_branches_v1.json --source outputs/training_runs/datamake_dialogue_stage2_recipe_lora_r64_both_branches_v1_4xh200_restart1/checkpoints/0000900 --destination outputs/checkpoint_migrations/stage6_ddp_peft_both_900_20260909_recoveryfix/0000900
python scripts/run_datamake_ddp_training.py --profile configs/datamake_stage6_ddp_peft_both_branches_v1.json --resume-from outputs/checkpoint_migrations/stage6_ddp_peft_both_900_20260909_recoveryfix/0000900 --dry-run
python scripts/convert_datamake_fsdp_to_peft.py --profile configs/datamake_stage6_ddp_peft_freeze_und_v1.json --source outputs/training_runs/datamake_dialogue_stage2_recipe_lora_r64_freeze_und_v1_4xh200_restart1/checkpoints/0000825 --destination outputs/checkpoint_migrations/stage6_ddp_peft_gen_825_20260909_recoveryfix/0000825
python scripts/run_datamake_ddp_training.py --profile configs/datamake_stage6_ddp_peft_freeze_und_v1.json --resume-from outputs/checkpoint_migrations/stage6_ddp_peft_gen_825_20260909_recoveryfix/0000825 --dry-run
```

上述 recoveryfix 目标尚未生成；转换前确认相应完整源仍在，目标目录须不存在；源若已轮转则改用实际保留的完整步数。已有空闲四 H200/testqueue allocation 时，先完成转换，再分别运行 launcher 命令并把 `--dry-run` 换成 `--mode validate`。也可由用户使用两份新 sbatch，设置 `RESUME_FROM` 为对应绝对转换路径，保持默认 `DDP_MODE=validate`；这只运行验证，不自动正式训练。原 FSDP job 文件继续保持原用途。通过 Gate 后可以用 `--mode benchmark --benchmark-updates 20` 取得同样本测量；`--trace` 应作为单独诊断，不能混入干净计时。

全关与隔层重算均已在当前双分支配方 OOM，当前不采用这两种模式。以下仅保留独立配置/转换工具的使用示例，不能作为已验证启动方案；如后续进行新的显存实验，先生成独立配置，再用转换器把同一个旧 FSDP checkpoint 转到该配置专属目标，分别验证、测量。转换器不会接收不同原生 DDP 合同：

```bash
python scripts/prepare_datamake_ddp_variant.py --profile configs/datamake_stage6_ddp_peft_both_branches_v1.json --activation-checkpointing alternate --output configs/datamake_stage6_ddp_peft_both_branches_ac_alternate_v1.json
python scripts/convert_datamake_fsdp_to_peft.py --profile configs/datamake_stage6_ddp_peft_both_branches_ac_alternate_v1.json --source outputs/training_runs/datamake_dialogue_stage2_recipe_lora_r64_both_branches_v1_4xh200_restart1/checkpoints/0000800 --destination outputs/checkpoint_migrations/stage6_both_800_ac_alternate/0000800
python scripts/analyze_datamake_ddp_benchmark.py --run all=/absolute/all/benchmark --run alternate=/absolute/alternate/benchmark --warmup-updates 1 --output /absolute/comparison.json
```

正式选择还需覆盖 R1～R5 的最长上下文、检查峰值显存余量，以及在同4卡/CPU配额/数据顺序下测量。没有四卡 Gate 与足够长度的基准前，不宣称已实现确定比例的训练提速，也不自动将现有 FSDP 任务切到 DDP。

## 单卡运行记录与检查结果

截至 2026-09-09 18:43（Asia/Singapore），allocation126170 上的真实模型 `all` 模式完成3个更新，24个目标覆盖R1～R5（6/6/5/2/5例），峰值 allocated 41.313GiB。第2、3更新分别242.898和181.602秒，存在明显数据等待/编译及上下文长度波动，不能把两步平均视为稳定基准。

`none` 在首个 optimizer 更新完成前 OOM：GPU容量139.83GiB，PyTorch已分配137.91GiB，再申请246MiB失败；失败后显存已释放。当前配方不接受直接全关重算，因此保留 `all` 为默认，已进一步测试 `alternate`，结果见下方。失败原日志保留在 `ddp_none.err`；没有创建训练checkpoint。这个结果也说明“LoRA参数少”不代表长上下文激活显存很小。

修复前，两份 `_final/0000800` 的当时合同、全部文件哈希及恢复 dry-run 通过，next_step=800、四卡Gate仍required。原两臂各12个冻结实现文件和各自profile哈希与源checkpoint合同一致；补丁0016 reverse-apply检查与两份sbatch语法通过。113项Lance单元测试、22项文档+30项dataset+80项Unreal单元测试通过；当前环境未安装pytest，使用unittest直接执行完整现有套件。文档目录审计114文档/666链接、404脚本、5输出范围，独立子系统及跨层检查通过；另检167个下游研究本地链接无缺失。

机器证据：[implementation_validation.json](../outputs/optimization_diagnostics/peft_ddp_20260909/implementation_validation.json)、[单卡状态](../outputs/optimization_diagnostics/peft_ddp_20260909/single_gpu_probe_status.json)、[样本轮次覆盖](../outputs/optimization_diagnostics/peft_ddp_20260909/probe_sample_round_coverage.json)。小型运行证据在忽略的outputs目录保留；本报告记录可进Git的结论。

18:44只读Slurm核验：原126188在8GS9B74运行，126189等待Resources；126170仍为独立交互allocation。未对这些训练任务执行取消、修改或重启。旧FSDP源checkpoint按自身keep4滚动，日后转换新配置时必须先确认示例800源仍存在；若已轮转，应选择实际保留的完整源步数并同步目标命名，不能使用不完整目录。

隔层重算随后也在首个更新内OOM（PyTorch allocated137.49GiB，再申请776MiB失败）。这两项均为**双分支、单卡world1**诊断，不能外推为另一臂或不同输入条件的测试结果。两次失败均未写训练checkpoint；不继续以OOM配置做速度对比，也不据此修改原数据/帧数。

| 重算策略 | 当前双分支单H200结果 | 显存证据 | 当前选择 |
| --- | --- | --- | --- |
| all | 3更新/24目标完成，loss与gradient norm有限 | 峰值allocated41.313GiB | 保留默认；四卡Gate仍待执行 |
| alternate | 首个更新内OOM | 失败时allocated137.49GiB | 当前不采用 |
| none | 首个更新内OOM | 失败时allocated137.91GiB | 当前不采用 |

`all`去除首步后两步平均212.250秒，其中数据等待均值38.970秒、forward108.093秒、backward54.260秒；如此短的样本和1CPU资源不足以估计稳定四卡训练收益。当前结论是实现与单卡计算闭环可运行，**没有可接受的四卡加速倍数**。正式后端选择需要空闲四卡资源上的相同样本基准与完整恢复Gate。

最后审阅补齐了恢复辅助源码的合同哈希和launcher对官方基座文件的实际SHA256检查，`_final`转换候选随之重新生成；原FSDP源不变。这是保存/Gate修复前的记录；当前复查命令要求重新转换，见下节。

诊断退出后，126170上的GPU只读复核为1MiB、利用率0%；用户交互allocation仍保留。


## 保存重试与实际更新检查修复

2026-09-09，用户决定仅处理独立正确性审查中的两项：保存中断后重试，以及 Gate 验证真实更新。Adam 状态语义完整性强化和启动时逐 parquet 哈希核验暂缓；这两项防御性不足不代表正常保存或固定数据训练已经出错。本轮没有发现新的核心梯度计算错误，未执行真实四卡端到端验收。

- 保存：rank0 用 tempfile 创建独立 `.STEP.incomplete-<随机后缀>`，成功准备后将同一路径广播给全部 rank；各 rank 写自己的 RNG，最终仍原子发布到 `STEP/`。历史固定名/新格式残留都不会阻止重试；残留保留，不自动删除。已有完整同名 checkpoint 仍拒绝覆盖，keep4 仅作用于已完成数字目录。
- Gate：保留原连续3步与2+恢复第3步的一致性检查；额外要求连续与恢复结果各自至少一个 generation LoRA-B tensor 相对 prefix 有精确值变化。使用 prefix→第3步，避开新训练首步 LR=0 的正常行为；不要求所有 tensor 改变，不把数值对齐容差用作“是否更新”的阈值。
- 回归：115项 Lance CPU测试和132项核心CPU测试通过。新增故障注入覆盖旧临时目录、实际保存失败、同一步重试、完整目录防覆盖；Gate覆盖 first_step=0/800、两臂均不更新/单臂更新/两臂均更新，包括小于对齐容差的真实更新。
- 双进程CPU/Gloo实测通过：修复后的共享临时路径正确保存两rank RNG；两种分支、BF16基座/FP32 adapter、真实非重入重算、生产loss函数和累计8下，参考梯度差为0，保存后恢复下一步的权重/Adam/scheduler/RNG完全一致。前向与重算时基座 weight.requires_grad 均为False。CPU结果不代替四H200/NCCL验证。
- 代码/patch0016已同步。checkpoint-v6布局不变，但合同包含源码SHA，本轮修改使旧 `_final` 转换候选和旧 Gate 失效；禁止手工重写旧合同。下一次GPU验证前按上方命令从完整v5源重新转换到独立 recoveryfix 目录。本轮未执行该大型转换、未启动GPU作业。

修复验证证据：[recovery_gate_fix_validation.json](../outputs/optimization_diagnostics/peft_ddp_20260909/recovery_gate_fix_validation.json)。原FSDP代码、profile、数据和运行任务未改动，L10仍为in_progress。

## 位置处理归约优化（2026-09-10）

[共享位置helper优化](./datamake_position_sum_optimization_20260910.md)已完成CPU/CUDA等价及真实梯度/单样本速度验证；DDP实现合同新增data/common.py，已有转换候选/Gate不得沿用旧合同。正式四卡恢复与吞吐验收仍待执行，原训练保持900/825暂停。
