# Stage6：checkpoint 事故、restart1 训练与恢复记录

> 最新状态（2026-09-09 20:32）：用户要求暂停126188/126189；两臂已通过SAVE_AND_STOP完整保存900/825并正常退出，不自动续跑。见[暂停与速度短测](./datamake_lora_short_speed_20260909.md)。下文800续跑调度为历史记录。

> 日期：2026-09-07，时间均为Asia/Singapore。  
> 状态：`restart1_resume800_submitted`（2026-09-09更新）。  
> Technical所有者：[训练接入§6.12](../training_integration.md)。  
> 9月7日旧任务抢救未成功；后续restart1已取得完整正式checkpoint。当前两臂已由用户提交800步续跑；下方400恢复、旧事故和从头命令仅作历史。

## 当前结论：2026-09-09从800步续跑，用户已提交

Jobs125433/125434从各自400正常训练后，均在9月9日14:51达到18小时上限，Slurm为TIMEOUT。最后完成877/882更新，最新完整checkpoint均800；801～877共77步、801～882共82步未保存，恢复需重算。现各自保留500/600/700/800，旧100～400按keep4轮换，不再作为当前恢复入口。

两份800的complete标记、必需文件大小、5个非空optimizer DCP文件、optimizer边界游标`next_step=800/next_microstep=6400`及当前profile/source合同一致性通过；显式相对路径恢复dry-run通过，原GPU Gate仍可复用。用户已提交S6-1 Job126188与S6-2 Job126189；15:49检查分别PENDING(Resources)/PENDING(Priority)，资源与脚本正确，尚无启动日志。不要再次提交同一臂；等实际启动后确认800恢复及801更新。

已交付的命令记录（不是让用户重复提交）：

```bash
cd /scratch/prj0000000275/jcy/xks/DataMake/10_research/model_experiments/lance
sbatch --export=ALL,RESUME_FROM=outputs/training_runs/datamake_dialogue_stage2_recipe_lora_r64_both_branches_v1_4xh200_restart1/checkpoints/0000800 jobs/datamake_stage6_lora_both_branches.sbatch
sbatch --export=ALL,RESUME_FROM=outputs/training_runs/datamake_dialogue_stage2_recipe_lora_r64_freeze_und_v1_4xh200_restart1/checkpoints/0000800 jobs/datamake_stage6_lora_freeze_und.sbatch
```

恢复全部LoRA/Adam/scheduler/RNG/cursor，继续原3000步总预算，下一次定期保存900；累计8、LR和100/keep4/final-save、restart1目录/W&B身份均不变。仍只用testqueue，每臂4H200、每次最多18小时。助手没有代提交或修改训练；同日独立GPU上的[800步视觉检查](./datamake_stage6_step800_visual_sanity_20260909.md)不干扰上述队列任务。

## 历史：2026-09-08暂停，固定从400步恢复

用户要求停止现有训练并给出从400步恢复的指令。先查队列确认仅124654仍运行，然后执行`scancel 124654`；没有提交新任务，也没有触发额外保存或删除文件。

| 臂 | Job | Slurm最终状态 / 结束时间 | 最后完成更新 | 固定恢复点 | 舍弃的已完成更新 |
| --- | --- | --- | --- | --- | --- |
| S6-1 理解+生成LoRA | 124653 | TIMEOUT / 18:14:43 | 457 | 400 | 401～457，共57步 |
| S6-2 仅生成LoRA | 124654 | CANCELLED / 19:27:50 | 430 | 400 | 401～430，共30步 |

时间均为2026-09-08 Asia/Singapore。两Job已离开`squeue`；TIMEOUT即使显示ExitCode0:0也不是完成3000步。`metrics.jsonl`保留旧记录，内存中的未保存权重不可恢复。

恢复准备核验：两臂各有100/200/300/400四份完整正式checkpoint；400的complete标记、必需文件大小、5个非空optimizer DCP文件通过，`completed_steps=next_step=400`、`next_microstep=3200`且处于optimizer边界。当前profile与12份implementation source生成的contract和各自400保存合同完全相同；两条显式400恢复dry-run通过，已有同合同四卡启动Gate可复用，不需重新做启动smoke。没有修改训练代码、profile、数据、基座或已有checkpoint；本次并非重新执行400步的四卡恢复数值对照。

本次还读取两份400的adapter与scheduler：S6-1共1016个有限tensor，508个LoRA-B中503个非零（末层5个UND无loss路径，属已知预期）；S6-2共512个有限tensor，256个LoRA-B全部非零。两者scheduler.last_epoch=400、下一次LR均为0.000292974998213196。本次不重新合并/逐tensor比较全部Adam DCP或执行GPU恢复。

在Lance工作目录执行，两条命令中的相对checkpoint路径与sbatch脚本内部`cd`一致：

```bash
cd /scratch/prj0000000275/jcy/xks/DataMake/10_research/model_experiments/lance

sbatch --export=ALL,RESUME_FROM=outputs/training_runs/datamake_dialogue_stage2_recipe_lora_r64_both_branches_v1_4xh200_restart1/checkpoints/0000400 \
  jobs/datamake_stage6_lora_both_branches.sbatch

sbatch --export=ALL,RESUME_FROM=outputs/training_runs/datamake_dialogue_stage2_recipe_lora_r64_freeze_und_v1_4xh200_restart1/checkpoints/0000400 \
  jobs/datamake_stage6_lora_freeze_und.sbatch
```

恢复包括LoRA、Adam、scheduler、四rank RNG和已消费数据游标；下一次完成更新标为401，继续原3000步总预算（剩2600），不重置warmup。仍为testqueue、每臂单节点4H200、最多18h；每100步保存、keep4、最终保存，下一次定期保存500。使用原restart1输出目录与稳定W&B Run ID；本地指标追加，W&B使用自动递增内部日志步并以`optimizer_step`作横轴，重算401之后会出现重复横坐标，不覆盖/删除云端旧数据。stdout/stderr分别写入原`outputs/slurm_logs/`中的新Job ID文件。

真实四卡SAVE_AND_STOP请求保存退出仍未执行；本次用户指定从400恢复，因此直接取消，不把该路径写成已验证。L06/L08仍in_progress，WF-90 released不变。

本轮验证：9项Stage6运行时CPU测试、132项项目核心CPU测试通过（文档22/dataset30/Unreal80）；xks_lance无pytest，按项目既有方式用unittest运行。两份sbatch语法和`git diff --check`通过，相对路径形式恢复dry-run也通过。文档维护技能同步Technical、Plan、Status、Handoff和消融导航；Catalog/Output Inventory重建，114文档可达、663链接、404脚本、5输出范围，各独立子系统及跨层审计零错误/警告。未重新执行全部Lance测试或四卡400恢复，这是恢复准备，不是新训练已启动或视觉质量通过。

## 历史：9月7日用户决定取消并从头训练

2026-09-08后续决定：两臂改为每100步保存、保留最近4份，结束额外保存仍纳入这4份；准确存储估算和当前配置规则由[Stage6配方说明](./datamake_stage6_stage2_lora_preparation_20260907.md)维护。下文9月7日的keep1与验证条目是当时记录，不是最新保留策略。

2026-09-07 23:47:48（Asia/Singapore），按用户明确要求执行`scancel 124136 124137`，`sacct`确认两者均为CANCELLED。取消后本地日志最后完成更新为S6-1第470步、S6-2第385步；两者均无正式checkpoint，因此当前模型/Adam/RNG/游标的未保存进度已经丢失，不能从这些步续跑。没有删除旧目录、日志、W&B Run或启动smoke证据，也未取消其他作业。

9月7日重训准备时，两份profile保持100步保存、keep1和final-save，仅将本地`run.run_name`追加`_restart1`、W&B `run_id`追加`-restart1`，避免从0重训混入旧曲线与指标。新目录尚未创建，按需由启动器生成；官方base、fresh LoRA/Adam/scheduler、GT前缀、累计8、LR3e-4→3e-5和3000更新均不变。旧运行快照不改写，不迁移已不存在的正式恢复状态。

在DataMake根目录，由用户执行以下两条**从头启动**命令：

```bash
sbatch --export=ALL,RESUME_FROM=none 10_research/model_experiments/lance/jobs/datamake_stage6_lora_both_branches.sbatch
sbatch --export=ALL,RESUME_FROM=none 10_research/model_experiments/lance/jobs/datamake_stage6_lora_freeze_und.sbatch
```

显式`none`避免继承终端中可能残留的`RESUME_FROM=latest`。每项仍限定testqueue、单节点4×H200、最多18h；各自在同一作业内重新做当前合同的四卡3-vs-2+resume检查，通过后才从0开始正式训练。第一次正式保存应在第100个optimizer更新，按旧实测约4小时（含启动检查的粗估，非新节点保证）；首存完成后检查完整标记及adapter/optimizer一致性。未来续跑使用同一restart1身份和`RESUME_FROM=latest`，不能重复提交正在运行的同一臂。

新SAVE_AND_STOP入口保留；真实四卡请求退出路径仍待验证。本轮只取消旧作业、准备配置和检查命令，没有提交新训练、运行新GPU smoke或上传新W&B Run。取消/重训记录已同步至Technical、Plan、Status和消融登记，不将CPU检查视为重训成功或质量通过。

restart1准备核验：104项Lance与132项核心CPU测试通过；两臂显式`--resume-from none --dry-run`均通过且要求新的启动Gate，命令没有任何resume checkpoint参数。两份profile相对旧运行快照只差保存间隔、运行目录名、W&B Run ID三个字段；新输出目录尚不存在。Slurm bash语法、`git diff --check`通过；两旧作业已不在`squeue`中。目录/输出清单重建，114文档/663链接、404脚本/5输出范围，各独立与跨层审计零错误/警告。

## 历史运行证据与原因（取消前快照）

2026-09-07 22:03附近，读取Slurm状态、两臂`metrics.jsonl`、启动检查报告及正式checkpoint目录：

| 实验 / Job | 节点 | 完成更新 | 最近30步均值 | 18h截止 | 正式checkpoint |
| --- | --- | --- | --- | --- | --- |
| S6-1 / 124136 | JDS9B74 | 422 | 132.97秒 | 09-08 00:00:41 | 无 |
| S6-2 / 124137 | H64Y574 | 338 | 135.74秒 | 09-08 02:56:08 | 无 |

两份旧进程内配置均为每600次optimizer更新保存，最近1份，3000步结束再存，不在Slurm终止时额外保存。按实测均值，两组都无法在本次18h内达到第600步。启动准备没有用实际smoke耗时核验首存是否落在时限内，这是本次配置审查遗漏；训练正常更新不代表有可恢复结果。

运行目录均在`outputs/training_runs/`：

- `datamake_dialogue_stage2_recipe_lora_r64_both_branches_v1_4xh200/`
- `datamake_dialogue_stage2_recipe_lora_r64_freeze_und_v1_4xh200/`

对应stdout/stderr在`outputs/slurm_logs/stage6_lora_both_124136.out/.err`和`stage6_lora_freeze_und_124137.out/.err`。日志与W&B标量不包含足够恢复模型的权重状态。

两臂各自的四卡3-vs-2+resume启动Gate确实通过，不再标为pending：

- S6-1：`startup_validation/passed-9ca640065474c243a3ce1964d9fe377dafe63536af8bfde0875e49dfcadd0b9e.json`，1016/1016 adapter、4064/4064 Adam tensor bitwise相同；GEN 256/256 LoRA-B非零，UND 247/252非零，其余是没有loss路径的末层模块。
- S6-2：`startup_validation/passed-328729f282c58cc4eab98b5b20d7182baf72e70c072ff01b3612d8fb2bc5ffa2.json`，512/512 adapter、2048/2048 Adam tensor bitwise相同，GEN 256/256 LoRA-B非零。
- 两组scheduler、cursor、四rank共8个RNG tensor和step3各rank样本/loss均一致。此证据只覆盖当时600步配置与旧入口的启动检查。smoke的step2/3不是当前几百步训练的恢复点。

## 历史抢救尝试与权限边界

旧trainer没有signal handler、手动补存接口或profile热加载；代码和JSON在启动时已读入。直接修改磁盘不会让现有进程执行新逻辑，也不能用SIGTERM/SIGUSR1猜测触发保存。

在原allocation内用`--overlap --exact --nodes=1 --ntasks=1 --cpus-per-task=1 --gres=none`核验进程，不申请额外GPU。确认：

- 124136 ranks：2496026、2496027、2496028、2496029。
- 124137 ranks：1532838、1532839、1532840、1532841。
- 两节点均有GDB，`/proc/sys/kernel/yama/ptrace_scope=1`。
- 各选一个已确认rank，仅做一次限时15秒的只读GDB attach / info threads / detach；两次都报`Could not attach to process`、`ptrace: Inappropriate ioctl for device`，exit1，没有成功附加或执行任何进程内代码。不能只凭errno断言唯一原因就是Yama。

曾评估“受控调试向主解释器排队一个小回调，仅修改共同未来optimizer步的保存条件，由正常主循环执行完整保存”的可能性。CPython3.11的[Py_AddPendingCall说明](https://docs.python.org/3.11/c-api/init.html#c.Py_AddPendingCall)表明回调在主解释器线程的字节码边界、持有GIL时执行，但不保证及时性；[GDB文档](https://sourceware.org/gdb/current/onlinedocs/gdb.html/Calling.html)也警示inferior函数调用的副作用和卡死风险。此路线仅为未验证设想：只读attach前提失败，因此连独立CPU原型都没有继续，更没有用于训练。不能宣称该方法可靠或管理员一定能救回。

没有更改ptrace策略、提权、绕过限制、延长18h或操作其他作业。已请求用户联系管理员，评估仅对上述作业进行授权、受控的补存是否可行。没有可用checkpoint前不主动取消；也不让任务超过既定时限。若无管理员可用方案，现有内存状态在作业终止后将丢失。

## 取消前已落盘的修正（未作用于旧进程）

两份[Stage6 profile](./datamake_stage6_stage2_lora_preparation_20260907.md)只将`checkpoint.completed_step_interval`从600改成100；仍保留最近1份完整正式checkpoint、结束额外保存、adapter-only基座不重复、完整Adam/scheduler/RNG/cursor。学习率、累计8、3000更新、数据、LoRA范围和loss均未改。

[0015 patch](../patches/legacy/0015-stage6-save-at-optimizer-boundary.patch)补充简单的`SAVE_AND_STOP`入口：

1. 用户在**未来使用新代码的训练**的Run Root创建空文件`SAVE_AND_STOP`。
2. trainer只在完成累计8、optimizer/scheduler更新及zero_grad后，由rank0检查文件；广播同一停止决定给所有rank。
3. 强制调用既有checkpoint-v5完整保存；成功返回后才删除请求文件、同步并退出。
4. 不在signal handler内调用FSDP，也不自动处理Slurm终止信号。请求应提前于时限发出，留出当前step和完整保存时间；保存未成功时不把请求当作完成。

未来使用方法（`RUN_DIR`须替换为已确认使用新代码的确切运行目录）：`touch RUN_DIR/SAVE_AND_STOP`。本次没有创建该请求，因为124136/124137不认识它。标准续跑仍是各自sbatch的`RESUME_FROM=latest`，前提是存在兼容的完整正式checkpoint；不能现在照此命令重交或将smoke路径冒充latest。

profile全文件hash及trainer/checkpoint-bridge source hash已变化，因此现有Gate报告不会自动复用于新合同。若管理员救回旧进程checkpoint，必须先保留原`configs/profile.json`和checkpoint contract，单独审查仅保存策略/控制入口变更的续跑兼容性；本次未删除hash校验、改写旧合同或实现未经验证的迁移。未授权从零重启覆盖当前运行记录。

## 验证与待办

- 103项Lance CPU unittest通过，包括100-step策略、rank0单一文件决定、其他rank仅接收广播、保存前不消费请求；已有两种LoRA范围的非零保存/恢复测试继续通过。
- 0015 reverse-check、Python编译与`git diff --check`通过，0014保留原始版本；Stage5 A/B的21/21及22/22冻结源hash匹配，未修改旧checkpoint。两臂磁盘profile与实际Run快照的唯一字段差异均为600→100。
- 新控制入口的真实四卡保存退出尚未验证；本轮没有新GPU smoke。CPU/mock通过不等于抢救成功。
- 项目核心132项CPU unittest通过（文档22、dataset30、Unreal80）。Catalog/Output Inventory重建，114份文档均可达、663条本地链接、404脚本/5输出范围，各独立子系统与跨层审计均通过，零错误/警告。文档维护技能把真实GPU启动证据、当前救援阻塞及后续CPU修正分开记录；没有把L06/L08或质量Gate误标完成。

9月7日当时的下一步是由用户从头提交restart1；现已执行，当前行动以上方9月8日固定400恢复说明为准。原抢救路线以用户接受未保存进度丢弃而结束，不是抢救成功；L06/L08保持`in_progress`，WF-90发布状态与数据不变。

2026-09-09用户另行授权[PEFT/DDP 性能优化](./datamake_ddp_peft_optimization_20260909.md)：保留 Stage6 两臂语义，独立后端、Run 与完整状态迁移。实现和 CPU 检查已完成，四卡 Gate 待执行；原任务/恢复合同不改动，质量 Gate 不因此关闭。
