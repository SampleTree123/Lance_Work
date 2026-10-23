# Lance DataMake 第二阶段训练结果复盘（2026-09-03）

> 后续保留说明（2026-09-06）：Stage2基座、结果视频与本报告保留；旧`logs/generated_configs/`内的推理输入/评估JSON已按用户明确要求删除。当前推理使用独立Run内的输入与manifest，见[清理记录](./datamake_lance_storage_cleanup_20260906.md#后续授权旧输入与生成配置清理)。

## 结论

第二阶段训练在工程上完整成功，并对部分编辑类型产生了明确的视觉收益，但尚不能判定多轮编辑质量达到预期。

- Job `120425` 在 4×H200 上完成 `3669/3669` optimization steps，主任务 `COMPLETED`、`ExitCode=0:0`。
- 加权与未加权训练 MSE 均下降，过程没有发现 OOM、NaN、Inf、step 缺口或训练异常。
- teacher-forced held-out 样例中，身份编辑和第三轮换装相较第一阶段有大幅改善；第五轮换装也能接近目标。
- 动作样例消除了第一阶段明显的双人重影，但相机和背景发生较大漂移，因此像素指标反而略低。它说明单一像素指标不能替代人工语义判断。
- 真正的三轮自回灌中，第三轮仍能按指令换装，说明多轮调用机制和指令响应没有失效；但第二轮的构图漂移会进入第三轮并继续累积。这是当前最重要的失败模式。

因此，本轮应记为“训练与 checkpoint 通过、局部质量明显提升、多轮累积漂移未解决”，而不是“训练失败”或“质量 Gate 已通过”。

## 训练运行

| 项目 | 结果 |
|---|---|
| Slurm Job | `120425` |
| 时间 | 2026-09-01 18:05:33 ～ 2026-09-02 11:52:46（Asia/Singapore） |
| 用时 | `17:47:13` |
| 资源 | 4×H200，单节点 |
| 数据 | 3,600 train chains；13,483 原始前缀；R5×3 后 14,675 有效前缀 |
| 总步数 | `3669` |
| 初始 checkpoint | 第一阶段 `0003371` |
| 最终 checkpoint | 第二阶段 `0003669` |
| 训练方式 | 全参数 Lance core；ViT/VAE/embedding 冻结；无 LoRA；无 EMA |
| 学习率 | cosine：`1e-5 → 1e-6`，warmup 101 steps |
| 新增策略 | R5 三倍采样；VAE latent 编辑区域 soft weighting；条件 dropout 全关 |

W&B Run：`datamake-dialogue-stage2-r5x3-region-v1`，项目 `datamake_lance`。

保留状态更新（2026-09-04）：Job 完成时的 `0003669` 是完整可恢复 checkpoint；后续清理已删除四个旧 AdamW shard、scheduler 与 cursor，只保留模型和 tokenizer/config，迁移到 `outputs/model_bases/datamake_dialogue_stage2_step3669/`。该 base-only artifact 专供 fresh LoRA 基座消融，不能恢复第二阶段全参训练；详见 [`datamake_lance_storage_cleanup_20260904.md`](./datamake_lance_storage_cleanup_20260904.md)。

## 优化曲线摘要

W&B 本地历史共 3,669 条连续 step 记录：

| 指标 | 前 200 step 均值 | 后 200 step 均值 | 变化 |
|---|---:|---:|---:|
| 加权 `mse` | 0.065398 | 0.045999 | -29.66% |
| `mse_unweighted` | 0.053663 | 0.036942 | -31.16% |
| `total_norm` | 0.15670 | 0.09819 | 下降 |
| `step_time_sec` | — | 17.282 | 稳态正常 |

其他事实：

- 最后一步加权/未加权 MSE 为 `0.04402 / 0.03367`。
- 编辑区域平均权重全程均值约 `1.22536`，最后一步 `1.22711`；最大权重始终为 `2.0`。
- 梯度范数最大值 `7.5377`，没有非有限值；最后一步 `0.12215`。
- 平均 step time 约 `17.398 s`。

这些结果证明优化过程有效，但训练集 loss 下降不能单独证明 held-out 多轮视觉质量。

## Checkpoint 与日志

唯一保留的最终 checkpoint：

`10_research/model_experiments/lance/outputs/training_runs/datamake_dialogue_stage2_r5x3_region_fullparam_4xh200_v1/checkpoints/0003669/`

- 总占用约 68 GiB。
- `model.safetensors`：28,422,373,304 bytes。
- 4 个 optimizer shard：每个 11,110,227,837 bytes。
- `checkpoint_complete.json`、`trainer_state.json`、scheduler、data status 和 4 个 optimizer shard 齐全。
- rolling retention 已删除更早 checkpoint，只保留最终 `0003669`。

运行证据：

- `outputs/slurm_logs/dm_lance_dialogue_s2_120425.out`
- `outputs/slurm_logs/dm_lance_dialogue_s2_120425.err`
- `outputs/training_runs/datamake_dialogue_stage2_r5x3_region_fullparam_4xh200_v1/segments/job_120425/launch_manifest.json`
- `outputs/training_runs/datamake_dialogue_stage2_r5x3_region_fullparam_4xh200_v1/wandb/`

## 视觉结果

统一推理设置：validation split、30 diffusion steps、CFG `1.0`、seed `42`、50 requested frames。输出均为 848×480、57 frames、12 fps。

teacher-forced 条件下：

| 样例 | 第二阶段 mean SSIM-luma | 对照结论 |
|---|---:|---|
| R1 身份 | 0.80890 | 第一阶段为 0.50695；明显提升并接近目标 |
| R2 动作 | 0.21927 | 第一阶段为 0.24528；双人重影消失，但构图/背景漂移导致像素分数下降 |
| R3 换装 | 0.80037 | 第一阶段为 0.25236；明显提升并接近目标 |
| R5 换装 | 0.63965 | 无同条件第一阶段对照；视觉上能完成换装并保留主要结构 |

视觉输出根目录：

`outputs/multiturn_chat/stage2_3669_visual_sanity_20260903/`

重点预览：

- `comparison_preview_{10,50,90}pct.jpg`：第一阶段、第二阶段与 GT 对比。
- `outfit_r5_preview_{10,50,90}pct.jpg`：第五轮输入、第二阶段输出与 GT 对比。
- `rollout_comparison_preview_{10,50,90}pct.jpg`：真正自回灌的每轮输入、GT-history 输出与 rollout 输出对比。

## 真正自回灌结果

同一条三轮链依次执行身份、动作、换装，并把前一轮模型输出作为后一轮输入：

| 轮次 | mean SSIM-luma（相对原始 GT target） | 观察 |
|---|---:|---|
| R1 身份 | 0.80890 | 与 teacher-forced R1 一致 |
| R2 动作 | 0.21796 | 动作被执行，但相机/背景明显漂移 |
| R3 换装 | 0.21477 | 能在 R2 的生成状态上继续换装，但继承已偏移的构图，与原始 GT 链目标差距大 |

低像素分数不能简单解释成“第三轮没有执行指令”。更准确的解释是：模型能对当前生成状态继续编辑，但训练只见过真值历史，未学习如何从自身带误差的历史状态中恢复或抑制漂移。

## 对下一阶段的直接启示

1. 增加模型输出历史作为条件是有针对性的：它直接覆盖了当前自回灌暴露出的 exposure gap。
2. 必须保留 teacher-forced LoRA 对照，否则无法区分收益来自 LoRA/学习率，还是来自模型输出历史。
3. 当最新 direct VAE source 也换成模型输出时，它不再是 GT target 的精确渲染父节点；原有 source-target latent 差分区域加权会把累积误差误判为编辑区域，首次对照必须关闭该加权。
4. 现有四个视觉样例只能作为 sanity，不足以形成正式质量结论；下一轮至少应冻结同一组链、seed、30 steps 与逐轮自回灌协议。
