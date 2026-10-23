# DataMake Stage 4 在线 Rollout LoRA 实现说明（2026-09-04）

> 状态：`checkpoint_v5_gpu_gate_passed_formal_restart_pending_user_authorization`  
> 冻结配置：`../configs/datamake_dialogue_online_rollout_lora_r64_v2.json`（历史文件已于2026-09-11清理）  
> Lance 基线：`bytedance/Lance@9717d9160ed16fedfdad5ce39ccbc6c9d69695e0`  
> 结论边界：代码、数据契约、CPU 打包和四卡 GPU optimization/save-resume 逐 tensor Gate 已通过；旧正式 Job `122549` 因 checkpoint 导出缺陷已停止且不可恢复，新正式训练尚未重新授权。尚无 held-out 视觉质量结论。

## 1. 本版冻结决策

本版从官方 Lance 预训练权重挂接 fresh、zero-output 的 LoRA，不继承第一或第二阶段权重。LoRA 固定 `r=64 / alpha=64 / dropout=0`，只覆盖 252 个 generation expert linear 与 4 个 generation I/O linear；全部基座参数、理解分支、ViT、VAE、embedding 与 lm head 冻结，EMA 关闭。所选 `qwen_2_5_vl_original` ViT 路径没有独立 connector 参数，因此配置中的 `freeze_vit_connector=false` 表示“该结构不存在 connector”，不是把 connector 设为可训练。

训练数据不再把 3,600 条 train chain 展开成 13,483 行互相独立的前缀。新的 chain parquet 每条链只有一行；训练主循环在链内依次执行每一轮：

```text
turn 1: ViT(v0), VAE(v0), p1                 -> loss(generation target v1), rollout g1
turn 2: ViT(v0,g1), VAE(g1), p1,p2           -> loss(generation target v2), rollout g2
turn 3: ViT(v0,g1,g2), VAE(g2), p1,p2,p3     -> loss(generation target v3), ...
```

- `g1...g(t-1)` 在训练 step 内由当前 LoRA 模型按 30 diffusion steps 在线生成。
- rollout 全程 `torch.no_grad()`，每轮结果 detach 后以 CPU FP16 `C×T×H×W` 张量保存到当前链的内存中。
- 下一轮的全部历史 ViT 条件和最新直接 VAE source 都使用模型生成张量；初始 `v0` 与当前 GT target `vt` 仍从 released 包读取。
- 不经过临时 MP4 编码/解码，避免把 codec 伪影混入训练条件。
- 最后一轮之后不生成无人使用的 `gT`。

## 2. 数据与调度

派生数据位于：

```text
outputs/training_data/datamake_dialogue_first_batch_v002_chain_seed2026_20260904/
```

它沿用既有 seed `2026` 的 3,600/200/200 chain split，仅把每条链压缩为最长完整记录：

| Split | Chains | 每 Epoch target videos |
|---|---:|---:|
| train | 3,600 | 13,483 |
| validation | 200 | 754 |
| test | 200 | 763 |

Train 链长分布为 R3 `1,513`、R4 `1,491`、R5 `596`。四个 rank 每次各处理一条链，同一 collective group 优先使用等长链；唯一 leftover group 是 1 条 R3 与 3 条 R4，因此每 Epoch 只需 1 次无损失 dummy rollout 来保持 FSDP collective 次序一致。每两个 chain group 做一次 optimizer update，故：

```text
3,600 chains / 4 GPUs / accumulation 2 = 450 optimizer steps / epoch
4 epochs = 1,800 optimizer steps
```

R5 不再过采样，区域加权关闭，standalone 不混入。

## 3. Loss 与梯度累计

每个目标视频仍使用 Lance 原生 flow-matching latent MSE，不是解码为 RGB 后计算像素 MSE。单个 target 先对 latent channel 与 token 求平均得到 `loss_t`。一个 accumulation window 内共有 `N` 个真实 target；各 rank 对每个 target 的 backward 系数为 `world_size / N`，抵消 FSDP 的跨 rank 平均后得到：

```text
window_loss = (loss_1 + ... + loss_N) / N
```

因此所有目标视频权重完全相同；含 5 个目标的链自然比含 3 个目标的链贡献更多总监督。rollout 结果已 detach，梯度不会跨轮反传，也不会把 30-step 采样图保留到后续轮次。`CE weight=0`，编辑区域权重关闭。

这里存在已接受但必须独立解释的监督错配：第 `t` 轮实际 direct parent 是生成的 `g(t-1)`，而 rendered target `v(t)` 的真实父节点是 `v(t-1)`。因此该 loss 同时训练“执行当前编辑”和“修复上一轮生成误差”，结果不能只归因为 exposure-bias 修复；`teacher-forced` 与 ViT-only generated-history 消融仍是区分两种效应的必要证据。

## 4. 优化、采样与日志

| 项目 | 冻结值 |
|---|---|
| 优化器 | AdamW，betas `0.9/0.95`，eps `1e-15`，weight decay `0` |
| LR | `1e-4`，warmup 20 steps，cosine 到 `1e-5` |
| 梯度裁剪 | `1.0` |
| 精度 / attention | BF16 / Flex attention |
| 视频输入 | VAE 480、ViT 448、12 fps、最多 6 秒 |
| token 上限 | 65,536 |
| rollout | 30 steps、text CFG `1.0`、timestep shift `3.0`、KV cache 开启 |
| 条件 dropout | text/ViT/VAE 全部 `0` |
| 训练 timestep shift | `4.0` |
| W&B | online，每 optimizer step 记录聚合指标 |

W&B 标量包括总 `mse`、`mse_round_1..5`、各轮 target 数、LR、梯度范数、同步后的 step/rollout/train 时间、target/rollout 数，以及跨 rank 的 rollout summon 前、完整参数召回后、生成峰值和退出 summon 后的 allocated/reserved 显存最大值。默认不上传原视频、生成历史、checkpoint、源码或训练媒体。

## 5. Checkpoint 与恢复

每 50 个 completed optimizer steps 保存一次，保留最近 4 个完整 checkpoint，并额外保存最终 step。checkpoint 不复制约 28 GB 基座，包含：

- `adapter.safetensors` 与精确 LoRA target topology；
- 分布式 AdamW optimizer state；
- scheduler、completed-step cursor；
- 每 rank Python/NumPy/Torch CPU/CUDA RNG；
- 数据、rollout、loss、基座 hash 与 profile hash 契约；
- 最后原子写入的 `checkpoint_complete.json`。

恢复要求相同的 4-GPU FSDP topology，并从完整 optimizer boundary 的下一 step 接续。旧实现通过模型 state dict 导出 nested-FSDP LoRA 时只保存了 2/256 个非零 `lora_B`；checkpoint v5 改为让 live LoRA shard 临时随官方 optimizer-state FQN 映射进入 DCP，导出后立即清除临时字段。恢复时只要求本 rank 实际拥有的非空 `use_orig_params=True` shard，空占位参数按 FSDP 语义跳过。

最终四卡验证对“连续训练 3 steps”和“训练 2 steps 保存、重启恢复并执行 step 3”进行了逐 tensor 比较：512/512 个 adapter 张量、2,048/2,048 个 optimizer 状态张量和 8/8 个 RNG tensor 全部 bitwise 相同，最大绝对差为 0；scheduler 与 trainer cursor 也完全一致，step2 checkpoint 中 256/256 个 `lora_B` 均非零。机器可读结果见 [`datamake_stage4_lora_resume_smoke_audit_20260904.json`](./datamake_stage4_lora_resume_smoke_audit_20260904.json)。

## 6. 实现入口

| 文件 | 作用 |
|---|---|
| `scripts/build_datamake_chain_training_data.py` | 从冻结 split 生成一行一链的 parquet/YAML/manifest，并核验源哈希与零泄漏 |
| `lance/train/datamake_online_rollout.py` | chain schema、确定性 seed、collective-safe 调度、每轮动态行和训练契约 |
| `lance/data/datasets_factory/dataset_datamake_multiturn_v2v_local.py` | 保持 Stage 2 路径式 Dataset 原文件和冻结哈希不变，继续提供已验证的角色编码 |
| `lance/data/datasets_factory/datamake_online_rollout_turn.py` | Stage 4 独立动态行适配器：接受审计路径或内存视频张量，构造历史 ViT、最新 VAE source 和当前 VAE target |
| `lance/train/datamake_generation_lora.py` | 精确 256-target LoRA、全冻结、adapter 严格加载 |
| `lance/train/datamake_lora_checkpoint.py` | adapter-only 原子 checkpoint 与 exact resume |
| `lance/train/datamake_online_rollout_lora_train.py` | 在线生成、逐 target loss、梯度累计、W&B 与 checkpoint 主循环 |
| `scripts/run_datamake_online_rollout_lora_training.py` | profile/source/data/base hash、W&B、GPU、resume 与授权校验 |
| `jobs/datamake_dialogue_online_rollout_lora_r64_v2*.sbatch` | testqueue 四卡正式/smoke 资源与日志入口 |
| `patches/legacy/0011-datamake-chain-online-rollout-lora.patch` | 相对 `0010` 基线的一行一链在线 rollout 实现 |
| `patches/legacy/0012-fix-nested-fsdp-lora-checkpoint.patch` | checkpoint v5：nested-FSDP live LoRA 导出和 exact resume 修复 |

启动器和训练入口都 fail closed：重复 CLI 参数被拒绝，history mode 与实际 YAML/manifest/parquet 强绑定，正式 profile 在 `training_authorized=false` 时即使绕过 launcher 也不能运行。

用户提供的 `/home/users/astar/cfar/stuchengyou/jcy/xks/1.md` 代码审查建议已落实到本版：基底与 adapter 路径分离；LoRA target 用精确名称/shape/signature 校验；profile 锁定真实源码、数据和基底哈希；resume 必须匹配完整 adapter/optimizer/scheduler/cursor/RNG 契约；正式与 smoke 均由可执行 launcher/profile 驱动而不是仅停留在设计说明。额外回归中还把内存视频输入隔离到 Stage 4 适配器，避免改变已完成 Stage 2 的冻结 Dataset 哈希。

后续快速审查又关闭了三个静态缺陷：独立 adapter 推理 loader 现在先调用 Lance 原始 loader 加载 `--model_path` 基底，再挂 LoRA 并严格读取 adapter；传给 Lance 的 noise seed 会抵消其内部 rank offset，使实际 seed 与 rank 分配无关；训练入口新增 QK norm、ViT type、latent patch、frame/latent 上限、visual path、ViT connector freeze 和 FSDP topology 等关键参数绑定。完整模型召回仍是显存/吞吐高风险，现已加入专门遥测，但只有四卡 smoke 才能关闭。

## 7. 已验证证据与剩余边界

已完成：

- chain 数据构建：train/validation/test 为 3,600/200/200 chains 和 13,483/754/763 targets；
- 29 项聚焦 DataMake/LoRA/rollout unittest 与当前 72 项完整 Lance unittest 通过；其中测试覆盖 base 先于 adapter 加载、rank seed offset 抵消、正式授权与 smoke 恢复 run identity，并拒绝直接入口的模型结构漂移；Stage 2 冻结 profile 回归测试仍通过；
- adapter-only 单进程模型、AdamW、scheduler 与 RNG 保存恢复 roundtrip 通过；
- 真实五轮内存历史 CPU pack 为 33,191 / 40,530 / 47,868 / 55,205 / 62,542 tokens，均小于 65,536；每轮恰有 1 个 VAE source、1 个 VAE target；
- profile dry-run 与 Hugging Face 参数解析通过；
- `0011` 在应用到 `0010` 后的临时 Lance 基线上通过 `git apply --check`。

首次四卡 smoke Job `122546/122547` 只比较了恢复前后的 step 标量，没有覆盖非零 nested LoRA 的逐 tensor roundtrip。随后正式 Job `122549` 虽然训练前向、梯度与调度正常，但 step50 审计发现其 adapter 只有 2/256 个 `lora_B` 非零，而 Adam DCP 中 256/256 个模块都有非零动量。这证明训练发生了，但模型 state 导出读取了 nested FSDP 的初始化视图。用户在 completed step99 后停止该 Job；其 checkpoint 和 W&B 只能作为故障证据，禁止推理、恢复或继续训练。

checkpoint v5 的最终四卡 Gate 于 `testqueue` 单节点 4×H200 上关闭：

- Job `122758` 从官方基座和 fresh LoRA 连续完成 3 steps，Slurm `COMPLETED/0:0`；step1/2/3 的 MSE 为 `0.265194 / 0.239544 / 0.198684`；
- Job `122827` 从共同初始状态完成 2 steps 并写出 checkpoint，Slurm `COMPLETED/0:0`；step2 checkpoint 的 256/256 个 `lora_B` 均已脱离零初始化；
- Job `122836` 读取该 checkpoint，日志确认 `starting_step=2`，完成 step3 并 `COMPLETED/0:0`；其 step3 MSE、grad norm、LR、target/rollout 数和 rollout latent sum/square/numel 均与连续基准完全一致；
- 离线审计比较 512 个 adapter tensor、2,048 个 Adam/custom parameter-state tensor、8 个 per-rank RNG tensor、scheduler 与 trainer cursor，全部 bitwise 相同，最大绝对差为 `0.0`；
- backward → 已累计梯度 → full-param summon → 30-step KV-cache rollout → VAE decode → 后续 backward → optimizer → checkpoint save/load → 下一轮 backward 的真实四卡路径已通过，无 OOM、NaN 或 collective hang。

最终实现继续使用 Lance 现有 PyTorch trainer 与 DCP，不引入未安装的 PEFT/Accelerate。官方 PEFT 的 FSDP 路线要求不同的 `use_orig_params` 和 auto-wrap policy，会改变现有拓扑；若未来替换，应作为独立实现和独立 smoke，而不是当前修复的无验证替换。

仍未完成：用户重新授权 v2 正式训练、正式 checkpoint 的视觉审看和 held-out 多轮质量评估。当前结论只证明训练工程路径与 exact resume 正确，不证明多轮编辑质量有效。
