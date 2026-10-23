# Stage6：Stage2配方的LoRA理解分支对照

> 日期：2026-09-07；保留策略更新：2026-09-08  
> 状态：`restart1_resume800_submitted_pending_user_visual_review`（2026-09-09）  
> 实现所有者：[训练接入](../training_integration.md)  
> 范围：restart1已通过两臂四卡恢复Gate并保存至800；800续跑已由用户提交，同条件视觉输出及媒体检查完成，待用户验收。准确状态和已执行命令见[恢复记录](./datamake_stage6_checkpoint_rescue_20260907.md)，不重复提交，不宣称质量Gate通过。

## 两臂与冻结规则

| 项目 | S6-1 | S6-2 |
| --- | --- | --- |
| 配置 | [both_branches](../configs/datamake_dialogue_stage2_recipe_lora_r64_both_branches_v1.json) | freeze_und（历史文件已于2026-09-11清理） |
| 生成分支LoRA | 更新：256模块、120,412,160参数 | 相同 |
| 理解分支LoRA | 更新：252模块、119,734,272参数 | 不添加适配器，理解参数冻结 |
| 总LoRA参数 | 240,146,432 | 120,412,160 |
| 基座、ViT、VAE、embedding、lm_head、norm/bias | 全冻结 | 全冻结 |
| 理解激活detach | False | False |

不使用 `freeze_und=True`：原开关会截断理解激活梯度，不是仅冻结参数。两组都保留Stage2的 `freeze_und=False`，只改变理解线性层LoRA是否存在。GEN适配器按模块名与种子初始化，跨两臂相同，且不消耗主训练随机数流。LoRA参数FP32，FSDP BF16计算，r64/alpha64/dropout0。

## 完整共同配方

- 从官方 `models/Lance/Lance_3B_Video/` + fresh LoRA/Adam/scheduler开始；不加载Stage2、Stage5或旧optimizer。原Stage2从Stage1继续训练，因此只能将新两臂互比视作严格的理解adapter消融。
- 同一seed2026的3,600/200/200链划分；Stage2 R5×3数据，共14,675加权前缀。validation/test不参与训练。
- 每个microbatch一个dialogue前缀、一个GT目标。全部历史GT进入ViT，最新GT作为唯一clean VAE source；不运行rollout或pred_x0。
- 保留Stage2区域加权：源/目标GT VAE差异，boost1、50%/90%分位数。原生flow-matching、timestep_shift4，MSE系数1、CE系数0.25；此数据CE实际为0。
- LR `3e-4 → 3e-5`，101-update warmup，cosine单次下降；AdamW beta0.9/0.95、eps1e-15、weight_decay0、梯度裁剪1。
- 条件dropout全部0，无EMA。VAE480/ViT448分桶，12fps，max_duration6，max_frames121，latent_patch(1,1,1)，max_latent64，max_tokens65536，flex attention。
- 4×H200 HYBRID_SHARD，replicate1/shard4，CPUoffload关闭；每卡microbatch1，累计8，有效batch32。
- 3000 optimizer updates，24,000 microbatches/rank，96,000次目标暴露，约6.54次加权数据遍历。
- 每100 completed optimizer updates保存、结束再保存，最近4份完整正式checkpoint；Slurm终止不额外保存。旧600间隔作业已取消，不从其smoke续跑。
- W&B独立Run ID与本地目录，逐optimizer step记录标量；不上传媒体、checkpoint或代码。仅testqueue，每次最多18小时，手动续跑。

学习率日志明确区分本次更新使用的 `train/lr` 和下一次使用的 `train/next_lr`。warmup的第1次更新实际LR为0，不能只用step1验证非零权重保存；启动检查因此使用step2与step3。

### 2026-09-08：保留最近4份与存储估算

用户将两臂`checkpoint.keep_last_complete`从1改为4；100步间隔、结束额外保存、完整续训状态、其他训练参数、restart1目录/W&B身份及启动命令不变。第5份完整保存并原子落盘后才删除最早的一份；最终checkpoint也纳入最近4份，不额外永久保留第5份。本次只改配置和回归测试，没有改训练/保存实现或删除既有产物。

00:02核验当前队列没有Stage6两臂，两个restart1输出目录尚不存在，因此本修改供新任务启动时读取，没有对运行进程热修改。使用旧四卡启动smoke的`continuous/checkpoints/0000003`实测文件长度（十进制GB，正式同拓扑检查点应接近）：

| 实验 | 纯FP32 LoRA权重 | 单份完整续训checkpoint | 4份完整checkpoint |
| --- | --- | --- | --- |
| S6-1 理解+生成 | 960,717,544 bytes ≈ 0.96GB | 3,867,282,949 bytes ≈ 3.87GB | 15.47GB |
| S6-2 仅生成 | 481,716,824 bytes ≈ 0.48GB | 1,939,249,117 bytes ≈ 1.94GB | 7.76GB |

两组各4份合计约23.23GB，不包含共享base、旧smoke/日志。完整checkpoint比adapter大，因为还包含Adam moments，以及checkpoint-v5在optimizer DCP中携带的live参数副本、scheduler/RNG/cursor。原子保存先写新checkpoint，合并DCP时还有临时文件，之后才轮换删除，因此保存期间峰值会高于23.23GB；建议为两臂正式checkpoint及保存临时空间合计预留约40GB。共享挂载当时`df -h`显示318GiB可用，此数不是独立用户quota保证。

105项Lance CPU测试通过，新增真实小模型连续保存5次、只保留最近4份的回归；旧非零adapter恢复测试继续通过。两份fresh-launch dry-run及132项核心CPU测试通过，目录/输出清单重建，114文档/663链接、404脚本/5输出范围独立与跨层审计均零错误/警告，`git diff --check`通过。文档维护技能同步Technical、当前Plan/Status、消融与决策日志，并保留旧事故当时的keep1记录。新任务及GPU Gate未执行，本项只验证配置/CPU保留逻辑，不将其记为GPU训练或视觉质量通过。

## 实现入口和数据恢复

| 文件 | 责任 |
| --- | --- |
| [datamake_stage2_lora_train.py（已退役，历史补丁）](../patches/legacy/0014-datamake-stage2-prefix-branch-lora.patch) | 复用Stage2参数映射、模型/数据编码和区域loss；实现8次累计与完整训练循环 |
| [datamake_branch_lora.py](../lance/train/datamake_branch_lora.py) | 两种LoRA范围、对齐初始化、base先加载的推理hook |
| [datamake_stage2_lora_checkpoint.py](../lance/train/datamake_stage2_lora_checkpoint.py) | 私有导入已验证checkpoint-v5，只替换branch config reader，不改Stage5全局实现 |
| [datamake_stage2_lora_data.py](../lance/train/datamake_stage2_lora_data.py) | 单前缀map-style打包、绝对已消费microstep游标、确定性预处理 |
| [run_datamake_stage2_lora_training.py](../scripts/run_datamake_stage2_lora_training.py) | 短CLI、输入检查、同任务GPU恢复Gate、正式启动/手动恢复 |
| [inspect_datamake_stage6_runtime.py](../scripts/inspect_datamake_stage6_runtime.py) | 无GPU的真实权重头拓扑、视频打包、spawn预取恢复检查 |
| [run_datamake_lora_visual_sanity.py](../scripts/run_datamake_lora_visual_sanity.py) | 按adapter schema选择Stage5/Stage6加载器，标准30-step推理保持不变 |
| [0014 patch](../patches/legacy/0014-datamake-stage2-prefix-branch-lora.patch) | 外层Git保存新增clone训练代码；依赖既有0001～0013 |
| [0015 patch](../patches/legacy/0015-stage6-save-at-optimizer-boundary.patch) | 新进程支持在optimizer边界响应SAVE_AND_STOP，成功完整保存后退出 |

梯度为 `(1/8) × Σ grad(Stage2跨卡区域加权microbatch loss)`；不是32个视频无条件严格等权（区域/token归一化仍保留）。每8次反向后才执行一次clip/optimizer/scheduler/zero_grad。每次反向仍同步FSDP，不使用会保留完整梯度的no_sync。

数据沿用Stage2 data_seed2081的rank/shard分配和两个逻辑worker交替行顺序，在各shard结尾循环。预处理随机种子按data_seed、rank、绝对microstep固定，不依赖物理worker或预取进度；与旧Stage2的worker-RNG轨迹不承诺逐位一致，但两组新实验输入一致。checkpoint保存 `next_microstep=completed_steps×8`，恢复直接从此索引继续，无需跳过或重放24,000条缓存。损坏/超长样本会明确报错，不静默改变样本日程。

checkpoint-v5保存live adapter、DCP Adam、scheduler、每rank RNG和游标，不重复基座。部分末层UND输出可能没有loss路径，允许对应adapter/Adam保持0；给非空本地参数显式分配准确Adam step0状态，避免未使用参数的DCP字段不齐，不伪造optimizer更新。推理加载顺序是base → 同范围LoRA → adapter。

## 提交、自动GPU检查与恢复

两臂800续跑已由用户提交，已执行命令及状态见[恢复记录顶部](./datamake_stage6_checkpoint_rescue_20260907.md)，不要重复提交。下列`none`命令仅记录9月7日首次启动方式，**当前不要执行**：

```bash
sbatch --export=ALL,RESUME_FROM=none 10_research/model_experiments/lance/jobs/datamake_stage6_lora_both_branches.sbatch
sbatch --export=ALL,RESUME_FROM=none 10_research/model_experiments/lance/jobs/datamake_stage6_lora_freeze_und.sbatch
```

每个任务先运行同一4卡配置的恢复检查：

1. 共同官方基座，连续训练3个optimizer updates；
2. 重新初始化，训练2个updates后保存；
3. 新进程恢复step2，再训练step3；
4. 比较全部adapter、Adam、scheduler、四rank RNG、数据游标、step3样本与loss；检查step2全部256个GEN LoRA-B非零，双分支实验还要求UND有真实更新；
5. 通过后才从全新基座启动正式3000-step训练。失败自动退出，不继续正式训练。

使用实际累计8、warmup101和3000-step调度，smoke只提前结束，不缩短scheduler horizon。比较预设atol1e-7、rtol1e-5，同时报告bitwise数量；通过报告保存在 `startup_validation/passed-<contract hash>.json`。启动检查不写正式W&B，不计入3000步；其证据checkpoint与正式保留策略分目录。未改变代码/配置的后续恢复可以复用已通过报告。

手动从各自最近完整checkpoint恢复：

```bash
sbatch --export=ALL,RESUME_FROM=latest 10_research/model_experiments/lance/jobs/datamake_stage6_lora_both_branches.sbatch
sbatch --export=ALL,RESUME_FROM=latest 10_research/model_experiments/lance/jobs/datamake_stage6_lora_freeze_und.sbatch
```

不要同时提交同一臂的多个实例。不同实验可同时排队，不借用其他分区。此次已提交各自800恢复，完整状态继续原3000步调度，不重新warmup；未保存进度丢弃。旧600配置没有正式checkpoint，不做状态迁移。

## 输出与日志

每臂输出位于 `outputs/training_runs/<profile.run.run_name>/`，现行名称以`_restart1`结尾，W&B Run ID对应以`-restart1`结尾；启动时创建，旧无后缀目录保留：

- `configs/profile.json`、`lora_targets.json`：实际配置与目标。
- `checkpoints/0000100/`等：最近4份完整正式状态；当前固定恢复点由[恢复记录](./datamake_stage6_checkpoint_rescue_20260907.md)维护。
- `metrics.jsonl`及`wandb/`：逐步标量和W&B本地缓冲。
- `startup_validation/`：3-vs-2+resume证据，仅此目录保留启动检查的3份checkpoint，不受正式keep4影响，未授权前不自动删除。
- stdout/stderr：`outputs/slurm_logs/stage6_lora_both_<jobid>.out/.err`与`stage6_lora_freeze_und_<jobid>.out/.err`。

关注 `train/mse`（优化的区域加权MSE）、`train/mse_unweighted`、`train/loss`、`train/grad_norm`、本次/下次LR、`perf/step_time`、目标吞吐和峰值allocated/reserved显存。W&B以optimizer_step作横轴，恢复后的重算步可能有重复x值，不删除云端历史。

## 验证边界

最初实现阶段已完成（下列为历史CPU证据，实时状态见本节末尾）：

- 102项Lance CPU unittest通过（新增7项运行时测试，含两种scope的非零step2保存/恢复第3步、未使用UND Adam state、base先加载推理、累计均值和数据游标；另有8项两臂配置测试）。
- 官方权重头的508模块/240,146,432个LoRA参数实际挂载形状核对通过；不分配整个基座权重。
- 真实媒体microstep16/17由新map-style入口打包通过；均一source/一target，实际VAE视频为3×57×352×624（480是bucket配置，并非固定输出宽高）。双spawn worker恢复的文本和视频与直接索引读取逐tensor相同。首次沙箱内检查受本机IPC socket权限限制，已终止；同一只读CPU检查在沙箱外通过，没有使用GPU。
- 两份launcher dry-run、实际HF dataclass参数解析、Python编译、Slurm bash语法和0014 reverse-check通过。
- Stage5 A/B的21/22份冻结source哈希仍匹配；没有改旧训练实现/配置或已有checkpoint。
- 项目核心132项CPU unittest通过（文档22、dataset30、Unreal80）；xks_lance无pytest，使用项目现行unittest入口。
- Catalog/Output Inventory已重建；114份文档全部可达、660条链接、404个脚本与5个输出范围审计通过，各独立子系统及跨层检查零错误/警告；`git diff --check`通过。文档技能将本轮状态限定为“实现/CPU已验证、GPU pending”，没有将L06/L08或WF-90状态误晋升。

旧600首存事故、restart1四卡Gate及400恢复均有保留证据；后续Jobs125433/125434已训练并完整保存到800，现用户提交800续训。新的[800步两臂视觉检查](./datamake_stage6_step800_visual_sanity_20260909.md)复用标准30-step推理，真实结果以报告为准。手动SAVE_AND_STOP GPU退出仍未执行；L06/L08保持in_progress，WF-90不变。

前序清理仅删除经完整替代核验的两份旧索引，保留当前chain、sharded8和Stage2 R5×3数据；历史清单见[清理记录](./datamake_lance_storage_cleanup_20260906.md)。本轮实现没有清理任何模型、数据或既有训练产物。

2026-09-09用户另行授权[PEFT/DDP 性能优化](./datamake_ddp_peft_optimization_20260909.md)：保留 Stage6 两臂语义，独立后端、Run 与完整状态迁移。实现和 CPU 检查已完成，四卡 Gate 待执行；原任务/恢复合同不改动，质量 Gate 不因此关闭。
