# Stage 2 基座 LoRA 对照准备（2026-09-05）

> 状态：`formal_job_123681_running_visual_pending`（2026-09-06 核验）。  
> 实验：`ABL-LORA-BASE-01/B`；执行所有者：[训练接入 §6.10](../training_integration.md#610-stage-2-基座对照的手动启动与续跑)。

## 决定与范围

用户播放当前 v3 step400 后认为效果仍一般，决定保持官方基座臂继续训练，同时准备 Stage 2 基座对照；2026-09-05 准备阶段由用户负责提交 Slurm，Codex 未提交或占用新 GPU，也未修改 Job `123628` 的配置或共享训练实现。用户随后提交的真实 Job 为 `123681`，运行更新见下节。

新臂只将官方 Lance 基座换为第二阶段 Job `120425` 最终 step3669 权重。全部基座冻结，挂接 fresh generation-only r64/alpha64/dropout0 LoRA；不加载官方基座臂的 adapter，不恢复旧 Stage 2 optimizer，也不继承当前 v3 的 step/data cursor。优化器、scheduler、LoRA 与链游标均从新实验 step0 开始。

## 独立入口与身份

- Profile：[datamake_dialogue_one_step_x0_lora_r64_stage2base_v1.json](../configs/datamake_dialogue_one_step_x0_lora_r64_stage2base_v1.json)。
- Slurm：[datamake_dialogue_one_step_x0_lora_r64_stage2base_v1.sbatch](../jobs/datamake_dialogue_one_step_x0_lora_r64_stage2base_v1.sbatch)。
- 测试：[test_datamake_stage2base_profile.py](../tests/legacy/test_datamake_stage2base_profile.py)。
- 复用 launcher：`scripts/run_datamake_online_rollout_lora_training.py`。
- 复用 trainer：`lance/train/datamake_online_rollout_lora_train.py`；LoRA/checkpoint v5/one-step 实现均不修改。
- Run Root：`outputs/training_runs/datamake_dialogue_one_step_x0_lora_r64_4xh200_stage2base_v1/`，仅在用户提交且启动预检通过后创建。
- W&B project：`datamake_lance`；Run ID：`datamake-dialogue-one-step-x0-lora-r64-stage2base-v1`；group 与 A 同为 `first-batch-dialogue-one-step-x0`，新增 `stage2-base`、`ablation-base-01-b` tags。
- stdout/stderr：`outputs/slurm_logs/dm_lance_x0_s2base_<job_id>.out/.err`。

`training_authorized=true` 表示这份经用户确认的配置可由用户直接提交，不表示 Codex 已提交。首次命令显式传 `RESUME_FROM=none`；后续只用本 Run Root 的 `latest`。脚本固定新 profile，不继承另一实验的 `DATAMAKE_FORMAL_PROFILE`。

## 基座与控制变量

基座目录为 `outputs/model_bases/datamake_dialogue_stage2_step3669/`；只保留一份模型，不复制到新 Run。模型为 28,422,373,304 bytes，登记 SHA-256 为 `ae9c4aba917af7564403972976bc706a4c6455c169128f2794c12e3bef99075e`。该目录不含旧 optimizer/scheduler，不能恢复旧全参训练，但满足 fresh LoRA 初始化需要。

与 A 相同的训练配方：

- 同一 chain parquet/YAML、3,600/200/200 split、schedule seed2042、global seed2026、同一数据顺序。
- 一行一链；中间历史为同次 forward 的 detached `pred_x0`，全部历史 ViT + 最新历史 VAE；首轮源为真值；GT target 不变。
- 每 target 等权 flow MSE；无 CE、区域加权、R5 加采样或 EMA；三个 condition dropout=0。
- r64/alpha64、256 个 generation/IO 模块、120,412,160 个 FP32 master adapter 参数；BF16 混合精度。
- 4 H200、HYBRID_SHARD、accumulation2、8 chains/update、450 steps/epoch。
- 4 epochs/1800 steps；warmup20；cosine `1e-4→1e-5`；其余 AdamW/clip 不变。
- VAE480/ViT448、12fps、max frames121、max tokens65536、Flex Attention。
- 每50步保存 adapter/optimizer/scheduler/cursor/各rank RNG，最近4份及最终保存；18小时到期不额外保存，手动续跑。

新 profile SHA-256：`793d8a4d90df35986a2f32d82683d5eb6bcc738e24ef0829f9e3c2520dea0b9c`。原 A profile SHA-256 保持 `315a8ef1cec83a16e3ab6f26c01de2d85e298c6145ecf327e85ef4a588637f7d`，其21个冻结实现文件均不修改。

## 2026-09-06 运行更新

用户提交 Job `123681` 后，任务于 00:09:08 在 `8GS9B74/testqueue` 启动；实际入口使用 Stage 2 step3669 基座、fresh LoRA 和 `RESUME_FROM=none`，与官方基座 A 使用独立 Run/W&B。本次 allocation 的 18 小时截止为 18:09:08（新加坡时间）。

14:54:39 核验时，B 仍为 `RUNNING`，已用 `14:45:31`、剩余 `03:14:29`；最后完成 step341，最新完整标记为 step300。最近 50 步平均约 152.67 秒，估算达到 step350 还需约 23 分钟，达到 step400 还需约 150 分钟，因此本段预计可保存到 step400，但实际链长与保存耗时会影响结果。本次没有重新深审计 B 的 checkpoint tensor，也没有执行视觉推理。

A Job `123628` 因剩余时间不足到达下一保存点，已按用户要求于 14:55:04 取消，恢复点为 step800；B 未受影响，14:55:24 仍为 `RUNNING`。下一步保持 B 运行；后续只从各自 Run 的完整 checkpoint 手动恢复，不跨臂混用 adapter、optimizer 或游标。

## 准备阶段验证与未执行边界（2026-09-05）

- 82 项 Lance unittest 已通过，其中5项新测试覆盖配方相同、fresh Stage 2 命令、训练入口合约、Run/W&B 隔离、基座 LoRA topology 和 Slurm 约束。
- Stage 2 权重头部实查为256个 LoRA target、120,412,160参数；名称/shape 签名与 A 相同。
- Slurm `bash -n` 已通过。2026-09-05 `scontrol show partition testqueue` 确认分区 UP、MaxTime18:00:00；新脚本只申请该分区单节点4H200，最多18小时。
- 完整基座 SHA-256/source/data dry-run 已通过，基座全文哈希与保留 Manifest 一致，实际命令使用 Stage 2 基座且没有 `--resume_from`；data YAML/manifest和全部22个实现引用哈希通过。
- `sbatch --test-only` exit0，仅给出预计节点8GS9B74；不是正式提交，不产生新训练 Job。脚本语法与资源配置通过，不保证实际排队启动时间。
- 对 test-only 预测编号的 `squeue` 查询返回 Invalid job id，确认它不是已提交任务；原 Job `123628` 仍为 RUNNING。当前 scratch 可用约487GiB，无需复制28.4GB基座或视频。
- 132项核心unittest（documentation22、dataset30、Unreal80）通过；Script Catalog/Output Inventory 已重建。文档审计114份文档可达、669条链接、各独立子系统及跨层检查均零错误、零警告；`git diff --check` 通过。
- 未执行 Stage 2 基座的新 GPU optimization smoke、未提交新训练、未产生新 checkpoint 或 W&B Run。沿用已通过的 v3 四卡连续/恢复工程证据，因为训练代码、目标拓扑、FSDP 和数值计算流程均未改变；不把它写成新基座运行或视觉已通过。
- 实际分配的 GPU 与 W&B 身份预检仍由既有 launcher 在用户提交后的计算节点完成；不为了预检挤占当前 A 的四卡。

## 评估与解释

先在 B 的 step50～100 检查能力是否明显退化；在 A/B 同 step400、900 比较固定样例、prompt、seed42、30-step、CFG1，并始终保留 Stage 2 未加新 adapter 的起点对照。已有 Stage 2 六例可作初始参考，后续同协议推理仍属于独立操作，本次脚本没有自动视觉评估。

总 horizon 保持1800，不为只看400步而缩短 cosine。按用户视觉判断早停；“B 优于 A”不代表“B 优于自身起点”。该实验比较基座选择，不是相同累计预训练/微调计算成本下的对比。少量 sanity 不能关闭 L06/L08；发布数据和 test split 不修改。
