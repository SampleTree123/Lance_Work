# DataMake Stage 5 单步 `pred_x0` 历史训练实现与 Smoke（2026-09-04）

> 状态：`job_123628_cancelled_by_user_latest_checkpoint800_visual_partial`  
> 冻结配置：[`../configs/datamake_dialogue_one_step_x0_lora_r64_v3.json`](../configs/datamake_dialogue_one_step_x0_lora_r64_v3.json)  
> 对照配置：`../configs/datamake_dialogue_online_rollout_lora_r64_v2.json`（历史文件已于2026-09-11清理）  
> 结论边界：one-step 路径已通过连续 3-step 与 2-step-save/resumed-step3 四卡逐 tensor Gate，并显著缩短 step time；正式 Job `122959` 的首个 step50 checkpoint 已通过 adapter、AdamW、scheduler、cursor 与 RNG 深审计。step400 已经用户复核为视觉效果一般；A 当前停止于第二段，尚未完成 1,800-step 训练或 held-out 质量验收。

## 1. 修改目的与严格边界

Stage 4 每个中间 turn 都执行一次独立 30-step diffusion rollout，训练时间主要消耗在生成历史视频。Stage 5 按用户确认只替换历史构造方式，其他训练规则保持不变：

- 同一份 3,600 条一行一链数据和 4 Epoch / 1,800 optimizer steps；
- 同一 generation-only LoRA `r64 / alpha64 / dropout0`，从官方 Lance 基座和 fresh adapter 开始；
- 同一 4×H200、gradient accumulation 2、每个目标视频等权；
- 同一 AdamW、warmup20、cosine `1e-4 → 1e-5`；
- condition dropout、CE、区域损失和 EMA 仍为 0/关闭；
- checkpoint v5 每 50 completed steps 保存，最近 4 份，另存最终 step；
- held-out 正式推理仍使用标准多步采样，本修改不改变推理代码。

变化仅发生在尚有下一轮的目标视频上。Lance 的原生 flow-matching forward 已构造：

```text
z_t = (1 - t) * x0 + t * epsilon
velocity_target = epsilon - x0
```

模型输出 `pred_velocity` 后，训练器复用同一次 forward 估计：

```text
pred_x0 = z_t - t * pred_velocity
```

`pred_x0` 立即 detach，按本轮 target 的 latent `T×H×W` 还原并经冻结 VAE decode 成 CPU FP16 视频。下一轮继续走既有动态输入适配器：所有历史 `pred_x0` 视频进入 ViT，最近一段同时重新 VAE encode 为 direct source。没有额外 diffusion step、CFG 双分支、KV cache 或临时 MP4。

## 2. 语义解释

这一方法比完整 rollout 快，但不是完整推理分布的等价替代。它从“对 rendered GT 加噪后的 `z_t`”出发做一次模型去噪，因此历史带有 GT 锚点；随机训练 timestep 越小，输入越接近 GT，越大则更依赖模型预测。它适合快速验证“模型输出误差进入下一轮后是否仍能学习”，但不能单独证明模型能承受标准 30-step 自回灌历史。

目标监督本身未变：每轮仍用 Lance 原生 latent velocity MSE 对 rendered GT 训练，`pred_x0` 只作为后续轮条件，且梯度不会跨轮传播。最终必须把 Stage 5 与 Stage 4 full rollout 作为 history-source 消融，并用标准 30-step held-out 多轮推理比较视觉效果。

## 3. 实现入口

| 文件 | 作用 |
|---|---|
| `lance/modeling/lance/lance.py` | 可选返回当前 MSE forward 已有的 `z_t`、预测 velocity 和 timestep；默认路径输出与 loss 不变 |
| `lance/train/datamake_online_rollout.py` | 注册 `one_step_x0_history` 运行契约，并强制 diffusion steps=0、KV cache=false |
| `lance/train/datamake_online_rollout_lora_train.py` | 计算/解码 detached `pred_x0`，复用原有链内 ViT/VAE 历史与 checkpoint 主循环 |
| `scripts/run_datamake_online_rollout_lora_training.py` | 校验 v3 profile、实现/data/base hash 和正式授权 |
| `configs/datamake_dialogue_one_step_x0_lora_r64_v3.json` | 1,800-step 正式冻结候选 |
| `jobs/datamake_dialogue_one_step_x0_lora_r64_v3*.sbatch` | `testqueue` 单节点四 H200 的正式/Smoke 入口，最长分别 18h/2h |
| `patches/legacy/0013-datamake-one-step-x0-history.patch` | 相对 checkpoint-v5 Stage 4 实现的 one-step 历史补丁 |

## 4. 静态与 CPU 验证

- 新增纯张量代数测试，精确验证 `pred_x0 = z_t - t * pred_velocity`；
- v3 profile 测试固定 steps=0、CFG1 等价单 conditional forward、KV cache=false 和正式 fail-closed；
- Lance 完整 DataMake 测试共 74 项通过；
- Python compile、Shell `bash -n`、JSON 解析、launcher dry-run 和 `git diff --check` 通过；
- `0013` 可从当前工作实现干净 reverse-check，补丁包含 Lance core 与两个训练文件的全部 Stage 5 改动。

## 5. 四卡连续 Smoke 与吞吐

连续 3-step Job `122843` 在 `testqueue` 单节点 4×H200 完成且 ExitCode=0。三个 optimizer step 均正常完成 forward、backward、LoRA update 和最终 checkpoint：

| Step | MSE | Targets | Histories | Grad norm | LR | Step time |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 0.184559 | 28 | 20 | 0.023041 | 5e-6 | 171.19 s |
| 2 | 0.198563 | 28 | 20 | 0.036077 | 1e-5 | 138.36 s |
| 3 | 0.168077 | 24 | 16 | 0.023210 | 1.5e-5 | 115.41 s |

同一 schedule 的 Stage 4 30-step full rollout 前三步为 `311.78 / 279.55 / 221.35 s`。平均值从 `270.89 s/step` 降到 `141.65 s/step`：

```text
speedup = 1.91x
step-time reduction = 47.7%
```

按前三步均值机械外推，1,800 steps 约需 70.8 小时，即约四个 18 小时 Slurm segment；这只是启动段估算，正式 steady-state 和 50-step checkpoint 开销仍需用实际日志更新。

## 6. 保存恢复 Gate

Job `122844` 从共同初始状态完成 2 steps 并保存，Job `122845` 从其 `0000002` checkpoint 恢复，日志确认 `starting_step=2` 后只执行 step3；两者均为 `COMPLETED/0:0`。与 Job `122843` 的连续 step3 深比较得到：

- 512/512 个 LoRA A/B tensor bitwise 相同，最大差 `0.0`；
- 2,048/2,048 个 Adam/custom optimizer tensor bitwise 相同，最大差 `0.0`；
- 8/8 个 per-rank RNG tensor bitwise 相同，scheduler 与 trainer cursor 相同；
- step3 的 MSE `0.168077`、grad norm `0.023210`、LR `1.5e-5`、24 targets、16 histories 与全部 `pred_x0` latent telemetry 相同；
- step2 prefix checkpoint 的 256/256 个 `lora_B` 均已脱离零初始化。

机器可读结果见 [`datamake_stage5_one_step_x0_resume_smoke_audit_20260904.json`](./datamake_stage5_one_step_x0_resume_smoke_audit_20260904.json)。该 Gate 已关闭此前 nested-FSDP 保存恢复风险；v3 profile 状态更新为 GPU smoke 已通过，但 `training_authorized` 仍为 `false`，正式 1,800-step 训练必须等待用户单独确认。

三个 GPU Job 运行时绑定的 profile SHA-256 为 `04c42bfec13798d70ab3a15d76a05972292e2270ba86e70de36e16b8cb3fbfa5`。Gate 通过后将 profile 状态从 smoke pending 改为 smoke passed，并补登记已经执行的 `0013` patch 哈希。

### 6.1 启动前代码复查修正

后续静态复查发现两个真实代码问题，均已修正：

- Lance 默认 `forward` 只返回原有 `mse/ce/frame_mse/total_mse_tokens` 四个字段；三个 flow 中间量仅在 `return_flow_intermediates=True` 时追加，避免破坏原 `unified_train` 的 loss consumer。
- 真正决定 `z_t` 分布的 `training_args.timestep_shift` 已固定为 `4.0`，并要求它与 profile 的 `optimization.timestep_shift`、`rollout.timestep_shift` 三者一致。

授权状态测试改为分别构造临时 pending/authorized profile，不再依赖权威 profile 当前处于哪个阶段。profile 中未产出证据的 `predicted-x0 history video sanity review` 已从正式启动前硬门槛移除；它不是训练数值正确性的必要条件，视觉质量仍由正式训练早期 checkpoint 的标准 30-step held-out 自回灌推理判断。

这些改动没有改变四卡 smoke 实际走过的 `return_flow_intermediates=True` one-step 数值分支、模型参数、数据、loss、optimizer、LoRA 或 checkpoint，因此不重复消耗 GPU。74 项 Lance unittest、Python compile、profile source-hash dry-run、`git diff --check` 和更新后 `0013` reverse-check 均通过。待授权 profile SHA-256 为 `3163ecd4d913d9fae5dcc5cdb4445d78a066975a035403a494555955956e8083`，更新后 `0013` SHA-256 为 `e21ff5517c5b9e4dafecbb2417262b984a68ac073473b0e447951451619f0ecb`。

2026-09-04 用户明确授权正式训练后，profile 仅把状态切换为 `training_authorized`、`training_authorized=true`，其余字段不变；授权态 SHA-256 为 `315a8ef1cec83a16e3ab6f26c01de2d85e298c6145ecf327e85ef4a588637f7d`。完整模型、数据和 implementation source-hash dry-run、9 项聚焦测试及 Slurm 语法通过。正式 Job `122959` 于 `19:03:02+08:00` 在 `BFS9B74` 获得 `testqueue` 单节点四 H200；launch manifest 确认 `resume_from=none`、授权 profile hash、官方 Lance 基座、fresh zero-output LoRA、W&B online 和 1,800-step 调度均正确。前两个 optimizer steps 连续完成：step1 `mse=0.184559 / grad_norm=0.023041 / 174.50s`，step2 `mse=0.198563 / grad_norm=0.036077 / 138.57s`，与 smoke 对应数值一致，日志没有 OOM、NaN、traceback 或运行时错误。正式启动 Gate 因此通过；step50 checkpoint 与视觉质量仍待后续验证。

### 6.2 正式 step50 checkpoint 审计

Job `122959` 的首个正式 checkpoint `checkpoints/0000050/` 已完整落盘并通过 checkpoint-v5 内容审计：

- `checkpoint_complete.json` 为 `status=complete`、`completed_steps=next_step=50`、`world_size=4`，所有登记文件尺寸一致；不存在 `.0000050.incomplete` 残留；
- `adapter.safetensors` SHA-256 为 `7767c3b10e599dafa165a3229220fac0fad9c9f926009cb3fedd6c4a7603f55d`，包含 512 个 FP32 A/B tensor、总参数量 120,412,160，与已通过恢复 Gate 的 v3 smoke adapter 名称集合和 shape 全部一致；
- 256/256 个 `lora_B` 均非零且各 tensor 的全部元素均已脱离零初始化，其中 generation expert 为 252/252、generation I/O 为 4/4；512 个 adapter tensor 均为有限值；
- DCP 实际物化后包含 512 组参数状态和 2,048 个 optimizer tensor。512/512 个 `exp_avg` 与 512/512 个 `exp_avg_sq` 均非零，全部 Adam step counter 为 50；DCP 携带的 512 个 live 参数值与 `adapter.safetensors` 逐 tensor bitwise 相同；
- scheduler 为 `last_epoch=50 / _step_count=51 / lr=9.993693574008003e-05`；trainer cursor 为 `epoch=0 / epoch_step=50 / optimizer_boundary=true`；四个 rank 的 Python、NumPy、CPU Torch 与 CUDA RNG 状态均存在；
- checkpoint 总占用约 1.9 GiB。保存完成后训练继续越过 step50，未见 OOM、NaN、traceback 或 checkpoint 运行时错误。

因此旧 Job `122549` 的 nested-FSDP stale adapter 故障没有在正式 v3 checkpoint 中复现，首个正式保存 Gate 已关闭。此次审计验证了正式 step50 文件内容；没有为了测试而中断当前任务做一次真实 restart。相同 checkpoint-v5 恢复路径此前已由 Jobs `122843/122844/122845` 在四卡上完成逐 tensor 连续/恢复验证。

### 6.3 清理后的保留状态

首存 Gate 通过后，用户授权删除已被正式结果取代的重型 smoke/调试 Run。Stage 4/5 的 audit JSON 与 Slurm 日志继续保留，但其源 smoke checkpoint 路径已离线；当前 v3 正式目录未参与清理，清理后仍有完整 `0000050` 与 `0000100`。Lance `outputs/` 从约 163 GiB 降至约 31 GiB，细节见 [`datamake_lance_storage_cleanup_20260904.md`](./datamake_lance_storage_cleanup_20260904.md)。

### 6.4 首段时限退出与当前视觉检查（2026-09-05）

首段 Job `122959` 于 2026-09-05 13:03:06 达到 18 小时时限，Slurm 状态为 `TIMEOUT`，最后完整记录为 step422，不能将 wrapper 的 exit0 当作 1,800-step 已完成。最新完整 `0000400` 经 CPU 深审计：512 adapter 与 DCP live 值相同、256 个 `lora_B` 和全部 Adam moments 非零、scheduler/cursor/四 rank RNG 完整。

用户提交 Job `123628`，已于 21:19:36 在 `H64Y574/testqueue` 获得四 H200 并从 `starting_step=400` 正常恢复；W&B 续写同一 Run。重跑的旧步号指标会被 W&B 忽略而非覆盖，越过旧记录范围后恢复追加，不影响真实 optimizer 更新。

用户随后要求先看早期效果。在另一 allocation `123574/BFS9B74` 的单 H200 上运行准备时最新的完整 step400，标准 30-step、CFG1、seed42；真正三轮回灌与三个 teacher-forced case 相互独立。推理 loader 的 512 adapter 均与 checkpoint 转 BF16 后一致。状态和后续视觉结论见 step400 视觉检查（历史文件已于2026-09-11清理）。正式训练和 sampler 未因这次检查而改变。

### 6.5 用户要求提前结束第二段（2026-09-06）

14:54:39（新加坡时间）核验：A Job `123628/H64Y574/testqueue` 已用 `17:35:03`，剩余 `00:24:57`，最后完成 step810。最近 50 个 optimizer step 平均约 150.01 秒，距离下一个保存点 step850 还有 40 步，预计约 100 分钟，无法在本次 allocation 内完成。

按用户明确要求仅执行 `scancel 123628`；`sacct` 确认主 Job 于 14:55:04 进入 `CANCELLED`，batch 于 14:55:07 退出。没有修改训练代码或冻结配置，没有额外保存、删除 checkpoint 或提交续跑。`checkpoints/0000800` 已通过 launcher 的完整标记、必要文件及文件大小检查；本次未重新做逐 tensor 深审计。已完成但未保存的 step801～810 舍弃，后续若用户决定续跑，应从本臂 step800 恢复。

独立 B Job `123681` 未受影响，14:55:24 仍为 `RUNNING`；其运行和下一保存点由 [Stage 2 基座对照报告](./datamake_stage2base_lora_preparation_20260905.md) 维护。这次停止是剩余时限不足，不是检测到训练故障，也不代表正式训练完成。

## 7. 下一步

1. A 保持停止；若用户决定续跑，只从本臂完整 step800 恢复，不自动提交任务。B 保持原配置运行。
2. step400 六个标准 30-step held-out 输出已由用户复核，效果仍一般；step800 尚未进行视觉评估。后续按用户要求比较同一步数的 A/B 与 Stage 2 起点，不能以训练 loss 替代质量结论。
